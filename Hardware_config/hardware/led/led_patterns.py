"""
LED Patterns
Defines color patterns and sequences for LED effects
"""

from typing import List, Tuple


class LEDPatterns:
    """Predefined LED color patterns"""
    
    # Status colors
    STATUS_IDLE = (0, 255, 0)        # Green
    STATUS_MOVING = (0, 0, 255)      # Blue
    STATUS_WARNING = (255, 165, 0)   # Orange
    STATUS_EMERGENCY = (255, 0, 0)   # Red
    STATUS_CONNECTED = (0, 255, 255) # Cyan
    STATUS_DISCONNECTED = (128, 0, 128)  # Purple
    
    # Rainbow pattern (HSV converted to RGB)
    RAINBOW = [
        (255, 0, 0),      # Red
        (255, 127, 0),    # Orange
        (255, 255, 0),    # Yellow
        (0, 255, 0),      # Green
        (0, 0, 255),      # Blue
        (75, 0, 130),     # Indigo
        (148, 0, 211),    # Violet
    ]
    
    # Police pattern
    POLICE = [
        (255, 0, 0),      # Red
        (0, 0, 255),      # Blue
    ]
    
    @staticmethod
    def get_status_color(status: str) -> Tuple[int, int, int]:
        """
        Get color for status
        
        Args:
            status: Status name
            
        Returns:
            RGB tuple
        """
        status_map = {
            'idle': LEDPatterns.STATUS_IDLE,
            'moving': LEDPatterns.STATUS_MOVING,
            'warning': LEDPatterns.STATUS_WARNING,
            'emergency': LEDPatterns.STATUS_EMERGENCY,
            'connected': LEDPatterns.STATUS_CONNECTED,
            'disconnected': LEDPatterns.STATUS_DISCONNECTED,
        }
        
        return status_map.get(status.lower(), LEDPatterns.STATUS_IDLE)
    
    @staticmethod
    def interpolate_color(color1: Tuple[int, int, int], 
                         color2: Tuple[int, int, int],
                         factor: float) -> Tuple[int, int, int]:
        """
        Interpolate between two colors
        
        Args:
            color1: Start color (R, G, B)
            color2: End color (R, G, B)
            factor: Interpolation factor (0.0 to 1.0)
            
        Returns:
            Interpolated color
        """
        r = int(color1[0] + (color2[0] - color1[0]) * factor)
        g = int(color1[1] + (color2[1] - color1[1]) * factor)
        b = int(color1[2] + (color2[2] - color1[2]) * factor)
        
        return (r, g, b)
