"""
LED Controller
High-level RGB LED control with PWM and effects
"""

import threading
from typing import Tuple, Optional
from enum import Enum
from hardware.utils.logger import get_logger
from hardware.utils.threading_utils import thread_safe, StoppableThread
from hardware.gpio.pin_definitions import pin_defs
from hardware.gpio.pwm_manager import pwm_manager, PWMChannel
from hardware.led.led_effects import LEDEffects
from hardware.led.led_patterns import LEDPatterns


class LEDEffect(Enum):
    """LED effect types"""
    SOLID = "solid"
    BLINK = "blink"
    FADE = "fade"
    RAINBOW = "rainbow"
    POLICE = "police"
    PULSE = "pulse"


class LEDController:
    """
    High-level RGB LED controller
    Controls RGB LED with PWM for colors and effects
    """
    
    def __init__(self):
        self.logger = get_logger("led_controller")
        
        # LED pins
        led_pins = pin_defs.led
        self.red_pin = led_pins.red
        self.green_pin = led_pins.green
        self.blue_pin = led_pins.blue
        
        # PWM channels
        self.red_pwm: Optional[PWMChannel] = None
        self.green_pwm: Optional[PWMChannel] = None
        self.blue_pwm: Optional[PWMChannel] = None
        
        # State
        self.current_color = (0, 0, 0)
        self.brightness = 50
        self.current_effect = LEDEffect.SOLID
        self.effect_running = False
        self.effect_thread: Optional[StoppableThread] = None
        
        self.initialized = False
        self._lock = threading.RLock()
    
    def initialize(self):
        """Initialize LED controller"""
        with self._lock:
            if self.initialized:
                self.logger.warning("LED controller already initialized")
                return
            
            try:
                # Create PWM channels
                frequency = pwm_manager.get_led_frequency()
                self.red_pwm = pwm_manager.create_pwm(self.red_pin, frequency)
                self.green_pwm = pwm_manager.create_pwm(self.green_pin, frequency)
                self.blue_pwm = pwm_manager.create_pwm(self.blue_pin, frequency)
                
                # Start PWM at 0
                self.red_pwm.start(0)
                self.green_pwm.start(0)
                self.blue_pwm.start(0)
                
                self.initialized = True
                self.logger.info("LED controller initialized")
                
            except Exception as e:
                self.logger.error(f"Failed to initialize LED controller: {e}")
                raise
    
    @thread_safe
    def set_color(self, red: int, green: int, blue: int):
        """
        Set RGB color
        
        Args:
            red: Red value (0-255)
            green: Green value (0-255)
            blue: Blue value (0-255)
        """
        if not self.initialized:
            raise RuntimeError("LED controller not initialized")
        
        self.stop_effect()
        
        self.current_color = (red, green, blue)
        self._apply_color(red, green, blue)
        self.logger.debug(f"LED color set to RGB({red}, {green}, {blue})")
    
    @thread_safe
    def set_brightness(self, brightness: int):
        """
        Set brightness
        
        Args:
            brightness: Brightness (0-100)
        """
        self.brightness = max(0, min(100, brightness))
        self._apply_color(*self.current_color)
        self.logger.debug(f"LED brightness set to {self.brightness}%")
    
    @thread_safe
    def set_status_color(self, status: str):
        """
        Set color based on status
        
        Args:
            status: Status name (idle, moving, warning, emergency, etc.)
        """
        color = LEDPatterns.get_status_color(status)
        self.set_color(*color)
        self.logger.debug(f"LED status set to: {status}")
    
    @thread_safe
    def off(self):
        """Turn LED off"""
        self.stop_effect()
        self.set_color(0, 0, 0)
    
    @thread_safe
    def start_effect(self, effect: LEDEffect):
        """
        Start LED animation effect
        
        Args:
            effect: Effect type
        """
        self.stop_effect()
        
        self.current_effect = effect
        self.effect_running = True
        
        # Start effect thread
        self.effect_thread = StoppableThread(
            target=self._effect_loop,
            args=(effect,),
            name=f"LED-{effect.value}"
        )
        self.effect_thread.start()
        
        self.logger.debug(f"Started LED effect: {effect.value}")
    
    @thread_safe
    def stop_effect(self):
        """Stop current effect"""
        if self.effect_running:
            self.effect_running = False
            if self.effect_thread:
                self.effect_thread.stop()
                self.effect_thread.join(timeout=1.0)
            self.logger.debug("LED effect stopped")
    
    def get_status(self) -> dict:
        """Get LED controller status"""
        return {
            'color': self.current_color,
            'brightness': self.brightness,
            'effect': self.current_effect.value,
            'effect_running': self.effect_running,
            'initialized': self.initialized
        }
    
    def _apply_color(self, red: int, green: int, blue: int):
        """Apply color with brightness adjustment"""
        brightness_factor = self.brightness / 100.0
        
        r_duty = (red / 255.0) * 100 * brightness_factor
        g_duty = (green / 255.0) * 100 * brightness_factor
        b_duty = (blue / 255.0) * 100 * brightness_factor
        
        self.red_pwm.change_duty_cycle(r_duty)
        self.green_pwm.change_duty_cycle(g_duty)
        self.blue_pwm.change_duty_cycle(b_duty)
    
    def _effect_loop(self, effect: LEDEffect):
        """Effect animation loop"""
        try:
            if effect == LEDEffect.BLINK:
                LEDEffects.blink(
                    self._apply_color,
                    self.current_color,
                    running_check=lambda: self.effect_running
                )
            elif effect == LEDEffect.FADE:
                LEDEffects.fade(
                    self._apply_color,
                    self.current_color,
                    running_check=lambda: self.effect_running
                )
            elif effect == LEDEffect.RAINBOW:
                LEDEffects.rainbow(
                    self._apply_color,
                    running_check=lambda: self.effect_running
                )
            elif effect == LEDEffect.POLICE:
                LEDEffects.police(
                    self._apply_color,
                    running_check=lambda: self.effect_running
                )
            elif effect == LEDEffect.PULSE:
                LEDEffects.pulse(
                    self._apply_color,
                    self.current_color,
                    running_check=lambda: self.effect_running
                )
        except Exception as e:
            self.logger.error(f"Error in effect loop: {e}")
    
    def cleanup(self):
        """Cleanup LED controller"""
        with self._lock:
            self.stop_effect()
            self.off()
            self.logger.info("LED controller cleaned up")
