"""
optimize_for_pi.py
==================
Post-training optimisation pipeline for Raspberry Pi 4.

Takes the fine-tuned ONNX model and produces:
  1. ONNX with graph optimisations (onnxruntime / onnx-simplifier)
  2. TFLite FP16  — half-precision, ~2× faster than FP32
  3. TFLite INT8  — 8-bit quantised, ~4× faster than FP32, smallest size
  4. OpenCV DNN benchmark on all three

Usage:
    python optimize_for_pi.py                        # optimise yolov8n-face.onnx
    python optimize_for_pi.py --model my_model.onnx  # custom model
    python optimize_for_pi.py --benchmark-only       # just benchmark existing files
"""

import argparse
import sys
import time
import shutil
import subprocess
from pathlib import Path

import numpy as np


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def pip_install(pkg: str):
    subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", pkg],
                   check=True)


def section(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


# ─────────────────────────────────────────────────────────────────────────────
# 1. Simplify ONNX graph
# ─────────────────────────────────────────────────────────────────────────────

def simplify_onnx(src: Path) -> Path:
    section("Simplifying ONNX graph")

    dst = src.parent / (src.stem + "_simplified.onnx")
    if dst.exists():
        print(f"  ✅ Already simplified: {dst}")
        return dst

    try:
        pip_install("onnx onnxsim")
        import onnx
        from onnxsim import simplify

        model = onnx.load(str(src))
        model_simplified, ok = simplify(model)

        if ok:
            onnx.save(model_simplified, str(dst))
            orig_kb = src.stat().st_size  // 1024
            simp_kb = dst.stat().st_size  // 1024
            print(f"  ✅ Simplified: {orig_kb} KB → {simp_kb} KB  ({dst})")
        else:
            print("  ⚠️  Simplification failed — using original")
            shutil.copy2(src, dst)

    except Exception as e:
        print(f"  ⚠️  onnxsim not available: {e}")
        print("       Using original ONNX")
        shutil.copy2(src, dst)

    return dst


# ─────────────────────────────────────────────────────────────────────────────
# 2. Convert ONNX → TFLite FP16 + INT8
# ─────────────────────────────────────────────────────────────────────────────

def onnx_to_tflite(onnx_path: Path, imgsz: int = 320):
    section("Converting ONNX → TFLite (FP16 + INT8)")

    fp16_path = onnx_path.parent / (onnx_path.stem + "_fp16.tflite")
    int8_path = onnx_path.parent / (onnx_path.stem + "_int8.tflite")

    try:
        pip_install("tensorflow onnx-tf")
        import tensorflow as tf
        import onnx
        from onnx_tf.backend import prepare

        print("  Converting ONNX → TF SavedModel …")
        onnx_model  = onnx.load(str(onnx_path))
        tf_rep      = prepare(onnx_model)
        saved_model = onnx_path.parent / "tf_saved_model"
        tf_rep.export_graph(str(saved_model))

        # ── FP16 ─────────────────────────────────────────────────────────────
        if not fp16_path.exists():
            print("  Converting → TFLite FP16 …")
            converter = tf.lite.TFLiteConverter.from_saved_model(str(saved_model))
            converter.optimizations = [tf.lite.Optimize.DEFAULT]
            converter.target_spec.supported_types = [tf.float16]
            tflite_model = converter.convert()
            fp16_path.write_bytes(tflite_model)
            print(f"  ✅ FP16: {fp16_path.stat().st_size // 1024} KB  →  {fp16_path}")

        # ── INT8 (representative dataset for calibration) ─────────────────────
        if not int8_path.exists():
            print("  Converting → TFLite INT8 (quantised) …")

            def representative_dataset():
                for _ in range(100):
                    data = np.random.rand(1, imgsz, imgsz, 3).astype(np.float32)
                    yield [data]

            converter = tf.lite.TFLiteConverter.from_saved_model(str(saved_model))
            converter.optimizations = [tf.lite.Optimize.DEFAULT]
            converter.representative_dataset = representative_dataset
            converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
            converter.inference_input_type  = tf.uint8
            converter.inference_output_type = tf.uint8
            tflite_model = converter.convert()
            int8_path.write_bytes(tflite_model)
            print(f"  ✅ INT8: {int8_path.stat().st_size // 1024} KB  →  {int8_path}")

    except ImportError as e:
        print(f"  ⚠️  TensorFlow not available: {e}")
        print("       Install with: pip install tensorflow onnx-tf")
        print("       Skipping TFLite conversion")
        return None, None
    except Exception as e:
        print(f"  ⚠️  Conversion error: {e}")
        return None, None

    return fp16_path, int8_path


# ─────────────────────────────────────────────────────────────────────────────
# 3. Benchmark all models
# ─────────────────────────────────────────────────────────────────────────────

def benchmark_all(onnx_path: Path, fp16_path: Path, int8_path: Path,
                  imgsz: int = 320, n_runs: int = 30):
    section("Benchmarking on this machine")

    import cv2

    dummy_bgr  = np.random.randint(0, 255, (imgsz, imgsz, 3), dtype=np.uint8)
    dummy_fp32 = (dummy_bgr.astype(np.float32) / 255.0)[np.newaxis]  # (1,H,W,3)

    results = {}

    # ── ONNX via OpenCV DNN ───────────────────────────────────────────────────
    if onnx_path and onnx_path.exists():
        try:
            net = cv2.dnn.readNetFromONNX(str(onnx_path))
            net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
            net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
            blob = cv2.dnn.blobFromImage(dummy_bgr, 1/255.0,
                                          (imgsz, imgsz), swapRB=True)
            # warmup
            for _ in range(5):
                net.setInput(blob); net.forward()

            t0 = time.perf_counter()
            for _ in range(n_runs):
                net.setInput(blob); net.forward()
            ms = (time.perf_counter() - t0) / n_runs * 1000
            results["ONNX (OpenCV DNN)"] = ms
        except Exception as e:
            print(f"  ⚠️  ONNX benchmark failed: {e}")

    # ── TFLite FP16 ───────────────────────────────────────────────────────────
    for label, path in [("TFLite FP16", fp16_path), ("TFLite INT8", int8_path)]:
        if path and path.exists():
            try:
                try:
                    import tflite_runtime.interpreter as tflite
                except ImportError:
                    import tensorflow.lite as tflite

                interp = tflite.Interpreter(model_path=str(path), num_threads=3)
                interp.allocate_tensors()
                inp_det = interp.get_input_details()[0]
                inp_dtype = inp_det["dtype"]

                if inp_dtype == np.uint8:
                    inp_data = dummy_bgr[np.newaxis]          # uint8
                else:
                    inp_data = dummy_fp32                     # float32

                # warmup
                for _ in range(5):
                    interp.set_tensor(inp_det["index"], inp_data)
                    interp.invoke()

                t0 = time.perf_counter()
                for _ in range(n_runs):
                    interp.set_tensor(inp_det["index"], inp_data)
                    interp.invoke()
                ms = (time.perf_counter() - t0) / n_runs * 1000
                results[label] = ms

            except Exception as e:
                print(f"  ⚠️  {label} benchmark failed: {e}")

    # ── Print table ───────────────────────────────────────────────────────────
    print()
    print(f"  {'Model':<25}  {'ms/frame':>10}  {'FPS':>8}  {'vs ONNX':>10}")
    print(f"  {'-'*25}  {'-'*10}  {'-'*8}  {'-'*10}")

    baseline = results.get("ONNX (OpenCV DNN)", None)

    for name, ms in results.items():
        fps     = 1000 / ms
        speedup = f"{baseline/ms:.2f}×" if baseline and name != "ONNX (OpenCV DNN)" else "baseline"
        print(f"  {name:<25}  {ms:>10.1f}  {fps:>8.1f}  {speedup:>10}")

    print()

    # Pi 4 estimate (roughly 3-5× slower than a modern laptop)
    print("  Estimated Raspberry Pi 4 performance (÷4 approximation):")
    for name, ms in results.items():
        pi_ms  = ms * 4
        pi_fps = 1000 / pi_ms
        print(f"    {name:<25}  ~{pi_ms:.0f} ms  →  ~{pi_fps:.1f} FPS")

    return results


# ─────────────────────────────────────────────────────────────────────────────
# 4. Copy best model to project root
# ─────────────────────────────────────────────────────────────────────────────

def deploy_best(onnx_path: Path, fp16_path: Path, int8_path: Path,
                results: dict):
    section("Deploying best model to project root")

    # Pick fastest
    if results:
        best_name = min(results, key=results.get)
        print(f"  Fastest model: {best_name}  ({results[best_name]:.1f} ms)")
    else:
        best_name = "ONNX (OpenCV DNN)"

    # Always deploy ONNX (most compatible)
    if onnx_path and onnx_path.exists():
        dst = Path("yolov8n-face.onnx")
        shutil.copy2(onnx_path, dst)
        print(f"  ✅ Deployed ONNX → {dst}  ({dst.stat().st_size//1024} KB)")

    # Deploy INT8 TFLite if available
    if int8_path and int8_path.exists():
        dst = Path("yolov8n-face_int8.tflite")
        shutil.copy2(int8_path, dst)
        print(f"  ✅ Deployed TFLite INT8 → {dst}  ({dst.stat().st_size//1024} KB)")

    # Deploy FP16 TFLite if available
    if fp16_path and fp16_path.exists():
        dst = Path("yolov8n-face_fp16.tflite")
        shutil.copy2(fp16_path, dst)
        print(f"  ✅ Deployed TFLite FP16 → {dst}  ({dst.stat().st_size//1024} KB)")

    # Update config.py to use ONNX
    config_path = Path("config.py")
    if config_path.exists():
        text = config_path.read_text(encoding="utf-8")
        if "yolov8n-face.onnx" not in text:
            text = text.replace(
                'YOLO_MODEL = "yolov8n-face.pt"',
                'YOLO_MODEL = "yolov8n-face.onnx"  # optimised fine-tuned model'
            )
            config_path.write_text(text, encoding="utf-8")
            print("  ✅ config.py updated: YOLO_MODEL → yolov8n-face.onnx")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Optimise YOLOv8-nano face model for Raspberry Pi")
    parser.add_argument("--model",          default="yolov8n-face.onnx",
                        help="Path to ONNX model (default: yolov8n-face.onnx)")
    parser.add_argument("--imgsz",          type=int, default=320)
    parser.add_argument("--benchmark-only", action="store_true",
                        help="Skip conversion, only benchmark existing files")
    args = parser.parse_args()

    onnx_src = Path(args.model)

    if not onnx_src.exists():
        print(f"❌ Model not found: {onnx_src}")
        print("   Run setup_and_train.py first to download and train the model.")
        sys.exit(1)

    print("\n" + "="*60)
    print("🔧 YOLOv8-nano — Raspberry Pi Optimisation Pipeline")
    print("="*60)
    print(f"  Input model : {onnx_src}  ({onnx_src.stat().st_size//1024} KB)")
    print(f"  Image size  : {args.imgsz}×{args.imgsz}")

    if args.benchmark_only:
        fp16 = onnx_src.parent / (onnx_src.stem + "_fp16.tflite")
        int8 = onnx_src.parent / (onnx_src.stem + "_int8.tflite")
        results = benchmark_all(onnx_src, fp16, int8, args.imgsz)
        return

    # Step 1 — simplify ONNX
    simplified = simplify_onnx(onnx_src)

    # Step 2 — convert to TFLite
    fp16_path, int8_path = onnx_to_tflite(simplified, args.imgsz)

    # Step 3 — benchmark
    results = benchmark_all(simplified, fp16_path, int8_path, args.imgsz)

    # Step 4 — deploy
    deploy_best(simplified, fp16_path, int8_path, results)

    print("\n" + "="*60)
    print("✅ Optimisation complete!")
    print("="*60)
    print()
    print("  Files ready for Raspberry Pi:")
    for f in Path(".").glob("yolov8n-face*"):
        print(f"    {f.name:<40} {f.stat().st_size//1024:>6} KB")
    print()
    print("  Run the system:")
    print("    python gui_tracker.py")
    print("    python multiprocessing_core.py")


if __name__ == "__main__":
    main()
