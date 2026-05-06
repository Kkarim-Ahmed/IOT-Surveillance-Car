"""
Motor Driver
Low-level L298N motor driver interface
"""

import time
from typing import Tuple
from hardware.utils.logger import get_logger
from hardware.gpio.gpio_manager import gpio_manager
from hardware.gpio.pwm_manager import pwm_manager, PWMChannel
from hardware.gpio.pin_definitions import pin_defs


class MotorDriver:
    """
    Low-level L298N motor driver interface
    Controls individual motor direction and speed via PWM
    """
    
    def __init__(self, enable_pin: int, input1_pin: int, input2_pin: int, name: str = "motor"):
        """
        Initialize motor driver
        
        Args:
            enable_pin: Enable pin (PWM for speed control)
            input1_pin: Direction control pin 1
            input2_pin: Direction control pin 2
            name: Motor name for logging
        """
        self.logger = get_logger(f"motor_driver.{name}")
        self.name = name
        
        # Pin assignments
        self.enable_pin = enable_pin
        self.input1_pin = input1_pin
        self.input2_pin = input2_pin
        
        # PWM channel
        self.pwm_channel: PWMChannel = None
        
        # State
        self.current_speed = 0.0
        self.current_direction = 0  # 1=forward, -1=backward, 0=stop
        self.initialized = False
    
    def initialize(self):
        """Initialize motor driver pins"""
        if self.initialized:
            self.logger.warning(f"{self.name} already initialized")
            return
        
        try:
            # Setup direction pins as outputs
            gpio_manager.setup_output(self.input1_pin, initial=0)
            gpio_manager.setup_output(self.input2_pin, initial=0)
            
            # Setup PWM on enable pin
            frequency = pwm_manager.get_motor_frequency()
            self.pwm_channel = pwm_manager.create_pwm(self.enable_pin, frequency)
            self.pwm_channel.start(0)
            
            self.initialized = True
            self.logger.info(f"{self.name} initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize {self.name}: {e}")
            raise
    
    def set_direction_forward(self):
        """Set motor direction to forward"""
        gpio_manager.output(self.input1_pin, True)
        gpio_manager.output(self.input2_pin, False)
        self.current_direction = 1
    
    def set_direction_backward(self):
        """Set motor direction to backward"""
        gpio_manager.output(self.input1_pin, False)
        gpio_manager.output(self.input2_pin, True)
        self.current_direction = -1
    
    def set_direction_stop(self):
        """Stop motor (both inputs low)"""
        gpio_manager.output(self.input1_pin, False)
        gpio_manager.output(self.input2_pin, False)
        self.current_direction = 0
    
    def set_speed(self, speed: float):
        """
        Set motor speed
        
        Args:
            speed: Speed as percentage (0-100)
        """
        if not self.initialized:
            raise RuntimeError(f"{self.name} not initialized")
        
        # Clamp speed
        speed = max(0.0, min(100.0, speed))
        
        # Set PWM duty cycle
        self.pwm_channel.change_duty_cycle(speed)
        self.current_speed = speed
    
    def stop(self):
        """Stop motor immediately"""
        self.set_direction_stop()
        self.set_speed(0)
    
    def get_state(self) -> Tuple[float, int]:
        """
        Get current motor state
        
        Returns:
            Tuple of (speed, direction)
        """
        return (self.current_speed, self.current_direction)
    
    def cleanup(self):
        """Cleanup motor driver"""
        if self.initialized:
            self.stop()
            time.sleep(0.1)
            self.logger.info(f"{self.name} cleaned up")
