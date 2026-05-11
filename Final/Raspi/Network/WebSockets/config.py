"""
config.py
==========
Centralized configuration for the WebSocket streaming subsystem.
All tunable values live here — no magic numbers scattered across modules.

To override settings without editing this file, set environment variables
before launching main.py:

    WS_PORT=9000 MQTT_BROKER=192.168.1.10 python main.py

For Ngrok WAN access (no port forwarding needed):

    NGROK_ENABLED=true NGROK_AUTH_TOKEN=your_token python main.py

Environment variable names match the constant names below (uppercase).
"""

import os

# ─────────────────────────────────────────────────────────────────────────────
# WebSocket Server
# ─────────────────────────────────────────────────────────────────────────────

# Bind address. "0.0.0.0" listens on all interfaces (required for WAN access).
# Set to "127.0.0.1" to restrict to localhost only (e.g. behind a reverse proxy).
WS_HOST: str = os.environ.get("WS_HOST", "0.0.0.0")

# WebSocket port.
# WAN / Port Forwarding : Forward this port on your router to the Raspberry Pi.
# Reverse Proxy         : Point nginx/caddy at this port and terminate TLS there.
# Firewall              : sudo ufw allow <WS_PORT>/tcp
WS_PORT: int = int(os.environ.get("WS_PORT", 8765))

# WebSocket keep-alive ping interval and timeout (seconds).
# Increase ping_timeout on flaky WAN connections.
WS_PING_INTERVAL: int = int(os.environ.get("WS_PING_INTERVAL", 20))
WS_PING_TIMEOUT: int = int(os.environ.get("WS_PING_TIMEOUT", 10))

# Maximum incoming WebSocket message size in bytes (2 MB default).
WS_MAX_MESSAGE_SIZE: int = int(os.environ.get("WS_MAX_MESSAGE_SIZE", 2 * 1024 * 1024))

# Per-client send queue depth (frames). When full, the oldest frame is dropped
# to protect latency. Keep this small (1–3) for lowest lag.
WS_CLIENT_QUEUE_MAX: int = int(os.environ.get("WS_CLIENT_QUEUE_MAX", 2))

# How often (seconds) to log broadcast throughput statistics.
WS_STATS_INTERVAL: float = float(os.environ.get("WS_STATS_INTERVAL", 10.0))

# ─────────────────────────────────────────────────────────────────────────────
# MQTT Broker
# ─────────────────────────────────────────────────────────────────────────────

# Hostname or IP of the MQTT broker (Mosquitto running on the Pi or LAN).
MQTT_BROKER: str = os.environ.get("MQTT_BROKER", "localhost")

# Standard MQTT port (1883 plain, 8883 TLS).
MQTT_PORT: int = int(os.environ.get("MQTT_PORT", 1883))

# MQTT keep-alive interval in seconds.
MQTT_KEEPALIVE: int = int(os.environ.get("MQTT_KEEPALIVE", 60))

# Client ID used by the WebSocket ↔ MQTT bridge.
MQTT_CLIENT_ID: str = os.environ.get("MQTT_CLIENT_ID", "ws-bridge")

# ─────────────────────────────────────────────────────────────────────────────
# MQTT Topics
# ─────────────────────────────────────────────────────────────────────────────

# Inbound: car publishes status here; bridge forwards to WebSocket clients.
MQTT_TOPIC_STATUS: str = os.environ.get("MQTT_TOPIC_STATUS", "dev/status")

# Bidirectional: dashboard sends motor commands via WebSocket;
# bridge publishes them here for the car to consume.
MQTT_TOPIC_MOTOR: str = os.environ.get("MQTT_TOPIC_MOTOR", "dev/motor")

# ─────────────────────────────────────────────────────────────────────────────
# Video Capture
# ─────────────────────────────────────────────────────────────────────────────

# OpenCV device index. 0 = /dev/video0 (first USB/CSI camera on the Pi).
VIDEO_CAMERA_INDEX: int = int(os.environ.get("VIDEO_CAMERA_INDEX", 0))

# Capture resolution. 640×480 is the sweet spot for latency vs. quality on Pi.
# Reduce to 320×240 for very constrained bandwidth.
VIDEO_CAPTURE_WIDTH: int = int(os.environ.get("VIDEO_CAPTURE_WIDTH", 640))
VIDEO_CAPTURE_HEIGHT: int = int(os.environ.get("VIDEO_CAPTURE_HEIGHT", 480))

# Target capture frame rate. The async feeder matches this pace.
# 15–20 FPS is recommended; higher values increase CPU load on the Pi.
VIDEO_TARGET_FPS: int = int(os.environ.get("VIDEO_TARGET_FPS", 20))

