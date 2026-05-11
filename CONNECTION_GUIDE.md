# 🔐 Connection Guide - Your Custom MQTT Broker

## Default Credentials

Your custom MQTT broker requires authentication (just like HiveMQ Cloud):

```
Username: admin
Password: surveillance2024
```

## Connection Information

### When Running Locally

```
URL: mqtt://localhost:1883
Username: admin
Password: surveillance2024
```

### When Running with Ngrok (WAN Access)

After starting the system with `./run.sh`, you'll see:

```
======================================================================
🌐 NGROK WAN TUNNELS ACTIVE
======================================================================
📡 MQTT Broker (TCP): tcp://0.tcp.ngrok.io:12345
======================================================================

📋 MQTT BROKER CONNECTION INFO
======================================================================
Local URL: mqtt://localhost:1883
Username: admin
Password: surveillance2024
Authentication: Required
======================================================================
```

**Use these for WAN access:**
```
URL: tcp://0.tcp.ngrok.io:12345  (your actual URL will be different)
Username: admin
Password: surveillance2024
```

---

## 🧪 Testing from Another Laptop

### Option 1: MQTT Client (Command Line)

**Install MQTT client:**
```bash
# Windows
choco install mosquitto

# Mac
brew install mosquitto

# Linux
sudo apt-get install mosquitto-clients
```

**Connect and test:**
```bash
# Subscribe to all topics
mosquitto_sub -h 0.tcp.ngrok.io -p 12345 -u admin -P surveillance2024 -t 'dev/#' -v

# Publish a command
mosquitto_pub -h 0.tcp.ngrok.io -p 12345 -u admin -P surveillance2024 -t dev/motor -m '{"command":"forward"}'
```

---

### Option 2: Python Script

Create `test_mqtt.py`:

```python
import paho.mqtt.client as mqtt
import time

# Your Ngrok URL (get from console output)
MQTT_HOST = "0.tcp.ngrok.io"  # Replace with your URL
MQTT_PORT = 12345              # Replace with your port
MQTT_USERNAME = "admin"
MQTT_PASSWORD = "surveillance2024"

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ Connected successfully!")
        client.subscribe("dev/#")
        print("📡 Subscribed to dev/#")
    else:
        print(f"❌ Connection failed with code {rc}")
        if rc == 5:
            print("   Authentication failed - check username/password")

def on_message(client, userdata, msg):
    print(f"📨 Received: {msg.topic} -> {msg.payload.decode()}")

# Create client
client = mqtt.Client("laptop_test_client")

# Set credentials
client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

# Set callbacks
client.on_connect = on_connect
client.on_message = on_message

# Connect
print(f"🔌 Connecting to {MQTT_HOST}:{MQTT_PORT}...")
print(f"👤 Username: {MQTT_USERNAME}")

try:
    client.connect(MQTT_HOST, MQTT_PORT, 60)
    client.loop_start()
    
    # Wait for connection
    time.sleep(2)
    
    # Send test commands
    print("\n🚗 Sending motor commands...")
    client.publish("dev/motor", '{"command":"forward"}')
    time.sleep(1)
    client.publish("dev/motor", '{"command":"stop"}')
    time.sleep(1)
    client.publish("dev/motor", '{"command":"backward"}')
    
    # Keep running
    print("\n✅ Test complete! Press Ctrl+C to exit...")
    while True:
        time.sleep(1)
        
except KeyboardInterrupt:
    print("\n👋 Disconnecting...")
    client.loop_stop()
    client.disconnect()
except Exception as e:
    print(f"❌ Error: {e}")
```

**Run it:**
```bash
pip install paho-mqtt
python test_mqtt.py
```

---

### Option 3: MQTT Explorer (GUI)

1. **Download MQTT Explorer**: http://mqtt-explorer.com/
2. **Create new connection:**
   - Name: `Raspberry Pi Car`
   - Protocol: `mqtt://`
   - Host: `0.tcp.ngrok.io` (your Ngrok URL)
   - Port: `12345` (your Ngrok port)
   - Username: `admin`
   - Password: `surveillance2024`
3. **Click "Connect"**
4. **Subscribe to** `dev/#`
5. **Publish messages** to `dev/motor`

---

### Option 4: Web Dashboard

1. **Copy `client_example.html`** to your laptop
2. **Open in browser**
3. **Enter WebSocket URL**: `wss://abc123.ngrok.io` (from console)
4. **Click "Connect"**
5. **Control the car!**

---

