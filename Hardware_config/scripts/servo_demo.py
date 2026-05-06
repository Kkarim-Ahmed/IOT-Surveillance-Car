#!/usr/bin/env python3
"""
Servo Control Demonstration
Shows various servo control patterns and capabilities
"""

import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from hardware.servo.servo_controller import ServoController
from hardware.utils.logger import get_logger


def main():
    """Run servo demonstration"""
    logger = get_logger("servo_demo")
    
    logger.info("=" * 60)
    logger.info("Servo Control Demonstration")
    logger.info("=" * 60)
    
    # Initialize servo controller
    servo = ServoController()
    
    try:
        servo.initialize()
        logger.info("Servo controller initialized")
        time.sleep(1)
        
        # Demo 1: Center position
        logger.info("\n--- Demo 1: Center Position ---")
        logger.info("Moving to center position...")
        servo.center()
        time.sleep(1)
        
        # Demo 2: Basic movements
        logger.info("\n--- Demo 2: Basic Movements ---")
        
        logger.info("Looking left...")
        servo.set_angle(pan=90, tilt=0)
        time.sleep(1)
        
        logger.info("Looking right...")
        servo.set_angle(pan=-90, tilt=0)
        time.sleep(1)
        
        logger.info("Looking up...")
        servo.set_angle(pan=0, tilt=45)
        time.sleep(1)
        
        logger.info("Looking down...")
        servo.set_angle(pan=0, tilt=-45)
        time.sleep(1)
        
        servo.center()
        time.sleep(1)
        
        # Demo 3: Smooth movement
        logger.info("\n--- Demo 3: Smooth Movement ---")
        logger.info("Smoothly moving from center to (45, 30)...")
        servo.move_smooth(pan=45, tilt=30, steps=10, delay=0.05)
        time.sleep(0.5)
        
        logger.info("Smoothly returning to center...")
        servo.move_smooth(pan=0, tilt=0, steps=10, delay=0.05)
        time.sleep(1)
        
        # Demo 4: Preset positions
        logger.info("\n--- Demo 4: Preset Positions ---")
        
        presets = ['home', 'look_left', 'look_right', 'look_up', 'look_down']
        for preset in presets:
            logger.info(f"Moving to preset: {preset}")
            servo.move_to_preset(preset)
            time.sleep(1)
        
        servo.center()
        time.sleep(1)
        
        # Demo 5: Horizontal scan
        logger.info("\n--- Demo 5: Horizontal Scan ---")
        logger.info("Scanning from -90 to +90 degrees...")
        servo.scan_horizontal(start=-90, end=90, step=15, delay=0.2)
        time.sleep(0.5)
        
        logger.info("Scanning back from +90 to -90 degrees...")
        servo.scan_horizontal(start=90, end=-90, step=15, delay=0.2)
        time.sleep(0.5)
        
        servo.center()
        time.sleep(1)
        
        # Demo 6: Vertical scan
        logger.info("\n--- Demo 6: Vertical Scan ---")
        logger.info("Scanning from -45 to +45 degrees...")
        servo.scan_vertical(start=-45, end=45, step=10, delay=0.2)
        time.sleep(0.5)
        
        servo.center()
        time.sleep(1)
        
        # Demo 7: Diagonal movements
        logger.info("\n--- Demo 7: Diagonal Movements ---")
        
        positions = [
            (45, 30, "Upper right"),
            (-45, 30, "Upper left"),
            (-45, -30, "Lower left"),
            (45, -30, "Lower right"),
            (0, 0, "Center")
        ]
        
        for pan, tilt, description in positions:
            logger.info(f"Moving to {description}: ({pan}, {tilt})")
            servo.move_smooth(pan=pan, tilt=tilt, steps=8, delay=0.03)
            time.sleep(0.5)
        
        # Demo 8: Tracking pattern
        logger.info("\n--- Demo 8: Tracking Pattern ---")
        logger.info("Simulating object tracking...")
        
        tracking_points = [
            (0, 0), (15, 5), (30, 10), (45, 15),
            (30, 20), (15, 15), (0, 10), (-15, 5),
            (-30, 0), (-15, -5), (0, 0)
        ]
        
        for pan, tilt in tracking_points:
            servo.set_angle(pan=pan, tilt=tilt)
            time.sleep(0.3)
        
        servo.center()
        time.sleep(1)
        
        # Demo 9: Search pattern
        logger.info("\n--- Demo 9: Search Pattern ---")
        logger.info("Executing search pattern...")
        
        # Sweep pattern
        for tilt_angle in [0, 20, -20, 0]:
            servo.set_angle(tilt=tilt_angle)
            servo.scan_horizontal(start=-60, end=60, step=20, delay=0.15)
            time.sleep(0.3)
        
        servo.center()
        
        # Show final status
        logger.info("\n--- Final Status ---")
        status = servo.get_status()
        logger.info(f"Pan angle: {status['pan']['angle']}°")
        logger.info(f"Tilt angle: {status['tilt']['angle']}°")
        logger.info(f"Pan limits: {status['pan']['limits']}")
        logger.info(f"Tilt limits: {status['tilt']['limits']}")
        
        logger.info("\n" + "=" * 60)
        logger.info("Servo demonstration complete!")
        logger.info("=" * 60)
        
    except KeyboardInterrupt:
        logger.info("\nDemo interrupted by user")
    
    except Exception as e:
        logger.error(f"Demo error: {e}", exc_info=True)
    
    finally:
        logger.info("Cleaning up...")
        servo.cleanup()


if __name__ == "__main__":
    main()
