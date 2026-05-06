"""
LED Effects
Implements various LED animation effects
"""

import time
import math
from typing import Callable, Tuple
from hardware.led.led_patterns import LEDPatterns


class LEDEffects:
    """LED animation effects"""
    
    @staticmethod
    def blink(set_color_func: Callable, color: Tuple[int, int, int], 
             interval: float = 0.5, running_check: Callable = None):
        """
        Blink effect
        
        Args:
            set_color_func: Function to set LED color
            color: RGB color tuple
            interval: Blink interval in seconds
            running_check: Function that returns True while effect should run
        """
        while running_check is None or running_check():
            set_color_func(*color)
            time.sleep(interval)
            set_color_func(0, 0, 0)
            time.sleep(interval)
    
    @staticmethod
    def fade(set_color_func: Callable, color: Tuple[int, int, int],
            speed: float = 0.05, running_check: Callable = None):
        """
        Fade in/out effect
        
        Args:
            set_color_func: Function to set LED color
            color: RGB color tuple
            speed: Fade speed (delay between steps)
            running_check: Function that returns True while effect should run
        """
        while running_check is None or running_check():
            # Fade in
            for brightness in range(0, 101, 5):
                if running_check and not running_check():
                    break
                r = int(color[0] * brightness / 100)
                g = int(color[1] * brightness / 100)
                b = int(color[2] * brightness / 100)
                set_color_func(r, g, b)
                time.sleep(speed)
            
            # Fade out
            for brightness in range(100, -1, -5):
                if running_check and not running_check():
                    break
                r = int(color[0] * brightness / 100)
                g = int(color[1] * brightness / 100)
                b = int(color[2] * brightness / 100)
                set_color_func(r, g, b)
                time.sleep(speed)
    
    @staticmethod
    def rainbow(set_color_func: Callable, speed: float = 0.05,
               running_check: Callable = None):
        """
        Rainbow color cycle effect
        
        Args:
            set_color_func: Function to set LED color
            speed: Animation speed
            running_check: Function that returns True while effect should run
        """
        colors = LEDPatterns.RAINBOW
        index = 0
        
        while running_check is None or running_check():
            set_color_func(*colors[index])
            index = (index + 1) % len(colors)
            time.sleep(speed * 10)
    
    @staticmethod
    def police(set_color_func: Callable, speed: float = 0.1,
              running_check: Callable = None):
        """
        Police lights effect (red/blue alternating)
        
        Args:
            set_color_func: Function to set LED color
            speed: Animation speed
            running_check: Function that returns True while effect should run
        """
        colors = LEDPatterns.POLICE
        index = 0
        
        while running_check is None or running_check():
            set_color_func(*colors[index])
            index = (index + 1) % len(colors)
            time.sleep(speed * 5)
    
    @staticmethod
    def pulse(set_color_func: Callable, color: Tuple[int, int, int],
             speed: float = 0.05, running_check: Callable = None):
        """
        Smooth pulse effect using sine wave
        
        Args:
            set_color_func: Function to set LED color
            color: RGB color tuple
            speed: Animation speed
            running_check: Function that returns True while effect should run
        """
        angle = 0
        
        while running_check is None or running_check():
            # Calculate brightness using sine wave (0 to 1)
            brightness = (math.sin(angle) + 1) / 2
            
            r = int(color[0] * brightness)
            g = int(color[1] * brightness)
            b = int(color[2] * brightness)
            
            set_color_func(r, g, b)
            
            angle += 0.1
            if angle > 2 * math.pi:
                angle = 0
            
            time.sleep(speed)
