#!/usr/bin/env python3
"""
HiveMQ Connection Tester
Auto-generated script to test HiveMQ connection
"""

import paho.mqtt.client as mqtt
import ssl
import json
import time

# HiveMQ Configuration
HIVEMQ_HOST = "78ed3eab06c348d0948ef7681cf4a377.s1.eu.hivemq.cloud"
HIVEMQ_PORT = 8883
HIVEMQ_USERNAME = "mohamed"
HIVEMQ_PASSWORD = "P@ssw0rd"

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ Connected to HiveMQ!")
        client.subscribe("dev/status")
        # Send test command
        test_cmd = {"direction": "forward", "speed": 50}
        client.publish("dev/motor", json.dumps(test_cmd))
        print("📤 Sent test motor command")
    else:
        print(f"❌ Connection failed: {rc}")

def on_message(client, userdata, msg):
    print(f"📨 {msg.topic}: {msg.payload.decode()}")

def main():
    client = mqtt.Client()
    client.username_pw_set(HIVEMQ_USERNAME, HIVEMQ_PASSWORD)
    
    # Configure TLS
    client.tls_set(ca_certs=None, certfile=None, keyfile=None,
                  cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLS)
    
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        print(f"🌐 Connecting to HiveMQ: {HIVEMQ_HOST}")
        client.connect(HIVEMQ_HOST, HIVEMQ_PORT, 60)
        client.loop_forever()
    except KeyboardInterrupt:
        print("\n👋 Disconnecting...")
        client.disconnect()

if __name__ == "__main__":
    main()
