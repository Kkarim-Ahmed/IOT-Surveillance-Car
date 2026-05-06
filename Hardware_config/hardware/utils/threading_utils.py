"""
Threading Utilities
Provides thread-safe utilities for hardware control
"""

import threading
from typing import Any, Callable, Optional
from functools import wraps


class ThreadSafeLock:
    """Thread-safe lock wrapper"""
    
    def __init__(self, name: str = "unnamed"):
        self.lock = threading.RLock()
        self.name = name
    
    def __enter__(self):
        self.lock.acquire()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.lock.release()
    
    def acquire(self, blocking: bool = True, timeout: float = -1) -> bool:
        """Acquire lock"""
        return self.lock.acquire(blocking, timeout)
    
    def release(self):
        """Release lock"""
        self.lock.release()


def thread_safe(func: Callable) -> Callable:
    """Decorator to make a method thread-safe"""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if not hasattr(self, '_lock'):
            self._lock = threading.RLock()
        
        with self._lock:
            return func(self, *args, **kwargs)
    
    return wrapper


class StoppableThread(threading.Thread):
    """Thread that can be stopped gracefully"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._stop_event = threading.Event()
        self.daemon = True
    
    def stop(self):
        """Signal thread to stop"""
        self._stop_event.set()
    
    def stopped(self) -> bool:
        """Check if stop was requested"""
        return self._stop_event.is_set()
    
    def wait(self, timeout: Optional[float] = None) -> bool:
        """Wait for stop signal"""
        return self._stop_event.wait(timeout)


class SharedResource:
    """Thread-safe shared resource"""
    
    def __init__(self, initial_value: Any = None):
        self._value = initial_value
        self._lock = threading.RLock()
    
    def get(self) -> Any:
        """Get resource value"""
        with self._lock:
            return self._value
    
    def set(self, value: Any):
        """Set resource value"""
        with self._lock:
            self._value = value
    
    def update(self, func: Callable[[Any], Any]):
        """Update resource using function"""
        with self._lock:
            self._value = func(self._value)
