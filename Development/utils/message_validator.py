"""
message_validator.py — Validate MQTT JSON command payloads.

Ensures that messages published to dev/motor and dev/commands contain
the required fields with valid values before they are sent to the Pi.

Usage:
    from message_validator import validate_motor_command, validate_command

    ok, err = validate_motor_command({"direction": "forward", "speed": 80})
    if not ok:
        print(f"Invalid: {err}")
"""

import json

VALID_DIRECTIONS = {"forward", "backward", "left", "right", "stop"}
VALID_COMMANDS   = {"FORWARD", "BACKWARD", "LEFT", "RIGHT", "STOP",
                    "SERVO", "LED_ON", "LED_OFF", "BEEP"}


def validate_motor_command(payload: dict) -> tuple:
    """
    Validate a dev/motor payload.

    Rules:
      - 'direction' must be present and one of VALID_DIRECTIONS
      - 'speed' must be an integer between 0 and 100 (optional, defaults to 80)

    Returns
    -------
    (True, None)          — valid
    (False, error_string) — invalid
    """
    if not isinstance(payload, dict):
        return False, "Payload must be a JSON object"

    direction = payload.get("direction")
    if direction is None:
        return False, "Missing required field: 'direction'"
    if direction not in VALID_DIRECTIONS:
        return False, f"Invalid direction '{direction}'. Must be one of: {sorted(VALID_DIRECTIONS)}"

    speed = payload.get("speed", 80)
    if not isinstance(speed, (int, float)):
        return False, f"'speed' must be a number, got {type(speed).__name__}"
    if not (0 <= speed <= 100):
        return False, f"'speed' must be between 0 and 100, got {speed}"

    return True, None


def validate_command(payload: dict) -> tuple:
    """
    Validate a dev/commands payload.

    Rules:
      - 'command' must be present and one of VALID_COMMANDS
      - 'angle' (if present) must be 0–180
      - 'speed' (if present) must be 0–100

    Returns
    -------
    (True, None)          — valid
    (False, error_string) — invalid
    """
    if not isinstance(payload, dict):
        return False, "Payload must be a JSON object"

    command = payload.get("command")
    if command is None:
        return False, "Missing required field: 'command'"
    if command.upper() not in VALID_COMMANDS:
        return False, f"Unknown command '{command}'. Must be one of: {sorted(VALID_COMMANDS)}"

    if "angle" in payload:
        angle = payload["angle"]
        if not isinstance(angle, (int, float)):
            return False, f"'angle' must be a number, got {type(angle).__name__}"
        if not (0 <= angle <= 180):
            return False, f"'angle' must be between 0 and 180, got {angle}"

    if "speed" in payload:
        speed = payload["speed"]
        if not isinstance(speed, (int, float)):
            return False, f"'speed' must be a number, got {type(speed).__name__}"
        if not (0 <= speed <= 100):
            return False, f"'speed' must be between 0 and 100, got {speed}"

    return True, None


def validate_json_string(raw: str) -> tuple:
    """
    Parse a raw JSON string and validate it as either a motor or command payload.

    Returns (True, parsed_dict) or (False, error_string).
    """
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as e:
        return False, f"Invalid JSON: {e}"

    if "direction" in payload:
        ok, err = validate_motor_command(payload)
    elif "command" in payload:
        ok, err = validate_command(payload)
    else:
        return False, "Payload must contain 'direction' or 'command'"

    return (True, payload) if ok else (False, err)


# ── Quick self-test ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    tests = [
        ({"direction": "forward", "speed": 80},  True),
        ({"direction": "fly",     "speed": 80},  False),
        ({"direction": "stop",    "speed": 150}, False),
        ({"command": "SERVO",     "angle": 90},  True),
        ({"command": "SERVO",     "angle": 200}, False),
        ({"command": "BEEP"},                    True),
        ({},                                     False),
    ]

    print("Message Validator — Self Test")
    print("-" * 40)
    all_pass = True
    for payload, expected in tests:
        if "direction" in payload:
            ok, err = validate_motor_command(payload)
        else:
            ok, err = validate_command(payload)
        passed = ok == expected
        all_pass = all_pass and passed
        mark = "✓" if passed else "✗"
        print(f"  {mark}  {payload}  →  ok={ok}  err={err}")

    print("-" * 40)
    print("All tests passed!" if all_pass else "Some tests FAILED.")
