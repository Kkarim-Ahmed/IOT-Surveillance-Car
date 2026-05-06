"""
GPIO Manager
Centralized GPIO pin management with thread-safe operations
"""

import threading
from typing import Dict, List, Optional, Set
from hardware.utils.logger import get_logger
from hardware.gpio.pin_definitions import pin_defs

try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except (ImportError, RuntimeError):
    GPIO_AVAILABLE = False
    print("WARNING: RPi.GPIO not available. Running in simulation mode.")


class GPIOManager:
    """
    Centralized GPIO management system
    Provides thread-safe GPIO operations and pin tracking
    """
    
    _instance: Optional['GPIOManager'] = None
    _lock = threading.RLock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
            return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self.logger = get_logger("gpio_manager")
            self.pin_defs = pin_defs
            
            # Track active pins
            self.active_pins: Set[int] = set()
            self.pin_modes: Dict[int, str] = {}  # pin -> 'IN' or 'OUT'
            self.pin_locks: Dict[int, threading.RLock] = {}
            
            # GPIO state
            self.initialized = False
            self.simulation_mode = not GPIO_AVAILABLE
            
            self._initialized = True
    
    def initialize(self):
        """Initialize GPIO system"""
        with self._lock:
            if self.initialized:
                self.logger.warning("GPIO already initialized")
                return
            
            if self.simulation_mode:
                self.logger.warning("Running in SIMULATION mode - no actual GPIO control")
                self.initialized = True
                return
            
            try:
                # Set GPIO mode
                if self.pin_defs.board_mode == 'BCM':
                    GPIO.setmode(GPIO.BCM)
                else:
                    GPIO.setmode(GPIO.BOARD)
                
                # Configure warnings
                GPIO.setwarnings(self.pin_defs.config.get('warnings_enabled', True))
                
                self.initialized = True
                self.logger.info(f"GPIO initialized in {self.pin_defs.board_mode} mode")
                
            except Exception as e:
                self.logger.error(f"Failed to initialize GPIO: {e}")
                raise
    
    def setup_output(self, pin: int, initial: int = 0) -> bool:
        """
        Setup pin as output
        
        Args:
            pin: GPIO pin number
            initial: Initial state (0 or 1)
            
        Returns:
            True if successful
        """
        with self._lock:
            if not self.initialized:
                raise RuntimeError("GPIO not initialized")
            
            # Validate pin
            self.pin_defs.validate_pin(pin)
            
            if self.simulation_mode:
                self.logger.debug(f"[SIM] Setup pin {pin} as OUTPUT, initial={initial}")
                self.active_pins.add(pin)
                self.pin_modes[pin] = 'OUT'
                return True
            
            try:
                GPIO.setup(pin, GPIO.OUT, initial=GPIO.HIGH if initial else GPIO.LOW)
                self.active_pins.add(pin)
                self.pin_modes[pin] = 'OUT'
                self.pin_locks[pin] = threading.RLock()
                
                self.logger.debug(f"Pin {pin} configured as OUTPUT")
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to setup pin {pin} as output: {e}")
                return False
    
    def setup_input(self, pin: int, pull_up_down: Optional[str] = None) -> bool:
        """
        Setup pin as input
        
        Args:
            pin: GPIO pin number
            pull_up_down: 'UP', 'DOWN', or None
            
        Returns:
            True if successful
        """
        with self._lock:
            if not self.initialized:
                raise RuntimeError("GPIO not initialized")
            
            # Validate pin
            self.pin_defs.validate_pin(pin)
            
            if self.simulation_mode:
                self.logger.debug(f"[SIM] Setup pin {pin} as INPUT, pull={pull_up_down}")
                self.active_pins.add(pin)
                self.pin_modes[pin] = 'IN'
                return True
            
            try:
                if pull_up_down == 'UP':
                    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                elif pull_up_down == 'DOWN':
                    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
                else:
                    GPIO.setup(pin, GPIO.IN)
                
                self.active_pins.add(pin)
                self.pin_modes[pin] = 'IN'
                self.pin_locks[pin] = threading.RLock()
                
                self.logger.debug(f"Pin {pin} configured as INPUT")
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to setup pin {pin} as input: {e}")
                return False
    
    def output(self, pin: int, state: bool):
        """
        Set output pin state
        
        Args:
            pin: GPIO pin number
            state: True for HIGH, False for LOW
        """
        if pin not in self.active_pins:
            raise ValueError(f"Pin {pin} not configured")
        
        if self.pin_modes.get(pin) != 'OUT':
            raise ValueError(f"Pin {pin} not configured as output")
        
        if self.simulation_mode:
            return
        
        with self.pin_locks[pin]:
            GPIO.output(pin, GPIO.HIGH if state else GPIO.LOW)
    
    def input(self, pin: int) -> bool:
        """
        Read input pin state
        
        Args:
            pin: GPIO pin number
            
        Returns:
            True for HIGH, False for LOW
        """
        if pin not in self.active_pins:
            raise ValueError(f"Pin {pin} not configured")
        
        if self.pin_modes.get(pin) != 'IN':
            raise ValueError(f"Pin {pin} not configured as input")
        
        if self.simulation_mode:
            return False
        
        with self.pin_locks[pin]:
            return GPIO.input(pin) == GPIO.HIGH
    
    def cleanup_pin(self, pin: int):
        """Cleanup specific pin"""
        with self._lock:
            if pin in self.active_pins:
                if not self.simulation_mode:
                    GPIO.cleanup(pin)
                
                self.active_pins.remove(pin)
                self.pin_modes.pop(pin, None)
                self.pin_locks.pop(pin, None)
                
                self.logger.debug(f"Pin {pin} cleaned up")
    
    def cleanup_all(self):
        """Cleanup all GPIO pins"""
        with self._lock:
            if not self.initialized:
                return
            
            if self.simulation_mode:
                self.logger.info("[SIM] GPIO cleanup")
                self.active_pins.clear()
                self.pin_modes.clear()
                return
            
            try:
                GPIO.cleanup()
                self.active_pins.clear()
                self.pin_modes.clear()
                self.pin_locks.clear()
                
                self.logger.info("All GPIO pins cleaned up")
                
            except Exception as e:
                self.logger.error(f"Error during GPIO cleanup: {e}")
    
    def get_active_pins(self) -> List[int]:
        """Get list of active pins"""
        return list(self.active_pins)
    
    def is_pin_active(self, pin: int) -> bool:
        """Check if pin is active"""
        return pin in self.active_pins


# Global instance
gpio_manager = GPIOManager()
