"""
Hardware Manager Integration Tests
Tests for complete hardware system integration
"""

import pytest
import time
from unittest.mock import patch
from hardware.managers.hardware_manager import hardware_manager
from hardware.safety.emergency_stop import EmergencyTrigger


class TestHardwareManager:
    """Test hardware manager integration"""
    
    @pytest.fixture
    def manager(self):
        """Create hardware manager instance"""
        with patch('hardware.gpio.gpio_manager.GPIO_AVAILABLE', False):
            with patch('cv2.VideoCapture'):
                # Initialize
                hardware_manager.initialize()
                yield hardware_manager
                # Cleanup
                hardware_manager.cleanup()
    
    def test_initialization(self, manager):
        """Test hardware manager initialization"""
        assert manager.initialized
        assert manager.motor is not None
        assert manager.servo is not None
        assert manager.led is not None
        assert manager.ultrasonic is not None
        assert manager.camera is not None
    
    def test_get_status(self, manager):
        """Test status reporting"""
        status = manager.get_status()
        
        assert 'initialized' in status
        assert 'emergency' in status
        assert 'watchdog' in status
        assert 'health' in status
        assert 'motor' in status
        assert 'servo' in status
        assert 'led' in status
        assert 'ultrasonic' in status
        assert 'camera' in status
    
    def test_heartbeat(self, manager):
        """Test heartbeat system"""
        # Send heartbeats
        manager.heartbeat('motor')
        manager.heartbeat('servo')
        manager.heartbeat('ultrasonic')
        manager.heartbeat('camera')
        
        # Should not trigger watchdog
        status = manager.get_status()
        assert not status['emergency']['active']
    
    def test_emergency_trigger(self, manager):
        """Test emergency stop trigger"""
        # Trigger emergency
        manager.trigger_emergency(EmergencyTrigger.MANUAL, "Test emergency")
        
        status = manager.get_status()
        assert status['emergency']['active']
        
        # Reset emergency
        manager.reset_emergency()
        status = manager.get_status()
        assert not status['emergency']['active']
    
    def test_motor_integration(self, manager):
        """Test motor control through manager"""
        # Move forward
        manager.motor.move_forward(speed=70)
        
        status = manager.get_status()
        assert status['motor']['direction'] == 'forward'
        assert status['motor']['speed'] == 70
        
        # Stop
        manager.motor.stop()
        status = manager.get_status()
        assert status['motor']['speed'] == 0
    
    def test_servo_integration(self, manager):
        """Test servo control through manager"""
        # Set angle
        manager.servo.set_angle(pan=45, tilt=20)
        
        status = manager.get_status()
        assert status['servo']['pan']['angle'] == 45
        assert status['servo']['tilt']['angle'] == 20
    
    def test_led_integration(self, manager):
        """Test LED control through manager"""
        # Set color
        manager.led.set_color(255, 0, 0)
        
        status = manager.get_status()
        assert status['led']['color'] == (255, 0, 0)
    
    def test_ultrasonic_integration(self, manager):
        """Test ultrasonic sensor through manager"""
        distance = manager.ultrasonic.get_distance()
        
        assert distance >= 0
        
        status = manager.get_status()
        assert 'last_distance' in status['ultrasonic']
    
    def test_camera_integration(self, manager):
        """Test camera through manager"""
        frame = manager.camera.get_latest_frame()
        
        # In test environment, may be None
        status = manager.get_status()
        assert 'frames_captured' in status['camera']
    
    def test_emergency_handler(self, manager):
        """Test emergency handler integration"""
        # Trigger emergency
        manager.trigger_emergency(EmergencyTrigger.OBSTACLE_DETECTED, "Test obstacle")
        
        # Motor should be stopped
        motor_status = manager.motor.get_status()
        assert motor_status['speed'] == 0
        
        # LED should be red
        led_status = manager.led.get_status()
        assert led_status['color'] == (255, 0, 0)
    
    def test_watchdog_integration(self, manager):
        """Test watchdog monitoring"""
        # Watchdog should be running
        watchdog_status = manager.watchdog.get_status()
        assert watchdog_status['running']
        
        # Send heartbeats
        for _ in range(3):
            manager.heartbeat('motor')
            time.sleep(0.1)
        
        # Should not trigger emergency
        status = manager.get_status()
        assert not status['emergency']['active']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
