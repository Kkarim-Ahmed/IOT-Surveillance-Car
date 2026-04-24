# MQTT API Reference

Complete reference for all MQTT topics, message formats, and expected
behaviour in the IoT Surveillance Car system.

---

## Broker

| Mode  | Host                  | Port |
|-------|-----------------------|------|
| Local | `192.168.1.100`       | 1883 |
| Cloud | `broker.hivemq.com`   | 1883 |

Broker settings are stored in `config/server_profiles.json`.

---

## Topics

| Topic          | Direction     | Description                        |
|----------------|---------------|------------------------------------|
| `dev/motor`    | GUI → Pi      | Motor direction and speed          |
| `dev/led`      | GUI → Pi      | LED on / off / blink               |
| `dev/commands` | GUI → Pi      | Servo, beep, and system commands   |
| `dev/status`   | Pi → GUI      | Acknowledgements and fail-safe alerts |

---

## Message Formats

### `dev/motor` — Motor control

```json
{
  "direction": "forward",
  "speed": 80
}
```

| Field       | Type   | Values                                      | Required |
|-------------|--------|---------------------------------------------|----------|
| `direction` | string | `forward` `backward` `left` `right` `stop` | ✅ Yes   |
| `speed`     | int    | 0 – 100 (PWM duty cycle %)                  | Optional (default 80) |

---

### `dev/led` — LED control

```json
{ "state": "on" }
```

| Field   | Type   | Values              |
|---------|--------|---------------------|
| `state` | string | `on` `off` `blink`  |

---

### `dev/commands` — System commands

```json
{
  "command": "SERVO",
  "angle": 90,
  "speed": 80
}
```

| Field     | Type   | Values                                                    | Required |
|-----------|--------|-----------------------------------------------------------|----------|
| `command` | string | `FORWARD` `BACKWARD` `LEFT` `RIGHT` `STOP` `SERVO` `LED_ON` `LED_OFF` `BEEP` | ✅ Yes |
| `angle`   | int    | 0 – 180 (degrees, used with `SERVO`)                      | Optional |
| `speed`   | int    | 0 – 100                                                   | Optional |

---

### `dev/status` — Pi status / acknowledgement

```json
{
  "command": "forward",
  "speed": 80,
  "servo": 90,
  "timestamp": 1714000000.0
}
```

Fail-safe alert format:

```json
{
  "type": "failsafe",
  "message": "No command received — motors stopped",
  "elapsed": 2.3,
  "timestamp": 1714000000.0
}
```

---

## Fail-Safe Behaviour

If no message is received on `dev/motor` or `dev/commands` for **2 seconds**,
the Pi automatically:

1. Stops all motors
2. Triggers the buzzer alert
3. Publishes a `failsafe` message to `dev/status`

The watchdog resets as soon as the next command arrives.

---

## QoS Levels

| Topic          | QoS | Reason                              |
|----------------|-----|-------------------------------------|
| `dev/motor`    | 1   | Reliable delivery for movement      |
| `dev/led`      | 1   | Reliable delivery                   |
| `dev/commands` | 1   | Reliable delivery                   |
| `dev/status`   | 0   | High-frequency, loss acceptable     |
