# Getting Started with Hardware Control System

Quick guide to get your hardware control system up and running.

## 📋 Prerequisites

### Hardware Requirements
- Raspberry Pi 3 or 4
- L298N Motor Driver
- 2x DC Motors
- 2x Servo Motors (pan/tilt)
- RGB LED (common cathode)
- HC-SR04 Ultrasonic Sensor
- Camera Module (CSI or USB)
- External power supply (12V for motors)
- Jumper wires
- Breadboard (optional)

### Software Requirements
- Raspberry Pi OS (Raspbian)
- Python 3.7 or higher
- Internet connection (for installation)

---

## 🚀 Installation

### Step 1: Update System

```bash
sudo apt-get update
sudo apt-get upgrade -y
```

### Step 2: Install System Dependencies

```bash
# Install Python development tools
sudo apt-get install -y python3-dev python3-pip

# Install GPIO library
sudo apt-get install -y python3-rpi.gpio

# Install OpenCV dependencies
sudo apt-get install -y python3-opencv

# Install camera support
sudo apt-get install -y python3-picamera
```

### Step 3: Clone/Copy Project

```bash
# Navigate to your projects directory
cd ~

# Copy the project_root folder to your Raspberry Pi
# (Use scp, rsync, or USB drive)
```

### Step 4: Install Python Dependencies

```bash
cd project_root

# Install requirements
pip3 install -r requirements.txt
```

### Step 5: Configure Permissions

```bash
# Add user to GPIO group
sudo usermod -a -G gpio $USER

# Add user to video group (for camera)
sudo usermod -a -G video $USER

# Reboot to apply changes
sudo reboot
```

---

## 🔌 Hardware Setup

### Step 1: Review Wiring Guide

Read `docs/gpio_layout.md` for complete wiring instructions.

### Step 2: Connect Components

**⚠️ IMPORTANT**: Disconnect power before wiring!

1. **Connect L298N Motor Driver**
   - Left motor: EN1→GPIO12, IN1→GPIO23, IN2→GPIO24
   - Right motor: EN2→GPIO13, IN3→GPIO27, IN4→GPIO22
   - Connect motors to motor driver outputs
   - Connect external 12V power to motor driver
   - **Connect common ground** between Pi and motor driver

2. **Connect Servos**
   - Pan servo signal → GPIO17
   - Tilt servo signal → GPIO18
   - Connect servo power (5V) and ground
   - Use external power if servos draw > 500mA

3. **Connect RGB LED**
   - Red → GPIO16
   - Green → GPIO20
   - Blue → GPIO21
   - Use 220Ω resistors for each color
   - Connect common cathode to ground

4. **Connect Ultrasonic Sensor**
   - Trigger → GPIO5
   - Echo → GPIO6
   - VCC → 5V
   - GND → Ground

5. **Connect Camera**
   - CSI camera: Connect to CSI port
   - USB camera: Connect to USB port

### Step 3: Verify Connections

```bash
# Check GPIO pins
gpio readall

# Check camera
vcgencmd get_camera
```

---

## ✅ Verification

### Step 1: Run Hardware Check

```bash
cd project_root
python3 scripts/hardware_check.py
```

This will test:
- GPIO initialization
- Motor control
- Servo movement
- LED colors
- Ultrasonic sensor
- Camera capture

### Step 2: Run Individual Demos

```bash
# Test motors
python3 scripts/motor_demo.py

# Test servos
python3 scripts/servo_demo.py

# Test LEDs
python3 scripts/led_demo.py
```

---

## 🎮 Basic Usage

### Example 1: Simple Motor Control

```python
from hardware.motor.motor_controller import MotorController

# Initialize
motor = MotorController()
motor.initialize()

# Move forward
motor.move_forward(speed=70)

# Wait 2 seconds
import time
time.sleep(2)

# Stop
motor.stop()

# Cleanup
motor.cleanup()
```

### Example 2: Servo Control

```python
from hardware.servo.servo_controller import ServoController

# Initialize
servo = ServoController()
servo.initialize()

# Look left
servo.set_angle(pan=90, tilt=0)

# Center
servo.center()

# Cleanup
servo.cleanup()
```

### Example 3: LED Control

```python
from hardware.led.led_controller import LEDController

# Initialize
led = LEDController()
led.initialize()

# Set red color
led.set_color(255, 0, 0)

# Set status
led.set_status_color('moving')

# Cleanup
led.cleanup()
```

