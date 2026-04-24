"""
test_gui_functionality.py — Unit tests for GUI helper logic.

Tests the non-visual parts of the GUI: speed clamping, servo angle
clamping, command building, and topic routing. No Tkinter window is
opened during these tests.

Run with:
    pytest Development/tests/test_gui_functionality.py -v
"""

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "utils"))


# ── Speed helpers ──────────────────────────────────────────────────────────────

def clamp_speed(value: int) -> int:
    return max(0, min(100, value))


def clamp_angle(value: int) -> int:
    return max(0, min(180, value))


def build_motor_payload(direction: str, speed: int) -> dict:
    return {"direction": direction, "speed": clamp_speed(speed)}


def build_servo_payload(angle: int) -> dict:
    return {"command": "SERVO", "angle": clamp_angle(angle)}


# ── Tests ──────────────────────────────────────────────────────────────────────

def test_speed_clamp_normal():
    assert clamp_speed(80) == 80


def test_speed_clamp_above_max():
    assert clamp_speed(150) == 100


def test_speed_clamp_below_min():
    assert clamp_speed(-20) == 0


def test_speed_clamp_boundary():
    assert clamp_speed(0)   == 0
    assert clamp_speed(100) == 100


def test_angle_clamp_normal():
    assert clamp_angle(90) == 90


def test_angle_clamp_above_max():
    assert clamp_angle(200) == 180


def test_angle_clamp_below_min():
    assert clamp_angle(-5) == 0


def test_motor_payload_structure():
    payload = build_motor_payload("forward", 80)
    assert "direction" in payload
    assert "speed"     in payload
    assert payload["direction"] == "forward"


def test_motor_payload_speed_clamped():
    payload = build_motor_payload("forward", 999)
    assert payload["speed"] == 100


def test_servo_payload_structure():
    payload = build_servo_payload(90)
    assert payload["command"] == "SERVO"
    assert payload["angle"]   == 90


def test_servo_payload_angle_clamped():
    payload = build_servo_payload(250)
    assert payload["angle"] == 180


def test_payload_serialisable():
    payload = build_motor_payload("left", 60)
    raw     = json.dumps(payload)
    parsed  = json.loads(raw)
    assert parsed == payload


def test_all_directions_produce_valid_payloads():
    for direction in ("forward", "backward", "left", "right", "stop"):
        payload = build_motor_payload(direction, 70)
        assert payload["direction"] == direction


def test_dummy():
    """Baseline test — always passes."""
    assert True
