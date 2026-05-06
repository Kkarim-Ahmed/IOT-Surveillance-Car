"""
Servo Controller
High-level servo control with smooth movement and safety
"""

import time
import threading
from typing import Optional, Tuple
from hardware.utils.logger import get_logger
from hardware.utils.threading_utils import thread_safe
from hardware.gpio.pin_definitions import pin_defs
from hardware.gpio.pwm_manager import pwm_manager, PWMChannel
from hardware.servo.servo_limits import ServoLimits
from hardware.servo.servo_calibration import ServoCalibration


class ServoController:
    """
    High-level servo controller
    Controls pan and tilt servos with smooth movement
    """
    
    def __init__(self):
        self.logger = get_logger("servo_controller")
        
        # Servo pins
        servo_pins = pin_defs.servo
        self.pan_pin = servo_pins.pan
        self.tilt_pin = servo_pins.tilt
        
        # PWM channels
        self.pan_pwm: Optional[PWMChannel] = None
        self.tilt_pwm: Optional[PWMChannel] = None
        
        # Limits and calibration
        self.pan_limits = ServoLimits('pan')
        self.tilt_limits = ServoLimits('tilt')
        self.calibration = ServoCalibration()
        
        # Current positions
        self.pan_angle = self.pan_limits.center_angle
        self.tilt_angle = self.tilt_limits.center_angle
        
        # State
        self.initialized = False
        self._lock = threading.RLock()
    
    def initialize(self):
        """Initialize servo controller"""
        with self._lock:
            if self.initialized:
                self.logger.warning("Servo controller already initialized")
                return
            
            try:
                # Create PWM channels
                frequency = pwm_manager.get_servo_frequency()
                self.pan_pwm = pwm_manager.create_pwm(self.pan_pin, frequency)
                self.tilt_pwm = pwm_manager.create_pwm(self.tilt_pin, frequency)
                
                # Start PWM
                self.pan_pwm.start(0)
                self.tilt_pwm.start(0)
                
                # Move to center position
                self.center()
                
                self.initialized = True
                self.logger.info("Servo controller initialized")
                
            except Exception as e:
                self.logger.error(f"Failed to initialize servo controller: {e}")
                raise
    
    @thread_safe
    def set_angle(self, pan: Optional[float] = None, tilt: Optional[float] = None,
                  smooth: bool = True):
        """
        Set servo angles
        
        Args:
            pan: Pan angle (horizontal), None to keep current
            tilt: Tilt angle (vertical), None to keep current
            smooth: If True, move smoothly
        """
        if not self.initialized:
            raise RuntimeError("Servo controller not initialized")
        
        # Validate and set pan
        if pan is not None:
            pan = self.pan_limits.validate_angle(pan)
            if smooth:
                self._move_smooth(self.pan_pwm, self.pan_angle, pan, 
                                self.pan_limits.min_angle, self.pan_limits.max_angle)
            else:
                self._set_servo_angle(self.pan_pwm, pan,
                                    self.pan_limits.min_angle, self.pan_limits.max_angle)
            self.pan_angle = pan
        
        # Validate and set tilt
        if tilt is not None:
            tilt = self.tilt_limits.validate_angle(tilt)
            if smooth:
                self._move_smooth(self.tilt_pwm, self.tilt_angle, tilt,
                                self.tilt_limits.min_angle, self.tilt_limits.max_angle)
            else:
                self._set_servo_angle(self.tilt_pwm, tilt,
                                    self.tilt_limits.min_angle, self.tilt_limits.max_angle)
            self.tilt_angle = tilt
        
        self.logger.debug(f"Servo position: pan={self.pan_angle}, tilt={self.tilt_angle}")
    
    @thread_safe
    def pan_left(self, degrees: float = 15):
        """Pan left by specified degrees"""
        new_angle = self.pan_angle - degrees
        self.set_angle(pan=new_angle)
    
    @thread_safe
    def pan_right(self, degrees: float = 15):
        """Pan right by specified degrees"""
        new_angle = self.pan_angle + degrees
        self.set_angle(pan=new_angle)
    
    @thread_safe
    def tilt_up(self, degrees: float = 15):
        """Tilt up by specified degrees"""
        new_angle = self.tilt_angle + degrees
        self.set_angle(tilt=new_angle)
    
    @thread_safe
    def tilt_down(self, degrees: float = 15):
        """Tilt down by specified degrees"""
        new_angle = self.tilt_angle - degrees
        self.set_angle(tilt=new_angle)
    
    @thread_safe
    def center(self):
        """Move to center position"""
        self.set_angle(
            pan=self.pan_limits.center_angle,
            tilt=self.tilt_limits.center_angle,
            smooth=True
        )
        self.logger.debug("Moved to center position")
    
    @thread_safe
    def set_preset(self, preset_name: str):
        """
        Move to preset position
        
        Args:
            preset_name: Name of preset (e.g., 'center', 'left', 'right')
        """
        try:
            pan_angle = self.pan_limits.get_preset_angle(preset_name)
            self.set_angle(pan=pan_angle, smooth=True)
        except ValueError:
            try:
                tilt_angle = self.tilt_limits.get_preset_angle(preset_name)
                self.set_angle(tilt=tilt_angle, smooth=True)
            except ValueError:
                self.logger.error(f"Unknown preset: {preset_name}")
    
    def get_position(self) -> Tuple[float, float]:
        """Get current position"""
        return (self.pan_angle, self.tilt_angle)
    
    def get_status(self) -> dict:
        """Get servo controller status"""
        return {
            'pan_angle': self.pan_angle,
            'tilt_angle': self.tilt_angle,
            'pan_limits': self.pan_limits.get_limits(),
            'tilt_limits': self.tilt_limits.get_limits(),
            'initialized': self.initialized
        }
    
    def _set_servo_angle(self, pwm: PWMChannel, angle: float, 
                        min_angle: float, max_angle: float):
        """Set servo to specific angle"""
        duty_cycle = self.calibration.angle_to_duty_cycle(angle, min_angle, max_angle)
        pwm.change_duty_cycle(duty_cycle)
    
    def _move_smooth(self, pwm: PWMChannel, current_angle: float, 
                    target_angle: float, min_angle: float, max_angle: float):
        """Move servo smoothly to target angle"""
        step_size = 5  # degrees per step
        step_delay = 0.02  # seconds
        
        angle = current_angle
        direction = 1 if target_angle > current_angle else -1
        
        while abs(angle - target_angle) > step_size:
            angle += step_size * direction
            self._set_servo_angle(pwm, angle, min_angle, max_angle)
            time.sleep(step_delay)
        
        # Final position
        self._set_servo_angle(pwm, target_angle, min_angle, max_angle)
    
    def cleanup(self):
        """Cleanup servo controller"""
        with self._lock:
            if self.initialized:
                self.center()
                time.sleep(0.5)
                
                if self.pan_pwm:
                    self.pan_pwm.stop()
                if self.tilt_pwm:
                    self.tilt_pwm.stop()
                
                self.logger.info("Servo controller cleaned up")
