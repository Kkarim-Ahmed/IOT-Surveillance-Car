"""
setup_and_train.py
==================
One-shot script that:
  1. Installs all Python dependencies
  2. Downloads YOLOv8-nano pretrained weights
  3. Downloads + converts the WIDER FACE dataset to YOLO format
  4. Fine-tunes YOLOv8-nano on WIDER FACE (face-only class)
  5. Exports the trained model to ONNX (for laptop/Pi OpenCV DNN)
  6. Exports to TFLite INT8 (for Raspberry Pi — fastest)
  7. Benchmarks the exported models

Run once:
    python setup_and_train.py

On Raspberry Pi use --no-train to skip training (use pretrained weights only):
    python setup_and_train.py --no-train --export-only
"""

import subprocess
import sys
import os
import argparse
import shutil
import zipfile
import urllib.request
from pathlib import Path


# ─────────────────────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────────────────────

YOLO_BASE_MODEL   = "yolov8n.pt"          # nano — smallest / fastest
DATASET_DIR       = Path("datasets/widerface")
RUNS_DIR          = Path("runs/face_detect")
EXPORT_DIR        = Path("models")
TRAIN_EPOCHS      = 30                    # increase to 100 for better accuracy
TRAIN_IMGSZ       = 320                   # 320 for Pi speed, 640 for accuracy
TRAIN_BATCH       = 16                    # reduce to 8 if OOM
TRAIN_WORKERS     = 3                     # leave 1 core for OS on Pi
CONFIDENCE_THRESH = 0.5
IOU_THRESH        = 0.45

# WIDER FACE download URLs (official mirrors)
WIDER_TRAIN_URL   = "https://huggingface.co/datasets/wider_face/resolve/main/data/WIDER_train.zip"
WIDER_VAL_URL     = "https://huggingface.co/datasets/wider_face/resolve/main/data/WIDER_val.zip"
WIDER_ANNOT_URL   = "https://huggingface.co/datasets/wider_face/resolve/main/data/wider_face_split.zip"


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def run(cmd: str, check=True):
    print(f"\n$ {cmd}")
    result = subprocess.run(cmd, shell=True)
    if check and result.returncode != 0:
        print(f"❌ Command failed: {cmd}")
        sys.exit(result.returncode)
    return result.returncode == 0


def download(url: str, dest: Path, desc: str = ""):
    if dest.exists():
        print(f"  ✅ Already downloaded: {dest.name}")
        return
    print(f"  ⬇️  Downloading {desc or dest.name} …")
    dest.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(url, dest,
        reporthook=lambda b, bs, ts: print(
            f"\r     {min(b*bs, ts)//1024//1024} / {ts//1024//1024} MB", end=""))
    print()


def unzip(src: Path, dest: Path):
    if dest.exists():
        print(f"  ✅ Already extracted: {dest}")
        return
    print(f"  📦 Extracting {src.name} …")
    with zipfile.ZipFile(src, "r") as z:
        z.extractall(dest.parent)


# ─────────────────────────────────────────────────────────────────────────────
# Step 1 — Install dependencies
# ─────────────────────────────────────────────────────────────────────────────

def install_deps():
    print("\n" + "="*60)
    print("📦 Step 1 — Installing dependencies")
    print("="*60)

    packages = [
        "ultralytics==8.1.0",
        "opencv-python==4.8.1.78",
        "numpy==1.24.3",
        "Pillow==10.1.0",
        "scipy==1.11.4",
        "mediapipe==0.10.9",
        "face-recognition==1.3.0",
    ]

    for pkg in packages:
        run(f"{sys.executable} -m pip install --quiet {pkg}")

    print("✅ Dependencies installed")


# ─────────────────────────────────────────────────────────────────────────────
# Step 2 — Download YOLOv8-nano base weights
# ─────────────────────────────────────────────────────────────────────────────

def download_base_model():
    print("\n" + "="*60)
    print("🤖 Step 2 — Downloading YOLOv8-nano base weights")
    print("="*60)

    if Path(YOLO_BASE_MODEL).exists():
        print(f"  ✅ {YOLO_BASE_MODEL} already present")
        return

    # Ultralytics auto-downloads on first use
    from ultralytics import YOLO
    model = YOLO(YOLO_BASE_MODEL)
    print(f"  ✅ Downloaded {YOLO_BASE_MODEL}")
    return model


