"""
Multi-Core Processing Manager
Splits face detection, recognition, and servo control across CPU cores.

Core allocation (Raspberry Pi 4 - 4 cores):
  Core 0  → OS (reserved, never touched)
  Core 1  → Camera capture + display loop
  Core 2  → Face detection (BlazeFace / YOLO)
  Core 3  → Face recognition (dlib embeddings) + servo PID
"""

import multiprocessing as mp
import threading
import queue
import time
import os
import cv2
import numpy as np
from collections import deque
import config
from camera_utils import open_camera, read_frame


# ─────────────────────────────────────────────────────────────────────────────
# Shared data structures (process-safe)
# ─────────────────────────────────────────────────────────────────────────────

class SharedState:
    """Thread/process-safe shared state between cores."""

    def __init__(self):
        # Latest raw frame (numpy array stored in shared memory via Queue)
        self.frame_queue      = mp.Queue(maxsize=2)   # camera → detector
        self.detection_queue  = mp.Queue(maxsize=2)   # detector → recognizer
        self.result_queue     = mp.Queue(maxsize=2)   # recognizer → display

        # Servo command pipe (recognizer → servo worker)
        self.servo_cmd_queue  = mp.Queue(maxsize=4)

        # Flags
        self.stop_event = mp.Event()

    def stop(self):
        self.stop_event.set()

    def is_running(self):
        return not self.stop_event.is_set()


# ─────────────────────────────────────────────────────────────────────────────
# Worker: Face Detection  (pinned to Core 2)
# ─────────────────────────────────────────────────────────────────────────────

def detection_worker(frame_queue: mp.Queue,
                     detection_queue: mp.Queue,
                     stop_event: mp.Event):
    """
    Runs on Core 2.
    Reads raw frames, runs BlazeFace, pushes (frame, locations) downstream.
    """
    # Pin this process to Core 2
    try:
        os.sched_setaffinity(0, {2})
    except Exception:
        pass  # Not available on all platforms (Windows)

    # Import here so the import happens inside the worker process
    from blazeface_detector import BlazeFaceDetector
    detector = BlazeFaceDetector()

    frame_skip = 0

    while not stop_event.is_set():
        try:
            frame = frame_queue.get(timeout=0.05)
        except Exception:
            continue

        # Frame skipping: process 1 out of every PROCESS_EVERY_N_FRAMES
        frame_skip += 1
        if frame_skip < config.PROCESS_EVERY_N_FRAMES:
            # Still push frame so recognizer can display it
            try:
                detection_queue.put_nowait((frame, []))
            except Exception:
                pass
            continue
        frame_skip = 0

        face_locations = detector.detect_faces(frame)

        try:
            detection_queue.put_nowait((frame, face_locations))
        except Exception:
            pass  # Drop if downstream is full


# ─────────────────────────────────────────────────────────────────────────────
# Worker: Face Recognition + Servo PID  (pinned to Core 3)
# ─────────────────────────────────────────────────────────────────────────────

def recognition_worker(detection_queue: mp.Queue,
                       result_queue: mp.Queue,
                       servo_cmd_queue: mp.Queue,
                       stop_event: mp.Event):
    """
    Runs on Core 3.
    Reads (frame, locations), runs face recognition, computes PID error,
    pushes servo commands and annotated results.
    """
    try:
        os.sched_setaffinity(0, {3})
    except Exception:
        pass

    from face_recognition_module import FaceRecognitionSystem
    recognizer = FaceRecognitionSystem()

    # Cache last recognition results to avoid re-running every frame
    cached_results = []
    cached_locations = []
    recog_frame_count = 0

    while not stop_event.is_set():
        try:
            frame, face_locations = detection_queue.get(timeout=0.05)
        except Exception:
            continue

        # Only run recognition every N frames (expensive)
        recog_frame_count += 1
        if recog_frame_count >= config.PROCESS_EVERY_N_FRAMES:
            recog_frame_count = 0
            if len(face_locations) > 0:
                cached_results   = recognizer.recognize_faces(frame, face_locations)
                cached_locations = face_locations
            else:
                cached_results   = []
                cached_locations = []

        # Compute face center for servo
        if len(face_locations) > 0:
            # Pick largest face
            largest_area  = 0
            target_idx    = 0
            for i, (top, right, bottom, left) in enumerate(face_locations):
                area = (right - left) * (bottom - top)
                if area > largest_area:
                    largest_area = area
                    target_idx   = i

            top, right, bottom, left = face_locations[target_idx]
            cx = (left + right) // 2
            cy = (top  + bottom) // 2

            # Push servo command
            try:
                servo_cmd_queue.put_nowait((cx, cy))
            except Exception:
                pass

        # Push display result
        try:
            result_queue.put_nowait({
                "frame":      frame,
                "locations":  face_locations,
                "results":    cached_results if cached_results else [("Unknown", 0.0)] * len(face_locations),
            })
        except Exception:
            pass


# ─────────────────────────────────────────────────────────────────────────────
# Worker: Servo PID  (thread on Core 3, same process as recognition)
# ─────────────────────────────────────────────────────────────────────────────

def servo_worker(servo_cmd_queue: mp.Queue, stop_event: mp.Event):
    """
    Lightweight thread that reads (cx, cy) commands and drives servos via PID.
    Runs as a thread inside the recognition process (Core 3).
    """
    from servo_control import FaceTrackingServo
    servo = FaceTrackingServo()

    while not stop_event.is_set():
        try:
            cx, cy = servo_cmd_queue.get(timeout=0.05)
            servo.update(cx, cy)
        except Exception:
            continue

    servo.reset()


