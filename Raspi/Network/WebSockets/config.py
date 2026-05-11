"""
Centralized Configuration System
All configurable values with environment variable override support
"""

import os
import logging

# ============================================================================
# WEBSOCKET SETTINGS
# ============================================================================
WS_HOST = os.getenv("WS_HOST", "0.0.0.0")
WS_PORT = int(os.getenv("WS_PORT", "8765"))
WS_MAX_CLIENTS = int(os.getenv("WS_MAX_CLIENTS", "10"))
WS_PING_INTERVAL = int(os.getenv("WS_PING_INTERVAL", "20"))
WS_PING_TIMEOUT = int(os.getenv("WS_PING_TIMEOUT", "10"))

# ============================================================================
# MQTT SETTINGS
# ============================================================================
MQTT_BROKER_HOST = os.getenv("MQTT_BROKER_HOST", "localhost")
MQTT_BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", "1883"))
MQTT_KEEPALIVE = int(os.getenv("MQTT_KEEPALIVE", "60"))
MQTT_QOS = int(os.getenv("MQTT_QOS", "1"))
MQTT_CLIENT_ID = os.getenv("MQTT_CLIENT_ID", "raspi_surveillance_car")

# MQTT Authentication
MQTT_USERNAME = os.getenv("MQTT_USERNAME", "admin")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "surveillance2024")

# MQTT Topics
MQTT_TOPIC_MOTOR = "dev/motor"
MQTT_TOPIC_STATUS = "dev/status"
MQTT_TOPIC_AUDIO = "dev/audio"
MQTT_TOPIC_VIDEO = "dev/video"
MQTT_TOPIC_CONTROL = "dev/control"
MQTT_TOPICS_SUBSCRIBE = [
    MQTT_TOPIC_MOTOR,
    MQTT_TOPIC_CONTROL,
    MQTT_TOPIC_STATUS
]

# ============================================================================
# VIDEO STREAMING SETTINGS
# ============================================================================
VIDEO_ENABLED = os.getenv("VIDEO_ENABLED", "true").lower() == "true"
VIDEO_WIDTH = int(os.getenv("VIDEO_WIDTH", "640"))
VIDEO_HEIGHT = int(os.getenv("VIDEO_HEIGHT", "480"))
VIDEO_FPS = int(os.getenv("VIDEO_FPS", "15"))
VIDEO_JPEG_QUALITY = int(os.getenv("VIDEO_JPEG_QUALITY", "65"))
VIDEO_BUFFER_SIZE = int(os.getenv("VIDEO_BUFFER_SIZE", "1"))
VIDEO_CAMERA_INDEX = int(os.getenv("VIDEO_CAMERA_INDEX", "0"))
VIDEO_FRAME_DROP_THRESHOLD = float(os.getenv("VIDEO_FRAME_DROP_THRESHOLD", "0.1"))

# ============================================================================
# AUDIO STREAMING SETTINGS
# ============================================================================
AUDIO_ENABLED = os.getenv("AUDIO_ENABLED", "true").lower() == "true"
AUDIO_SAMPLE_RATE = int(os.getenv("AUDIO_SAMPLE_RATE", "16000"))
AUDIO_CHANNELS = int(os.getenv("AUDIO_CHANNELS", "1"))
AUDIO_FORMAT = "int16"  # 16-bit PCM
AUDIO_CHUNK_SIZE = int(os.getenv("AUDIO_CHUNK_SIZE", "1024"))
AUDIO_INPUT_DEVICE_INDEX = int(os.getenv("AUDIO_INPUT_DEVICE_INDEX", "-1"))  # -1 = default

# ============================================================================
# NGROK SETTINGS
# ============================================================================
NGROK_ENABLED = os.getenv("NGROK_ENABLED", "true").lower() == "true"
NGROK_AUTH_TOKEN = os.getenv("NGROK_AUTH_TOKEN", "")
NGROK_REGION = os.getenv("NGROK_REGION", "us")  # us, eu, ap, au, sa, jp, in
NGROK_MQTT_PORT = MQTT_BROKER_PORT
NGROK_WS_PORT = WS_PORT

# ============================================================================
# PACKET TAGS (Binary Protocol)
# ============================================================================
PACKET_TAG_JSON = 0x00      # JSON/MQTT events
PACKET_TAG_VIDEO = 0x01     # Video frames
PACKET_TAG_AUDIO = 0x02     # Audio chunks

# ============================================================================
# LOGGING SETTINGS
# ============================================================================
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format=LOG_FORMAT,
    datefmt=LOG_DATE_FORMAT
)

# ============================================================================
# PERFORMANCE SETTINGS
# ============================================================================
ASYNC_QUEUE_MAXSIZE = int(os.getenv("ASYNC_QUEUE_MAXSIZE", "10"))
RECONNECT_DELAY = int(os.getenv("RECONNECT_DELAY", "5"))
MAX_RECONNECT_ATTEMPTS = int(os.getenv("MAX_RECONNECT_ATTEMPTS", "10"))

# ============================================================================
# SYSTEM SETTINGS
# ============================================================================
GRACEFUL_SHUTDOWN_TIMEOUT = int(os.getenv("GRACEFUL_SHUTDOWN_TIMEOUT", "5"))

def print_config():
    """Print current configuration (for debugging)"""
    print("\n" + "="*70)
    print("RASPBERRY PI SURVEILLANCE CAR - CONFIGURATION")
    print("="*70)
    print(f"WebSocket Server: {WS_HOST}:{WS_PORT}")
    print(f"MQTT Broker: {MQTT_BROKER_HOST}:{MQTT_BROKER_PORT}")
    print(f"Video: {VIDEO_WIDTH}x{VIDEO_HEIGHT} @ {VIDEO_FPS}fps (Quality: {VIDEO_JPEG_QUALITY})")
    print(f"Audio: {AUDIO_SAMPLE_RATE}Hz, {AUDIO_CHANNELS} channel(s)")
    print(f"Ngrok: {'Enabled' if NGROK_ENABLED else 'Disabled'}")
    print(f"Log Level: {LOG_LEVEL}")
    print("="*70 + "\n")
