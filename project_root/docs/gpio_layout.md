# GPIO Pin Layout and Wiring Guide

Complete GPIO pin mapping and wiring instructions for the hardware control system.

## ⚠️ CRITICAL SAFETY WARNINGS

### Power Supply Safety
- **NEVER** power motors or servos from Raspberry Pi GPIO pins
- **ALWAYS** use external power supplies:
  - Motors: 7-12V 2A minimum
  - Servos: 5-6V 2A minimum
- **COMMON GROUND**: All power supplies MUST share common ground with Raspberry Pi

### GPIO Current Limits
- Maximum current per GPIO pin: **16mA**
- Maximum total GPIO current: **50mA**
- Exceeding these limits **WILL PERMANENTLY DAMAGE** your Raspberry Pi

### Reserved Pins - DO NOT USE
- GPIO 0, 1: I2C ID EEPROM
- GPIO 2, 3: I2C (SDA, SCL)
- GPIO 14, 15: UART (TX, RX)

---

## Complete GPIO Pin Mapping (BCM Mode)

### L298N Motor Driver

| Component | GPIO Pin | Physical Pin | Type | Function |
|-----------|----------|--------------|------|----------|
| Left Motor Enable | 12 | 32 | PWM | Speed control |
| Left Motor IN1 | 23 | 16 | Digital | Direction |
| Left Motor IN2 | 24 | 18 | Digital | Direction |
| Right Motor Enable | 13 | 33 | PWM | Speed control |
| Right Motor IN3 | 27 | 13 | Digital | Direction |
| Right Motor IN4 | 22 | 15 | Digital | Direction |

**PWM Frequency**: 1000 Hz

### Servo Motors

| Component | GPIO Pin | Physical Pin | Type | Function |
|-----------|----------|--------------|------|----------|
| Pan Servo | 17 | 11 | PWM | Horizontal movement |
| Tilt Servo | 18 | 12 | PWM | Vertical movement |

**PWM Frequency**: 50 Hz (standard servo frequency)  
**Pulse Width**: 500-2500 microseconds

### RGB LED

| Component | GPIO Pin | Physical Pin | Type | Function |
|-----------|----------|--------------|------|----------|
| Red LED | 16 | 36 | PWM | Red channel |
| Green LED | 20 | 38 | PWM | Green channel |
| Blue LED | 21 | 40 | PWM | Blue channel |

**PWM Frequency**: 1000 Hz  
**Resistors**: 220Ω on each channel

### HC-SR04 Ultrasonic Sensor

| Component | GPIO Pin | Physical Pin | Type | Function |
|-----------|----------|--------------|------|----------|
| Trigger | 5 | 29 | Digital Out | Send pulse |
| Echo | 6 | 31 | Digital In | Receive echo |

**IMPORTANT**: Echo pin outputs 5V. Use voltage divider (1kΩ + 2kΩ) to reduce to 3.3V!

### Camera Module

| Component | Interface | Connection |
|-----------|-----------|------------|
| Camera | CSI | Camera port (ribbon cable) |

---

## Detailed Wiring Instructions

### 1. L298N Motor Driver

#### Power Connections
```
L298N:
├── 12V Input → External 12V power supply (+)
├── GND → External power (-) AND Raspberry Pi GND
├── 5V Output → NOT USED (do not connect to RPi)
└── Motors → OUT1/OUT2 (left), OUT3/OUT4 (right)
```

#### Control Connections
```
Raspberry Pi          L298N
GPIO 12 (PWM)    →    ENA (Left Enable)
GPIO 23          →    IN1
GPIO 24          →    IN2
GPIO 13 (PWM)    →    ENB (Right Enable)
GPIO 27          →    IN3
GPIO 22          →    IN4
GND              →    GND (COMMON GROUND)
```

**Critical Notes**:
- Remove ENA/ENB jumpers for PWM speed control
- Motor voltage: 7-12V recommended
- Never connect motor power to Raspberry Pi

### 2. Servo Motors

