"""
Distance Filter
Filters noisy ultrasonic sensor readings
"""

from collections import deque
from typing import Optional
from hardware.utils.logger import get_logger


class DistanceFilter:
    """Filters ultrasonic distance measurements"""
    
    def __init__(self, window_size: int = 3, noise_threshold: float = 5.0):
        """
        Initialize distance filter
        
        Args:
            window_size: Number of samples for moving average
            noise_threshold: Threshold for noise rejection (cm)
        """
        self.logger = get_logger("distance_filter")
        self.window_size = window_size
        self.noise_threshold = noise_threshold
        
        self.buffer = deque(maxlen=window_size)
        self.last_valid_distance: Optional[float] = None
    
    def add_measurement(self, distance: float) -> Optional[float]:
        """
        Add measurement and get filtered value
        
        Args:
            distance: Raw distance measurement
            
        Returns:
            Filtered distance or None if invalid
        """
        # Validate measurement
        if distance <= 0:
            return self.last_valid_distance
        
        # Add to buffer
        self.buffer.append(distance)
        
        # Calculate filtered value
        if len(self.buffer) < self.window_size:
            # Not enough samples yet
            filtered = distance
        else:
            # Moving average
            filtered = sum(self.buffer) / len(self.buffer)
            
            # Noise rejection
            if self.last_valid_distance is not None:
                diff = abs(filtered - self.last_valid_distance)
                if diff > self.noise_threshold:
                    # Large change - might be noise, use median instead
                    sorted_buffer = sorted(self.buffer)
                    filtered = sorted_buffer[len(sorted_buffer) // 2]
        
        self.last_valid_distance = filtered
        return filtered
    
    def reset(self):
        """Reset filter"""
        self.buffer.clear()
        self.last_valid_distance = None
    
    def get_last_valid(self) -> Optional[float]:
        """Get last valid distance"""
        return self.last_valid_distance
