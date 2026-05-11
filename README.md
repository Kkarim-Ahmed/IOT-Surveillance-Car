# Raspberry Pi Surveillance Car - Self-Hosted MQTT + WebSocket Infrastructure

A complete, production-quality self-hosted WAN-ready MQTT + WebSocket infrastructure for IoT surveillance car control with real-time video/audio streaming.

## 🎯 Features

✅ **Self-Hosted MQTT Broker** (Eclipse Mosquitto)  
✅ **WAN Access via Ngrok** (no port forwarding needed)  
✅ **Real-Time Video Streaming** (WebSocket + OpenCV)  
✅ **Real-Time Audio Streaming** (WebSocket + PyAudio)  
✅ **MQTT ↔ WebSocket Bridge** (bidirectional communication)  
✅ **Low-Latency Optimized** (async architecture)  
✅ **Raspberry Pi Compatible**  
✅ **Modular Architecture**  
✅ **Production-Ready**

## 🏗️ Architecture

```
Web Dashboard / Laptop
         ↓
   Ngrok WAN Tunnel
         ↓
WebSocket Server + MQTT Broker
         ↓
   Raspberry Pi
         ↓
Motors + Camera + Audio
```

## 📁 Project Structure

```
Final/
├── Raspi/
│   ├── Network/
│   │   └── WebSockets/
│   │       ├── __init__.py
│   │       ├── config.py              # Centralized configuration
│   │       ├── main.py                # Main entry point
│   │       ├── websocket_server.py    # WebSocket server
│   │       ├── video_stream_handler.py # Video streaming
│   │       ├── audio_system.py        # Audio streaming
│   │       └── ngrok_manager.py       # Ngrok tunnel management
│   └── MQTT/
│       ├── __init__.py
│       ├── mqtt_device_controller.py  # Device controller
│       ├── connection_manager.py      # MQTT connection
│       └── mosquitto.conf             # Mosquitto config
├── requirements.txt                    # Python dependencies
├── setup.sh                           # Installation script
└── README.md                          # This file
```

## 🚀 Quick Start

### 1. Installation

```bash
# Clone or download the project
cd Final

# Run setup script (installs everything)
chmod +x setup.sh
./setup.sh
```

The setup script will:
- Install system dependencies
- Install Mosquitto MQTT broker
- Install Ngrok
- Create Python virtual environment
- Install Python packages
- Configure Mosquitto
- Create systemd service

### 2. Configure Ngrok (Required for WAN access)

