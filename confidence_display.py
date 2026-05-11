#!/usr/bin/env python3
"""
Recognition Confidence Display
Real-time confidence visualization and tracking.
"""

import cv2
import numpy as np
from collections import deque
from typing import Tuple, Optional, List


class ConfidenceDisplay:
    """Display and track recognition confidence metrics."""
    
    def __init__(self, history_length: int = 90):  # 3 seconds at 30 FPS
        self.history_length = history_length
        self.confidence_history = deque(maxlen=history_length)
        self.smoothed_confidence = 0.0
        self.smoothing_factor = 0.3
        
    def update(self, confidence: float) -> None:
        """Update confidence with new value."""
        # Smooth confidence to reduce jitter
        if self.smoothed_confidence == 0.0:
            self.smoothed_confidence = confidence
        else:
            self.smoothed_confidence = (self.smoothing_factor * confidence + 
                                       (1 - self.smoothing_factor) * self.smoothed_confidence)
        
        self.confidence_history.append(self.smoothed_confidence)
    
    def get_confidence(self) -> float:
        """Get current smoothed confidence."""
        return self.smoothed_confidence
    
    def get_average_confidence(self) -> float:
        """Get average confidence over history."""
        if not self.confidence_history:
            return 0.0
        return sum(self.confidence_history) / len(self.confidence_history)
    
    def get_confidence_level(self) -> Tuple[str, Tuple[int, int, int]]:
        """Get confidence level and color."""
        conf = self.smoothed_confidence * 100
        
        if conf >= 70:
            return "High", (0, 255, 0)  # Green
        elif conf >= 50:
            return "Medium", (0, 255, 255)  # Yellow
        else:
            return "Low", (0, 0, 255)  # Red
    
    def get_trend(self) -> str:
        """Get confidence trend (improving/declining/stable)."""
        if len(self.confidence_history) < 10:
            return "Stable"
        
        recent = list(self.confidence_history)[-10:]
        older = list(self.confidence_history)[-20:-10] if len(self.confidence_history) >= 20 else recent
        
        recent_avg = sum(recent) / len(recent)
        older_avg = sum(older) / len(older)
        
        diff = recent_avg - older_avg
        
        if diff > 0.05:
            return "Improving"
        elif diff < -0.05:
            return "Declining"
        else:
            return "Stable"
    
    def draw_confidence_bar(self, frame: np.ndarray, x: int, y: int, 
                           width: int = 200, height: int = 30) -> None:
        """Draw confidence bar on frame."""
        conf = self.smoothed_confidence
        level, color = self.get_confidence_level()
        
        # Background
        cv2.rectangle(frame, (x, y), (x + width, y + height), (50, 50, 50), -1)
        cv2.rectangle(frame, (x, y), (x + width, y + height), (200, 200, 200), 2)
        
        # Confidence bar
        bar_width = int(width * conf)
        if bar_width > 0:
            cv2.rectangle(frame, (x + 2, y + 2), 
                         (x + bar_width - 2, y + height - 2), color, -1)
        
        # Text
        text = f"{conf * 100:.0f}% - {level}"
        cv2.putText(frame, text, (x + 5, y + height - 8),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    
    def draw_confidence_graph(self, frame: np.ndarray, x: int, y: int,
                             width: int = 200, height: int = 100) -> None:
        """Draw confidence history graph."""
        if len(self.confidence_history) < 2:
            return
        
        # Background
        cv2.rectangle(frame, (x, y), (x + width, y + height), (30, 30, 30), -1)
        cv2.rectangle(frame, (x, y), (x + width, y + height), (200, 200, 200), 2)
        
        # Grid lines
        for i in range(5):
            grid_y = y + int(height * i / 4)
            cv2.line(frame, (x, grid_y), (x + width, grid_y), (60, 60, 60), 1)
        
        # Plot confidence history
        history = list(self.confidence_history)
        points = []
        
        for i, conf in enumerate(history):
            px = x + int(width * i / len(history))
            py = y + height - int(height * conf)
            points.append((px, py))
        
        # Draw line
        for i in range(len(points) - 1):
            color = (0, 255, 0) if history[i] >= 0.7 else (0, 255, 255) if history[i] >= 0.5 else (0, 0, 255)
            cv2.line(frame, points[i], points[i + 1], color, 2)
        
        # Labels
        cv2.putText(frame, "100%", (x + 5, y + 15),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
        cv2.putText(frame, "0%", (x + 5, y + height - 5),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
    
    def draw_compact_display(self, frame: np.ndarray, x: int, y: int,
                            name: str = "Unknown") -> None:
        """Draw compact confidence display near face box."""
        conf = self.smoothed_confidence
        level, color = self.get_confidence_level()
        
        # Confidence percentage
        text = f"{conf * 100:.0f}%"
        (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
        
        # Background
        cv2.rectangle(frame, (x - 5, y - th - 10), (x + tw + 5, y + 5), color, -1)
        
        # Text
        cv2.putText(frame, text, (x, y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    def should_alert(self) -> bool:
        """Check if confidence is too low and should alert."""
        return self.smoothed_confidence < 0.5
    
    def reset(self) -> None:
        """Reset confidence tracking."""
        self.confidence_history.clear()
        self.smoothed_confidence = 0.0
