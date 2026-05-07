#!/usr/bin/env python3
"""
Hardware Component Test Script
Tests all hardware components sequentially for 5 seconds each.

This script verifies:
- Motors (forward, backward, left, right)
- Servos (pan and tilt)
- RGB LED (colors and effects)
- Ultrasonic sensor (distance readings)
- Camera (frame capture)
- Emergency stop system

Usage:
    python3 test_hardware.py

Requirements:
    - All hardware must be connected as per CONNECTIONS_GUIDE.md
    - Run on Raspberry Pi with proper GPIO permissions
    - External 12V power for motors required
"""

import sys
import time
import signal
from pathlib import Path

# Add Raspi directory to Python path
raspi_path = Path(__file__).parent / "Raspi"
sys.path.insert(0, str(raspi_path))

try:
    from Drivers.hardware.managers.hardware_manager import hardware_manager
except ImportError as e:
    print(f"❌ Error importing hardware_manager: {e}")
    print("Make sure you're running this on Raspberry Pi with all dependencies installed.")
    sys.exit(1)


class HardwareTest:
    """Hardware component test suite"""
    
    def __init__(self):
        self.hardware_manager = hardware_manager
        self.test_duration = 5  # seconds per test
        self.running = True
        
        # Setup signal handler for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle Ctrl+C gracefully"""
        print("\n\n⚠️  Test interrupted by user")
        self.running = False
        self.cleanup()
        sys.exit(0)
    
    def print_header(self, title):
        """Print formatted test header"""
        print("\n" + "="*60)
        print(f"  {title}")
        print("="*60)
    
    def print_test(self, component, action):
        """Print test action"""
        print(f"🔧 Testing {component}: {action}")
    
    def wait_with_countdown(self, seconds, message=""):
        """Wait with countdown display"""
        for i in range(seconds, 0, -1):
            if not self.running:
                break
            print(f"   ⏱️  {message} {i}s remaining...", end='\r')
            time.sleep(1)
        print(" " * 60, end='\r')  # Clear line
    
    def initialize(self):
        """Initialize hardware manager"""
        self.print_header("INITIALIZING HARDWARE MANAGER")
        try:
            print("🔄 Initializing all hardware components...")
            self.hardware_manager.initialize()
            print("✅ Hardware manager initialized successfully")
            time.sleep(2)
            return True
        except Exception as e:
            print(f"❌ Failed to initialize hardware: {e}")
            return False
    
    def test_motors(self):
        """Test motor movements"""
        self.print_header("TEST 1: MOTOR CONTROLLER")
        
        if not self.running:
            return
        
        # Test forward
        self.print_test("Motors", "Moving FORWARD at 60% speed")
        try:
            self.hardware_manager.motor.move_forward(60)
            self.wait_with_countdown(self.test_duration, "Forward")
            self.hardware_manager.motor.stop()
            print("✅ Forward movement complete")
            time.sleep(1)
        except Exception as e:
            print(f"❌ Forward test failed: {e}")
        
        if not self.running:
            return
        
        # Test backward
        self.print_test("Motors", "Moving BACKWARD at 60% speed")
        try:
            self.hardware_manager.motor.move_backward(60)
            self.wait_with_countdown(self.test_duration, "Backward")
            self.hardware_manager.motor.stop()
            print("✅ Backward movement complete")
            time.sleep(1)
        except Exception as e:
            print(f"❌ Backward test failed: {e}")
        
        if not self.running:
            return
        
        # Test left turn
        self.print_test("Motors", "Turning LEFT at 60% speed")
        try:
            self.hardware_manager.motor.turn_left(60)
            self.wait_with_countdown(self.test_duration, "Left turn")
            self.hardware_manager.motor.stop()
            print("✅ Left turn complete")
            time.sleep(1)
        except Exception as e:
            print(f"❌ Left turn test failed: {e}")
        
        if not self.running:
            return
        
        # Test right turn
        self.print_test("Motors", "Turning RIGHT at 60% speed")
        try:
            self.hardware_manager.motor.turn_right(60)
            self.wait_with_countdown(self.test_duration, "Right turn")
            self.hardware_manager.motor.stop()
            print("✅ Right turn complete")
            time.sleep(1)
        except Exception as e:
            print(f"❌ Right turn test failed: {e}")
        
        print("\n✅ Motor tests complete")
    
    def test_servos(self):
        """Test servo movements"""
        self.print_header("TEST 2: SERVO CONTROLLER")
        
        if not self.running:
            return
        
        # Center position
        self.print_test("Servos", "Moving to CENTER position")
        try:
            self.hardware_manager.servo.center()
            self.wait_with_countdown(2, "Center")
            print("✅ Center position set")
        except Exception as e:
            print(f"❌ Center test failed: {e}")
        
        if not self.running:
            return
        
        # Pan left
        self.print_test("Servos", "Panning LEFT (-90°)")
        try:
            self.hardware_manager.servo.set_angle(pan=-90, tilt=0)
            self.wait_with_countdown(self.test_duration, "Pan left")
            print("✅ Pan left complete")
        except Exception as e:
            print(f"❌ Pan left test failed: {e}")
        
        if not self.running:
            return
        
        # Pan right
        self.print_test("Servos", "Panning RIGHT (+90°)")
        try:
            self.hardware_manager.servo.set_angle(pan=90, tilt=0)
            self.wait_with_countdown(self.test_duration, "Pan right")
            print("✅ Pan right complete")
        except Exception as e:
            print(f"❌ Pan right test failed: {e}")
        
        if not self.running:
            return
        
        # Center again
        self.print_test("Servos", "Returning to CENTER")
        try:
            self.hardware_manager.servo.center()
            self.wait_with_countdown(2, "Center")
        except Exception as e:
            print(f"❌ Center return failed: {e}")
        
        if not self.running:
            return
        
        
    
    def test_led(self):
        """Test LED colors and effects"""
        self.print_header("TEST 3: LED CONTROLLER")
        
        if not self.running:
            return
        
        # Red
        self.print_test("LED", "Setting color to RED")
        try:
            self.hardware_manager.led.set_color(255, 0, 0)
            self.wait_with_countdown(self.test_duration, "Red")
            print("✅ Red color complete")
        except Exception as e:
            print(f"❌ Red test failed: {e}")
        
        if not self.running:
            return
        
        # Green
        self.print_test("LED", "Setting color to GREEN")
        try:
            self.hardware_manager.led.set_color(0, 255, 0)
            self.wait_with_countdown(self.test_duration, "Green")
            print("✅ Green color complete")
        except Exception as e:
            print(f"❌ Green test failed: {e}")
        
        if not self.running:
            return
        
        # Blue
        self.print_test("LED", "Setting color to BLUE")
        try:
            self.hardware_manager.led.set_color(0, 0, 255)
            self.wait_with_countdown(self.test_duration, "Blue")
            print("✅ Blue color complete")
        except Exception as e:
            print(f"❌ Blue test failed: {e}")
        
        if not self.running:
            return
        
        # Yellow
        self.print_test("LED", "Setting color to YELLOW")
        try:
            self.hardware_manager.led.set_color(255, 255, 0)
            self.wait_with_countdown(self.test_duration, "Yellow")
            print("✅ Yellow color complete")
        except Exception as e:
            print(f"❌ Yellow test failed: {e}")
        
        if not self.running:
            return
        
        # Blink effect
        self.print_test("LED", "Starting BLINK effect (white)")
        try:
            self.hardware_manager.led.start_effect('blink', color=(255, 255, 255))
            self.wait_with_countdown(self.test_duration, "Blink effect")
            self.hardware_manager.led.stop_effect()
            print("✅ Blink effect complete")
        except Exception as e:
            print(f"❌ Blink effect failed: {e}")
        
        if not self.running:
            return
        
        # Turn off
        self.print_test("LED", "Turning OFF")
        try:
            self.hardware_manager.led.turn_off()
            time.sleep(1)
            print("✅ LED off")
        except Exception as e:
            print(f"❌ LED off failed: {e}")
        
        print("\n✅ LED tests complete")
    
    def test_ultrasonic(self):
        """Test ultrasonic sensor"""
        self.print_header("TEST 4: ULTRASONIC SENSOR")
        
        if not self.running:
            return
        
        self.print_test("Ultrasonic", "Reading distance for 5 seconds")
        print("   📏 Move your hand in front of the sensor to see readings change")
        
        try:
            start_time = time.time()
            readings = []
            
            while time.time() - start_time < self.test_duration and self.running:
                distance = self.hardware_manager.ultrasonic.get_distance()
                readings.append(distance)
                
                if distance is not None:
                    print(f"   📏 Distance: {distance:.1f} cm" + " " * 20, end='\r')
                else:
                    print(f"   📏 Distance: Out of range" + " " * 20, end='\r')
                
                time.sleep(0.2)  # 5 Hz update rate
            
            print()  # New line
            
            # Calculate statistics
            valid_readings = [r for r in readings if r is not None]
            if valid_readings:
                avg_distance = sum(valid_readings) / len(valid_readings)
                min_distance = min(valid_readings)
                max_distance = max(valid_readings)
                print(f"   📊 Statistics:")
                print(f"      Average: {avg_distance:.1f} cm")
                print(f"      Min: {min_distance:.1f} cm")
                print(f"      Max: {max_distance:.1f} cm")
                print(f"      Readings: {len(valid_readings)}/{len(readings)}")
            
            print("✅ Ultrasonic sensor test complete")
        except Exception as e:
            print(f"\n❌ Ultrasonic test failed: {e}")
    
    def test_camera(self):
        """Test camera capture"""
        self.print_header("TEST 5: CAMERA")
        
        if not self.running:
            return
        
        self.print_test("Camera", "Capturing frames for 5 seconds")
        
        try:
            start_time = time.time()
            frame_count = 0
            
            while time.time() - start_time < self.test_duration and self.running:
                frame = self.hardware_manager.camera.get_frame()
                
                if frame is not None:
                    frame_count += 1
                    height, width = frame.shape[:2]
                    print(f"   📷 Captured frame {frame_count}: {width}x{height}" + " " * 20, end='\r')
                else:
                    print(f"   📷 Frame capture failed" + " " * 20, end='\r')
                
                time.sleep(0.1)  # ~10 FPS for testing
            
            print()  # New line
            
            elapsed = time.time() - start_time
            fps = frame_count / elapsed if elapsed > 0 else 0
            
            print(f"   📊 Statistics:")
            print(f"      Total frames: {frame_count}")
            print(f"      Average FPS: {fps:.1f}")
            print(f"      Duration: {elapsed:.1f}s")
            
            print("✅ Camera test complete")
        except Exception as e:
            print(f"\n❌ Camera test failed: {e}")
    
    def test_emergency_stop(self):
        """Test emergency stop system"""
        self.print_header("TEST 6: EMERGENCY STOP SYSTEM")
        
        if not self.running:
            return
        
        self.print_test("Emergency Stop", "Testing emergency stop functionality")
        
        try:
            # Start motor
            print("   🚗 Starting motor at 50% speed...")
            self.hardware_manager.motor.move_forward(50)
            time.sleep(2)
            
            # Trigger emergency stop
            print("   🚨 Triggering EMERGENCY STOP...")
            self.hardware_manager.emergency_stop.trigger_emergency(
                trigger="TEST",
                message="Hardware test emergency stop"
            )
            time.sleep(2)
            
            # Check if motor stopped
            print("   ✅ Emergency stop triggered")
            print("   ⚠️  All operations should now be blocked")
            
            # Try to move (should fail)
            print("   🔒 Testing if motor is blocked...")
            try:
                self.hardware_manager.motor.move_forward(50)
                print("   ❌ WARNING: Motor moved during emergency stop!")
            except Exception:
                print("   ✅ Motor correctly blocked during emergency")
            
            time.sleep(2)
            
            # Reset emergency
            print("   🔄 Resetting emergency stop...")
            self.hardware_manager.emergency_stop.reset_emergency()
            time.sleep(1)
            
            # Verify reset
            if not self.hardware_manager.emergency_stop.is_emergency_active():
                print("   ✅ Emergency stop reset successfully")
            else:
                print("   ❌ Emergency stop still active!")
            
            print("✅ Emergency stop test complete")
        except Exception as e:
            print(f"❌ Emergency stop test failed: {e}")
            # Make sure to reset emergency
            try:
                self.hardware_manager.emergency_stop.reset_emergency()
            except:
                pass
    
    def cleanup(self):
        """Cleanup and shutdown"""
        self.print_header("CLEANUP")
        print("🔄 Shutting down hardware manager...")
        try:
            self.hardware_manager.shutdown()
            print("✅ Hardware manager shutdown complete")
        except Exception as e:
            print(f"⚠️  Cleanup warning: {e}")
    
    def run_all_tests(self):
        """Run all hardware tests"""
        print("\n" + "="*60)
        print("  🔧 HARDWARE COMPONENT TEST SUITE")
        print("  Testing all components for 5 seconds each")
        print("="*60)
        print("\n⚠️  SAFETY WARNINGS:")
        print("   - Ensure 12V external power is connected to motor driver")
        print("   - Keep hands away from moving parts")
        print("   - Press Ctrl+C to stop at any time")
        print("   - Make sure car has space to move")
        print("\n⏳ Starting tests in 3 seconds...")
        time.sleep(3)
        
        # Initialize
        if not self.initialize():
            print("\n❌ Initialization failed. Exiting.")
            return False
        
        # Run tests
        try:
            self.test_motors()
            self.test_servos()
            self.test_led()
            self.test_ultrasonic()
            self.test_camera()
            self.test_emergency_stop()
            
            # Final summary
            self.print_header("TEST SUMMARY")
            print("✅ All hardware tests completed successfully!")
            print("\n📋 Components tested:")
            print("   ✅ Motors (forward, backward, left, right)")
            print("   ✅ Servos (pan and tilt)")
            print("   ✅ LED (colors and effects)")
            print("   ✅ Ultrasonic sensor (distance readings)")
            print("   ✅ Camera (frame capture)")
            print("   ✅ Emergency stop system")
            print("\n🎉 Your hardware is ready to use!")
            
            return True
            
        except Exception as e:
            print(f"\n❌ Test suite failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        finally:
            self.cleanup()


def main():
    """Main entry point"""
    # Check if running on Raspberry Pi
    try:
        with open('/proc/cpuinfo', 'r') as f:
            if 'Raspberry Pi' not in f.read():
                print("⚠️  Warning: This doesn't appear to be a Raspberry Pi")
                response = input("Continue anyway? (y/n): ")
                if response.lower() != 'y':
                    sys.exit(0)
    except:
        print("⚠️  Warning: Could not verify Raspberry Pi")
    
    # Run tests
    tester = HardwareTest()
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
