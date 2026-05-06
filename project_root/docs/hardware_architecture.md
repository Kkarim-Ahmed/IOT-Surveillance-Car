# Hardware Architecture Documentation

Complete explanation of the hardware control system architecture.

## Overview

This document explains the design, structure, and rationale behind every component of the hardware control system.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Layer Responsibilities](#layer-responsibilities)
3. [Module Breakdown](#module-breakdown)
4. [Design Patterns](#design-patterns)
5. [Threading Architecture](#threading-architecture)
6. [Safety System Design](#safety-system-design)
7. [Data Flow](#data-flow)
8. [Integration Points](#integration-points)

---

## Architecture Overview

### Layered Architecture

```
┌─────────────────────────────────────────┐
│      Hardware Manager (Coordinator)     │
└─────────────────────────────────────────┘
                    ↕
┌─────────────────────────────────────────┐
│    Component Controllers (High-Level)   │
│  Motor, Servo, LED, Ultrasonic, Camera  │
└─────────────────────────────────────────┘
                    ↕
┌─────────────────────────────────────────┐
│     GPIO/PWM Managers (Abstraction)     │
└─────────────────────────────────────────┘
                    ↕
┌─────────────────────────────────────────┐
│         RPi.GPIO (Hardware API)         │
└─────────────────────────────────────────┘
                    ↕
┌─────────────────────────────────────────┐
│          Physical Hardware              │
└─────────────────────────────────────────┘
```

### Key Principles

1. **Separation of Concerns** - Each layer has single responsibility
2. **Abstraction** - Hardware details hidden behind clean interfaces
3. **Modularity** - Components are independent and replaceable
4. **Safety-First** - Safety systems can override all operations
5. **Thread-Safe** - All operations protected for concurrent access

---

## Layer Responsibilities

### Layer 1: Hardware Manager

**File**: `hardware/managers/hardware_manager.py`

**Responsibility**: Coordinate all hardware components

**Does**:
- Initialize all hardware components
- Provide unified interface
- Coordinate safety systems
- Manage component lifecycle
- Handle emergency responses

**Does NOT**:
- Control GPIO pins directly
- Implement hardware protocols
- Contain business logic

### Layer 2: Component Controllers

**Files**: `hardware/motor/`, `hardware/servo/`, etc.

**Responsibility**: High-level component control

**Does**:
- Provide user-friendly APIs
- Implement smooth movements
- Handle component-specific logic
- Validate parameters
- Report status

**Does NOT**:
- Access GPIO directly
- Know about other components
- Implement safety logic (delegates to safety system)

### Layer 3: GPIO/PWM Managers

**Files**: `hardware/gpio/gpio_manager.py`, `hardware/gpio/pwm_manager.py`

**Responsibility**: Hardware abstraction

**Does**:
- Centralize GPIO access
- Manage PWM channels
- Track active pins
- Provide thread-safe operations
- Handle cleanup

**Does NOT**:
- Know about components
- Implement control logic
- Make decisions

### Layer 4: Safety Systems

**Files**: `hardware/safety/`

**Responsibility**: System safety

**Does**:
- Monitor hardware state
- Detect emergencies
- Trigger emergency stops
- Track component health
- Enforce safety rules

**Does NOT**:
- Control hardware directly
- Implement component logic

---

## Module Breakdown

### GPIO Module (`hardware/gpio/`)

#### `gpio_manager.py`
- **Purpose**: Centralized GPIO pin management
- **Pattern**: Singleton
- **Thread-Safe**: Yes (RLock)
- **Key Features**:
  - Pin validation
  - Reserved pin protection
  - Active pin tracking
  - Simulation mode for development

#### `pwm_manager.py`
- **Purpose**: Centralized PWM control
- **Pattern**: Singleton
- **Thread-Safe**: Yes (RLock per channel)
- **Key Features**:
  - PWM channel management
  - Frequency control
  - Duty cycle control
  - Configuration-driven

#### `pin_definitions.py`
- **Purpose**: Load pin configuration from YAML
- **Pattern**: Singleton
- **Key Features**:
  - Configuration loading
  - Pin conflict detection
  - Reserved pin checking

### Motor Module (`hardware/motor/`)

#### `motor_controller.py`
- **Purpose**: High-level motor control
- **Features**:
  - Forward/backward movement
  - Turning (differential drive)
  - Smooth acceleration/deceleration
  - Emergency stop
  - Thread-safe operations

#### `motor_driver.py`
- **Purpose**: Low-level L298N interface
- **Features**:
  - Direction control
  - PWM speed control
  - Individual motor control

#### `motor_safety.py`
- **Purpose**: Motor-specific safety
- **Features**:
  - Speed validation
  - Direction change safety
  - Acceleration limiting
  - Emergency stop state

### Servo Module (`hardware/servo/`)

#### `servo_controller.py`
- **Purpose**: High-level servo control
- **Features**:
  - Angle-based positioning
  - Smooth movement
  - Preset positions
  - Thread-safe operations

#### `servo_calibration.py`
- **Purpose**: Angle to PWM conversion
- **Features**:
  - Pulse width calculation
  - Duty cycle conversion
  - Calibration support

#### `servo_limits.py`
- **Purpose**: Angle validation
- **Features**:
  - Min/max angle enforcement
  - Preset management
  - Calibration offset

### LED Module (`hardware/led/`)

#### `led_controller.py`
- **Purpose**: High-level LED control
- **Features**:
  - RGB color control
  - Brightness control
  - Animation effects
  - Status indication

#### `led_effects.py`
- **Purpose**: Animation implementations
- **Features**:
  - Blink, fade, rainbow, police, pulse
  - Threaded execution
  - Configurable speed

#### `led_patterns.py`
- **Purpose**: Color definitions
- **Features**:
  - Status colors
  - Pattern sequences
  - Color interpolation

### Ultrasonic Module (`hardware/ultrasonic/`)

#### `ultrasonic_controller.py`
- **Purpose**: Distance measurement
- **Features**:
  - HC-SR04 control
  - Continuous monitoring
  - Threaded operation
  - Obstacle detection integration

#### `distance_filter.py`
- **Purpose**: Noise filtering
- **Features**:
  - Moving average
  - Median filtering
  - Noise rejection

#### `obstacle_detection.py`
- **Purpose**: Obstacle logic
- **Features**:
  - Distance thresholds
  - Emergency triggering
  - Warning callbacks

### Camera Module (`hardware/camera/`)

#### `camera_controller.py`
- **Purpose**: High-level camera control
- **Features**:
  - OpenCV integration
  - Threaded capture
  - Dual buffers (main + AI)
  - Snapshot capture

#### `stream_handler.py`
- **Purpose**: Stream management
- **Features**:
  - Frame capture
  - Rate limiting
  - Frame processing
  - FPS calculation

#### `frame_buffer.py`
- **Purpose**: Thread-safe buffering
- **Features**:
  - Queue-based buffering
  - Size limiting
  - Statistics tracking

### Safety Module (`hardware/safety/`)

#### `emergency_stop.py`
- **Purpose**: Emergency management
- **Features**:
  - Multiple trigger types
  - Callback system
  - State tracking
  - Emergency logging

#### `watchdog.py`
- **Purpose**: Component monitoring
- **Features**:
  - Heartbeat tracking
  - Timeout detection
  - Automatic emergency trigger

#### `hardware_monitor.py`
- **Purpose**: Health monitoring
- **Features**:
  - State tracking
  - Health checking
  - System-wide status

---

## Design Patterns

### 1. Singleton Pattern

**Used In**: GPIO Manager, PWM Manager, Hardware Manager

**Why**: Ensure single instance for hardware access

```python
class GPIOManager:
    _instance = None
    _lock = threading.RLock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
            return cls._instance
```

### 2. Factory Pattern

**Used In**: PWM Manager (creating PWM channels)

**Why**: Centralized creation of PWM channels

### 3. Observer Pattern

**Used In**: Emergency Stop (callbacks)

**Why**: Notify multiple components of emergencies

### 4. Strategy Pattern

**Used In**: LED Effects

**Why**: Different animation algorithms

---

## Threading Architecture

### Thread Overview

```
Main Thread
├── Hardware Manager initialization
└── Heartbeat loop

Camera Thread (High Priority)
└── Frame capture and buffering

Ultrasonic Thread (Medium Priority)
└── Distance monitoring

LED Effect Thread (Low Priority)
└── Animation effects

Watchdog Thread (High Priority)
└── Component monitoring
```

### Thread Safety Mechanisms

1. **RLock** - Reentrant locks for nested calls
2. **Queue** - Thread-safe frame buffers
3. **StoppableThread** - Graceful thread termination
4. **@thread_safe** - Decorator for automatic locking

### Thread Communication

- **Queues**: Camera frames
- **Callbacks**: Emergency events, obstacles
- **Shared State**: Protected by locks
- **Events**: Thread synchronization

---

## Safety System Design

### Emergency Triggers

1. **Obstacle Detected** - Ultrasonic < 15cm
2. **Communication Timeout** - No heartbeat
3. **Invalid GPIO State** - Hardware error
4. **Manual Button** - Physical button
5. **Watchdog Timeout** - Component failure
6. **Hardware Error** - Exception in hardware

### Emergency Response Flow

```
Trigger Detected
    ↓
Emergency Stop System
    ↓
Execute Callbacks
    ├→ Stop Motors
    ├→ Set LED Red
    └→ Log Event
    ↓
Block New Commands
```

### Watchdog Operation

```
Register Components
    ↓
Monitor Loop (1s interval)
    ├→ Check Heartbeats
    ├→ Compare to Timeout (10s)
    └→ Trigger Emergency if Timeout
```

---

## Data Flow

### Command Flow

```
User/Backend
    ↓
Hardware Manager
    ↓
Component Controller
    ↓
GPIO/PWM Manager
    ↓
Physical Hardware
```

### Status Flow

```
Physical Hardware
    ↓
Sensor Reading
    ↓
Controller Status
    ↓
Hardware Manager
    ↓
User/Backend
```

---

## Integration Points

### For Backend Integration

```python
# Backend can use Hardware Manager directly
from hardware.managers.hardware_manager import hardware_manager

# Initialize
hardware_manager.initialize()

# Control hardware
hardware_manager.motor.move_forward(70)
hardware_manager.servo.set_angle(pan=45)

# Get status
status = hardware_manager.get_status()

# Cleanup
hardware_manager.cleanup()
```

### For GUI Integration

```python
# GUI can access hardware through manager
status = hardware_manager.get_status()

# Display motor status
motor_status = status['motor']
print(f"Speed: {motor_status['speed']}")

# Display camera frame
frame = hardware_manager.camera.get_latest_frame()
# Display frame in GUI
```

### For AI Integration

```python
# AI can use dedicated buffer
ai_frame = hardware_manager.camera.get_ai_frame()

# Process frame
detections = ai_model.detect(ai_frame)

# Control based on detections
if person_detected:
    hardware_manager.servo.set_angle(pan=angle)
```

---

## Configuration System

### YAML-Based Configuration

All hardware parameters in YAML files:

```yaml
# gpio_config.yaml
motor:
  left_motor:
    enable: 12
    input1: 23
    input2: 24
```

### Configuration Loading

```python
# Loaded at startup
pin_defs = PinDefinitions()  # Loads gpio_config.yaml
pwm_config = PWMManager()    # Loads pwm_config.yaml
```

### Benefits

- No hardcoded values
- Easy customization
- Environment-specific configs
- Version control friendly

---

## Why This Architecture?

### Modularity
- Each component can be tested independently
- Easy to replace components
- Clear boundaries

### Scalability
- Easy to add new hardware
- Supports multiple instances
- Ready for distributed systems

### Maintainability
- Clear structure
- Well-documented
- Consistent patterns

### Safety
- Centralized safety systems
- Multiple protection layers
- Fail-safe design

### Integration
- Clean interfaces
- No tight coupling
- Backend/GUI ready

---

## Future Expansion

### Adding New Hardware

1. Create controller in `hardware/[component]/`
2. Add configuration to `configs/`
3. Initialize in `hardware_manager.py`
4. Add tests
5. Update documentation

### Example: Adding Buzzer

```python
# 1. Create hardware/buzzer/buzzer_controller.py
class BuzzerController:
    def __init__(self):
        self.pin = pin_defs.buzzer.pin
    
    def beep(self, duration):
        # Implementation

# 2. Add to configs/gpio_config.yaml
buzzer:
  pin: 25

# 3. Add to hardware_manager.py
self.buzzer = BuzzerController()
self.buzzer.initialize()
```

---

**Document Version**: 1.0  
**Last Updated**: 2024  
**Author**: Hardware Control System Team
