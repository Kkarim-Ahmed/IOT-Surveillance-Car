"""
Camera Controller
High-level camera control with threaded capture
"""

import cv2
import threading
from typing import Optional
from pathlib import Path
from hardware.utils.logger import get_logger
from hardware.utils.threading_utils import thread_safe, StoppableThread
from hardware.camera.frame_buffer import FrameBuffer
from hardware.camera.stream_handler import StreamHandler


class CameraController:
    """
    High-level camera controller
    Manages camera capture with threaded operation
    """
    
    def __init__(self, device_id: int = 0, resolution: tuple = (640, 480), fps: int = 30):
        """
        Initialize camera controller
        
        Args:
            device_id: Camera device ID
            resolution: Camera resolution (width, height)
            fps: Target frames per second
        """
        self.logger = get_logger("camera_controller")
        
        # Configuration
        self.device_id = device_id
        self.resolution = resolution
        self.target_fps = fps
        
        # Camera
        self.camera = None
        self.stream_handler: Optional[StreamHandler] = None
        
        # Frame buffers
        self.main_buffer = FrameBuffer(max_size=10)
        self.ai_buffer = FrameBuffer(max_size=5)
        
        # Capture thread
        self.is_capturing = False
        self.capture_thread: Optional[StoppableThread] = None
        
        # State
        self.initialized = False
        self._lock = threading.RLock()
    
    def initialize(self):
        """Initialize camera"""
        with self._lock:
            if self.initialized:
                self.logger.warning("Camera already initialized")
                return
            
            try:
                # Open camera
                self.camera = cv2.VideoCapture(self.device_id)
                
                if not self.camera.isOpened():
                    raise RuntimeError("Failed to open camera")
                
                # Configure camera
                self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
                self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])
                self.camera.set(cv2.CAP_PROP_FPS, self.target_fps)
                
                # Create stream handler
                self.stream_handler = StreamHandler(self.camera, self.target_fps)
                
                self.initialized = True
                self.logger.info(f"Camera initialized: {self.resolution[0]}x{self.resolution[1]} @ {self.target_fps}fps")
                
            except Exception as e:
                self.logger.error(f"Failed to initialize camera: {e}")
                if self.camera:
                    self.camera.release()
                raise
    
    @thread_safe
    def start_capture(self):
        """Start camera capture thread"""
        if self.is_capturing:
            self.logger.warning("Capture already running")
            return
        
        if not self.initialized:
            raise RuntimeError("Camera not initialized")
        
        self.is_capturing = True
        
        self.capture_thread = StoppableThread(
            target=self._capture_loop,
            name="Camera-Capture"
        )
        self.capture_thread.start()
        
        self.logger.info("Camera capture started")
    
    @thread_safe
    def stop_capture(self):
        """Stop camera capture thread"""
        if self.is_capturing:
            self.is_capturing = False
            if self.capture_thread:
                self.capture_thread.stop()
                self.capture_thread.join(timeout=2.0)
            self.logger.info("Camera capture stopped")
    
    def get_frame(self, timeout: float = 1.0) -> Optional:
        """
        Get frame from main buffer
        
        Args:
            timeout: Timeout in seconds
            
        Returns:
            Frame or None
        """
        return self.main_buffer.get_frame(timeout=timeout)
    
    def get_latest_frame(self) -> Optional:
        """Get latest frame, discarding older frames"""
        return self.main_buffer.get_latest_frame()
    
    def get_ai_frame(self, timeout: float = 1.0) -> Optional:
        """
        Get frame from AI buffer
        
        Args:
            timeout: Timeout in seconds
            
        Returns:
            Frame or None
        """
        return self.ai_buffer.get_frame(timeout=timeout)
    
    @thread_safe
    def capture_snapshot(self, filepath: str) -> bool:
        """
        Capture and save snapshot
        
        Args:
            filepath: Path to save snapshot
            
        Returns:
            True if successful
        """
        try:
            frame = self.get_latest_frame()
            
            if frame is None:
                self.logger.error("No frame available for snapshot")
                return False
            
            # Ensure directory exists
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)
            
            # Save frame
            cv2.imwrite(filepath, frame)
            self.logger.info(f"Snapshot saved: {filepath}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to capture snapshot: {e}")
            return False
    
    def get_status(self) -> dict:
        """Get camera status"""
        return {
            'capturing': self.is_capturing,
            'fps': self.stream_handler.get_fps() if self.stream_handler else 0,
            'main_buffer': self.main_buffer.get_stats(),
            'ai_buffer': self.ai_buffer.get_stats(),
            'resolution': self.resolution,
            'initialized': self.initialized
        }
    
    def _capture_loop(self):
        """Main capture loop"""
        ai_frame_counter = 0
        ai_frame_interval = 2  # Capture AI frame every N frames
        
        while self.is_capturing and not self.capture_thread.stopped():
            try:
                # Capture frame
                frame = self.stream_handler.capture_frame_rate_limited()
                
                if frame is not None:
                    # Add to main buffer
                    self.main_buffer.add_frame(frame.copy(), block=False)
                    
                    # Add to AI buffer (at lower rate)
                    ai_frame_counter += 1
                    if ai_frame_counter >= ai_frame_interval:
                        ai_frame_counter = 0
                        # Resize for AI processing
                        ai_frame = cv2.resize(frame, (320, 240))
                        self.ai_buffer.add_frame(ai_frame, block=False)
                
            except Exception as e:
                self.logger.error(f"Error in capture loop: {e}")
    
    def cleanup(self):
        """Cleanup camera"""
        with self._lock:
            self.stop_capture()
            
            if self.camera:
                self.camera.release()
            
            self.main_buffer.clear()
            self.ai_buffer.clear()
            
            self.logger.info("Camera cleaned up")
