# Testing Guide

Complete guide for testing the Hardware Control System.

## Table of Contents

1. [Test Structure](#test-structure)
2. [Running Tests](#running-tests)
3. [Test Categories](#test-categories)
4. [Hardware Tests](#hardware-tests)
5. [Simulation Mode](#simulation-mode)
6. [Demo Scripts](#demo-scripts)
7. [Continuous Integration](#continuous-integration)

---

## Test Structure

```
tests/
├── motor_tests/           # Motor controller tests
├── servo_tests/           # Servo controller tests
├── led_tests/             # LED controller tests
├── ultrasonic_tests/      # Ultrasonic sensor tests
├── camera_tests/          # Camera controller tests
└── integration_tests/     # Full system integration tests
```

Each test module follows the pattern:
- `test_[component]_controller.py` - Main component tests
- Uses pytest fixtures for setup/teardown
- Mocks GPIO when hardware unavailable
- Tests both functionality and error handling

---

## Running Tests

### Run All Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=hardware --cov-report=html
```

### Run Specific Test Suites

```bash
# Motor tests only
pytest tests/motor_tests/

# Servo tests only
pytest tests/servo_tests/

# LED tests only
pytest tests/led_tests/

# Integration tests only
pytest tests/integration_tests/
```

### Run Specific Test Files

```bash
# Test motor controller
pytest tests/motor_tests/test_motor_controller.py

# Test hardware manager
pytest tests/integration_tests/test_hardware_manager.py
```

### Run Specific Test Functions

```bash
# Test specific function
pytest tests/motor_tests/test_motor_controller.py::TestMotorController::test_move_forward

# Test multiple specific functions
pytest tests/motor_tests/test_motor_controller.py::TestMotorController::test_move_forward \
       tests/motor_tests/test_motor_controller.py::TestMotorController::test_stop
```

---

## Test Categories

Tests are marked with categories for selective execution:

### Unit Tests

```bash
# Run only unit tests
pytest -m unit
```

Tests individual components in isolation.

### Integration Tests

```bash
# Run only integration tests
pytest -m integration
```

Tests component interactions and system integration.

### Hardware Tests

```bash
# Run only hardware tests (requires actual hardware)
pytest -m hardware
```

Tests that require physical hardware connection.

### Simulation Tests

```bash
# Run only simulation tests
pytest -m simulation
```

Tests that run in simulation mode without hardware.

---

## Hardware Tests

### Prerequisites

1. **Hardware Setup**
   - Raspberry Pi with all components connected
   - Proper power supply for motors and servos
   - All GPIO connections verified

2. **Permissions**
   ```bash
   # Add user to GPIO group
   sudo usermod -a -G gpio $USER
   
   # Reboot to apply
   sudo reboot
   ```

3. **Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

### Running Hardware Tests

```bash
# Check hardware connections first
python3 scripts/hardware_check.py

# Run hardware-specific tests
pytest -m hardware

# Run with hardware logging
pytest -m hardware --log-cli-level=DEBUG
```

### Safety Considerations

⚠️ **IMPORTANT**: Hardware tests will activate motors, servos, and other components.

- Ensure robot is on a stable surface
- Keep clear of moving parts
- Have emergency stop ready
- Monitor power consumption
- Check for overheating

---

## Simulation Mode

All tests can run in simulation mode without hardware:

### Automatic Simulation

Tests automatically detect if `RPi.GPIO` is unavailable and switch to simulation mode.

```bash
# On non-Raspberry Pi systems
pytest  # Automatically runs in simulation mode
```

### Manual Simulation

```bash
# Force simulation mode
export HARDWARE_SIMULATION=1
pytest
```

### Simulation Features

- No actual GPIO operations
- Mock PWM control
- Simulated sensor readings
- Safe for development on any platform
- Useful for CI/CD pipelines

---

## Demo Scripts

Interactive demonstrations of hardware capabilities.

### Motor Demo

```bash
# Run motor demonstration
python3 scripts/motor_demo.py
```

**Demonstrates:**
- Forward/backward movement
- Left/right turning
- Speed control
- Smooth acceleration/deceleration
- Emergency stop

### Servo Demo

```bash
# Run servo demonstration
python3 scripts/servo_demo.py
```

**Demonstrates:**
- Pan/tilt movements
- Preset positions
- Smooth movement
- Scanning patterns
- Tracking simulation

### LED Demo

```bash
# Run LED demonstration
python3 scripts/led_demo.py
```

**Demonstrates:**
- Basic colors
- Brightness control
- Status colors
- Rainbow effect
- Blink, fade, pulse effects
- Emergency flash

### Hardware Check

```bash
# Comprehensive hardware validation
python3 scripts/hardware_check.py
```

**Checks:**
- GPIO initialization
- Motor functionality
- Servo operation
- LED control
- Sensor readings
- Camera capture

---

## Test Coverage

### Generate Coverage Report

```bash
# Run tests with coverage
pytest --cov=hardware --cov-report=html --cov-report=term

# View HTML report
# Open htmlcov/index.html in browser
```

### Coverage Goals

- **Unit Tests**: > 80% coverage
- **Integration Tests**: > 70% coverage
- **Critical Paths**: 100% coverage
  - Emergency stop
  - Safety systems
  - GPIO management

---

## Continuous Integration

### GitHub Actions Example

```yaml
name: Hardware Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.9
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-cov
    
    - name: Run tests
      run: |
        pytest --cov=hardware --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v2
```

---

## Troubleshooting

### Common Issues

#### 1. Permission Denied on GPIO

```bash
# Solution
sudo usermod -a -G gpio $USER
sudo reboot
```

#### 2. Import Errors

```bash
# Ensure project root in path
export PYTHONPATH="${PYTHONPATH}:/path/to/project_root"

# Or install in development mode
pip install -e .
```

#### 3. Camera Not Found

```bash
# Check camera
vcgencmd get_camera

# Enable camera
sudo raspi-config
# Interface Options → Camera → Enable
```

#### 4. Tests Hanging

```bash
# Run with timeout
pytest --timeout=60

# Or kill hanging processes
pkill -f pytest
```

#### 5. GPIO Already in Use

```bash
# Cleanup GPIO
python3 scripts/gpio_cleanup.py

# Or force cleanup
sudo python3 -c "import RPi.GPIO as GPIO; GPIO.cleanup()"
```

---

## Writing New Tests

### Test Template

```python
"""
Component Tests
Description of what is being tested
"""

import pytest
from unittest.mock import patch
from hardware.component.controller import Controller


class TestController:
    """Test controller functionality"""
    
    @pytest.fixture
    def controller(self):
        """Create controller instance"""
        with patch('hardware.gpio.gpio_manager.GPIO_AVAILABLE', False):
            ctrl = Controller()
            ctrl.initialize()
            yield ctrl
            ctrl.cleanup()
    
    def test_initialization(self, controller):
        """Test controller initialization"""
        assert controller.initialized
    
    def test_functionality(self, controller):
        """Test specific functionality"""
        # Test implementation
        pass
```

### Best Practices

1. **Use Fixtures** - Setup/teardown in fixtures
2. **Mock Hardware** - Use mocks for GPIO operations
3. **Test Edge Cases** - Invalid inputs, boundary conditions
4. **Test Error Handling** - Exception handling
5. **Document Tests** - Clear docstrings
6. **Keep Tests Fast** - Mock slow operations
7. **Isolate Tests** - No dependencies between tests

---

## Performance Testing

### Timing Tests

```python
import time

def test_motor_response_time(motor_controller):
    """Test motor response time"""
    start = time.time()
    motor_controller.move_forward(speed=70)
    elapsed = time.time() - start
    
    assert elapsed < 0.1  # Should respond in < 100ms
```

### Load Testing

```python
def test_continuous_operation(motor_controller):
    """Test continuous operation"""
    for _ in range(1000):
        motor_controller.move_forward(speed=50)
        time.sleep(0.01)
        motor_controller.stop()
    
    # Should complete without errors
    assert motor_controller.get_status()['initialized']
```

---

## Test Maintenance

### Regular Tasks

1. **Update Tests** - When adding new features
2. **Review Coverage** - Maintain > 80% coverage
3. **Fix Flaky Tests** - Investigate intermittent failures
4. **Update Mocks** - Keep mocks synchronized with hardware
5. **Document Changes** - Update test documentation

### Test Review Checklist

- [ ] All tests pass
- [ ] Coverage meets goals
- [ ] No flaky tests
- [ ] Documentation updated
- [ ] Hardware tests verified
- [ ] Simulation tests work
- [ ] CI/CD pipeline passes

---

## Additional Resources

- [pytest Documentation](https://docs.pytest.org/)
- [unittest.mock Guide](https://docs.python.org/3/library/unittest.mock.html)
- [Coverage.py Documentation](https://coverage.readthedocs.io/)
- [Raspberry Pi GPIO Documentation](https://sourceforge.net/p/raspberry-gpio-python/wiki/Home/)

---

**Version**: 1.0.0  
**Last Updated**: 2024
