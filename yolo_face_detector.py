"""
YOLOv8-nano Face Detector
Supports both ONNX and TFLite backends for Raspberry Pi.
Falls back to HOG (dlib) if YOLO is unavailable.
"""

import cv2
import numpy as np
import os
import config


# ─────────────────────────────────────────────────────────────────────────────
# YOLOv8-nano via Ultralytics (ONNX / PyTorch)
# ─────────────────────────────────────────────────────────────────────────────

class YOLOFaceDetector:
    """
    YOLOv8-nano face detector.
    On Raspberry Pi use the ONNX export for best speed:
        yolo export model=yolov8n-face.pt format=onnx imgsz=320
    """

    def __init__(self, model_path: str = None, confidence: float = None):
        self.confidence = confidence or config.YOLO_CONFIDENCE
        self.model_path = model_path or config.YOLO_MODEL
        self.model      = None
        self.backend    = None

        self._load_model()

    # ── model loading ────────────────────────────────────────────────────────

    def _load_model(self):
        """Try ONNX → TFLite → Ultralytics PyTorch in that order."""

        # 1. ONNX (fastest on Pi with OpenCV DNN)
        onnx_path = self.model_path.replace(".pt", ".onnx")
        if os.path.exists(onnx_path):
            try:
                self.model   = cv2.dnn.readNetFromONNX(onnx_path)
                self.backend = "onnx"
                # Use OpenCV's optimised backend
                self.model.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
                self.model.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
                print(f"✅ YOLOv8-nano loaded (ONNX): {onnx_path}")
                return
            except Exception as e:
                print(f"⚠️  ONNX load failed: {e}")

        # 2. TFLite
        tflite_path = self.model_path.replace(".pt", ".tflite")
        if os.path.exists(tflite_path):
            try:
                import tflite_runtime.interpreter as tflite
                self.model   = tflite.Interpreter(model_path=tflite_path,
                                                   num_threads=2)
                self.model.allocate_tensors()
                self.backend = "tflite"
                self._tflite_input  = self.model.get_input_details()
                self._tflite_output = self.model.get_output_details()
                print(f"✅ YOLOv8-nano loaded (TFLite): {tflite_path}")
                return
            except Exception as e:
                print(f"⚠️  TFLite load failed: {e}")

        # 3. Ultralytics PyTorch (auto-downloads yolov8n.pt if needed)
        try:
            from ultralytics import YOLO
            self.model   = YOLO(self.model_path)
            self.model.to("cpu")
            self.backend = "ultralytics"
            print(f"✅ YOLOv8-nano loaded (Ultralytics): {self.model_path}")
        except Exception as e:
            print(f"⚠️  Ultralytics load failed: {e}")
            self.model   = None
            self.backend = None
            print("   YOLO unavailable — use BlazeFaceDetector instead")

    # ── public API ───────────────────────────────────────────────────────────

    def detect_faces(self, frame: np.ndarray):
        """
        Detect faces in a BGR frame.

        Returns:
            List of (top, right, bottom, left) tuples — same format as
            face_recognition library.
        """
        if self.model is None:
            return []

        if self.backend == "onnx":
            return self._detect_onnx(frame)
        elif self.backend == "tflite":
            return self._detect_tflite(frame)
        elif self.backend == "ultralytics":
            return self._detect_ultralytics(frame)
        return []

    def detect_and_draw(self, frame: np.ndarray):
        locs = self.detect_faces(frame)
        out  = frame.copy()
        for (top, right, bottom, left) in locs:
            cv2.rectangle(out, (left, top), (right, bottom), (0, 255, 0), 2)
        return out, locs

    # ── backends ─────────────────────────────────────────────────────────────

    def _detect_ultralytics(self, frame):
        results = self.model(frame,
                             conf=self.confidence,
                             iou=config.YOLO_IOU,
                             verbose=False)
        locs = []
        for r in results:
            for box in r.boxes:
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
                if (x2 - x1) >= config.MIN_FACE_SIZE and (y2 - y1) >= config.MIN_FACE_SIZE:
                    locs.append((y1, x2, y2, x1))
        return locs

    def _detect_onnx(self, frame):
        """
        Run YOLOv8-nano ONNX via OpenCV DNN.
        Input: 640×640 (or 320×320 for speed) normalised float32 blob.
        Output: [1, 5+nc, 8400] — x,y,w,h,conf,[cls…]
        """
        h, w = frame.shape[:2]
        input_size = 320  # Use 320 for speed on Pi

        blob = cv2.dnn.blobFromImage(frame,
                                     scalefactor=1 / 255.0,
                                     size=(input_size, input_size),
                                     swapRB=True,
                                     crop=False)
        self.model.setInput(blob)
        outputs = self.model.forward()          # shape: (1, 5, 8400) or (1, 84, 8400)

        # Transpose to (8400, 5+nc)
        preds = outputs[0].T                    # (8400, 5)

        locs = []
        for pred in preds:
            conf = float(pred[4])
            if conf < self.confidence:
                continue

            # cx, cy, bw, bh  (normalised 0-1)
            cx_n, cy_n, bw_n, bh_n = pred[:4]

            # Scale to pixel coords
            cx  = cx_n * w / input_size * input_size   # already normalised
            cy  = cy_n * h / input_size * input_size
            bw  = bw_n * w / input_size * input_size
            bh  = bh_n * h / input_size * input_size

            # Correct: normalised → pixel
            cx  = int(cx_n * w)
            cy  = int(cy_n * h)
            bw  = int(bw_n * w)
            bh  = int(bh_n * h)

            left   = max(0, cx - bw // 2)
            top    = max(0, cy - bh // 2)
            right  = min(w, cx + bw // 2)
            bottom = min(h, cy + bh // 2)

            if (right - left) >= config.MIN_FACE_SIZE and (bottom - top) >= config.MIN_FACE_SIZE:
                locs.append((top, right, bottom, left))

        return locs

    def _detect_tflite(self, frame):
        """Run YOLOv8-nano TFLite model."""
        input_detail  = self._tflite_input[0]
        output_detail = self._tflite_output[0]

        input_shape = input_detail["shape"]   # [1, H, W, 3]
        ih, iw      = input_shape[1], input_shape[2]
        h, w        = frame.shape[:2]

        resized = cv2.resize(frame, (iw, ih))
        rgb     = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        inp     = (rgb.astype(np.float32) / 255.0)[np.newaxis]  # (1,H,W,3)

        self.model.set_tensor(input_detail["index"], inp)
        self.model.invoke()
        output = self.model.get_tensor(output_detail["index"])   # (1, 5, N)

        preds = output[0].T   # (N, 5)
        locs  = []

        for pred in preds:
            conf = float(pred[4])
            if conf < self.confidence:
                continue

            cx_n, cy_n, bw_n, bh_n = pred[:4]
            cx   = int(cx_n * w)
            cy   = int(cy_n * h)
            bw   = int(bw_n * w)
            bh   = int(bh_n * h)

            left   = max(0, cx - bw // 2)
            top    = max(0, cy - bh // 2)
            right  = min(w, cx + bw // 2)
            bottom = min(h, cy + bh // 2)

            if (right - left) >= config.MIN_FACE_SIZE and (bottom - top) >= config.MIN_FACE_SIZE:
                locs.append((top, right, bottom, left))

        return locs


# ─────────────────────────────────────────────────────────────────────────────
# HOG fallback (dlib / face_recognition)
# ─────────────────────────────────────────────────────────────────────────────

class HOGFaceDetector:
    """
    HOG-based face detector using dlib (built into face_recognition).
    Slowest option but zero extra dependencies.
    """

    def __init__(self):
        print("✅ HOG face detector ready (dlib)")

    def detect_faces(self, frame: np.ndarray):
        import face_recognition
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        locs = face_recognition.face_locations(rgb, model=config.FACE_RECOGNITION_MODEL)
        return [
            (top, right, bottom, left)
            for (top, right, bottom, left) in locs
            if (right - left) >= config.MIN_FACE_SIZE
        ]

    def detect_and_draw(self, frame: np.ndarray):
        locs = self.detect_faces(frame)
        out  = frame.copy()
        for (top, right, bottom, left) in locs:
            cv2.rectangle(out, (left, top), (right, bottom), (0, 255, 0), 2)
        return out, locs
