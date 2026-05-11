"""
Raspi/AI — Face Recognition System
Perfect dark-theme tkinter GUI.

Run:
    python main.py
    python main.py --pi          # Raspberry Pi (picamera2 + servo)
    python main.py --mode track  # start in tracking mode
    python main.py --camera 1   # use camera index 1
"""

import sys
import os
import time
import queue
import threading
import argparse
import logging

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

import config

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from PIL import Image, ImageTk
import cv2
import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("main")

# ── Dark theme palette ────────────────────────────────────────────────────────
BG        = "#0d1117"    # window background
PANEL     = "#161b22"    # card / panel background
BORDER    = "#21262d"    # card border / divider
SURFACE   = "#1c2128"    # subtle raised surface
TEXT      = "#e6edf3"    # primary text
TEXT_DIM  = "#8b949e"    # secondary / dim text
GREEN     = "#3fb950"    # known face / success
RED       = "#f85149"    # unknown / error
BLUE      = "#58a6ff"    # accent / info
ORANGE    = "#d29922"    # tracking mode / warning
BTN_GREEN = "#238636"
BTN_RED   = "#b91c1c"
BTN_BLUE  = "#1f6feb"
BTN_HOVER = "#30363d"


def _style_btn(btn: tk.Button, bg: str = BTN_BLUE, fg: str = TEXT, font_size: int = 10):
    btn.configure(
        bg=bg, fg=fg, activebackground=BTN_HOVER, activeforeground=TEXT,
        relief="flat", bd=0, cursor="hand2",
        font=("Segoe UI", font_size, "bold"),
        padx=12, pady=6,
    )


# ════════════════════════════════════════════════════════════════════════════
# Enrollment dialog
# ════════════════════════════════════════════════════════════════════════════