# ─────────────────────────────────────────────────────────────────────────────
# Step 3 — Download & convert WIDER FACE dataset
# ─────────────────────────────────────────────────────────────────────────────

def download_wider_face():
    print("\n" + "="*60)
    print("📥 Step 3 — Downloading WIDER FACE dataset")
    print("="*60)

    raw = DATASET_DIR / "raw"
    raw.mkdir(parents=True, exist_ok=True)

    train_zip = raw / "WIDER_train.zip"
    val_zip   = raw / "WIDER_val.zip"
    annot_zip = raw / "wider_face_split.zip"

    download(WIDER_TRAIN_URL, train_zip, "WIDER FACE train (~1.5 GB)")
    download(WIDER_VAL_URL,   val_zip,   "WIDER FACE val (~400 MB)")
    download(WIDER_ANNOT_URL, annot_zip, "WIDER FACE annotations")

    unzip(train_zip, DATASET_DIR / "WIDER_train")
    unzip(val_zip,   DATASET_DIR / "WIDER_val")
    unzip(annot_zip, DATASET_DIR / "wider_face_split")

    print("  ✅ WIDER FACE downloaded and extracted")


def convert_wider_to_yolo():
    """
    Convert WIDER FACE annotation format → YOLO format.

    WIDER FACE annotation format:
        <image_path>
        <num_faces>
        x1 y1 w h blur expression illumination invalid occlusion pose
        ...

    YOLO format (one .txt per image):
        <class_id> <cx_norm> <cy_norm> <w_norm> <h_norm>
    """
    print("\n" + "="*60)
    print("🔄 Step 3b — Converting WIDER FACE → YOLO format")
    print("="*60)

    yolo_train_img = DATASET_DIR / "images" / "train"
    yolo_train_lbl = DATASET_DIR / "labels" / "train"
    yolo_val_img   = DATASET_DIR / "images" / "val"
    yolo_val_lbl   = DATASET_DIR / "labels" / "val"

    for d in [yolo_train_img, yolo_train_lbl, yolo_val_img, yolo_val_lbl]:
        d.mkdir(parents=True, exist_ok=True)

    splits = [
        (DATASET_DIR / "wider_face_split" / "wider_face_train_bbx_gt.txt",
         DATASET_DIR / "WIDER_train" / "images",
         yolo_train_img, yolo_train_lbl, "train"),
        (DATASET_DIR / "wider_face_split" / "wider_face_val_bbx_gt.txt",
         DATASET_DIR / "WIDER_val"   / "images",
         yolo_val_img,   yolo_val_lbl,   "val"),
    ]

    for annot_file, src_img_root, dst_img, dst_lbl, split_name in splits:
        if not annot_file.exists():
            print(f"  ⚠️  Annotation file not found: {annot_file}")
            continue

        converted = 0
        skipped   = 0

        with open(annot_file, "r") as f:
            lines = [l.strip() for l in f.readlines()]

        i = 0
        while i < len(lines):
            img_rel = lines[i]; i += 1
            if i >= len(lines): break

            num_faces = int(lines[i]); i += 1

            # Source image
            src_img = src_img_root / img_rel
            dst_img_path = dst_img / img_rel.replace("/", "_")
            dst_lbl_path = dst_lbl / (img_rel.replace("/", "_").rsplit(".", 1)[0] + ".txt")

            boxes = []
            for _ in range(max(num_faces, 1)):
                if i >= len(lines): break
                parts = lines[i].split(); i += 1
                if len(parts) < 4: continue

                x, y, w, h = int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3])

                # Skip invalid / tiny boxes
                if w < 10 or h < 10:
                    continue

                # We need image dimensions to normalise
                boxes.append((x, y, w, h))

            if not src_img.exists():
                skipped += 1
                continue

            # Copy image
            if not dst_img_path.exists():
                shutil.copy2(src_img, dst_img_path)

            # Write YOLO label (need image size)
            import cv2
            img = cv2.imread(str(src_img))
            if img is None:
                skipped += 1
                continue

            ih, iw = img.shape[:2]
            label_lines = []

            for (x, y, w, h) in boxes:
                cx = (x + w / 2) / iw
                cy = (y + h / 2) / ih
                nw = w / iw
                nh = h / ih

                # Clamp to [0, 1]
                cx = max(0.0, min(1.0, cx))
                cy = max(0.0, min(1.0, cy))
                nw = max(0.0, min(1.0, nw))
                nh = max(0.0, min(1.0, nh))

                label_lines.append(f"0 {cx:.6f} {cy:.6f} {nw:.6f} {nh:.6f}")

            if label_lines:
                with open(dst_lbl_path, "w") as lf:
                    lf.write("\n".join(label_lines))
                converted += 1

        print(f"  ✅ {split_name}: {converted} images converted, {skipped} skipped")

    # Write dataset YAML
    yaml_path = DATASET_DIR / "widerface.yaml"
    yaml_content = f"""# WIDER FACE dataset — YOLO format
path: {DATASET_DIR.resolve()}
train: images/train
val:   images/val

nc: 1
names:
  0: face
"""
    yaml_path.write_text(yaml_content)
    print(f"  ✅ Dataset YAML written: {yaml_path}")
    return yaml_path


