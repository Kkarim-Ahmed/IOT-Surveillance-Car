#!/usr/bin/env python3
"""
MQTT Device Controller - Modified for Cloud Mode
Automatically connects to HiveMQ cloud broker
"""

import json
import time
import threading
import signal
import sys
import os

# Import connection manager
from connection_manager import ConnectionManager

# Hardware imports (with fallback to mock)
try:
    import simple_motor_controller as motors
    from servo_controller import ServoController
    from peripherals import Peripherals
    _HARDWARE_AVAILABLE = True
except ImportError:
    _HARDWARE_AVAILABLE = False
    print("[DEVICE] Hardware modules not found — running in mock mode")

# Config path
_CONFIG_PATH = "config/client_config.json"

# Topics
TOPIC_MOTOR = "dev/motor"
TOPIC_LED = "dev/led"
TOPIC_COMMANDS = "dev/commands"
TOPIC_STATUS = "dev/status"

# Global state
_last_command_time = time.time()
_failsafe_active = False
_servo = None
_periph = None
_mqtt_client = None

# Mock hardware classes
class _MockMotors:
    def setup(self): print("[MOCK] motors.setup()")
    def move_forward(self, s=80): print(f"[MOCK] FORWARD speed={s}")
    def move_backward(self, s=80): print(f"[MOCK] BACKWARD speed={s}")
    def turn_left(self, s=60): print(f"[MOCK] LEFT speed={s}")
    def turn_right(self, s=60): print(f"[MOCK] RIGHT speed={s}")
    def stop(self): print("[MOCK] STOP")
    def cleanup(self): print("[MOCK] motors.cleanup()")

class _MockServo:
    angle = 90
    def set_angle(self, a): self.angle = a; print(f"[MOCK] SERVO → {a}°")
    def cleanup(self): print("[MOCK] servo.cleanup()")

class _MockPeriph:
    def led_on(self): print("[MOCK] LED ON")
    def led_off(self): print("[MOCK] LED OFF")
    def led_blink(self): print("[MOCK] LED BLINK")
    def beep(self): print("[MOCK] BEEP")
    def alert_beep(self): print("[MOCK] ALERT BEEP")
    def cleanup(self): print("[MOCK] periph.cleanup()")

def _handle_motor(payload: dict):
    global _last_command_time, _failsafe_active
    _last_command_time = time.time()
    _failsafe_active = False

    direction = payload.get("direction", "stop").lower()
    speed = max(0, min(100, int(payload.get("speed", 80))))

    if direction == "forward": motors.move_forward(speed)
    elif direction == "backward": motors.move_backward(speed)
    elif direction == "left": motors.turn_left(speed)
    elif direction == "right": motors.turn_right(speed)
    elif direction == "stop": motors.stop()
    else:
        print(f"[DEVICE] Unknown direction: {direction}")
        return

    _publish_status({"command": direction, "speed": speed, "servo": _servo.angle})

def _handle_led(payload: dict):
    state = payload.get("state", "off").lower()
    if state == "on": _periph.led_on()
    elif state == "off": _periph.led_off()
    elif state == "blink": _periph.led_blink()
    else:
        print(f"[DEVICE] Unknown LED state: {state}")
        return
    print(f"[DEVICE] LED → {state}")
    _publish_status({"command": f"LED_{state.upper()}", "servo": _servo.angle})

def _handle_commands(payload: dict):
    global _last_command_time, _failsafe_active
    command = payload.get("command", "").upper()
    
    if command == "STATUS":
        _publish_status({"command": "STATUS", "timestamp": time.time()})
    else:
        print(f"[DEVICE] Unknown command: {command}")

def _publish_status(extra: dict = None):
    if not _mqtt_client:
        return
    payload = {"timestamp": time.time(), "servo": _servo.angle if _servo else 90}
    if extra:
        payload.update(extra)
    _mqtt_client.publish(TOPIC_STATUS, json.dumps(payload), qos=0)

def _on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"[MQTT] ✅ Connected to HiveMQ cloud broker!")
        topics = [(TOPIC_MOTOR, 1), (TOPIC_LED, 1), (TOPIC_COMMANDS, 1)]
        client.subscribe(topics)
        print(f"[MQTT] Subscribed: {[t[0] for t in topics]}")
        client.publish(TOPIC_STATUS, json.dumps({"status": "online", "timestamp": time.time()}), qos=1)
        if _periph:
            _periph.led_on()
            _periph.beep()
    else:
        error_messages = {
            1: "Incorrect protocol version",
            2: "Invalid client identifier", 
            3: "Server unavailable",
            4: "Bad username or password",
            5: "Not authorized"
        }
        error_msg = error_messages.get(rc, f"Unknown error code {rc}")
        print(f"[MQTT] ❌ Connection failed: {error_msg}")

def _on_disconnect(client, userdata, rc):
    print(f"[MQTT] Disconnected (rc={rc})")
    if _periph:
        _periph.led_off()

def _on_message(client, userdata, msg):
    topic = msg.topic
    try:
        payload = json.loads(msg.payload.decode("utf-8"))
        print(f"[MQTT] ← {topic}: {payload}")
    except (json.JSONDecodeError, Exception) as e:
        print(f"[MQTT] Decode error on {topic}: {e}")
        return

    try:
        if topic == TOPIC_MOTOR: _handle_motor(payload)
        elif topic == TOPIC_LED: _handle_led(payload)
        elif topic == TOPIC_COMMANDS: _handle_commands(payload)
        else:
            print(f"[MQTT] Unhandled topic: {topic}")
    except Exception as e:
        print(f"[MQTT] Handler error on {topic}: {e}")

def _shutdown(signum, frame):
    print("\n[DEVICE] Shutting down...")
    if hasattr(motors, 'stop'):
        motors.stop()
    if _servo: _servo.cleanup()
    if _periph: _periph.cleanup()
    if _mqtt_client:
        _mqtt_client.publish(
            TOPIC_STATUS,
            json.dumps({"status": "offline", "timestamp": time.time()}),
            qos=1,
        )
        time.sleep(0.3)
        _mqtt_client.disconnect()
    if hasattr(motors, 'cleanup'):
        motors.cleanup()
    sys.exit(0)

def main():
    global motors, _servo, _periph, _mqtt_client

    print("=" * 55)
    print("  MQTT Device Controller - HiveMQ Cloud Mode")
    print(f"  Hardware: {'Raspberry Pi GPIO' if _HARDWARE_AVAILABLE else 'MOCK MODE'}")
    print("=" * 55)

    # Hardware or mock init
    if _HARDWARE_AVAILABLE:
        motors.setup()
        _servo = ServoController()
        _periph = Peripherals()
    else:
        mock = _MockMotors()
        motors = mock
        _servo = _MockServo()
        _periph = _MockPeriph()

    # MQTT client with cloud mode
    manager = ConnectionManager(config_path=_CONFIG_PATH)
    _mqtt_client = manager.build_client(
        client_id="surveillance-car-pi-cloud",
        on_connect=_on_connect,
        on_disconnect=_on_disconnect,
        on_message=_on_message,
    )
    
    # Set will message
    _mqtt_client.will_set(
        TOPIC_STATUS,
        json.dumps({"status": "offline", "reason": "unexpected disconnect"}),
        qos=1, retain=True,
    )
    
    # Connect to cloud broker
    print("[DEVICE] Connecting to HiveMQ cloud broker...")
    manager.connect(_mqtt_client, mode="cloud")
    _mqtt_client.loop_start()

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    print("[DEVICE] Ready — waiting for MQTT commands from HiveMQ...")
    while True:
        time.sleep(1)

if __name__ == "__main__":
    main()
