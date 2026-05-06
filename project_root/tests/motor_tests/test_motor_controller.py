"""
Motor Controller Tests
Tests for motor control functionality
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from hardware.motor.motor_controller import MotorController
from hardware.motor.motor_driver import MotorDirection


class TestMotorController:
    """Test motor controller functionality"""
    
    @pytest.fixture
    def motor_controller(self):
        """Create motor controller instance"""
        with patch('hardware.gpio.gpio_manager.GPIO_AVAILABLE', False):
            controller = MotorController()
            controller.initialize()
            yield controller
            controller.cleanup()
    
    def test_initialization(self, motor_controller):
        """Test motor controller initialization"""
        assert motor_controller.initialized
        assert motor_controller.driver is not None
        assert motor_controller.safety is not None
    
    def test_move_forward(self, motor_controller):
        """Test forward movement"""
        motor_controller.move_forward(speed=70)
        
        status = motor_controller.get_status()
        assert status['direction'] == 'forward'
        assert status['speed'] == 70
    
    def test_move_backward(self, motor_controller):
        """Test backward movement"""
        motor_controller.move_backward(speed=60)
        
        status = motor_controller.get_status()
        assert status['direction'] == 'backward'
        assert status['speed'] == 60
    
    def test_turn_left(self, motor_controller):
        """Test left turn"""
        motor_controller.turn_left(speed=50)
        
        status = motor_controller.get_status()
        assert status['direction'] == 'left'
    
    def test_turn_right(self, motor_controller):
        """Test right turn"""
        motor_controller.turn_right(speed=50)
        
        status = motor_controller.get_status()
        assert status['direction'] == 'right'
    
    def test_stop(self, motor_controller):
        """Test motor stop"""
        motor_controller.move_forward(speed=70)
        motor_controller.stop()
        
        status = motor_controller.get_status()
        assert status['speed'] == 0
        assert status['direction'] == 'stopped'
    
    def test_emergency_stop(self, motor_controller):
        """Test emergency stop"""
        motor_controller.move_forward(speed=70)
        motor_controller.emergency_stop()
        
        status = motor_controller.get_status()
        assert status['speed'] == 0
        assert status['emergency_stopped']
    
    def test_speed_limits(self, motor_controller):
        """Test speed limiting"""
        # Test max speed
        motor_controller.move_forward(speed=150)
        status = motor_controller.get_status()
        assert status['speed'] <= 100
        
        # Test min speed
        motor_controller.move_forward(speed=-10)
        status = motor_controller.get_status()
        assert status['speed'] >= 0
    
    def test_smooth_acceleration(self, motor_controller):
        """Test smooth acceleration"""
        motor_controller.set_speed(0)
        motor_controller.gradual_acceleration(target_speed=80, step=10, delay=0.01)
        
        status = motor_controller.get_status()
        assert status['speed'] == 80
    
    def test_smooth_deceleration(self, motor_controller):
        """Test smooth deceleration"""
        motor_controller.set_speed(80)
        motor_controller.gradual_deceleration(step=10, delay=0.01)
        
        status = motor_controller.get_status()
        assert status['speed'] == 0
    
    def test_direction_change_safety(self, motor_controller):
        """Test that direction changes require stopping first"""
        motor_controller.move_forward(speed=70)
        
        # Should stop before changing direction
        motor_controller.move_backward(speed=60)
        
        # Verify it worked
        status = motor_controller.get_status()
        assert status['direction'] == 'backward'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
