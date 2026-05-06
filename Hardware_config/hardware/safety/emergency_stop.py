"""
Emergency Stop System
Handles emergency stop triggers and responses
"""

import threading
from enum import Enum
from datetime import datetime
from typing import List, Callable, Optional
from hardware.utils.logger import get_logger, HardwareLogger


class EmergencyTrigger(Enum):
    """Emergency trigger types"""
    OBSTACLE_DETECTED = "obstacle_detected"
    COMMUNICATION_TIMEOUT = "communication_timeout"
    INVALID_GPIO_STATE = "invalid_gpio_state"
    MANUAL_BUTTON = "manual_button"
    WATCHDOG_TIMEOUT = "watchdog_timeout"
    HARDWARE_ERROR = "hardware_error"


class EmergencyStop:
    """
    Emergency stop system
    Manages emergency triggers and callbacks
    """
    
    def __init__(self):
        self.logger = get_logger("emergency_stop")
        
        # State
        self.emergency_active = False
        self.trigger: Optional[EmergencyTrigger] = None
        self.trigger_time: Optional[datetime] = None
        self.trigger_message: str = ""
        
        # Callbacks
        self.emergency_callbacks: List[Callable] = []
        
        # Threading
        self._lock = threading.RLock()
    
    def trigger_emergency(self, trigger: EmergencyTrigger, message: str = ""):
        """
        Trigger emergency stop
        
        Args:
            trigger: Type of emergency trigger
            message: Additional information
        """
        with self._lock:
            if self.emergency_active:
                self.logger.warning(f"Emergency already active: {self.trigger.value}")
                return
            
            self.emergency_active = True
            self.trigger = trigger
            self.trigger_time = datetime.now()
            self.trigger_message = message
            
            # Log emergency
            HardwareLogger.log_emergency(
                "emergency_stop",
                f"{trigger.value}: {message}"
            )
            
            self.logger.critical(f"EMERGENCY STOP: {trigger.value} - {message}")
            
            # Execute callbacks
            self._execute_callbacks(trigger, message)
    
    def reset_emergency(self):
        """Reset emergency stop state"""
        with self._lock:
            if not self.emergency_active:
                self.logger.warning("No emergency to reset")
                return
            
            self.logger.info(f"Resetting emergency: {self.trigger.value}")
            
            self.emergency_active = False
            self.trigger = None
            self.trigger_time = None
            self.trigger_message = ""
    
    def is_emergency_active(self) -> bool:
        """Check if emergency is active"""
        return self.emergency_active
    
    def register_callback(self, callback: Callable):
        """
        Register emergency callback
        
        Args:
            callback: Function to call on emergency (trigger, message)
        """
        self.emergency_callbacks.append(callback)
        self.logger.debug(f"Registered emergency callback: {callback.__name__}")
    
    def get_status(self) -> dict:
        """Get emergency stop status"""
        return {
            'active': self.emergency_active,
            'trigger': self.trigger.value if self.trigger else None,
            'time': self.trigger_time.isoformat() if self.trigger_time else None,
            'message': self.trigger_message
        }
    
    def _execute_callbacks(self, trigger: EmergencyTrigger, message: str):
        """Execute all registered callbacks"""
        for callback in self.emergency_callbacks:
            try:
                callback(trigger, message)
            except Exception as e:
                self.logger.error(f"Error in emergency callback {callback.__name__}: {e}")
