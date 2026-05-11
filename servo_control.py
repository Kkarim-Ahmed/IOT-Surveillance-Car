"""
Servo Motor Control Module for Raspberry Pi
"""
import time
import config
from pid_controller import PIDController, ServoController


class ServoDriver:
    """
    Servo driver using PCA9685 board (Raspberry Pi only)
    """
    
    def __init__(self):
        """Initialize servo driver"""
        self.kit = None
        self.enabled = False
        
        if config.IS_RASPBERRY_PI and config.ENABLE_SERVO_CONTROL:
            try:
                from adafruit_servokit import ServoKit
                
                # Initialize PCA9685
                self.kit = ServoKit(
                    channels=16,
                    address=config.SERVO_I2C_ADDRESS,
                    frequency=config.SERVO_FREQUENCY
                )
                
                self.enabled = True
                print("✅ Servo driver initialized (PCA9685)")
                
            except Exception as e:
                print(f"⚠️  Failed to initialize servo driver: {e}")
                print("   Servo control disabled")
        else:
            print("ℹ️  Servo control disabled (not on Raspberry Pi or disabled in config)")
    
    def set_angle(self, channel, angle):
        """
        Set servo angle
        
        Args:
            channel: Servo channel (0-15)
            angle: Target angle (0-180)
        """
        if self.enabled and self.kit:
            try:
                self.kit.servo[channel].angle = angle
            except Exception as e:
                print(f"⚠️  Error setting servo angle: {e}")
    
    def is_enabled(self):
        """Check if servo control is enabled"""
        return self.enabled


class FaceTrackingServo:
    """
    Face tracking servo controller with PID
    """
    
    def __init__(self):
        """Initialize face tracking servo system"""
        # Initialize servo driver
        self.driver = ServoDriver()
        
        # Initialize PID controllers
        self.pan_pid = PIDController(
            kp=config.PAN_KP,
            ki=config.PAN_KI,
            kd=config.PAN_KD,
            integral_limit=config.PID_INTEGRAL_LIMIT,
            output_limit=config.PID_OUTPUT_LIMIT
        )
        
        self.tilt_pid = PIDController(
            kp=config.TILT_KP,
            ki=config.TILT_KI,
            kd=config.TILT_KD,
            integral_limit=config.PID_INTEGRAL_LIMIT,
            output_limit=config.PID_OUTPUT_LIMIT
        )
        
        # Initialize servo controllers
        self.pan_servo = ServoController(
            min_angle=config.PAN_MIN,
            max_angle=config.PAN_MAX,
            center_angle=config.PAN_CENTER,
            max_speed=config.MAX_SERVO_SPEED
        )
        
        self.tilt_servo = ServoController(
            min_angle=config.TILT_MIN,
            max_angle=config.TILT_MAX,
            center_angle=config.TILT_CENTER,
            max_speed=config.MAX_SERVO_SPEED
        )
        
        # State
        self.frame_center_x = config.FRAME_WIDTH // 2
        self.frame_center_y = config.FRAME_HEIGHT // 2
        self.tracking_active = False
        
        # Move to center position
        self.reset()
        
    def reset(self):
        """Reset servos to center position"""
        self.pan_pid.reset()
        self.tilt_pid.reset()
        self.pan_servo.reset()
        self.tilt_servo.reset()
        
        if self.driver.is_enabled():
            self.driver.set_angle(config.PAN_CHANNEL, config.PAN_CENTER)
            self.driver.set_angle(config.TILT_CHANNEL, config.TILT_CENTER)
        
        self.tracking_active = False
        print("🎯 Servos reset to center position")
    
    def update(self, face_center_x, face_center_y):
        """
        Update servo positions to track face
        
        Args:
            face_center_x: X coordinate of face center
            face_center_y: Y coordinate of face center
        """
        if not self.driver.is_enabled():
            return
        
        # Calculate error (distance from frame center)
        error_x = self.frame_center_x - face_center_x
        error_y = self.frame_center_y - face_center_y
        
        # Apply deadzone
        if abs(error_x) < config.DEADZONE_X:
            error_x = 0
        if abs(error_y) < config.DEADZONE_Y:
            error_y = 0
        
        # Calculate PID corrections
        current_time = time.time()
        pan_correction = self.pan_pid.update(error_x, current_time)
        tilt_correction = self.tilt_pid.update(error_y, current_time)
        
        # Update servo targets
        current_pan = self.pan_servo.get_angle()
        current_tilt = self.tilt_servo.get_angle()
        
        self.pan_servo.set_target(current_pan + pan_correction)
        self.tilt_servo.set_target(current_tilt - tilt_correction)  # Invert for natural movement
        
        # Update servo positions
        new_pan = self.pan_servo.update()
        new_tilt = self.tilt_servo.update()
        
        # Send to hardware
        self.driver.set_angle(config.PAN_CHANNEL, new_pan)
        self.driver.set_angle(config.TILT_CHANNEL, new_tilt)
        
        self.tracking_active = True
    
    def get_status(self):
        """
        Get current servo status
        
        Returns:
            Dictionary with servo angles and tracking status
        """
        return {
            "pan_angle": self.pan_servo.get_angle(),
            "tilt_angle": self.tilt_servo.get_angle(),
            "tracking_active": self.tracking_active,
            "enabled": self.driver.is_enabled()
        }
    
    def set_pid_gains(self, axis, kp=None, ki=None, kd=None):
        """
        Update PID gains for tuning
        
        Args:
            axis: "pan" or "tilt"
            kp, ki, kd: New gain values (optional)
        """
        if axis.lower() == "pan":
            self.pan_pid.set_gains(kp, ki, kd)
            print(f"🔧 Updated PAN PID: Kp={self.pan_pid.kp}, Ki={self.pan_pid.ki}, Kd={self.pan_pid.kd}")
        elif axis.lower() == "tilt":
            self.tilt_pid.set_gains(kp, ki, kd)
            print(f"🔧 Updated TILT PID: Kp={self.tilt_pid.kp}, Ki={self.tilt_pid.ki}, Kd={self.tilt_pid.kd}")
