"""
PWM Manager
Centralized PWM control with thread-safe operations
"""

import threading
import yaml
from pathlib import Path
from typing import Dict, Optional
from hardware.utils.logger import get_logger
from hardware.gpio.gpio_manager import gpio_manager, GPIO_AVAILABLE

if GPIO_AVAILABLE:
    import RPi.GPIO as GPIO


class PWMChannel:
    """Represents a single PWM channel"""
    
    def __init__(self, pin: int, frequency: float, gpio_pwm=None):
        self.pin = pin
        self.frequency = frequency
        self.duty_cycle = 0.0
        self.running = False
        self.gpio_pwm = gpio_pwm
        self.lock = threading.RLock()
    
    def start(self, duty_cycle: float = 0.0):
        """Start PWM"""
        with self.lock:
            if self.gpio_pwm and not gpio_manager.simulation_mode:
                self.gpio_pwm.start(duty_cycle)
            self.duty_cycle = duty_cycle
            self.running = True
    
    def stop(self):
        """Stop PWM"""
        with self.lock:
            if self.gpio_pwm and not gpio_manager.simulation_mode:
                self.gpio_pwm.stop()
            self.running = False
            self.duty_cycle = 0.0
    
    def change_duty_cycle(self, duty_cycle: float):
        """Change PWM duty cycle"""
        with self.lock:
            if not self.running:
                raise RuntimeError(f"PWM on pin {self.pin} not started")
            
            # Validate duty cycle
            if not (0 <= duty_cycle <= 100):
                raise ValueError(f"Invalid duty cycle: {duty_cycle}. Must be 0-100")
            
            if self.gpio_pwm and not gpio_manager.simulation_mode:
                self.gpio_pwm.ChangeDutyCycle(duty_cycle)
            
            self.duty_cycle = duty_cycle
    
    def change_frequency(self, frequency: float):
        """Change PWM frequency"""
        with self.lock:
            if not self.running:
                raise RuntimeError(f"PWM on pin {self.pin} not started")
            
            if self.gpio_pwm and not gpio_manager.simulation_mode:
                self.gpio_pwm.ChangeFrequency(frequency)
            
            self.frequency = frequency


class PWMManager:
    """
    Centralized PWM management system
    Provides thread-safe PWM operations
    """
    
    _instance: Optional['PWMManager'] = None
    _lock = threading.RLock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
            return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self.logger = get_logger("pwm_manager")
            self.channels: Dict[int, PWMChannel] = {}
            self._load_config()
            self._initialized = True
    
    def _load_config(self):
        """Load PWM configuration"""
        config_path = Path("configs/pwm_config.yaml")
        
        if config_path.exists():
            with open(config_path, 'r') as f:
                self.config = yaml.safe_load(f)
        else:
            self.logger.warning("PWM config not found, using defaults")
            self.config = {
                'motor': {'frequency': 1000},
                'servo': {'frequency': 50},
                'led': {'frequency': 1000}
            }
    
    def create_pwm(self, pin: int, frequency: float) -> PWMChannel:
        """
        Create PWM channel
        
        Args:
            pin: GPIO pin number
            frequency: PWM frequency in Hz
            
        Returns:
            PWMChannel instance
        """
        with self._lock:
            if pin in self.channels:
                self.logger.warning(f"PWM channel already exists on pin {pin}")
                return self.channels[pin]
            
            # Ensure pin is setup as output
            if not gpio_manager.is_pin_active(pin):
                gpio_manager.setup_output(pin)
            
            # Create GPIO PWM instance
            gpio_pwm = None
            if not gpio_manager.simulation_mode:
                gpio_pwm = GPIO.PWM(pin, frequency)
            
            # Create channel
            channel = PWMChannel(pin, frequency, gpio_pwm)
            self.channels[pin] = channel
            
            self.logger.debug(f"Created PWM channel on pin {pin} at {frequency}Hz")
            return channel
    
    def get_channel(self, pin: int) -> Optional[PWMChannel]:
        """Get existing PWM channel"""
        return self.channels.get(pin)
    
    def remove_channel(self, pin: int):
        """Remove PWM channel"""
        with self._lock:
            if pin in self.channels:
                channel = self.channels[pin]
                if channel.running:
                    channel.stop()
                del self.channels[pin]
                self.logger.debug(f"Removed PWM channel on pin {pin}")
    
    def stop_all(self):
        """Stop all PWM channels"""
        with self._lock:
            for channel in self.channels.values():
                if channel.running:
                    channel.stop()
            self.logger.info("All PWM channels stopped")
    
    def cleanup(self):
        """Cleanup all PWM channels"""
        with self._lock:
            self.stop_all()
            self.channels.clear()
            self.logger.info("PWM manager cleaned up")
    
    def get_motor_frequency(self) -> float:
        """Get configured motor PWM frequency"""
        return self.config.get('motor', {}).get('frequency', 1000)
    
    def get_servo_frequency(self) -> float:
        """Get configured servo PWM frequency"""
        return self.config.get('servo', {}).get('frequency', 50)
    
    def get_led_frequency(self) -> float:
        """Get configured LED PWM frequency"""
        return self.config.get('led', {}).get('frequency', 1000)


# Global instance
pwm_manager = PWMManager()
