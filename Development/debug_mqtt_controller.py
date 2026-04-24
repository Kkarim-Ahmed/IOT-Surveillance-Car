"""
debug_mqtt_controller.py — Mock MQTT device controller for testing.

Subscribes to the same topics as mqtt_device_controller.py but prints
received messages instead of controlling any hardware. Safe to run on
any machine (no GPIO required).

Usage:
    python debug_mqtt_controller.py
"""

import json
import time
import signal
import sys

import paho.mqtt.client as mqtt

# ── Broker settings (edit to match your setup) ────────────────────────────────
BROKER_HOST = "broker.hivemq.com"
BROKER_PORT = 1883
CLIENT_ID   = "debug-device-controller"

# ── Topics ────────────────────────────────────────────────────────────────────
TOPIC_MOTOR    = "dev/motor"
TOPIC_LED      = "dev/led"
TOPIC_COMMANDS = "dev/commands"
TOPIC_STATUS   = "dev/status"


# ── MQTT callbacks ─────────────────────────────────────────────────────────────

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"[DEBUG] Connected to {BROKER_HOST}:{BROKER_PORT}")
        client.subscribe([(TOPIC_MOTOR, 1), (TOPIC_LED, 1), (TOPIC_COMMANDS, 1)])
        print(f"[DEBUG] Subscribed to: {TOPIC_MOTOR}, {TOPIC_LED}, {TOPIC_COMMANDS}")
        client.publish(TOPIC_STATUS, json.dumps({"status": "debug-online"}), qos=1)
    else:
        print(f"[DEBUG] Connection failed, rc={rc}")


def on_disconnect(client, userdata, rc):
    print(f"[DEBUG] Disconnected (rc={rc})")


def on_message(client, userdata, msg):
    """Print every incoming message instead of executing hardware commands."""
    try:
        payload = json.loads(msg.payload.decode("utf-8"))
        print(f"[DEBUG] ← {msg.topic}: {json.dumps(payload, indent=2)}")

        # Simulate what the real controller would do
        if msg.topic == TOPIC_MOTOR:
            direction = payload.get("direction", "?")
            speed     = payload.get("speed", "?")
            print(f"  → [MOCK MOTOR] direction={direction}  speed={speed}")

        elif msg.topic == TOPIC_LED:
            state = payload.get("state", "?")
            print(f"  → [MOCK LED] state={state}")

        elif msg.topic == TOPIC_COMMANDS:
            command = payload.get("command", "?")
            print(f"  → [MOCK CMD] command={command}")

        # Echo back a status acknowledgement
        ack = {"ack": msg.topic, "received": payload, "timestamp": time.time()}
        client.publish(TOPIC_STATUS, json.dumps(ack), qos=0)

    except json.JSONDecodeError:
        print(f"[DEBUG] Non-JSON message on {msg.topic}: {msg.payload}")
    except Exception as e:
        print(f"[DEBUG] Error: {e}")


# ── Graceful shutdown ──────────────────────────────────────────────────────────

def shutdown(signum, frame):
    print("\n[DEBUG] Shutting down...")
    client.publish(TOPIC_STATUS, json.dumps({"status": "debug-offline"}), qos=1)
    time.sleep(0.3)
    client.disconnect()
    sys.exit(0)


# ── Main ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 50)
    print("  MQTT Debug Controller (no hardware)")
    print("=" * 50)

    client = mqtt.Client(client_id=CLIENT_ID, clean_session=True)
    client.on_connect    = on_connect
    client.on_disconnect = on_disconnect
    client.on_message    = on_message

    signal.signal(signal.SIGINT,  shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    print(f"[DEBUG] Connecting to {BROKER_HOST}:{BROKER_PORT}...")
    client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
    client.loop_forever()
