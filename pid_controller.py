"""
PID Controller for Servo Motor Control
"""
import time


class PIDController:
    """
    PID Controller for smooth servo tracking
    """
    
    def __init__(self, kp, ki, kd, integral_limit=100, output_limit=30):
        """
        Initialize PID controller
        
        Args:
            kp: Proportional gain
            ki: Integral gain
            kd: Derivative gain
            integral_limit: Maximum integral accumulation (anti-windup)
            output_limit: Maximum output value
        """
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.integral_limit = integral_limit
        self.output_limit = output_limit
        
        # State variables
        self.previous_error = 0
        self.integral = 0
        self.last_time = time.time()
        
    def update(self, error, current_time=None):
        """
        Calculate PID output based on error
        
        Args:
            error: Current error value (setpoint - measured_value)
            current_time: Current timestamp (optional)
            
        Returns:
            PID output value
        """
        if current_time is None:
            current_time = time.time()
            
        # Calculate time delta
        dt = current_time - self.last_time
        if dt <= 0:
            dt = 0.01  # Prevent division by zero
            
        # Proportional term
        p_term = self.kp * error
        
        # Integral term with anti-windup
        self.integral += error * dt
        self.integral = max(min(self.integral, self.integral_limit), -self.integral_limit)
        i_term = self.ki * self.integral
        
        # Derivative term
        derivative = (error - self.previous_error) / dt
        d_term = self.kd * derivative
        
        # Calculate total output
        output = p_term + i_term + d_term
        
        # Limit output
        output = max(min(output, self.output_limit), -self.output_limit)
        
        # Update state
        self.previous_error = error
        self.last_time = current_time
        
        return output
    
    def reset(self):
        """Reset PID controller state"""
        self.previous_error = 0
        self.integral = 0
        self.last_time = time.time()
    
    def set_gains(self, kp=None, ki=None, kd=None):
        """Update PID gains"""
        if kp is not None:
            self.kp = kp
        if ki is not None:
            self.ki = ki
        if kd is not None:
            self.kd = kd


class ServoController:
    """
    Servo controller with PID and smooth movement
    """
    
    def __init__(self, min_angle, max_angle, center_angle, max_speed=5):
        """
        Initialize servo controller
        
        Args:
            min_angle: Minimum servo angle
            max_angle: Maximum servo angle
            center_angle: Center/home position
            max_speed: Maximum degrees per update
        """
        self.min_angle = min_angle
        self.max_angle = max_angle
        self.center_angle = center_angle
        self.max_speed = max_speed
        
        self.current_angle = center_angle
        self.target_angle = center_angle
        
    def set_target(self, angle):
        """Set target angle"""
        self.target_angle = max(min(angle, self.max_angle), self.min_angle)
        
    def update(self):
        """
        Update current angle towards target with speed limiting
        
        Returns:
            Current angle after update
        """
        error = self.target_angle - self.current_angle
        
        # Limit movement speed
        if abs(error) > self.max_speed:
            movement = self.max_speed if error > 0 else -self.max_speed
        else:
            movement = error
            
        self.current_angle += movement
        self.current_angle = max(min(self.current_angle, self.max_angle), self.min_angle)
        
        return self.current_angle
    
    def reset(self):
        """Reset to center position"""
        self.current_angle = self.center_angle
        self.target_angle = self.center_angle
        
    def get_angle(self):
        """Get current angle"""
        return self.current_angle
