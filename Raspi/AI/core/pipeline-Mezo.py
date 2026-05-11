"""
AI pipeline thread.

Reads frames from Camera.queue, runs detection → recognition → tracking,
then annotates and puts result dicts into result_queue for the GUI.

DETECT mode : FaceDetector (full-range BlazeFace) + recognition every N frames
TRACK  mode : PersonDetector (MediaPipe Pose Lite) for body bbox → motor control
              Falls back to FaceDetector if no body is found.

result dict:
    {
      "frame":   np.ndarray (annotated 640×480 BGR),
      "tracks":  List[dict] — snapshot of active tracks,
      "mode":    "DETECT" | "TRACK",
      "ai_fps":  float,
      "motor":   dict — telemetry from MotorController (empty if disabled),
    }
"""

import sys
import time
import queue
import threading
import logging
from typing import Optional

import cv2
import numpy as np

sys.path.insert(0, "..")
import config
from core.camera     import Camera
from core.detector   import FaceDetector
from core.recognizer import FaceRecognizer
from core.tracker    import Tracker

log = logging.getLogger(__name__)

# Servo support (optional)
_servo_ok = False
try:
    from adafruit_servokit import ServoKit as _ServoKit   # type: ignore
    _servo_ok = True
except ImportError:
    pass

# Motor support (optional — falls back to mock driver on non-RPi machines)
_motor_available = False
try:
    from integration.motor_controller import MotorController as _MotorController
    _motor_available = True
except Exception:
    pass

# HUD zone colours (BGR) — mirrors config zone boundaries
_ZONE_COLORS = {
    "STOP":   (50,  50,  220),   # red
    "HOLD":   (50,  165, 230),   # orange
    "FOLLOW": (50,  200, 50),    # green
    "CHASE":  (230, 200, 50),    # yellow-cyan
    "IDLE":   (150, 150, 150),   # grey
}