# ─────────────────────────────────────────────────────────────────────────────
# Step 4 — Fine-tune YOLOv8-nano on WIDER FACE
# ─────────────────────────────────────────────────────────────────────────────

def fine_tune(yaml_path: Path):
    print("\n" + "="*60)
    print("🏋️  Step 4 — Fine-tuning YOLOv8-nano on WIDER FACE")
    print(f"    Epochs: {TRAIN_EPOCHS}  |  imgsz: {TRAIN_IMGSZ}  |  batch: {TRAIN_BATCH}")
    print("="*60)

    from ultralytics import YOLO

    model = YOLO(YOLO_BASE_MODEL)

    results = model.train(
        data      = str(yaml_path),
        epochs    = TRAIN_EPOCHS,
        imgsz     = TRAIN_IMGSZ,
        batch     = TRAIN_BATCH,
        workers   = TRAIN_WORKERS,
        device    = "cpu",          # CPU only — no GPU assumed
        project   = str(RUNS_DIR),
        name      = "yolov8n_face",
        exist_ok  = True,
        patience  = 10,             # early stopping
        optimizer = "AdamW",
        lr0       = 0.001,
        lrf       = 0.01,
        momentum  = 0.937,
        weight_decay = 0.0005,
        warmup_epochs = 3,
        box       = 7.5,
        cls       = 0.5,
        dfl       = 1.5,
        # Augmentation — helps generalise to surveillance angles
        hsv_h     = 0.015,
        hsv_s     = 0.7,
        hsv_v     = 0.4,
        degrees   = 10.0,
        translate = 0.1,
        scale     = 0.5,
        flipud    = 0.0,
        fliplr    = 0.5,
        mosaic    = 1.0,
        mixup     = 0.1,
        copy_paste = 0.1,
        verbose   = True,
    )

    best_weights = RUNS_DIR / "yolov8n_face" / "weights" / "best.pt"
    print(f"\n  ✅ Training complete. Best weights: {best_weights}")
    return best_weights


# ─────────────────────────────────────────────────────────────────────────────
# Step 5 — Export to ONNX + TFLite INT8
# ─────────────────────────────────────────────────────────────────────────────

