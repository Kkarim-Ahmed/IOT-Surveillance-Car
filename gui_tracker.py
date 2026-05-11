"""
GUI Face Tracking System — dark-themed Tkinter UI
Modes: Tracking | Enrollment | Coordinate Extraction
Live PID tuning, enrolled-faces list, servo status.
"""

import cv2
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from PIL import Image, ImageTk
import threading
import time
import csv
import numpy as np
from pathlib import Path
from collections import deque

import config
from camera_utils import open_camera, read_frame
from blazeface_detector import BlazeFaceDetector
from face_recognition_module import FaceRecognitionSystem
from servo_control import FaceTrackingServo
from settings_manager import SettingsManager
from face_quality import FaceQualityAnalyzer
from confidence_display import ConfidenceDisplay
from multi_angle_enrollment import MultiAngleEnrollment
from temporal_smoothing import TemporalRecognitionSmoothing
from face_preprocessing import FacePreprocessor, FaceAligner, MultiCropRecognition
from enhanced_body_tracking import EnhancedBodyTracker, MotionPatternTracker

from tiny_llm import TinyLLMConfig, TinyLLMEngine

# Try to import psutil for performance monitoring
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("⚠️  psutil not available - performance monitoring disabled")


# ─────────────────────────────────────────────────────────────────────────────
# Premium Dark Theme Palette
# ─────────────────────────────────────────────────────────────────────────────
BG       = "#0f172a"  # Slate 900
BG2      = "#1e293b"  # Slate 800
BG3      = "#334155"  # Slate 700
ACCENT   = "#3b82f6"  # Blue 500
ACCENT2  = "#60a5fa"  # Blue 400
FG       = "#f8fafc"  # Slate 50
FG2      = "#94a3b8"  # Slate 400
GREEN    = "#10b981"  # Emerald 500
RED      = "#ef4444"  # Red 500
CYAN     = "#06b6d4"  # Cyan 500


# ─────────────────────────────────────────────────────────────────────────────
# Lightweight motor dashboard calculator (mock driver — no GPIO needed)
# ─────────────────────────────────────────────────────────────────────────────

class _MotorPID:
    def __init__(self, kp=0.15, ki=0.0, kd=0.04):
        self.kp, self.ki, self.kd = kp, ki, kd
        self._integral   = 0.0
        self._prev_error = 0.0
        self._prev_t     = time.perf_counter()

    def update(self, error: float) -> float:
        now = time.perf_counter()
        dt  = max(now - self._prev_t, 1e-4)
        self._integral += error * dt
        d   = (error - self._prev_error) / dt
        out = self.kp * error + self.ki * self._integral + self.kd * d
        self._prev_error = error
        self._prev_t     = now
        return out

    def reset(self):
        self._integral   = 0.0
        self._prev_error = 0.0
        self._prev_t     = time.perf_counter()


class MotorDashboard:
    """4-zone proportional differential-drive state calculator (desktop preview)."""

    SAFE_CM    = 60
    HOLD_CM    = 90     # Adjusted for slower, heavier car
    CHASE_CM   = 200    # Start full speed earlier (2 meters)
    BASE_SPEED = 180    # Increased to overcome 2.5kg inertia
    DEAD_PX    = 30
    ALPHA      = 0.35   # EMA smoothing

    # Actual DC motor RPM range (loaded estimate)
    MAX_RPM    = 75     # ~75 RPM under 600g per motor load (100 RPM no-load)

    ZONE_COLOR = {
        "STOP":   "#ef4444",
        "HOLD":   "#f97316",
        "FOLLOW": "#10b981",
        "CHASE":  "#eab308",
        "SEARCH": "#a855f7",
        "IDLE":   "#94a3b8",
    }

    def __init__(self):
        self._pid = _MotorPID()
        self._el  = 0.0
        self._er  = 0.0
        self.reset()

    def reset(self):
        self._el = self._er = 0.0
        self._pid.reset()
        self.cx          = 0
        self.cy          = 0
        self.error_x     = 0.0
        self.error_y     = 0.0
        self.distance_cm = 0.0
        self.left_speed  = 0
        self.right_speed = 0
        self.state       = "IDLE"

    def update(self, bbox: tuple, fw: int = 640, fh: int = 480):
        x1, y1, x2, y2 = bbox
        self.cx      = int((x1 + x2) / 2)
        self.cy      = int((y1 + y2) / 2)
        self.error_x = self.cx - fw / 2.0
        self.error_y = self.cy - fh / 2.0
        bh           = y2 - y1
        
        # Adaptive reference height: face is ~30% of frame height at 1 meter
        adaptive_ref_h = int(fh * 0.3)
        self.distance_cm = (adaptive_ref_h * 100.0 / bh) if bh > 0 else 9999.0
        d = self.distance_cm

        if d < self.SAFE_CM:
            self._instant_stop()
            return

        if d < self.HOLD_CM:
            fwd, self.state = 0, "HOLD"
        elif d < self.CHASE_CM:
            t   = (d - self.HOLD_CM) / (self.CHASE_CM - self.HOLD_CM)
            fwd = int(self.BASE_SPEED * (0.40 + 0.60 * max(0.0, min(1.0, t))))
            self.state = "FOLLOW"
        else:
            fwd, self.state = self.BASE_SPEED, "CHASE"

        turn  = 0 if abs(self.error_x) < self.DEAD_PX else int(self._pid.update(self.error_x))
        raw_l = max(0, min(255, fwd + turn))
        raw_r = max(0, min(255, fwd - turn))
        self._el       = self.ALPHA * raw_l + (1 - self.ALPHA) * self._el
        self._er       = self.ALPHA * raw_r + (1 - self.ALPHA) * self._er
        self.left_speed  = int(self._el)
        self.right_speed = int(self._er)

    def search(self, last_error_x: float = 0.0):
        """Visual-only SEARCH state — rotates toward side target was last seen."""
        spd = int(self.BASE_SPEED * 0.30)
        if last_error_x >= 0:
            self.left_speed, self.right_speed = spd, 0
        else:
            self.left_speed, self.right_speed = 0, spd
        self.distance_cm = 9999.0
        self.error_x     = 0.0
        self.error_y     = 0.0
        self.state       = "SEARCH"

    def _instant_stop(self):
        self._el = self._er = 0.0
        self.left_speed = self.right_speed = 0
        self.state = "STOP"
        self._pid.reset()


def _style(root: tk.Tk):
    """Apply premium dark ttk theme."""
    style = ttk.Style(root)
    style.theme_use("clam")

    style.configure(".",
                    background=BG, foreground=FG,
                    fieldbackground=BG2, troughcolor=BG2,
                    bordercolor=BG2, darkcolor=BG2, lightcolor=BG2,
                    font=("Segoe UI", 11))

    style.configure("TFrame",       background=BG)
    style.configure("Sidebar.TFrame", background=BG2)
    style.configure("TLabel",       background=BG,  foreground=FG)
    style.configure("Sidebar.TLabel", background=BG2, foreground=FG)
    style.configure("TLabelframe",  background=BG,  foreground=ACCENT2, borderwidth=0)
    style.configure("Sidebar.TLabelframe", background=BG2, foreground=ACCENT2, borderwidth=0)
    style.configure("TLabelframe.Label", background=BG, foreground=ACCENT2,
                    font=("Segoe UI", 12, "bold"))
    style.configure("Sidebar.TLabelframe.Label", background=BG2, foreground=ACCENT2,
                    font=("Segoe UI", 12, "bold"))
    style.configure("TButton",      background=ACCENT, foreground=FG,
                    borderwidth=0, focusthickness=0, padding=8,
                    font=("Segoe UI", 11, "bold"))
    style.map("TButton",
              background=[("active", ACCENT2), ("pressed", BG3)])
    style.configure("TEntry",       fieldbackground=BG3, foreground=FG,
                    insertcolor=FG, padding=5)
    style.configure("Treeview",     background=BG3, foreground=FG,
                    fieldbackground=BG3, rowheight=30, borderwidth=0)
    style.configure("Treeview.Heading", background=BG2, foreground=ACCENT2,
                    font=("Segoe UI", 11, "bold"), borderwidth=0)
    style.map("Treeview", background=[("selected", ACCENT)])

    style.configure("Status.TLabel", background=BG, foreground=FG2,
                    relief="flat", padding=(10, 5), font=("Segoe UI", 10))
    style.configure("FPS.TLabel",    background=BG, foreground=GREEN,
                    relief="flat", padding=(10, 5),
                    font=("Segoe UI", 10, "bold"))
    style.configure("Title.TLabel",  background=BG2, foreground=FG,
                    font=("Segoe UI", 18, "bold"))
    style.configure("Danger.TButton", background=RED, foreground=FG,
                    borderwidth=0, padding=8, font=("Segoe UI", 11, "bold"))
    style.map("Danger.TButton",
              background=[("active", "#dc2626")])


# ─────────────────────────────────────────────────────────────────────────────
# Main GUI class
# ─────────────────────────────────────────────────────────────────────────────

