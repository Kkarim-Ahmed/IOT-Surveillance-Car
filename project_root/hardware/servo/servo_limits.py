"""
Servo Limits
Defines and enforces servo angle limits
"""

import yaml
from pathlib import Path
from typing import Tuple
from hardware.utils.logger import get_logger


class ServoLimits:
    """Servo angle limits and validation"""
    
    def __init__(self, servo_name: str):
        """
        Initialize servo limits
        
        Args:
            servo_name: 'pan' or 'tilt'
        """
        self.logger = get_logger(f"servo_limits.{servo_name}")
        self.servo_name = servo_name
        self._load_config()
    
    def _load_config(self):
        """Load servo configuration"""
        config_path = Path("configs/servo_config.yaml")
        
        if not config_path.exists():
            raise FileNotFoundError(f"Servo config not found: {config_path}")
        
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        servo_config = config.get(self.servo_name, {})
        limits = servo_config.get('angle_limits', {})
        
        self.min_angle = limits.get('min', -90)
        self.max_angle = limits.get('max', 90)
        self.center_angle = limits.get('center', 0)
        
        # Calibration
        calibration = servo_config.get('calibration', {})
        self.offset = calibration.get('offset', 0)
        self.inverted = calibration.get('inverted', False)
        
        # Presets
        self.presets = servo_config.get('presets', {})
    
    def validate_angle(self, angle: float) -> float:
        """
        Validate and clamp angle to limits
        
        Args:
            angle: Requested angle
            
        Returns:
            Validated angle within limits
        """
        # Apply inversion
        if self.inverted:
            angle = -angle
        
        # Apply offset
        angle += self.offset
        
        # Clamp to limits
        if angle < self.min_angle:
            self.logger.warning(f"Angle {angle} below minimum {self.min_angle}, clamping")
            angle = self.min_angle
        elif angle > self.max_angle:
            self.logger.warning(f"Angle {angle} above maximum {self.max_angle}, clamping")
            angle = self.max_angle
        
        return angle
    
    def get_preset_angle(self, preset_name: str) -> float:
        """
        Get preset angle
        
        Args:
            preset_name: Name of preset
            
        Returns:
            Preset angle
        """
        if preset_name not in self.presets:
            raise ValueError(f"Unknown preset: {preset_name}")
        
        return self.presets[preset_name]
    
    def get_limits(self) -> Tuple[float, float]:
        """Get angle limits"""
        return (self.min_angle, self.max_angle)
    
    def get_center(self) -> float:
        """Get center angle"""
        return self.center_angle
