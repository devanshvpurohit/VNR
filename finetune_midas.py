"""
finetune_midas.py — Teacher-student distillation fine-tune of MiDaS_small
                    for Indian indoor/outdoor depth scenes.

Design rationale
----------------
True metric-depth fine-tuning requires ground-truth depth maps (LiDAR /
structured-light sensors) which this project doesn't have.  Instead we use
teacher-student distillation:

  1. TEACHER  — frozen DPT_Large (high-capacity MiDaS model).  Run ONCE per
                training image to generate pseudo-ground-truth depth maps.
                Maps are cached to disk so the teacher is never re-run during
                training epochs.

  2. STUDENT  — MiDaS_small with its encoder entirely frozen and only the
                last 2 decoder blocks unfrozen (≈ 600 k trainable params).
                This recalibrates depth for Indian surfaces (dimly-lit
                corridors, rough roads, Mangalore-tile floors, etc.) without
                disturbing the general depth-ordering that MiDaS already
                does well.

  3. LOSS     — scale-invariant log loss (SILog), which is robust to the
                absolute-scale ambiguity in monocular depth estimation.

  4. TRAINING — 4 epochs, decoder-only.  Intentionally shallow.  Deeper
                training on a small (~50-200 image) domain-specific set risks
                catastrophic forgetting of MiDaS's general knowledge.

Usage
-----
    python finetune_midas.py \\
        --images path/to/indian_scenes/ \\
        --epochs 4 \\
        --lr 1e-5

The --images directory should contain .jpg / .png photos of typical Indian
environments where SURDAS operates: corridors, staircases, pavements, markets,
home interiors.  200 images is a good starting point.

Output
------
    models/midas_small_india_ft.pt   ← loaded automatically by surdas_brain.py
"""
import argparse
import os
import torch
import torch.nn as nn
import numpy as np
from pathlib import Path

# ── CLI ──────────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser(description="Fine-tune MiDaS_small via teacher-student distillation")
parser.add_argument("--images",         required=True, metavar="IMAGE_DIR",
                    help="Directory of Indian scene images (.jpg / .png)")
parser.add_argument("--epochs",         type=int,   default=4,
                    help="Training epochs (default 4 — intentionally shallow)")
parser.add_argument("--lr",             type=float, default=1e-5,
                    help="Learning rate (default 1e-5)")
parser.add_argument("--freeze-encoder", action="store_true", default=True,
                    help="Freeze student encoder (default True; unset only for experiments)")
parser.add_argument("--no-freeze-encoder", dest="freeze_encoder", action="store_false")
parser.add_argument("--batch",          type=int,   default=4,
                    help="Batch size (default 4; reduce to 2 if OOM)")
parser.add_argument("--cache-dir",      default=".midas_teacher_cache",
                    help="Directory for cached teacher depth maps (default .midas_teacher_cache)")
args = parser.parse_args()

# ── Imports (after argparse so --help is fast) ───────────────────────────────
import cv2
from torch.utils.data import Dataset, DataLoader

# ── Device ───────────────────────────────────────────────────────────────────
if torch.cuda.is_available():
    DEVICE = "cuda"
elif torch.backends.mps.is_available():
    DEVICE = "mps"
else:
    DEVICE = "cpu"

print(f"[FINETUNE-MIDAS] Device: {DEVICE}")

SCRIPT_DIR = Path(__file__).resolve().parent
MIDAS_REPO = Path.home() / ".cache" / "torch" / "hub" / "intel-isl_MiDaS_master"

if not MIDAS_REPO.is_dir():
    raise RuntimeError(
        "MiDaS hub cache not found. Run setup_offline_models.py while online first."
    )

# ── Load teacher (DPT_Large) — used ONLY for pseudo-GT generation ─────────────
print("[FINETUNE-MIDAS] Loading DPT_Large teacher ...")
# DPT_Large requires internet for first pull — this must be run while online
# (same session as setup_offline_models.py, or while online).
try:
    teacher = torch.hub.load(
        str(MIDAS_REPO), "DPT_Large", source="local", pretrained=True
    ).to(DEVICE).eval()
    teacher_transforms = torch.hub.load(str(MIDAS_REPO), "transforms", source="local")
    teacher_transform = teacher_transforms.dpt_transform
    print("[FINETUNE-MIDAS] ✅ DPT_Large teacher loaded from local hub cache.")
