"""
Face detector — MediaPipe BlazeFace TFLite (tiny model, built into mediapipe).

MediaPipe uses a TFLite BlazeFace model internally; no separate model file
is needed. This is the "tiny model" for detection: ~0.5 MB quantized,
~10-15 FPS at 320×240 on bare RPi4.

Returns detections as dicts:
    {"bbox": (x1,y1,x2,y2), "score": float, "keypoints": [(x,y)×6]}
    keypoints order: right_eye, left_eye, nose, mouth, right_ear, left_ear
"""

import sys
import logging
from typing import List, Dict, Any, Tuple

import cv2
import numpy as np

sys.path.insert(0, "..")
import config

log = logging.getLogger(__name__)
Detection = Dict[str, Any]


class FaceDetector:
    """MediaPipe BlazeFace — TFLite backed, fast and accurate."""

    def __init__(self):
        self._detector = None
        self._backend  = "none"
        self._init()

    def _init(self) -> None:
        # ── Primary: MediaPipe (TFLite internally) ────────────────────────────
        try:
            import mediapipe as mp
            self._mp_fd = mp.solutions.face_detection.FaceDetection(
                model_selection=1,                         # 1 = full-range up to 5 m
                min_detection_confidence=config.DETECT_CONFIDENCE,
            )
            self._backend = "mediapipe-tflite"
            log.info("Detector: MediaPipe BlazeFace TFLite (full-range, up to 5 m)")
            return
        except Exception as e:
            log.warning("MediaPipe unavailable: %s", e)

        # ── Fallback: OpenCV Haar cascade ─────────────────────────────────────
        try:
            path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            cc = cv2.CascadeClassifier(path)
            if not cc.empty():
                self._haar = cc
                self._backend = "haar"
                log.info("Detector: Haar cascade (fallback)")
                return
        except Exception as e:
            log.warning("Haar unavailable: %s", e)

        log.error("No face detector available!")

    # ── Public ────────────────────────────────────────────────────────────────

    def detect(self, frame: np.ndarray) -> List[Detection]:
        """Detect faces in a BGR frame. Returns list sorted by score desc."""
        if self._backend == "mediapipe-tflite":
            return self._detect_mp(frame)
        if self._backend == "haar":
            return self._detect_haar(frame)
        return []

    @property
    def backend(self) -> str:
        return self._backend

    # ── Backends ──────────────────────────────────────────────────────────────

    def _detect_mp(self, frame: np.ndarray) -> List[Detection]:
        import mediapipe as mp
        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        res = self._mp_fd.process(rgb)

        out: List[Detection] = []
        if not res.detections:
            return out

        for det in res.detections:
            score = det.score[0]
            if score < config.DETECT_CONFIDENCE:
                continue
            bb = det.location_data.relative_bounding_box
            x1 = max(0, int(bb.xmin * w))
            y1 = max(0, int(bb.ymin * h))
            x2 = min(w, int((bb.xmin + bb.width)  * w))
            y2 = min(h, int((bb.ymin + bb.height) * h))
            if x2 <= x1 or y2 <= y1:
                continue

            # Extract 6 keypoints for face alignment
            kps: List[Tuple[float, float]] = []
            for kp in det.location_data.relative_keypoints:
                kps.append((kp.x * w, kp.y * h))

            out.append({"bbox": (x1, y1, x2, y2), "score": float(score), "keypoints": kps})

        return sorted(out, key=lambda d: d["score"], reverse=True)[:10]

    def _detect_haar(self, frame: np.ndarray) -> List[Detection]:
        gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self._haar.detectMultiScale(gray, 1.1, 5, minSize=(30, 30))
        out: List[Detection] = []
        if len(faces) == 0:
            return out
        for x, y, fw, fh in faces:
            out.append({
                "bbox": (x, y, x+fw, y+fh),
                "score": 0.8,
                "keypoints": [],
            })
        return out


# ── Face alignment helper (used by recognizer) ────────────────────────────────

def align_face(frame: np.ndarray, detection: Detection, size: int = 112) -> np.ndarray:
    """
    Align and crop a detected face to `size` × `size` for embedding.
    Uses eye keypoints when available for rotation correction.
    Falls back to simple bbox crop.
    """
    x1, y1, x2, y2 = detection["bbox"]
    kps = detection.get("keypoints", [])

    # Eye keypoints: index 0=right_eye, 1=left_eye (from camera's perspective)
    if len(kps) >= 2:
        re = kps[0]   # right eye
        le = kps[1]   # left eye
        dx = le[0] - re[0]
        dy = le[1] - re[1]
        angle = float(np.degrees(np.arctan2(dy, dx)))

        eye_cx = (re[0] + le[0]) / 2
        eye_cy = (re[1] + le[1]) / 2

        # Rotate around midpoint between eyes
        M = cv2.getRotationMatrix2D((eye_cx, eye_cy), angle, 1.0)
        h, w = frame.shape[:2]
        rotated = cv2.warpAffine(frame, M, (w, h), flags=cv2.INTER_LINEAR)

        # Transform bbox corners to find new crop region
        corners = np.array([[x1, y1], [x2, y1], [x2, y2], [x1, y2]], dtype=np.float32)
        ones = np.ones((4, 1), dtype=np.float32)
        corners_h = np.hstack([corners, ones])
        rotated_corners = (M @ corners_h.T).T
        rx1 = int(max(0, rotated_corners[:, 0].min()))
        ry1 = int(max(0, rotated_corners[:, 1].min()))
        rx2 = int(min(w,  rotated_corners[:, 0].max()))
        ry2 = int(min(h,  rotated_corners[:, 1].max()))

        if rx2 > rx1 and ry2 > ry1:
            crop = rotated[ry1:ry2, rx1:rx2]
            return cv2.resize(crop, (size, size))

    # Simple crop fallback
    pad = max(0, int((y2 - y1) * 0.1))
    h, w = frame.shape[:2]
    y1c = max(0, y1 - pad)
    y2c = min(h, y2 + pad)
    x1c = max(0, x1 - pad)
    x2c = min(w, x2 + pad)
    crop = frame[y1c:y2c, x1c:x2c]
    if crop.size == 0:
        return np.zeros((size, size, 3), dtype=np.uint8)
    return cv2.resize(crop, (size, size))
