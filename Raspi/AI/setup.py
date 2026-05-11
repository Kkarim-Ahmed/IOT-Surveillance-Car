"""
First-time setup: download tiny TFLite models and build face encodings.

Run once before starting the system:
    python setup.py

What it does:
  1. Creates models/ directory
  2. Downloads MobileFaceNet TFLite (~4 MB) — the tiny recognition model
  3. Scans dataset/faces/ and builds dataset/encodings.pkl
"""

import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))


# ── Model URLs ────────────────────────────────────────────────────────────────

# MobileFaceNet quantized INT8 TFLite — 4.0 MB, ~30 ms on RPi4
# Source: Qengineering Face-Recognition-Raspberry-Pi-64-bits
MOBILEFACENET_URL = (
    "https://github.com/Qengineering/Face-Recognition-Raspberry-Pi-64-bits"
    "/raw/main/models/MobileFaceNet.tflite"
)


def download(url: str, dest: Path) -> bool:
    if dest.exists():
        print(f"  Already exists: {dest.name}")
        return True
    print(f"  Downloading {dest.name}  ({url[:60]}…)")
    try:
        urllib.request.urlretrieve(url, str(dest))
        size = dest.stat().st_size / 1024
        print(f"  ✓ Saved {dest.name}  ({size:.0f} KB)")
        return True
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        return False


def download_models() -> None:
    models_dir = ROOT / "models"
    models_dir.mkdir(exist_ok=True)

    print("\n── Downloading tiny TFLite models ──")
    ok = download(MOBILEFACENET_URL, models_dir / "mobilefacenet.tflite")
    if not ok:
        print("\n  Note: MobileFaceNet download failed.")
        print("  The system will use InsightFace ONNX as fallback (auto-detected).")


def build_encodings() -> None:
    print("\n── Building face encodings ──")
    dataset_dir = ROOT / "dataset" / "faces"
    if not dataset_dir.exists():
        print(f"  No faces found in {dataset_dir}")
        print(f"  Create folders like:  dataset/faces/YourName/*.jpg")
        print(f"  Then run:  python setup.py")
        return

    persons = [p for p in dataset_dir.iterdir() if p.is_dir()]
    if not persons:
        print("  No person folders found. Add photos first.")
        return

    from dataset.manager import DatasetManager
    dm = DatasetManager()
    dm.build_and_save()


if __name__ == "__main__":
    print("=" * 50)
    print("  Raspi/AI — First-Time Setup")
    print("=" * 50)
    download_models()
    build_encodings()
    print("\n✓ Setup complete. Run: python main.py\n")
