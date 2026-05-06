#!/usr/bin/env python3
"""
LED Control Demonstration
Shows various LED effects and color patterns
"""

import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from hardware.led.led_controller import LEDController, LEDEffect
from hardware.utils.logger import get_logger


def main():
    """Run LED demonstration"""
    logger = get_logger("led_demo")
    
    logger.info("=" * 60)
    logger.info("LED Control Demonstration")
    logger.info("=" * 60)
    
    # Initialize LED controller
    led = LEDController()
    
    try:
        led.initialize()
        logger.info("LED controller initialized")
        time.sleep(1)
        
        # Demo 1: Basic colors
        logger.info("\n--- Demo 1: Basic Colors ---")
        
        colors = [
            ((255, 0, 0), "Red"),
            ((0, 255, 0), "Green"),
            ((0, 0, 255), "Blue"),
            ((255, 255, 0), "Yellow"),
            ((255, 0, 255), "Magenta"),
            ((0, 255, 255), "Cyan"),
            ((255, 255, 255), "White")
        ]
        
        for (r, g, b), name in colors:
            logger.info(f"Setting color to {name}...")
            led.set_color(r, g, b)
            time.sleep(1)
        
        led.turn_off()
        time.sleep(1)
        
        # Demo 2: Brightness control
        logger.info("\n--- Demo 2: Brightness Control ---")
        led.set_color(255, 255, 255)
        
        brightness_levels = [100, 75, 50, 25, 10, 25, 50, 75, 100]
        for brightness in brightness_levels:
            logger.info(f"Brightness: {brightness}%")
            led.set_brightness(brightness)
            time.sleep(0.5)
        
        led.turn_off()
        time.sleep(1)
        
        # Demo 3: Status colors
        logger.info("\n--- Demo 3: Status Colors ---")
        
        statuses = ['idle', 'moving', 'warning', 'emergency', 'success']
        for status in statuses:
            logger.info(f"Status: {status}")
            led.set_status_color(status)
            time.sleep(1.5)
        
        led.turn_off()
        time.sleep(1)
        
        # Demo 4: Rainbow effect
        logger.info("\n--- Demo 4: Rainbow Effect ---")
        logger.info("Starting rainbow effect for 5 seconds...")
        led.start_effect(LEDEffect.RAINBOW)
        time.sleep(5)
        led.stop_effect()
        time.sleep(1)
        
        # Demo 5: Blink effect
        logger.info("\n--- Demo 5: Blink Effect ---")
        logger.info("Red blinking...")
        led.set_color(255, 0, 0)
        led.start_effect(LEDEffect.BLINK)
        time.sleep(3)
        led.stop_effect()
        time.sleep(1)
        
        # Demo 6: Fade effect
        logger.info("\n--- Demo 6: Fade Effect ---")
        logger.info("Blue fading...")
        led.set_color(0, 0, 255)
        led.start_effect(LEDEffect.FADE)
        time.sleep(4)
        led.stop_effect()
        time.sleep(1)
        
        # Demo 7: Pulse effect
        logger.info("\n--- Demo 7: Pulse Effect ---")
        logger.info("Green pulsing...")
        led.set_color(0, 255, 0)
        led.start_effect(LEDEffect.PULSE)
        time.sleep(4)
        led.stop_effect()
        time.sleep(1)
        
        # Demo 8: Strobe effect
        logger.info("\n--- Demo 8: Strobe Effect ---")
        logger.info("White strobe...")
        led.set_color(255, 255, 255)
        led.start_effect(LEDEffect.STROBE)
        time.sleep(3)
        led.stop_effect()
        time.sleep(1)
        
        # Demo 9: Emergency flash
        logger.info("\n--- Demo 9: Emergency Flash ---")
        logger.info("Emergency flash pattern...")
        led.start_effect(LEDEffect.EMERGENCY_FLASH)
        time.sleep(4)
        led.stop_effect()
        time.sleep(1)
        
        # Demo 10: Color transitions
        logger.info("\n--- Demo 10: Smooth Color Transitions ---")
        logger.info("Transitioning through colors...")
        
        transition_colors = [
            (255, 0, 0),    # Red
            (255, 127, 0),  # Orange
            (255, 255, 0),  # Yellow
            (0, 255, 0),    # Green
            (0, 0, 255),    # Blue
            (75, 0, 130),   # Indigo
            (148, 0, 211),  # Violet
        ]
        
        for r, g, b in transition_colors:
            led.set_color(r, g, b)
            time.sleep(0.8)
        
        led.turn_off()
        time.sleep(1)
        
        # Demo 11: Breathing effect
        logger.info("\n--- Demo 11: Breathing Effect ---")
        logger.info("Cyan breathing...")
        led.set_color(0, 255, 255)
        
        for _ in range(3):
            # Breathe in
            for brightness in range(0, 101, 5):
                led.set_brightness(brightness)
                time.sleep(0.03)
            # Breathe out
            for brightness in range(100, -1, -5):
                led.set_brightness(brightness)
                time.sleep(0.03)
        
        led.turn_off()
        time.sleep(1)
        
        # Demo 12: Status indication sequence
        logger.info("\n--- Demo 12: Status Indication Sequence ---")
        logger.info("Simulating system startup sequence...")
        
        sequence = [
            ('idle', "System idle", 1),
            ('moving', "System active", 1.5),
            ('success', "Operation successful", 1),
            ('warning', "Warning condition", 1.5),
            ('emergency', "Emergency!", 2),
            ('idle', "System reset", 1)
        ]
        
        for status, message, duration in sequence:
            logger.info(message)
            led.set_status_color(status)
            time.sleep(duration)
        
        led.turn_off()
        
        # Show final status
        logger.info("\n--- Final Status ---")
        status = led.get_status()
        logger.info(f"Color: {status['color']}")
        logger.info(f"Brightness: {status['brightness']}%")
        logger.info(f"Effect running: {status['effect_running']}")
        
        logger.info("\n" + "=" * 60)
        logger.info("LED demonstration complete!")
        logger.info("=" * 60)
        
    except KeyboardInterrupt:
        logger.info("\nDemo interrupted by user")
    
    except Exception as e:
        logger.error(f"Demo error: {e}", exc_info=True)
    
    finally:
        logger.info("Cleaning up...")
        led.cleanup()


if __name__ == "__main__":
    main()