# Derived: seconds between frames (used for sleep pacing in both threads).
VIDEO_FRAME_INTERVAL: float = 1.0 / VIDEO_TARGET_FPS

# JPEG compression quality (0–100). Lower = smaller payload = less latency.
# 60–70 is the recommended range for surveillance streams.
VIDEO_JPEG_QUALITY: int = int(os.environ.get("VIDEO_JPEG_QUALITY", 65))

# How often (seconds) to log video throughput statistics.
VIDEO_STATS_INTERVAL: float = float(os.environ.get("VIDEO_STATS_INTERVAL", 10.0))

# ─────────────────────────────────────────────────────────────────────────────
# Audio Capture
# ─────────────────────────────────────────────────────────────────────────────

# Microphone sample rate in Hz. 16 kHz is standard for voice/surveillance.
AUDIO_SAMPLE_RATE: int = int(os.environ.get("AUDIO_SAMPLE_RATE", 16_000))

# Number of audio channels. 1 = mono (lower bandwidth, sufficient for voice).
AUDIO_CHANNELS: int = int(os.environ.get("AUDIO_CHANNELS", 1))

# Bytes per sample. 2 = 16-bit PCM (paInt16 in PyAudio).
AUDIO_SAMPLE_WIDTH: int = int(os.environ.get("AUDIO_SAMPLE_WIDTH", 2))

# Samples per audio chunk. 1024 samples @ 16 kHz ≈ 64 ms per packet.
# Reduce to 512 for ~32 ms latency at the cost of more CPU overhead.
AUDIO_CHUNK_SAMPLES: int = int(os.environ.get("AUDIO_CHUNK_SAMPLES", 1024))

# PyAudio input device index. None = system default microphone.
# Set to an integer to select a specific device (use `python -m pyaudio` to list).
_audio_device_env = os.environ.get("AUDIO_DEVICE_INDEX")
AUDIO_DEVICE_INDEX = int(_audio_device_env) if _audio_device_env is not None else None

# Max audio chunks queued before oldest is dropped (backpressure).
AUDIO_QUEUE_MAX: int = int(os.environ.get("AUDIO_QUEUE_MAX", 4))

# Timeout (seconds) for the blocking queue.get() call inside the async feeder.
# Shorter = more responsive shutdown; longer = fewer executor wakeups.
AUDIO_QUEUE_TIMEOUT: float = float(os.environ.get("AUDIO_QUEUE_TIMEOUT", 0.05))

# ─────────────────────────────────────────────────────────────────────────────
# Ngrok Tunneling (WAN Access without Port Forwarding)
# ─────────────────────────────────────────────────────────────────────────────

# Enable/disable Ngrok tunneling globally.
# When enabled, creates public URLs for WebSocket and MQTT services.
# Works behind CGNAT, mobile hotspots, and restrictive firewalls.
NGROK_ENABLED: bool = os.environ.get("NGROK_ENABLED", "false").lower() in ("true", "1", "yes")

# Ngrok authentication token (REQUIRED for Ngrok to work).
# Get your free token from: https://dashboard.ngrok.com/get-started/your-authtoken
# Set via environment variable: export NGROK_AUTH_TOKEN="your_token_here"
NGROK_AUTH_TOKEN: str = os.environ.get("NGROK_AUTH_TOKEN", "")

# Ngrok region (affects latency). Options: us, eu, ap, au, sa, jp, in
# Choose the region closest to your clients for best performance.
NGROK_REGION: str = os.environ.get("NGROK_REGION", "us")

# Enable WebSocket tunnel (creates wss:// public URL)
NGROK_WEBSOCKET_ENABLED: bool = os.environ.get("NGROK_WEBSOCKET_ENABLED", "true").lower() in ("true", "1", "yes")

# Enable MQTT tunnel (creates tcp:// public endpoint)
NGROK_MQTT_ENABLED: bool = os.environ.get("NGROK_MQTT_ENABLED", "true").lower() in ("true", "1", "yes")

# Local ports to tunnel (should match your service ports)
NGROK_WS_PORT: int = int(os.environ.get("NGROK_WS_PORT", WS_PORT))
NGROK_MQTT_PORT: int = int(os.environ.get("NGROK_MQTT_PORT", MQTT_PORT))

# Ngrok tunnel reconnection settings
NGROK_RECONNECT_DELAY: int = int(os.environ.get("NGROK_RECONNECT_DELAY", 5))  # seconds
NGROK_HEALTH_CHECK_INTERVAL: int = int(os.environ.get("NGROK_HEALTH_CHECK_INTERVAL", 30))  # seconds

# ─────────────────────────────────────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────────────────────────────────────

LOG_LEVEL: str = os.environ.get("LOG_LEVEL", "INFO").upper()
LOG_FORMAT: str = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOG_DATE_FORMAT: str = "%H:%M:%S"
