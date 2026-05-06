"""
Stream Handler
Manages camera stream capture and processing
"""

import time
import cv2
import numpy as np
from typing import Optional
from hardware.utils.logger import get_logger
from hardware.utils.timing_utils import RateLimiter


class StreamHandler:
    """Handles camera stream capture"""
    
    def __init__(self, camera, target_fps: int = 30):
        """
        Initialize stream handler
        
        Args:
            camera: OpenCV camera object
            target_fps: Target frames per second
        """
        self.logger = get_logger("stream_handler")
        self.camera = camera
        self.target_fps = target_fps
        
        # Rate limiting
        self.rate_limiter = RateLimiter(target_fps)
        
        # Statistics
        self.frame_count = 0
        self.fps = 0.0
        self.last_fps_time = time.time()
    
    def capture_frame(self) -> Optional[np.ndarray]:
        """
        Capture single frame
        
        Returns:
            Frame or None if capture failed
        """
        try:
            ret, frame = self.camera.read()
            
            if ret:
                self.frame_count += 1
                self._update_fps()
                return frame
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error capturing frame: {e}")
            return None
    
    def capture_frame_rate_limited(self) -> Optional[np.ndarray]:
        """
        Capture frame with rate limiting
        
        Returns:
            Frame or None
        """
        self.rate_limiter.wait()
        return self.capture_frame()
    
    def resize_frame(self, frame: np.ndarray, width: int, height: int) -> np.ndarray:
        """
        Resize frame
        
        Args:
            frame: Input frame
            width: Target width
            height: Target height
            
        Returns:
            Resized frame
        """
        return cv2.resize(frame, (width, height))
    
    def rotate_frame(self, frame: np.ndarray, angle: int) -> np.ndarray:
        """
        Rotate frame
        
        Args:
            frame: Input frame
            angle: Rotation angle (0, 90, 180, 270)
            
        Returns:
            Rotated frame
        """
        if angle == 90:
            return cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
        elif angle == 180:
            return cv2.rotate(frame, cv2.ROTATE_180)
        elif angle == 270:
            return cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
        return frame
    
    def flip_frame(self, frame: np.ndarray, horizontal: bool = False, 
                   vertical: bool = False) -> np.ndarray:
        """
        Flip frame
        
        Args:
            frame: Input frame
            horizontal: Flip horizontally
            vertical: Flip vertically
            
        Returns:
            Flipped frame
        """
        if horizontal and vertical:
            return cv2.flip(frame, -1)
        elif horizontal:
            return cv2.flip(frame, 1)
        elif vertical:
            return cv2.flip(frame, 0)
        return frame
    
    def get_fps(self) -> float:
        """Get current FPS"""
        return self.fps
    
    def _update_fps(self):
        """Update FPS calculation"""
        current_time = time.time()
        elapsed = current_time - self.last_fps_time
        
        if elapsed >= 1.0:
            self.fps = self.frame_count / elapsed
            self.frame_count = 0
            self.last_fps_time = current_time
