"""
mqtt_client_tester.py — CLI tool for publishing test MQTT commands.

Lets you quickly send motor commands to the surveillance car from the
terminal without needing the full GUI.

Usage:
    python mqtt_client_tester.py                  # interactive menu
    python mqtt_client_tester.py forward 80       # single command
    python mqtt_client_tester.py stop

Commands: forward | backward | left | right | stop
"""

import json
import sys
import time

import paho.mqtt.client as mqtt

# ── Broker settings ────────────────────────────────────────────────────────────
BROKER_HOST = "broker.hivemq.com"
BROKER_PORT = 1883
CLIENT_ID   = "mqtt-client-tester"

TOPIC_MOTOR  = "dev/motor"
TOPIC_STATUS = "dev/status"

VALID_DIRECTIONS = ("forward", "backward", "left", "right", "stop")


# ── Helpers ────────────────────────────────────────────────────────────────────

def build_payload(direction: str, speed: int = 80) -> str:
    return json.dumps({"direction": direction, "speed": speed})


def publish_command(client: mqtt.Client, direction: str, speed: int = 80):
    payload = build_payload(direction, speed)
    result  = client.publish(TOPIC_MOTOR, payload, qos=1)
    result.wait_for_publish()
    print(f"[TESTER] → {TOPIC_MOTOR}: {payload}")


# ── Status callback ────────────────────────────────────────────────────────────

def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode())
        print(f"[TESTER] ← status: {data}")
    except Exception:
        pass


# ── Interactive menu ───────────────────────────────────────────────────────────

MENU = """
┌─────────────────────────────┐
│   MQTT Client Tester        │
│  Broker: {host}:{port}      │
├─────────────────────────────┤
│  1) forward                 │
│  2) backward                │
│  3) left                    │
│  4) right                   │
│  5) stop                    │
│  q) quit                    │
└─────────────────────────────┘
"""

MENU_MAP = {
    "1": "forward",
    "2": "backward",
    "3": "left",
    "4": "right",
    "5": "stop",
}


def interactive_mode(client: mqtt.Client):
    print(MENU.format(host=BROKER_HOST, port=BROKER_PORT))
    while True:
        choice = input("Command (1-5 / q): ").strip().lower()
        if choice == "q":
            print("[TESTER] Bye!")
            break
        direction = MENU_MAP.get(choice) or (choice if choice in VALID_DIRECTIONS else None)
        if direction is None:
            print(f"  Unknown command. Choose 1-5 or type a direction.")
            continue
        speed_str = input(f"  Speed (0-100) [80]: ").strip()
        speed = int(speed_str) if speed_str.isdigit() else 80
        speed = max(0, min(100, speed))
        publish_command(client, direction, speed)


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    client = mqtt.Client(client_id=CLIENT_ID, clean_session=True)
    client.on_message = on_message

    print(f"[TESTER] Connecting to {BROKER_HOST}:{BROKER_PORT}...")
    client.connect(BROKER_HOST, BROKER_PORT, keepalive=30)
    client.subscribe(TOPIC_STATUS, qos=1)
    client.loop_start()
    time.sleep(0.5)   # wait for connection to settle

    # CLI mode: python mqtt_client_tester.py forward 80
    if len(sys.argv) >= 2:
        direction = sys.argv[1].lower()
        speed     = int(sys.argv[2]) if len(sys.argv) >= 3 else 80
        if direction not in VALID_DIRECTIONS:
            print(f"[TESTER] Unknown direction '{direction}'. Use: {VALID_DIRECTIONS}")
            sys.exit(1)
        publish_command(client, direction, speed)
        time.sleep(0.5)
    else:
        interactive_mode(client)

    client.loop_stop()
    client.disconnect()


if __name__ == "__main__":
    main()
