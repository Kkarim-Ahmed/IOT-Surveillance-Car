"""
Video Stream Handler - Optimized for Low Latency
Handles webcam capture, JPEG encoding, and async broadcasting
"""

import asyncio
import logging
import time
from typing import Set, Optional
import threading

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    logging.warning("OpenCV not available, video streaming disabled")

from . import config

logger = logging.getLogger(__name__)


class VideoStreamHandler:
    """Handles video capture and streaming with optimization"""
    
    def __init__(self):
        self.camera = None
        self.running = False
        self.frame_queue = asyncio.Queue(maxsize=config.ASYNC_QUEUE_MAXSIZE)
        self.capture_thread = None
        self.stats = {
            "frames_captured": 0,
            "frames_dropped": 0,
            "frames_sent": 0,
            "fps": 0,
            "last_fps_update": time.time()
        }
        
    def start(self):
        """Start video capture"""
        if not CV2_AVAILABLE or not config.VIDEO_ENABLED:
            logger.warning("Video streaming is disabled or OpenCV not available")
            return False
        
        try:
            logger.info(f"Initializing camera {config.VIDEO_CAMERA_INDEX}...")
            self.camera = cv2.VideoCapture(config.VIDEO_CAMERA_INDEX)
            
            if not self.camera.isOpened():
                logger.error("Failed to open camera")
                return False
            
            # Configure camera for low latency
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, config.VIDEO_WIDTH)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, config.VIDEO_HEIGHT)
            self.camera.set(cv2.CAP_PROP_FPS, config.VIDEO_FPS)
            self.camera.set(cv2.CAP_PROP_BUFFERSIZE, config.VIDEO_BUFFER_SIZE)
            
            # Verify settings
            actual_width = int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
            actual_fps = int(self.camera.get(cv2.CAP_PROP_FPS))
            
            logger.info(f"Camera initialized: {actual_width}x{actual_height} @ {actual_fps}fps")
            
            self.running = True
            
            # Start capture thread
            self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
            self.capture_thread.start()
            
            logger.info("Video streaming started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start video capture: {e}")
            return False
    
    def _capture_loop(self):
        """Capture frames in separate thread (blocking I/O)"""
        frame_interval = 1.0 / config.VIDEO_FPS
        last_capture_time = time.time()
        
        while self.running:
            try:
                current_time = time.time()
                elapsed = current_time - last_capture_time
                
                # Frame rate limiting
                if elapsed < frame_interval:
                    time.sleep(frame_interval - elapsed)
                    continue
                
                last_capture_time = current_time
                
                # Capture frame
                ret, frame = self.camera.read()
                
                if not ret:
                    logger.warning("Failed to capture frame")
                    continue
                
                # Encode to JPEG
                encode_params = [cv2.IMWRITE_JPEG_QUALITY, config.VIDEO_JPEG_QUALITY]
                ret, jpeg_buffer = cv2.imencode('.jpg', frame, encode_params)
                
                if not ret:
                    logger.warning("Failed to encode frame")
                    continue
                
                jpeg_bytes = jpeg_buffer.tobytes()
                
                # Put in async queue (non-blocking)
                try:
                    self.frame_queue.put_nowait(jpeg_bytes)
                    self.stats["frames_captured"] += 1
                except asyncio.QueueFull:
                    # Drop frame if queue is full (prevent backlog)
                    self.stats["frames_dropped"] += 1
                
                # Update FPS stats
                if current_time - self.stats["last_fps_update"] >= 1.0:
                    self.stats["fps"] = self.stats["frames_captured"]
                    self.stats["frames_captured"] = 0
                    self.stats["last_fps_update"] = current_time
                    
            except Exception as e:
                logger.error(f"Error in capture loop: {e}")
                time.sleep(0.1)
    
    async def get_frame(self) -> Optional[bytes]:
        """Get next frame (async)"""
        try:
            frame = await asyncio.wait_for(
                self.frame_queue.get(),
                timeout=1.0
            )
            return frame
        except asyncio.TimeoutError:
            return None
    
    async def broadcast_frames(self, clients: Set):
        """Broadcast frames to all connected WebSocket clients"""
        if not self.running:
            return
        
        while self.running:
            try:
                # Get frame from queue
                frame = await self.get_frame()
                
                if frame is None:
                    continue
                
                # Create packet: [TAG][FRAME_DATA]
                packet = bytes([config.PACKET_TAG_VIDEO]) + frame
                
                # Broadcast to all clients (async)
                if clients:
                    # Send to all clients concurrently
                    send_tasks = []
                    for client in list(clients):
                        send_tasks.append(self._send_frame_to_client(client, packet))
                    
                    # Wait for all sends (with timeout)
                    await asyncio.gather(*send_tasks, return_exceptions=True)
                    
                    self.stats["frames_sent"] += 1
                    
            except Exception as e:
                logger.error(f"Error broadcasting frame: {e}")
                await asyncio.sleep(0.01)
    
    async def _send_frame_to_client(self, client, packet):
        """Send frame to single client with error handling"""
        try:
            await asyncio.wait_for(
                client.send(packet),
                timeout=config.VIDEO_FRAME_DROP_THRESHOLD
            )
        except asyncio.TimeoutError:
            logger.debug("Client too slow, dropping frame")
        except Exception as e:
            logger.debug(f"Failed to send frame to client: {e}")
    
    def stop(self):
        """Stop video capture"""
        logger.info("Stopping video capture...")
        self.running = False
        
        if self.capture_thread:
            self.capture_thread.join(timeout=2)
        
        if self.camera:
            self.camera.release()
        
        logger.info("Video capture stopped")
    
    def get_stats(self) -> dict:
        """Get streaming statistics"""
        return {
            "fps": self.stats["fps"],
            "frames_sent": self.stats["frames_sent"],
            "frames_dropped": self.stats["frames_dropped"],
            "queue_size": self.frame_queue.qsize()
        }