### Example 4: Complete System

```python
from hardware.managers.hardware_manager import hardware_manager

# Initialize all hardware
hardware_manager.initialize()

# Control motor
hardware_manager.motor.move_forward(speed=70)

# Control servo
hardware_manager.servo.set_angle(pan=45, tilt=20)

# Control LED
hardware_manager.led.set_status_color('moving')

# Get distance
distance = hardware_manager.ultrasonic.get_distance()
print(f"Distance: {distance}cm")

# Capture frame
frame = hardware_manager.camera.get_latest_frame()

# Cleanup
hardware_manager.cleanup()
```

---

## 🎯 Running the Main Application

### Start the System

```bash
python3 main.py
```

This will:
1. Initialize all hardware components
2. Start safety systems (watchdog, emergency stop)
3. Begin monitoring sensors
4. Start camera capture
5. Run main loop with heartbeat monitoring

### Stop the System

Press `Ctrl+C` for graceful shutdown.

---

## 🧪 Running Tests

### Run All Tests

```bash
pytest
```

### Run Specific Tests

```bash
# Motor tests
pytest tests/motor_tests/

# Integration tests
pytest tests/integration_tests/

# With verbose output
pytest -v

# With coverage
pytest --cov=hardware --cov-report=html
```

---

## ⚙️ Configuration

### Customize GPIO Pins

Edit `configs/gpio_config.yaml`:

```yaml
motor:
  left_motor:
    enable: 12
    input1: 23
    input2: 24
```

### Customize PWM Frequencies

Edit `configs/pwm_config.yaml`:

```yaml
motor:
  frequency: 1000  # Hz
```

### Customize Servo Limits

Edit `configs/servo_config.yaml`:

```yaml
pan:
  min_angle: -90
  max_angle: 90
```

### Customize Safety Settings

Edit `configs/safety_config.yaml`:

```yaml
obstacle_detection:
  threshold: 20  # cm
```

---

## 🔧 Troubleshooting

### Issue: Permission Denied

```bash
# Solution
sudo usermod -a -G gpio $USER
sudo reboot
```

### Issue: Camera Not Found

```bash
# Enable camera
sudo raspi-config
# Interface Options → Camera → Enable

# Reboot
sudo reboot
```

### Issue: Motors Not Working

**Check:**
1. External power connected?
2. Common ground connected?
3. GPIO pins correct?
4. Motor driver enabled?

```bash
# Test GPIO
python3 scripts/hardware_check.py
```

### Issue: Import Errors

```bash
# Add to path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Or reinstall
pip3 install -r requirements.txt
```

### Issue: GPIO Already in Use

```bash
# Cleanup GPIO
python3 scripts/gpio_cleanup.py
```

---

## 📚 Next Steps

### Learn More
1. Read `README.md` for overview
2. Read `docs/hardware_architecture.md` for architecture
3. Read `docs/TESTING.md` for testing guide
4. Read `docs/gpio_layout.md` for wiring details

### Customize
1. Modify configuration files
2. Add new hardware components
3. Create custom control scripts
4. Integrate with backend systems

### Develop
1. Write tests for new features
2. Add new hardware modules
3. Create custom effects
4. Build GUI or API layer

---

## 🆘 Getting Help

### Documentation
- `README.md` - Project overview
- `docs/` - Detailed documentation
- `scripts/` - Example scripts

### Testing
- `scripts/hardware_check.py` - Validate hardware
- `pytest` - Run test suite

### Debugging
- Check logs in console output
- Use `--log-cli-level=DEBUG` with pytest
- Review configuration files

---

## ✅ Checklist

Before running your system:

- [ ] All hardware connected correctly
- [ ] External power for motors connected
- [ ] Common ground connected
- [ ] Python dependencies installed
- [ ] User added to gpio group
- [ ] Camera enabled (if using)
- [ ] Hardware check passed
- [ ] Configuration files reviewed
- [ ] Safety systems understood

---

## 🎉 You're Ready!

Your hardware control system is now set up and ready to use.

**Start with:**
```bash
python3 main.py
```

**Or try demos:**
```bash
python3 scripts/motor_demo.py
python3 scripts/servo_demo.py
python3 scripts/led_demo.py
```

**Happy building! 🚀**

---

**Version**: 1.0.0  
**Platform**: Raspberry Pi 3/4  
**Status**: Production Ready
