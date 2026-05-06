"""
Servo Controller Tests
Tests for servo control functionality
"""

import pytest
import time
from unittest.mock import patch
from hardware.servo.servo_controller import ServoController


class TestServoController:
    """Test servo controller functionality"""
    
    @pytest.fixture
    def servo_controller(self):
        """Create servo controller instance"""
        with patch('hardware.gpio.gpio_manager.GPIO_AVAILABLE', False):
            controller = ServoController()
            controller.initialize()
            yield controller
            controller.cleanup()
    
    def test_initialization(self, servo_controller):
        """Test servo controller initialization"""
        assert servo_controller.initialized
        assert servo_controller.pan_servo is not None
        assert servo_controller.tilt_servo is not None
    
    def test_set_angle(self, servo_controller):
        """Test setting servo angles"""
        servo_controller.set_angle(pan=45, tilt=20)
        
        status = servo_controller.get_status()
        assert status['pan']['angle'] == 45
        assert status['tilt']['angle'] == 20
    
    def test_angle_limits(self, servo_controller):
        """Test angle limiting"""
        # Test pan limits
        servo_controller.set_angle(pan=120)  # Beyond limit
        status = servo_controller.get_status()
        assert -90 <= status['pan']['angle'] <= 90
        
        # Test tilt limits
        servo_controller.set_angle(tilt=60)  # Beyond limit
        status = servo_controller.get_status()
        assert -45 <= status['tilt']['angle'] <= 45
    
    def test_center_position(self, servo_controller):
        """Test centering servos"""
        servo_controller.set_angle(pan=45, tilt=30)
        servo_controller.center()
        
        status = servo_controller.get_status()
        assert status['pan']['angle'] == 0
        assert status['tilt']['angle'] == 0
    
    def test_preset_positions(self, servo_controller):
        """Test preset positions"""
        # Test home position
        servo_controller.move_to_preset('home')
        status = servo_controller.get_status()
        assert status['pan']['angle'] == 0
        assert status['tilt']['angle'] == 0
        
        # Test look_left position
        servo_controller.move_to_preset('look_left')
        status = servo_controller.get_status()
        assert status['pan']['angle'] == 90
    
    def test_smooth_movement(self, servo_controller):
        """Test smooth servo movement"""
        servo_controller.set_angle(pan=0, tilt=0)
        servo_controller.move_smooth(pan=45, tilt=20, steps=5, delay=0.01)
        
        status = servo_controller.get_status()
        assert status['pan']['angle'] == 45
        assert status['tilt']['angle'] == 20
    
    def test_scan_pattern(self, servo_controller):
        """Test scanning pattern"""
        servo_controller.scan_horizontal(start=-45, end=45, step=15, delay=0.01)
        
        # Should complete without error
        status = servo_controller.get_status()
        assert status['initialized']
    
    def test_invalid_preset(self, servo_controller):
        """Test handling of invalid preset"""
        with pytest.raises(ValueError):
            servo_controller.move_to_preset('invalid_preset')


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
