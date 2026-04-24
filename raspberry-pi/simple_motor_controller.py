"""
simple_motor_controller.py — Lightweight GPIO motor control for MQTT device controller.

Hardware: L298N dual H-bridge motor driver.

Wiring:
  ENA → PWM speed for left  motors  (GPIO12 / PWM0)
  ENB → PWM speed for right motors  (GPIO13 / PWM1)
  IN1 / IN2 → left  motor direction
  IN3 / IN4 → right motor direction

Direction truth table (L298N):
  Forward  : IN1=H IN2=L  IN3=H IN4=L
  Backward : IN1=L IN2=H  IN3=L IN4=H
  Left     : IN1=L IN2=H  IN3=H IN4=L  (left back, right forward)
  Right    : IN1=H IN2=L  IN3=L IN4=H  (left forward, right back)
  Stop     : IN1=L IN2=L  IN3=L IN4=L  ENA=0 ENB=0

Public API (unchanged — fully compatible with mqtt_device_controller.py):
  setup()
  move_forward(speed=80)
  move_backward(speed=80)
  turn_left(speed=60)
  turn_right(speed=60)
  stop()
  set_speed(speed)
  cleanup()
"""

import RPi.GPIO as GPIO
from config import (
    ENA_PIN, ENB_PIN,
    IN1_PIN, IN2_PIN,
    IN3_PIN, IN4_PIN,
    PWM_FREQ,
)

# ─── Module-level PWM handles ─────────────────────────────────────────────────
# Initialised once by setup(); reused by all movement functions.
_pwm_left  = None   # ENA — controls left  motor speed
_pwm_right = None   # ENB — controls right motor speed
_initialized = False


def setup():
    """
    Configure GPIO pins and start PWM channels on ENA / ENB.
    Must be called once before any movement function.
    Safe to call multiple times — subsequent calls are no-ops.
    """
    global _pwm_left, _pwm_right, _initialized

    if _initialized:
        return

    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

    # Set all L298N control pins as outputs
    output_pins = [ENA_PIN, ENB_PIN, IN1_PIN, IN2_PIN, IN3_PIN, IN4_PIN]
    GPIO.setup(output_pins, GPIO.OUT)

    # Start with all direction pins LOW (motors braked)
    GPIO.output([IN1_PIN, IN2_PIN, IN3_PIN, IN4_PIN], GPIO.LOW)

    # Initialise PWM on enable pins at 0% duty cycle
    _pwm_left  = GPIO.PWM(ENA_PIN, PWM_FREQ)
    _pwm_right = GPIO.PWM(ENB_PIN, PWM_FREQ)
    _pwm_left.start(0)
    _pwm_right.start(0)

    _initialized = True
    print("[SIMPLE_MOTOR] L298N GPIO setup complete")


# ─── Internal helpers ─────────────────────────────────────────────────────────

def _set_direction(in1, in2, in3, in4):
    """
    Set the four direction pins in one call.
    Each argument is GPIO.HIGH or GPIO.LOW.
    """
    GPIO.output(IN1_PIN, in1)
    GPIO.output(IN2_PIN, in2)
    GPIO.output(IN3_PIN, in3)
    GPIO.output(IN4_PIN, in4)


def _set_pwm(speed):
    """
    Apply the same duty cycle to both ENA and ENB.
    speed: 0–100 (clamped automatically).
    """
    speed = max(0, min(100, speed))
    _pwm_left.ChangeDutyCycle(speed)
    _pwm_right.ChangeDutyCycle(speed)


def _drive(left_in1, left_in2, right_in3, right_in4, speed):
    """
    Set direction pins then apply PWM speed.
    Centralises all motor state changes.
    """
    _set_direction(left_in1, left_in2, right_in3, right_in4)
    _set_pwm(speed)


# ─── Public movement API ──────────────────────────────────────────────────────

def move_forward(speed=80):
    """Drive both motor pairs forward at the given speed (0–100)."""
    print(f"[SIMPLE_MOTOR] FORWARD  speed={speed}")
    # IN1=H IN2=L → left forward  |  IN3=H IN4=L → right forward
    _drive(GPIO.HIGH, GPIO.LOW, GPIO.HIGH, GPIO.LOW, speed)


def move_backward(speed=80):
    """Drive both motor pairs backward at the given speed (0–100)."""
    print(f"[SIMPLE_MOTOR] BACKWARD speed={speed}")
    # IN1=L IN2=H → left backward  |  IN3=L IN4=H → right backward
    _drive(GPIO.LOW, GPIO.HIGH, GPIO.LOW, GPIO.HIGH, speed)


def turn_left(speed=60):
    """
    Pivot left in place.
    Left motors run backward, right motors run forward.
    """
    print(f"[SIMPLE_MOTOR] LEFT     speed={speed}")
    # IN1=L IN2=H → left backward  |  IN3=H IN4=L → right forward
    _drive(GPIO.LOW, GPIO.HIGH, GPIO.HIGH, GPIO.LOW, speed)


def turn_right(speed=60):
    """
    Pivot right in place.
    Left motors run forward, right motors run backward.
    """
    print(f"[SIMPLE_MOTOR] RIGHT    speed={speed}")
    # IN1=H IN2=L → left forward  |  IN3=L IN4=H → right backward
    _drive(GPIO.HIGH, GPIO.LOW, GPIO.LOW, GPIO.HIGH, speed)


def stop():
    """
    Brake all motors immediately.
    All direction pins LOW, PWM duty cycle → 0.
    """
    print("[SIMPLE_MOTOR] STOP")
    _set_direction(GPIO.LOW, GPIO.LOW, GPIO.LOW, GPIO.LOW)
    _set_pwm(0)


def set_speed(speed):
    """
    Update PWM duty cycle on ENA and ENB without changing direction.
    Useful for smooth speed ramping while already moving.
    """
    speed = max(0, min(100, speed))
    print(f"[SIMPLE_MOTOR] SET_SPEED speed={speed}")
    _set_pwm(speed)


def cleanup():
    """Stop all motors, release PWM channels, and free GPIO resources."""
    stop()
    if _pwm_left:
        _pwm_left.stop()
    if _pwm_right:
        _pwm_right.stop()
    GPIO.cleanup()
    print("[SIMPLE_MOTOR] GPIO cleaned up")
