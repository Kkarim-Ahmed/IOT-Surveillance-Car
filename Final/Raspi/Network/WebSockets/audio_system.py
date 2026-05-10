"""
audio_system.py
================
Captures microphone audio and streams raw PCM chunks via WebSocket.

Audio spec (defaults, all overridable in config.py):
  - Format  : PCM signed 16-bit little-endian (S16_LE)
  - Rate    : 16 000 Hz
  - Channels: 1 (mono)
  - Chunk   : 1024 samples ≈ 64 ms per packet

Architecture:
  ┌──────────────────────┐   thread-safe queue   ┌──────────────────────┐
  │  PyAudio callback    │ ──────────────────────▶│  AsyncAudioFeeder    │
  │  (audio thread)      │                        │  (asyncio coroutine) │
  └──────────────────────┘                        └──────────────────────┘
                                                          │
                                                          ▼
                                               WebSocketServer.broadcast_frame()
                                               (frame_type="audio")

All tunable values are in config.py.

Dependencies:
    pip install pyaudio
    sudo apt-get install portaudio19-dev   # Raspberry Pi
"""

import asyncio
import logging
import queue
from typing import Optional

import config

logger = logging.getLogger("AudioSystem")

try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False
    logger.warning("pyaudio not installed – audio streaming disabled.")
class AudioSystem:
    """
    Captures microphone audio in a PyAudio callback thread and exposes an
    async stream_loop() coroutine that feeds chunks to the WebSocketServer.
    """

    def __init__(self, server, device_index: Optional[int] = config.AUDIO_DEVICE_INDEX) -> None:
        """
        Args:
            server: WebSocketServer instance with broadcast_frame() coroutine.
            device_index: PyAudio input device index. None = default mic.
        """
        self._server = server
        self._device_index = device_index

        # Thread-safe queue between PyAudio callback and asyncio loop
        self._audio_queue: queue.Queue = queue.Queue(maxsize=config.AUDIO_QUEUE_MAX)

        self._running = False
        self._pa: Optional["pyaudio.PyAudio"] = None
        self._stream: Optional["pyaudio.Stream"] = None

    # ── Public API ────────────────────────────────────────────────────────────

    def start_capture(self) -> None:
        """Open the microphone and start the PyAudio stream."""
        if not PYAUDIO_AVAILABLE:
            logger.error("Cannot start audio: pyaudio not installed.")
            return
        if self._running:
            return

        self._pa = pyaudio.PyAudio()
        self._running = True

        try:
            self._stream = self._pa.open(
                format=pyaudio.paInt16,
                channels=config.AUDIO_CHANNELS,
                rate=config.AUDIO_SAMPLE_RATE,
                input=True,
                input_device_index=self._device_index,
                frames_per_buffer=config.AUDIO_CHUNK_SAMPLES,
                stream_callback=self._audio_callback,
            )
            self._stream.start_stream()
            logger.info(
                "Audio capture started: %d Hz, %d-bit, mono, chunk=%d samples",
                config.AUDIO_SAMPLE_RATE, config.AUDIO_SAMPLE_WIDTH * 8, config.AUDIO_CHUNK_SAMPLES,
            )
        except Exception as exc:
            logger.error("Failed to open audio stream: %s", exc)
            self._running = False
            self._pa.terminate()
            self._pa = None

    def stop_capture(self) -> None:
        """Stop the microphone stream and release resources."""
        self._running = False
        if self._stream:
            try:
                self._stream.stop_stream()
                self._stream.close()
            except Exception:
                pass
            self._stream = None
        if self._pa:
            self._pa.terminate()
            self._pa = None
        logger.info("Audio capture stopped.")

    async def stream_loop(self) -> None:
        """
        Async loop that drains the audio queue and broadcasts chunks.
        Run as an asyncio task alongside the WebSocket server.
        """
        if not PYAUDIO_AVAILABLE:
            logger.warning("Audio stream loop skipped (pyaudio unavailable).")
            return

        logger.info("Audio stream loop started.")
        loop = asyncio.get_running_loop()

        while self._running:
            try:
                # Non-blocking get with a short timeout so we yield to the event loop
                chunk: bytes = await loop.run_in_executor(
                    None, self._blocking_get, config.AUDIO_QUEUE_TIMEOUT
                )
                if chunk:
                    await self._server.broadcast_frame(chunk, frame_type="audio")
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Audio stream loop error: %s", exc)
                await asyncio.sleep(0.1)

    # ── PyAudio callback (runs in audio thread) ───────────────────────────────

    def _audio_callback(
        self,
        in_data: bytes,
        frame_count: int,
        time_info: dict,
        status_flags: int,
    ):
        """Called by PyAudio in its own thread for each audio chunk."""
        import pyaudio  # local import to avoid NameError if not installed

        if status_flags:
            logger.debug("Audio callback status flags: %d", status_flags)

        if self._running:
            if self._audio_queue.full():
                # Drop oldest chunk to keep latency low
                try:
                    self._audio_queue.get_nowait()
                except queue.Empty:
                    pass
            try:
                self._audio_queue.put_nowait(in_data)
            except queue.Full:
                pass  # Still full – drop this chunk

        return (None, pyaudio.paContinue)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _blocking_get(self, timeout: float) -> Optional[bytes]:
        """Block up to `timeout` seconds waiting for an audio chunk."""
        try:
            return self._audio_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    @property
    def is_running(self) -> bool:
        return self._running


# ─────────────────────────────────────────────────────────────────────────────
# Standalone test
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(message)s")

    class _MockServer:
        _clients = ["mock"]

        async def broadcast_frame(self, data: bytes, frame_type: str = "audio") -> None:
            print(f"[mock] broadcast {frame_type} chunk: {len(data)} bytes")

    audio = AudioSystem(_MockServer())
    audio.start_capture()

    async def _test():
        await audio.stream_loop()

    try:
        asyncio.run(_test())
    except KeyboardInterrupt:
        audio.stop_capture()
        sys.exit(0)
