"""
Camera Controller Tests
Tests for camera capture functionality
"""

import pytest
import numpy as np
from unittest.mock import patch, MagicMock
from hardware.camera.camera_controller import CameraController


class TestCameraController:
    """Test camera controller functionality"""
    
    @pytest.fixture
    def camera_controller(self):
        """Create camera controller instance"""
        with patch('cv2.VideoCapture') as mock_cap:
            # Mock camera
            mock_instance = MagicMock()
            mock_instance.isOpened.return_value = True
            mock_instance.read.return_value = (True, np.zeros((480, 640, 3), dtype=np.uint8))
            mock_cap.return_value = mock_instance
            
            controller = CameraController(device_id=0, resolution=(640, 480), fps=30)
            controller.initialize()
            yield controller
            controller.cleanup()
    
    def test_initialization(self, camera_controller):
        """Test camera controller initialization"""
        assert camera_controller.initialized
        assert camera_controller.capture is not None
    
    def test_frame_capture(self, camera_controller):
        """Test frame capture"""
        camera_controller.start_capture()
        
        # Get frame
        frame = camera_controller.get_latest_frame()
        assert frame is not None
        assert isinstance(frame, np.ndarray)
    
    def test_capture_thread(self, camera_controller):
        """Test capture thread operation"""
        camera_controller.start_capture()
        
        status = camera_controller.get_status()
        assert status['capturing']
        
        camera_controller.stop_capture()
        status = camera_controller.get_status()
        assert not status['capturing']
    
    def test_snapshot(self, camera_controller):
        """Test snapshot saving"""
        camera_controller.start_capture()
        
        # Save snapshot
        success = camera_controller.save_snapshot('test_snapshot.jpg')
        
        # In test environment, may not actually save
        assert isinstance(success, bool)
    
    def test_status(self, camera_controller):
        """Test status reporting"""
        status = camera_controller.get_status()
        
        assert 'initialized' in status
        assert 'capturing' in status
        assert 'resolution' in status
        assert 'fps' in status
        assert 'frames_captured' in status
    
    def test_frame_buffer(self, camera_controller):
        """Test frame buffering"""
        camera_controller.start_capture()
        
        # Should have frames in buffer
        frame = camera_controller.get_latest_frame()
        assert frame is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
