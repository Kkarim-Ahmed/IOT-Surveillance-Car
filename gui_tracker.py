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
        self.temporal_smoother = TemporalRecognitionSmoothing(window_size=10, min_agreement=0.6)
        self.face_preprocessor = FacePreprocessor(enable_denoising=True, enable_sharpening=True)
        self.face_aligner = FaceAligner()
        self.multi_crop = MultiCropRecognition()
        self.enhanced_body_tracker = EnhancedBodyTracker()
        self.motion_tracker = MotionPatternTracker()
        
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
        """Initialize simple body detection."""
        try:
            # Try YOLO first
            from ultralytics import YOLO
            self.body_detector = YOLO('yolov8n.pt')
            print("✅ YOLO body detection loaded")
        except:
            # Fallback to HOG
            self.body_detector = cv2.HOGDescriptor()
            self.body_detector.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
            print("✅ HOG body detection loaded")
    
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

        # 1 column for sidebar, 1 for video. Video gets all the weight.
        self.root.columnconfigure(0, weight=0)
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=0)

        # Left sidebar (slim)
        sidebar = ttk.Frame(self.root, width=320, style="Sidebar.TFrame")
        sidebar.grid(row=0, column=0, rowspan=2, sticky="nsew")
        sidebar.grid_propagate(False)
        self._build_sidebar(sidebar)

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
            best_distance = float('inf')
            
            for i in unmatched_faces:
                if i >= len(self.face_locations):
                    continue
                    
                top, right, bottom, left = self.face_locations[i]
                face_center = ((left + right) // 2, (top + bottom) // 2)
                
                # Calculate distance to last known position
                last_pos = person_data['last_pos']
                if last_pos:
                    distance = np.sqrt((face_center[0] - last_pos[0])**2 + 
                                     (face_center[1] - last_pos[1])**2)
                    
                    if distance < best_distance and distance < 150:  # Max 150 pixels
                        best_distance = distance
                        best_match = i
            
            if best_match is not None:
                matched_people[person_id] = best_match
                unmatched_faces.remove(best_match)
        
        # Update matched people
        for person_id, face_idx in matched_people.items():
            if face_idx < len(self.recognition_results):
                name, confidence = self.recognition_results[face_idx]
            else:
                name, confidence = "Unknown", 0.0
                
            top, right, bottom, left = self.face_locations[face_idx]
            center = ((left + right) // 2, (top + bottom) // 2)
            
            self.tracked_people[person_id].update({
                'name': name,
                'confidence': confidence,
                'last_pos': center,
                'last_seen': current_time,
                'bbox': (left, top, right - left, bottom - top)
            })
        
        # Add new people for unmatched faces (up to max limit)
        current_count = len([p for p in self.tracked_people.values() 
                           if current_time - p['last_seen'] < 5.0])
        
        for face_idx in unmatched_faces:
            if current_count >= max_people:
                break
                
            if face_idx < len(self.recognition_results):
                name, confidence = self.recognition_results[face_idx]
            else:
                name, confidence = "Unknown", 0.0
                
            top, right, bottom, left = self.face_locations[face_idx]
            center = ((left + right) // 2, (top + bottom) // 2)
            
            person_id = self.next_person_id
            self.next_person_id += 1
            
            self.tracked_people[person_id] = {
                'name': name,
                'confidence': confidence,
                'last_pos': center,
                'last_seen': current_time,
                'color': self._get_person_color(person_id),
                'bbox': (left, top, right - left, bottom - top)
            }
            current_count += 1
        
        # Clean up expired people
        expired_ids = [pid for pid, data in self.tracked_people.items()
                      if current_time - data['last_seen'] > 5.0]
        for pid in expired_ids:
            del self.tracked_people[pid]

    def _process_enhanced_tracking(self):
        """Enhanced tracking with face + body tracking and identity persistence."""
        current_time = time.time()

        # Step 1: Try face tracking first
        if self.face_locations:
            # Face detected - do face tracking
            if self.servo_var.get():
                self._do_face_tracking()
            
            # Reset face lost timer and update identity
            self.face_lost_time = None
            self.tracking_mode = "face"
            
            # Update target identity from recognition
            if self.recognition_results:
                name, conf = self.recognition_results[0]
                if name != "Unknown":
                    self.target_identity = name
                    self.tracking_status_var.set(f"✅ Tracking: {name} (Face)")
                else:
                    self.tracking_status_var.set(f"👤 Tracking: Unknown (Face)")
            
            return

        # Step 2: No faces detected - handle face loss
        if self.tracking_mode == "face":
            if self.face_lost_time is None:
                self.face_lost_time = current_time
                print(f"😞 Lost face - starting {self.face_lost_timeout}s timer")
                self.tracking_status_var.set(f"⏳ Face lost - waiting...")
            
            elapsed = current_time - self.face_lost_time
            if self.body_tracking_var.get() and elapsed > self.face_lost_timeout:
                self.tracking_mode = "body"
                print(f"🔄 Switching to body tracking for {self.target_identity}")
                self.tracking_status_var.set(f"🎯 Body tracking: {self.target_identity}")

        # Step 3: Body tracking with identity persistence
        if self.tracking_mode == "body" and self.body_tracking_var.get():
            if self.servo_var.get():
                body_found = self._do_body_tracking()
                if body_found:
                    self.tracking_status_var.set(f"🎯 Body tracking: {self.target_identity}")
                else:
                    if current_time - self.face_lost_time > 8.0:
                        self.tracking_mode = "lost"
                        self.target_body_box = None
                        self.tracking_status_var.set(f"❌ Lost: {self.target_identity}")
                        print(f"❌ Lost tracking completely")
            else:
                self._detect_and_show_bodies()
                if self.target_body_box:
                    self.tracking_status_var.set(f"👁️ Body visible: {self.target_identity}")
        elif not self.body_tracking_var.get():
            self.tracking_status_var.set("⚠️ Body tracking disabled")
            self.tracking_mode = "face"
            self.target_identity = self.recognition_results[0][0] if self.recognition_results else "Unknown"
            return

        # Step 2: No faces detected - handle face loss
        if self.tracking_mode == "face":
            if self.face_lost_time is None:
                self.face_lost_time = current_time
                print(f"😞 Lost {self.target_identity} - starting {self.face_lost_timeout}s timer")
            
            elapsed = current_time - self.face_lost_time
            if self.body_tracking_var.get() and elapsed > self.face_lost_timeout:
                self.tracking_mode = "body"
                print(f"🔄 Switching to body tracking for {self.target_identity}")

        # Step 3: Body tracking with identity persistence
        if self.tracking_mode == "body" and self.body_tracking_var.get():
            if self.servo_var.get():
                body_found = self._do_body_tracking()
                if not body_found:
                    if current_time - self.face_lost_time > 8.0:
                        self.tracking_mode = "lost"
                        self.target_body_box = None
                        print(f"❌ Lost tracking of {self.target_identity} completely")
            else:
                self._detect_and_show_bodies()

    def _select_best_target(self):
        """Select the best person to track."""
        if not self.tracked_people:
            return None
            
        # Priority: known people > current target > largest face
        current_time = time.time()
        active_people = {pid: data for pid, data in self.tracked_people.items()
                        if current_time - data['last_seen'] < 1.0}
        
        if not active_people:
            return None
            
        # If we have a current target, stick with them
        if self.current_target_id and self.current_target_id in active_people:
            return active_people[self.current_target_id]
        
        # Prefer known people
        known_people = {pid: data for pid, data in active_people.items()
                       if data['name'] != "Unknown"}
        
        if known_people:
            # Select known person with highest confidence
            best_person = max(known_people.values(), key=lambda p: p['confidence'])
            self.current_target_id = next(pid for pid, data in known_people.items() 
                                        if data == best_person)
            return best_person
        
        # Fall back to largest face
        best_person = max(active_people.values(), 
                         key=lambda p: p['bbox'][2] * p['bbox'][3])
        self.current_target_id = next(pid for pid, data in active_people.items() 
                                    if data == best_person)
        return best_person

    def _do_face_tracking_with_identity(self, person_data):
        """Face tracking with identity information."""
        bbox = person_data['bbox']
        cx = bbox[0] + bbox[2] // 2
        cy = bbox[1] + bbox[3] // 2
        
        # Store identity
        self.target_identity = person_data['name']
        
        # Apply smoothing and update servo
        if self.smoothed_position is None:
            self.smoothed_position = (cx, cy)
        else:
            a = config.SMOOTHING_FACTOR
            sx = int(a * cx + (1 - a) * self.smoothed_position[0])
            sy = int(a * cy + (1 - a) * self.smoothed_position[1])
            self.smoothed_position = (sx, sy)

        if self.servo_var.get():
            self.servo.update(*self.smoothed_position)

    def _auto_select_target(self):
        """Auto-select the best target to track."""
        target = self._select_best_target()
        if target:
            self.status_var.set(f"Auto-selected target: {target['name']}")
        else:
            self.status_var.set("No suitable target found")

    def _clear_all_targets(self):
        """Clear all tracked people."""
        self.tracked_people.clear()
        self.current_target_id = None
        self.target_identity = "Unknown"
        self.status_var.set("All targets cleared")

    def _update_performance_display(self):
        """Update the FPS display only."""
        try:
            stats = self.perf_stats
            
            # Update FPS display safely
            fps_value = stats.get('fps', 0)
            self.fps_var.set(f"FPS: {fps_value:.1f}")
            
        except Exception as e:
            print(f"Performance display error: {e}")

    # =========================================================================
    # Mode processing (legacy methods for compatibility)
    # =========================================================================

    def _process_tracking(self):
        """Legacy method - redirects to enhanced tracking."""
        self._process_enhanced_tracking()

    def _do_face_tracking(self):
        """Original face tracking logic."""
        # Largest face
        best_i, best_area = 0, 0
        for i, (top, right, bottom, left) in enumerate(self.face_locations):
            a = (right - left) * (bottom - top)
            if a > best_area:
                best_area, best_i = a, i

        top, right, bottom, left = self.face_locations[best_i]
        cx = (left + right) // 2
        cy = (top  + bottom) // 2

        # Exponential smoothing
        if self.smoothed_position is None:
            self.smoothed_position = (cx, cy)
        else:
            a  = config.SMOOTHING_FACTOR
            sx = int(a * cx + (1 - a) * self.smoothed_position[0])
            sy = int(a * cy + (1 - a) * self.smoothed_position[1])
            self.smoothed_position = (sx, sy)

        self.servo.update(*self.smoothed_position)

    def _do_body_tracking(self):
        """Simple body tracking when face is lost."""
        try:
            bodies = self._detect_bodies()
            
            if not bodies:
                self.target_body_box = None
                return False
            
            # Use closest body to last known position or largest body
            if self.smoothed_position:
                # Find closest body to last face position
                best_body = None
                best_distance = float('inf')
                
                for body in bodies:
                    bx, by, bw, bh = body
                    body_center = (bx + bw // 2, by + bh // 2)
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
