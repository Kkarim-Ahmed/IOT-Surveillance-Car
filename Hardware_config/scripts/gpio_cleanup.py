#!/usr/bin/env python3
"""
GPIO Cleanup Script
Safely cleanup all GPIO pins
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from hardware.gpio.gpio_manager import gpio_manager
from hardware.gpio.pwm_manager import pwm_manager


def main():
    """Cleanup GPIO"""
    print("Cleaning up GPIO pins...")
    
    try:
        # Initialize if needed
        if not gpio_manager.initialized:
            gpio_manager.initialize()
        
        # Stop all PWM
        pwm_manager.stop_all()
        print("✓ PWM stopped")
        
        # Cleanup PWM
        pwm_manager.cleanup()
        print("✓ PWM cleaned up")
        
        # Cleanup GPIO
        gpio_manager.cleanup_all()
        print("✓ GPIO cleaned up")
        
        print("\nGPIO cleanup complete!")
        return 0
        
    except Exception as e:
        print(f"✗ Error during cleanup: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