def export_models(weights_path: Path):
    print("\n" + "="*60)
    print("📤 Step 5 — Exporting models")
    print("="*60)

    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    from ultralytics import YOLO
    model = YOLO(str(weights_path))

    # ── ONNX (for laptop + Pi with OpenCV DNN) ───────────────────────────────
    print("\n  Exporting ONNX (imgsz=320, opset=12) …")
    model.export(
        format   = "onnx",
        imgsz    = TRAIN_IMGSZ,
        opset    = 12,           # OpenCV DNN requires opset ≤ 12
        simplify = True,         # onnx-simplifier removes redundant ops
        dynamic  = False,        # static shape — faster on Pi
    )
    onnx_src = weights_path.parent / "best.onnx"
    onnx_dst = EXPORT_DIR / "yolov8n_face.onnx"
    if onnx_src.exists():
        shutil.copy2(onnx_src, onnx_dst)
        print(f"  ✅ ONNX saved: {onnx_dst}  ({onnx_dst.stat().st_size//1024} KB)")

    # ── TFLite INT8 (for Raspberry Pi — fastest inference) ───────────────────
    print("\n  Exporting TFLite INT8 (quantised) …")
    try:
        model.export(
            format   = "tflite",
            imgsz    = TRAIN_IMGSZ,
            int8     = True,     # INT8 quantisation — 4× faster on Pi
            data     = str(DATASET_DIR / "widerface.yaml"),  # calibration data
        )
        tflite_src = weights_path.parent / "best_int8.tflite"
        if not tflite_src.exists():
            tflite_src = weights_path.parent / "best.tflite"
        tflite_dst = EXPORT_DIR / "yolov8n_face_int8.tflite"
        if tflite_src.exists():
            shutil.copy2(tflite_src, tflite_dst)
            print(f"  ✅ TFLite INT8 saved: {tflite_dst}  ({tflite_dst.stat().st_size//1024} KB)")
    except Exception as e:
        print(f"  ⚠️  TFLite export failed: {e}")
        print("     Install tensorflow: pip install tensorflow")
        print("     Or use ONNX on the Pi — it works fine with OpenCV DNN")

    # ── Copy ONNX to project root so yolo_face_detector.py finds it ──────────
    root_onnx = Path("yolov8n-face.onnx")
    if onnx_dst.exists() and not root_onnx.exists():
        shutil.copy2(onnx_dst, root_onnx)
        print(f"\n  ✅ Copied to project root: {root_onnx}")

    root_tflite = Path("yolov8n-face.tflite")
    tflite_dst2 = EXPORT_DIR / "yolov8n_face_int8.tflite"
    if tflite_dst2.exists() and not root_tflite.exists():
        shutil.copy2(tflite_dst2, root_tflite)
        print(f"  ✅ Copied to project root: {root_tflite}")

    return onnx_dst


# ─────────────────────────────────────────────────────────────────────────────
# Step 6 — Benchmark
# ─────────────────────────────────────────────────────────────────────────────

def benchmark(weights_path: Path):
    print("\n" + "="*60)
    print("⏱️  Step 6 — Benchmarking exported models")
    print("="*60)

    import cv2
    import numpy as np
    import time

    # Create a dummy 320×320 test image
    dummy = np.random.randint(0, 255, (320, 320, 3), dtype=np.uint8)

    # ── ONNX via OpenCV DNN ───────────────────────────────────────────────────
    onnx_path = Path("yolov8n-face.onnx")
    if onnx_path.exists():
        net = cv2.dnn.readNetFromONNX(str(onnx_path))
        net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
        net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)

        blob = cv2.dnn.blobFromImage(dummy, 1/255.0, (320, 320), swapRB=True)

        # Warmup
        for _ in range(3):
            net.setInput(blob)
            net.forward()

        # Benchmark
        N = 20
        t0 = time.time()
        for _ in range(N):
            net.setInput(blob)
            net.forward()
        elapsed = (time.time() - t0) / N * 1000

        print(f"  ONNX (OpenCV DNN):  {elapsed:.1f} ms/frame  →  {1000/elapsed:.1f} FPS")
    else:
        print("  ONNX model not found — skipping ONNX benchmark")

    # ── TFLite ────────────────────────────────────────────────────────────────
    tflite_path = Path("yolov8n-face.tflite")
    if tflite_path.exists():
        try:
            import tflite_runtime.interpreter as tflite
        except ImportError:
            try:
                import tensorflow.lite as tflite
            except ImportError:
                print("  TFLite runtime not installed — skipping TFLite benchmark")
                return

        interp = tflite.Interpreter(model_path=str(tflite_path), num_threads=2)
        interp.allocate_tensors()
        inp_det = interp.get_input_details()[0]

        inp_data = (dummy.astype(np.float32) / 255.0)[np.newaxis]

        # Warmup
        for _ in range(3):
            interp.set_tensor(inp_det["index"], inp_data)
            interp.invoke()

        N = 20
        t0 = time.time()
        for _ in range(N):
            interp.set_tensor(inp_det["index"], inp_data)
            interp.invoke()
        elapsed = (time.time() - t0) / N * 1000

        print(f"  TFLite INT8:        {elapsed:.1f} ms/frame  →  {1000/elapsed:.1f} FPS")
    else:
        print("  TFLite model not found — skipping TFLite benchmark")


