# Installation Guide - Raspberry Pi Surveillance System with Ngrok

## 📋 Table of Contents

1. [System Requirements](#system-requirements)
2. [Raspberry Pi Setup](#raspberry-pi-setup)
3. [Python Dependencies](#python-dependencies)
4. [Ngrok Setup](#ngrok-setup)
5. [MQTT Broker Setup](#mqtt-broker-setup)
6. [Testing](#testing)
7. [Troubleshooting](#troubleshooting)

---

## 🖥️ System Requirements

### Hardware
- **Raspberry Pi 3B+ or newer** (Pi 4 recommended)
- **USB Webcam or Pi Camera Module**
- **USB Microphone** (optional, for audio streaming)
- **MicroSD Card** (16GB minimum, 32GB recommended)
- **Stable Internet Connection**

### Software
- **Raspberry Pi OS** (Bullseye or newer)
- **Python 3.7+** (pre-installed on Pi OS)
- **Git** (for cloning repository)

---

## 🔧 Raspberry Pi Setup

### 1. Update System

```bash
sudo apt-get update
sudo apt-get upgrade -y
```

### 2. Install System Dependencies

```bash
# Video capture dependencies
sudo apt-get install -y libopencv-dev python3-opencv

# Audio capture dependencies
sudo apt-get install -y portaudio19-dev python3-pyaudio

# Build tools
sudo apt-get install -y python3-dev python3-pip git

# Optional: MQTT broker (if running locally)
sudo apt-get install -y mosquitto mosquitto-clients
```

### 3. Enable Camera (if using Pi Camera Module)

```bash
sudo raspi-config
# Navigate to: Interface Options → Camera → Enable
# Reboot when prompted
```

### 4. Test Camera

```bash
# For USB camera
ls /dev/video*

# For Pi Camera Module
vcgencmd get_camera

# Test capture
raspistill -o test.jpg  # Pi Camera
# OR
fswebcam test.jpg       # USB Camera
```

---

## 🐍 Python Dependencies

### 1. Upgrade pip

```bash
python3 -m pip install --upgrade pip
```

### 2. Install Python Packages

```bash
cd Final/Raspi/Network/WebSockets

# Install all dependencies
pip3 install -r requirements.txt
```

**Manual installation (if requirements.txt fails):**

```bash
pip3 install websockets>=12.0
pip3 install paho-mqtt>=1.6.1
pip3 install opencv-python-headless>=4.8.0
pip3 install numpy>=1.24.0
pip3 install PyAudio>=0.2.13
pip3 install pyngrok>=7.0.0
```

### 3. Verify Installation

```bash
python3 -c "import websockets; print('websockets OK')"
python3 -c "import paho.mqtt.client; print('paho-mqtt OK')"
python3 -c "import cv2; print('opencv OK')"
python3 -c "import pyaudio; print('pyaudio OK')"
python3 -c "import pyngrok; print('pyngrok OK')"
```

---

## 🌐 Ngrok Setup

### 1. Create Ngrok Account

1. Go to https://ngrok.com/signup
2. Sign up (free tier is sufficient)
3. Verify your email

### 2. Get Auth Token

1. Login to https://dashboard.ngrok.com
2. Navigate to: https://dashboard.ngrok.com/get-started/your-authtoken
3. Copy your auth token (format: `2abc...xyz`)

### 3. Configure Auth Token

**Option A: Environment Variable (Temporary)**

```bash
export NGROK_AUTH_TOKEN="your_token_here"
export NGROK_ENABLED=true
```

**Option B: Persistent Configuration**

```bash
# Add to ~/.bashrc
echo 'export NGROK_AUTH_TOKEN="your_token_here"' >> ~/.bashrc
echo 'export NGROK_ENABLED=true' >> ~/.bashrc
source ~/.bashrc
```

**Option C: Use .env File**

```bash
# Copy example configuration
cp .env.example .env

# Edit with your token
nano .env

# Update this line:
NGROK_AUTH_TOKEN=your_actual_token_here

# Load environment
set -a; source .env; set +a
```

### 4. Test Ngrok

```bash
python3 -c "from pyngrok import ngrok; print('Ngrok OK')"
```

---

## 📡 MQTT Broker Setup

### Option 1: Local Mosquitto (Recommended)

```bash
# Install Mosquitto
sudo apt-get install -y mosquitto mosquitto-clients

# Enable and start service
sudo systemctl enable mosquitto
sudo systemctl start mosquitto

# Check status
sudo systemctl status mosquitto

# Test local connection
mosquitto_pub -h localhost -t "test" -m "hello"
mosquitto_sub -h localhost -t "test" -v
```

### Option 2: Remote MQTT Broker

If using a remote broker, update configuration:

```bash
export MQTT_BROKER=your.mqtt.broker.com
export MQTT_PORT=1883
```

### Configure Mosquitto (Optional)

```bash
# Edit configuration
sudo nano /etc/mosquitto/mosquitto.conf

# Add these lines:
listener 1883
allow_anonymous true

# Restart service
sudo systemctl restart mosquitto
```

**⚠️ Security Note:** For production, configure authentication:

```bash
# Create password file
sudo mosquitto_passwd -c /etc/mosquitto/passwd username

# Update mosquitto.conf
listener 1883
allow_anonymous false
password_file /etc/mosquitto/passwd

# Restart
sudo systemctl restart mosquitto
```

---

## 🧪 Testing

### 1. Test Local Setup (Without Ngrok)

```bash
# Disable Ngrok temporarily
export NGROK_ENABLED=false

# Start system
python3 main.py
```

**Expected output:**
```
[INFO] WebSocketServer: WebSocket server starting on ws://0.0.0.0:8765
[INFO] WebSocketServer: Local network only. For WAN access:
[INFO] WebSocketServer:   Option 1: Forward port 8765 on your router
[INFO] WebSocketServer:   Option 2: Enable Ngrok
[INFO] Main: All subsystems started. Running…
```

**Test WebSocket connection:**

```bash
# Install wscat
npm install -g wscat

# Connect
wscat -c ws://localhost:8765
```

### 2. Test with Ngrok

```bash
# Enable Ngrok
export NGROK_ENABLED=true
export NGROK_AUTH_TOKEN="your_token"

# Start system
python3 main.py
```

**Expected output:**
```
[INFO] NgrokManager: Starting Ngrok tunnels...
[INFO] NgrokManager: Ngrok configured: region=us
[INFO] NgrokManager: Creating WebSocket tunnel for port 8765...
[INFO] NgrokManager: ✓ WebSocket tunnel created: wss://abc123.ngrok-free.app
[INFO] NgrokManager: Creating MQTT tunnel for port 1883...
[INFO] NgrokManager: ✓ MQTT tunnel created: tcp://4.tcp.ngrok.io:12345
================================================================================
🌐 NGROK TUNNELS ACTIVE - WAN ACCESS ENABLED
================================================================================

  WEBSOCKET Service:
    Local:  wss://localhost:8765
    Public: wss://abc123.ngrok-free.app

  MQTT Service:
    Local:  tcp://localhost:1883
    Public: tcp://4.tcp.ngrok.io:12345

================================================================================
```

**Test public WebSocket:**

```bash
wscat -c wss://your-ngrok-url.ngrok-free.app
```

### 3. Test Video Stream

```bash
# Check if camera is detected
python3 -c "import cv2; print(cv2.VideoCapture(0).isOpened())"

# Should print: True
```

### 4. Test Audio Stream

```bash
# List audio devices
python3 -m pyaudio

# Test recording
python3 -c "
import pyaudio
p = pyaudio.PyAudio()
stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=1024)
print('Recording... Press Ctrl+C to stop')
try:
    while True:
        data = stream.read(1024)
        print(f'Captured {len(data)} bytes')
except KeyboardInterrupt:
    pass
stream.close()
p.terminate()
"
```

### 5. Test MQTT Bridge

**Terminal 1 (Start system):**
```bash
python3 main.py
```

**Terminal 2 (Publish to MQTT):**
```bash
mosquitto_pub -h localhost -t "dev/motor" -m "forward"
```

**Terminal 3 (Subscribe to MQTT):**
```bash
mosquitto_sub -h localhost -t "dev/status" -v
```

---

## 🚀 Quick Start Scripts

### Linux/Raspberry Pi

```bash
# Make script executable
chmod +x start_with_ngrok.sh

# Run
./start_with_ngrok.sh
```

### Windows (for testing)

```cmd
start_with_ngrok.bat
```

---

## 🔍 Troubleshooting

### Problem: "No module named 'websockets'"

**Solution:**
```bash
pip3 install websockets
```

### Problem: "No module named 'cv2'"

**Solution:**
```bash
sudo apt-get install python3-opencv
pip3 install opencv-python-headless
```

### Problem: "No module named 'pyaudio'"

**Solution:**
```bash
sudo apt-get install portaudio19-dev
pip3 install pyaudio
```

### Problem: Camera not detected

**Solution:**
```bash
# Check camera connection
ls /dev/video*

# For Pi Camera, enable in raspi-config
sudo raspi-config
# Interface Options → Camera → Enable

# Test camera
raspistill -o test.jpg  # Pi Camera
fswebcam test.jpg       # USB Camera
```

### Problem: "ALSA lib" errors (audio)

**Solution:**
```bash
# These are warnings, not errors - system will still work
# To suppress, create ~/.asoundrc:
cat > ~/.asoundrc << EOF
pcm.!default {
    type hw
    card 0
}
ctl.!default {
    type hw
    card 0
}
EOF
```

### Problem: Ngrok tunnel fails

**Solutions:**

1. **Check auth token:**
   ```bash
   echo $NGROK_AUTH_TOKEN
   ```

2. **Test Ngrok directly:**
   ```bash
   python3 -c "from pyngrok import ngrok, conf; conf.get_default().auth_token='your_token'; t=ngrok.connect(8765); print(t.public_url)"
   ```

3. **Check Ngrok status:**
   - https://status.ngrok.com

4. **View Ngrok logs:**
   - https://dashboard.ngrok.com/observability/event-subscriptions

### Problem: Permission denied on ports

**Solution:**
```bash
# Use ports > 1024 (don't require root)
export WS_PORT=8765
export MQTT_PORT=1883

# OR run with sudo (not recommended)
sudo python3 main.py
```

### Problem: High CPU usage

**Solutions:**

1. **Reduce video FPS:**
   ```bash
   export VIDEO_TARGET_FPS=15
   ```

2. **Lower video resolution:**
   ```bash
   export VIDEO_CAPTURE_WIDTH=320
   export VIDEO_CAPTURE_HEIGHT=240
   ```

3. **Reduce JPEG quality:**
   ```bash
   export VIDEO_JPEG_QUALITY=50
   ```

---

## 📊 Performance Optimization

### For Raspberry Pi 3

```bash
export VIDEO_CAPTURE_WIDTH=320
export VIDEO_CAPTURE_HEIGHT=240
export VIDEO_TARGET_FPS=15
export VIDEO_JPEG_QUALITY=60
```

### For Raspberry Pi 4

```bash
export VIDEO_CAPTURE_WIDTH=640
export VIDEO_CAPTURE_HEIGHT=480
export VIDEO_TARGET_FPS=20
export VIDEO_JPEG_QUALITY=70
```

### For Raspberry Pi 5

```bash
export VIDEO_CAPTURE_WIDTH=1280
export VIDEO_CAPTURE_HEIGHT=720
export VIDEO_TARGET_FPS=30
export VIDEO_JPEG_QUALITY=75
```

---

## 🔐 Security Hardening

### 1. Firewall Configuration

```bash
# Install UFW
sudo apt-get install ufw

# Allow SSH (important!)
sudo ufw allow 22/tcp

# Allow WebSocket (if not using Ngrok)
sudo ufw allow 8765/tcp

# Allow MQTT (if not using Ngrok)
sudo ufw allow 1883/tcp

# Enable firewall
sudo ufw enable
```

### 2. MQTT Authentication

```bash
# Create password file
sudo mosquitto_passwd -c /etc/mosquitto/passwd admin

# Update config
sudo nano /etc/mosquitto/mosquitto.conf
# Add:
# allow_anonymous false
# password_file /etc/mosquitto/passwd

# Restart
sudo systemctl restart mosquitto
```

### 3. Disable Unused Services

```bash
sudo systemctl disable bluetooth
sudo systemctl disable avahi-daemon
```

---

## 📚 Next Steps

1. ✅ **Complete installation** following this guide
2. ✅ **Test locally** without Ngrok
3. ✅ **Enable Ngrok** for WAN access
4. ✅ **Read [README_NGROK.md](README_NGROK.md)** for Ngrok details
5. ✅ **Configure your client** to use public URLs
6. ✅ **Monitor performance** and optimize settings

---

## 🆘 Getting Help

- **Check logs** for error messages
- **Review configuration** in `config.py`
- **Test components individually** (camera, audio, MQTT)
- **Verify network connectivity**
- **Check Ngrok dashboard** for tunnel status

---

**🎉 Installation complete! Your surveillance system is ready to use!**
