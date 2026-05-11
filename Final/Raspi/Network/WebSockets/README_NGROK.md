# Ngrok WAN Access Setup Guide

## 🎯 Overview

This guide explains how to enable **remote internet access** to your Raspberry Pi surveillance system using **Ngrok tunneling** — no router port forwarding required!

### What is Ngrok?

Ngrok creates secure tunnels from public URLs to your local services, allowing you to:
- ✅ Access your surveillance system from anywhere on the internet
- ✅ Work behind CGNAT (Carrier-Grade NAT)
- ✅ Use mobile hotspots without port forwarding
- ✅ Bypass restrictive firewalls
- ✅ Get automatic HTTPS/WSS encryption

---

## 📋 Prerequisites

1. **Ngrok Account** (free tier works fine)
   - Sign up at: https://ngrok.com/signup
   - Get your auth token from: https://dashboard.ngrok.com/get-started/your-authtoken

2. **Python Dependencies**
   ```bash
   pip install pyngrok
   ```

---

## 🚀 Quick Start

### Step 1: Get Your Ngrok Auth Token

1. Go to https://dashboard.ngrok.com/get-started/your-authtoken
2. Copy your auth token (looks like: `2abc...xyz`)

### Step 2: Set Environment Variables

**Option A: Export in terminal (temporary)**
```bash
export NGROK_ENABLED=true
export NGROK_AUTH_TOKEN="your_token_here"
```

**Option B: Add to ~/.bashrc (permanent)**
```bash
echo 'export NGROK_ENABLED=true' >> ~/.bashrc
echo 'export NGROK_AUTH_TOKEN="your_token_here"' >> ~/.bashrc
source ~/.bashrc
```

**Option C: Create .env file**
```bash
# Create .env file in the WebSockets directory
cat > .env << EOF
NGROK_ENABLED=true
NGROK_AUTH_TOKEN=your_token_here
NGROK_REGION=us
EOF

# Load it before running
set -a; source .env; set +a
```

### Step 3: Run the System

```bash
python main.py
```

You'll see output like:
```
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
📱 Use the PUBLIC URLs above to connect from anywhere on the internet
🔒 Ngrok provides automatic HTTPS/WSS encryption
⚠️  Free tier has connection limits - upgrade at https://ngrok.com/pricing
================================================================================
```

---

## ⚙️ Configuration Options

All settings can be configured via environment variables or `config.py`:

| Variable | Default | Description |
|----------|---------|-------------|
| `NGROK_ENABLED` | `false` | Enable/disable Ngrok tunneling |
| `NGROK_AUTH_TOKEN` | `""` | Your Ngrok auth token (required) |
| `NGROK_REGION` | `us` | Ngrok region: `us`, `eu`, `ap`, `au`, `sa`, `jp`, `in` |
| `NGROK_WEBSOCKET_ENABLED` | `true` | Create WebSocket tunnel |
| `NGROK_MQTT_ENABLED` | `true` | Create MQTT tunnel |
| `NGROK_WS_PORT` | `8765` | Local WebSocket port to tunnel |
| `NGROK_MQTT_PORT` | `1883` | Local MQTT port to tunnel |

### Example: Custom Configuration

```bash
# Use EU region for lower latency in Europe
export NGROK_REGION=eu

# Only tunnel WebSocket (disable MQTT)
export NGROK_MQTT_ENABLED=false

# Use custom ports
export NGROK_WS_PORT=9000
export NGROK_MQTT_PORT=1884

python main.py
```

---

## 🌍 Choosing the Right Region

Select the region **closest to your clients** for best performance:

- `us` - United States
- `eu` - Europe
- `ap` - Asia/Pacific
- `au` - Australia
- `sa` - South America
- `jp` - Japan
- `in` - India

Example:
```bash
export NGROK_REGION=eu  # For European clients
```

---

## 🔧 Troubleshooting

### Problem: "NGROK_AUTH_TOKEN not set"

**Solution:** Make sure you've exported the token:
```bash
export NGROK_AUTH_TOKEN="your_actual_token"
echo $NGROK_AUTH_TOKEN  # Verify it's set
```

### Problem: "pyngrok not installed"

**Solution:** Install the dependency:
```bash
pip install pyngrok
```

### Problem: Tunnel disconnects frequently

**Causes:**
- Free tier has connection limits (40 connections/minute)
- Network instability
- Ngrok service issues

**Solutions:**
1. Upgrade to paid Ngrok plan for higher limits
2. Check your internet connection stability
3. Monitor logs for specific error messages

### Problem: Can't connect to public URL

