"""
setup_offline_models.py — Run ONCE while online to pre-cache all model weights.

After this script completes successfully, SURDAS can run fully offline.
Run with:  python setup_offline_models.py

The script prints a ✅ or ❌ line for each component.
"""
import os
import sys

# Allow downloads — this is the ONE script that should hit the network.
# Clear any offline flags that surdas_brain.py sets.
for _k in ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE"):
    os.environ.pop(_k, None)

os.environ["TORCH_HOME"] = os.path.expanduser("~/.cache/torch")

# Get script directory for path resolution (DO NOT change working directory)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

import traceback

_ok = []
_fail = []


def _step(name: str, fn):
    """Run fn(), print result, record pass/fail."""
    print(f"\n[SETUP] Downloading / verifying: {name} ...")
    try:
        fn()
        print(f"  ✅ {name}")
        _ok.append(name)
    except Exception as e:
        print(f"  ❌ {name}: {e}")
        traceback.print_exc()
        _fail.append(name)


# ── 1. faster-whisper tiny.en ────────────────────────────────────────────────
def _fw():
    from faster_whisper import WhisperModel
    m = WhisperModel("tiny.en", device="cpu", compute_type="int8")
    del m

_step("faster-whisper tiny.en", _fw)


# ── 2. openai-whisper tiny.en (fallback) ─────────────────────────────────────
def _ow():
    import whisper
    m = whisper.load_model("tiny.en")
    del m

_step("openai-whisper tiny.en", _ow)


# ── 3. Silero VAD ────────────────────────────────────────────────────────────
def _silero():
    import torch
    model, _ = torch.hub.load(
        "snakers4/silero-vad",
        "silero_vad",
        force_reload=False,
        onnx=False,
        trust_repo=True,
    )
    del model

_step("Silero VAD (torch.hub)", _silero)


# ── 4. openWakeWord default models ───────────────────────────────────────────
def _oww():
    import openwakeword
    openwakeword.utils.download_models()

_step("openWakeWord default models", _oww)


# ── 5. MiDaS_small + transforms ──────────────────────────────────────────────
def _midas():
    import torch
    model = torch.hub.load(
        "intel-isl/MiDaS",
        "MiDaS_small",
        trust_repo=True,
    )
    transforms = torch.hub.load(
        "intel-isl/MiDaS",
        "transforms",
        trust_repo=True,
    )
    _ = transforms.small_transform
    del model

_step("MiDaS_small + transforms (torch.hub)", _midas)


# ── 6. EasyOCR (en + hi) ─────────────────────────────────────────────────────
def _ocr():
    import easyocr
    reader = easyocr.Reader(["en", "hi"], download_enabled=True)
    del reader

_step("EasyOCR [en, hi]", _ocr)


# ── 7. YOLOv8n ───────────────────────────────────────────────────────────────
def _yolo():
    from pathlib import Path
    from ultralytics import YOLO

    project_dir = Path(SCRIPT_DIR)
    models_dir = project_dir / "models"
    models_dir.mkdir(parents=True, exist_ok=True)

    model_path = models_dir / "yolov8n.pt"

    if model_path.exists():
        print(f"    (already cached at {model_path})")
        YOLO(str(model_path))
        return

    # Download via ultralytics (fetches from GitHub releases)
    model = YOLO("yolov8n.pt")
    downloaded = Path("yolov8n.pt")
    if downloaded.exists():
        downloaded.replace(model_path)
    else:
        # ultralytics may place it elsewhere; copy from wherever it landed
        import shutil
        ul_cache = Path.home() / ".config" / "Ultralytics" / "yolov8n.pt"
        if ul_cache.exists():
            shutil.copy(ul_cache, model_path)
    YOLO(str(model_path))

_step("YOLOv8n (yolov8n.pt → models/yolov8n.pt)", _yolo)


# ── Summary ───────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print(f"  SETUP COMPLETE  ✅ {len(_ok)} passed   ❌ {len(_fail)} failed")
if _ok:
    print("  Passed:", ", ".join(_ok))
if _fail:
    print("  Failed:", ", ".join(_fail))
print("=" * 60)
print()
print("IMPORTANT — one remaining online-only prerequisite:")
print("  Run `ollama pull <model>` (e.g.  ollama pull gemma3:1b) once")
print("  while online.  Ollama model weights are not managed by this")
print("  script.  After pulling, Ollama answers will also work offline.")
print()
if _fail:
    sys.exit(1)
