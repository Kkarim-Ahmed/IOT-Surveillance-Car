"""
WebSocket Streaming Subsystem for Raspberry Pi Surveillance Car
===============================================================
Package providing real-time video, audio, and MQTT bridge over WebSocket.

Modules:
    config                - Centralized configuration (all tunable values)
    websocket_server      - Core async WebSocket server with multi-client broadcast
    video_stream_handler  - OpenCV frame capture, resize, JPEG encode, and stream
    audio_system          - PCM microphone capture and binary audio streaming
"""

from .websocket_server import WebSocketServer
from .video_stream_handler import VideoStreamHandler
from .audio_system import AudioSystem
from . import config

__all__ = ["WebSocketServer", "VideoStreamHandler", "AudioSystem", "config"]
__version__ = "1.0.0"