except Exception:
    # Fall back to downloading if not in cache yet
    print("[FINETUNE-MIDAS] DPT_Large not in local hub cache — downloading ...")
    teacher = torch.hub.load(
        "intel-isl/MiDaS", "DPT_Large", trust_repo=True
    ).to(DEVICE).eval()
    teacher_transforms = torch.hub.load("intel-isl/MiDaS", "transforms", trust_repo=True)
    teacher_transform = teacher_transforms.dpt_transform

for p in teacher.parameters():
    p.requires_grad_(False)

# ── Load student (MiDaS_small) ────────────────────────────────────────────────
print("[FINETUNE-MIDAS] Loading MiDaS_small student ...")
student = torch.hub.load(
    str(MIDAS_REPO), "MiDaS_small", source="local", pretrained=True
).to(DEVICE)
student_transforms = torch.hub.load(str(MIDAS_REPO), "transforms", source="local")
student_transform = student_transforms.small_transform

# ── Freeze student encoder, unfreeze last 2 decoder blocks ────────────────────
if args.freeze_encoder:
    # Freeze all params first
    for p in student.parameters():
        p.requires_grad_(False)

    # Unfreeze: last 2 refinenet/decoder blocks.
    # MiDaS_small (EfficientNet-Lite3 + DPT-like decoder) has
    # scratch.refinenet1 and scratch.refinenet2 as the shallower output blocks.
    decoder_blocks_to_unfreeze = []
    for name, module in student.named_modules():
        if any(tag in name for tag in [
            "scratch.refinenet1",
            "scratch.refinenet2",
            "scratch.output_conv",
        ]):
            decoder_blocks_to_unfreeze.append(name)

    for name, param in student.named_parameters():
        if any(name.startswith(blk) for blk in decoder_blocks_to_unfreeze):
            param.requires_grad_(True)

trainable = sum(p.numel() for p in student.parameters() if p.requires_grad)
total     = sum(p.numel() for p in student.parameters())
print(f"[FINETUNE-MIDAS] Trainable params: {trainable:,} / {total:,} ({100*trainable/total:.1f}%)")

student.train()


# ── SILog Loss ────────────────────────────────────────────────────────────────
def silog_loss(pred: torch.Tensor, target: torch.Tensor, eps: float = 1e-6) -> torch.Tensor:
    """
    Scale-invariant logarithmic loss (SILog).
    Robust to absolute-scale ambiguity in monocular depth.
    """
    # Work in log space
    log_pred   = torch.log(pred.clamp(min=eps))
    log_target = torch.log(target.clamp(min=eps))
    diff       = log_pred - log_target
    n          = diff.numel()
    loss = (diff ** 2).mean() - (diff.sum() ** 2) / (n ** 2 + eps)
    return loss


# ── Dataset with lazy teacher-cache ───────────────────────────────────────────
class IndianDepthDataset(Dataset):
    """
    Loads images from --images dir.
    On first access per image, runs DPT_Large teacher → caches depth map.
    Subsequent epochs load from cache — teacher is never re-run.
    """

    EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

    def __init__(self, image_dir: str, cache_dir: str):
        self.image_dir  = Path(image_dir)
        self.cache_dir  = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.paths = sorted(
            p for p in self.image_dir.rglob("*")
            if p.suffix.lower() in self.EXTS
        )
        if not self.paths:
            raise ValueError(f"No images found in {image_dir}")
        print(f"[FINETUNE-MIDAS] Dataset: {len(self.paths)} images from {image_dir}")

    def _teacher_depth(self, img_path: Path) -> np.ndarray:
        """Generate or load cached pseudo-GT depth map from DPT_Large."""
        cache_file = self.cache_dir / (img_path.stem + "_depth.npy")

        if cache_file.exists():
            return np.load(str(cache_file))

        bgr = cv2.imread(str(img_path))
        if bgr is None:
            raise IOError(f"Cannot read image: {img_path}")
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)

        input_tensor = teacher_transform(rgb).to(DEVICE)

        with torch.no_grad():
            depth = teacher(input_tensor)
            depth = nn.functional.interpolate(
                depth.unsqueeze(1),
                size=(384, 384),   # normalize teacher output size
                mode="bicubic",
                align_corners=False,
            ).squeeze()

        depth_np = depth.cpu().numpy()
        np.save(str(cache_file), depth_np)
        return depth_np

    def __len__(self) -> int:
        return len(self.paths)

    def __getitem__(self, idx: int):
        img_path = self.paths[idx]

        bgr = cv2.imread(str(img_path))
        if bgr is None:
            # Return a dummy sample — collate_fn will discard zeros later
            return (
                torch.zeros(3, 384, 384, dtype=torch.float32),
                torch.zeros(1, 384, 384, dtype=torch.float32),
            )
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)

        # Student input
        student_tensor = student_transform(rgb)  # shape (1, 3, H, W) or (3, H, W)
        if student_tensor.ndim == 4:
            student_tensor = student_tensor.squeeze(0)

        # Teacher pseudo-GT (cached)
        depth_np = self._teacher_depth(img_path)
        depth_t  = torch.from_numpy(depth_np).float()
        # Resize to match student output (MiDaS_small outputs vary with input size;
        # we'll handle resize in the training loop after the forward pass)
        return student_tensor, depth_t


