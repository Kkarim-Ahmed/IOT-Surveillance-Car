# Client Setup Guide

Step-by-step instructions for setting up and running the MQTT
surveillance car system on your laptop and Raspberry Pi.

---

## What is MQTT?

MQTT (Message Queuing Telemetry Transport) is a lightweight
publish/subscribe messaging protocol designed for IoT devices.

- A **broker** sits in the middle and routes messages
- **Publishers** send messages to a topic (e.g. the GUI sends to `dev/motor`)
- **Subscribers** receive messages from a topic (e.g. the Pi listens on `dev/motor`)

This project uses [Mosquitto](https://mosquitto.org/) as the local broker
and [HiveMQ](https://www.hivemq.com/public-mqtt-broker/) as the cloud broker.

---

## Prerequisites

| Component     | Requirement                        |
|---------------|------------------------------------|
| Laptop        | Python 3.8+, `paho-mqtt`           |
| Raspberry Pi  | Python 3.8+, `paho-mqtt`, `RPi.GPIO` |
| Broker        | Mosquitto (local) or HiveMQ (cloud)|

---

## Phase 1 — Local Network Setup

### Step 1: Install the broker (laptop or Pi)

```bash
chmod +x setup/setup_mqtt_broker.sh
./setup/setup_mqtt_broker.sh
```

Or manually:

```bash
sudo apt-get install -y mosquitto mosquitto-clients
sudo systemctl enable mosquitto
sudo systemctl start mosquitto
```

### Step 2: Install Python dependencies (laptop)

```bash
chmod +x setup/install_client.sh
./setup/install_client.sh
```

Or manually:

```bash
pip install paho-mqtt==1.6.1
```

### Step 3: Configure the broker IP

Edit `config/server_profiles.json` and set `local.host` to your
machine's LAN IP. Find it with:

```bash
python utils/network_scanner.py
```

### Step 4: Test the connection

```bash
python utils/connection_test.py
```

### Step 5: Start the debug controller (no hardware needed)

```bash
python debug_mqtt_controller.py
```

### Step 6: Send a test command

```bash
python mqtt_client_tester.py forward 80
```

### Step 7: Start the full GUI

```bash
python mqtt_gui_controller.py
```

---

## Phase 2 — WAN / Cloud Setup

1. Change the broker mode to **Cloud** in the GUI radio button, or
2. Edit `config/server_profiles.json` and point `cloud.host` to your
   private broker, then enable TLS in `client_config.json`.

No other changes are needed — `connection_manager.py` handles switching.

---

## Running on the Raspberry Pi

```bash
cd raspberry-pi
python mqtt_device_controller.py
```

The Pi will:
- Connect to the broker
- Subscribe to `dev/motor`, `dev/led`, `dev/commands`
- Execute hardware commands via GPIO
- Publish status to `dev/status`
- Trigger the fail-safe if no command arrives for 2 seconds

---

## Running Tests

```bash
pip install pytest
pytest Development/tests/ -v
```
