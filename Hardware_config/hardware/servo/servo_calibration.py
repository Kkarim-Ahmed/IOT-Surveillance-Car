"""
Servo Calibration
Handles servo calibration and pulse width calculations
"""

import yaml
from pathlib import Path
from hardware.utils.logger import get_logger


class ServoCalibration:
    """Servo calibration and pulse width conversion"""
    
    def __init__(self):
        self.logger = get_logger("servo_calibration")
        self._load_config()
    
    def _load_config(self):
        """Load PWM configuration"""
        config_path = Path("configs/pwm_config.yaml")
        
        if not config_path.exists():
            raise FileNotFoundError(f"PWM config not found: {config_path}")
        
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        servo_config = config.get('servo', {})
        pulse_config = servo_config.get('pulse_width', {})
        
        self.frequency = servo_config.get('frequency', 50)
        self.min_pulse = pulse_config.get('min', 500)
        self.max_pulse = pulse_config.get('max', 2500)
        self.center_pulse = pulse_config.get('center', 1500)
    
    def angle_to_duty_cycle(self, angle: float, min_angle: float = -90, 
                           max_angle: float = 90) -> float:
        """
        Convert angle to PWM duty cycle
        
        Args:
            angle: Servo angle in degrees
            min_angle: Minimum angle
            max_angle: Maximum angle
            
        Returns:
            PWM duty cycle (0-100)
        """
        # Map angle to pulse width
        angle_range = max_angle - min_angle
        pulse_range = self.max_pulse - self.min_pulse
        
        # Calculate pulse width for this angle
        pulse_width = self.min_pulse + ((angle - min_angle) / angle_range) * pulse_range
        
        # Convert pulse width to duty cycle
        # Period = 1/frequency (in seconds)
        # Duty cycle = (pulse_width / period) * 100
        period_us = (1.0 / self.frequency) * 1_000_000  # Period in microseconds
        duty_cycle = (pulse_width / period_us) * 100
        
        return duty_cycle
    
    def duty_cycle_to_angle(self, duty_cycle: float, min_angle: float = -90,
                           max_angle: float = 90) -> float:
        """
        Convert PWM duty cycle to angle
        
        Args:
            duty_cycle: PWM duty cycle (0-100)
            min_angle: Minimum angle
            max_angle: Maximum angle
            
        Returns:
            Servo angle in degrees
        """
        # Convert duty cycle to pulse width
        period_us = (1.0 / self.frequency) * 1_000_000
        pulse_width = (duty_cycle / 100) * period_us
        
        # Map pulse width to angle
        pulse_range = self.max_pulse - self.min_pulse
        angle_range = max_angle - min_angle
        
        angle = min_angle + ((pulse_width - self.min_pulse) / pulse_range) * angle_range
        
        return angle