# ─────────────────────────────────────────────────────────────────────────────
# Main Orchestrator  (Core 1)
# ─────────────────────────────────────────────────────────────────────────────

class MultiCoreTracker:
    """
    Orchestrates all workers across 3 CPU cores.
    Core 1 (this process): camera capture + display
    Core 2: detection_worker
    Core 3: recognition_worker + servo_worker thread
    """

    def __init__(self):
        # Pin main process to Core 1
        try:
            os.sched_setaffinity(0, {1})
        except Exception:
            pass

        self.state = SharedState()

        # Spawn detection process
        self.det_proc = mp.Process(
            target=detection_worker,
            args=(self.state.frame_queue,
                  self.state.detection_queue,
                  self.state.stop_event),
            daemon=True,
            name="DetectionCore2"
        )

        # Spawn recognition process (servo thread lives inside it)
        self.rec_proc = mp.Process(
            target=self._recognition_with_servo,
            args=(self.state.detection_queue,
                  self.state.result_queue,
                  self.state.servo_cmd_queue,
                  self.state.stop_event),
            daemon=True,
            name="RecognitionCore3"
        )

        # Camera
        self.cap = open_camera()

        # FPS tracking
        self.fps_queue = deque(maxlen=30)

    @staticmethod
    def _recognition_with_servo(detection_queue, result_queue,
                                 servo_cmd_queue, stop_event):
        """Entry point for Core 3 process: starts servo thread then runs recognizer."""
        servo_thread = threading.Thread(
            target=servo_worker,
            args=(servo_cmd_queue, stop_event),
            daemon=True
        )
        servo_thread.start()
        recognition_worker(detection_queue, result_queue, servo_cmd_queue, stop_event)
        servo_thread.join()

    def start(self):
        """Start all worker processes."""
        self.det_proc.start()
        self.rec_proc.start()
        print("✅ Multi-core workers started")
        print(f"   Core 1 → Camera + Display (PID {os.getpid()})")
        print(f"   Core 2 → Face Detection   (PID {self.det_proc.pid})")
        print(f"   Core 3 → Recognition+Servo (PID {self.rec_proc.pid})")

    def run(self):
        """Main camera + display loop (Core 1)."""
        self.start()

        print("\n▶️  Running — press 'q' to quit, 'r' to reset servos, 's' to save frame")

        latest_result = None

        try:
            while True:
                t0 = time.time()

                ret, frame = read_frame(self.cap)   # flip applied here
                if not ret:
                    print("❌ Camera read failed")
                    break

                # Push frame to detection pipeline (drop if full)
                try:
                    self.state.frame_queue.put_nowait(frame)
                except Exception:
                    pass

                # Pull latest result (non-blocking)
                try:
                    latest_result = self.state.result_queue.get_nowait()
                except Exception:
                    pass

                # Draw
                display = self._draw(frame, latest_result)

                # FPS
                elapsed = time.time() - t0
                fps = 1.0 / elapsed if elapsed > 0 else 0
                self.fps_queue.append(fps)
                avg_fps = sum(self.fps_queue) / len(self.fps_queue)
                cv2.putText(display, f"FPS: {avg_fps:.1f}", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

                cv2.imshow("Face Tracking — Multi-Core", display)

                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
                elif key == ord('s'):
                    fname = f"capture_{int(time.time())}.jpg"
                    cv2.imwrite(fname, display)
                    print(f"📸 Saved {fname}")

        except KeyboardInterrupt:
            pass
        finally:
            self.stop()

    def _draw(self, frame, result):
        """Draw bounding boxes and labels on frame."""
        display = frame.copy()
        h, w = frame.shape[:2]
        cx, cy = w // 2, h // 2

        # Crosshair
        cv2.line(display, (cx - 20, cy), (cx + 20, cy), (255, 0, 0), 2)
        cv2.line(display, (cx, cy - 20), (cx, cy + 20), (255, 0, 0), 2)

        # Deadzone rectangle
        cv2.rectangle(display,
                      (cx - config.DEADZONE_X, cy - config.DEADZONE_Y),
                      (cx + config.DEADZONE_X, cy + config.DEADZONE_Y),
                      (255, 0, 0), 1)

        if result is None:
            return display

        locations = result.get("locations", [])
        recog     = result.get("results",   [])

        for i, (top, right, bottom, left) in enumerate(locations):
            name, conf = recog[i] if i < len(recog) else ("Unknown", 0.0)
            color = (0, 255, 0) if name != "Unknown" else (0, 165, 255)

            cv2.rectangle(display, (left, top), (right, bottom), color, 2)

            label = f"{name} {conf:.2f}" if name != "Unknown" else "Unknown"
            (lw, lh), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2)
            cv2.rectangle(display, (left, top - lh - 8), (left + lw, top), color, -1)
            cv2.putText(display, label, (left, top - 4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)

            # Face center dot
            fcx = (left + right) // 2
            fcy = (top  + bottom) // 2
            cv2.circle(display, (fcx, fcy), 5, color, -1)

            # Error vector to frame center
            cv2.line(display, (fcx, fcy), (cx, cy), (200, 200, 0), 1)

        return display

    def stop(self):
        """Gracefully stop all workers."""
        print("\n🛑 Stopping workers…")
        self.state.stop()
        self.det_proc.join(timeout=3)
        self.rec_proc.join(timeout=3)
        self.cap.release()
        cv2.destroyAllWindows()
        print("✅ All workers stopped")


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Required on Windows / macOS for multiprocessing
    mp.set_start_method("spawn", force=True)

    tracker = MultiCoreTracker()
    tracker.run()