class Pipeline:
    """
    Runs as a single background thread.
    """

    def __init__(self, camera: Camera, result_queue: queue.Queue):
        self._cam       = camera
        self._result_q  = result_queue
        self._detector  = FaceDetector()
        self._recognizer= FaceRecognizer()
        self._tracker   = Tracker()
        self._mode      = "DETECT"   # "DETECT" or "TRACK"
        self._stop      = threading.Event()
        self._thread: threading.Thread | None = None
        self._ai_fps         = 0.0
        self._frame_n        = 0
        self._last_names: list = []
        self._last_motor_bbox: Optional[tuple] = None

        # Servo (optional — pan/tilt for static-camera setups)
        self._kit = None
        self._pan  = float(config.PAN_CENTER)
        self._tilt = float(config.TILT_CENTER)
        self._pan_integral  = 0.0
        self._tilt_integral = 0.0
        if config.ENABLE_SERVO and _servo_ok:
            try:
                self._kit = _ServoKit(channels=16)
                log.info("Servo kit initialised")
            except Exception as e:
                log.warning("Servo init failed: %s", e)

        # Body / person detector (TRACK mode — robust long-range detection)
        self._person_det = None
        if config.USE_BODY_DETECTOR:
            try:
                from core.person_detector import PersonDetector
                self._person_det = PersonDetector()
            except Exception as exc:
                log.warning("PersonDetector unavailable: %s", exc)

        # Motor controller (differential drive — mutually exclusive with servo)
        self._motor = None
        if _motor_available and config.MOTOR_ENABLED:
            self._motor = _MotorController()
            log.info("MotorController initialised")

        log.info("Pipeline ready — detector: %s | recognizer: %s | persons: %d",
                 self._detector.backend,
                 self._recognizer.backend_name,
                 self._recognizer.person_count())

    # ── Public ────────────────────────────────────────────────────────────────

    def start(self) -> None:
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="pipeline")
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)
        if self._motor is not None:
            self._motor.cleanup()

    def set_mode(self, mode: str) -> None:
        self._mode = mode.upper()
        log.info("Mode → %s", self._mode)

    def reload_recognizer(self) -> None:
        self._recognizer.reload()

    def enroll(self, face_bgr: np.ndarray, name: str) -> bool:
        return self._recognizer.enroll_face(face_bgr, name)

    def save_encodings(self) -> None:
        self._recognizer.save_encodings()

    def delete_person(self, name: str) -> bool:
        return self._recognizer.delete_person(name)

    @property
    def ai_fps(self) -> float:
        return self._ai_fps

    @property
    def recognizer(self) -> FaceRecognizer:
        return self._recognizer

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def motor(self):
        return self._motor

    def lock_target(self, name: str) -> None:
        """Tell the tracker to follow a specific enrolled person by name."""
        self._tracker.target_name = name
        log.info("Target locked via pipeline: %s", name)

    def unlock_target(self) -> None:
        """Clear the target lock — tracker will re-acquire on next recognition."""
        self._tracker.target_name = None
        log.info("Target lock cleared")

    @property
    def locked_target(self) -> Optional[str]:
        return self._tracker.target_name

    # ── Main loop ─────────────────────────────────────────────────────────────

    def _run(self) -> None:
        t0, n = time.perf_counter(), 0

        while not self._stop.is_set():
            try:
                frame = self._cam.queue.get(timeout=0.5)
            except queue.Empty:
                continue

            self._frame_n += 1
            result = self._process(frame)

            # Push to GUI queue (drop oldest if full)
            try:
                self._result_q.put_nowait(result)
            except queue.Full:
                try:
                    self._result_q.get_nowait()
                except queue.Empty:
                    pass
                self._result_q.put_nowait(result)

            n += 1
            elapsed = time.perf_counter() - t0
            if elapsed >= 1.0:
                self._ai_fps = n / elapsed
                n, t0 = 0, time.perf_counter()

    # ── Helpers + per-frame processing ───────────────────────────────────────

    def _scale_dets(self, raw: list, sx: float, sy: float) -> list:
        out = []
        for d in raw:
            x1, y1, x2, y2 = d["bbox"]
            kps = [(kx * sx, ky * sy) for kx, ky in d.get("keypoints", [])]
            out.append({
                "bbox":      (int(x1*sx), int(y1*sy), int(x2*sx), int(y2*sy)),
                "score":     d["score"],
                "keypoints": kps,
            })
        return out

    def _face_to_body_bbox(self, face_bbox: tuple) -> tuple:
        """Estimate full-body bbox from face bbox using anthropometric ratios.

        A standing adult's head is roughly 1/7.5 of total height.
        Shoulder width is ~2.5× face width.
        """
        x1, y1, x2, y2 = face_bbox
        fh = max(y2 - y1, 1)
        fw = max(x2 - x1, 1)
        cx = (x1 + x2) / 2.0

        body_h  = fh * 7.5
        body_w  = max(fw * 2.5, fh * 2.5)
        bx1 = int(cx - body_w / 2)
        by1 = int(y1 - fh * 0.15)          # just above forehead
        bx2 = int(cx + body_w / 2)
        by2 = int(y1 + body_h)

        bx1 = max(0, bx1);  by1 = max(0, by1)
        bx2 = min(config.FRAME_W, bx2);  by2 = min(config.FRAME_H, by2)
        return (bx1, by1, bx2, by2)

    def _process(self, frame: np.ndarray) -> dict:
        # Downscale for AI inference
        small = cv2.resize(frame, (config.AI_W, config.AI_H))
        sx = config.FRAME_W / config.AI_W
        sy = config.FRAME_H / config.AI_H

        motor_bbox: Optional[tuple] = None
        is_detect_frame = (self._frame_n % config.DETECT_EVERY_N == 0)

        if self._mode == "TRACK":
            if is_detect_frame:
                # ── Full detection pass (every DETECT_EVERY_N frames) ───────────
                # Step 1: Detect ALL faces (BlazeFace, up to 10 faces, ~10 ms)
                face_dets = self._scale_dets(self._detector.detect(small), sx, sy)

                # Step 2: Recognition on every RECOG_EVERY_N-th frame
                if self._frame_n % config.RECOG_EVERY_N == 0 and face_dets:
                    pairs = self._recognizer.identify_detections(frame, face_dets)
                    self._last_names = pairs
                names = self._last_names

                # Step 3: Kalman update on real detections
                tracks = self._tracker.update(face_dets, names, frame=frame)

                # Step 4: Find target face → derive body bbox for motor
                if face_dets and names:
                    for i, (name, conf) in enumerate(names):
                        is_locked  = (name == self._tracker.target_name and conf > 0)
                        is_new_hit = (self._tracker.target_name is None
                                      and conf >= config.RECOG_THRESHOLD)
                        if is_locked or is_new_hit:
                            motor_bbox = self._face_to_body_bbox(face_dets[i]["bbox"])
                            break

                # Step 5: Fallback — person turned away, run body detector
                if motor_bbox is None and self._person_det is not None:
                    body_raw = self._person_det.detect(small)
                    if body_raw:
                        bd = self._scale_dets(body_raw, sx, sy)
                        motor_bbox = bd[0]["bbox"]

                self._last_motor_bbox = motor_bbox
            else:
                # ── Skip frame: Kalman prediction only, reuse last motor bbox ──
                tracks = self._tracker.predict_only()
                motor_bbox = self._last_motor_bbox

        else:
            # ── DETECT mode — face detection + recognition ─────────────────────
            dets = self._scale_dets(self._detector.detect(small), sx, sy)
            names = None
            if self._frame_n % config.RECOG_EVERY_N == 0 and dets:
                pairs = self._recognizer.identify_detections(frame, dets)
                self._last_names = pairs
                names = pairs
            else:
                names = self._last_names if self._last_names else None
            tracks = self._tracker.update(dets, names, frame=frame)

        # ── Motor / Servo control ───────────────────────────────────────────────
        motor_state: dict = {}
        if self._mode == "TRACK":
            if motor_bbox is not None:
                if self._motor is not None:
                    self._motor.update(motor_bbox,
                                       frame_width=config.FRAME_W,
                                       frame_height=config.FRAME_H)
                elif self._kit is not None:
                    x1, y1, x2, y2 = motor_bbox
                    self._servo_step((x1 + x2) / 2.0, (y1 + y2) / 2.0)
            else:
                if self._motor is not None:
                    self._motor.search(last_error_x=self._motor.error_x)

        if self._motor is not None:
            motor_state = {
                "distance_cm": self._motor.distance_cm,
                "error_x":     self._motor.error_x,
                "left_speed":  self._motor.left_speed,
                "right_speed": self._motor.right_speed,
                "state":       self._motor.state,
            }

        annotated = self._annotate(frame.copy(), tracks, motor_state)
        return {
            "frame":   annotated,
            "tracks":  [{"id": t.id, "name": t.name, "confidence": t.confidence,
                         "bbox": t.bbox()} for t in tracks],
            "mode":    self._mode,
            "ai_fps":  self._ai_fps,
            "motor":   motor_state,
        }

    # ── Annotation ────────────────────────────────────────────────────────────

    def _annotate(self, frame: np.ndarray, tracks,
                  motor_state: dict = None) -> np.ndarray:
        h, w = frame.shape[:2]

        # Track boxes + labels
        for t in tracks:
            x1, y1, x2, y2 = t.bbox()
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)

            if self._mode == "TRACK":
                ms_state = (motor_state or {}).get("state", "IDLE")
                color    = _ZONE_COLORS.get(ms_state, config.COLOR_TRACK)
                label    = f"ID {t.id}"
            elif t.name == "Unknown":
                color = config.COLOR_UNKNOWN
                label = "Unknown"
            else:
                color = config.COLOR_KNOWN
                label = f"{t.name}  {t.confidence:.0%}"

            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)
            py = max(y1 - 8, th + 8)
            cv2.rectangle(frame, (x1, py - th - 6), (x1 + tw + 8, py + 2), color, -1)
            cv2.putText(frame, label, (x1 + 4, py - 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)

        # Mode + FPS banner
        mode_col = (50, 200, 50) if self._mode == "DETECT" else (50, 165, 230)
        cv2.putText(frame, f"{self._mode}  {self._ai_fps:.1f} FPS",
                    (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.65, mode_col, 2, cv2.LINE_AA)

        # TRACK mode: motor HUD overlay
        if self._mode == "TRACK" and motor_state:
            self._draw_motor_hud(frame, motor_state)

        return frame

    def _draw_motor_hud(self, frame: np.ndarray, ms: dict) -> None:
        """Overlay dead-zone lines, steering arrow, zone badge, and speed bars."""
        h, w   = frame.shape[:2]
        cx     = w // 2
        dist   = ms.get("distance_cm", 0.0)
        state  = ms.get("state", "IDLE")
        err_x  = ms.get("error_x",  0.0)
        l_spd  = ms.get("left_speed",  0)
        r_spd  = ms.get("right_speed", 0)

        hud_col = _ZONE_COLORS.get(state, (150, 150, 150))

        # Dead-zone boundary lines (subtle vertical guides)
        dz = config.MOTOR_DEAD_ZONE_PX
        cv2.line(frame, (cx - dz, h // 3), (cx - dz, h), (80, 80, 80), 1)
        cv2.line(frame, (cx + dz, h // 3), (cx + dz, h), (80, 80, 80), 1)
        cv2.line(frame, (cx,      h // 3), (cx,      h), (50, 50, 50), 1)

        # Steering arrow (center bottom)
        if abs(err_x) > config.MOTOR_DEAD_ZONE_PX:
            tip_x = int(cx + err_x * 0.25)
            tip_x = max(8, min(w - 8, tip_x))
            cv2.arrowedLine(frame, (cx, h - 28), (tip_x, h - 28),
                            hud_col, 2, cv2.LINE_AA, tipLength=0.35)

        # Zone + distance badge (bottom-left)
        dist_txt = f"{dist:.0f} cm" if dist < 9000 else "– cm"
        badge    = f"{state}  {dist_txt}"
        (bw, bh), _ = cv2.getTextSize(badge, cv2.FONT_HERSHEY_SIMPLEX, 0.60, 2)
        cv2.rectangle(frame, (6, h - bh - 16), (14 + bw, h - 4), (20, 20, 20), -1)
        cv2.putText(frame, badge,
                    (10, h - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.60, hud_col, 2, cv2.LINE_AA)

        # Mini vertical speed bars (bottom-right corner)
        bar_h = 48
        bar_w = 10
        x_r   = w - 8
        y_bot = h - 8
        for spd, x_off in [(l_spd, x_r - bar_w - 4), (r_spd, x_r - 2 * bar_w - 10)]:
            fill = int(spd / 255 * bar_h)
            cv2.rectangle(frame, (x_off, y_bot - bar_h), (x_off + bar_w, y_bot),
                          (50, 50, 50), -1)
            if fill > 0:
                cv2.rectangle(frame, (x_off, y_bot - fill), (x_off + bar_w, y_bot),
                              hud_col, -1)

    # ── Servo ─────────────────────────────────────────────────────────────────

    def _servo_step(self, face_cx: float, face_cy: float) -> None:
        if not self._kit:
            return
        err_x = face_cx - config.FRAME_W / 2
        err_y = face_cy - config.FRAME_H / 2
        if abs(err_x) < config.DEADZONE_X: err_x = 0.0
        if abs(err_y) < config.DEADZONE_Y: err_y = 0.0
        self._pan_integral  += err_x
        self._tilt_integral += err_y
        dp = config.KP*err_x + config.KI*self._pan_integral
        dt = config.KP*err_y + config.KI*self._tilt_integral
        dp = max(-config.MAX_SERVO_SPEED, min(config.MAX_SERVO_SPEED, dp))
        dt = max(-config.MAX_SERVO_SPEED, min(config.MAX_SERVO_SPEED, dt))
        self._pan  = max(config.PAN_MIN,  min(config.PAN_MAX,  self._pan  + dp))
        self._tilt = max(config.TILT_MIN, min(config.TILT_MAX, self._tilt + dt))
        try:
            self._kit.servo[config.PAN_CHANNEL].angle  = self._pan
            self._kit.servo[config.TILT_CHANNEL].angle = self._tilt
        except Exception:
            pass
