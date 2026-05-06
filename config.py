"""
Configuration file for Face Recognition and Tracking System
"""

# ============================================================================
# CAMERA SETTINGS
# ============================================================================
CAMERA_INDEX = 0  # 0 for laptop webcam, adjust for Pi camera
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
FPS_TARGET = 30

# Flip the raw frame from the camera before ANY processing.
# FLIP_HORIZONTAL = True  → corrects mirrored webcam (most laptops)
# FLIP_VERTICAL   = True  → corrects upside-down mount (e.g. Pi cam on car)
# Both can be True at the same time.
FLIP_HORIZONTAL = True   # set False if your camera is already correct
FLIP_VERTICAL   = False  # set True if camera is mounted upside-down

# ============================================================================
# FACE DETECTION SETTINGS (YOLOv8-nano)
# ============================================================================
YOLO_MODEL = "yolov8n-face.pt"  # Will be downloaded/trained
YOLO_CONFIDENCE = 0.5  # Detection confidence threshold
YOLO_IOU = 0.45  # Non-max suppression IOU threshold

# ============================================================================
# FACE RECOGNITION SETTINGS
# ============================================================================
FACE_ENCODINGS_PATH = "known_faces/encodings.pkl"
FACE_IMAGES_DIR = "known_faces/images"
RECOGNITION_TOLERANCE = 0.6  # Lower = stricter matching (0.6 is default)
FACE_RECOGNITION_MODEL = "hog"  # "hog" for CPU, "cnn" for GPU (use hog on Pi)

# ============================================================================
# SERVO SETTINGS (PCA9685)
# ============================================================================
SERVO_I2C_ADDRESS = 0x40
SERVO_FREQUENCY = 50  # 50Hz for standard servos

# Servo channels on PCA9685
PAN_CHANNEL = 0   # Horizontal movement
TILT_CHANNEL = 1  # Vertical movement

# Servo angle limits (adjust based on your servo specs)
PAN_MIN = 0
PAN_MAX = 180
PAN_CENTER = 90

TILT_MIN = 0
TILT_MAX = 180
TILT_CENTER = 90

# Servo speed limits (degrees per frame)
MAX_SERVO_SPEED = 5  # Maximum degrees to move per frame

# ============================================================================
# PID CONTROLLER SETTINGS
# ============================================================================
# PAN (Horizontal) PID parameters
PAN_KP = 0.08  # Proportional gain
PAN_KI = 0.001  # Integral gain
PAN_KD = 0.02  # Derivative gain

# TILT (Vertical) PID parameters
TILT_KP = 0.08
TILT_KI = 0.001
TILT_KD = 0.02

# PID limits
PID_INTEGRAL_LIMIT = 100  # Prevent integral windup
PID_OUTPUT_LIMIT = 30  # Maximum correction per cycle (degrees)

# Deadzone (pixels) - don't move servo if face is within this range of center
DEADZONE_X = 30
DEADZONE_Y = 30

# ============================================================================
# TRACKING SETTINGS
# ============================================================================
TRACK_UNKNOWN_FACES = True  # Track even if face is not recognized
MIN_FACE_SIZE = 50  # Minimum face width/height in pixels
SMOOTHING_FACTOR = 0.3  # Exponential smoothing (0-1, lower = smoother)

# ============================================================================
# PERFORMANCE SETTINGS
# ============================================================================
# Frame skipping: run face RECOGNITION every N frames (detection runs every frame)
# 1 = every frame (slowest, most accurate)
# 5 = every 5th frame (recommended for Pi — ~15 FPS detection, ~3 FPS recognition)
PROCESS_EVERY_N_FRAMES = 5

USE_MULTIPROCESSING = True  # Use separate process for face recognition
MAX_CPU_CORES = 3           # Maximum cores to use (leave 1 for OS on Pi)

# ============================================================================
# TINY LLM SETTINGS (event-driven assistant, Raspberry Pi friendly)
# ============================================================================
# Keep disabled by default for compatibility. Enable from GUI settings when ready.
ENABLE_TINY_LLM = False
TINY_LLM_MODEL_PATH = "models/qwen2.5-1.5b-instruct-q4_k_m.gguf"
TINY_LLM_PROFILE = "pi_fast"  # "pi_fast", "balanced", "quality"
TINY_LLM_MAX_EVENT_RATE_SEC = 2.0

# Profile parameters
TINY_LLM_PROFILE_PRESETS = {
    "pi_fast": {
        "n_ctx": 768,
        "max_tokens": 48,
        "temperature": 0.15,
        "top_p": 0.9,
        "top_k": 20,
        "repeat_penalty": 1.05,
        "n_threads": 2,
    },
    "balanced": {
        "n_ctx": 1024,
        "max_tokens": 72,
        "temperature": 0.2,
        "top_p": 0.92,
        "top_k": 30,
        "repeat_penalty": 1.08,
        "n_threads": 3,
    },
    "quality": {
        "n_ctx": 1536,
        "max_tokens": 96,
        "temperature": 0.25,
        "top_p": 0.95,
        "top_k": 40,
        "repeat_penalty": 1.1,
        "n_threads": 4,
    },
}

# Coordinate extraction stabilization
COORDINATE_SMOOTHING_WINDOW = 5

# ============================================================================
# DISPLAY SETTINGS
# ============================================================================
SHOW_FPS = True
SHOW_FACE_BOX = True
SHOW_LANDMARKS = False
DISPLAY_SCALE = 1.0  # Scale display window (1.0 = original size)

# ============================================================================
# RASPBERRY PI SPECIFIC
# ============================================================================
IS_RASPBERRY_PI = False  # Set to True when running on Pi
ENABLE_SERVO_CONTROL = False  # Set to True to enable servo motors
