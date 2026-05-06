"""
Watchdog System
Monitors hardware components and triggers emergency on timeout
"""

import time
import threading
from typing import Dict
from hardware.utils.logger import get_logger
from hardware.utils.threading_utils import StoppableThread
from hardware.safety.emergency_stop import EmergencyStop, EmergencyTrigger


class Watchdog:
    """
    Hardware watchdog system
    Monitors component heartbeats and triggers emergency on timeout
    """
    
    def __init__(self, emergency_stop: EmergencyStop, timeout: float = 10.0, 
                 check_interval: float = 1.0):
        """
        Initialize watchdog
        
        Args:
            emergency_stop: Emergency stop system
            timeout: Timeout in seconds
            check_interval: Check interval in seconds
        """
        self.logger = get_logger("watchdog")
        self.emergency_stop = emergency_stop
        self.timeout = timeout
        self.check_interval = check_interval
        
        # Component heartbeats
        self.heartbeats: Dict[str, float] = {}
        self.monitored_components: set = set()
        
        # Watchdog thread
        self.running = False
        self.watchdog_thread: Optional[StoppableThread] = None
        
        # Threading
        self._lock = threading.RLock()
    
    def start(self):
        """Start watchdog monitoring"""
        with self._lock:
            if self.running:
                self.logger.warning("Watchdog already running")
                return
            
            self.running = True
            
            self.watchdog_thread = StoppableThread(
                target=self._watchdog_loop,
                name="Watchdog"
            )
            self.watchdog_thread.start()
            
            self.logger.info("Watchdog started")
    
    def stop(self):
        """Stop watchdog monitoring"""
        with self._lock:
            if self.running:
                self.running = False
                if self.watchdog_thread:
                    self.watchdog_thread.stop()
                    self.watchdog_thread.join(timeout=2.0)
                self.logger.info("Watchdog stopped")
    
    def register_component(self, component_name: str):
        """
        Register component for monitoring
        
        Args:
            component_name: Name of component to monitor
        """
        with self._lock:
            self.monitored_components.add(component_name)
            self.heartbeats[component_name] = time.time()
            self.logger.debug(f"Registered component: {component_name}")
    
    def heartbeat(self, component_name: str):
        """
        Update component heartbeat
        
        Args:
            component_name: Name of component
        """
        with self._lock:
            if component_name in self.monitored_components:
                self.heartbeats[component_name] = time.time()
    
    def check_component(self, component_name: str) -> bool:
        """
        Check if component is alive
        
        Args:
            component_name: Name of component
            
        Returns:
            True if component is alive
        """
        if component_name not in self.heartbeats:
            return True  # Not monitored
        
        elapsed = time.time() - self.heartbeats[component_name]
        return elapsed < self.timeout
    
    def get_status(self) -> dict:
        """Get watchdog status"""
        status = {
            'running': self.running,
            'timeout': self.timeout,
            'components': {}
        }
        
        current_time = time.time()
        for component in self.monitored_components:
            last_heartbeat = self.heartbeats.get(component, 0)
            elapsed = current_time - last_heartbeat
            status['components'][component] = {
                'alive': elapsed < self.timeout,
                'last_heartbeat': elapsed
            }
        
        return status
    
    def _watchdog_loop(self):
        """Watchdog monitoring loop"""
        while self.running and not self.watchdog_thread.stopped():
            try:
                current_time = time.time()
                
                # Check all components
                for component in self.monitored_components:
                    last_heartbeat = self.heartbeats.get(component, 0)
                    elapsed = current_time - last_heartbeat
                    
                    if elapsed > self.timeout:
                        self.logger.error(f"Component {component} timeout: {elapsed:.1f}s")
                        self.emergency_stop.trigger_emergency(
                            EmergencyTrigger.WATCHDOG_TIMEOUT,
                            f"Component {component} timeout"
                        )
                        break
                
                time.sleep(self.check_interval)
                
            except Exception as e:
                self.logger.error(f"Error in watchdog loop: {e}")
                time.sleep(self.check_interval)
