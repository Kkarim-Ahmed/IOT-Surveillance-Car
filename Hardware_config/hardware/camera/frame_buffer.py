"""
Frame Buffer
Thread-safe frame buffering for camera
"""

import threading
from queue import Queue, Full, Empty
from typing import Optional
import numpy as np
from hardware.utils.logger import get_logger


class FrameBuffer:
    """Thread-safe frame buffer with size limit"""
    
    def __init__(self, max_size: int = 10):
        """
        Initialize frame buffer
        
        Args:
            max_size: Maximum number of frames to buffer
        """
        self.logger = get_logger("frame_buffer")
        self.max_size = max_size
        self.queue = Queue(maxsize=max_size)
        self._lock = threading.RLock()
        
        # Statistics
        self.frames_added = 0
        self.frames_dropped = 0
        self.frames_retrieved = 0
    
    def add_frame(self, frame: np.ndarray, block: bool = False, timeout: Optional[float] = None) -> bool:
        """
        Add frame to buffer
        
        Args:
            frame: Frame to add
            block: If True, block until space available
            timeout: Timeout for blocking
            
        Returns:
            True if frame was added
        """
        try:
            self.queue.put(frame, block=block, timeout=timeout)
            self.frames_added += 1
            return True
        except Full:
            self.frames_dropped += 1
            return False
    
    def get_frame(self, block: bool = True, timeout: Optional[float] = 1.0) -> Optional[np.ndarray]:
        """
        Get frame from buffer
        
        Args:
            block: If True, block until frame available
            timeout: Timeout for blocking
            
        Returns:
            Frame or None if not available
        """
        try:
            frame = self.queue.get(block=block, timeout=timeout)
            self.frames_retrieved += 1
            return frame
        except Empty:
            return None
    
    def get_latest_frame(self) -> Optional[np.ndarray]:
        """
        Get latest frame, discarding older frames
        
        Returns:
            Latest frame or None
        """
        frame = None
        while not self.queue.empty():
            try:
                frame = self.queue.get_nowait()
            except Empty:
                break
        return frame
    
    def clear(self):
        """Clear all frames from buffer"""
        with self._lock:
            while not self.queue.empty():
                try:
                    self.queue.get_nowait()
                except Empty:
                    break
    
    def size(self) -> int:
        """Get current buffer size"""
        return self.queue.qsize()
    
    def is_full(self) -> bool:
        """Check if buffer is full"""
        return self.queue.full()
    
    def is_empty(self) -> bool:
        """Check if buffer is empty"""
        return self.queue.empty()
    
    def get_stats(self) -> dict:
        """Get buffer statistics"""
        return {
            'size': self.size(),
            'max_size': self.max_size,
            'frames_added': self.frames_added,
            'frames_dropped': self.frames_dropped,
            'frames_retrieved': self.frames_retrieved,
            'drop_rate': self.frames_dropped / max(1, self.frames_added) * 100
        }
