"""
test_mqtt_communication.py — Unit tests for MQTT message validation and payload building.

Run with:
    pytest Development/tests/test_mqtt_communication.py -v
"""

import json
import sys
import os

# Allow importing from parent and utils directories
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "utils"))

from message_validator import validate_motor_command, validate_command, validate_json_string


# ── Motor command tests ────────────────────────────────────────────────────────

def test_valid_forward_command():
    ok, err = validate_motor_command({"direction": "forward", "speed": 80})
    assert ok is True
    assert err is None


def test_valid_stop_command():
    ok, err = validate_motor_command({"direction": "stop", "speed": 0})
    assert ok is True


def test_all_valid_directions():
    for direction in ("forward", "backward", "left", "right", "stop"):
        ok, err = validate_motor_command({"direction": direction, "speed": 60})
        assert ok is True, f"Expected valid for direction={direction}, got err={err}"


def test_invalid_direction():
    ok, err = validate_motor_command({"direction": "fly", "speed": 80})
    assert ok is False
    assert "direction" in err.lower() or "fly" in err


def test_missing_direction():
    ok, err = validate_motor_command({"speed": 80})
    assert ok is False
    assert "direction" in err.lower()


def test_speed_out_of_range_high():
    ok, err = validate_motor_command({"direction": "forward", "speed": 150})
    assert ok is False
    assert "speed" in err.lower()


def test_speed_out_of_range_low():
    ok, err = validate_motor_command({"direction": "forward", "speed": -10})
    assert ok is False


def test_speed_boundary_values():
    for speed in (0, 50, 100):
        ok, _ = validate_motor_command({"direction": "forward", "speed": speed})
        assert ok is True, f"Expected valid for speed={speed}"


def test_default_speed_is_optional():
    # speed field is optional — should default to 80 internally
    ok, err = validate_motor_command({"direction": "backward"})
    assert ok is True


# ── System command tests ───────────────────────────────────────────────────────

def test_valid_servo_command():
    ok, err = validate_command({"command": "SERVO", "angle": 90})
    assert ok is True


def test_servo_angle_out_of_range():
    ok, err = validate_command({"command": "SERVO", "angle": 200})
    assert ok is False
    assert "angle" in err.lower()


def test_valid_beep_command():
    ok, err = validate_command({"command": "BEEP"})
    assert ok is True


def test_unknown_command():
    ok, err = validate_command({"command": "LAUNCH"})
    assert ok is False


def test_missing_command_field():
    ok, err = validate_command({})
    assert ok is False


# ── JSON string validation ─────────────────────────────────────────────────────

def test_valid_json_string_motor():
    ok, result = validate_json_string('{"direction": "left", "speed": 60}')
    assert ok is True
    assert result["direction"] == "left"


def test_invalid_json_string():
    ok, err = validate_json_string("not json at all")
    assert ok is False
    assert "json" in err.lower()


def test_json_string_missing_keys():
    ok, err = validate_json_string('{"speed": 80}')
    assert ok is False


# ── Payload serialisation ──────────────────────────────────────────────────────

def test_payload_is_valid_json():
    payload = json.dumps({"direction": "forward", "speed": 80})
    parsed  = json.loads(payload)
    assert parsed["direction"] == "forward"
    assert parsed["speed"] == 80


def test_dummy():
    """Baseline test — always passes."""
    assert True