**Checklist:**
1. ✅ Is the system running? (`python main.py`)
2. ✅ Do you see "NGROK TUNNELS ACTIVE" in logs?
3. ✅ Are you using the correct public URL (wss:// for WebSocket)?
4. ✅ Is your client configured to use the public URL?
5. ✅ Check Ngrok dashboard: https://dashboard.ngrok.com/status/tunnels

### Problem: "ERR_NGROK_108" or tunnel limit errors

**Cause:** Free tier limits exceeded

**Solutions:**
- Wait a few minutes and try again
- Upgrade to paid plan: https://ngrok.com/pricing
- Use fewer concurrent connections

---

## 🔒 Security Considerations

### Free Tier Limitations

⚠️ **Important:** Ngrok free tier provides:
- Public URLs that anyone can access
- No authentication by default
- Connection limits (40/min)

### Recommended Security Measures

1. **Add Authentication to Your WebSocket Server**
   ```python
   # In websocket_server.py, add token validation
   async def _client_handler(self, websocket):
       # Require auth token in first message
       auth_msg = await websocket.recv()
       if not self._validate_token(auth_msg):
           await websocket.close()
           return
       # ... rest of handler
   ```

2. **Use Ngrok IP Restrictions** (paid plans)
   ```bash
   ngrok http 8765 --cidr-allow 1.2.3.4/32
   ```

3. **Monitor Access Logs**
   - Check Ngrok dashboard for suspicious activity
   - Enable detailed logging in your application

4. **Rotate URLs Regularly**
   - Restart Ngrok to get new URLs
   - Don't share URLs publicly

5. **Consider Upgrading to Paid Plan**
   - Custom domains
   - IP whitelisting
   - Higher connection limits
   - Better security features

---

## 📊 Monitoring

### View Active Tunnels

The system automatically monitors tunnel health and attempts reconnection if tunnels fail.

**Check logs for:**
```
✓ WebSocket tunnel created: wss://abc123.ngrok-free.app
✓ MQTT tunnel created: tcp://4.tcp.ngrok.io:12345
Tunnel monitoring started
```

### Ngrok Dashboard

View real-time traffic and tunnel status:
- https://dashboard.ngrok.com/status/tunnels

### Manual Tunnel Check

```python
# In your code or Python shell
from ngrok_manager import NgrokManager
import asyncio

async def check():
    manager = NgrokManager()
    await manager.start()
    print(f"WebSocket: {manager.websocket_url}")
    print(f"MQTT: {manager.mqtt_url}")
    await manager.stop()

asyncio.run(check())
```

---

## 🆙 Upgrading from Local-Only Setup

If you're currently using port forwarding or local network only:

### Before (Port Forwarding)
```bash
# Required router configuration
# Required firewall rules
python main.py
# Access via: ws://your-public-ip:8765
```

### After (Ngrok)
```bash
# No router configuration needed
# No firewall changes needed
export NGROK_ENABLED=true
export NGROK_AUTH_TOKEN="your_token"
python main.py
# Access via: wss://abc123.ngrok-free.app
```

**Benefits:**
- ✅ No router access needed
- ✅ Works behind CGNAT
- ✅ Automatic HTTPS/WSS encryption
- ✅ Dynamic IP changes don't matter
- ✅ Works on mobile hotspots

---

## 💰 Ngrok Pricing

### Free Tier
- ✅ 1 online ngrok process
- ✅ 4 tunnels per process
- ✅ 40 connections/minute
- ✅ Random URLs
- ⚠️ Limited bandwidth

**Perfect for:** Development, testing, personal projects

### Paid Plans (starting $8/month)
- ✅ Custom domains
- ✅ Reserved TCP addresses
- ✅ IP whitelisting
- ✅ Higher connection limits
- ✅ Better performance

**Recommended for:** Production, commercial use

See: https://ngrok.com/pricing

---

## 🧪 Testing Your Setup

### Test WebSocket Connection

```bash
# Install wscat for testing
npm install -g wscat

# Test local connection
wscat -c ws://localhost:8765

# Test Ngrok public URL
wscat -c wss://your-ngrok-url.ngrok-free.app
```

### Test MQTT Connection

```bash
# Install mosquitto clients
sudo apt-get install mosquitto-clients

# Test local connection
mosquitto_pub -h localhost -p 1883 -t "test" -m "hello"

# Test Ngrok public URL (extract host:port from tcp://4.tcp.ngrok.io:12345)
mosquitto_pub -h 4.tcp.ngrok.io -p 12345 -t "test" -m "hello"
```

---

## 📚 Additional Resources

- **Ngrok Documentation:** https://ngrok.com/docs
- **Ngrok Dashboard:** https://dashboard.ngrok.com
- **pyngrok Documentation:** https://pyngrok.readthedocs.io
- **WebSocket Testing:** https://www.websocket.org/echo.html

---

## 🐛 Getting Help

If you encounter issues:

1. **Check logs** for error messages
2. **Verify configuration** (auth token, region, ports)
3. **Test locally first** (without Ngrok)
4. **Check Ngrok status** at https://status.ngrok.com
5. **Review Ngrok dashboard** for tunnel activity

---

## 📝 Example: Complete Setup Script

```bash
#!/bin/bash
# setup_ngrok.sh - Complete Ngrok setup for Raspberry Pi

# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure Ngrok
read -p "Enter your Ngrok auth token: " TOKEN
export NGROK_ENABLED=true
export NGROK_AUTH_TOKEN="$TOKEN"
export NGROK_REGION=us

# 3. Save to .bashrc for persistence
echo "export NGROK_ENABLED=true" >> ~/.bashrc
echo "export NGROK_AUTH_TOKEN=\"$TOKEN\"" >> ~/.bashrc
echo "export NGROK_REGION=us" >> ~/.bashrc

# 4. Start the system
echo "Starting surveillance system with Ngrok..."
python main.py
```

Make it executable and run:
```bash
chmod +x setup_ngrok.sh
./setup_ngrok.sh
```

---

**🎉 You're all set! Your Raspberry Pi surveillance system is now accessible from anywhere on the internet!**