Get your free auth token from [ngrok.com](https://ngrok.com)

```bash
export NGROK_AUTH_TOKEN=your_token_here
ngrok config add-authtoken $NGROK_AUTH_TOKEN
```

### 3. Start the System

**Option A: Direct execution**
```bash
./run.sh
```

**Option B: Systemd service**
```bash
sudo systemctl start surveillance-car
sudo systemctl status surveillance-car
```

**Option C: Manual**
```bash
source venv/bin/activate
python -m Raspi.Network.WebSockets.main
```

### 4. Verify System

The system will display:
```
======================================================================
🌐 NGROK WAN TUNNELS ACTIVE
======================================================================
📡 MQTT Broker (TCP): tcp://0.tcp.ngrok.io:12345
   Connect with: mqtt://0.tcp.ngrok.io:12345
🔌 WebSocket Server: wss://abc123.ngrok.io
   Connect with: wss://abc123.ngrok.io
======================================================================

🚀 SYSTEM READY - All services running
```

## ⚙️ Configuration

All settings are in `Raspi/Network/WebSockets/config.py`

### Environment Variables

Override any setting with environment variables:

```bash
# WebSocket settings
export WS_PORT=9000
export WS_HOST=0.0.0.0

# MQTT settings
export MQTT_BROKER_HOST=localhost
export MQTT_BROKER_PORT=1883

# Video settings
export VIDEO_WIDTH=640
export VIDEO_HEIGHT=480
export VIDEO_FPS=15
export VIDEO_JPEG_QUALITY=65

# Audio settings
export AUDIO_SAMPLE_RATE=16000
export AUDIO_CHANNELS=1

# Ngrok settings
export NGROK_ENABLED=true
export NGROK_AUTH_TOKEN=your_token
export NGROK_REGION=us

# Logging
export LOG_LEVEL=INFO
```

### Example: Custom Configuration

```bash
# High quality video
VIDEO_JPEG_QUALITY=85 VIDEO_FPS=30 python -m Raspi.Network.WebSockets.main

# Disable audio
AUDIO_ENABLED=false python -m Raspi.Network.WebSockets.main

# Different MQTT broker
MQTT_BROKER_HOST=192.168.1.100 python -m Raspi.Network.WebSockets.main
```

## 📡 MQTT Topics

The system uses the following MQTT topics:

| Topic | Direction | Purpose |
|-------|-----------|---------|
| `dev/motor` | Bidirectional | Motor control commands |
| `dev/status` | Bidirectional | System status updates |
| `dev/control` | Subscribe | General control commands |
| `dev/audio` | Publish | Audio metadata |
| `dev/video` | Publish | Video metadata |

### Example MQTT Commands

**Control motors:**
```bash
mosquitto_pub -h localhost -t dev/motor -m '{"command":"forward"}'
mosquitto_pub -h localhost -t dev/motor -m '{"command":"stop"}'
```

**Request status:**
```bash
mosquitto_pub -h localhost -t dev/status -m '{"command":"get_status"}'
```

**Subscribe to all topics:**
```bash
mosquitto_sub -h localhost -t 'dev/#' -v
```

## 🔌 WebSocket Protocol

### Binary Packet Format

All WebSocket messages use a tagged binary protocol:

```
[TAG_BYTE][DATA]
```

**Packet Tags:**
- `0x00` - JSON/MQTT events
- `0x01` - Video frames (JPEG)
- `0x02` - Audio chunks (PCM)

### Client → Server Messages (JSON)

**Publish to MQTT:**
```json
{
  "type": "mqtt_publish",
  "topic": "dev/motor",
  "payload": "forward"
}
```

**Send command:**
```json
{
  "type": "command",
  "command": "motor",
  "params": {
    "direction": "forward"
  }
}
```

**Get statistics:**
```json
{
  "type": "get_stats"
}
```

### Server → Client Messages

**Welcome message:**
```json
{
  "type": "welcome",
  "message": "Connected to Raspberry Pi Surveillance Car",
  "video_enabled": true,
  "audio_enabled": true
}
```

**MQTT message:**
```json
{
  "type": "mqtt_message",
  "topic": "dev/motor",
  "payload": "{\"state\":\"forward\"}"
}
```

**Statistics:**
```json
{
  "type": "stats",
  "clients": 2,
  "video": {
    "fps": 15,
    "frames_sent": 1500,
    "frames_dropped": 5
  },
  "audio": {
    "chunks_sent": 3000,
    "chunks_dropped": 10
  }
}
```

## 🌐 Web Client Example

```html
<!DOCTYPE html>
<html>
<head>
    <title>Surveillance Car Control</title>
</head>
<body>
    <h1>Raspberry Pi Surveillance Car</h1>
    
    <div>
        <video id="video" width="640" height="480" autoplay></video>
        <audio id="audio" autoplay></audio>
    </div>
    
    <div>
        <button onclick="sendCommand('forward')">Forward</button>
        <button onclick="sendCommand('backward')">Backward</button>
        <button onclick="sendCommand('left')">Left</button>
        <button onclick="sendCommand('right')">Right</button>
        <button onclick="sendCommand('stop')">Stop</button>
    </div>
    
    <script>
        // Connect to WebSocket (use your ngrok URL)
        const ws = new WebSocket('wss://your-ngrok-url.ngrok.io');
        
        // Video canvas
        const video = document.getElementById('video');
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        
        // Audio context
        const audioCtx = new AudioContext();
        
        ws.binaryType = 'arraybuffer';
        
        ws.onmessage = async (event) => {
            const data = new Uint8Array(event.data);
            const tag = data[0];
            const payload = data.slice(1);
            
            if (tag === 0x00) {
                // JSON message
                const json = JSON.parse(new TextDecoder().decode(payload));
                console.log('Message:', json);
            } else if (tag === 0x01) {
                // Video frame
                const blob = new Blob([payload], {type: 'image/jpeg'});
                const url = URL.createObjectURL(blob);
                const img = new Image();
                img.onload = () => {
                    canvas.width = img.width;
                    canvas.height = img.height;
                    ctx.drawImage(img, 0, 0);
                    video.src = canvas.toDataURL();
                    URL.revokeObjectURL(url);
                };
                img.src = url;
            } else if (tag === 0x02) {
                // Audio chunk
                playAudio(payload);
            }
        };
        
        function sendCommand(direction) {
            const msg = {
                type: 'mqtt_publish',
                topic: 'dev/motor',
                payload: JSON.stringify({command: direction})
            };
            ws.send(JSON.stringify(msg));
        }
        
        function playAudio(audioData) {
            // Decode PCM audio
            const audioBuffer = audioCtx.createBuffer(1, audioData.length / 2, 16000);
            const channelData = audioBuffer.getChannelData(0);
            
            const view = new DataView(audioData.buffer);
            for (let i = 0; i < audioData.length / 2; i++) {
                channelData[i] = view.getInt16(i * 2, true) / 32768.0;
            }
            
            const source = audioCtx.createBufferSource();
            source.buffer = audioBuffer;
            source.connect(audioCtx.destination);
            source.start();
        }
    </script>
</body>
</html>
```

## 🔧 Testing

### Test MQTT Broker

```bash
# Terminal 1: Subscribe
mosquitto_sub -h localhost -t 'dev/#' -v

# Terminal 2: Publish
mosquitto_pub -h localhost -t dev/motor -m 'test'
```

### Test WebSocket Server

```bash
# Install wscat
npm install -g wscat

# Connect to WebSocket
wscat -c ws://localhost:8765

# Send test message
{"type":"ping"}
```

### Test Video Capture

```python
import cv2

cap = cv2.VideoCapture(0)
ret, frame = cap.read()
if ret:
    print("Camera working!")
    cv2.imwrite('test.jpg', frame)
cap.release()
```

### Test Audio Capture

```python
import pyaudio

p = pyaudio.PyAudio()
stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True)
data = stream.read(1024)
print(f"Audio captured: {len(data)} bytes")
stream.close()
p.terminate()
```

## 📊 Monitoring

### View Logs

```bash
# Systemd service logs
sudo journalctl -u surveillance-car -f

# Mosquitto logs
sudo tail -f /var/log/mosquitto/mosquitto.log

# Application logs (if running directly)
python -m Raspi.Network.WebSockets.main
```

### System Status

```bash
# Check Mosquitto
sudo systemctl status mosquitto

# Check surveillance car service
sudo systemctl status surveillance-car

# Check Ngrok tunnels
curl http://localhost:4040/api/tunnels
```

## 🐛 Troubleshooting

### Camera not working

```bash
# Check camera
vcgencmd get_camera

# Test with raspistill
raspistill -o test.jpg

# Check permissions
sudo usermod -a -G video $USER
```

### Audio not working

```bash
# List audio devices
arecord -l

# Test recording
arecord -D plughw:1,0 -f S16_LE -r 16000 test.wav
```

### MQTT connection failed

```bash
# Check Mosquitto is running
sudo systemctl status mosquitto

# Check port is open
netstat -tuln | grep 1883

# Test connection
mosquitto_pub -h localhost -t test -m "hello"
```

### Ngrok not connecting

```bash
# Check auth token
ngrok config check

# Test manually
ngrok tcp 1883

# Check account limits
# Free accounts have connection limits
```

## 🔒 Security Notes

**For Production:**

1. **Enable MQTT Authentication:**
   ```bash
   sudo mosquitto_passwd -c /etc/mosquitto/passwd username
   ```
   
   Update `mosquitto.conf`:
   ```
   allow_anonymous false
   password_file /etc/mosquitto/passwd
   ```

2. **Use TLS/SSL:**
   - Configure Mosquitto with certificates
   - Use WSS (WebSocket Secure)

3. **Implement Access Control:**
   - Configure ACL in `mosquitto.conf`
   - Restrict topic access per user

4. **Firewall Rules:**
   ```bash
   sudo ufw allow 1883/tcp
   sudo ufw allow 8765/tcp
   sudo ufw enable
   ```

## 📈 Performance Tuning

### High FPS Video

```bash
VIDEO_FPS=30 VIDEO_JPEG_QUALITY=70 python -m Raspi.Network.WebSockets.main
```

### Low Bandwidth

```bash
VIDEO_WIDTH=320 VIDEO_HEIGHT=240 VIDEO_FPS=10 VIDEO_JPEG_QUALITY=50 python -m Raspi.Network.WebSockets.main
```

### Disable Audio

```bash
AUDIO_ENABLED=false python -m Raspi.Network.WebSockets.main
```

## 🤝 Integration with Motor Control

To integrate with actual motor hardware, modify `handle_motor_command` in `main.py`:

```python
def handle_motor_command(self, command: str, data: dict):
    """Handle motor control commands"""
    import RPi.GPIO as GPIO
    
    # GPIO pin configuration
    MOTOR_LEFT_FWD = 17
    MOTOR_LEFT_BWD = 18
    MOTOR_RIGHT_FWD = 22
    MOTOR_RIGHT_BWD = 23
    
    if command == "forward":
        GPIO.output(MOTOR_LEFT_FWD, GPIO.HIGH)
        GPIO.output(MOTOR_RIGHT_FWD, GPIO.HIGH)
    elif command == "stop":
        GPIO.output(MOTOR_LEFT_FWD, GPIO.LOW)
        GPIO.output(MOTOR_LEFT_BWD, GPIO.LOW)
        GPIO.output(MOTOR_RIGHT_FWD, GPIO.LOW)
        GPIO.output(MOTOR_RIGHT_BWD, GPIO.LOW)
    # ... more commands
```

## 📝 License

This project is provided as-is for educational and IoT development purposes.

## 🙏 Credits

Built with:
- Eclipse Mosquitto
- Paho MQTT
- WebSockets
- OpenCV
- PyAudio
- Ngrok

---

**Made for Raspberry Pi IoT Projects** 🚗📹🔊
