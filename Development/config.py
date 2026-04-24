"""
config.py — Central configuration for the MQTT Surveillance Car system.

Edit this file to match your broker settings and hardware wiring.
Used by mqtt_device_controller.py, connection_manager.py, and the GUI.
"""

# ─── MQTT Broker ──────────────────────────────────────────────────────────────
MQTT_BROKER    = "broker.hivemq.com"   # Replace with your local IP for Phase 1
MQTT_PORT      = 1883
MQTT_USERNAME  = ""                    # Leave empty for anonymous access
MQTT_PASSWORD  = ""
MQTT_CLIENT_ID = "surveillance-car-pi"

# ─── MQTT Topics (dev/* namespace used by this MQTT system) ───────────────────
TOPIC_MOTOR    = "dev/motor"      # GUI → Pi  : motor direction + speed
TOPIC_LED      = "dev/led"        # GUI → Pi  : LED on/off/blink
TOPIC_COMMANDS = "dev/commands"   # GUI → Pi  : servo, beep, system commands
TOPIC_STATUS   = "dev/status"     # Pi  → GUI : acknowledgements + fail-safe

# ─── Legacy car/* topics (used by the Node.js backend / main.py) ──────────────
TOPIC_CONTROL   = "car/control"
TOPIC_ALERT     = "car/alert"
TOPIC_AUDIO     = "car/audio"
TOPIC_MIC_AUDIO = "car/mic_audio"
TOPIC_MODE      = "car/mode"

# ─── Fail-Safe ────────────────────────────────────────────────────────────────
FAILSAFE_TIMEOUT = 2.0   # seconds — stop motors if no command received

# ─── PWM Frequency ────────────────────────────────────────────────────────────
PWM_FREQ = 1000  # Hz

# ─── Motor Driver (L298N) ─────────────────────────────────────────────────────
# ENA → PWM speed for left  motors (must be a PWM-capable GPIO pin)
# ENB → PWM speed for right motors (must be a PWM-capable GPIO pin)
# IN1 / IN2 → left  motor direction
# IN3 / IN4 → right motor direction
ENA_PIN = 12   # GPIO12 (PWM0)
ENB_PIN = 13   # GPIO13 (PWM1)
IN1_PIN = 17   # GPIO17
IN2_PIN = 27   # GPIO27
IN3_PIN = 22   # GPIO22
IN4_PIN = 23   # GPIO23

# ─── Servo Motor (SG90) ───────────────────────────────────────────────────────
SERVO_PIN = 21   # GPIO21

# ─── LED & Buzzer ─────────────────────────────────────────────────────────────
LED_PIN    = 20  # GPIO20
BUZZER_PIN = 4   # GPIO4

# ─── Audio ────────────────────────────────────────────────────────────────────
AUDIO_RATE         = 16000  # 16 kHz
AUDIO_CHANNELS     = 1      # Mono
AUDIO_CHUNK_SIZE   = 1024   # frames per chunk
AUDIO_DEVICE_INDEX = None   # None = default mic

# ─── Face Tracking ────────────────────────────────────────────────────────────
FACE_SERVO_MIN   = 30    # degrees
FACE_SERVO_MAX   = 150   # degrees
FACE_SERVO_STEP  = 5     # degrees per correction
FACE_DEAD_ZONE   = 0.10  # fraction of frame width
FACE_DRIVE_SPEED = 50    # motor speed when tracking
