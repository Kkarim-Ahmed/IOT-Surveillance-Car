"""
batch_commands.py — Send a sequence of MQTT motor commands with delays.

Useful for automated demos, testing movement sequences, or scripted
runs without needing the GUI.

Usage:
    python batch_commands.py                  # run built-in demo sequence
    python batch_commands.py forward stop     # custom sequence (equal delays)
"""

import json
import sys
import time

import paho.mqtt.client as mqtt

# ── Broker settings ────────────────────────────────────────────────────────────
BROKER_HOST = "broker.hivemq.com"
BROKER_PORT = 1883
CLIENT_ID   = "batch-commander"
TOPIC_MOTOR = "dev/motor"

# ── Default demo sequence: (direction, speed, duration_seconds) ───────────────
DEFAULT_SEQUENCE = [
    ("forward",  80, 1.5),
    ("stop",      0, 0.5),
    ("left",     60, 1.0),
    ("stop",      0, 0.5),
    ("right",    60, 1.0),
    ("stop",      0, 0.5),
    ("backward", 70, 1.5),
    ("stop",      0, 0.5),
]


def publish(client: mqtt.Client, direction: str, speed: int):
    payload = json.dumps({"direction": direction, "speed": speed})
    client.publish(TOPIC_MOTOR, payload, qos=1)
    print(f"[BATCH] → {direction:10s}  speed={speed}")


def run_sequence(client: mqtt.Client, sequence: list):
    """
    Execute a list of (direction, speed, duration) tuples.
    Publishes each command, waits for the duration, then moves to the next.
    """
    print(f"[BATCH] Running {len(sequence)} commands...")
    print("-" * 40)
    for direction, speed, duration in sequence:
        publish(client, direction, speed)
        time.sleep(duration)
    print("-" * 40)
    print("[BATCH] Sequence complete.")


def main():
    client = mqtt.Client(client_id=CLIENT_ID, clean_session=True)

    print(f"[BATCH] Connecting to {BROKER_HOST}:{BROKER_PORT}...")
    client.connect(BROKER_HOST, BROKER_PORT, keepalive=30)
    client.loop_start()
    time.sleep(0.5)

    if len(sys.argv) > 1:
        # Build a simple sequence from CLI args: each direction runs for 1s at speed 80
        sequence = [(d.lower(), 80, 1.0) for d in sys.argv[1:]]
        sequence.append(("stop", 0, 0.3))   # always end with stop
    else:
        sequence = DEFAULT_SEQUENCE

    run_sequence(client, sequence)

    client.loop_stop()
    client.disconnect()


if __name__ == "__main__":
    main()
