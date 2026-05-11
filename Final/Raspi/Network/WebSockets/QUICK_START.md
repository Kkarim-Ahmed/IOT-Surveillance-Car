# 🚀 Quick Start Guide - Ngrok WAN Access

## ⚡ 3-Step Setup

### 1️⃣ Install Dependencies
```bash
pip3 install -r requirements.txt
```

### 2️⃣ Configure Ngrok
```bash
# Get your token from: https://dashboard.ngrok.com/get-started/your-authtoken
export NGROK_ENABLED=true
export NGROK_AUTH_TOKEN="your_token_here"
```

### 3️⃣ Run
```bash
python3 main.py
```

**Done!** Your public URLs will be displayed in the console.

---

## 📋 What You'll See

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
```

**Use the PUBLIC URLs to connect from anywhere!**

---

## 🔧 Common Configurations

### WebSocket Only
```bash
export NGROK_ENABLED=true
export NGROK_AUTH_TOKEN="your_token"
export NGROK_MQTT_ENABLED=false
python3 main.py
```

### Europe Region (Lower Latency)
```bash
export NGROK_ENABLED=true
export NGROK_AUTH_TOKEN="your_token"
export NGROK_REGION=eu
python3 main.py
```

### Custom Ports
```bash
export NGROK_ENABLED=true
export NGROK_AUTH_TOKEN="your_token"
export WS_PORT=9000
export NGROK_WS_PORT=9000
python3 main.py
```

---

## 🧪 Testing

### Test WebSocket Connection
```bash
# Install wscat
npm install -g wscat

# Connect to public URL
wscat -c wss://your-ngrok-url.ngrok-free.app
```

### Test MQTT Connection
```bash
# Extract host:port from tcp://4.tcp.ngrok.io:12345
mosquitto_pub -h 4.tcp.ngrok.io -p 12345 -t "test" -m "hello"
```

---

## 🐛 Troubleshooting

| Problem | Solution |
|---------|----------|
| "NGROK_AUTH_TOKEN not set" | `export NGROK_AUTH_TOKEN="your_token"` |
| "pyngrok not installed" | `pip3 install pyngrok` |
| Can't connect to public URL | Check system is running, verify URL is correct |
| Tunnel disconnects | Free tier has limits, check network stability |

---

## 📚 Full Documentation

- **[README_NGROK.md](README_NGROK.md)** - Complete Ngrok guide
- **[INSTALLATION.md](INSTALLATION.md)** - Full installation instructions
- **[NGROK_SUMMARY.md](NGROK_SUMMARY.md)** - Integration details
- **[.env.example](.env.example)** - All configuration options

---

## 🎯 Key Benefits

✅ **No port forwarding** - Works behind CGNAT  
✅ **No router config** - Zero network setup  
✅ **Works anywhere** - Mobile hotspots, corporate networks  
✅ **Automatic HTTPS/WSS** - Secure by default  
✅ **3-step setup** - Running in minutes  

---

## 💡 Pro Tips

1. **Save your token permanently:**
   ```bash
   echo 'export NGROK_AUTH_TOKEN="your_token"' >> ~/.bashrc
   source ~/.bashrc
   ```

2. **Use the quick start script:**
   ```bash
   chmod +x start_with_ngrok.sh
   ./start_with_ngrok.sh
   ```

3. **Monitor your tunnels:**
   - Dashboard: https://dashboard.ngrok.com/status/tunnels
   - Check logs for "NGROK TUNNELS ACTIVE"

4. **Choose the right region:**
   - `us` - United States
   - `eu` - Europe
   - `ap` - Asia/Pacific
   - `au` - Australia

---

**🎉 That's it! You're ready to access your surveillance system from anywhere!**
