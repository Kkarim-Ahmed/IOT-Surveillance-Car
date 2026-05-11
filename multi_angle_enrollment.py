#!/usr/bin/env python3
"""
Multi-Angle Face Enrollment
Captures faces from 9 different angles for better recognition accuracy.
"""

import cv2
import numpy as np
from typing import Tuple, List, Optional, Dict
from pathlib import Path
import time


class MultiAngleEnrollment:
    """Multi-angle face enrollment system."""
    
    # 9 angles: front, left, right, up, down, 4 diagonals
    ANGLES = [
        ("Front", "👤 Look straight at camera"),
        ("Left", "👈 Turn head left"),
        ("Right", "👉 Turn head right"),
        ("Up", "👆 Tilt head up"),
        ("Down", "👇 Tilt head down"),
        ("Up-Left", "↖️ Look up and left"),
        ("Up-Right", "↗️ Look up and right"),
        ("Down-Left", "↙️ Look down and left"),
        ("Down-Right", "↘️ Look down and right"),
    ]
    
    def __init__(self, quality_analyzer=None):
        self.quality_analyzer = quality_analyzer
        self.current_angle_index = 0
        self.captured_angles = {}  # angle_name -> image_path
        self.capture_countdown = 0
        self.countdown_start = 0
        self.auto_capture_enabled = True
        self.quality_threshold = 60  # Minimum quality score
        
    def start_enrollment(self, person_name: str, save_dir: str) -> None:
        """Start multi-angle enrollment session."""
        self.person_name = person_name
        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(parents=True, exist_ok=True)
        self.current_angle_index = 0
        self.captured_angles = {}
        self.capture_countdown = 0
        print(f"🎯 Starting multi-angle enrollment for {person_name}")
    
    def get_current_angle(self) -> Tuple[str, str]:
        """Get current angle name and instruction."""
        if self.current_angle_index >= len(self.ANGLES):
            return ("Complete", "✅ All angles captured!")
        return self.ANGLES[self.current_angle_index]
    
    def get_progress(self) -> Tuple[int, int]:
        """Get enrollment progress (current, total)."""
        return (len(self.captured_angles), len(self.ANGLES))
    
    def is_complete(self) -> bool:
        """Check if all angles are captured."""
        return len(self.captured_angles) >= len(self.ANGLES)
    
    def is_angle_captured(self, angle_name: str) -> bool:
        """Check if specific angle is captured."""
        return angle_name in self.captured_angles
    
    def check_auto_capture(self, frame: np.ndarray, face_box: Optional[Tuple[int, int, int, int]],
                          quality_score: float) -> bool:
        """
        Check if conditions are right for auto-capture.
        Returns True if image was captured.
        """
        if not self.auto_capture_enabled:
            return False
        
        if self.is_complete():
            return False
        
        if face_box is None:
            self.capture_countdown = 0
            return False
        
        # Check quality
        if quality_score < self.quality_threshold:
            self.capture_countdown = 0
            return False
        
        # Start countdown if not started
        if self.capture_countdown == 0:
            self.capture_countdown = 3  # 3 second countdown
            self.countdown_start = time.time()
            return False
        
        # Check if countdown complete
        elapsed = time.time() - self.countdown_start
        if elapsed >= self.capture_countdown:
            # Capture!
            self.capture_current_angle(frame)
            self.capture_countdown = 0
            return True
        
        return False
    
    def get_countdown_remaining(self) -> float:
        """Get remaining countdown time."""
        if self.capture_countdown == 0:
            return 0.0
        
        elapsed = time.time() - self.countdown_start
        remaining = max(0, self.capture_countdown - elapsed)
        return remaining
    
    def capture_current_angle(self, frame: np.ndarray) -> bool:
        """Capture current angle manually."""
        if self.is_complete():
            return False
        
        angle_name, _ = self.get_current_angle()
        
        # Save image
        filename = f"{self.person_name}_{angle_name.lower().replace('-', '_')}.jpg"
        filepath = self.save_dir / filename
        
        cv2.imwrite(str(filepath), frame)
        self.captured_angles[angle_name] = str(filepath)
        
        print(f"✅ Captured {angle_name} ({len(self.captured_angles)}/{len(self.ANGLES)})")
        
        # Move to next angle
        self.current_angle_index += 1
        self.capture_countdown = 0
        
        return True
    
    def skip_current_angle(self) -> bool:
        """Skip current angle."""
        if self.is_complete():
            return False
        
        angle_name, _ = self.get_current_angle()
        print(f"⏭️ Skipped {angle_name}")
        
        self.current_angle_index += 1
        self.capture_countdown = 0
        return True
    
    def get_captured_images(self) -> List[str]:
        """Get list of captured image paths."""
        return list(self.captured_angles.values())
    
    def draw_enrollment_ui(self, frame: np.ndarray) -> np.ndarray:
        """Draw enrollment UI overlay."""
        display = frame.copy()
        h, w = frame.shape[:2]
        
        # Progress bar at top
        progress_current, progress_total = self.get_progress()
        progress_pct = progress_current / progress_total
        
        # Progress bar background
        bar_height = 40
        cv2.rectangle(display, (0, 0), (w, bar_height), (30, 30, 30), -1)
        
        # Progress bar fill
        bar_width = int(w * progress_pct)
        cv2.rectangle(display, (0, 0), (bar_width, bar_height), (0, 255, 0), -1)
        
        # Progress text
        progress_text = f"Progress: {progress_current}/{progress_total} angles"
        cv2.putText(display, progress_text, (10, 28),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        
        # Current angle instruction
        if not self.is_complete():
            angle_name, instruction = self.get_current_angle()
            
            # Instruction box
            inst_y = h - 120
            cv2.rectangle(display, (0, inst_y), (w, h), (30, 30, 30), -1)
            
            # Angle name
            cv2.putText(display, f"Angle: {angle_name}", (10, inst_y + 35),
                       cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)
            
            # Instruction
            cv2.putText(display, instruction, (10, inst_y + 75),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            
            # Countdown
            countdown = self.get_countdown_remaining()
            if countdown > 0:
                countdown_text = f"Capturing in {countdown:.1f}s"
                cv2.putText(display, countdown_text, (10, inst_y + 110),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        else:
            # Completion message
            cv2.rectangle(display, (0, h - 80), (w, h), (0, 255, 0), -1)
            cv2.putText(display, "✅ All angles captured!", (10, h - 45),
                       cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 3)
            cv2.putText(display, "Click 'Finish & Save' to complete enrollment", (10, h - 15),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # Draw angle checklist on right side
        self._draw_angle_checklist(display, w - 250, 60)
        
        return display
    
    def _draw_angle_checklist(self, frame: np.ndarray, x: int, y: int) -> None:
        """Draw checklist of captured angles."""
        # Background
        box_height = len(self.ANGLES) * 30 + 40
        cv2.rectangle(frame, (x - 10, y - 10), (x + 240, y + box_height), (30, 30, 30), -1)
        cv2.rectangle(frame, (x - 10, y - 10), (x + 240, y + box_height), (200, 200, 200), 2)
        
        # Title
        cv2.putText(frame, "Angles Checklist:", (x, y + 15),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # Angles
        for i, (angle_name, _) in enumerate(self.ANGLES):
            angle_y = y + 45 + i * 30
            
            # Checkmark or circle
            if self.is_angle_captured(angle_name):
                # Green checkmark
                cv2.putText(frame, "✓", (x, angle_y),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                color = (0, 255, 0)
            elif i == self.current_angle_index:
                # Current angle - yellow arrow
                cv2.putText(frame, "→", (x, angle_y),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                color = (0, 255, 255)
            else:
                # Not captured - gray circle
                cv2.circle(frame, (x + 10, angle_y - 8), 8, (100, 100, 100), 2)
                color = (150, 150, 150)
            
            # Angle name
            cv2.putText(frame, angle_name, (x + 30, angle_y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
    
    def reset(self) -> None:
        """Reset enrollment session."""
        self.current_angle_index = 0
        self.captured_angles = {}
        self.capture_countdown = 0
