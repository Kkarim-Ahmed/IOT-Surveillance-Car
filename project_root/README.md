# Hardware Control System for Raspberry Pi

A professional, production-grade hardware abstraction layer for robotics and IoT projects on Raspberry Pi.

## 🎯 Overview

This project provides a complete hardware control system with:
- **Modular Architecture** - Each hardware component isolated and independently testable
- **Thread-Safe Operations** - Safe concurrent access to all hardware
- **Centralized Configuration** - All settings in YAML files, no hardcoded values
- **Safety Systems** - Emergency stop, watchdog, and hardware monitoring
- **Professional Code Quality** - Type hints, docstrings, SOLID principles

## 🏗️ Architecture

```
Hardware Layer
├── GPIO Management (Centralized pin control)
├── PWM Management (Centralized PWM control)
├── Motor Control (L298N driver with safety)
├── Servo Control (Pan/tilt with smooth movement)
├── LED Control (RGB with PWM and effects)
├── Ultrasonic Sensor (Distance measurement with filtering)
├── Camera Control (Threaded capture with buffering)
└── Safety Systems (Emergency stop, watchdog, monitoring)
```

## 📋 Hardware Support

- **L298N Motor Driver** - Dual DC motor control with PWM speed
- **Servo Motors** - Pan/tilt servos with angle limits
- **RGB LED** - PWM-controlled with 6 animation effects
- **HC-SR04 Ultrasonic** - Distance measurement with noise filtering
- **Camera Module** - OpenCV-based capture with dual buffers

## 🚀 Quick Start

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Make scripts executable
chmod +x scripts/*.sh scripts/*.py

# Run hardware check
python3 scripts/hardware_check.py
```

### Basic Usage

```python
from hardware.managers.hardware_manager import hardware_manager

# Initialize all hardware
hardware_manager.initialize()

# Control motor
hardware_manager.motor.move_forward(speed=70)
time.sleep(2)
hardware_manager.motor.stop()

# Control servo
hardware_manager.servo.set_angle(pan=45, tilt=20)

# Control LED
hardware_manager.led.set_color(255, 0, 0)  # Red

# Get distance
distance = hardware_manager.ultrasonic.get_filtered_distance()

# Capture frame
frame = hardware_manager.camera.get_latest_frame()

# Cleanup
hardware_manager.cleanup()
```

## 📁 Project Structure

```
project_root/
├── hardware/
│   ├── gpio/              # GPIO and PWM management
│   ├── motor/             # Motor control
│   ├── servo/             # Servo control
│   ├── led/               # LED control
│   ├── ultrasonic/        # Distance sensor
│   ├── camera/            # Camera control
│   ├── safety/            # Safety systems
│   ├── managers/          # Hardware manager
│   └── utils/             # Utilities
├── configs/               # YAML configuration files
├── tests/                 # Test suites
├── scripts/               # Utility scripts
├── docs/                  # Documentation
└── main.py                # Entry point
```

## ⚙️ Configuration

All hardware configuration is in YAML files:

- `gpio_config.yaml` - GPIO pin mappings
- `pwm_config.yaml` - PWM frequencies and duty cycles
- `servo_config.yaml` - Servo angle limits and presets
- `safety_config.yaml` - Safety thresholds and triggers

## 🔒 Safety Features

### Emergency Stop System
- Multiple trigger types (obstacle, timeout, manual, etc.)
- Immediate motor stop
- LED emergency indication
- Callback system for custom responses

### Watchdog
- Monitors component heartbeats
- Configurable timeout
- Automatic emergency trigger on failure

### Hardware Monitor
- Tracks component states
- Health checking
- Anomaly detection

## 🧪 Testing

```bash
# Run all hardware tests
python3 scripts/hardware_check.py

# Test specific component
pytest tests/motor_tests/

# Run with coverage
pytest --cov=hardware --cov-report=html
```

## 📚 Documentation

- **[GPIO Layout](docs/gpio_layout.md)** - Complete wiring guide
- **[Hardware Architecture](docs/hardware_architecture.md)** - System design explanation

## 🔧 Hardware Wiring

See `docs/gpio_layout.md` for complete wiring instructions.

**Quick Reference (BCM Mode)**:
- Motors: EN1=12, IN1=23, IN2=24, EN2=13, IN3=27, IN4=22
- Servos: Pan=17, Tilt=18
- LED: R=16, G=20, B=21
- Ultrasonic: Trig=5, Echo=6

⚠️ **IMPORTANT**: Use external power for motors and servos!

## 🎓 Key Features

### Modular Design
- Each component is independently testable
- Easy to add new hardware
- Clean separation of concerns

### Thread-Safe
- All hardware access is thread-safe
- Proper locking mechanisms
- Safe concurrent operations

### Configuration-Driven
- No hardcoded values
- Easy to customize
- Environment-specific configs

### Safety-First
- Emergency stop system
- Watchdog monitoring
- Hardware health checking

## 🔌 Integration Ready

This hardware layer is designed for easy integration with:
- **Backend Services** - REST API, MQTT, WebSocket
- **GUI Applications** - PyQt5, web interfaces
- **AI Systems** - Computer vision, autonomous control
- **Network Control** - Remote operation, fleet management

## 📝 Example: Motor Control

```python
from hardware.motor.motor_controller import MotorController

# Initialize
motor = MotorController()
motor.initialize()

# Move forward with smooth acceleration
motor.move_forward(speed=70)

# Turn left
motor.turn_left(speed=60)

# Stop smoothly
motor.stop(smooth=True)

# Emergency stop
motor.emergency_stop()

# Cleanup
motor.cleanup()
```

## 📝 Example: LED Effects

```python
from hardware.led.led_controller import LEDController, LEDEffect

# Initialize
led = LEDController()
led.initialize()

# Set color
led.set_color(255, 0, 0)  # Red

# Set status color
led.set_status_color('moving')  # Blue

# Start effect
led.start_effect(LEDEffect.RAINBOW)

# Stop effect
led.stop_effect()

# Cleanup
led.cleanup()
```

## 🛠️ Development

### Adding New Hardware

1. Create controller in `hardware/[component]/`
2. Add configuration to `configs/`
3. Update `hardware_manager.py`
4. Add tests in `tests/`
5. Update documentation

### Code Style

- Use type hints
- Write docstrings
- Follow SOLID principles
- Keep modules independent
- Use thread-safe patterns

## 📊 Performance

- **Motor Response**: < 100ms
- **Servo Movement**: Smooth stepping at 20ms intervals
- **Camera FPS**: 30fps (configurable)
- **Sensor Update**: 10Hz (100ms intervals)
- **Thread-Safe**: All operations protected

## 🐛 Troubleshooting

### Permission Denied on GPIO
```bash
sudo usermod -a -G gpio $USER
sudo reboot
```

### Camera Not Found
```bash
# Check camera
vcgencmd get_camera

# Enable in raspi-config
sudo raspi-config
# Interface Options → Camera → Enable
```

### Motors Not Working
- Check external power supply (12V)
- Verify common ground connection
- Check GPIO pin numbers in config

## 📄 License

This project is provided for educational and development purposes.

## 🙏 Acknowledgments

- Raspberry Pi Foundation
- Python Community
- OpenCV Project

---

**Version**: 1.0.0  
**Status**: Production Ready  
**Platform**: Raspberry Pi 3/4