class EnrollDialog(tk.Toplevel):
    """Live-camera face capture dialog."""

    CAPTURE_COUNT = 15   # photos to capture

    def __init__(self, parent, pipeline, on_done):
        super().__init__(parent)
        self._pipeline  = pipeline
        self._on_done   = on_done
        self._name      = ""
        self._saved     = 0
        self._auto      = False
        self._auto_last = 0.0
        self._cap       = None
        self._running   = True

        self.title("Enroll New Face")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.grab_set()

        self._build_ui()
        self._ask_name()

    def _ask_name(self):
        name = simpledialog.askstring(
            "Name", "Enter person's name:", parent=self
        )
        if not name or not name.strip():
            self.destroy()
            return
        self._name = name.strip()
        self.title(f"Enroll — {self._name}")
        self._start_camera()

    def _build_ui(self):
        # Video canvas
        self._canvas = tk.Canvas(
            self, width=480, height=360, bg="#000", highlightthickness=0
        )
        self._canvas.pack(padx=16, pady=(16, 8))

        # Progress bar area
        prog_frame = tk.Frame(self, bg=BG)
        prog_frame.pack(fill="x", padx=16)

        self._prog_var = tk.DoubleVar(value=0)
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Enroll.Horizontal.TProgressbar",
                         troughcolor=PANEL, background=GREEN, thickness=8)
        ttk.Progressbar(prog_frame, variable=self._prog_var,
                        maximum=self.CAPTURE_COUNT, length=480,
                        style="Enroll.Horizontal.TProgressbar").pack(pady=4)

        self._status_var = tk.StringVar(value="Press CAPTURE or AUTO to start")
        tk.Label(prog_frame, textvariable=self._status_var,
                 bg=BG, fg=TEXT_DIM, font=("Segoe UI", 9)).pack(pady=2)

        # Buttons
        btn_frame = tk.Frame(self, bg=BG)
        btn_frame.pack(pady=12)

        self._cap_btn = tk.Button(btn_frame, text="📸  CAPTURE",
                                   command=self._capture)
        _style_btn(self._cap_btn, bg=BTN_GREEN)
        self._cap_btn.pack(side="left", padx=8)

        self._auto_btn = tk.Button(btn_frame, text="⚡  AUTO",
                                    command=self._toggle_auto)
        _style_btn(self._auto_btn, bg=BTN_BLUE)
        self._auto_btn.pack(side="left", padx=8)

        tk.Button(btn_frame, text="✕  Cancel",
                  command=self.destroy).configure(
            bg=BTN_RED, fg=TEXT, relief="flat", bd=0, cursor="hand2",
            font=("Segoe UI", 10, "bold"), padx=12, pady=6
        )
        tk.Button(btn_frame, text="✕  Cancel",
                  command=self.destroy).pack(side="left", padx=8)
        # Redo last button
        btn_frame.winfo_children()[-1].configure(
            bg=BTN_RED, fg=TEXT, relief="flat", bd=0, cursor="hand2",
            font=("Segoe UI", 10, "bold"), padx=12, pady=6
        )

    def _start_camera(self):
        self._vcap = cv2.VideoCapture(config.CAMERA_INDEX)
        self._update_frame()

    def _update_frame(self):
        if not self._running:
            return
        ok, frame = self._vcap.read()
        if ok:
            if config.FLIP_H:
                frame = cv2.flip(frame, 1)
            # Auto-capture
            if self._auto and (time.perf_counter() - self._auto_last) >= 0.5:
                self._do_capture(frame)

            # Draw face boxes
            small = cv2.resize(frame, (config.AI_W, config.AI_H))
            from core.detector import FaceDetector
            if not hasattr(self, "_det"):
                self._det = FaceDetector()
            dets = self._det.detect(small)
            sx = frame.shape[1] / config.AI_W
            sy = frame.shape[0] / config.AI_H
            for d in dets:
                x1,y1,x2,y2 = [int(v*(sx if i%2==0 else sy)) for i,v in enumerate(d["bbox"])]
                cv2.rectangle(frame, (x1,y1), (x2,y2), (50,220,50), 2)

            # Resize to canvas
            h, w = frame.shape[:2]
            canvas_w, canvas_h = 480, 360
            scale = min(canvas_w/w, canvas_h/h)
            disp = cv2.resize(frame, (int(w*scale), int(h*scale)))
            disp_rgb = cv2.cvtColor(disp, cv2.COLOR_BGR2RGB)
            img = ImageTk.PhotoImage(Image.fromarray(disp_rgb))
            self._canvas.create_image(0, 0, anchor="nw", image=img)
            self._canvas._img = img   # prevent GC

        if self._running:
            self.after(33, self._update_frame)

    def _capture(self):
        ok, frame = self._vcap.read()
        if ok:
            if config.FLIP_H:
                frame = cv2.flip(frame, 1)
            self._do_capture(frame)

    def _do_capture(self, frame: np.ndarray):
        if self._saved >= self.CAPTURE_COUNT:
            return
        ok = self._pipeline.enroll(frame, self._name)
        if ok:
            self._saved += 1
            self._auto_last = time.perf_counter()
            pct = int(self._saved / self.CAPTURE_COUNT * 100)
            self._prog_var.set(self._saved)
            self._status_var.set(f"Captured {self._saved}/{self.CAPTURE_COUNT}  ({pct}%)")

            # Also save to dataset directory
            save_dir = os.path.join(config.DATASET_DIR, self._name)
            os.makedirs(save_dir, exist_ok=True)
            existing = len(os.listdir(save_dir))
            cv2.imwrite(os.path.join(save_dir, f"face_{existing:04d}.jpg"), frame)

            if self._saved >= self.CAPTURE_COUNT:
                self._pipeline.save_encodings()
                self._status_var.set(f"✓ Done! {self._name} enrolled with {self._saved} photos")
                self._auto = False
                self._auto_btn.configure(text="⚡  AUTO", bg=BTN_BLUE)
                self._cap_btn.configure(state="disabled")
                self.after(1500, self._finish)

    def _toggle_auto(self):
        self._auto = not self._auto
        if self._auto:
            self._auto_btn.configure(text="⏹  STOP AUTO", bg=BTN_RED)
            self._auto_last = 0.0
        else:
            self._auto_btn.configure(text="⚡  AUTO", bg=BTN_BLUE)

    def _finish(self):
        self._running = False
        self._vcap.release()
        if self._on_done:
            self._on_done()
        self.destroy()

    def destroy(self):
        self._running = False
        try:
            self._vcap.release()
        except Exception:
            pass
        super().destroy()


