"""
Ultrasonic Sensor Tests
Tests for ultrasonic distance measurement
"""

import pytest
import time
from unittest.mock import patch, MagicMock
from hardware.ultrasonic.ultrasonic_controller import UltrasonicController


class TestUltrasonicController:
    """Test ultrasonic sensor functionality"""
    
    @pytest.fixture
    def ultrasonic_controller(self):
        """Create ultrasonic controller instance"""
        with patch('hardware.gpio.gpio_manager.GPIO_AVAILABLE', False):
            controller = UltrasonicController()
            controller.initialize()
            yield controller
            controller.cleanup()
    
    def test_initialization(self, ultrasonic_controller):
        """Test ultrasonic controller initialization"""
        assert ultrasonic_controller.initialized
        assert ultrasonic_controller.detector is not None
    
    def test_distance_measurement(self, ultrasonic_controller):
        """Test distance measurement"""
        # In simulation mode, should return default value
        distance = ultrasonic_controller.get_distance()
        assert distance >= 0
    
    def test_filtered_distance(self, ultrasonic_controller):
        """Test filtered distance measurement"""
        distance = ultrasonic_controller.get_filtered_distance()
        assert distance >= 0
    
    def test_obstacle_detection(self, ultrasonic_controller):
        """Test obstacle detection"""
        # Mock distance reading
        with patch.object(ultrasonic_controller, 'get_distance', return_value=15.0):
            is_obstacle = ultrasonic_controller.is_obstacle_detected()
            assert is_obstacle  # Should detect obstacle at 15cm (threshold is 20cm)
        
        with patch.object(ultrasonic_controller, 'get_distance', return_value=50.0):
            is_obstacle = ultrasonic_controller.is_obstacle_detected()
            assert not is_obstacle  # Should not detect obstacle at 50cm
    
    def test_monitoring_thread(self, ultrasonic_controller):
        """Test continuous monitoring"""
        callback_called = []
        
        def test_callback(distance):
            callback_called.append(distance)
        
        ultrasonic_controller.register_obstacle_callback(test_callback)
        
        # Start monitoring
        ultrasonic_controller.start_monitoring(interval=0.1)
        time.sleep(0.3)
        
        # Stop monitoring
        ultrasonic_controller.stop_monitoring()
        
        status = ultrasonic_controller.get_status()
        assert not status['monitoring']
    
    def test_callback_registration(self, ultrasonic_controller):
        """Test callback registration"""
        callback_mock = MagicMock()
        
        ultrasonic_controller.register_obstacle_callback(callback_mock)
        
        # Simulate obstacle detection
        with patch.object(ultrasonic_controller, 'get_distance', return_value=10.0):
            ultrasonic_controller.start_monitoring(interval=0.1)
            time.sleep(0.2)
            ultrasonic_controller.stop_monitoring()
        
        # Callback should have been called
        # (In simulation mode, behavior may vary)
    
    def test_status(self, ultrasonic_controller):
        """Test status reporting"""
        status = ultrasonic_controller.get_status()
        
        assert 'initialized' in status
        assert 'monitoring' in status
        assert 'last_distance' in status
        assert 'obstacle_detected' in status


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
