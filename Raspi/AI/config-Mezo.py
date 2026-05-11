"""
Raspi/AI — configuration.
Edit these values; everything else reads from here.
"""
import os

# ── Camera ────────────────────────────────────────────────────────────────────
CAMERA_INDEX      = 0
FRAME_W           = 640
FRAME_H           = 480
AI_W              = 320     # inference resolution (faster on RPi)
AI_H              = 240
FPS_TARGET        = 30
FLIP_H            = True    # mirror correction for most webcams
FLIP_V            = False
USE_PICAMERA2     = False   # True on Raspberry Pi

# ── Tiny-model paths (downloaded by setup.py) ─────────────────────────────────
MODELS_DIR        = os.path.join(os.path.dirname(__file__), "models")
TFLITE_RECOGNIZER = os.path.join(MODELS_DIR, "mobilefacenet.tflite")  # ~5 MB
# Detection uses MediaPipe which bundles its own TFLite model internally.

# ── Recognition ───────────────────────────────────────────────────────────────
RECOG_THRESHOLD   = 0.55    # cosine similarity to accept a match (↑ = stricter)
MAX_EMBS_PERSON   = 8       # store up to N embeddings per person
DETECT_EVERY_N    = 3       # run face detection every N frames; Kalman fills gaps
RECOG_EVERY_N     = 10      # run recognition every N AI frames (saves CPU)
DETECT_CONFIDENCE = 0.5     # MediaPipe min detection score

# ── Dataset ───────────────────────────────────────────────────────────────────
DATASET_DIR       = os.path.join(os.path.dirname(__file__), "dataset", "faces")
ENCODINGS_PATH    = os.path.join(os.path.dirname(__file__), "dataset", "encodings.pkl")
FALLBACK_ENCODINGS = os.path.join(os.path.dirname(__file__), "..", "..", "known_faces", "encodings.pkl")
MIN_PHOTOS        = 5       # minimum images per person for enrollment

# ── Kalman tracker ────────────────────────────────────────────────────────────
IOU_THRESHOLD     = 0.25
MAX_FRAMES_LOST   = 25

# ── Body / person detection — used in TRACK mode ─────────────────────────────
# MediaPipe Pose Lite (complexity=0) runs ~40 ms/frame on RPi4.
# Detects full-body even when person faces away — essential for car following.
USE_BODY_DETECTOR      = True
BODY_DETECT_CONFIDENCE = 0.50   # pose min_detection_confidence
BODY_TRACK_CONFIDENCE  = 0.50   # pose min_tracking_confidence

# ── Motor (L298N) — differential drive ───────────────────────────────────────
MOTOR_ENABLED          = True
MOTOR_IN1              = 17      # left  motor direction A
MOTOR_IN2              = 18      # left  motor direction B
MOTOR_IN3              = 22      # right motor direction A
MOTOR_IN4              = 23      # right motor direction B
MOTOR_ENA              = 24      # left  motor PWM (ENA)
MOTOR_ENB              = 25      # right motor PWM (ENB)

# Distance zones — optimal values for a ~30 cm-long car with forward camera
#   STOP  : < 60 cm  → cut power (car body + safety gap)
#   HOLD  : 60-100 cm → steer-only, no forward drive (too close to advance)
#   FOLLOW: 100-280 cm → proportional forward speed (40 %→100 % of BASE_SPEED)
#                        This is the comfortable human–robot walking range.
#   CHASE : > 280 cm → full BASE_SPEED (person getting far, risk of losing lock)
MOTOR_SAFE_CM          = 60      # danger boundary — never go below this
MOTOR_HOLD_CM          = 100     # steer-only boundary
MOTOR_CHASE_CM         = 280     # full-speed boundary
MOTOR_SAFE_DISTANCE_CM = MOTOR_SAFE_CM   # backward-compat alias

MOTOR_BASE_SPEED       = 180     # 0-255 PWM duty at full throttle
MOTOR_DEAD_ZONE_PX     = 40      # ignore |error_x| < this (no-turn band, px)
MOTOR_REF_BBOX_H       = 200     # body bbox height (px) when person is 1 m away
                                  # → use the Calibrate button in the GUI!
MOTOR_SMOOTH_ALPHA     = 0.35    # EMA alpha for speed commands
                                  # 0 = never changes, 1 = instant, 0.35 = smooth
MOTOR_KP               = 0.40
MOTOR_KI               = 0.01
MOTOR_KD               = 0.05

# ── Recognition tuning ────────────────────────────────────────────────────────
RECOG_AMBIGUITY_MARGIN = 0.05   # reject if top-1 minus top-2 similarity < this

# ── Servo (PCA9685) — only active when ENABLE_SERVO=True ──────────────────────
ENABLE_SERVO      = False
PAN_CHANNEL       = 0
TILT_CHANNEL      = 1
PAN_CENTER        = 90
TILT_CENTER       = 90
PAN_MIN, PAN_MAX  = 0, 180
TILT_MIN,TILT_MAX = 0, 180
MAX_SERVO_SPEED   = 5
DEADZONE_X        = 30
DEADZONE_Y        = 30
KP, KI, KD       = 0.08, 0.001, 0.02

# ── Operating mode ────────────────────────────────────────────────────────────
# "track" = PersonDetector (full-body bbox) → best for floor-mounted camera on a car
# "detect" = FaceDetector only → use for enrollment / desktop testing
DEFAULT_MODE      = "track"

# ── Display / GUI ─────────────────────────────────────────────────────────────
WIN_W             = 1120    # initial window width
WIN_H             = 600     # initial window height
VIDEO_PANEL_W     = 640
VIDEO_PANEL_H     = 480
COLOR_KNOWN       = (50, 200, 50)    # BGR green
COLOR_UNKNOWN     = (50, 50, 220)    # BGR red
COLOR_TRACK       = (50, 165, 230)   # BGR orange
