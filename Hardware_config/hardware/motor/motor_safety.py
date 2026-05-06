"""
Motor Safety System
Implements safety checks and limits for motor control
"""

import yaml
from pathlib import Path
from typing import Optional
from hardware.utils.logger import get_logger


class MotorSafety:
    """
    Motor safety system
    Enforces speed limits, direction change safety, and emergency stops
    """
    
    def __init__(self):
        self.logger = get_logger("motor_safety")
        self._load_config()
        
        # State tracking
        self.emergency_stop_active = False
        self.last_direction = 0
    
    def _load_config(self):
        """Load safety configuration"""
        config_path = Path("configs/safety_config.yaml")
        
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                motor_config = config.get('motor', {})
        else:
            self.logger.warning("Safety config not found, using defaults")
            motor_config = {}
        
        # Speed limits
        speed_limits = motor_config.get('speed_limits', {})
        self.min_speed = speed_limits.get('min', 30)
        self.max_speed = speed_limits.get('max', 100)
        self.safe_mode_speed = speed_limits.get('safe_mode', 50)
        
        # Direction change safety
        dir_change = motor_config.get('direction_change', {})
        self.require_stop_before_direction_change = dir_change.get('require_stop', True)
        self.direction_change_delay = dir_change.get('delay', 0.2)
        
        # Acceleration
        self.acceleration_limit = motor_config.get('acceleration_limit', 10)
        self.emergency_stop_time = motor_config.get('emergency_stop_time', 0.1)
    
    def validate_speed(self, speed: float, safe_mode: bool = False) -> float:
        """
        Validate and clamp speed to safe limits
        
        Args:
            speed: Requested speed (0-100)
            safe_mode: If True, use safe mode speed limit
            
        Returns:
            Validated speed
        """
        if self.emergency_stop_active:
            return 0.0
        
        # Apply limits
        max_limit = self.safe_mode_speed if safe_mode else self.max_speed
        
        if speed > 0:
            speed = max(self.min_speed, min(speed, max_limit))
        else:
            speed = 0.0
        
        return speed
    
    def can_change_direction(self, current_direction: int, new_direction: int, 
                            current_speed: float) -> bool:
        """
        Check if direction change is safe
        
        Args:
            current_direction: Current direction (1, -1, or 0)
            new_direction: Requested direction (1, -1, or 0)
            current_speed: Current speed
            
        Returns:
            True if direction change is safe
        """
        # Same direction is always safe
        if current_direction == new_direction:
            return True
        
        # Stopping is always safe
        if new_direction == 0:
            return True
        
        # If require stop before direction change
        if self.require_stop_before_direction_change:
            # Must be stopped to change direction
            if current_direction != 0 and current_speed > 0:
                self.logger.warning("Must stop before changing direction")
                return False
        
        return True
    
    def calculate_safe_acceleration(self, current_speed: float, target_speed: float) -> float:
        """
        Calculate safe acceleration step
        
        Args:
            current_speed: Current speed
            target_speed: Target speed
            
        Returns:
            Next safe speed value
        """
        speed_diff = target_speed - current_speed
        
        if abs(speed_diff) <= self.acceleration_limit:
            return target_speed
        
        if speed_diff > 0:
            return current_speed + self.acceleration_limit
        else:
            return current_speed - self.acceleration_limit
    
    def trigger_emergency_stop(self):
        """Trigger emergency stop"""
        self.emergency_stop_active = True
        self.logger.critical("EMERGENCY STOP ACTIVATED")
    
    def reset_emergency_stop(self):
        """Reset emergency stop"""
        self.emergency_stop_active = False
        self.logger.info("Emergency stop reset")
    
    def is_emergency_stop_active(self) -> bool:
        """Check if emergency stop is active"""
        return self.emergency_stop_active
