#!/usr/bin/env python3
"""
Import Diagnostics Script
Helps diagnose why hardware test imports are failing

Run this BEFORE running hardware tests to check your setup.

Usage:
    python3 diagnose_imports.py
"""

import sys
from pathlib import Path

def print_section(title):
    """Print section header"""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)

def check_directory_structure():
    """Check if directory structure is correct"""
    print_section("DIRECTORY STRUCTURE CHECK")
    
    script_dir = Path(__file__).resolve().parent
    raspi_dir = script_dir.parent
    drivers_dir = raspi_dir / "Drivers"
    
    print(f"📁 Script location: {script_dir}")
    print(f"📁 Raspi directory: {raspi_dir}")
    print(f"📁 Drivers directory: {drivers_dir}")
    
    # Check critical paths
    checks = [
        (raspi_dir, "Raspi directory"),
        (drivers_dir, "Drivers directory"),
        (drivers_dir / "hardware", "hardware package"),
        (drivers_dir / "hardware" / "__init__.py", "hardware __init__.py"),
        (drivers_dir / "hardware" / "managers", "managers package"),
        (drivers_dir / "hardware" / "managers" / "__init__.py", "managers __init__.py"),
        (drivers_dir / "hardware" / "managers" / "hardware_manager.py", "hardware_manager.py"),
    ]
    
    all_good = True
    for path, name in checks:
        if path.exists():
            print(f"✅ {name}: {path}")
        else:
            print(f"❌ {name}: NOT FOUND at {path}")
            all_good = False
    
    return all_good, drivers_dir

def check_python_path(drivers_dir):
    """Check Python path configuration"""
    print_section("PYTHON PATH CHECK")
    
    print(f"🐍 Python version: {sys.version}")
    print(f"\n📚 Current Python path (first 5 entries):")
    for i, path in enumerate(sys.path[:5], 1):
        print(f"   {i}. {path}")
    
    # Add drivers to path
    sys.path.insert(0, str(drivers_dir))
    print(f"\n✅ Added to Python path: {drivers_dir}")

def test_imports():
    """Test importing hardware components"""
    print_section("IMPORT TESTS")
    
    imports_to_test = [
        ("hardware.managers.hardware_manager", "hardware_manager"),
        ("hardware.gpio.gpio_manager", "gpio_manager"),
        ("hardware.motor.motor_controller", "MotorController"),
        ("hardware.servo.servo_controller", "ServoController"),
        ("hardware.led.led_controller", "LEDController"),
        ("hardware.ultrasonic.ultrasonic_controller", "UltrasonicController"),
        ("hardware.camera.camera_controller", "CameraController"),
        ("hardware.safety.emergency_stop", "EmergencyStop"),
    ]
    
    success_count = 0
    fail_count = 0
    
    for module_path, item_name in imports_to_test:
        try:
            module = __import__(module_path, fromlist=[item_name])
            item = getattr(module, item_name)
            print(f"✅ {module_path}.{item_name}")
            success_count += 1
        except ImportError as e:
            print(f"❌ {module_path}.{item_name}")
            print(f"   Error: {e}")
            fail_count += 1
        except AttributeError as e:
            print(f"⚠️  {module_path}.{item_name} (module imported but item not found)")
            print(f"   Error: {e}")
            fail_count += 1
    
    print(f"\n📊 Import Results: {success_count} passed, {fail_count} failed")
    return fail_count == 0

def check_dependencies():
    """Check if required Python packages are installed"""
    print_section("DEPENDENCY CHECK")
    
    required_packages = [
        ("RPi.GPIO", "RPi.GPIO"),
        ("cv2", "opencv-python"),
        ("numpy", "numpy"),
    ]
    
    all_installed = True
    for import_name, package_name in required_packages:
        try:
            __import__(import_name)
            print(f"✅ {package_name}")
        except ImportError:
            print(f"❌ {package_name} - Install with: pip3 install {package_name}")
            all_installed = False
    
    return all_installed

def check_raspberry_pi():
    """Check if running on Raspberry Pi"""
    print_section("RASPBERRY PI CHECK")
    
    try:
        with open('/proc/cpuinfo', 'r') as f:
            cpuinfo = f.read()
            if 'Raspberry Pi' in cpuinfo:
                print("✅ Running on Raspberry Pi")
                # Extract model info
                for line in cpuinfo.split('\n'):
                    if 'Model' in line:
                        print(f"   {line.strip()}")
                return True
            else:
                print("❌ Not running on Raspberry Pi")
                print("   Hardware tests require actual Raspberry Pi hardware")
                return False
    except FileNotFoundError:
        print("⚠️  Cannot determine if running on Raspberry Pi")
        print("   /proc/cpuinfo not found")
        return False

def check_gpio_permissions():
    """Check GPIO permissions"""
    print_section("GPIO PERMISSIONS CHECK")
    
    import os
    import grp
    
    try:
        # Check if user is in gpio group
        gpio_gid = grp.getgrnam('gpio').gr_gid
        user_groups = os.getgroups()
        
        if gpio_gid in user_groups:
            print("✅ User is in 'gpio' group")
            return True
        else:
            print("❌ User is NOT in 'gpio' group")
            print("   Fix with: sudo usermod -a -G gpio $USER")
            print("   Then reboot or log out and back in")
            return False
    except KeyError:
        print("⚠️  'gpio' group not found")
        print("   This is normal on non-Raspberry Pi systems")
        return False
    except Exception as e:
        print(f"⚠️  Could not check GPIO permissions: {e}")
        return False

def main():
    """Run all diagnostic checks"""
    print("\n" + "="*60)
    print("  🔍 HARDWARE TEST IMPORT DIAGNOSTICS")
    print("="*60)
    print("\nThis script checks if your environment is set up correctly")
    print("for running hardware tests.\n")
    
    results = {}
    
    # Check directory structure
    results['structure'], drivers_dir = check_directory_structure()
    
    # Check Python path
    check_python_path(drivers_dir)
    
    # Test imports
    results['imports'] = test_imports()
    
    # Check dependencies
    results['dependencies'] = check_dependencies()
    
    # Check Raspberry Pi
    results['raspberry_pi'] = check_raspberry_pi()
    
    # Check GPIO permissions
    results['gpio_permissions'] = check_gpio_permissions()
    
    # Final summary
    print_section("SUMMARY")
    
    all_passed = all(results.values())
    
    print("\n📋 Diagnostic Results:")
    print(f"   {'✅' if results['structure'] else '❌'} Directory structure")
    print(f"   {'✅' if results['imports'] else '❌'} Python imports")
    print(f"   {'✅' if results['dependencies'] else '❌'} Dependencies installed")
    print(f"   {'✅' if results['raspberry_pi'] else '❌'} Running on Raspberry Pi")
    print(f"   {'✅' if results['gpio_permissions'] else '❌'} GPIO permissions")
    
    if all_passed:
        print("\n🎉 All checks passed! You're ready to run hardware tests.")
        print("\n💡 Run the test with:")
        print("   python3 test_hardware_working.py")
    else:
        print("\n⚠️  Some checks failed. Please fix the issues above before running tests.")
        print("\n💡 Common fixes:")
        print("   1. Make sure you're in the correct directory")
        print("   2. Install missing dependencies: pip3 install -r requirements.txt")
        print("   3. Add user to gpio group: sudo usermod -a -G gpio $USER")
        print("   4. Reboot after adding to gpio group")
        print("   5. Make sure you're running on actual Raspberry Pi hardware")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
