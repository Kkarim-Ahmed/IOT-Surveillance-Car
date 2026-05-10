"""
main.py
========
Entry point that wires WebSocketServer + VideoStreamHandler + AudioSystem
together and runs them as concurrent asyncio tasks.

All configuration (host, port, FPS, MQTT broker, etc.) is read from config.py.
Override any value with an environment variable before launching:

    WS_PORT=9000 VIDEO_TARGET_FPS=15 python main.py

Usage:
    python main.py

Install dependencies on Raspberry Pi:
    pip install websockets paho-mqtt opencv-python-headless pyaudio numpy
    sudo apt-get install portaudio19-dev libopencv-dev
"""

import asyncio
import logging

import config
from websocket_server import WebSocketServer
from video_stream_handler import VideoStreamHandler
from audio_system import AudioSystem

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL, logging.INFO),
    format=config.LOG_FORMAT,
    datefmt=config.LOG_DATE_FORMAT,
)
logger = logging.getLogger("Main")


async def main() -> None:
    # 1. Create the server (picks up host/port/MQTT settings from config)
    server = WebSocketServer(
        host=config.WS_HOST,
        port=config.WS_PORT,
        mqtt_broker=config.MQTT_BROKER,
        mqtt_port=config.MQTT_PORT,
    )

    # 2. Create video and audio handlers (pick up their settings from config)
    video = VideoStreamHandler(server, camera_index=config.VIDEO_CAMERA_INDEX)
    audio = AudioSystem(server, device_index=config.AUDIO_DEVICE_INDEX)

    # 3. Start background capture threads (non-blocking)
    video.start_capture()
    audio.start_capture()

    logger.info("All subsystems started. Running…")

    # 4. Run server + stream loops concurrently
    try:
        await asyncio.gather(
            server.start(),
            video.stream_loop(),
            audio.stream_loop(),
        )
    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("Shutting down…")
    finally:
        video.stop_capture()
        audio.stop_capture()
        logger.info("Clean shutdown complete.")


if __name__ == "__main__":
    asyncio.run(main())
