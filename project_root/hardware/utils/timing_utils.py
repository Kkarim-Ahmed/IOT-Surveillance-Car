"""
Timing Utilities
Provides precise timing utilities for hardware control
"""

import time
from typing import Callable, Optional
from functools import wraps


class Timer:
    """Simple timer for measuring elapsed time"""
    
    def __init__(self):
        self.start_time: Optional[float] = None
        self.elapsed_time: float = 0.0
    
    def start(self):
        """Start timer"""
        self.start_time = time.time()
    
    def stop(self) -> float:
        """Stop timer and return elapsed time"""
        if self.start_time is not None:
            self.elapsed_time = time.time() - self.start_time
            self.start_time = None
        return self.elapsed_time
    
    def elapsed(self) -> float:
        """Get elapsed time without stopping"""
        if self.start_time is not None:
            return time.time() - self.start_time
        return self.elapsed_time
    
    def reset(self):
        """Reset timer"""
        self.start_time = None
        self.elapsed_time = 0.0


class RateLimiter:
    """Rate limiter for controlling execution frequency"""
    
    def __init__(self, rate_hz: float):
        """
        Initialize rate limiter
        
        Args:
            rate_hz: Maximum rate in Hz (executions per second)
        """
        self.interval = 1.0 / rate_hz
        self.last_time = 0.0
    
    def wait(self):
        """Wait if necessary to maintain rate"""
        current_time = time.time()
        elapsed = current_time - self.last_time
        
        if elapsed < self.interval:
            time.sleep(self.interval - elapsed)
        
        self.last_time = time.time()
    
    def ready(self) -> bool:
        """Check if ready for next execution"""
        current_time = time.time()
        elapsed = current_time - self.last_time
        return elapsed >= self.interval


def rate_limited(rate_hz: float) -> Callable:
    """Decorator to rate limit function calls"""
    def decorator(func: Callable) -> Callable:
        limiter = RateLimiter(rate_hz)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            limiter.wait()
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def timeout(seconds: float) -> Callable:
    """Decorator to add timeout to function"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            import signal
            
            def timeout_handler(signum, frame):
                raise TimeoutError(f"Function {func.__name__} timed out after {seconds} seconds")
            
            # Set alarm
            old_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(int(seconds))
            
            try:
                result = func(*args, **kwargs)
            finally:
                # Cancel alarm
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old_handler)
            
            return result
        
        return wrapper
    return decorator


def retry(max_attempts: int = 3, delay: float = 0.1) -> Callable:
    """Decorator to retry function on failure"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        time.sleep(delay)
            
            raise last_exception
        
        return wrapper
    return decorator


class Debouncer:
    """Debounce rapid changes"""
    
    def __init__(self, delay: float = 0.1):
        """
        Initialize debouncer
        
        Args:
            delay: Debounce delay in seconds
        """
        self.delay = delay
        self.last_time = 0.0
        self.last_value = None
    
    def update(self, value: any) -> bool:
        """
        Update value with debouncing
        
        Returns:
            True if value changed after debounce period
        """
        current_time = time.time()
        
        if value != self.last_value:
            if current_time - self.last_time >= self.delay:
                self.last_value = value
                self.last_time = current_time
                return True
        
        return False
