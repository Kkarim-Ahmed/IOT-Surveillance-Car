"""
Hardware Monitor
Monitors hardware state and health
"""

import threading
from typing import Dict, Optional
from hardware.utils.logger import get_logger


class HardwareMonitor:
    """
    Hardware health monitoring
    Tracks hardware state and detects anomalies
    """
    
    def __init__(self):
        self.logger = get_logger("hardware_monitor")
        
        # Component states
        self.component_states: Dict[str, dict] = {}
        
        # Threading
        self._lock = threading.RLock()
    
    def update_component_state(self, component: str, state: dict):
        """
        Update component state
        
        Args:
            component: Component name
            state: State dictionary
        """
        with self._lock:
            self.component_states[component] = {
                **state,
                'last_update': threading.current_thread().name
            }
    
    def get_component_state(self, component: str) -> Optional[dict]:
        """
        Get component state
        
        Args:
            component: Component name
            
        Returns:
            State dictionary or None
        """
        return self.component_states.get(component)
    
    def get_all_states(self) -> Dict[str, dict]:
        """Get all component states"""
        with self._lock:
            return self.component_states.copy()
    
    def check_component_health(self, component: str) -> bool:
        """
        Check if component is healthy
        
        Args:
            component: Component name
            
        Returns:
            True if healthy
        """
        state = self.get_component_state(component)
        
        if state is None:
            return False
        
        # Check if initialized
        if not state.get('initialized', False):
            return False
        
        # Component-specific checks
        if component == 'motor':
            return not state.get('emergency_stopped', False)
        
        return True
    
    def get_system_health(self) -> dict:
        """Get overall system health"""
        health = {
            'healthy': True,
            'components': {}
        }
        
        for component, state in self.component_states.items():
            is_healthy = self.check_component_health(component)
            health['components'][component] = is_healthy
            
            if not is_healthy:
                health['healthy'] = False
        
        return health