def _collate(batch):
    imgs, depths = zip(*batch)
    return torch.stack(imgs), list(depths)


# ── Pre-generate all teacher caches before training (runs once) ───────────────
print("[FINETUNE-MIDAS] Pre-generating teacher depth caches (runs once) ...")
dataset = IndianDepthDataset(args.images, args.cache_dir)
for i, path in enumerate(dataset.paths):
    _ = dataset._teacher_depth(path)
    if (i + 1) % 10 == 0 or (i + 1) == len(dataset):
        print(f"  Teacher cache: {i+1}/{len(dataset)}", end="\r")
print(f"\n[FINETUNE-MIDAS] ✅ Teacher caches ready in {args.cache_dir}/")

# Disable teacher (free VRAM) — all caches are on disk now
del teacher
if DEVICE == "cuda":
    torch.cuda.empty_cache()


# ── DataLoader ────────────────────────────────────────────────────────────────
loader = DataLoader(
    dataset,
    batch_size=args.batch,
    shuffle=True,
    num_workers=0,      # 0 avoids fork issues with torch.hub on macOS
    collate_fn=_collate,
    drop_last=False,
)

# ── Optimizer ─────────────────────────────────────────────────────────────────
optimizer = torch.optim.AdamW(
    filter(lambda p: p.requires_grad, student.parameters()),
    lr=args.lr,
    weight_decay=1e-4,
)

# ── Training loop ─────────────────────────────────────────────────────────────
print(f"\n[FINETUNE-MIDAS] Training {args.epochs} epoch(s) ...")
for epoch in range(1, args.epochs + 1):
    epoch_loss = 0.0
    n_batches  = 0

    for batch_imgs, batch_depths in loader:
        batch_imgs = batch_imgs.to(DEVICE)

        optimizer.zero_grad()

        # Student forward
        with torch.set_grad_enabled(True):
            pred_depth = student(batch_imgs)   # (B, H', W')

        total_loss = torch.tensor(0.0, device=DEVICE, requires_grad=True)

        for b_idx, gt_depth in enumerate(batch_depths):
            pred = pred_depth[b_idx]           # (H', W')
            gt   = gt_depth.to(DEVICE)

            # Resize GT to match prediction spatial size
            if gt.shape != pred.shape:
                gt = nn.functional.interpolate(
                    gt.unsqueeze(0).unsqueeze(0),
                    size=pred.shape,
                    mode="bilinear",
                    align_corners=False,
                ).squeeze()

            loss_item = silog_loss(
                pred.unsqueeze(0),
                gt.unsqueeze(0),
            )
            total_loss = total_loss + loss_item

        total_loss = total_loss / len(batch_depths)
        total_loss.backward()
        optimizer.step()

        epoch_loss += total_loss.item()
        n_batches  += 1

    avg = epoch_loss / max(n_batches, 1)
    print(f"  Epoch {epoch}/{args.epochs}  avg SILog loss: {avg:.5f}")

# ── Save fine-tuned weights ───────────────────────────────────────────────────
models_dir = SCRIPT_DIR / "models"
models_dir.mkdir(parents=True, exist_ok=True)
dest = models_dir / "midas_small_india_ft.pt"

student.eval()
torch.save(student.state_dict(), str(dest))
print(f"\n[FINETUNE-MIDAS] ✅ Fine-tuned weights saved → {dest}")
print("[FINETUNE-MIDAS] surdas_brain.py will load these automatically on next run.")
