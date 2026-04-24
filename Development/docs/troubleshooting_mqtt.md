# Troubleshooting MQTT

Common problems and solutions for the IoT Surveillance Car MQTT system.

---

## Connection Issues

### ❌ `Connection refused` on port 1883

**Cause:** Mosquitto is not running or is bound to a different interface.

**Fix:**
```bash
sudo systemctl status mosquitto
sudo systemctl restart mosquitto
```

Check that `mosquitto.conf` contains:
```
listener 1883
allow_anonymous true
```

---

### ❌ GUI shows "Disconnected" immediately

**Cause:** Wrong broker IP in `server_profiles.json`.

**Fix:**
1. Run `python utils/network_scanner.py` to find your LAN IP.
2. Update `config/server_profiles.json` → `local.host`.
3. Restart the GUI.

---

### ❌ Pi connects but GUI receives no status messages

**Cause:** Both devices are on different brokers (one local, one cloud).

**Fix:** Ensure both the Pi (`mqtt_device_controller.py`) and the GUI
(`mqtt_gui_controller.py`) point to the **same** broker host.

---

### ❌ `paho.mqtt` not found

**Fix:**
```bash
pip install paho-mqtt==1.6.1
```

---

## Motor / Hardware Issues

### ❌ Motors don't move after receiving a command

**Possible causes:**
- GPIO pins in `config.py` don't match your wiring
- L298N `ENA`/`ENB` pins not connected to PWM-capable GPIO pins
- Power supply insufficient for motors

**Fix:**
1. Double-check `ENA_PIN`, `ENB_PIN`, `IN1_PIN`–`IN4_PIN` in `config.py`.
2. Verify the L298N is powered (separate 12V supply recommended).
3. Test with `python debug_mqtt_controller.py` first — if messages arrive
   but motors don't move, the issue is hardware, not MQTT.

---

### ❌ Fail-safe triggers immediately

**Cause:** The watchdog timeout (2 s) fires before the first command arrives.

**Fix:** The watchdog resets on the first received command. If it keeps
triggering, check that the GUI is connected and publishing to `dev/motor`.

---

## Message Issues

### ❌ `Invalid JSON` error in logs

**Cause:** A publisher is sending malformed JSON.

**Fix:** Use `message_validator.py` to validate payloads before publishing:
```python
from utils.message_validator import validate_motor_command
ok, err = validate_motor_command({"direction": "forward", "speed": 80})
```

---

### ❌ Commands arrive but are ignored

**Cause:** Unknown `direction` or `command` value.

**Valid directions:** `forward` `backward` `left` `right` `stop`

**Valid commands:** `FORWARD` `BACKWARD` `LEFT` `RIGHT` `STOP` `SERVO` `LED_ON` `LED_OFF` `BEEP`

---

## Testing Without Hardware

Run the debug controller on any machine (no GPIO needed):

```bash
python debug_mqtt_controller.py
```

Then send commands from another terminal:

```bash
python mqtt_client_tester.py forward 80
python mqtt_client_tester.py stop
```

Or run the full automated test sequence:

```bash
python utils/batch_commands.py
```

---

## Useful Diagnostic Commands

```bash
# Watch all messages on all topics
mosquitto_sub -h 192.168.1.100 -t "#" -v

# Publish a test motor command
mosquitto_pub -h 192.168.1.100 -t "dev/motor" \
  -m '{"direction": "forward", "speed": 80}'

# Check broker is reachable
python utils/connection_test.py

# Run all tests
pytest Development/tests/ -v
```
