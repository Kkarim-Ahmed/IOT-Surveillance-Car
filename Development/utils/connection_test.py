"""
connection_test.py — Test MQTT broker connectivity and print result.

Tries to connect to both the local and cloud brokers defined in
server_profiles.json and reports success or failure for each.

Usage:
    python connection_test.py
    python connection_test.py 192.168.1.100 1883   # test a specific broker
"""

import json
import os
import sys
import time

import paho.mqtt.client as mqtt

# ── Load profiles ──────────────────────────────────────────────────────────────
_PROFILES_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "server_profiles.json")

def _load_profiles() -> dict:
    try:
        with open(_PROFILES_PATH) as f:
            data = json.load(f)
        # Strip comment keys
        return {k: v for k, v in data.items() if not k.startswith("_")}
    except Exception:
        return {
            "local": {"host": "192.168.1.100", "port": 1883},
            "cloud": {"host": "broker.hivemq.com", "port": 1883},
        }


# ── Single broker test ─────────────────────────────────────────────────────────

def test_broker(host: str, port: int, timeout: float = 5.0) -> bool:
    """
    Attempt to connect to an MQTT broker.

    Returns True if connection succeeds within timeout, False otherwise.
    """
    result = {"connected": False}

    def on_connect(client, userdata, flags, rc):
        result["connected"] = (rc == 0)
        client.disconnect()

    client = mqtt.Client(client_id="connection-tester", clean_session=True)
    client.on_connect = on_connect

    try:
        client.connect(host, port, keepalive=10)
        client.loop_start()
        deadline = time.time() + timeout
        while time.time() < deadline and not result["connected"]:
            time.sleep(0.1)
        client.loop_stop()
    except Exception as e:
        print(f"  [ERROR] {e}")
        return False

    return result["connected"]


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print("=" * 50)
    print("  MQTT Connection Test")
    print("=" * 50)

    # CLI override: python connection_test.py <host> <port>
    if len(sys.argv) == 3:
        host = sys.argv[1]
        port = int(sys.argv[2])
        print(f"\n  Testing {host}:{port} ...")
        ok = test_broker(host, port)
        status = "✓ SUCCESS" if ok else "✗ FAILED"
        print(f"  Result: {status}\n")
        sys.exit(0 if ok else 1)

    # Test all profiles
    profiles = _load_profiles()
    all_ok   = True

    for name, cfg in profiles.items():
        host = cfg.get("host", "?")
        port = int(cfg.get("port", 1883))
        print(f"\n  [{name}] {host}:{port}")
        print(f"  Testing...", end=" ", flush=True)
        ok = test_broker(host, port)
        if ok:
            print("✓ Connected successfully")
        else:
            print("✗ Connection failed")
            all_ok = False

    print()
    print("=" * 50)
    overall = "ALL BROKERS REACHABLE" if all_ok else "SOME BROKERS UNREACHABLE"
    print(f"  Result: {overall}")
    print("=" * 50)
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
