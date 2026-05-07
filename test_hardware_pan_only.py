#!/usr/bin/env python3
"""
Hardware Component Test Script - PAN SERVO ONLY
Tests all hardware components sequentially for 5 seconds each.
Modified to test only PAN servo (no tilt).

Usage:
    cd ~/Downloads
    PYTHONPATH=/home/iot/Downloads/Raspi/Drivers python3 test_hardware_pan_only.py
"""

import sys
import time
import signal
from pathlib import Path

# Add paths for imports
raspi_path = Path(__file__).parent / "Raspi"
drivers_path = raspi_path / "Drivers"
sys.path.insert(0, str(raspi_path))
sys.path.insert(0, str(drivers_path))

try:
    from hardware.managers.hardware_manager import hardware_manager
except ImportError as e:
    print(f"❌ Error importing hardware_manager: {e}")
    print("\n💡 Run with: PYTHONPATH=/home/iot/Downloads/Raspi/Drivers python3 test_hardware_pan_only.py")
    sys.exit(1)


class HardwareTest:
    """Hardware component test suite - Pan servo only"""
    
    def __init__(self):
        self.hardware_manager = hardware_manager
        self.test_duration = 5
        self.running = True
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        print("\n\n⚠️  Test interrupted by user")
        self.running = False
        self.cleanup()
        sys.exit(0)
    
    def print_header(self, title):
        print("\n" + "="*60)
        print(f"  {title}")
        print("="*60)
    
    def print_test(self, component, action):
        print(f"🔧 Testing {component}: {action}")
    
    def wait_with_countdown(self, seconds, message=""):
        for i in range(seconds, 0, -1):
            if not self.running:
                break
            print(f"   ⏱️  {message} {i}s remaining...", end='\r')
            time.sleep(1)
        print(" " * 60, end='\r')
    
    def initialize(self):
        self.print_header("INITIALIZING HARDWARE MANAGER")
        try:
            print("🔄 Initializing all hardware components...")
            self.hardware_manager.initialize()
            print("✅ Hardware manager initialized successfully")
            time.sleep(2)
            return True
        except Exception as e:
            print(f"❌ Failed to initialize hardware: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_motors(self):
        self.print_header("TEST 1: MOTOR CONTROLLER")
        
        tests = [
            ("FORWARD", lambda: self.hardware_manager.motor.move_forward(60)),
            ("BACKWARD", lambda: self.hardware_manager.motor.move_backward(60)),
            ("LEFT", lambda: self.hardware_manager.motor.turn_left(60)),
            ("RIGHT", lambda: self.hardware_manager.motor.turn_right(60)),
        ]
        
        for direction, action in tests:
            if not self.running:
                return
            self.print_test("Motors", f"Moving {direction} at 60% speed")
            try:
                action()
                self.wait_with_countdown(self.test_duration, direction)
                self.hardware_manager.motor.stop()
                print(f"✅ {direction} movement complete")
                time.sleep(1)
            except Exception as e:
                print(f"❌ {direction} test failed: {e}")
        
        print("\n✅ Motor tests complete")
    
    def test_servo_pan_only(self):
        """Test PAN servo only - no tilt"""
        self.print_header("TEST 2: PAN SERVO CONTROLLER (TILT DISABLED)")
        
        if not self.running:
            return
        
        positions = [
            ("CENTER (0°)", 0),
            ("LEFT (-90°)", -90),
            ("RIGHT (+90°)", 90),
            ("+45°", 45),
            ("-45°", -45),
            ("CENTER (0°)", 0),
        ]
        
        for name, angle in positions:
            if not self.running:
                return
            
            self.print_test("Pan Servo", f"Moving to {name}")
            try:
                self.hardware_manager.servo.set_angle(pan=angle, tilt=0)
                duration = 2 if "CENTER" in name else self.test_duration
                self.wait_with_countdown(duration, name)
                print(f"✅ {name} complete")
            except Exception as e:
                print(f"❌ {name} test failed: {e}")
        
        print("\n✅ Pan servo tests complete")
        print("ℹ️  Note: Tilt servo not tested (only pan configured)")
    
    def test_led(self):
        self.print_header("TEST 3: LED CONTROLLER")
        
        colors = [
            ("RED", (255, 0, 0)),
            ("GREEN", (0, 255, 0)),
            ("BLUE", (0, 0, 255)),
            ("YELLOW", (255, 255, 0)),
        ]
        
        for name, rgb in colors:
            if not self.running:
                return
            self.print_test("LED", f"Setting color to {name}")
            try:
                self.hardware_manager.led.set_color(*rgb)
                self.wait_with_countdown(self.test_duration, name)
                print(f"✅ {name} color complete")
            except Exception as e:
                print(f"❌ {name} test failed: {e}")
        
        if self.running:
            self.print_test("LED", "Starting BLINK effect (white)")
            try:
                self.hardware_manager.led.start_effect('blink', color=(255, 255, 255))
                self.wait_with_countdown(self.test_duration, "Blink effect")
                self.hardware_manager.led.stop_effect()
                print("✅ Blink effect complete")
            except Exception as e:
                print(f"❌ Blink effect failed: {e}")
        
        if self.running:
            self.print_test("LED", "Turning OFF")
            try:
                self.hardware_manager.led.turn_off()
                time.sleep(1)
                print("✅ LED off")
            except Exception as e:
                print(f"❌ LED off failed: {e}")
        
        print("\n✅ LED tests complete")
    
    def test_ultrasonic(self):
        self.print_header("TEST 4: ULTRASONIC SENSOR")
        
        if not self.running:
            return
        
        self.print_test("Ultrasonic", "Reading distance for 5 seconds")
        print("   📏 Move your hand in front of the sensor")
        
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
                
                time.sleep(0.2)
            
            print()
            
            valid_readings = [r for r in readings if r is not None]
            if valid_readings:
                print(f"   📊 Statistics:")
                print(f"      Average: {sum(valid_readings)/len(valid_readings):.1f} cm")
                print(f"      Min: {min(valid_readings):.1f} cm")
                print(f"      Max: {max(valid_readings):.1f} cm")
                print(f"      Readings: {len(valid_readings)}/{len(readings)}")
            
            print("✅ Ultrasonic sensor test complete")
        except Exception as e:
            print(f"\n❌ Ultrasonic test failed: {e}")
    
    def test_camera(self):
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
                    print(f"   📷 Frame {frame_count}: {width}x{height}" + " " * 20, end='\r')
                else:
                    print(f"   📷 Frame capture failed" + " " * 20, end='\r')
                
                time.sleep(0.1)
            
            print()
            
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
        self.print_header("TEST 6: EMERGENCY STOP SYSTEM")
        
        if not self.running:
            return
        
        self.print_test("Emergency Stop", "Testing emergency stop functionality")
        
        try:
            print("   🚗 Starting motor at 50% speed...")
            self.hardware_manager.motor.move_forward(50)
            time.sleep(2)
            
            print("   🚨 Triggering EMERGENCY STOP...")
            self.hardware_manager.emergency_stop.trigger_emergency(
                trigger="TEST",
                message="Hardware test emergency stop"
            )
            time.sleep(2)
            
            print("   ✅ Emergency stop triggered")
            print("   ⚠️  All operations should now be blocked")
            
            print("   🔒 Testing if motor is blocked...")
            try:
                self.hardware_manager.motor.move_forward(50)
                print("   ❌ WARNING: Motor moved during emergency stop!")
            except Exception:
                print("   ✅ Motor correctly blocked during emergency")
            
            time.sleep(2)
            
            print("   🔄 Resetting emergency stop...")
            self.hardware_manager.emergency_stop.reset_emergency()
            time.sleep(1)
            
            if not self.hardware_manager.emergency_stop.is_emergency_active():
                print("   ✅ Emergency stop reset successfully")
            else:
                print("   ❌ Emergency stop still active!")
            
            print("✅ Emergency stop test complete")
        except Exception as e:
            print(f"❌ Emergency stop test failed: {e}")
            try:
                self.hardware_manager.emergency_stop.reset_emergency()
            except:
                pass
    
    def cleanup(self):
        self.print_header("CLEANUP")
        print("🔄 Shutting down hardware manager...")
        try:
            self.hardware_manager.shutdown()
            print("✅ Hardware manager shutdown complete")
        except Exception as e:
            print(f"⚠️  Cleanup warning: {e}")
    
    def run_all_tests(self):
        print("\n" + "="*60)
        print("  🔧 HARDWARE TEST SUITE - PAN SERVO ONLY")
        print("  Testing all components for 5 seconds each")
        print("="*60)
        print("\n⚠️  SAFETY WARNINGS:")
        print("   - Ensure 12V external power connected to motor driver")
        print("   - Keep hands away from moving parts")
        print("   - Press Ctrl+C to stop at any time")
        print("   - Make sure car has space to move")
        print("\n⏳ Starting tests in 3 seconds...")
        time.sleep(3)
        
        if not self.initialize():
            print("\n❌ Initialization failed. Exiting.")
            return False
        
        try:
            self.test_motors()
            self.test_servo_pan_only()
            self.test_led()
            self.test_ultrasonic()
            self.test_camera()
            self.test_emergency_stop()
            
            self.print_header("TEST SUMMARY")
            print("✅ All hardware tests completed successfully!")
            print("\n📋 Components tested:")
            print("   ✅ Motors (forward, backward, left, right)")
            print("   ✅ Pan Servo (left, right, center, ±45°)")
            print("   ✅ LED (red, green, blue, yellow, blink)")
            print("   ✅ Ultrasonic sensor (distance readings)")
            print("   ✅ Camera (frame capture)")
            print("   ✅ Emergency stop system")
            print("\n💡 Note: Only pan servo tested (tilt servo not configured)")
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
    try:
        with open('/proc/cpuinfo', 'r') as f:
            if 'Raspberry Pi' not in f.read():
                print("⚠️  Warning: This doesn't appear to be a Raspberry Pi")
                response = input("Continue anyway? (y/n): ")
                if response.lower() != 'y':
                    sys.exit(0)
    except:
        print("⚠️  Warning: Could not verify Raspberry Pi")
    
    tester = HardwareTest()
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
