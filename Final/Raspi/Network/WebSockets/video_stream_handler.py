"""
video_stream_handler.py
========================
Captures webcam frames via OpenCV, encodes them as JPEG, and feeds them
to the WebSocketServer for broadcast.

Design goals:
  - Target 15–20 FPS at 640×480 with JPEG quality 65
  - Run capture in a background thread (non-blocking for asyncio)
  - Drop stale frames when the async loop falls behind (zero-copy queue swap)
  - Avoid unnecessary buffer copies

Architecture:
  ┌──────────────────────┐      shared        ┌──────────────────────┐
  │  CaptureThread       │ ──── latest_frame ─▶│  AsyncFeeder         │
  │  (threading.Thread)  │      (atomic swap)  │  (asyncio coroutine) │
  └──────────────────────┘                     └──────────────────────┘
                                                        │
                                                        ▼
                                               WebSocketServer.broadcast_frame()

All tunable values are in config.py.

Dependencies:
    pip install opencv-python-headless numpy
"""

import asyncio
import logging
import threading
import time
from typing import Optional

import cv2

import config

logger = logging.getLogger("VideoStreamHandler")


# ─────────────────────────────────────────────────────────────────────────────
# VideoStreamHandler
# ─────────────────────────────────────────────────────────────────────────────
class VideoStreamHandler:
    """
    Captures frames from a webcam in a background thread and streams them
    to a WebSocketServer instance via asyncio.
    """

    def __init__(self, server, camera_index: int = config.VIDEO_CAMERA_INDEX) -> None:
        """
        Args:
            server: A WebSocketServer instance with a broadcast_frame() coroutine.
            camera_index: OpenCV camera device index (default from config).
        """
        self._server = server
        self._camera_index = camera_index

        # Latest encoded JPEG bytes – written by capture thread, read by async feeder
        self._latest_frame: Optional[bytes] = None
        self._frame_lock = threading.Lock()

        self._running = False
        self._capture_thread: Optional[threading.Thread] = None

        # JPEG encode params (pre-built once)
        self._encode_params = [cv2.IMWRITE_JPEG_QUALITY, config.VIDEO_JPEG_QUALITY]

        # Stats
        self._frames_captured: int = 0
        self._frames_sent: int = 0
        self._stat_time: float = time.time()

    # ── Public API ────────────────────────────────────────────────────────────

    def start_capture(self) -> None:
        """Start the background capture thread."""
        if self._running:
            return
        self._running = True
        self._capture_thread = threading.Thread(
            target=self._capture_loop,
            name="VideoCapture",
            daemon=True,
        )
        self._capture_thread.start()
        logger.info("Video capture thread started (camera %d).", self._camera_index)

    def stop_capture(self) -> None:
        """Signal the capture thread to stop."""
        self._running = False
        if self._capture_thread:
            self._capture_thread.join(timeout=3)
        logger.info("Video capture stopped.")

    async def stream_loop(self) -> None:
        """
        Async loop that reads the latest captured frame and broadcasts it.
        Run this as an asyncio task alongside the WebSocket server.
        """
        logger.info("Video stream loop started.")
        while self._running:
            frame_bytes = self._pop_latest_frame()
            if frame_bytes is not None:
                await self._server.broadcast_frame(frame_bytes, frame_type="video")
                self._frames_sent += 1
                self._log_stats()
            # Yield to event loop; sleep keeps us near TARGET_FPS
            await asyncio.sleep(config.VIDEO_FRAME_INTERVAL)

    # ── Capture thread ────────────────────────────────────────────────────────

    def _capture_loop(self) -> None:
        """
        Runs in a background thread.
        Opens the camera, captures frames, encodes to JPEG, stores latest.
        """
        cap = self._open_camera()
        if cap is None:
            logger.error("Could not open camera %d. Capture thread exiting.", self._camera_index)
            self._running = False
            return

        logger.info(
            "Camera opened: %dx%d @ target %d FPS",
            config.VIDEO_CAPTURE_WIDTH, config.VIDEO_CAPTURE_HEIGHT, config.VIDEO_TARGET_FPS,
        )

        next_frame_time = time.monotonic()

        while self._running:
            ret, frame = cap.read()
            if not ret:
                logger.warning("Frame read failed – retrying…")
                time.sleep(0.1)
                continue

            # Encode to JPEG (in-place, no extra copy)
            ok, buf = cv2.imencode(".jpg", frame, self._encode_params)
            if not ok:
                continue

            jpeg_bytes: bytes = buf.tobytes()

            # Atomic swap – async feeder always gets the freshest frame
            with self._frame_lock:
                self._latest_frame = jpeg_bytes

            self._frames_captured += 1

            # Pace the capture thread to TARGET_FPS
            next_frame_time += config.VIDEO_FRAME_INTERVAL
            sleep_for = next_frame_time - time.monotonic()
            if sleep_for > 0:
                time.sleep(sleep_for)
            else:
                # We're behind – reset pacing to avoid spiral
                next_frame_time = time.monotonic()

        cap.release()
        logger.info("Camera released.")

    def _open_camera(self) -> Optional[cv2.VideoCapture]:
        """Open and configure the camera, return None on failure."""
        cap = cv2.VideoCapture(self._camera_index, cv2.CAP_V4L2)
        if not cap.isOpened():
            # Fallback: try without explicit backend
            cap = cv2.VideoCapture(self._camera_index)
        if not cap.isOpened():
            return None

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.VIDEO_CAPTURE_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.VIDEO_CAPTURE_HEIGHT)
        cap.set(cv2.CAP_PROP_FPS, config.VIDEO_TARGET_FPS)
        # Minimize internal buffer to reduce latency
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        return cap

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _pop_latest_frame(self) -> Optional[bytes]:
        """Return and clear the latest frame (None if no new frame)."""
        with self._frame_lock:
            frame = self._latest_frame
            self._latest_frame = None  # Mark as consumed
        return frame

    def _log_stats(self) -> None:
        now = time.time()
        elapsed = now - self._stat_time
        if elapsed >= config.VIDEO_STATS_INTERVAL:
            sent_fps = self._frames_sent / elapsed
            cap_fps = self._frames_captured / elapsed
            logger.info(
                "Video stats: capture=%.1f fps | sent=%.1f fps | clients=%d",
                cap_fps,
                sent_fps,
                len(self._server._clients),
            )
            self._frames_captured = 0
            self._frames_sent = 0
            self._stat_time = now


# ─────────────────────────────────────────────────────────────────────────────
# Standalone test (no WebSocket server needed)
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(message)s")

    class _MockServer:
        _clients = ["mock"]

        async def broadcast_frame(self, data: bytes, frame_type: str = "video") -> None:
            print(f"[mock] broadcast {frame_type} frame: {len(data)} bytes")

    handler = VideoStreamHandler(_MockServer())
    handler.start_capture()

    async def _test():
        await handler.stream_loop()

    try:
        asyncio.run(_test())
    except KeyboardInterrupt:
        handler.stop_capture()
        sys.exit(0)
