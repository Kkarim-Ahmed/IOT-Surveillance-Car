"""
main.py
========
Entry point that wires WebSocketServer + VideoStreamHandler + AudioSystem
+ NgrokManager together and runs them as concurrent asyncio tasks.

All configuration (host, port, FPS, MQTT broker, Ngrok, etc.) is read from config.py.
Override any value with an environment variable before launching:

    WS_PORT=9000 VIDEO_TARGET_FPS=15 python main.py

For WAN access via Ngrok (no port forwarding needed):

    NGROK_ENABLED=true NGROK_AUTH_TOKEN=your_token python main.py

Usage:
    python main.py

Install dependencies on Raspberry Pi:
    pip install websockets paho-mqtt opencv-python-headless pyaudio numpy pyngrok
    sudo apt-get install portaudio19-dev libopencv-dev
"""

import asyncio
import logging

import config
from websocket_server import WebSocketServer
from video_stream_handler import VideoStreamHandler
from audio_system import AudioSystem
from ngrok_manager import NgrokManager

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL, logging.INFO),
    format=config.LOG_FORMAT,
    datefmt=config.LOG_DATE_FORMAT,
)
logger = logging.getLogger("Main")


async def main() -> None:
    ngrok_manager = None
    
    try:
        # 1. Start Ngrok tunnels first (if enabled)
        if config.NGROK_ENABLED:
            logger.info("Ngrok is enabled - starting tunnels...")
            ngrok_manager = NgrokManager()
            await ngrok_manager.start()
            
            # Give tunnels a moment to stabilize
            await asyncio.sleep(2)
            
            if ngrok_manager.websocket_url:
                logger.info("=" * 80)
                logger.info("🌐 REMOTE ACCESS READY")
                logger.info("=" * 80)
                logger.info(f"WebSocket URL: {ngrok_manager.websocket_url}")
                if ngrok_manager.mqtt_url:
                    logger.info(f"MQTT Broker:   {ngrok_manager.mqtt_url}")
                logger.info("=" * 80)
        else:
            logger.info("Ngrok is disabled - using local network only")
            logger.info("To enable WAN access: NGROK_ENABLED=true NGROK_AUTH_TOKEN=your_token python main.py")

        # 2. Create the server (picks up host/port/MQTT settings from config)
        server = WebSocketServer(
            host=config.WS_HOST,
            port=config.WS_PORT,
            mqtt_broker=config.MQTT_BROKER,
            mqtt_port=config.MQTT_PORT,
        )

        # 3. Create video and audio handlers (pick up their settings from config)
        video = VideoStreamHandler(server, camera_index=config.VIDEO_CAMERA_INDEX)
        audio = AudioSystem(server, device_index=config.AUDIO_DEVICE_INDEX)

        # 4. Start background capture threads (non-blocking)
        video.start_capture()
        audio.start_capture()

        logger.info("All subsystems started. Running…")

        # 5. Run server + stream loops concurrently
        await asyncio.gather(
            server.start(),
            video.stream_loop(),
            audio.stream_loop(),
        )
        
    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("Shutting down…")
    finally:
        # Clean shutdown
        if 'video' in locals():
            video.stop_capture()
        if 'audio' in locals():
            audio.stop_capture()
        if ngrok_manager:
            await ngrok_manager.stop()
        logger.info("Clean shutdown complete.")


if __name__ == "__main__":
    asyncio.run(main())
