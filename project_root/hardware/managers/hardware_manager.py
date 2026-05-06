"""
Hardware Manager
Coordinates all hardware components with unified interface
"""

import threading
from typing import Optional
from hardware.utils.logger import get_logger
from hardware.gpio.gpio_manager import gpio_manager
from hardware.gpio.pwm_manager import pwm_manager
from hardware.motor.motor_controller import MotorController
from hardware.servo.servo_controller import ServoController
from hardware.led.led_controller import LEDController
from hardware.ultrasonic.ultrasonic_controller import UltrasonicController
from hardware.camera.camera_controller import CameraController
from hardware.safety.emergency_stop import EmergencyStop, EmergencyTrigger
from hardware.safety.watchdog import Watchdog
from hardware.safety.hardware_monitor import HardwareMonitor


class HardwareManager:
    """
    Unified hardware management system
    Coordinates all hardware components and safety systems
    """
    
    _instance: Optional['HardwareManager'] = None
    _lock = threading.RLock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
            return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self.logger = get_logger("hardware_manager")
            
            # Safety systems (initialize first)
            self.emergency_stop = EmergencyStop()
            self.watchdog = Watchdog(self.emergency_stop, timeout=10.0)
            self.hardware_monitor = HardwareMonitor()
            
            # Hardware controllers
            self.motor: Optional[MotorController] = None
            self.servo: Optional[ServoController] = None
            self.led: Optional[LEDController] = None
            self.ultrasonic: Optional[UltrasonicController] = None
            self.camera: Optional[CameraController] = None
            
            # State
            self.initialized = False
            
            self._initialized = True
    
    def initialize(self):
        """Initialize all hardware components"""
        with self._lock:
            if self.initialized:
                self.logger.warning("Hardware manager already initialized")
                return
            
            try:
                self.logger.info("Initializing hardware components...")
                
                # Initialize GPIO system
                gpio_manager.initialize()
                
                # Register emergency callback
                self.emergency_stop.register_callback(self._emergency_handler)
                
                # Initialize motor controller
                self.logger.info("Initializing motor controller...")
                self.motor = MotorController()
                self.motor.initialize()
                self.watchdog.register_component('motor')
                
                # Initialize servo controller
                self.logger.info("Initializing servo controller...")
                self.servo = ServoController()
                self.servo.initialize()
                self.watchdog.register_component('servo')
                
                # Initialize LED controller
                self.logger.info("Initializing LED controller...")
                self.led = LEDController()
                self.led.initialize()
                self.led.set_status_color('idle')
                
                # Initialize ultrasonic sensor
                self.logger.info("Initializing ultrasonic sensor...")
                self.ultrasonic = UltrasonicController()
                self.ultrasonic.initialize()
                self.ultrasonic.register_obstacle_callback(self._obstacle_detected)
                self.ultrasonic.start_monitoring(interval=0.1)
                self.watchdog.register_component('ultrasonic')
                
                # Initialize camera
                self.logger.info("Initializing camera...")
                self.camera = CameraController(device_id=0, resolution=(640, 480), fps=30)
                self.camera.initialize()
                self.camera.start_capture()
                self.watchdog.register_component('camera')
                
                # Start watchdog
                self.watchdog.start()
                
                self.initialized = True
                self.logger.info("All hardware components initialized successfully")
                
            except Exception as e:
                self.logger.critical(f"Hardware initialization failed: {e}", exc_info=True)
                self.cleanup()
                raise
    
    def get_status(self) -> dict:
        """Get status of all hardware components"""
        status = {
            'initialized': self.initialized,
            'emergency': self.emergency_stop.get_status(),
            'watchdog': self.watchdog.get_status(),
            'health': self.hardware_monitor.get_system_health()
        }
        
        if self.motor:
            status['motor'] = self.motor.get_status()
            self.hardware_monitor.update_component_state('motor', status['motor'])
        
        if self.servo:
            status['servo'] = self.servo.get_status()
            self.hardware_monitor.update_component_state('servo', status['servo'])
        
        if self.led:
            status['led'] = self.led.get_status()
            self.hardware_monitor.update_component_state('led', status['led'])
        
        if self.ultrasonic:
            status['ultrasonic'] = self.ultrasonic.get_status()
            self.hardware_monitor.update_component_state('ultrasonic', status['ultrasonic'])
        
        if self.camera:
            status['camera'] = self.camera.get_status()
            self.hardware_monitor.update_component_state('camera', status['camera'])
        
        return status
    
    def heartbeat(self, component: str):
        """
        Send heartbeat for component
        
        Args:
            component: Component name
        """
        self.watchdog.heartbeat(component)
    
    def trigger_emergency(self, trigger: EmergencyTrigger, message: str = ""):
        """
        Trigger emergency stop
        
        Args:
            trigger: Emergency trigger type
            message: Additional information
        """
        self.emergency_stop.trigger_emergency(trigger, message)
    
    def reset_emergency(self):
        """Reset emergency stop"""
        self.emergency_stop.reset_emergency()
        
        # Reset motor safety
        if self.motor:
            self.motor.safety.reset_emergency_stop()
    
    def _emergency_handler(self, trigger: EmergencyTrigger, message: str):
        """Handle emergency events"""
        self.logger.critical(f"Emergency handler activated: {trigger.value} - {message}")
        
        # Stop all motors immediately
        if self.motor:
            self.motor.emergency_stop()
        
        # Set LED to emergency color
        if self.led:
            self.led.set_status_color('emergency')
    
    def _obstacle_detected(self, distance: float):
        """Handle obstacle detection"""
        self.logger.warning(f"Obstacle detected at {distance}cm")
        self.trigger_emergency(
            EmergencyTrigger.OBSTACLE_DETECTED,
            f"Obstacle at {distance}cm"
        )
    
    def cleanup(self):
        """Cleanup all hardware components"""
        with self._lock:
            self.logger.info("Cleaning up hardware components...")
            
            # Stop watchdog
            if hasattr(self, 'watchdog'):
                self.watchdog.stop()
            
            # Cleanup components
            if self.ultrasonic:
                self.ultrasonic.cleanup()
            
            if self.camera:
                self.camera.cleanup()
            
            if self.motor:
                self.motor.cleanup()
            
            if self.servo:
                self.servo.cleanup()
            
            if self.led:
                self.led.cleanup()
            
            # Cleanup PWM and GPIO
            pwm_manager.cleanup()
            gpio_manager.cleanup_all()
            
            self.logger.info("Hardware cleanup complete")


# Global instance
hardware_manager = HardwareManager()