# ════════════════════════════════════════════════════════════════════════════
# Settings dialog
# ════════════════════════════════════════════════════════════════════════════

class SettingsDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Settings")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.grab_set()

        self._vars = {}
        fields = [
            ("Recognition Threshold", "RECOG_THRESHOLD", 0.0, 1.0, 0.05),
            ("Detection Confidence",  "DETECT_CONFIDENCE", 0.1, 1.0, 0.05),
            ("Recognise Every N Frames", "RECOG_EVERY_N", 1, 20, 1),
            ("Max Frames Lost (tracking)", "MAX_FRAMES_LOST", 5, 60, 1),
        ]

        tk.Label(self, text="Settings", bg=BG, fg=TEXT,
                 font=("Segoe UI", 13, "bold")).pack(pady=(16, 8))

        for label, attr, mn, mx, step in fields:
            row = tk.Frame(self, bg=BG)
            row.pack(fill="x", padx=24, pady=4)
            tk.Label(row, text=label, bg=BG, fg=TEXT_DIM,
                     width=30, anchor="w", font=("Segoe UI", 10)).pack(side="left")
            var = tk.DoubleVar(value=getattr(config, attr))
            self._vars[attr] = var
            tk.Spinbox(row, from_=mn, to=mx, increment=step,
                       textvariable=var, width=8, bg=PANEL, fg=TEXT,
                       insertbackground=TEXT, relief="flat",
                       font=("Segoe UI", 10)).pack(side="right")

        btn_frame = tk.Frame(self, bg=BG)
        btn_frame.pack(pady=16)
        save_btn = tk.Button(btn_frame, text="Save", command=self._save)
        _style_btn(save_btn, bg=BTN_GREEN)
        save_btn.pack(side="left", padx=8)
        tk.Button(btn_frame, text="Cancel", command=self.destroy,
                  bg=PANEL, fg=TEXT_DIM, relief="flat", bd=0, cursor="hand2",
                  font=("Segoe UI", 10), padx=12, pady=6).pack(side="left", padx=8)

    def _save(self):
        for attr, var in self._vars.items():
            val = var.get()
            if attr == "RECOG_EVERY_N" or attr == "MAX_FRAMES_LOST":
                setattr(config, attr, int(val))
            else:
                setattr(config, attr, float(val))
        messagebox.showinfo("Settings", "Settings saved for this session.", parent=self)
        self.destroy()


# ════════════════════════════════════════════════════════════════════════════
# Face card widget
# ════════════════════════════════════════════════════════════════════════════

class FaceCard(tk.Frame):
    """A single row in the "detected faces" sidebar list."""

    def __init__(self, parent, name: str, conf: float, known: bool, on_delete=None):
        super().__init__(parent, bg=PANEL, pady=6, padx=10)

        dot_col = GREEN if known else RED
        tk.Label(self, text="●", bg=PANEL, fg=dot_col,
                 font=("Segoe UI", 10)).pack(side="left")

        name_col = TEXT if known else RED
        tk.Label(self, text=name, bg=PANEL, fg=name_col,
                 font=("Segoe UI", 10, "bold"), width=14, anchor="w").pack(side="left", padx=(4, 0))

        if known and conf > 0:
            conf_text = f"{conf:.0%}"
            bar_w = int(conf * 60)
            tk.Label(self, text=conf_text, bg=PANEL, fg=TEXT_DIM,
                     font=("Segoe UI", 9)).pack(side="left", padx=4)

        if on_delete and known:
            tk.Button(self, text="✕", command=lambda: on_delete(name),
                      bg=PANEL, fg=RED, relief="flat", bd=0, cursor="hand2",
                      font=("Segoe UI", 9)).pack(side="right")


