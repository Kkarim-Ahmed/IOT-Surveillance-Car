"""
Ultrasonic Sensor Controller
Controls HC-SR04 ultrasonic distance sensor
"""

import time
import threading
from typing import Optional
from hardware.utils.logger import get_logger
from hardware.utils.threading_utils import thread_safe, StoppableThread
from hardware.utils.timing_utils import retry
from hardware.gpio.gpio_manager import gpio_manager
from hardware.gpio.pin_definitions import pin_defs
from hardware.ultrasonic.distance_filter import DistanceFilter
from hardware.ultrasonic.obstacle_detection import ObstacleDetection


class UltrasonicController:
    """
    HC-SR04 Ultrasonic Distance Sensor Controller
    Measures distance with filtering and obstacle detection
    """
    
    def __init__(self):
        self.logger = get_logger("ultrasonic_controller")
        
        # Sensor pins
        ultrasonic_pins = pin_defs.ultrasonic
        self.trigger_pin = ultrasonic_pins.trigger
        self.echo_pin = ultrasonic_pins.echo
        
        # Components
        self.filter = DistanceFilter(window_size=3, noise_threshold=5.0)
        self.obstacle_detection = ObstacleDetection()
        
        # State
        self.current_distance: Optional[float] = None
        self.is_monitoring = False
        self.monitor_thread: Optional[StoppableThread] = None
        
        self.initialized = False
        self._lock = threading.RLock()
    
    def initialize(self):
        """Initialize ultrasonic sensor"""
        with self._lock:
            if self.initialized:
                self.logger.warning("Ultrasonic sensor already initialized")
                return
            
            try:
                # Setup pins
                gpio_manager.setup_output(self.trigger_pin, initial=0)
                gpio_manager.setup_input(self.echo_pin)
                
                # Ensure trigger is low
                gpio_manager.output(self.trigger_pin, False)
                time.sleep(0.1)
                
                self.initialized = True
                self.logger.info("Ultrasonic sensor initialized")
                
            except Exception as e:
                self.logger.error(f"Failed to initialize ultrasonic sensor: {e}")
                raise
    
    @retry(max_attempts=3, delay=0.01)
    def measure_distance(self) -> Optional[float]:
        """
        Measure distance in centimeters
        
        Returns:
            Distance in cm or None if measurement failed
        """
        if not self.initialized:
            raise RuntimeError("Ultrasonic sensor not initialized")
        
        try:
            # Send trigger pulse
            gpio_manager.output(self.trigger_pin, True)
            time.sleep(0.00001)  # 10 microseconds
            gpio_manager.output(self.trigger_pin, False)
            
            # Wait for echo start
            timeout_start = time.time()
            while not gpio_manager.input(self.echo_pin):
                if time.sleep - timeout_start > 0.1:
                    return None
                pulse_start = time.time()
            
            # Wait for echo end
            timeout_start = time.time()
            while gpio_manager.input(self.echo_pin):
                if time.time() - timeout_start > 0.1:
                    return None
                pulse_end = time.time()
            
            # Calculate distance
            pulse_duration = pulse_end - pulse_start
            distance = pulse_duration * 17150  # Speed of sound / 2
            distance = round(distance, 2)
            
            # Validate distance
            if 2 <= distance <= 400:
                return distance
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error measuring distance: {e}")
            return None
    
    @thread_safe
    def get_filtered_distance(self) -> Optional[float]:
        """Get filtered distance measurement"""
        raw_distance = self.measure_distance()
        
        if raw_distance is not None:
            filtered_distance = self.filter.add_measurement(raw_distance)
            self.current_distance = filtered_distance
            return filtered_distance
        
        return self.filter.get_last_valid()
    
    @thread_safe
    def start_monitoring(self, interval: float = 0.1):
        """
        Start continuous distance monitoring
        
        Args:
            interval: Measurement interval in seconds
        """
        if self.is_monitoring:
            self.logger.warning("Monitoring already active")
            return
        
        self.is_monitoring = True
        
        self.monitor_thread = StoppableThread(
            target=self._monitor_loop,
            args=(interval,),
            name="Ultrasonic-Monitor"
        )
        self.monitor_thread.start()
        
        self.logger.info("Started distance monitoring")
    
    @thread_safe
    def stop_monitoring(self):
        """Stop continuous monitoring"""
        if self.is_monitoring:
            self.is_monitoring = False
            if self.monitor_thread:
                self.monitor_thread.stop()
                self.monitor_thread.join(timeout=1.0)
            self.logger.info("Stopped distance monitoring")
    
    def register_obstacle_callback(self, callback):
        """Register callback for obstacle detection"""
        self.obstacle_detection.register_obstacle_callback(callback)
    
    def get_status(self) -> dict:
        """Get sensor status"""
        distance = self.current_distance
        status = 'unknown'
        
        if distance is not None:
            status = self.obstacle_detection.check_distance(distance)
        
        return {
            'distance_cm': distance,
            'status': status,
            'monitoring': self.is_monitoring,
            'emergency_threshold': self.obstacle_detection.emergency_distance,
            'warning_threshold': self.obstacle_detection.warning_distance,
            'initialized': self.initialized
        }
    
    def _monitor_loop(self, interval: float):
        """Continuous monitoring loop"""
        while self.is_monitoring and not self.monitor_thread.stopped():
            try:
                distance = self.get_filtered_distance()
                
                if distance is not None:
                    # Check for obstacles
                    self.obstacle_detection.check_distance(distance)
                
                time.sleep(interval)
                
            except Exception as e:
                self.logger.error(f"Error in monitor loop: {e}")
                time.sleep(interval)
    
    def cleanup(self):
        """Cleanup ultrasonic sensor"""
        with self._lock:
            self.stop_monitoring()
            gpio_manager.output(self.trigger_pin, False)
            self.logger.info("Ultrasonic sensor cleaned up")
