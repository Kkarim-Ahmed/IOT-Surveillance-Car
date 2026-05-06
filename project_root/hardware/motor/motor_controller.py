"""
Motor Controller
High-level motor control with safety features and smooth movement
"""

import time
import threading
from enum import Enum
from typing import Optional
from hardware.utils.logger import get_logger
from hardware.utils.threading_utils import thread_safe
from hardware.gpio.pin_definitions import pin_defs
from hardware.motor.motor_driver import MotorDriver
from hardware.motor.motor_safety import MotorSafety


class MotorDirection(Enum):
    """Motor movement directions"""
    FORWARD = "forward"
    BACKWARD = "backward"
    LEFT = "left"
    RIGHT = "right"
    STOP = "stop"


class MotorController:
    """
    High-level motor controller
    Provides smooth acceleration, turning, and safety features
    """
    
    def __init__(self):
        self.logger = get_logger("motor_controller")
        
        # Initialize motor drivers
        motor_pins = pin_defs.motor
        self.left_motor = MotorDriver(
            motor_pins.left_enable,
            motor_pins.left_input1,
            motor_pins.left_input2,
            name="left"
        )
        self.right_motor = MotorDriver(
            motor_pins.right_enable,
            motor_pins.right_input3,
            motor_pins.right_input4,
            name="right"
        )
        
        # Safety system
        self.safety = MotorSafety()
        
        # State
        self.current_direction = MotorDirection.STOP
        self.target_speed = 70.0
        self.current_speed = 0.0
        self.initialized = False
        
        # Threading
        self._lock = threading.RLock()
    
    def initialize(self):
        """Initialize motor controller"""
        with self._lock:
            if self.initialized:
                self.logger.warning("Motor controller already initialized")
                return
            
            try:
                self.left_motor.initialize()
                self.right_motor.initialize()
                
                self.initialized = True
                self.logger.info("Motor controller initialized")
                
            except Exception as e:
                self.logger.error(f"Failed to initialize motor controller: {e}")
                raise
    
    @thread_safe
    def move_forward(self, speed: Optional[float] = None):
        """
        Move forward
        
        Args:
            speed: Speed percentage (0-100), uses target_speed if None
        """
        if not self.initialized:
            raise RuntimeError("Motor controller not initialized")
        
        if self.safety.is_emergency_stop_active():
            self.logger.warning("Cannot move - emergency stop active")
            return
        
        speed = speed if speed is not None else self.target_speed
        speed = self.safety.validate_speed(speed)
        
        # Check direction change safety
        if not self.safety.can_change_direction(
            self.left_motor.current_direction, 1, self.current_speed
        ):
            self.stop()
            time.sleep(self.safety.direction_change_delay)
        
        # Set direction
        self.left_motor.set_direction_forward()
        self.right_motor.set_direction_forward()
        
        # Set speed with acceleration
        self._set_speed_smooth(speed)
        
        self.current_direction = MotorDirection.FORWARD
        self.logger.debug(f"Moving forward at {speed}%")
    
    @thread_safe
    def move_backward(self, speed: Optional[float] = None):
        """
        Move backward
        
        Args:
            speed: Speed percentage (0-100), uses target_speed if None
        """
        if not self.initialized:
            raise RuntimeError("Motor controller not initialized")
        
        if self.safety.is_emergency_stop_active():
            self.logger.warning("Cannot move - emergency stop active")
            return
        
        speed = speed if speed is not None else self.target_speed
        speed = self.safety.validate_speed(speed)
        
        # Check direction change safety
        if not self.safety.can_change_direction(
            self.left_motor.current_direction, -1, self.current_speed
        ):
            self.stop()
            time.sleep(self.safety.direction_change_delay)
        
        # Set direction
        self.left_motor.set_direction_backward()
        self.right_motor.set_direction_backward()
        
        # Set speed with acceleration
        self._set_speed_smooth(speed)
        
        self.current_direction = MotorDirection.BACKWARD
        self.logger.debug(f"Moving backward at {speed}%")
    
    @thread_safe
    def turn_left(self, speed: Optional[float] = None):
        """
        Turn left (left motor slower/stopped, right motor forward)
        
        Args:
            speed: Speed percentage (0-100), uses target_speed if None
        """
        if not self.initialized:
            raise RuntimeError("Motor controller not initialized")
        
        if self.safety.is_emergency_stop_active():
            self.logger.warning("Cannot move - emergency stop active")
            return
        
        speed = speed if speed is not None else self.target_speed
        speed = self.safety.validate_speed(speed)
        
        # Set directions
        self.left_motor.set_direction_backward()
        self.right_motor.set_direction_forward()
        
        # Set speeds (left slower for turning)
        turn_ratio = 0.7
        self.left_motor.set_speed(speed * turn_ratio)
        self.right_motor.set_speed(speed)
        
        self.current_speed = speed
        self.current_direction = MotorDirection.LEFT
        self.logger.debug(f"Turning left at {speed}%")
    
    @thread_safe
    def turn_right(self, speed: Optional[float] = None):
        """
        Turn right (right motor slower/stopped, left motor forward)
        
        Args:
            speed: Speed percentage (0-100), uses target_speed if None
        """
        if not self.initialized:
            raise RuntimeError("Motor controller not initialized")
        
        if self.safety.is_emergency_stop_active():
            self.logger.warning("Cannot move - emergency stop active")
            return
        
        speed = speed if speed is not None else self.target_speed
        speed = self.safety.validate_speed(speed)
        
        # Set directions
        self.left_motor.set_direction_forward()
        self.right_motor.set_direction_backward()
        
        # Set speeds (right slower for turning)
        turn_ratio = 0.7
        self.left_motor.set_speed(speed)
        self.right_motor.set_speed(speed * turn_ratio)
        
        self.current_speed = speed
        self.current_direction = MotorDirection.RIGHT
        self.logger.debug(f"Turning right at {speed}%")
    
    @thread_safe
    def stop(self, smooth: bool = True):
        """
        Stop motors
        
        Args:
            smooth: If True, decelerate smoothly
        """
        if smooth:
            self._decelerate_smooth()
        else:
            self.left_motor.stop()
            self.right_motor.stop()
            self.current_speed = 0.0
        
        self.current_direction = MotorDirection.STOP
        self.logger.debug("Motors stopped")
    
    @thread_safe
    def emergency_stop(self):
        """Emergency stop - immediate halt"""
        self.safety.trigger_emergency_stop()
        self.left_motor.stop()
        self.right_motor.stop()
        self.current_speed = 0.0
        self.current_direction = MotorDirection.STOP
        self.logger.critical("EMERGENCY STOP")
    
    @thread_safe
    def set_speed(self, speed: float):
        """
        Set target speed
        
        Args:
            speed: Target speed (0-100)
        """
        self.target_speed = self.safety.validate_speed(speed)
        self.logger.debug(f"Target speed set to {self.target_speed}%")
    
    def _set_speed_smooth(self, target_speed: float):
        """Set speed with smooth acceleration"""
        while abs(self.current_speed - target_speed) > self.safety.acceleration_limit:
            self.current_speed = self.safety.calculate_safe_acceleration(
                self.current_speed, target_speed
            )
            self.left_motor.set_speed(self.current_speed)
            self.right_motor.set_speed(self.current_speed)
            time.sleep(0.05)
        
        # Final speed
        self.current_speed = target_speed
        self.left_motor.set_speed(self.current_speed)
        self.right_motor.set_speed(self.current_speed)
    
    def _decelerate_smooth(self):
        """Smooth deceleration to stop"""
        while self.current_speed > 0:
            self.current_speed = max(0, self.current_speed - self.safety.acceleration_limit)
            self.left_motor.set_speed(self.current_speed)
            self.right_motor.set_speed(self.current_speed)
            time.sleep(0.05)
        
        self.left_motor.stop()
        self.right_motor.stop()
    
    def get_status(self) -> dict:
        """Get motor controller status"""
        return {
            'direction': self.current_direction.value,
            'speed': self.current_speed,
            'target_speed': self.target_speed,
            'emergency_stop': self.safety.is_emergency_stop_active(),
            'initialized': self.initialized
        }
    
    def cleanup(self):
        """Cleanup motor controller"""
        with self._lock:
            self.stop(smooth=False)
            self.left_motor.cleanup()
            self.right_motor.cleanup()
            self.logger.info("Motor controller cleaned up")