class FaceTrackingGUI:

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Premium Face Tracking System")
        self.root.geometry("1400x900")
        self.root.configure(bg=BG)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        _style(root)

        # ── system components ────────────────────────────────────────────────
        self.detector   = BlazeFaceDetector()
        self.recognizer = FaceRecognitionSystem()
        self.servo      = FaceTrackingServo()
        
        # Initialize body detector
        self.body_detector = None
        self._init_body_detector()
        
        # ── NEW: Top 5 improvements ──────────────────────────────────────────
        self.settings_manager = SettingsManager()
        self.quality_analyzer = FaceQualityAnalyzer()
        self.confidence_display = ConfidenceDisplay()
        self.multi_angle_enroll = MultiAngleEnrollment(self.quality_analyzer)
        
        # ── NEW: Accuracy improvements ───────────────────────────────────────
        self.temporal_smoother = TemporalRecognitionSmoothing(window_size=5, min_agreement=0.5)
        self.face_preprocessor = FacePreprocessor(enable_denoising=True, enable_sharpening=True)
        self.face_aligner = FaceAligner()
        self.multi_crop = MultiCropRecognition()
        self.enhanced_body_tracker = EnhancedBodyTracker()
        self.motion_tracker = MotionPatternTracker()

        # Motor dashboard calculator
        self.motor = MotorDashboard()
        
        self.current_person_id = None  # Currently tracked person
        
        # Body tracking signatures
        self.body_signatures = {}  # person_id -> body_signature

        # Tiny LLM runtime state
        self.tiny_llm = None
        self.last_llm_event_time = 0.0
        self.last_tracking_signature = None
        self.last_llm_message = "Assistant ready."
        self.llm_update_interval_ms = 350
        self.llm_profiles = ["pi_fast", "balanced", "quality"]
        self.llm_profile_var = None
        self.llm_enabled_var = None
        self.llm_status_var = None
        self.llm_hint_var = None

        # Coordinate stabilization state
        self.coord_history_by_face = {}
        self.coordinate_smoothing_window = int(
            self.settings_manager.get("coordinate_smoothing_window", config.COORDINATE_SMOOTHING_WINDOW)
        )
        
        # Apply loaded settings
        self._apply_settings()

        # ── runtime state ────────────────────────────────────────────────────
        self.cap               = None
        self.running           = False
        self.mode              = "tracking"
        self.frame_count       = 0
        self.fps_queue         = deque(maxlen=30)
        self.current_frame     = None
        self.face_locations    = []
        self.recognition_results = []
        self.smoothed_position = None
        
        # Body tracking state
        self.face_lost_time = None
        self.tracking_mode = "face"  # "face", "body", "lost"
        self.target_body_box = None
        self.face_lost_timeout = 1.0  # seconds - reduced for faster switching
        
        # Multi-person tracking state
        self.tracked_people = {}  # person_id -> {name, color, last_pos, confidence, last_seen}
        self.next_person_id = 1
        self.current_target_id = None
        self.target_identity = "Unknown"  # Remember who we're tracking
        
        # Lock-on and CV2 high-speed tracker state
        self.locked_identity = None
        self.cv2_tracker = None
        self.tracker_initialized = False
        
        # Performance monitoring
        self.perf_stats = {
            'fps': 0,
            'cpu_usage': 0,
            'memory_usage': 0,
            'detection_time': 0,
            'recognition_time': 0,
            'faces_detected': 0,
            'faces_recognized': 0,
            'tracking_accuracy': 0
        }
        self.perf_history = deque(maxlen=100)  # Store last 100 measurements

        # enrollment
        self.enroll_name   = None
        self.enroll_images = []
        self.enroll_count  = 0
        self.enroll_target = 5

        # coordinate extraction
        self.extracted_coords = []

        # ── build UI ─────────────────────────────────────────────────────────
        self._build_ui()
        self._init_tiny_llm()
        self._schedule_llm_poll()
        self._start_camera()

    def _init_body_detector(self):
        """Initialize high-speed OpenCV tracker (Zero-lag)."""
        # We no longer load YOLO/HOG as they cause severe lag.
        # We will use cv2.TrackerKCF_create() dynamically when a face is found.
        self.body_detector = None
        print("✅ High-speed OpenCV tracking engine ready (Zero-lag)")
    
    def _apply_settings(self):
        """Apply settings from settings manager."""
        try:
            # Apply recognition threshold
            threshold = self.settings_manager.get("recognition_threshold", 0.30)
            self.recognizer.SIMILARITY_THRESHOLD = threshold
            
            # Apply tracking settings
            self.face_lost_timeout = self.settings_manager.get("face_lost_timeout", 1.0)
            
            # Apply PID settings
            pan_kp = self.settings_manager.get("pan_kp", config.PAN_KP)
            pan_ki = self.settings_manager.get("pan_ki", config.PAN_KI)
            pan_kd = self.settings_manager.get("pan_kd", config.PAN_KD)
            tilt_kp = self.settings_manager.get("tilt_kp", config.TILT_KP)
            tilt_ki = self.settings_manager.get("tilt_ki", config.TILT_KI)
            tilt_kd = self.settings_manager.get("tilt_kd", config.TILT_KD)
            
            self.servo.set_pid_gains("pan", kp=pan_kp, ki=pan_ki, kd=pan_kd)
            self.servo.set_pid_gains("tilt", kp=tilt_kp, ki=tilt_ki, kd=tilt_kd)

            # Coordinate stabilization settings
            self.coordinate_smoothing_window = int(
                self.settings_manager.get("coordinate_smoothing_window", config.COORDINATE_SMOOTHING_WINDOW)
            )
             
            print("✅ Settings applied")
        except Exception as e:
            print(f"⚠️ Settings apply error: {e}")

    def _get_tiny_llm_config(self) -> TinyLLMConfig:
        profile_name = self.settings_manager.get("tiny_llm_profile", config.TINY_LLM_PROFILE)
        profile = config.TINY_LLM_PROFILE_PRESETS.get(
            profile_name, config.TINY_LLM_PROFILE_PRESETS[config.TINY_LLM_PROFILE]
        )
        model_path = self.settings_manager.get("tiny_llm_model_path", config.TINY_LLM_MODEL_PATH)

        return TinyLLMConfig(
            enabled=bool(self.settings_manager.get("tiny_llm_enabled", config.ENABLE_TINY_LLM)),
            model_path=model_path,
            n_ctx=int(profile["n_ctx"]),
            n_threads=int(profile["n_threads"]),
            max_tokens=int(profile["max_tokens"]),
            temperature=float(profile["temperature"]),
            top_p=float(profile["top_p"]),
            top_k=int(profile["top_k"]),
            repeat_penalty=float(profile["repeat_penalty"]),
        )

    def _init_tiny_llm(self):
        self.tiny_llm = TinyLLMEngine(self._get_tiny_llm_config())
        if self.llm_status_var is not None:
            self.llm_status_var.set(f"LLM: {self.tiny_llm.get_status()}")

    def _schedule_llm_poll(self):
        if not self.root.winfo_exists():
            return
        self._poll_llm_messages()
        self.root.after(self.llm_update_interval_ms, self._schedule_llm_poll)

    def _poll_llm_messages(self):
        if self.tiny_llm is None:
            return

        latest_result = None
        while True:
            result = self.tiny_llm.poll_result()
            if result is None:
                break
            latest_result = result

        if latest_result is not None:
            self.last_llm_message = latest_result["response"]
            if self.llm_hint_var is not None:
                self.llm_hint_var.set(f"Hint: {self.last_llm_message}")

        if self.llm_status_var is not None:
            self.llm_status_var.set(f"LLM: {self.tiny_llm.get_status()}")

    def _queue_llm_event(self, event_name: str, detail: str) -> None:
        if self.tiny_llm is None:
            return

        cooldown = float(self.settings_manager.get("tiny_llm_max_event_rate_sec", config.TINY_LLM_MAX_EVENT_RATE_SEC))
        now = time.time()
        if now - self.last_llm_event_time < cooldown:
            return

        if self.tiny_llm.submit_event(event_name, detail):
            self.last_llm_event_time = now

    def _update_tracking_llm_event(self):
        if self.tiny_llm is None or not getattr(self, "llm_enabled_var", None) or not self.llm_enabled_var.get():
            return
        face_count = len(self.face_locations)
        body_visible = self.target_body_box is not None
        signature = (self.tracking_mode, self.target_identity, face_count > 0, body_visible)

        if signature == self.last_tracking_signature:
            return
        self.last_tracking_signature = signature

        if face_count > 0 and self.tracking_mode == "face":
            self._queue_llm_event(
                "face_locked",
                f"Tracking {self.target_identity}; faces={face_count}; servo_enabled={self.servo_var.get()}",
            )
        elif self.tracking_mode == "face" and face_count == 0:
            self._queue_llm_event(
                "face_lost",
                f"Face lost timer active for {self.target_identity}; body_tracking={self.body_tracking_var.get()}",
            )
        elif self.tracking_mode == "body":
            self._queue_llm_event(
                "body_tracking",
                f"Body tracking target={self.target_identity}; body_visible={body_visible}",
            )
        elif self.tracking_mode == "lost":
            self._queue_llm_event(
                "tracking_lost",
                f"Tracking lost for {self.target_identity}; last_face_count={face_count}",
            )

    def _get_person_color(self, person_id):
        """Get consistent color for a person ID."""
        colors = [
            (0, 255, 0),    # Green
            (255, 0, 0),    # Blue  
            (0, 165, 255),  # Orange
            (255, 0, 255),  # Magenta
            (0, 255, 255),  # Yellow
            (255, 255, 0),  # Cyan
            (128, 0, 128),  # Purple
            (0, 128, 255),  # Light Orange
        ]
        return colors[person_id % len(colors)]

    def _update_performance_stats(self, detection_time, recognition_time):
        """Update performance statistics with error handling."""
        try:
            # CPU and memory usage (if psutil available)
            if PSUTIL_AVAILABLE:
                try:
                    self.perf_stats['cpu_usage'] = psutil.cpu_percent()
                    self.perf_stats['memory_usage'] = psutil.virtual_memory().percent
                except:
                    self.perf_stats['cpu_usage'] = 0
                    self.perf_stats['memory_usage'] = 0
            else:
                self.perf_stats['cpu_usage'] = 0
                self.perf_stats['memory_usage'] = 0
            
            # Processing times
            self.perf_stats['detection_time'] = detection_time * 1000  # Convert to ms
            self.perf_stats['recognition_time'] = recognition_time * 1000
            
            # Detection stats
            self.perf_stats['faces_detected'] = len(self.face_locations)
            recognized_count = sum(1 for name, _ in self.recognition_results if name != "Unknown")
            self.perf_stats['faces_recognized'] = recognized_count
            
            # Tracking accuracy (percentage of frames with successful tracking)
            if len(self.fps_queue) > 0:
                self.perf_stats['fps'] = sum(self.fps_queue) / len(self.fps_queue)
            
            # Store in history
            self.perf_history.append(self.perf_stats.copy())
        except Exception as e:
            print(f"Performance stats error: {e}")
            # Set default values if there's an error
            self.perf_stats = {
                'fps': 0,
                'cpu_usage': 0,
                'memory_usage': 0,
                'detection_time': 0,
                'recognition_time': 0,
                'faces_detected': 0,
                'faces_recognized': 0,
                'tracking_accuracy': 0
            }

    # =========================================================================
    # UI construction
    # =========================================================================

    def _build_ui(self):
        # Hidden variables to prevent crashes
        self.servo_var = tk.BooleanVar(value=False)
        self.body_tracking_var = tk.BooleanVar(value=True)
        self.threshold_var = tk.DoubleVar(value=self.settings_manager.get("recognition_threshold", 0.30))
        self.llm_enabled_var = tk.BooleanVar(value=False)
        self.llm_profile_var = tk.StringVar(value="balanced")
        self._pid_sliders = {}
        self.tracking_status_var = tk.StringVar(value="Status: Idle")

        # Sidebar | Video | Motor dashboard
        self.root.columnconfigure(0, weight=0)
        self.root.columnconfigure(1, weight=1)
        self.root.columnconfigure(2, weight=0)
        self.root.rowconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=0)

        # Left sidebar
        sidebar = ttk.Frame(self.root, width=320, style="Sidebar.TFrame")
        sidebar.grid(row=0, column=0, rowspan=2, sticky="nsew")
        sidebar.grid_propagate(False)
        self._build_sidebar(sidebar)

        # Right motor dashboard panel
        motor_panel = ttk.Frame(self.root, width=270, style="Sidebar.TFrame")
        motor_panel.grid(row=0, column=2, rowspan=2, sticky="nsew")
        motor_panel.grid_propagate(False)
        self._build_motor_dashboard(motor_panel)

        # Video panel (maximized)
        video_frame = ttk.Frame(self.root, style="TFrame")
        video_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        video_frame.columnconfigure(0, weight=1)
        video_frame.rowconfigure(0, weight=1)
        
        # Adding a subtle border effect for premium feel
        video_border = tk.Frame(video_frame, bg=ACCENT, bd=2)
        video_border.grid(row=0, column=0, sticky="nsew")
        video_border.columnconfigure(0, weight=1)
        video_border.rowconfigure(0, weight=1)
        
        self.video_label = ttk.Label(video_border, background=BG)
        self.video_label.grid(row=0, column=0, sticky="nsew")

        # Status bar
        status_bar = ttk.Frame(self.root, style="TFrame")
        status_bar.grid(row=1, column=1, sticky="ew", padx=20, pady=(0, 10))
        status_bar.columnconfigure(0, weight=1)

        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(status_bar, textvariable=self.status_var,
                  style="Status.TLabel").grid(row=0, column=0, sticky="w")

        self.fps_var = tk.StringVar(value="FPS: --")
        ttk.Label(status_bar, textvariable=self.fps_var,
                  style="FPS.TLabel").grid(row=0, column=1, sticky="e")

    def _build_sidebar(self, parent):
        parent.columnconfigure(0, weight=1)

        # Title
        title_frame = ttk.Frame(parent, style="Sidebar.TFrame")
        title_frame.pack(fill="x", pady=(20, 30), padx=20)
        ttk.Label(title_frame, text="✨ FaceTracker AI",
                  style="Title.TLabel").pack(anchor="center")

        # ── Add New Person (Enrollment) ──────────────────────────────────────
        enroll_frame = ttk.LabelFrame(parent, text="👤 Add New Person", style="Sidebar.TLabelframe")
        enroll_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        inner_enroll = ttk.Frame(enroll_frame, style="Sidebar.TFrame")
        inner_enroll.pack(fill="x", padx=10, pady=10)

        ttk.Button(inner_enroll, text="▶  Start Enrollment",
                   command=self._start_enrollment).pack(fill="x", pady=(0, 10))
        
        self.enroll_status_var = tk.StringVar(value="Status: Not enrolling")
        ttk.Label(inner_enroll, textvariable=self.enroll_status_var,
                  style="Sidebar.TLabel", foreground=FG2).pack(pady=(0, 10))

        # Multi-angle enrollment toggle
        self.multi_angle_var = tk.BooleanVar(value=True)

        ttk.Button(inner_enroll, text="📸  Capture Angle",
                   command=self._capture_enroll).pack(fill="x", pady=(0, 5))
        
        ttk.Button(inner_enroll, text="⏭️  Skip Angle",
                   command=self._skip_angle).pack(fill="x", pady=(0, 5))

        ttk.Button(inner_enroll, text="✅  Finish & Save",
                   command=self._finish_enrollment).pack(fill="x", pady=(10, 0))

        # ── Enrolled Faces List ──────────────────────────────────────────────
        faces_frame = ttk.LabelFrame(parent, text="📋 Enrolled Faces", style="Sidebar.TLabelframe")
        faces_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        inner_faces = ttk.Frame(faces_frame, style="Sidebar.TFrame")
        inner_faces.pack(fill="both", expand=True, padx=10, pady=10)

        # Adding a scrollbar for the treeview
        tree_scroll = ttk.Scrollbar(inner_faces)
        tree_scroll.pack(side="right", fill="y")
        
        self.faces_tree = ttk.Treeview(inner_faces,
                                       columns=("name", "count"),
                                       show="headings", yscrollcommand=tree_scroll.set)
        tree_scroll.config(command=self.faces_tree.yview)
        
        self.faces_tree.heading("name",  text="Name")
        self.faces_tree.heading("count", text="Angles")
        self.faces_tree.column("name",  width=180, anchor="w")
        self.faces_tree.column("count", width=60, anchor="center")
        self.faces_tree.pack(fill="both", expand=True, pady=(0, 10))

        ttk.Button(inner_faces, text="🗑  Delete Selected",
                   style="Danger.TButton",
                   command=self._delete_face).pack(fill="x")

        self._refresh_faces_list()

        # ── Quit ─────────────────────────────────────────────────────────────
        quit_frame = ttk.Frame(parent, style="Sidebar.TFrame")
        quit_frame.pack(fill="x", side="bottom", padx=20, pady=20)
        
        ttk.Button(quit_frame, text="✕  Exit System",
                   style="Danger.TButton",
                   command=self.on_closing).pack(fill="x")

    def _build_motor_dashboard(self, parent):
        """Right-side car motor telemetry panel."""
        parent.columnconfigure(0, weight=1)
        CW = 234   # inner canvas / bar width

        # ── Title ─────────────────────────────────────────────────────────────
        ttk.Label(parent, text="Car Motor Dashboard",
                  style="Sidebar.TLabel",
                  font=("Segoe UI", 13, "bold"),
                  anchor="center").pack(fill="x", pady=(18, 4), padx=12)

        ttk.Separator(parent, orient="horizontal").pack(fill="x", padx=12, pady=(0, 10))

        # ── Zone badge ────────────────────────────────────────────────────────
        self._zone_badge = tk.Label(parent, text="IDLE",
                                    bg=MotorDashboard.ZONE_COLOR["IDLE"],
                                    fg="white",
                                    font=("Segoe UI", 14, "bold"),
                                    pady=6)
        self._zone_badge.pack(fill="x", padx=12, pady=(0, 6))

        # ── Distance row ──────────────────────────────────────────────────────
        dist_row = ttk.Frame(parent, style="Sidebar.TFrame")
        dist_row.pack(fill="x", padx=16, pady=(0, 10))
        ttk.Label(dist_row, text="Distance:", style="Sidebar.TLabel",
                  foreground=FG2, font=("Segoe UI", 10)).pack(side="left")
        self._dist_var = tk.StringVar(value="-- cm")
        ttk.Label(dist_row, textvariable=self._dist_var, style="Sidebar.TLabel",
                  font=("Segoe UI", 11, "bold")).pack(side="right")

        # ── Face Position section ─────────────────────────────────────────────
        pos_frame = ttk.LabelFrame(parent, text="Face Position",
                                   style="Sidebar.TLabelframe")
        pos_frame.pack(fill="x", padx=12, pady=(0, 10))

        # Coordinate canvas  (crosshair + deadzone + face dot + arrow)
        self._coord_canvas = tk.Canvas(pos_frame, width=CW, height=110,
                                       bg=BG3, highlightthickness=0)
        self._coord_canvas.pack(padx=8, pady=(8, 4))
        self._draw_coord_canvas()   # draw idle state immediately

        # Numeric readouts
        info_grid = ttk.Frame(pos_frame, style="Sidebar.TFrame")
        info_grid.pack(fill="x", padx=12, pady=(0, 8))
        info_grid.columnconfigure(1, weight=1)

        self._pos_var  = tk.StringVar(value="cx -- / cy --")
        self._errx_var = tk.StringVar(value="--")
        self._erry_var = tk.StringVar(value="--")

        for r, (lbl, var) in enumerate([
            ("Position", self._pos_var),
            ("Error X",  self._errx_var),
            ("Error Y",  self._erry_var),
        ]):
            ttk.Label(info_grid, text=lbl, style="Sidebar.TLabel",
                      foreground=FG2, font=("Segoe UI", 9)).grid(
                      row=r, column=0, sticky="w", pady=1)
            ttk.Label(info_grid, textvariable=var, style="Sidebar.TLabel",
                      font=("Segoe UI", 10, "bold")).grid(
                      row=r, column=1, sticky="e", pady=1)

        # ── Motor Commands section ────────────────────────────────────────────
        cmd_frame = ttk.LabelFrame(parent, text="Motor Commands",
                                   style="Sidebar.TLabelframe")
        cmd_frame.pack(fill="x", padx=12, pady=(0, 10))

        bars_grid = ttk.Frame(cmd_frame, style="Sidebar.TFrame")
        bars_grid.pack(fill="x", padx=8, pady=8)
        bars_grid.columnconfigure(1, weight=1)

        self._left_spd_var  = tk.StringVar(value="0")
        self._right_spd_var = tk.StringVar(value="0")

        for r, (side, var) in enumerate([("L", self._left_spd_var),
                                          ("R", self._right_spd_var)]):
            ttk.Label(bars_grid, text=side, style="Sidebar.TLabel",
                      foreground=FG2, font=("Segoe UI", 10, "bold")).grid(
                      row=r, column=0, sticky="w", padx=(0, 6), pady=3)

            bar_canvas = tk.Canvas(bars_grid, width=CW - 56, height=18,
                                   bg=BG3, highlightthickness=0)
            bar_canvas.grid(row=r, column=1, sticky="ew", pady=3)
            if r == 0:
                self._left_bar_canvas  = bar_canvas
            else:
                self._right_bar_canvas = bar_canvas

            ttk.Label(bars_grid, textvariable=var, style="Sidebar.TLabel",
                      font=("Segoe UI", 10, "bold"), width=7).grid(
                      row=r, column=2, sticky="e", padx=(6, 0), pady=3)

        # ── Steering indicator ────────────────────────────────────────────────
        steer_frame = ttk.LabelFrame(parent, text="Steering",
                                     style="Sidebar.TLabelframe")
        steer_frame.pack(fill="x", padx=12, pady=(0, 12))

        self._steer_canvas = tk.Canvas(steer_frame, width=CW, height=36,
                                       bg=BG3, highlightthickness=0)
        self._steer_canvas.pack(padx=8, pady=8)
        self._draw_steer_canvas(0.0, "#94a3b8")

    # ── Motor display helpers ─────────────────────────────────────────────────

    def _draw_coord_canvas(self):
        c  = self._coord_canvas
        c.delete("all")
        W, H  = 234, 110
        cx, cy = W // 2, H // 2

        # Grid lines
        c.create_line(cx, 0, cx, H, fill=BG2, width=1)
        c.create_line(0, cy, W, cy, fill=BG2, width=1)

        # Dead-zone box
        SCALE_X = (W // 2 - 6) / 320.0
        SCALE_Y = (H // 2 - 6) / 240.0
        dz_px = int(MotorDashboard.DEAD_PX * SCALE_X)
        dz_py = int(MotorDashboard.DEAD_PX * SCALE_Y)
        c.create_rectangle(cx - dz_px, cy - dz_py, cx + dz_px, cy + dz_py,
                           outline="#475569", width=1, dash=(4, 3))

        m = self.motor
        if m.state == "IDLE":
            c.create_oval(cx - 4, cy - 4, cx + 4, cy + 4,
                          fill="#475569", outline="")
            return

        color = MotorDashboard.ZONE_COLOR.get(m.state, "#94a3b8")
        fx = int(cx + m.error_x * SCALE_X)
        fy = int(cy + m.error_y * SCALE_Y)
        fx = max(6, min(W - 6, fx))
        fy = max(6, min(H - 6, fy))

        # Arrow from center to face position
        if abs(m.error_x) > 4 or abs(m.error_y) > 4:
            c.create_line(cx, cy, fx, fy, fill=color, width=2,
                          arrow=tk.LAST, arrowshape=(8, 10, 4))

        # Center dot
        c.create_oval(cx - 3, cy - 3, cx + 3, cy + 3,
                      fill="#64748b", outline="")
        # Face dot
        c.create_oval(fx - 6, fy - 6, fx + 6, fy + 6,
                      fill=color, outline="white", width=1)

    def _draw_speed_bar(self, canvas: tk.Canvas, speed: int, color: str):
        canvas.delete("all")
        W = canvas.winfo_width() or (234 - 56)
        H = 18
        fill_w = int(speed / 255.0 * W)
        canvas.create_rectangle(0, 0, W, H, fill=BG2, outline="")
        if fill_w > 0:
            canvas.create_rectangle(0, 0, fill_w, H, fill=color, outline="")

    def _draw_steer_canvas(self, error_x: float, color: str):
        c  = self._steer_canvas
        c.delete("all")
        W, H = 234, 36
        cx, cy = W // 2, H // 2

        # Track line
        c.create_line(10, cy, W - 10, cy, fill="#334155", width=2)
        # Center tick
        c.create_line(cx, cy - 6, cx, cy + 6, fill="#475569", width=1)

        # Clamp and scale steering arrow
        clamped = max(-320.0, min(320.0, error_x))
        tip_x   = int(cx + clamped * ((W // 2 - 12) / 320.0))
        tip_x   = max(12, min(W - 12, tip_x))

        if abs(error_x) < MotorDashboard.DEAD_PX:
            c.create_oval(cx - 5, cy - 5, cx + 5, cy + 5,
                          fill=color, outline="")
        else:
            c.create_line(cx, cy, tip_x, cy, fill=color, width=3,
                          arrow=tk.LAST, arrowshape=(10, 12, 5))

    def _update_motor_display(self):
        """Refresh all motor dashboard widgets from current self.motor state."""
        m     = self.motor
        color = MotorDashboard.ZONE_COLOR.get(m.state, "#94a3b8")

        # Zone badge
        self._zone_badge.config(text=m.state, bg=color)

        # Distance
        if m.distance_cm < 9000:
            self._dist_var.set(f"{m.distance_cm:.0f} cm")
        else:
            self._dist_var.set("-- cm")

        # Coordinate readouts
        if m.state != "IDLE":
            sign_x = "+" if m.error_x >= 0 else ""
            sign_y = "+" if m.error_y >= 0 else ""
            self._pos_var.set(f"cx {m.cx}  /  cy {m.cy}")
            self._errx_var.set(f"{sign_x}{m.error_x:.0f} px")
            self._erry_var.set(f"{sign_y}{m.error_y:.0f} px")
        else:
            self._pos_var.set("cx --  /  cy --")
            self._errx_var.set("--")
            self._erry_var.set("--")

        # Coordinate canvas
        self._draw_coord_canvas()

        # Speed bar values — mapped to actual DC motor RPM range (0-100)
        rpm_l = int((m.left_speed / 255.0) * m.MAX_RPM)
        rpm_r = int((m.right_speed / 255.0) * m.MAX_RPM)
        self._left_spd_var.set(f"{rpm_l} rpm")
        self._right_spd_var.set(f"{rpm_r} rpm")
        self._draw_speed_bar(self._left_bar_canvas,  m.left_speed,  color)
        self._draw_speed_bar(self._right_bar_canvas, m.right_speed, color)

        # Steering canvas
        self._draw_steer_canvas(m.error_x, color)


    # =========================================================================
    # Camera loop (background thread)
    # =========================================================================

    def _start_camera(self):
        """Start camera with DirectShow backend (confirmed working)."""
        try:
            print("🚀 Starting camera with DirectShow...")
            self.status_var.set("Starting camera...")
            
            # Use DirectShow backend (confirmed working from tests)
            self.cap = cv2.VideoCapture(config.CAMERA_INDEX, cv2.CAP_DSHOW)
            
            if not self.cap.isOpened():
                raise Exception("Cannot open camera with DirectShow")
            
            # Test frame read
            ret, test_frame = self.cap.read()
            if not ret or test_frame is None:
                raise Exception("Camera opens but cannot read frames")
            
            # Configure camera settings
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.FRAME_WIDTH)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)
            self.cap.set(cv2.CAP_PROP_FPS, config.FPS_TARGET)
            
            print(f"✅ Camera ready: {test_frame.shape[1]}x{test_frame.shape[0]}")
            self.status_var.set("✅ Camera ready - Starting video...")
            
            # Start camera thread
            self.running = True
            threading.Thread(target=self._camera_loop, daemon=True).start()
            print("✅ Camera thread started")
            
        except Exception as e:
            error_msg = f"Camera failed: {e}"
            print(f"❌ {error_msg}")
            self.status_var.set(f"❌ {error_msg}")
            messagebox.showerror("Camera Error", 
                f"{error_msg}\n\nTroubleshooting:\n"
                f"1. Close other camera apps (Zoom, Teams, etc.)\n"
                f"2. Try different USB port\n"
                f"3. Check Windows camera permissions\n"
                f"4. Restart the application")

    def _camera_loop(self):
        """Camera loop with proper error handling."""
        while self.running and self.cap and self.cap.isOpened():
            try:
                start_time = time.time()
                
                # Read frame from camera
                ret, frame = self.cap.read()
                if not ret or frame is None:
                    print("❌ Failed to read camera frame")
                    self.root.after(0, self.status_var.set, "❌ Camera read failed")
                    time.sleep(0.1)  # Wait before retrying
                    continue

                # Apply camera flip using camera_utils
                from camera_utils import apply_camera_flip
                frame = apply_camera_flip(frame)
                self.current_frame = frame.copy()

                # ── Detection (every frame — BlazeFace is fast) ──────────────────
                detection_start = time.time()
                try:
                    self.face_locations = self.detector.detect_faces(frame)
                except Exception as e:
                    print(f"Face detection error: {e}")
                    self.face_locations = []
                detection_time = time.time() - detection_start

                # ── Recognition (every N frames) with preprocessing ─────────────────
                recognition_start = time.time()
                try:
                    if self.frame_count % config.PROCESS_EVERY_N_FRAMES == 0:
                        if self.face_locations:
                            # Preprocess faces before recognition
                            preprocessed_frame = frame.copy()
                            for face_box in self.face_locations:
                                top, right, bottom, left = face_box
                                face_roi = frame[top:bottom, left:right]
                                
                                # Apply preprocessing
                                face_roi = self.face_preprocessor.preprocess(face_roi)
                                preprocessed_frame[top:bottom, left:right] = face_roi
                            
                            # Run recognition on preprocessed frame
                            self.recognition_results = self.recognizer.recognize_faces(
                                preprocessed_frame, self.face_locations)
                            
                            # Apply temporal smoothing to first face
                            if self.recognition_results:
                                name, conf = self.recognition_results[0]
                                self.temporal_smoother.add_recognition(name, conf)
                                smoothed_name, smoothed_conf = self.temporal_smoother.get_smoothed_result()
                                
                                # Replace with smoothed result
                                self.recognition_results[0] = (smoothed_name, smoothed_conf)
                                
                                # Update confidence display
                                if smoothed_name != "Unknown":
                                    self.confidence_display.update(smoothed_conf)
                        else:
                            # No faces detected — flush smoother so next face
                            # starts with a clean slate (no stale votes)
                            self.temporal_smoother.reset()
                            self.recognition_results = []
                except Exception as e:
                    print(f"Face recognition error: {e}")
                    self.recognition_results = []
                recognition_time = time.time() - recognition_start
                
                # ── Quality Analysis (NEW) ───────────────────────────────────────
                self.current_quality = None
                if self.face_locations and (self.mode == "enrollment" or self.settings_manager.get("show_quality_metrics", True)):
                    try:
                        self.current_quality = self.quality_analyzer.analyze_face(frame, self.face_locations[0])
                    except Exception as e:
                        print(f"Quality analysis error: {e}")
                
                # ── Multi-angle enrollment auto-capture (NEW) ────────────────────
                if self.mode == "enrollment" and self.enroll_name and self.multi_angle_var.get():
                    try:
                        face_box = self.face_locations[0] if self.face_locations else None
                        quality_score = self.current_quality['overall_score'] if self.current_quality else 0
                        
                        if self.multi_angle_enroll.check_auto_capture(frame, face_box, quality_score):
                            # Image was auto-captured
                            self.enroll_count += 1
                            current, total = self.multi_angle_enroll.get_progress()
                            self.enroll_status_var.set(f"Enrolling: {self.enroll_name}  {current}/{total}")
                    except Exception as e:
                        print(f"Multi-angle enrollment error: {e}")

                # ── Multi-person tracking ────────────────────────────────────────
                # Removed - simplified to single-person tracking

                # ── Mode processing ───────────────────────────────────────────────
                try:
                    if self.mode == "tracking":
                        self._process_enhanced_tracking()
                        self._update_tracking_llm_event()
                        
                        # If no face found in tracking mode, spin toward last-known side
                        if not self.face_locations:
                            self.motor.search(last_error_x=self.motor.error_x)
                except Exception as e:
                    print(f"Tracking processing error: {e}")

                # ── Draw ──────────────────────────────────────────────────────────
                display = frame.copy()  # Start with frame copy
                try:
                    display = self._draw_enhanced_frame(frame)
                except Exception as e:
                    print(f"Drawing error: {e}")
                    # If drawing fails, just use the frame with basic info
                    h, w = frame.shape[:2]
                    cv2.putText(display, f"Frame: {self.frame_count}", (10, 30),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    cv2.putText(display, "Drawing error - using basic display", (10, 60),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

                # ── Convert to Tk image ───────────────────────────────────────────
                try:
                    rgb = cv2.cvtColor(display, cv2.COLOR_BGR2RGB)
                    img = Image.fromarray(rgb)
                    photo = ImageTk.PhotoImage(img)
                    self.root.after(0, self._update_video, photo)
                except Exception as e:
                    print(f"Image conversion error: {e}")

                # ── Performance tracking ──────────────────────────────────────────
                try:
                    elapsed = time.time() - start_time
                    fps = 1.0 / elapsed if elapsed > 0 else 0
                    self.fps_queue.append(fps)
                    
                    # Update performance stats
                    self._update_performance_stats(detection_time, recognition_time)
                    self.root.after(0, self._update_performance_display)
                except Exception as e:
                    print(f"Performance tracking error: {e}")

                # Refresh motor dashboard
                self.root.after(0, self._update_motor_display)

                self.frame_count += 1
                
                # Update status
                self.root.after(0, self.status_var.set, f"✅ Running - Frame {self.frame_count}")
                
            except Exception as e:
                print(f"❌ Camera loop error: {e}")
                self.root.after(0, self.status_var.set, f"❌ Error: {e}")
                time.sleep(0.1)  # Wait before retrying

    # =========================================================================
    # Multi-person tracking
    # =========================================================================

    def _update_multi_person_tracking(self):
        """Update multi-person tracking system."""
        current_time = time.time()
        max_people = self.max_people_var.get()
        
        # Match faces to existing tracked people
        matched_people = {}
        unmatched_faces = list(range(len(self.face_locations)))
        
        for person_id, person_data in self.tracked_people.items():
            if current_time - person_data['last_seen'] > 5.0:  # 5 second timeout
                continue  # Skip expired people
                
            best_match = None
    def _process_enhanced_tracking(self):
        """Enhanced tracking with Identity Lock and Zero-Lag OpenCV Tracker."""
        current_time = time.time()

        # Step 1: Process detected faces
        if self.face_locations:
            best_i = -1
            best_area = 0
            
            # IDENTITY LOCK LOGIC
            # If we don't have a locked identity, look for ANY known person
            if self.locked_identity is None:
                for i, (name, conf) in enumerate(self.recognition_results):
                    if name != "Unknown":
                        self.locked_identity = name
                        print(f"🔒 Locked on to {name}")
                        break
            
            # Find the face matching our locked identity
            if self.locked_identity is not None:
                for i, (name, conf) in enumerate(self.recognition_results):
                    if name == self.locked_identity:
                        top, right, bottom, left = self.face_locations[i]
                        a = (right - left) * (bottom - top)
                        if a > best_area:
                            best_area, best_i = a, i
            
            # If our locked person wasn't found (or we have no lock), fall back to largest face
            if best_i == -1:
                for i, (top, right, bottom, left) in enumerate(self.face_locations):
                    a = (right - left) * (bottom - top)
                    if a > best_area:
                        best_area, best_i = a, i

            if best_i != -1:
                t, r, b, l = self.face_locations[best_i]
                fw = getattr(config, 'FRAME_WIDTH', 640)
                fh = getattr(config, 'FRAME_HEIGHT', 480)
                self.motor.update((l, t, r, b), fw, fh)

                # Initialize High-Speed Tracker on this face/body box
                try:
                    w = r - l
                    h = b - t
                    pad_w = int(w * 0.5)
                    pad_h = int(h * 1.0)
                    track_box = (max(0, l - pad_w), max(0, t - pad_h // 2), 
                               min(fw - (l - pad_w), w + pad_w * 2), 
                               min(fh - (t - pad_h // 2), h + pad_h * 1.5))
                    
                    try:
                        self.cv2_tracker = cv2.TrackerKCF_create()
                    except:
                        try:
                            self.cv2_tracker = cv2.legacy.TrackerMOSSE_create()
                        except:
                            self.cv2_tracker = cv2.legacy.TrackerKCF_create()
                    
                    self.cv2_tracker.init(self.current_frame, track_box)
                    self.tracker_initialized = True
                    self.target_body_box = track_box
                except Exception as e:
                    print(f"Tracker init error: {e}")
                    self.tracker_initialized = False

                if self.servo_var.get():
                    self._do_face_tracking()
                
                self.face_lost_time = None
                self.tracking_mode = "face"
                
                name = self.recognition_results[best_i][0] if best_i < len(self.recognition_results) else "Unknown"
                self.target_identity = name
                self.tracking_status_var.set(f"✅ Tracking: {name}")
                return

        # Step 2: Face lost - fallback to High-Speed CV2 Tracker
        if self.tracking_mode == "face":
            if self.face_lost_time is None:
                self.face_lost_time = current_time
                print(f"😞 Lost face - starting {self.face_lost_timeout}s timer")
                self.tracking_status_var.set(f"⏳ Face lost - waiting...")
            
            elapsed = current_time - self.face_lost_time
            if self.body_tracking_var.get() and elapsed > self.face_lost_timeout:
                self.tracking_mode = "body"
                print(f"🔄 Switching to fast body tracking for {self.target_identity}")
                self.tracking_status_var.set(f"🎯 Body tracking: {self.target_identity}")

        # Step 3: Body tracking using OpenCV Tracker
        if self.tracking_mode == "body" and self.body_tracking_var.get():
            body_found = False
            if self.tracker_initialized and self.cv2_tracker is not None:
                try:
                    ok, bbox = self.cv2_tracker.update(self.current_frame)
                    if ok:
                        x, y, w, h = [int(v) for v in bbox]
                        self.target_body_box = (x, y, w, h)
                        body_found = True
                        if self.servo_var.get():
                            cx = x + w // 2
                            cy = y + h // 2
                            self.servo.update(cx, cy)
                            
                            fw = getattr(config, 'FRAME_WIDTH', 640)
                            fh = getattr(config, 'FRAME_HEIGHT', 480)
                            self.motor.update((x, y, x+w, y+h), fw, fh)
                except Exception as e:
                    print(f"Tracker update error: {e}")

            if body_found:
                self.tracking_status_var.set(f"🎯 Body tracking: {self.target_identity}")
            else:
                if current_time - self.face_lost_time > 5.0:
                    self.tracking_mode = "lost"
                    self.target_body_box = None
                    self.locked_identity = None  # UNLOCK so we can find someone else
                    self.tracker_initialized = False
                    self.tracking_status_var.set(f"❌ Lost: {self.target_identity}")
                    if self.servo_var.get():
                        self.motor.search()
                    print(f"❌ Lost tracking completely. Lock released.")
        elif not self.body_tracking_var.get():
            self.tracking_status_var.set("⚠️ Body tracking disabled")
            self.tracking_mode = "face"
            if current_time - (self.face_lost_time or current_time) > 5.0:
                self.locked_identity = None  # UNLOCK // 2)
                    distance = np.sqrt((body_center[0] - self.smoothed_position[0])**2 + 
                                     (body_center[1] - self.smoothed_position[1])**2)
                    
                    if distance < best_distance and distance < 300:  # Increased range
                        best_distance = distance
                        best_body = body
                
                if best_body:
                    self.target_body_box = best_body
                    bx, by, bw, bh = best_body
                    cx = bx + bw // 2
                    cy = by + bh // 2
                    self.servo.update(cx, cy)
                    print(f"🎯 Tracking body at ({cx}, {cy})")
                    return True
            
            # No previous position or no close body - use largest body
            if bodies:
                largest_body = max(bodies, key=lambda b: b[2] * b[3])
                self.target_body_box = largest_body
                bx, by, bw, bh = largest_body
                cx = bx + bw // 2
                cy = by + bh // 2
                self.servo.update(cx, cy)
                print(f"🎯 Tracking largest body at ({cx}, {cy})")
                return True
        
        except Exception as e:
            print(f"Body tracking error: {e}")
        
        self.target_body_box = None
        return False

    def _detect_and_show_bodies(self):
        """Detect bodies for visualization only (when servo is off)."""
        try:
            bodies = self._detect_bodies()
            if bodies:
                # Show largest body for visualization
                largest_body = max(bodies, key=lambda b: b[2] * b[3])
                self.target_body_box = largest_body
            else:
                self.target_body_box = None
        except Exception as e:
            print(f"Body detection error: {e}")
            self.target_body_box = None

    def _detect_bodies(self):
        """Simple body detection."""
        if self.current_frame is None:
            return []
        
        bodies = []
        
        try:
            if hasattr(self.body_detector, 'predict'):
                # YOLO detection
                results = self.body_detector(self.current_frame, verbose=False)
                for result in results:
                    boxes = result.boxes
                    if boxes is not None:
                        for box in boxes:
                            if int(box.cls) == 0 and float(box.conf) > 0.5:  # Person class
                                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                                x, y, w, h = int(x1), int(y1), int(x2-x1), int(y2-y1)
                                bodies.append((x, y, w, h))
            else:
                # HOG detection
                boxes, weights = self.body_detector.detectMultiScale(
                    self.current_frame, winStride=(8, 8), padding=(32, 32), scale=1.05
                )
                for (x, y, w, h) in boxes:
                    bodies.append((x, y, w, h))
        
        except Exception as e:
            print(f"Body detection error: {e}")
        
        return bodies

    # =========================================================================
    # Drawing
    # =========================================================================

    def _draw_enhanced_frame(self, frame: np.ndarray) -> np.ndarray:
        """Clean, simple drawing with face + body tracking."""
        try:
            display = frame.copy()
            h, w = frame.shape[:2]
            fcx, fcy = w // 2, h // 2
            
            # Multi-angle enrollment UI (NEW)
            if self.mode == "enrollment" and self.enroll_name and self.multi_angle_var.get():
                display = self.multi_angle_enroll.draw_enrollment_ui(display)
                return display

            # Crosshair at center
            cv2.line(display, (fcx - 22, fcy), (fcx + 22, fcy), (255, 60, 60), 2)
            cv2.line(display, (fcx, fcy - 22), (fcx, fcy + 22), (255, 60, 60), 2)

            # Deadzone rectangle
            cv2.rectangle(display,
                          (fcx - config.DEADZONE_X, fcy - config.DEADZONE_Y),
                          (fcx + config.DEADZONE_X, fcy + config.DEADZONE_Y),
                          (255, 60, 60), 1)

            # Draw face detection boxes
            self._draw_clean_faces(display, fcx, fcy)

            # Draw body tracking if active
            self._draw_body_tracking(display, fcx, fcy)

            # Draw status overlay
            self._draw_clean_status(display, w, h)

            return display
            
        except Exception as e:
            print(f"Drawing error: {e}")
            # Return frame with basic overlay
            display = frame.copy()
            cv2.putText(display, f"Frame: {self.frame_count}", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            return display

    def _draw_clean_faces(self, display, fcx, fcy):
        """Draw clean face detection boxes with confidence and quality."""
        try:
            if not self.face_locations:
                return
                
            for i, (top, right, bottom, left) in enumerate(self.face_locations):
                # Get recognition result
                name, conf = ("Unknown", 0.0)
                if i < len(self.recognition_results):
                    name, conf = self.recognition_results[i]

                # Color: Green for recognized, Orange for unknown
                color = (0, 255, 0) if name != "Unknown" else (0, 165, 255)

                # Draw bounding box
                cv2.rectangle(display, (left, top), (right, bottom), color, 3)

                # Prepare label
                if name != "Unknown":
                    label = f"{name}"
                else:
                    label = "Unknown"

                # Draw label background
                (lw, lh), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
                cv2.rectangle(display, (left, top - lh - 12), (left + lw + 8, top), color, -1)
                cv2.putText(display, label, (left + 4, top - 4),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                
                # Draw confidence bar (NEW)
                if name != "Unknown" and self.settings_manager.get("show_confidence", True):
                    self.confidence_display.draw_confidence_bar(display, left, bottom + 10, 
                                                               width=right-left, height=25)

                # Draw face center point
                bx = (left + right) // 2
                by = (top  + bottom) // 2
                cv2.circle(display, (bx, by), 6, color, -1)
                cv2.circle(display, (bx, by), 6, (255, 255, 255), 2)

                # Draw tracking line to frame center
                cv2.line(display, (bx, by), (fcx, fcy), color, 2)
                
                # Draw quality metrics (NEW)
                if self.current_quality and i == 0 and self.settings_manager.get("show_quality_metrics", True):
                    self._draw_quality_overlay(display, right + 10, top)

                # Coordinate label in coordinate mode
                if self.mode == "coordinate":
                    cv2.putText(display, f"({bx},{by})",
                                (bx + 10, by - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
                                
        except Exception as e:
            print(f"Face drawing error: {e}")
    
    def _draw_quality_overlay(self, display, x, y):
        """Draw quality metrics overlay (NEW)."""
        try:
            if not self.current_quality:
                return
            
            quality = self.current_quality
            
            # Quality score badge
            score_text = f"Quality: {quality['overall_score']}%"
            (tw, th), _ = cv2.getTextSize(score_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            
            cv2.rectangle(display, (x, y), (x + tw + 10, y + th + 10), (30, 30, 30), -1)
            cv2.putText(display, score_text, (x + 5, y + th + 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, quality['color'], 1)
            
            # Suggestions
            y_offset = y + th + 20
            for suggestion in quality['suggestions'][:2]:  # Show top 2
                cv2.putText(display, suggestion, (x, y_offset),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
                y_offset += 20
                
        except Exception as e:
            print(f"Quality overlay error: {e}")

    def _draw_body_tracking(self, display, fcx, fcy):
        """Draw body tracking visualization with identity."""
        try:
            if not self.target_body_box:
                return
                
            # Only show body tracking when in body mode or when face is lost
            if self.tracking_mode != "body" and self.face_locations:
                return
                
            bx, by, bw, bh = self.target_body_box
            
            # Yellow color for body tracking
            body_color = (0, 255, 255)  # Yellow in BGR
            cv2.rectangle(display, (bx, by), (bx + bw, by + bh), body_color, 3)
            
            # Body tracking label with identity
            if self.tracking_mode == "body" and self.target_identity != "Unknown":
                label = f"🎯 BODY: {self.target_identity}"
            else:
                label = "👤 BODY TRACKING"
                
            # Draw label background
            (lw, lh), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)
            cv2.rectangle(display, (bx, by - lh - 12), (bx + lw + 8, by), body_color, -1)
            cv2.putText(display, label, (bx + 4, by - 4),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
            
            # Draw center point
            center_x = bx + bw // 2
            center_y = by + bh // 2
            cv2.circle(display, (center_x, center_y), 10, body_color, -1)
            cv2.circle(display, (center_x, center_y), 10, (0, 0, 0), 2)
            
            # Draw tracking line to frame center
            cv2.line(display, (center_x, center_y), (fcx, fcy), body_color, 2)
            
        except Exception as e:
            print(f"Body tracking draw error: {e}")

    def _draw_clean_status(self, display, w, h):
        """Draw clean status information."""
        try:
            # Mode badge
            mode_colors = {
                "tracking": (124, 58, 237),    # Purple
                "enrollment": (34, 197, 94),   # Green
                "coordinate": (6, 182, 212),   # Cyan
            }
            
            mode_names = {
                "tracking": f"TRACKING - {self.tracking_mode.upper()}",
                "enrollment": "ENROLLMENT MODE",
                "coordinate": "COORDINATE MODE",
            }
            
            badge_color = mode_colors.get(self.mode, (100, 100, 100))
            badge_text = mode_names.get(self.mode, self.mode.upper())

            # Draw mode badge
            (badge_w, badge_h), _ = cv2.getTextSize(badge_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            cv2.rectangle(display, (w - badge_w - 20, 8), (w - 8, 38), badge_color, -1)
            cv2.putText(display, badge_text, (w - badge_w - 16, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

            # Show tracking target if in tracking mode
            if self.mode == "tracking" and self.target_identity != "Unknown":
                target_text = f"Target: {self.target_identity}"
                cv2.putText(display, target_text, (10, h - 70),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            # Show face lost timer when waiting for body tracking
            if self.face_lost_time and self.tracking_mode == "face" and self.body_tracking_var.get():
                elapsed = time.time() - self.face_lost_time
                remaining = max(0, self.face_lost_timeout - elapsed)
                if remaining > 0:
                    timer_text = f"Face lost - Body mode in {remaining:.1f}s"
                    cv2.putText(display, timer_text, (10, h - 40),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2)

            # Servo status
            status = self.servo.get_status()
            if status["enabled"]:
                servo_text = f"Servo: Pan {status['pan_angle']:.0f}° | Tilt {status['tilt_angle']:.0f}°"
                cv2.putText(display, servo_text, (10, h - 12),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                            
        except Exception as e:
            print(f"Status draw error: {e}")

    def _update_video(self, photo):
        self.video_label.configure(image=photo)
        self.video_label.image = photo

    # =========================================================================
    # Control callbacks
    # =========================================================================

    def _on_mode_change(self):
        """Handle mode change from radio buttons."""
        new_mode = self.mode_var.get()
        self.mode = new_mode
        
        # Update status
        mode_names = {
            "tracking": "Face Tracking",
            "enrollment": "Face Enrollment",
            "coordinate": "Coordinate Extraction"
        }
        self.status_var.set(f"✅ Mode changed to: {mode_names.get(new_mode, new_mode)}")
        
        # Reset servos when entering tracking mode
        if self.mode == "tracking":
            self.servo.reset()
            print(f"✅ Mode changed to: {new_mode}")
        
        # Clear enrollment state when leaving enrollment mode
        if new_mode != "enrollment" and self.enroll_name:
            self.enroll_name = None
            self.enroll_images = []
            self.enroll_count = 0
            self.enroll_status_var.set("Not enrolling")

    def _on_servo_toggle(self):
        if not self.servo_var.get():
            self.servo.reset()
            self.status_var.set("Servo tracking disabled")
        else:
            self.status_var.set("Servo tracking enabled")

    def _on_llm_toggle(self):
        enabled = bool(self.llm_enabled_var.get())
        self.settings_manager.set("tiny_llm_enabled", enabled)
        if self.tiny_llm is not None:
            self.tiny_llm.update_config(self._get_tiny_llm_config())
            self.llm_status_var.set(f"LLM: {self.tiny_llm.get_status()}")
        self.status_var.set("Tiny LLM enabled" if enabled else "Tiny LLM disabled")

    def _on_llm_profile_change(self, _event=None):
        profile = self.llm_profile_var.get()
        self.settings_manager.set("tiny_llm_profile", profile)
        if self.tiny_llm is not None:
            self.tiny_llm.update_config(self._get_tiny_llm_config())
            self.llm_status_var.set(f"LLM: {self.tiny_llm.get_status()}")
        self.status_var.set(f"Tiny LLM profile: {profile}")

    def _reset_servos(self):
        self.servo.reset()
        self.status_var.set("Servos reset to centre")

    def _apply_pid(self, key: str):
        """Push slider value to live PID controller."""
        val = round(self._pid_sliders[key].get(), 4)
        if key.startswith("pan"):
            param = key[4:]   # "kp" / "ki" / "kd"
            self.servo.set_pid_gains("pan",  **{param: val})
        else:
            param = key[5:]
            self.servo.set_pid_gains("tilt", **{param: val})
    
    def _on_threshold_change(self, _=None):
        """Handle recognition threshold change (NEW)."""
        threshold = round(self.threshold_var.get(), 2)
        self.recognizer.SIMILARITY_THRESHOLD = threshold
        self.settings_manager.set("recognition_threshold", threshold)
    
    def _save_settings(self):
        """Save current settings (NEW)."""
        # Save PID values
        for key, var in self._pid_sliders.items():
            self.settings_manager.set(key, var.get())
        
        # Save threshold
        self.settings_manager.set("recognition_threshold", self.threshold_var.get())
        self.settings_manager.set("tiny_llm_enabled", bool(self.llm_enabled_var.get()))
        self.settings_manager.set("tiny_llm_profile", self.llm_profile_var.get())
        self.settings_manager.set("coordinate_smoothing_window", int(self.coordinate_smoothing_window))
        
        # Save to file
        if self.settings_manager.save_settings():
            self.status_var.set("✅ Settings saved")
            messagebox.showinfo("Settings", "Settings saved successfully!")
        else:
            self.status_var.set("❌ Failed to save settings")
            messagebox.showerror("Settings", "Failed to save settings")
    
    def _reset_settings(self):
        """Reset settings to defaults (NEW)."""
        if not messagebox.askyesno("Reset Settings", "Reset all settings to defaults?"):
            return
        
        self.settings_manager.reset_to_defaults()
        self._apply_settings()
        
        # Update UI
        self.threshold_var.set(self.settings_manager.get("recognition_threshold", 0.30))
        for key, var in self._pid_sliders.items():
            var.set(self.settings_manager.get(key, config.PAN_KP))
        self.llm_enabled_var.set(bool(self.settings_manager.get("tiny_llm_enabled", config.ENABLE_TINY_LLM)))
        self.llm_profile_var.set(self.settings_manager.get("tiny_llm_profile", config.TINY_LLM_PROFILE))
        self.coordinate_smoothing_window = int(
            self.settings_manager.get("coordinate_smoothing_window", config.COORDINATE_SMOOTHING_WINDOW)
        )
        if self.tiny_llm is not None:
            self.tiny_llm.update_config(self._get_tiny_llm_config())
            self.llm_status_var.set(f"LLM: {self.tiny_llm.get_status()}")
        
        self.status_var.set("✅ Settings reset to defaults")
        messagebox.showinfo("Settings", "Settings reset to defaults!")

    # ── Enrollment ────────────────────────────────────────────────────────────

    def _start_enrollment(self):
        name = simpledialog.askstring("Enroll Face",
                                      "Enter person's name:",
                                      parent=self.root)
        if not name or not name.strip():
            return
        self.enroll_name   = name.strip()
        self.enroll_images = []
        self.enroll_count  = 0
        
        # Setup directory
        enroll_dir = Path(config.FACE_IMAGES_DIR) / self.enroll_name
        enroll_dir.mkdir(parents=True, exist_ok=True)
        
        # Start multi-angle enrollment if enabled
        if self.multi_angle_var.get():
            self.multi_angle_enroll.start_enrollment(self.enroll_name, str(enroll_dir))
            self.enroll_target = 9
            self.enroll_status_var.set(f"Enrolling: {self.enroll_name}  0/9 angles")
        else:
            self.enroll_target = 5
            self.enroll_status_var.set(f"Enrolling: {self.enroll_name}  0/{self.enroll_target}")
        
        self.status_var.set(f"Started enrollment for '{self.enroll_name}'")
        self.mode_var.set("enrollment")
        self.mode = "enrollment"

    def _capture_enroll(self):
        if not self.enroll_name:
            messagebox.showwarning("No Session", "Click 'Start Enrollment' first.")
            return
        
        if self.current_frame is None:
            return
        
        # Multi-angle enrollment
        if self.multi_angle_var.get():
            if self.multi_angle_enroll.is_complete():
                messagebox.showinfo("Done", "All angles captured — click 'Finish & Save'.")
                return
            
            if self.multi_angle_enroll.capture_current_angle(self.current_frame):
                self.enroll_count += 1
                current, total = self.multi_angle_enroll.get_progress()
                self.enroll_status_var.set(f"Enrolling: {self.enroll_name}  {current}/{total} angles")
                self.status_var.set(f"Captured angle {current}/{total}")
        else:
            # Standard enrollment
            if self.enroll_count >= self.enroll_target:
                messagebox.showinfo("Done", "Target reached — click 'Finish & Save'.")
                return
            
            path = Path(config.FACE_IMAGES_DIR) / self.enroll_name / \
                   f"{self.enroll_name}_{self.enroll_count + 1}.jpg"
            cv2.imwrite(str(path), self.current_frame)
            self.enroll_images.append(str(path))
            self.enroll_count += 1
            self.enroll_status_var.set(
                f"Enrolling: {self.enroll_name}  {self.enroll_count}/{self.enroll_target}")
            self.status_var.set(f"Captured image {self.enroll_count}/{self.enroll_target}")
    
    def _skip_angle(self):
        """Skip current angle in multi-angle enrollment (NEW)."""
        if not self.enroll_name or not self.multi_angle_var.get():
            return
        
        if self.multi_angle_enroll.skip_current_angle():
            current, total = self.multi_angle_enroll.get_progress()
            self.enroll_status_var.set(f"Enrolling: {self.enroll_name}  {current}/{total} angles")
            self.status_var.set(f"Skipped angle - {current}/{total}")

    def _finish_enrollment(self):
        if not self.enroll_name:
            messagebox.showwarning("No Images", "Start enrollment first.")
            return
        
        # Get images to enroll
        if self.multi_angle_var.get():
            images_to_enroll = self.multi_angle_enroll.get_captured_images()
            if not images_to_enroll:
                messagebox.showwarning("No Images", "Capture at least one angle first.")
                return
        else:
            if not self.enroll_images:
                messagebox.showwarning("No Images", "Capture at least one image first.")
                return
            images_to_enroll = self.enroll_images

        ok = 0
        for p in images_to_enroll:
            if self.recognizer.enroll_face(p, self.enroll_name):
                ok += 1

        if ok:
            self.recognizer.save_encodings()
            messagebox.showinfo("Enrolled",
                                f"✅  {ok} image(s) enrolled for '{self.enroll_name}'")
        else:
            messagebox.showerror("Failed",
                                 f"No faces found in captured images for '{self.enroll_name}'.\n"
                                 "Ensure your face is clearly visible and well-lit.")

        # Reset
        self.enroll_name   = None
        self.enroll_images = []
        self.enroll_count  = 0
        self.multi_angle_enroll.reset()
        self.enroll_status_var.set("Status: Not enrolling")
        self.status_var.set("Enrollment complete")
        self.mode = "tracking"
        try:
            self.mode_var.set("tracking")
        except AttributeError:
            pass
        self._refresh_faces_list()

    def _refresh_faces_list(self):
        """Rebuild the enrolled-faces treeview."""
        for row in self.faces_tree.get_children():
            self.faces_tree.delete(row)

        # Count samples per name
        from collections import Counter
        counts = Counter(self.recognizer.known_face_names)
        for name, cnt in sorted(counts.items()):
            self.faces_tree.insert("", "end", values=(name, cnt))

    def _delete_face(self):
        sel = self.faces_tree.selection()
        if not sel:
            return
        name = self.faces_tree.item(sel[0])["values"][0]
        if not messagebox.askyesno("Delete",
                                   f"Remove all encodings for '{name}'?"):
            return

        # Filter out
        pairs = [(e, n) for e, n in zip(
            self.recognizer.known_face_encodings,
            self.recognizer.known_face_names) if n != name]

        if pairs:
            encs, names = zip(*pairs)
            self.recognizer.known_face_encodings = list(encs)
            self.recognizer.known_face_names     = list(names)
        else:
            self.recognizer.known_face_encodings = []
            self.recognizer.known_face_names     = []

        self.recognizer.save_encodings()
        self._refresh_faces_list()
        self.status_var.set(f"Deleted '{name}' from database")

    # ── Coordinate extraction ─────────────────────────────────────────────────

    def _stabilize_coordinate(self, face_key: str, cx: int, cy: int):
        history = self.coord_history_by_face.get(face_key)
        if history is None:
            history = deque(maxlen=self.coordinate_smoothing_window)
            self.coord_history_by_face[face_key] = history

        history.append((cx, cy))
        avg_x = int(sum(p[0] for p in history) / len(history))
        avg_y = int(sum(p[1] for p in history) / len(history))
        return avg_x, avg_y

    def _extract_coords(self):
        if not self.face_locations:
            messagebox.showinfo("No Faces", "No faces detected in current frame.")
            return

        self.extracted_coords = []
        self.coord_text.delete("1.0", tk.END)

        for i, (top, right, bottom, left) in enumerate(self.face_locations):
            cx = (left + right) // 2
            cy = (top  + bottom) // 2
            name = "Unknown"
            if i < len(self.recognition_results):
                name = self.recognition_results[i][0]

            face_key = f"{name}:{i}"
            sx, sy = self._stabilize_coordinate(face_key, cx, cy)

            frame_h, frame_w = self.current_frame.shape[:2] if self.current_frame is not None else (1, 1)
            entry = {
                "name": name,
                "center": (cx, cy),
                "stabilized_center": (sx, sy),
                "normalized_center": (round(sx / max(frame_w, 1), 4), round(sy / max(frame_h, 1), 4)),
                "bbox": (top, right, bottom, left),
            }
            self.extracted_coords.append(entry)

            self.coord_text.insert(tk.END,
                f"Face {i+1}: {name}\n"
                f"  Centre : ({cx}, {cy})\n"
                f"  Stable : ({sx}, {sy})\n"
                f"  Norm   : ({entry['normalized_center'][0]}, {entry['normalized_center'][1]})\n"
                f"  BBox   : T{top} R{right} B{bottom} L{left}\n\n")

        self.status_var.set(f"Extracted {len(self.extracted_coords)} face coordinate(s)")
        self._queue_llm_event(
            "coordinate_snapshot",
            f"extracted={len(self.extracted_coords)} mode={self.mode} smoothing_window={self.coordinate_smoothing_window}",
        )

    def _export_coords(self):
        if not self.extracted_coords:
            messagebox.showinfo("No Coordinates", "Extract coordinates first.")
            return

        export_dir = Path("captures")
        export_dir.mkdir(parents=True, exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        export_path = export_dir / f"coordinates_{timestamp}.csv"

        with export_path.open("w", newline="", encoding="utf-8") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow([
                "name",
                "center_x",
                "center_y",
                "stable_x",
                "stable_y",
                "norm_x",
                "norm_y",
                "top",
                "right",
                "bottom",
                "left",
            ])
            for entry in self.extracted_coords:
                top, right, bottom, left = entry["bbox"]
                center_x, center_y = entry["center"]
                stable_x, stable_y = entry["stabilized_center"]
                norm_x, norm_y = entry["normalized_center"]
                writer.writerow([
                    entry["name"],
                    center_x,
                    center_y,
                    stable_x,
                    stable_y,
                    norm_x,
                    norm_y,
                    top,
                    right,
                    bottom,
                    left,
                ])

        self.status_var.set(f"Coordinates exported: {export_path}")

    def _clear_coords(self):
        self.extracted_coords = []
        self.coord_history_by_face = {}
        self.coord_text.delete("1.0", tk.END)
        self.status_var.set("Coordinates cleared")

    # =========================================================================
    # Cleanup
    # =========================================================================

    def on_closing(self):
        self.running = False
        if self.cap:
            self.cap.release()
        self.servo.reset()
        self.root.destroy()


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main():
    root = tk.Tk()
    app  = FaceTrackingGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
