"""
mqtt_device_controller.py — MQTT subscriber and hardware dispatcher (Raspberry Pi).

Responsibilities:
  1. Connect to the MQTT broker defined in client_config.json (or config.py fallback)
  2. Subscribe to dev/motor, dev/led, dev/commands
  3. Parse incoming JSON payloads and dispatch to hardware controllers
  4. Publish acknowledgement / status messages to dev/status
  5. Fail-safe watchdog: stop all motors if no command is received for 2 seconds

Topics consumed:
  dev/motor    → { "direction": "forward"|"backward"|"left"|"right"|"stop",
                   "speed": 0-100 }
  dev/led      → { "state": "on"|"off"|"blink" }
  dev/commands → { "command": "BEEP"|"SERVO"|"STOP"|"LED_ON"|"LED_OFF",
                   "angle": 0-180, "speed": 0-100 }

Topic published:
  dev/status   → { "command": "...", "speed": ..., "servo": ..., "timestamp": ... }

Run on the Raspberry Pi:
  python mqtt_device_controller.py
"""

import json
import time
import threading
import signal
import sys

import paho.mqtt.client as mqtt

# ── Local hardware modules ────────────────────────────────────────────────────
import simple_motor_controller as motors
from servo_controller import ServoController
from peripherals      import Peripherals
from connection_manager import ConnectionManager

# ── Load broker config from client_config.json ───────────────────────────────
import os

_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "mqtt-config", "client_config.json")

def _load_config():
    """Load broker settings from client_config.json, fall back to config.py values."""
    try:
        with open(_CONFIG_PATH, "r") as f:
            cfg = json.load(f)
        print(f"[DEVICE] Loaded broker config from {_CONFIG_PATH}")
        return cfg
    except FileNotFoundError:
        print(f"[DEVICE] client_config.json not found — using config.py defaults")
        from config import MQTT_BROKER, MQTT_PORT
        return {
            "broker_host": MQTT_BROKER,
            "broker_port": MQTT_PORT,
            "topics": {
                "motor"   : "dev/motor",
                "led"     : "dev/led",
                "commands": "dev/commands",
                "status"  : "dev/status",
            },
        }

_cfg = _load_config()

# ─── Topic constants ──────────────────────────────────────────────────────────
_TOPICS = _cfg.get("topics", {})
TOPIC_MOTOR    = _TOPICS.get("motor",    "dev/motor")
TOPIC_LED      = _TOPICS.get("led",      "dev/led")
TOPIC_COMMANDS = _TOPICS.get("commands", "dev/commands")
TOPIC_STATUS   = _TOPICS.get("status",   "dev/status")

# ─── Fail-safe configuration ──────────────────────────────────────────────────
FAILSAFE_TIMEOUT = 2.0   # seconds — stop motors if no command received

# ─── Global state ─────────────────────────────────────────────────────────────
_last_command_time = time.time()
_failsafe_active   = False
_servo             = None
_periph            = None
_mqtt_client       = None


# ─── Fail-safe watchdog ───────────────────────────────────────────────────────

def _failsafe_watchdog():
    """
    Background thread.
    Stops all motors if no motor/command message arrives within FAILSAFE_TIMEOUT.
    Publishes an alert to dev/status when triggered.
    """
    global _failsafe_active, _last_command_time

    while True:
        time.sleep(0.25)   # check 4× per second for fast response
        elapsed = time.time() - _last_command_time

        if elapsed > FAILSAFE_TIMEOUT and not _failsafe_active:
            _failsafe_active = True
            print(f"[FAILSAFE] No command for {elapsed:.1f}s — stopping motors!")
            motors.stop()
            _periph.alert_beep()

            # Publish fail-safe alert to status topic
            if _mqtt_client:
                payload = json.dumps({
                    "type"     : "failsafe",
                    "message"  : "No command received — motors stopped",
                    "elapsed"  : round(elapsed, 2),
                    "timestamp": time.time(),
                })
                _mqtt_client.publish(TOPIC_STATUS, payload, qos=1)

        elif elapsed <= FAILSAFE_TIMEOUT and _failsafe_active:
            _failsafe_active = False
            print("[FAILSAFE] Command resumed — watchdog reset")


# ─── Command handlers ─────────────────────────────────────────────────────────

def _handle_motor(payload: dict):
    """
    Handle dev/motor messages.
    Expected payload: { "direction": "forward", "speed": 80 }
    """
    global _last_command_time, _failsafe_active

    _last_command_time = time.time()
    _failsafe_active   = False

    direction = payload.get("direction", "stop").lower()
    speed     = int(payload.get("speed", 80))
    speed     = max(0, min(100, speed))

    if   direction == "forward":  motors.move_forward(speed)
    elif direction == "backward": motors.move_backward(speed)
    elif direction == "left":     motors.turn_left(speed)
    elif direction == "right":    motors.turn_right(speed)
    elif direction == "stop":     motors.stop()
    else:
        print(f"[DEVICE] Unknown direction: {direction}")
        return

    _publish_status({"command": direction, "speed": speed, "servo": _servo.angle})


def _handle_led(payload: dict):
    """
    Handle dev/led messages.
    Expected payload: { "state": "on" | "off" | "blink" }
    """
    state = payload.get("state", "off").lower()

    if   state == "on":    _periph.led_on()
    elif state == "off":   _periph.led_off()
    elif state == "blink": _periph.led_blink()
    else:
        print(f"[DEVICE] Unknown LED state: {state}")
        return

    print(f"[DEVICE] LED → {state}")
    _publish_status({"command": f"LED_{state.upper()}", "servo": _servo.angle})


