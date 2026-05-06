#!/usr/bin/env python3
"""
Hardware Check Script
Tests each hardware component individually
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from hardware.gpio.gpio_manager import gpio_manager
from hardware.gpio.pwm_manager import pwm_manager
from hardware.motor.motor_controller import MotorController
from hardware.servo.servo_controller import ServoController
from hardware.led.led_controller import LEDController, LEDEffect
from hardware.ultrasonic.ultrasonic_controller import UltrasonicController
from hardware.camera.camera_controller import CameraController


def test_gpio():
    """Test GPIO initialization"""
    print("\n" + "="*50)
    print("Testing GPIO System")
    print("="*50)
    
    try:
        gpio_manager.initialize()
        print("✓ GPIO initialized successfully")
        return True
    except Exception as e:
        print(f"✗ GPIO initialization failed: {e}")
        return False


def test_motor():
    """Test motor controller"""
    print("\n" + "="*50)
    print("Testing Motor Controller")
    print("="*50)
    
    try:
        motor = MotorController()
        motor.initialize()
        print("✓ Motor initialized")
        
        print("Testing forward movement...")
        motor.move_forward(speed=50)
        time.sleep(2)
        motor.stop()
        print("✓ Forward movement OK")
        
        print("Testing backward movement...")
        motor.move_backward(speed=50)
        time.sleep(2)
        motor.stop()
        print("✓ Backward movement OK")
        
        motor.cleanup()
        print("✓ Motor test PASSED")
        return True
        
    except Exception as e:
        print(f"✗ Motor test FAILED: {e}")
        return False


def test_servo():
    """Test servo controller"""
    print("\n" + "="*50)
    print("Testing Servo Controller")
    print("="*50)
    
    try:
        servo = ServoController()
        servo.initialize()
        print("✓ Servo initialized")
        
        print("Testing center position...")
        servo.center()
        time.sleep(1)
        print("✓ Center position OK")
        
        print("Testing pan left...")
        servo.pan_left(30)
        time.sleep(1)
        print("✓ Pan left OK")
        
        print("Testing pan right...")
        servo.pan_right(60)
        time.sleep(1)
        print("✓ Pan right OK")
        
        servo.center()
        servo.cleanup()
        print("✓ Servo test PASSED")
        return True
        
    except Exception as e:
        print(f"✗ Servo test FAILED: {e}")
        return False


def test_led():
    """Test LED controller"""
    print("\n" + "="*50)
    print("Testing LED Controller")
    print("="*50)
    
    try:
        led = LEDController()
        led.initialize()
        print("✓ LED initialized")
        
        print("Testing red...")
        led.set_color(255, 0, 0)
        time.sleep(1)
        print("✓ Red OK")
        
        print("Testing green...")
        led.set_color(0, 255, 0)
        time.sleep(1)
        print("✓ Green OK")
        
        print("Testing blue...")
        led.set_color(0, 0, 255)
        time.sleep(1)
        print("✓ Blue OK")
        
        print("Testing blink effect...")
        led.start_effect(LEDEffect.BLINK)
        time.sleep(3)
        led.stop_effect()
        print("✓ Effect OK")
        
        led.cleanup()
        print("✓ LED test PASSED")
        return True
        
    except Exception as e:
        print(f"✗ LED test FAILED: {e}")
        return False


def test_ultrasonic():
    """Test ultrasonic sensor"""
    print("\n" + "="*50)
    print("Testing Ultrasonic Sensor")
    print("="*50)
    
    try:
        ultrasonic = UltrasonicController()
        ultrasonic.initialize()
        print("✓ Ultrasonic initialized")
        
        print("Taking distance measurements...")
        for i in range(5):
            distance = ultrasonic.get_filtered_distance()
            if distance:
                print(f"  Measurement {i+1}: {distance:.2f} cm")
            else:
                print(f"  Measurement {i+1}: Out of range")
            time.sleep(0.5)
        
        print("✓ Measurements OK")
        
        ultrasonic.cleanup()
        print("✓ Ultrasonic test PASSED")
        return True
        
    except Exception as e:
        print(f"✗ Ultrasonic test FAILED: {e}")
        return False


def test_camera():
    """Test camera"""
    print("\n" + "="*50)
    print("Testing Camera")
    print("="*50)
    
    try:
        camera = CameraController(device_id=0, resolution=(640, 480), fps=30)
        camera.initialize()
        print("✓ Camera initialized")
        
        camera.start_capture()
        print("✓ Capture started")
        
        time.sleep(2)
        
        frame = camera.get_latest_frame()
        if frame is not None:
            print(f"✓ Frame captured: {frame.shape}")
        else:
            print("✗ No frame captured")
        
        camera.cleanup()
        print("✓ Camera test PASSED")
        return True
        
    except Exception as e:
        print(f"✗ Camera test FAILED: {e}")
        return False


def main():
    """Main test function"""
    print("="*50)
    print("Hardware Component Test Suite")
    print("="*50)
    
    results = {}
    
    try:
        results['gpio'] = test_gpio()
        results['motor'] = test_motor()
        results['servo'] = test_servo()
        results['led'] = test_led()
        results['ultrasonic'] = test_ultrasonic()
        results['camera'] = test_camera()
        
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    
    finally:
        # Cleanup
        pwm_manager.cleanup()
        gpio_manager.cleanup_all()
    
    # Print summary
    print("\n" + "="*50)
    print("Test Summary")
    print("="*50)
    for component, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{component.capitalize()}: {status}")
    
    print("="*50)
    
    # Exit code
    all_passed = all(results.values())
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
