# Quick Start Guide - Raspberry Pi Surveillance Car

Get your surveillance car system running in 5 minutes!

## Prerequisites

- Raspberry Pi (3B+ or newer recommended)
- Raspberry Pi OS (Bullseye or newer)
- USB Webcam or Pi Camera
- USB Microphone (optional)
- Internet connection

## Installation (One Command)

```bash
chmod +x setup.sh && ./setup.sh
```

This installs everything automatically:
- System dependencies
- Mosquitto MQTT broker
- Ngrok
- Python packages
- Systemd service

## Configuration

### 1. Get Ngrok Auth Token

1. Sign up at [ngrok.com](https://ngrok.com) (free)
2. Copy your auth token
3. Configure it:

```bash
export NGROK_AUTH_TOKEN=your_token_here
ngrok config add-authtoken $NGROK_AUTH_TOKEN
```

### 2. Test Components

```bash
# Activate virtual environment
source venv/bin/activate

# Run system test
python test_system.py
```

## Running the System

### Method 1: Direct Execution (Recommended for testing)

```bash
./run.sh
```

### Method 2: Systemd Service (Recommended for production)

```bash
# Enable service
sudo systemctl enable surveillance-car

# Start service
sudo systemctl start surveillance-car

# Check status
sudo systemctl status surveillance-car

# View logs
sudo journalctl -u surveillance-car -f
```

## Accessing Your Car

After starting, you'll see:

```
======================================================================
🌐 NGROK WAN TUNNELS ACTIVE
======================================================================
📡 MQTT Broker (TCP): tcp://0.tcp.ngrok.io:12345
🔌 WebSocket Server: wss://abc123.ngrok.io
======================================================================
```

### Option 1: Web Dashboard

1. Open `client_example.html` in your browser
2. Enter the WebSocket URL (wss://...)
3. Click "Connect"
4. Use arrow keys or buttons to control

### Option 2: MQTT Client

```bash
# Subscribe to all topics
mosquitto_sub -h 0.tcp.ngrok.io -p 12345 -t 'dev/#' -v

# Send motor command
mosquitto_pub -h 0.tcp.ngrok.io -p 12345 -t dev/motor -m '{"command":"forward"}'
```

### Option 3: Custom Client

```python
import websockets
import asyncio

async def control_car():
    async with websockets.connect('wss://your-url.ngrok.io') as ws:
        # Send command
        await ws.send('{"type":"mqtt_publish","topic":"dev/motor","payload":"forward"}')
        
        # Receive video/audio
        while True:
            data = await ws.recv()
            # Process data...

asyncio.run(control_car())
```

## Basic Commands

### Motor Control

```bash
# Forward
mosquitto_pub -h localhost -t dev/motor -m '{"command":"forward"}'

# Backward
mosquitto_pub -h localhost -t dev/motor -m '{"command":"backward"}'

# Left
mosquitto_pub -h localhost -t dev/motor -m '{"command":"left"}'

# Right
mosquitto_pub -h localhost -t dev/motor -m '{"command":"right"}'

# Stop
mosquitto_pub -h localhost -t dev/motor -m '{"command":"stop"}'
```

### Status Request

```bash
mosquitto_pub -h localhost -t dev/status -m '{"command":"get_status"}'
```

### Monitor All Messages

```bash
mosquitto_sub -h localhost -t 'dev/#' -v
```

## Troubleshooting

### Camera not working

```bash
# Check camera
vcgencmd get_camera

# Test camera
raspistill -o test.jpg

# If using USB camera, check device
ls -l /dev/video*
```

### Audio not working

```bash
# List audio devices
arecord -l

# Test microphone
arecord -D plughw:1,0 -d 5 test.wav
aplay test.wav
```

### MQTT not connecting

```bash
# Check Mosquitto status
sudo systemctl status mosquitto

# Restart Mosquitto
sudo systemctl restart mosquitto

# Check logs
sudo tail -f /var/log/mosquitto/mosquitto.log
```

### Ngrok not working

```bash
# Check auth token
ngrok config check

# Test manually
ngrok tcp 1883

# Check account (free accounts have limits)
```

## Configuration Options

Edit `Raspi/Network/WebSockets/config.py` or use environment variables:

```bash
# High quality video
VIDEO_JPEG_QUALITY=85 VIDEO_FPS=30 ./run.sh

# Low bandwidth
VIDEO_WIDTH=320 VIDEO_HEIGHT=240 VIDEO_FPS=10 ./run.sh

# Disable audio
AUDIO_ENABLED=false ./run.sh

# Different MQTT broker
MQTT_BROKER_HOST=192.168.1.100 ./run.sh

# Debug logging
LOG_LEVEL=DEBUG ./run.sh
```

## Performance Tips

### For Best Video Quality
```bash
VIDEO_WIDTH=1280 VIDEO_HEIGHT=720 VIDEO_FPS=30 VIDEO_JPEG_QUALITY=85 ./run.sh
```

### For Low Bandwidth
```bash
VIDEO_WIDTH=320 VIDEO_HEIGHT=240 VIDEO_FPS=10 VIDEO_JPEG_QUALITY=50 ./run.sh
```

### For Maximum FPS
```bash
VIDEO_WIDTH=640 VIDEO_HEIGHT=480 VIDEO_FPS=30 VIDEO_JPEG_QUALITY=60 ./run.sh
```

## Next Steps

1. **Integrate Motor Control**: Edit `handle_motor_command()` in `main.py`
2. **Add Sensors**: Extend MQTT topics for ultrasonic, IR, etc.
3. **Secure the System**: Enable MQTT authentication (see README.md)
4. **Custom Dashboard**: Modify `client_example.html`
5. **Add Features**: Implement autonomous driving, object detection, etc.

## Support

- Full documentation: `README.md`
- Test system: `python test_system.py`
- Check logs: `sudo journalctl -u surveillance-car -f`
- MQTT monitor: `mosquitto_sub -h localhost -t 'dev/#' -v`

## Common Issues

**"Module not found" error**
```bash
source venv/bin/activate
pip install -r requirements.txt
```

**"Permission denied" on GPIO**
```bash
sudo usermod -a -G gpio $USER
sudo usermod -a -G video $USER
# Logout and login again
```

**"Port already in use"**
```bash
# Check what's using the port
sudo netstat -tulpn | grep 8765

# Kill the process or change port
WS_PORT=9000 ./run.sh
```

**Ngrok connection limit**
```bash
# Free accounts have connection limits
# Upgrade at ngrok.com or restart ngrok
```

---

**You're ready to go! 🚀**

Start the system with `./run.sh` and open `client_example.html` in your browser!