def _handle_commands(payload: dict):
    """
    Handle dev/commands messages.
    Expected payload: { "command": "SERVO", "angle": 90, "speed": 80 }
    """
    global _last_command_time, _failsafe_active

    command = payload.get("command", "").upper()
    angle   = int(payload.get("angle", 90))
    speed   = int(payload.get("speed", 80))

    # Motor commands also reset the fail-safe timer
    if command in ("FORWARD", "BACKWARD", "LEFT", "RIGHT", "STOP"):
        _last_command_time = time.time()
        _failsafe_active   = False

    if   command == "FORWARD":  motors.move_forward(speed)
    elif command == "BACKWARD": motors.move_backward(speed)
    elif command == "LEFT":     motors.turn_left(speed)
    elif command == "RIGHT":    motors.turn_right(speed)
    elif command == "STOP":     motors.stop()
    elif command == "SERVO":
        angle = max(0, min(180, angle))
        _servo.set_angle(angle)
    elif command == "LED_ON":   _periph.led_on()
    elif command == "LED_OFF":  _periph.led_off()
    elif command == "BEEP":     _periph.beep()
    else:
        print(f"[DEVICE] Unknown command: {command}")
        return

    _publish_status({"command": command, "speed": speed, "servo": _servo.angle})


def _publish_status(extra: dict = None):
    """Publish a status message to dev/status."""
    if not _mqtt_client:
        return
    payload = {
        "timestamp": time.time(),
        "servo"    : _servo.angle if _servo else 90,
    }
    if extra:
        payload.update(extra)
    _mqtt_client.publish(TOPIC_STATUS, json.dumps(payload), qos=0)


# ─── MQTT callbacks ───────────────────────────────────────────────────────────

def _on_connect(client, userdata, flags, rc):
    if rc == 0:
        broker = _cfg.get("broker_host", "?")
        port   = _cfg.get("broker_port", 1883)
        print(f"[MQTT] Connected to {broker}:{port}")

        # Subscribe to all inbound topics
        topics = [
            (TOPIC_MOTOR,    1),
            (TOPIC_LED,      1),
            (TOPIC_COMMANDS, 1),
        ]
        client.subscribe(topics)
        print(f"[MQTT] Subscribed: {[t[0] for t in topics]}")

        # Announce online
        client.publish(TOPIC_STATUS, json.dumps({"status": "online", "timestamp": time.time()}), qos=1)
        _periph.led_on()
        _periph.beep()
    else:
        print(f"[MQTT] Connection failed, rc={rc}")


def _on_disconnect(client, userdata, rc):
    print(f"[MQTT] Disconnected (rc={rc})")
    _periph.led_off()


def _on_message(client, userdata, msg):
    """Route incoming MQTT messages to the correct handler."""
    topic = msg.topic

    try:
        payload = json.loads(msg.payload.decode("utf-8"))
        print(f"[MQTT] ← {topic}: {payload}")
    except json.JSONDecodeError:
        print(f"[MQTT] Invalid JSON on {topic}: {msg.payload}")
        return
    except Exception as e:
        print(f"[MQTT] Decode error on {topic}: {e}")
        return

    try:
        if   topic == TOPIC_MOTOR:    _handle_motor(payload)
        elif topic == TOPIC_LED:      _handle_led(payload)
        elif topic == TOPIC_COMMANDS: _handle_commands(payload)
        else:
            print(f"[MQTT] Unhandled topic: {topic}")
    except Exception as e:
        print(f"[MQTT] Handler error on {topic}: {e}")


# ─── Graceful shutdown ────────────────────────────────────────────────────────

def _shutdown(signum, frame):
    print("\n[DEVICE] Shutting down...")
    motors.stop()
    if _servo:  _servo.cleanup()
    if _periph: _periph.cleanup()
    if _mqtt_client:
        _mqtt_client.publish(
            TOPIC_STATUS,
            json.dumps({"status": "offline", "timestamp": time.time()}),
            qos=1,
        )
        time.sleep(0.3)
        _mqtt_client.disconnect()
    motors.cleanup()
    sys.exit(0)


# ─── Entry point ──────────────────────────────────────────────────────────────

def main():
    global _servo, _periph, _mqtt_client

    print("=" * 55)
    print("  MQTT Device Controller — Raspberry Pi")
    print("=" * 55)

    # ── Hardware init ─────────────────────────────────────────────────────────
    motors.setup()
    _servo  = ServoController()
    _periph = Peripherals()

    # ── MQTT client via ConnectionManager ────────────────────────────────────
    manager = ConnectionManager(config_path=_CONFIG_PATH)
    _mqtt_client = manager.build_client(
        client_id  = _cfg.get("client_id", "mqtt-device-controller"),
        on_connect = _on_connect,
        on_disconnect = _on_disconnect,
        on_message = _on_message,
    )

    # Last-will: mark device offline if connection drops unexpectedly
    _mqtt_client.will_set(
        TOPIC_STATUS,
        json.dumps({"status": "offline", "reason": "unexpected disconnect"}),
        qos=1,
        retain=True,
    )

    manager.connect(_mqtt_client)
    _mqtt_client.loop_start()

    # ── Fail-safe watchdog thread ─────────────────────────────────────────────
    watchdog = threading.Thread(target=_failsafe_watchdog, daemon=True)
    watchdog.start()
    print(f"[DEVICE] Fail-safe watchdog active (timeout={FAILSAFE_TIMEOUT}s)")

    # ── Signal handlers ───────────────────────────────────────────────────────
    signal.signal(signal.SIGINT,  _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    print("[DEVICE] Ready — waiting for MQTT commands...")

    # Keep main thread alive
    while True:
        time.sleep(1)


if __name__ == "__main__":
    main()
