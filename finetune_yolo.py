"""
finetune_yolo.py — Light fine-tune YOLOv8n for Indian context.

Strategy
--------
freeze=10 keeps the first 10 backbone layers (general COCO knowledge) frozen
and only adapts the detection head + the last few backbone layers.  This is a
light fine-tune, not a full retrain — obstacle detection for objects outside
the new classes will not regress.

Useful India-specific classes to annotate (docstring note — not fabricated data):
  • auto-rickshaw        — three-wheeler mixed-traffic obstacle
  • handcart / thela    — common footpath obstacle
  • stray cattle        — cows/buffaloes on roads and footpaths
  • stray dog           — aggressive stray dogs near footpaths
  • two-wheeler clutter — scooters/motorcycles parked on footpaths
  • pothole             — road-surface hazard
  • speed breaker       — unmarked speed bumps
  • currency note       — note held in hand (for currency detection mode)

To annotate training data, use Roboflow, CVAT, or Label Studio and export in
YOLOv8 format (images/ + labels/ directories, data.yaml).

Usage
-----
    python finetune_yolo.py \\
        --data path/to/india_dataset/data.yaml \\
        --epochs 20 \\
        --weights yolov8n.pt

Output
------
    models/yolov8n_india_ft.pt   ← picked up automatically by surdas_brain.py
"""
import argparse
import os
import shutil
from pathlib import Path

# ── CLI ──────────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser(description="Fine-tune YOLOv8n for Indian context")
parser.add_argument("--data",    required=True, metavar="DATA_YAML",
                    help="Path to YOLOv8 data.yaml (Roboflow / CVAT export)")
parser.add_argument("--epochs",  type=int, default=20,
                    help="Training epochs (default 20)")
parser.add_argument("--imgsz",   type=int, default=640,
                    help="Input image size (default 640)")
parser.add_argument("--batch",   type=int, default=16,
                    help="Batch size (default 16, reduce to 8 on low-VRAM GPU)")
parser.add_argument("--freeze",  type=int, default=10,
                    help="Number of backbone layers to freeze (default 10)")
parser.add_argument("--lr0",     type=float, default=0.001,
                    help="Initial learning rate (default 0.001)")
parser.add_argument("--patience",type=int, default=5,
                    help="Early-stopping patience (default 5)")
parser.add_argument("--weights", default="yolov8n.pt",
                    help="Starting weights (default yolov8n.pt)")
parser.add_argument("--name",    default="yolov8n_india_ft",
                    help="Run name (default yolov8n_india_ft)")
args = parser.parse_args()

# ── Imports (after argparse so --help is instant) ───────────────────────────
import torch
from ultralytics import YOLO

# Auto-detect device
if torch.cuda.is_available():
    DEVICE = "cuda"
elif torch.backends.mps.is_available():
    DEVICE = "mps"
else:
    DEVICE = "cpu"

print(f"[FINETUNE-YOLO] Device: {DEVICE}")
print(f"[FINETUNE-YOLO] Starting weights: {args.weights}")
print(f"[FINETUNE-YOLO] Data YAML: {args.data}")
print(f"[FINETUNE-YOLO] Epochs: {args.epochs}  |  Freeze: {args.freeze} layers  |  LR: {args.lr0}")

# ── Load base model ──────────────────────────────────────────────────────────
model = YOLO(args.weights)

# ── Train ────────────────────────────────────────────────────────────────────
results = model.train(
    data=args.data,
    epochs=args.epochs,
    imgsz=args.imgsz,
    batch=args.batch,
    freeze=args.freeze,
    lr0=args.lr0,
    patience=args.patience,
    device=DEVICE,
    name=args.name,
    exist_ok=True,
    verbose=True,
)

# ── Copy best weights to models/ ─────────────────────────────────────────────
script_dir = Path(__file__).resolve().parent
models_dir = script_dir / "models"
models_dir.mkdir(parents=True, exist_ok=True)

# Ultralytics saves best.pt under runs/detect/<name>/weights/best.pt
best_pt = Path(f"runs/detect/{args.name}/weights/best.pt")
if not best_pt.exists():
    # Try relative to script directory
    best_pt = script_dir / f"runs/detect/{args.name}/weights/best.pt"

dest = models_dir / "yolov8n_india_ft.pt"

if best_pt.exists():
    shutil.copy(best_pt, dest)
    print(f"\n[FINETUNE-YOLO] ✅ Best weights saved → {dest}")
else:
    print(f"\n[FINETUNE-YOLO] ⚠️  Could not find {best_pt}. Check runs/ directory.")

# ── Print final mAP ──────────────────────────────────────────────────────────
try:
    metrics = results.results_dict
    map50    = metrics.get("metrics/mAP50(B)", metrics.get("mAP50", "N/A"))
    map50_95 = metrics.get("metrics/mAP50-95(B)", metrics.get("mAP50-95", "N/A"))
    print(f"[FINETUNE-YOLO] Final mAP@50: {map50}   mAP@50-95: {map50_95}")
except Exception as e:
    print(f"[FINETUNE-YOLO] (Could not parse final mAP: {e})")

print(f"\n[FINETUNE-YOLO] surdas_brain.py will automatically use {dest} on next run.")
