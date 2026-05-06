"""
LED Controller Tests
Tests for LED control functionality
"""

import pytest
import time
from unittest.mock import patch
from hardware.led.led_controller import LEDController, LEDEffect


class TestLEDController:
    """Test LED controller functionality"""
    
    @pytest.fixture
    def led_controller(self):
        """Create LED controller instance"""
        with patch('hardware.gpio.gpio_manager.GPIO_AVAILABLE', False):
            controller = LEDController()
            controller.initialize()
            yield controller
            controller.cleanup()
    
    def test_initialization(self, led_controller):
        """Test LED controller initialization"""
        assert led_controller.initialized
        assert led_controller.red_pwm is not None
        assert led_controller.green_pwm is not None
        assert led_controller.blue_pwm is not None
    
    def test_set_color(self, led_controller):
        """Test setting LED color"""
        led_controller.set_color(255, 0, 0)  # Red
        
        status = led_controller.get_status()
        assert status['color'] == (255, 0, 0)
    
    def test_color_validation(self, led_controller):
        """Test color value validation"""
        # Test values beyond range
        led_controller.set_color(300, -10, 128)
        
        status = led_controller.get_status()
        r, g, b = status['color']
        assert 0 <= r <= 255
        assert 0 <= g <= 255
        assert 0 <= b <= 255
    
    def test_brightness(self, led_controller):
        """Test brightness control"""
        led_controller.set_color(255, 255, 255)
        led_controller.set_brightness(50)
        
        status = led_controller.get_status()
        assert status['brightness'] == 50
    
    def test_status_colors(self, led_controller):
        """Test status color presets"""
        # Test idle status
        led_controller.set_status_color('idle')
        status = led_controller.get_status()
        assert status['color'] == (0, 255, 0)  # Green
        
        # Test moving status
        led_controller.set_status_color('moving')
        status = led_controller.get_status()
        assert status['color'] == (0, 0, 255)  # Blue
        
        # Test emergency status
        led_controller.set_status_color('emergency')
        status = led_controller.get_status()
        assert status['color'] == (255, 0, 0)  # Red
    
    def test_turn_off(self, led_controller):
        """Test turning LED off"""
        led_controller.set_color(255, 255, 255)
        led_controller.turn_off()
        
        status = led_controller.get_status()
        assert status['color'] == (0, 0, 0)
    
    def test_effects(self, led_controller):
        """Test LED effects"""
        # Test rainbow effect
        led_controller.start_effect(LEDEffect.RAINBOW)
        time.sleep(0.1)
        
        status = led_controller.get_status()
        assert status['effect'] == LEDEffect.RAINBOW
        assert status['effect_running']
        
        # Stop effect
        led_controller.stop_effect()
        status = led_controller.get_status()
        assert not status['effect_running']
    
    def test_blink_effect(self, led_controller):
        """Test blink effect"""
        led_controller.start_effect(LEDEffect.BLINK)
        time.sleep(0.2)
        led_controller.stop_effect()
        
        # Should complete without error
        assert True
    
    def test_fade_effect(self, led_controller):
        """Test fade effect"""
        led_controller.start_effect(LEDEffect.FADE)
        time.sleep(0.2)
        led_controller.stop_effect()
        
        # Should complete without error
        assert True
    
    def test_pulse_effect(self, led_controller):
        """Test pulse effect"""
        led_controller.start_effect(LEDEffect.PULSE)
        time.sleep(0.2)
        led_controller.stop_effect()
        
        # Should complete without error
        assert True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
