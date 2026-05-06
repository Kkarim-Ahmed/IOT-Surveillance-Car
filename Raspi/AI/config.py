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
RECOG_EVERY_N     = 5       # run recognition every N AI frames (saves CPU)
DETECT_CONFIDENCE = 0.5     # MediaPipe min detection score

# ── Dataset ───────────────────────────────────────────────────────────────────
DATASET_DIR       = os.path.join(os.path.dirname(__file__), "dataset", "faces")
ENCODINGS_PATH    = os.path.join(os.path.dirname(__file__), "dataset", "encodings.pkl")
FALLBACK_ENCODINGS = os.path.join(os.path.dirname(__file__), "..", "..", "known_faces", "encodings.pkl")
MIN_PHOTOS        = 5       # minimum images per person for enrollment

# ── Kalman tracker ────────────────────────────────────────────────────────────
IOU_THRESHOLD     = 0.25
MAX_FRAMES_LOST   = 25

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

# ── Display / GUI ─────────────────────────────────────────────────────────────
WIN_W             = 1060    # initial window width
WIN_H             = 600     # initial window height
VIDEO_PANEL_W     = 640
VIDEO_PANEL_H     = 480
COLOR_KNOWN       = (50, 200, 50)    # BGR green
COLOR_UNKNOWN     = (50, 50, 220)    # BGR red
COLOR_TRACK       = (50, 165, 230)   # BGR orange
