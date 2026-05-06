"""
GPIO Pin Definitions
Centralized pin definitions loaded from configuration
"""

import yaml
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class MotorPins:
    """Motor pin configuration"""
    left_enable: int
    left_input1: int
    left_input2: int
    right_enable: int
    right_input3: int
    right_input4: int


@dataclass
class ServoPins:
    """Servo pin configuration"""
    pan: int
    tilt: int


@dataclass
class LEDPins:
    """LED pin configuration"""
    red: int
    green: int
    blue: int


@dataclass
class UltrasonicPins:
    """Ultrasonic sensor pin configuration"""
    trigger: int
    echo: int


class PinDefinitions:
    """Centralized GPIO pin definitions"""
    
    _instance: Optional['PinDefinitions'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._load_config()
            self._initialized = True
    
    def _load_config(self):
        """Load pin configuration from YAML"""
        config_path = Path("configs/gpio_config.yaml")
        
        if not config_path.exists():
            raise FileNotFoundError(f"GPIO config not found: {config_path}")
        
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        # Parse motor pins
        motor_cfg = self.config['motor']
        self.motor = MotorPins(
            left_enable=motor_cfg['left_motor']['enable'],
            left_input1=motor_cfg['left_motor']['input1'],
            left_input2=motor_cfg['left_motor']['input2'],
            right_enable=motor_cfg['right_motor']['enable'],
            right_input3=motor_cfg['right_motor']['input3'],
            right_input4=motor_cfg['right_motor']['input4']
        )
        
        # Parse servo pins
        servo_cfg = self.config['servo']
        self.servo = ServoPins(
            pan=servo_cfg['pan']['pin'],
            tilt=servo_cfg['tilt']['pin']
        )
        
        # Parse LED pins
        led_cfg = self.config['led']
        self.led = LEDPins(
            red=led_cfg['red'],
            green=led_cfg['green'],
            blue=led_cfg['blue']
        )
        
        # Parse ultrasonic pins
        ultrasonic_cfg = self.config['ultrasonic']
        self.ultrasonic = UltrasonicPins(
            trigger=ultrasonic_cfg['trigger'],
            echo=ultrasonic_cfg['echo']
        )
        
        # Emergency button (optional)
        if 'emergency_button' in self.config:
            self.emergency_button = self.config['emergency_button']['pin']
        else:
            self.emergency_button = None
        
        # Board mode
        self.board_mode = self.config.get('board_mode', 'BCM')
        
        # Reserved pins
        self.reserved_pins: List[int] = self.config.get('reserved_pins', [])
    
    def is_reserved(self, pin: int) -> bool:
        """Check if pin is reserved"""
        return pin in self.reserved_pins
    
    def validate_pin(self, pin: int) -> bool:
        """Validate pin number"""
        if self.is_reserved(pin):
            raise ValueError(f"Pin {pin} is reserved and cannot be used")
        
        # BCM mode: valid pins are 0-27
        if self.board_mode == 'BCM':
            if not (0 <= pin <= 27):
                raise ValueError(f"Invalid BCM pin number: {pin}")
        
        return True
    
    def get_all_used_pins(self) -> List[int]:
        """Get list of all pins in use"""
        pins = []
        
        # Motor pins
        pins.extend([
            self.motor.left_enable,
            self.motor.left_input1,
            self.motor.left_input2,
            self.motor.right_enable,
            self.motor.right_input3,
            self.motor.right_input4
        ])
        
        # Servo pins
        pins.extend([self.servo.pan, self.servo.tilt])
        
        # LED pins
        pins.extend([self.led.red, self.led.green, self.led.blue])
        
        # Ultrasonic pins
        pins.extend([self.ultrasonic.trigger, self.ultrasonic.echo])
        
        # Emergency button
        if self.emergency_button:
            pins.append(self.emergency_button)
        
        return pins
    
    def check_conflicts(self) -> List[int]:
        """Check for pin conflicts"""
        pins = self.get_all_used_pins()
        duplicates = [pin for pin in pins if pins.count(pin) > 1]
        return list(set(duplicates))


# Global instance
pin_defs = PinDefinitions()
