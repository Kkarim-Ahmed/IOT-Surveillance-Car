"""
BlazeFace Detector
Uses MediaPipe Face Detection (Tasks API — mediapipe >= 0.10)
Falls back to Haar Cascade if MediaPipe is unavailable.
"""

import cv2
import numpy as np
import urllib.request
import os
import config


# ─────────────────────────────────────────────────────────────────────────────
# BlazeFace model download helper
# ─────────────────────────────────────────────────────────────────────────────

BLAZE_MODEL_URL  = (
    "https://storage.googleapis.com/mediapipe-models/"
    "face_detector/blaze_face_short_range/float16/1/"
    "blaze_face_short_range.tflite"
)
BLAZE_MODEL_PATH = "blaze_face_short_range.tflite"


def _download_blaze_model():
    """Download the BlazeFace TFLite model if not already present."""
    if os.path.exists(BLAZE_MODEL_PATH):
        return True
    print(f"  ⬇️  Downloading BlazeFace model from Google…")
    try:
        urllib.request.urlretrieve(BLAZE_MODEL_URL, BLAZE_MODEL_PATH)
        size_kb = os.path.getsize(BLAZE_MODEL_PATH) // 1024
        print(f"  ✅ BlazeFace model saved: {BLAZE_MODEL_PATH}  ({size_kb} KB)")
        return True
    except Exception as e:
        print(f"  ⚠️  BlazeFace download failed: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Main detector class
# ─────────────────────────────────────────────────────────────────────────────

class BlazeFaceDetector:
    """
    Ultra-fast face detector using MediaPipe BlazeFace.

    MediaPipe >= 0.10 uses the Tasks API (mediapipe.tasks).
    Falls back to Haar Cascade if MediaPipe is unavailable.
    """

    def __init__(self):
        self._detector   = None
        self._use_tasks  = False   # new Tasks API
        self._use_legacy = False   # old solutions API (mp < 0.10)
        self._use_haar   = False   # OpenCV fallback

        self._init_detector()

    # ── initialisation ────────────────────────────────────────────────────────

    def _init_detector(self):
        """Try Tasks API → legacy solutions → Haar Cascade."""

        # ── 1. MediaPipe Tasks API (>= 0.10) ─────────────────────────────────
        try:
            import mediapipe as mp
            from mediapipe.tasks import python as mp_python
            from mediapipe.tasks.python import vision as mp_vision

            # Download model if needed
            if not _download_blaze_model():
                raise RuntimeError("BlazeFace model download failed")

            base_options = mp_python.BaseOptions(
                model_asset_path=BLAZE_MODEL_PATH
            )
            options = mp_vision.FaceDetectorOptions(
                base_options=base_options,
                min_detection_confidence=config.YOLO_CONFIDENCE,
            )
            self._detector  = mp_vision.FaceDetector.create_from_options(options)
            self._use_tasks = True
            print("✅ BlazeFace ready (MediaPipe Tasks API)")
            return

        except Exception as e:
            print(f"  ⚠️  MediaPipe Tasks API failed: {e}")

        # ── 2. Legacy MediaPipe solutions API (< 0.10) ────────────────────────
        try:
            import mediapipe as mp
            mp_face = mp.solutions.face_detection          # type: ignore
            self._detector   = mp_face.FaceDetection(
                model_selection=0,
                min_detection_confidence=config.YOLO_CONFIDENCE,
            )
            self._use_legacy = True
            print("✅ BlazeFace ready (MediaPipe legacy API)")
            return

        except Exception as e:
            print(f"  ⚠️  MediaPipe legacy API failed: {e}")

        # ── 3. Haar Cascade fallback ──────────────────────────────────────────
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        self._detector = cv2.CascadeClassifier(cascade_path)
        self._use_haar = True
        print("✅ BlazeFace fallback: Haar Cascade (OpenCV)")

    # ── public API ────────────────────────────────────────────────────────────

    def detect_faces(self, frame: np.ndarray):
        """
        Detect faces in a BGR frame.

        Returns:
            List of (top, right, bottom, left) in pixels —
            same format as face_recognition library.
        """
        if self._use_tasks:
            return self._detect_tasks(frame)
        elif self._use_legacy:
            return self._detect_legacy(frame)
        else:
            return self._detect_haar(frame)

    def detect_and_draw(self, frame: np.ndarray):
        locs = self.detect_faces(frame)
        out  = frame.copy()
        for (top, right, bottom, left) in locs:
            cv2.rectangle(out, (left, top), (right, bottom), (0, 255, 0), 2)
        return out, locs

    # ── backends ──────────────────────────────────────────────────────────────

    def _detect_tasks(self, frame: np.ndarray):
        """MediaPipe Tasks API (mediapipe >= 0.10)."""
        import mediapipe as mp

        h, w = frame.shape[:2]
        rgb  = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

        result = self._detector.detect(mp_image)

        locs = []
        if result.detections:
            for det in result.detections:
                bb = det.bounding_box
                left   = max(0, bb.origin_x)
                top    = max(0, bb.origin_y)
                right  = min(w, bb.origin_x + bb.width)
                bottom = min(h, bb.origin_y + bb.height)

                if (right - left) >= config.MIN_FACE_SIZE and \
                   (bottom - top) >= config.MIN_FACE_SIZE:
                    locs.append((top, right, bottom, left))
        return locs

    def _detect_legacy(self, frame: np.ndarray):
        """MediaPipe legacy solutions API (mediapipe < 0.10)."""
        h, w = frame.shape[:2]
        rgb  = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        res  = self._detector.process(rgb)

        locs = []
        if res.detections:
            for det in res.detections:
                bb     = det.location_data.relative_bounding_box
                left   = max(0, int(bb.xmin * w))
                top    = max(0, int(bb.ymin * h))
                right  = min(w, int((bb.xmin + bb.width)  * w))
                bottom = min(h, int((bb.ymin + bb.height) * h))

                if (right - left) >= config.MIN_FACE_SIZE and \
                   (bottom - top) >= config.MIN_FACE_SIZE:
                    locs.append((top, right, bottom, left))
        return locs

    def _detect_haar(self, frame: np.ndarray):
        """OpenCV Haar Cascade fallback."""
        gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self._detector.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5,
            minSize=(config.MIN_FACE_SIZE, config.MIN_FACE_SIZE)
        )
        locs = []
        if len(faces):
            for (x, y, fw, fh) in faces:
                locs.append((y, x + fw, y + fh, x))
        return locs

    def __del__(self):
        if self._use_tasks and self._detector:
            try:
                self._detector.close()
            except Exception:
                pass
