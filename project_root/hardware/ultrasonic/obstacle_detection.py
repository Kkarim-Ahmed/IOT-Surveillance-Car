"""
Obstacle Detection
Detects obstacles based on distance thresholds
"""

import yaml
from pathlib import Path
from typing import Optional, Callable
from hardware.utils.logger import get_logger


class ObstacleDetection:
    """Obstacle detection logic"""
    
    def __init__(self):
        self.logger = get_logger("obstacle_detection")
        self._load_config()
        
        # Callbacks
        self.obstacle_callback: Optional[Callable] = None
        self.warning_callback: Optional[Callable] = None
    
    def _load_config(self):
        """Load safety configuration"""
        config_path = Path("configs/safety_config.yaml")
        
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                obstacle_config = config.get('obstacle_detection', {})
        else:
            self.logger.warning("Safety config not found, using defaults")
            obstacle_config = {}
        
        self.enabled = obstacle_config.get('enabled', True)
        self.emergency_distance = obstacle_config.get('emergency_distance', 15)
        self.warning_distance = obstacle_config.get('warning_distance', 30)
        self.auto_stop = obstacle_config.get('auto_stop', True)
    
    def check_distance(self, distance: float) -> str:
        """
        Check distance and determine status
        
        Args:
            distance: Distance in cm
            
        Returns:
            Status: 'clear', 'warning', or 'emergency'
        """
        if not self.enabled:
            return 'clear'
        
        if distance < self.emergency_distance:
            if self.obstacle_callback and self.auto_stop:
                try:
                    self.obstacle_callback(distance)
                except Exception as e:
                    self.logger.error(f"Error in obstacle callback: {e}")
            return 'emergency'
        
        elif distance < self.warning_distance:
            if self.warning_callback:
                try:
                    self.warning_callback(distance)
                except Exception as e:
                    self.logger.error(f"Error in warning callback: {e}")
            return 'warning'
        
        return 'clear'
    
    def register_obstacle_callback(self, callback: Callable):
        """Register callback for obstacle detection"""
        self.obstacle_callback = callback
    
    def register_warning_callback(self, callback: Callable):
        """Register callback for warning distance"""
        self.warning_callback = callback
    
    def is_obstacle_detected(self, distance: float) -> bool:
        """Check if obstacle is detected"""
        return distance < self.emergency_distance
    
    def is_warning_distance(self, distance: float) -> bool:
        """Check if in warning distance"""
        return distance < self.warning_distance
