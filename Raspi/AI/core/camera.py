"""
Camera thread — captures frames and puts them in a queue.

Supports:
  • OpenCV VideoCapture (dev machines, USB cams)
  • picamera2 (Raspberry Pi native — 2× faster)

Queue uses always-latest semantics: if the consumer is slow, old
frames are discarded so the AI thread always sees the freshest image.
"""

import queue
import threading
import logging
import sys
import cv2
import numpy as np

sys.path.insert(0, "..")
import config

log = logging.getLogger(__name__)


class Camera:
    def __init__(self):
        # One queue: full-res BGR frames (640×480)
        self.queue: queue.Queue = queue.Queue(maxsize=2)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.fps = 0.0

    def start(self) -> None:
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run_picamera2 if config.USE_PICAMERA2 else self._run_opencv,
            daemon=True, name="camera"
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=3)

    # ── OpenCV backend ────────────────────────────────────────────────────────

    def _run_opencv(self) -> None:
        import time
        cap = cv2.VideoCapture(config.CAMERA_INDEX)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH,  config.FRAME_W)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_H)
        cap.set(cv2.CAP_PROP_FPS,          config.FPS_TARGET)

        if not cap.isOpened():
            log.error("Cannot open camera %d", config.CAMERA_INDEX)
            return

        log.info("Camera opened: %dx%d @ %d FPS", config.FRAME_W, config.FRAME_H, config.FPS_TARGET)
        t0, n = time.perf_counter(), 0

        while not self._stop.is_set():
            ok, frame = cap.read()
            if not ok:
                continue
            frame = self._fix(frame)
            self._push(frame)
            n += 1
            elapsed = time.perf_counter() - t0
            if elapsed >= 1.0:
                self.fps = n / elapsed
                n, t0 = 0, time.perf_counter()

        cap.release()

    # ── picamera2 backend ─────────────────────────────────────────────────────

    def _run_picamera2(self) -> None:
        import time
        try:
            from picamera2 import Picamera2
        except ImportError:
            log.warning("picamera2 not found — falling back to OpenCV")
            config.USE_PICAMERA2 = False
            self._run_opencv()
            return

        picam2 = Picamera2()
        cfg = picam2.create_video_configuration(
            main={"size": (config.FRAME_W, config.FRAME_H), "format": "RGB888"}
        )
        picam2.configure(cfg)
        picam2.start()
        log.info("picamera2 started %dx%d", config.FRAME_W, config.FRAME_H)

        t0, n = time.perf_counter(), 0
        while not self._stop.is_set():
            rgb = picam2.capture_array()
            frame = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
            frame = self._fix(frame)
            self._push(frame)
            n += 1
            elapsed = time.perf_counter() - t0
            if elapsed >= 1.0:
                self.fps = n / elapsed
                n, t0 = 0, time.perf_counter()

        picam2.stop()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _fix(self, frame: np.ndarray) -> np.ndarray:
        if config.FLIP_H:
            frame = cv2.flip(frame, 1)
        if config.FLIP_V:
            frame = cv2.flip(frame, 0)
        return frame

    def _push(self, frame: np.ndarray) -> None:
        try:
            self.queue.put_nowait(frame)
        except queue.Full:
            try:
                self.queue.get_nowait()
            except queue.Empty:
                pass
            self.queue.put_nowait(frame)