## 🔒 Changing Credentials

### Method 1: Environment Variables

```bash
MQTT_USERNAME=myuser MQTT_PASSWORD=mypass ./run.sh
```

### Method 2: Edit config.py

Edit `Raspi/Network/WebSockets/config.py`:

```python
MQTT_USERNAME = os.getenv("MQTT_USERNAME", "your_username")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "your_password")
```

---

## 📋 Connection Examples

### MQTT.fx

```
Broker Address: 0.tcp.ngrok.io
Broker Port: 12345
Client ID: laptop_client
User Name: admin
Password: surveillance2024
```

### Node-RED

```json
{
  "broker": "0.tcp.ngrok.io",
  "port": 12345,
  "clientid": "nodered_client",
  "username": "admin",
  "password": "surveillance2024"
}
```

### Arduino/ESP32

```cpp
#include <WiFi.h>
#include <PubSubClient.h>

const char* mqtt_server = "0.tcp.ngrok.io";
const int mqtt_port = 12345;
const char* mqtt_user = "admin";
const char* mqtt_password = "surveillance2024";

WiFiClient espClient;
PubSubClient client(espClient);

void setup() {
  client.setServer(mqtt_server, mqtt_port);
  
  if (client.connect("ESP32Client", mqtt_user, mqtt_password)) {
    Serial.println("Connected!");
    client.subscribe("dev/#");
  }
}
```

### Python (Paho MQTT)

```python
import paho.mqtt.client as mqtt

client = mqtt.Client()
client.username_pw_set("admin", "surveillance2024")
client.connect("0.tcp.ngrok.io", 12345, 60)
client.subscribe("dev/#")
client.publish("dev/motor", "forward")
```

### JavaScript (MQTT.js)

```javascript
const mqtt = require('mqtt');

const client = mqtt.connect('mqtt://0.tcp.ngrok.io:12345', {
  username: 'admin',
  password: 'surveillance2024'
});

client.on('connect', () => {
  console.log('Connected!');
  client.subscribe('dev/#');
  client.publish('dev/motor', 'forward');
});
```

---

## ❌ Troubleshooting

### Authentication Failed

**Error:** `Connection refused: Bad user name or password`

**Solution:**
- Check username: `admin`
- Check password: `surveillance2024`
- Make sure you're using `-u` and `-P` flags in mosquitto_pub/sub

### Connection Timeout

**Error:** `Connection timeout`

**Solution:**
- Check Ngrok URL is correct
- Verify Raspberry Pi system is running
- Check internet connection

### Connection Refused

**Error:** `Connection refused`

**Solution:**
- Make sure the system is running: `./run.sh`
- Check if broker started successfully
- Verify port number matches

---

## 📊 Connection Status

### Check if Broker is Running

On Raspberry Pi:
```bash
# Check if process is running
ps aux | grep custom_mqtt_broker

# Check logs
sudo journalctl -u surveillance-car -f
```

### Test Local Connection

On Raspberry Pi:
```bash
mosquitto_pub -h localhost -p 1883 -u admin -P surveillance2024 -t test -m "hello"
```

---

## 🔐 Security Notes

### For Production:

1. **Change default credentials** immediately
2. **Use strong passwords** (16+ characters)
3. **Enable TLS/SSL** for encrypted connections
4. **Restrict topics** per user
5. **Monitor failed login attempts**

### Example Strong Password:

```bash
MQTT_PASSWORD=$(openssl rand -base64 32)
echo "Your password: $MQTT_PASSWORD"
```

---

## 📝 Quick Reference Card

```
╔════════════════════════════════════════════════════════════╗
║         RASPBERRY PI SURVEILLANCE CAR - MQTT ACCESS        ║
╠════════════════════════════════════════════════════════════╣
║                                                            ║
║  WAN URL:  tcp://0.tcp.ngrok.io:12345                     ║
║  Username: admin                                           ║
║  Password: surveillance2024                                ║
║                                                            ║
║  Topics:                                                   ║
║    dev/motor   - Motor control                            ║
║    dev/status  - System status                            ║
║    dev/control - General control                          ║
║                                                            ║
║  Example:                                                  ║
║    mosquitto_pub -h 0.tcp.ngrok.io -p 12345 \            ║
║      -u admin -P surveillance2024 \                       ║
║      -t dev/motor -m "forward"                            ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝
```

---

**Your custom MQTT broker with authentication is ready!** 🎉

Just like HiveMQ Cloud, but it's YOUR own broker! 🚀