# ════════════════════════════════════════════════════════════════════════════
# Main application window
# ════════════════════════════════════════════════════════════════════════════

class App(tk.Tk):
    """
    Layout:
    ┌─────────────────────────────────────────────┐
    │  Header (title + status dot)                │
    ├──────────────────────┬──────────────────────┤
    │                      │  MODE BUTTONS        │
    │   VIDEO PANEL        │  ─────────────────   │
    │   640 × 480          │  DETECTED FACES      │
    │                      │  (scrollable list)   │
    │                      │  ─────────────────   │
    │                      │  SYSTEM STATS        │
    │                      │  ─────────────────   │
    │                      │  ACTION BUTTONS      │
    ├──────────────────────┴──────────────────────┤
    │  Status bar                                 │
    └─────────────────────────────────────────────┘
    """

    def __init__(self, pipeline, result_queue: queue.Queue):
        super().__init__()
        self._pipeline    = pipeline
        self._result_q    = result_queue
        self._last_tracks = []

        self.title("Raspi AI · Face Recognition")
        self.configure(bg=BG)
        self.geometry(f"{config.WIN_W}x{config.WIN_H}")
        self.minsize(900, 560)

        # Stats vars
        self._mode_var   = tk.StringVar(value="DETECT")
        self._fps_var    = tk.StringVar(value="0.0")
        self._cam_fps_var= tk.StringVar(value="0.0")
        self._cpu_var    = tk.StringVar(value="–")
        self._mem_var    = tk.StringVar(value="–")
        self._face_cnt   = tk.StringVar(value="0")
        self._status_var = tk.StringVar(value="Starting…")
        self._backend_var= tk.StringVar(value="–")

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # Start update loop
        self._photo_ref = None  # prevent GC
        self.after(100, self._update_stats_loop)
        self.after(33,  self._update_frame)

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        self._build_header()

        content = tk.Frame(self, bg=BG)
        content.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        content.grid_columnconfigure(0, weight=0)
        content.grid_columnconfigure(1, weight=1)
        content.grid_rowconfigure(0, weight=1)

        self._build_video_panel(content)
        self._build_sidebar(content)
        self._build_statusbar()

    def _build_header(self):
        hdr = tk.Frame(self, bg=PANEL, height=50)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        tk.Label(hdr, text="🤖  Raspi AI", bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 15, "bold")).pack(side="left", padx=16)

        tk.Label(hdr, text="Face Recognition System", bg=PANEL, fg=TEXT_DIM,
                 font=("Segoe UI", 10)).pack(side="left")

        # Backend badge
        self._backend_lbl = tk.Label(hdr, textvariable=self._backend_var,
                                      bg="#1f6feb22", fg=BLUE,
                                      font=("Segoe UI", 9, "bold"),
                                      padx=8, pady=2)
        self._backend_lbl.pack(side="right", padx=16)

    def _build_video_panel(self, parent):
        vid_frame = tk.Frame(parent, bg=BORDER, bd=1, relief="solid")
        vid_frame.grid(row=0, column=0, sticky="ns", padx=(0, 10))

        self._video_lbl = tk.Label(vid_frame, bg="#000",
                                    width=config.VIDEO_PANEL_W,
                                    height=config.VIDEO_PANEL_H)
        self._video_lbl.pack()

    def _build_sidebar(self, parent):
        sb = tk.Frame(parent, bg=BG)
        sb.grid(row=0, column=1, sticky="nsew")
        sb.grid_rowconfigure(2, weight=1)

        # ── MODE BUTTONS ──────────────────────────────────────────────────────
        mode_card = self._card(sb, "MODE")
        mode_card.pack(fill="x", pady=(0, 8))

        btn_row = tk.Frame(mode_card, bg=PANEL)
        btn_row.pack(fill="x", pady=4)

        self._detect_btn = tk.Button(
            btn_row, text="👁  DETECT", command=self._set_detect,
        )
        _style_btn(self._detect_btn, bg=BTN_GREEN)
        self._detect_btn.pack(side="left", expand=True, fill="x", padx=(0, 4))

        self._track_btn = tk.Button(
            btn_row, text="🎯  TRACK", command=self._set_track,
        )
        _style_btn(self._track_btn, bg=SURFACE)
        self._track_btn.pack(side="left", expand=True, fill="x", padx=(4, 0))

        self._mode_lbl = tk.Label(
            mode_card,
            textvariable=self._mode_var,
            bg=PANEL, fg=GREEN,
            font=("Segoe UI", 11, "bold"),
        )
        self._mode_lbl.pack(pady=(0, 4))

        # ── DETECTED FACES ────────────────────────────────────────────────────
        face_card = self._card(sb, "DETECTED FACES")
        face_card.pack(fill="both", expand=True, pady=(0, 8))

        self._face_count_lbl = tk.Label(
            face_card, textvariable=self._face_cnt,
            bg=PANEL, fg=TEXT_DIM, font=("Segoe UI", 9),
        )
        self._face_count_lbl.pack(anchor="e", padx=4)

        self._face_scroll = tk.Frame(face_card, bg=PANEL)
        self._face_scroll.pack(fill="both", expand=True)

        # ── SYSTEM STATS ──────────────────────────────────────────────────────
        stats_card = self._card(sb, "SYSTEM")
        stats_card.pack(fill="x", pady=(0, 8))

        stats = [
            ("AI FPS",     self._fps_var,     BLUE),
            ("Camera FPS", self._cam_fps_var,  TEXT_DIM),
            ("CPU",        self._cpu_var,      TEXT_DIM),
            ("Memory",     self._mem_var,      TEXT_DIM),
        ]
        self._stat_labels = {}
        for label, var, col in stats:
            row = tk.Frame(stats_card, bg=PANEL)
            row.pack(fill="x", pady=1)
            tk.Label(row, text=label, bg=PANEL, fg=TEXT_DIM,
                     font=("Segoe UI", 9), width=12, anchor="w").pack(side="left")
            lbl = tk.Label(row, textvariable=var, bg=PANEL, fg=col,
                           font=("Segoe UI", 9, "bold"), anchor="e")
            lbl.pack(side="right")
            self._stat_labels[label] = lbl

        # ── ACTION BUTTONS ────────────────────────────────────────────────────
        action_card = self._card(sb, "ACTIONS")
        action_card.pack(fill="x")

        btn_defs = [
            ("➕  Enroll New Face",     self._enroll,   BTN_GREEN),
            ("🗑  Remove Person",       self._remove,   BTN_RED),
            ("🔄  Reload Encodings",    self._reload,   BTN_BLUE),
            ("⚙  Settings",            self._settings, SURFACE),
        ]
        for text, cmd, bg in btn_defs:
            b = tk.Button(action_card, text=text, command=cmd)
            _style_btn(b, bg=bg)
            b.pack(fill="x", pady=2)

    def _build_statusbar(self):
        bar = tk.Frame(self, bg=PANEL, height=30)
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)

        self._status_dot = tk.Label(bar, text="●", bg=PANEL, fg=GREEN,
                                     font=("Segoe UI", 10))
        self._status_dot.pack(side="left", padx=(12, 4))

        tk.Label(bar, textvariable=self._status_var, bg=PANEL, fg=TEXT_DIM,
                 font=("Segoe UI", 9)).pack(side="left")

        tk.Label(bar, text="Raspi/AI v2.0 · TFLite",
                 bg=PANEL, fg=BORDER, font=("Segoe UI", 8)).pack(side="right", padx=12)

    def _card(self, parent, title: str) -> tk.Frame:
        outer = tk.Frame(parent, bg=BORDER, bd=1, relief="solid")
        inner = tk.Frame(outer, bg=PANEL, padx=10, pady=8)
        inner.pack(fill="both", expand=True, padx=1, pady=1)
        tk.Label(inner, text=title, bg=PANEL, fg=TEXT_DIM,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(0, 4))
        tk.Frame(inner, bg=BORDER, height=1).pack(fill="x", pady=(0, 6))
        return inner

    # ── Frame update loop ─────────────────────────────────────────────────────

    def _update_frame(self):
        try:
            result = self._result_q.get_nowait()
            frame  = result.get("frame")
            tracks = result.get("tracks", [])
            mode   = result.get("mode", "DETECT")

            if frame is not None:
                # Convert BGR→RGB and display
                rgb  = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img  = Image.fromarray(rgb)
                photo = ImageTk.PhotoImage(img)
                self._video_lbl.configure(image=photo)
                self._photo_ref = photo

            # Update mode label colour
            self._mode_var.set(mode)
            col = GREEN if mode == "DETECT" else ORANGE
            self._mode_lbl.configure(fg=col)

            # Update detected faces
            self._last_tracks = tracks
            self._refresh_face_list(tracks)
            self._face_cnt.set(f"{len(tracks)} face(s) detected")
            self._fps_var.set(f"{result.get('ai_fps', 0):.1f} FPS")

        except queue.Empty:
            pass

        self.after(33, self._update_frame)

    def _refresh_face_list(self, tracks: list):
        # Clear old cards
        for w in self._face_scroll.winfo_children():
            w.destroy()

        if not tracks:
            tk.Label(self._face_scroll, text="No faces detected",
                     bg=PANEL, fg=TEXT_DIM, font=("Segoe UI", 9),
                     pady=12).pack()
            return

        seen = {}   # name → max confidence
        for t in tracks:
            n, c = t["name"], t["confidence"]
            if n not in seen or c > seen[n]:
                seen[n] = c

        for name, conf in sorted(seen.items()):
            known = (name != "Unknown")
            card = FaceCard(self._face_scroll, name, conf, known,
                            on_delete=self._delete_person)
            card.pack(fill="x", pady=2)

    # ── Stats update (every 2 s) ──────────────────────────────────────────────

    def _update_stats_loop(self):
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=None)
            mem = psutil.Process().memory_info().rss // (1024*1024)
            self._cpu_var.set(f"{cpu:.0f}%")
            self._mem_var.set(f"{mem} MB")
        except ImportError:
            self._cpu_var.set("–")

        # Camera FPS
        if hasattr(self, "_camera"):
            self._cam_fps_var.set(f"{self._camera.fps:.1f} FPS")

        # Status bar
        n_known = self._pipeline.recognizer.person_count()
        mode    = self._pipeline.mode
        ai_fps  = self._pipeline.ai_fps
        self._status_var.set(
            f"Running  ·  {mode}  ·  {n_known} person(s) enrolled  ·  AI {ai_fps:.1f} FPS"
        )

        # Backend label
        self._backend_var.set(self._pipeline.recognizer.backend_name)

        self.after(2000, self._update_stats_loop)

    # ── Mode switching ────────────────────────────────────────────────────────

    def _set_detect(self):
        self._pipeline.set_mode("DETECT")
        self._detect_btn.configure(bg=BTN_GREEN)
        self._track_btn.configure(bg=SURFACE)

    def _set_track(self):
        self._pipeline.set_mode("TRACK")
        self._track_btn.configure(bg=BTN_GREEN)
        self._detect_btn.configure(bg=SURFACE)

    # ── Actions ───────────────────────────────────────────────────────────────

    def _enroll(self):
        EnrollDialog(self, self._pipeline, on_done=self._on_enroll_done)

    def _on_enroll_done(self):
        self._pipeline.reload_recognizer()

    def _remove(self):
        names = self._pipeline.recognizer.known_names()
        if not names:
            messagebox.showinfo("Remove Person", "No enrolled persons.", parent=self)
            return

        # Simple listbox dialog
        dlg = tk.Toplevel(self)
        dlg.title("Remove Person")
        dlg.configure(bg=BG)
        dlg.grab_set()

        tk.Label(dlg, text="Select person to remove:", bg=BG, fg=TEXT,
                 font=("Segoe UI", 11)).pack(padx=20, pady=(16, 4))

        lb = tk.Listbox(dlg, bg=PANEL, fg=TEXT, selectbackground=BTN_BLUE,
                        font=("Segoe UI", 10), relief="flat", bd=0, height=8)
        for n in names:
            lb.insert("end", n)
        lb.pack(padx=20, pady=8, fill="both")

        def do_remove():
            sel = lb.curselection()
            if not sel:
                return
            name = lb.get(sel[0])
            if messagebox.askyesno("Confirm", f"Remove '{name}'?", parent=dlg):
                self._pipeline.delete_person(name)
                self._pipeline.save_encodings()
                dlg.destroy()

        btn = tk.Button(dlg, text="Remove", command=do_remove)
        _style_btn(btn, bg=BTN_RED)
        btn.pack(pady=(0, 16))

    def _delete_person(self, name: str):
        if messagebox.askyesno("Remove", f"Remove '{name}' from the system?", parent=self):
            self._pipeline.delete_person(name)
            self._pipeline.save_encodings()

    def _reload(self):
        self._pipeline.reload_recognizer()
        n = self._pipeline.recognizer.person_count()
        self._status_var.set(f"Reloaded — {n} person(s) enrolled")

    def _settings(self):
        SettingsDialog(self)

    def _on_close(self):
        if messagebox.askyesno("Quit", "Stop the face recognition system?", parent=self):
            self.quit()
            self.destroy()

    def set_camera(self, cam):
        self._camera = cam