# ─────────────────────────────────────────────────────────────────────────────
# Step 7 — Update config.py to point at the new model
# ─────────────────────────────────────────────────────────────────────────────

def update_config():
    print("\n" + "="*60)
    print("⚙️  Step 7 — Updating config.py")
    print("="*60)

    config_path = Path("config.py")
    if not config_path.exists():
        print("  ⚠️  config.py not found — skipping")
        return

    text = config_path.read_text(encoding="utf-8")

    # Point YOLO_MODEL at the ONNX file (works on both laptop and Pi)
    if "yolov8n-face.onnx" not in text:
        text = text.replace(
            'YOLO_MODEL = "yolov8n-face.pt"',
            'YOLO_MODEL = "yolov8n-face.onnx"  # fine-tuned on WIDER FACE'
        )
        config_path.write_text(text, encoding="utf-8")
        print("  ✅ config.py updated: YOLO_MODEL → yolov8n-face.onnx")
    else:
        print("  ✅ config.py already points at ONNX model")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Download, fine-tune, and export YOLOv8-nano face detector")
    parser.add_argument("--no-train",    action="store_true",
                        help="Skip training (use base YOLOv8n weights)")
    parser.add_argument("--export-only", action="store_true",
                        help="Only export existing trained weights")
    parser.add_argument("--epochs",      type=int, default=TRAIN_EPOCHS)
    parser.add_argument("--imgsz",       type=int, default=TRAIN_IMGSZ)
    parser.add_argument("--batch",       type=int, default=TRAIN_BATCH)
    args = parser.parse_args()

    global TRAIN_EPOCHS, TRAIN_IMGSZ, TRAIN_BATCH
    TRAIN_EPOCHS = args.epochs
    TRAIN_IMGSZ  = args.imgsz
    TRAIN_BATCH  = args.batch

    print("\n" + "="*60)
    print("🚀 YOLOv8-nano Face Model — Setup & Training Pipeline")
    print("="*60)

    # Step 1 — deps
    install_deps()

    # Step 2 — base model
    download_base_model()

    if args.export_only:
        # Find existing best weights
        best = RUNS_DIR / "yolov8n_face" / "weights" / "best.pt"
        if not best.exists():
            best = Path(YOLO_BASE_MODEL)
        export_models(best)
        benchmark(best)
        update_config()
        return

    if args.no_train:
        # Export base model directly
        export_models(Path(YOLO_BASE_MODEL))
        benchmark(Path(YOLO_BASE_MODEL))
        update_config()
        return

    # Step 3 — dataset
    download_wider_face()
    yaml_path = convert_wider_to_yolo()

    # Step 4 — fine-tune
    best_weights = fine_tune(yaml_path)

    # Step 5 — export
    export_models(best_weights)

    # Step 6 — benchmark
    benchmark(best_weights)

    # Step 7 — update config
    update_config()

    print("\n" + "="*60)
    print("✅ Pipeline complete!")
    print("="*60)
    print()
    print("  Model files in project root:")
    for f in ["yolov8n-face.onnx", "yolov8n-face.tflite"]:
        p = Path(f)
        if p.exists():
            print(f"    {f}  ({p.stat().st_size // 1024} KB)")
    print()
    print("  Run the system:")
    print("    python gui_tracker.py")
    print("    python multiprocessing_core.py   (Pi — multi-core)")
    print()
    print("  On Raspberry Pi (export only, skip training):")
    print("    python setup_and_train.py --no-train")


if __name__ == "__main__":
    main()
