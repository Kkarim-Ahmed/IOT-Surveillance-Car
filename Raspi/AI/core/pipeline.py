"""
AI pipeline thread.

Reads frames from Camera.queue, runs detection → recognition → tracking,
then annotates and puts result dicts into result_queue for the GUI.

result dict:
    {
      "frame":   np.ndarray (annotated 640×480 BGR),
      "tracks":  List[dict] — snapshot of active tracks,
      "mode":    "DETECT" | "TRACK",
      "ai_fps":  float,
    }
"""

import sys
import time
import queue
import threading
import logging

import cv2
import numpy as np

sys.path.insert(0, "..")
import config
from core.camera     import Camera
from core.detector   import FaceDetector
from core.recognizer import FaceRecognizer
from core.tracker    import Tracker

log = logging.getLogger(__name__)

# Servo support (optional)
_servo_ok = False
try:
    from adafruit_servokit import ServoKit as _ServoKit
    _servo_ok = True
except ImportError:
    pass


class Pipeline:
    """
    Runs as a single background thread.
    """

    def __init__(self, camera: Camera, result_queue: queue.Queue):
        self._cam       = camera
        self._result_q  = result_queue
        self._detector  = FaceDetector()
        self._recognizer= FaceRecognizer()
        self._tracker   = Tracker()
        self._mode      = "DETECT"   # "DETECT" or "TRACK"
        self._stop      = threading.Event()
        self._thread: threading.Thread | None = None
        self._ai_fps    = 0.0
        self._frame_n   = 0
        self._last_names: list = []

        # Servo (optional)
        self._kit = None
        self._pan  = float(config.PAN_CENTER)
        self._tilt = float(config.TILT_CENTER)
        self._pan_integral  = 0.0
        self._tilt_integral = 0.0
        if config.ENABLE_SERVO and _servo_ok:
            try:
                self._kit = _ServoKit(channels=16)
                log.info("Servo kit initialised")
            except Exception as e:
                log.warning("Servo init failed: %s", e)

        log.info("Pipeline ready — detector: %s | recognizer: %s | persons: %d",
                 self._detector.backend,
                 self._recognizer.backend_name,
                 self._recognizer.person_count())

    # ── Public ────────────────────────────────────────────────────────────────

    def start(self) -> None:
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="pipeline")
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)

    def set_mode(self, mode: str) -> None:
        self._mode = mode.upper()
        log.info("Mode → %s", self._mode)

    def reload_recognizer(self) -> None:
        self._recognizer.reload()

    def enroll(self, face_bgr: np.ndarray, name: str) -> bool:
        return self._recognizer.enroll_face(face_bgr, name)

    def save_encodings(self) -> None:
        self._recognizer.save_encodings()

    def delete_person(self, name: str) -> bool:
        return self._recognizer.delete_person(name)

    @property
    def ai_fps(self) -> float:
        return self._ai_fps

    @property
    def recognizer(self) -> FaceRecognizer:
        return self._recognizer

    @property
    def mode(self) -> str:
        return self._mode

    # ── Main loop ─────────────────────────────────────────────────────────────

    def _run(self) -> None:
        t0, n = time.perf_counter(), 0

        while not self._stop.is_set():
            try:
                frame = self._cam.queue.get(timeout=0.5)
            except queue.Empty:
                continue

            self._frame_n += 1
            result = self._process(frame)

            # Push to GUI queue (drop oldest if full)
            try:
                self._result_q.put_nowait(result)
            except queue.Full:
                try:
                    self._result_q.get_nowait()
                except queue.Empty:
                    pass
                self._result_q.put_nowait(result)

            n += 1
            elapsed = time.perf_counter() - t0
            if elapsed >= 1.0:
                self._ai_fps = n / elapsed
                n, t0 = 0, time.perf_counter()

    # ── Per-frame processing ──────────────────────────────────────────────────

    def _process(self, frame: np.ndarray) -> dict:
        # Downscale for AI
        small = cv2.resize(frame, (config.AI_W, config.AI_H))
        sx = config.FRAME_W / config.AI_W
        sy = config.FRAME_H / config.AI_H

        # Detect
        raw_dets = self._detector.detect(small)

        # Scale to full resolution
        dets = []
        for d in raw_dets:
            x1, y1, x2, y2 = d["bbox"]
            scaled_kps = [(kx*sx, ky*sy) for kx, ky in d.get("keypoints", [])]
            dets.append({
                "bbox":      (int(x1*sx), int(y1*sy), int(x2*sx), int(y2*sy)),
                "score":     d["score"],
                "keypoints": scaled_kps,
            })

        # Recognition (every N frames, detect mode only)
        names = None
        if self._mode == "DETECT" and self._frame_n % config.RECOG_EVERY_N == 0 and dets:
            pairs = self._recognizer.identify_detections(frame, dets)
            self._last_names = pairs
            names = pairs
        elif self._mode == "DETECT":
            names = self._last_names if self._last_names else None

        # Kalman tracking
        tracks = self._tracker.update(dets, names)

        # Motor (track mode)
        if self._mode == "TRACK":
            primary = self._tracker.primary
            if primary:
                cx, cy = primary.center()
                self._servo_step(cx, cy)

        # Annotate
        annotated = self._annotate(frame.copy(), tracks)

        return {
            "frame":   annotated,
            "tracks":  [{"id": t.id, "name": t.name, "confidence": t.confidence, "bbox": t.bbox()} for t in tracks],
            "mode":    self._mode,
            "ai_fps":  self._ai_fps,
        }

    # ── Annotation ────────────────────────────────────────────────────────────

    def _annotate(self, frame: np.ndarray, tracks) -> np.ndarray:
        h, w = frame.shape[:2]
        for t in tracks:
            x1, y1, x2, y2 = t.bbox()
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)

            if self._mode == "TRACK":
                color = config.COLOR_TRACK
                label = f"ID {t.id}"
            elif t.name == "Unknown":
                color = config.COLOR_UNKNOWN
                label = "Unknown"
            else:
                color = config.COLOR_KNOWN
                label = f"{t.name}  {t.confidence:.0%}"

            # Box
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

            # Label pill
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)
            py = max(y1 - 8, th + 8)
            cv2.rectangle(frame, (x1, py - th - 6), (x1 + tw + 8, py + 2), color, -1)
            cv2.putText(frame, label, (x1 + 4, py - 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)

        # HUD
        mode_col = (50, 200, 50) if self._mode == "DETECT" else (50, 165, 230)
        cv2.putText(frame, f"{self._mode}  {self._ai_fps:.1f} FPS",
                    (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.65, mode_col, 2, cv2.LINE_AA)
        return frame

    # ── Servo ─────────────────────────────────────────────────────────────────

    def _servo_step(self, face_cx: float, face_cy: float) -> None:
        if not self._kit:
            return
        err_x = face_cx - config.FRAME_W / 2
        err_y = face_cy - config.FRAME_H / 2
        if abs(err_x) < config.DEADZONE_X: err_x = 0.0
        if abs(err_y) < config.DEADZONE_Y: err_y = 0.0
        self._pan_integral  += err_x
        self._tilt_integral += err_y
        dp = config.KP*err_x + config.KI*self._pan_integral
        dt = config.KP*err_y + config.KI*self._tilt_integral
        dp = max(-config.MAX_SERVO_SPEED, min(config.MAX_SERVO_SPEED, dp))
        dt = max(-config.MAX_SERVO_SPEED, min(config.MAX_SERVO_SPEED, dt))
        self._pan  = max(config.PAN_MIN,  min(config.PAN_MAX,  self._pan  + dp))
        self._tilt = max(config.TILT_MIN, min(config.TILT_MAX, self._tilt + dt))
        try:
            self._kit.servo[config.PAN_CHANNEL].angle  = self._pan
            self._kit.servo[config.TILT_CHANNEL].angle = self._tilt
        except Exception:
            pass
