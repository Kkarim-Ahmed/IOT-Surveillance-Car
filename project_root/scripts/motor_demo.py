#!/usr/bin/env python3
"""
Motor Control Demonstration
Shows various motor control patterns and capabilities
"""

import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from hardware.motor.motor_controller import MotorController
from hardware.utils.logger import get_logger


def main():
    """Run motor demonstration"""
    logger = get_logger("motor_demo")
    
    logger.info("=" * 60)
    logger.info("Motor Control Demonstration")
    logger.info("=" * 60)
    
    # Initialize motor controller
    motor = MotorController()
    
    try:
        motor.initialize()
        logger.info("Motor controller initialized")
        
        # Demo 1: Forward movement
        logger.info("\n--- Demo 1: Forward Movement ---")
        logger.info("Moving forward at 50% speed...")
        motor.move_forward(speed=50)
        time.sleep(2)
        motor.stop(smooth=True)
        logger.info("Stopped")
        time.sleep(1)
        
        # Demo 2: Backward movement
        logger.info("\n--- Demo 2: Backward Movement ---")
        logger.info("Moving backward at 50% speed...")
        motor.move_backward(speed=50)
        time.sleep(2)
        motor.stop(smooth=True)
        logger.info("Stopped")
        time.sleep(1)
        
        # Demo 3: Turning
        logger.info("\n--- Demo 3: Turning ---")
        logger.info("Turning left...")
        motor.turn_left(speed=60)
        time.sleep(1.5)
        motor.stop()
        time.sleep(0.5)
        
        logger.info("Turning right...")
        motor.turn_right(speed=60)
        time.sleep(1.5)
        motor.stop()
        time.sleep(1)
        
        # Demo 4: Smooth acceleration
        logger.info("\n--- Demo 4: Smooth Acceleration ---")
        logger.info("Gradually accelerating from 0 to 80...")
        motor.move_forward(speed=0)
        motor.gradual_acceleration(target_speed=80, step=10, delay=0.2)
        logger.info("At full speed")
        time.sleep(1)
        
        # Demo 5: Smooth deceleration
        logger.info("\n--- Demo 5: Smooth Deceleration ---")
        logger.info("Gradually decelerating to stop...")
        motor.gradual_deceleration(step=10, delay=0.2)
        logger.info("Stopped smoothly")
        time.sleep(1)
        
        # Demo 6: Speed variations
        logger.info("\n--- Demo 6: Speed Variations ---")
        speeds = [30, 50, 70, 90]
        for speed in speeds:
            logger.info(f"Moving at {speed}% speed...")
            motor.move_forward(speed=speed)
            time.sleep(1)
        motor.stop()
        time.sleep(1)
        
        # Demo 7: Direction changes
        logger.info("\n--- Demo 7: Direction Changes ---")
        logger.info("Forward...")
        motor.move_forward(speed=60)
        time.sleep(1)
        
        logger.info("Backward...")
        motor.move_backward(speed=60)
        time.sleep(1)
        
        logger.info("Left turn...")
        motor.turn_left(speed=60)
        time.sleep(1)
        
        logger.info("Right turn...")
        motor.turn_right(speed=60)
        time.sleep(1)
        
        motor.stop()
        
        # Demo 8: Emergency stop
        logger.info("\n--- Demo 8: Emergency Stop ---")
        logger.info("Moving forward at high speed...")
        motor.move_forward(speed=90)
        time.sleep(1)
        logger.info("EMERGENCY STOP!")
        motor.emergency_stop()
        time.sleep(1)
        
        # Show final status
        logger.info("\n--- Final Status ---")
        status = motor.get_status()
        logger.info(f"Direction: {status['direction']}")
        logger.info(f"Speed: {status['speed']}%")
        logger.info(f"Emergency stopped: {status['emergency_stopped']}")
        
        logger.info("\n" + "=" * 60)
        logger.info("Motor demonstration complete!")
        logger.info("=" * 60)
        
    except KeyboardInterrupt:
        logger.info("\nDemo interrupted by user")
    
    except Exception as e:
        logger.error(f"Demo error: {e}", exc_info=True)
    
    finally:
        logger.info("Cleaning up...")
        motor.cleanup()


if __name__ == "__main__":
    main()