```
Pan Servo:
├── Signal (Yellow) → GPIO 17
├── Power (Red)     → External 5V (+)
└── Ground (Brown)  → Common GND

Tilt Servo:
├── Signal (Yellow) → GPIO 18
├── Power (Red)     → External 5V (+)
└── Ground (Brown)  → Common GND
```

**Critical Notes**:
- Servos draw up to 1A under load
- **NEVER** power from Raspberry Pi 5V pins
- Use dedicated 5-6V 2A power supply

### 3. RGB LED

```
Common Cathode RGB LED:

Red:
├── Anode → 220Ω resistor → GPIO 16
└── Cathode → GND

Green:
├── Anode → 220Ω resistor → GPIO 20
└── Cathode → GND

Blue:
├── Anode → 220Ω resistor → GPIO 21
└── Cathode → GND
```

### 4. Ultrasonic Sensor (HC-SR04)

```
HC-SR04:
├── VCC     → 5V (RPi Pin 2 or 4)
├── Trigger → GPIO 5 (direct)
├── Echo    → Voltage Divider → GPIO 6
└── GND     → GND

Voltage Divider:
Echo → 1kΩ → GPIO 6
              ↓
         2kΩ resistor
              ↓
             GND
```

**Formula**: 5V × (2kΩ / 3kΩ) = 3.33V ✓

### 5. Camera Module

```
1. Power off Raspberry Pi
2. Locate CSI camera port
3. Pull up on port edges
4. Insert ribbon cable (blue side facing audio jack)
5. Push port edges down
6. Enable camera in raspi-config
```

---

## PWM-Capable Pins

Raspberry Pi has limited hardware PWM:

| GPIO | Hardware PWM | Used For |
|------|--------------|----------|
| 12 | PWM0 | Left Motor Speed |
| 13 | PWM1 | Right Motor Speed |
| 18 | PWM0 | Tilt Servo |

**Software PWM** used for:
- GPIO 17 (Pan Servo)
- GPIO 16, 20, 21 (RGB LED)

---

## Power Distribution

```
Power System:
├── Raspberry Pi: 5V 3A (official power supply)
├── Motors: 12V 2A (external supply)
└── Servos: 5V 2A (external supply)

All grounds connected together!
```

---

## Grounding Strategy

**CRITICAL**: Common ground for all components!

```
Ground Bus:
├── Raspberry Pi GND
├── Motor Driver GND
├── Servo GND
├── LED GND
├── Ultrasonic GND
└── All Power Supply GND (-)
```

---

## Testing Procedure

### Before Power-On
- [ ] Verify all connections
- [ ] Check for short circuits
- [ ] Confirm voltage divider on echo pin
- [ ] Verify no motors/servos on RPi power
- [ ] Check common ground
- [ ] Verify GPIO pin numbers (BCM mode)

### Power-Up Sequence
1. Connect Raspberry Pi power (5V)
2. Boot and verify system starts
3. Connect motor power (12V)
4. Connect servo power (5V)
5. Run hardware check script
6. Test each component

---

## Troubleshooting

### Motors Not Working
- Check 12V power supply
- Verify ENA/ENB jumpers removed
- Confirm common ground
- Test GPIO pins with multimeter

### Servos Jittering
- Insufficient power supply current
- Use dedicated 5V 2A+ supply
- Check connections
- Verify 50Hz PWM frequency

### Ultrasonic Inaccurate
- Check voltage divider values
- Verify trigger/echo connections
- Ensure clear line of sight
- Check for electrical noise

### LED Not Lighting
- Verify resistor values (220Ω)
- Check LED polarity
- Test GPIO with multimeter
- Confirm PWM functioning

---

## Safety Checklist

- [ ] External power for motors
- [ ] External power for servos
- [ ] Common ground for all components
- [ ] Voltage divider on ultrasonic echo
- [ ] Current-limiting resistors on LEDs
- [ ] No connections to reserved pins
- [ ] Adequate power supply ratings
- [ ] Secure and insulated connections
- [ ] Tested with multimeter

---

**Document Version**: 1.0  
**Last Updated**: 2024  
**Platform**: Raspberry Pi 3/4
