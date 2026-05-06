#!/usr/bin/env python3
"""
Video Recorder Module
Records video with annotations (names, confidence, timestamps).
"""

import cv2
import numpy as np
from datetime import datetime
from pathlib import Path
import threading
import queue


class VideoRecorder:
    """Record video with annotations."""
    
    def __init__(self, output_dir: str = "recordings"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.is_recording = False
        self.video_writer = None
        self.current_filename = None
        self.frame_queue = queue.Queue(maxsize=100)
        self.recording_thread = None
        
        # Recording settings
        self.fps = 30
        self.codec = cv2.VideoWriter_fourcc(*'mp4v')
        
        # Statistics
        self.frames_recorded = 0
        self.recording_start_time = None
    
    def start_recording(self, frame_width: int, frame_height: int) -> str:
        """Start recording video."""
        if self.is_recording:
            return self.current_filename
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.current_filename = f"recording_{timestamp}.mp4"
        filepath = self.output_dir / self.current_filename
        
        # Create video writer
        self.video_writer = cv2.VideoWriter(
            str(filepath),
            self.codec,
            self.fps,
            (frame_width, frame_height)
        )
        
        if not self.video_writer.isOpened():
            print(f"❌ Failed to create video writer")
            return None
        
        self.is_recording = True
        self.frames_recorded = 0
        self.recording_start_time = datetime.now()
        
        # Start recording thread
        self.recording_thread = threading.Thread(target=self._recording_loop, daemon=True)
        self.recording_thread.start()
        
        print(f"🎥 Started recording: {self.current_filename}")
        return self.current_filename
    
    def stop_recording(self) -> dict:
        """Stop recording and return statistics."""
        if not self.is_recording:
            return None
        
        self.is_recording = False
        
        # Wait for queue to empty
        self.frame_queue.join()
        
        # Release video writer
        if self.video_writer:
            self.video_writer.release()
            self.video_writer = None
        
        # Calculate statistics
        duration = (datetime.now() - self.recording_start_time).total_seconds()
        
        stats = {
            'filename': self.current_filename,
            'frames': self.frames_recorded,
            'duration': duration,
            'fps': self.frames_recorded / duration if duration > 0 else 0,
            'filepath': str(self.output_dir / self.current_filename)
        }
        
        print(f"⏹️ Stopped recording: {self.current_filename}")
        print(f"   Frames: {self.frames_recorded}, Duration: {duration:.1f}s")
        
        self.current_filename = None
        self.frames_recorded = 0
        
        return stats
    
    def add_frame(self, frame: np.ndarray) -> bool:
        """Add frame to recording queue."""
        if not self.is_recording:
            return False
        
        try:
            self.frame_queue.put_nowait(frame.copy())
            return True
        except queue.Full:
            print("⚠️ Recording queue full, dropping frame")
            return False
    
    def _recording_loop(self):
        """Background thread for writing frames."""
        while self.is_recording or not self.frame_queue.empty():
            try:
                frame = self.frame_queue.get(timeout=1.0)
                if self.video_writer:
                    self.video_writer.write(frame)
                    self.frames_recorded += 1
                self.frame_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"❌ Recording error: {e}")
    
    def get_status(self) -> dict:
        """Get current recording status."""
        if not self.is_recording:
            return {
                'recording': False,
                'filename': None,
                'frames': 0,
                'duration': 0
            }
        
        duration = (datetime.now() - self.recording_start_time).total_seconds()
        
        return {
            'recording': True,
            'filename': self.current_filename,
            'frames': self.frames_recorded,
            'duration': duration,
            'queue_size': self.frame_queue.qsize()
        }


class SnapshotCapture:
    """Capture snapshots of detections."""
    
    def __init__(self, output_dir: str = "snapshots"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.snapshots_taken = 0
    
    def capture_snapshot(self, frame: np.ndarray, person_name: str = None) -> str:
        """Capture and save snapshot."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if person_name and person_name != "Unknown":
            # Create person directory
            person_dir = self.output_dir / person_name
            person_dir.mkdir(parents=True, exist_ok=True)
            filename = f"{person_name}_{timestamp}.jpg"
            filepath = person_dir / filename
        else:
            filename = f"snapshot_{timestamp}.jpg"
            filepath = self.output_dir / filename
        
        # Save image
        cv2.imwrite(str(filepath), frame)
        self.snapshots_taken += 1
        
        print(f"📸 Snapshot saved: {filename}")
        return str(filepath)
    
    def get_snapshots_count(self) -> int:
        """Get total snapshots taken."""
        return self.snapshots_taken