# ════════════════════════════════════════════════════════════════════════════
# Entry point
# ════════════════════════════════════════════════════════════════════════════

def parse_args():
    p = argparse.ArgumentParser(description="Raspi/AI Face Recognition")
    p.add_argument("--pi",     action="store_true", help="Raspberry Pi mode")
    p.add_argument("--mode",   choices=["detect", "track"], default="detect")
    p.add_argument("--camera", type=int, default=None)
    return p.parse_args()


def main():
    args = parse_args()

    if args.pi:
        config.USE_PICAMERA2 = True
        config.ENABLE_SERVO  = True
        log.info("Raspberry Pi mode enabled")

    if args.camera is not None:
        config.CAMERA_INDEX = args.camera

    # Ensure dataset directories exist
    os.makedirs(config.DATASET_DIR, exist_ok=True)
    os.makedirs(os.path.join(ROOT, "models"), exist_ok=True)

    # Shared queue
    result_queue = queue.Queue(maxsize=4)

    # Start camera
    from core.camera   import Camera
    from core.pipeline import Pipeline

    camera = Camera()
    camera.start()

    # Start AI pipeline
    pipeline = Pipeline(camera, result_queue)
    pipeline.set_mode(args.mode.upper())
    pipeline.start()

    log.info("Camera started | Pipeline started")

    # Launch GUI (runs on main thread)
    app = App(pipeline, result_queue)
    app.set_camera(camera)
    app.mainloop()

    # Teardown
    pipeline.stop()
    camera.stop()
    log.info("Shutdown complete")


if __name__ == "__main__":
    main()
