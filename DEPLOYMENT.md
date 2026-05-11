# Deployment Guide - Production Setup

Complete guide for deploying the Raspberry Pi Surveillance Car system in production environments.

## Table of Contents

1. [Hardware Requirements](#hardware-requirements)
2. [Initial Setup](#initial-setup)
3. [Security Hardening](#security-hardening)
4. [Performance Optimization](#performance-optimization)
5. [Monitoring & Logging](#monitoring--logging)
6. [Backup & Recovery](#backup--recovery)
7. [Troubleshooting](#troubleshooting)

## Hardware Requirements

### Minimum Requirements

- **Raspberry Pi**: 3B+ or newer
- **RAM**: 1GB (2GB+ recommended)
- **Storage**: 8GB microSD (16GB+ recommended)
- **Camera**: USB webcam or Pi Camera Module
- **Power**: 5V 2.5A power supply (3A for Pi 4)

### Recommended Setup

- **Raspberry Pi 4**: 4GB RAM
- **Storage**: 32GB Class 10 microSD or SSD
- **Camera**: Pi Camera Module V2 (8MP)
- **Microphone**: USB microphone with noise cancellation
- **Power**: Official Raspberry Pi power supply
- **Cooling**: Heatsinks or fan (for continuous operation)

### Optional Components

- **Motor Driver**: L298N or similar
- **Motors**: DC motors with encoders
- **Sensors**: Ultrasonic (HC-SR04), IR sensors
- **Battery**: LiPo battery with BMS
- **Display**: Small OLED for status

## Initial Setup

### 1. Raspberry Pi OS Installation

```bash
# Download Raspberry Pi Imager
# https://www.raspberrypi.com/software/

# Flash Raspberry Pi OS Lite (64-bit recommended)
# Enable SSH before first boot
```

### 2. First Boot Configuration

```bash
# SSH into Pi
ssh pi@raspberrypi.local

# Update system
sudo apt update && sudo apt upgrade -y

# Configure system
sudo raspi-config
# - Set hostname
# - Configure WiFi
# - Enable camera
# - Expand filesystem
# - Set timezone
```

### 3. Install System

```bash
# Clone or copy project
cd ~
# ... copy project files ...

# Run setup
cd Final
chmod +x setup.sh
./setup.sh
```

### 4. Configure Ngrok

```bash
# Get auth token from ngrok.com
export NGROK_AUTH_TOKEN=your_token_here
ngrok config add-authtoken $NGROK_AUTH_TOKEN
```

### 5. Test System

```bash
source venv/bin/activate
python test_system.py
```

## Security Hardening

### 1. MQTT Authentication

```bash
# Create password file
sudo mosquitto_passwd -c /etc/mosquitto/passwd admin

# Add more users
sudo mosquitto_passwd /etc/mosquitto/passwd user1

# Update mosquitto.conf
sudo nano /etc/mosquitto/conf.d/surveillance_car.conf
```

Add:
```
allow_anonymous false
password_file /etc/mosquitto/passwd
```

Update code to use authentication:
```python
# In connection_manager.py
self.client.username_pw_set("admin", "password")
```

### 2. MQTT Access Control (ACL)

Create `/etc/mosquitto/acl`:
```
# Admin has full access
user admin
topic readwrite #

# Regular users limited access
user user1
topic read dev/status
topic write dev/motor
```

Update `mosquitto.conf`:
```
acl_file /etc/mosquitto/acl
```

### 3. TLS/SSL for MQTT

```bash
# Generate certificates
cd /etc/mosquitto/certs

# CA certificate
openssl req -new -x509 -days 3650 -extensions v3_ca \
  -keyout ca.key -out ca.crt

# Server certificate
openssl genrsa -out server.key 2048
openssl req -new -out server.csr -key server.key
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key \
  -CAcreateserial -out server.crt -days 3650

# Set permissions
sudo chown mosquitto:mosquitto *.key *.crt
sudo chmod 600 *.key
```

Update `mosquitto.conf`:
```
listener 8883
cafile /etc/mosquitto/certs/ca.crt
certfile /etc/mosquitto/certs/server.crt
keyfile /etc/mosquitto/certs/server.key
require_certificate false
```

### 4. WebSocket Authentication

Add to `websocket_server.py`:

```python
async def authenticate(self, websocket):
    """Authenticate WebSocket client"""
    # Wait for auth message
    auth_msg = await asyncio.wait_for(websocket.recv(), timeout=10)
    data = json.loads(auth_msg)
    
    if data.get('type') != 'auth':
        return False
    
    username = data.get('username')
    password = data.get('password')
    
    # Verify credentials (implement your logic)
    if self.verify_credentials(username, password):
        return True
    
    return False
```

### 5. Firewall Configuration

```bash
# Install UFW
sudo apt install ufw

# Default policies
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH
sudo ufw allow 22/tcp

# Allow MQTT (local only)
sudo ufw allow from 192.168.0.0/16 to any port 1883

# Allow WebSocket (local only)
sudo ufw allow from 192.168.0.0/16 to any port 8765

# Enable firewall
sudo ufw enable
```

### 6. System Hardening

```bash
# Disable password authentication for SSH
sudo nano /etc/ssh/sshd_config
# Set: PasswordAuthentication no
# Set: PermitRootLogin no

# Use SSH keys only
ssh-copy-id pi@raspberrypi.local

# Restart SSH
sudo systemctl restart ssh

# Install fail2ban
sudo apt install fail2ban
sudo systemctl enable fail2ban
```

## Performance Optimization

### 1. Video Optimization

```bash
# High quality (requires Pi 4)
VIDEO_WIDTH=1280 \
VIDEO_HEIGHT=720 \
VIDEO_FPS=30 \
VIDEO_JPEG_QUALITY=85 \
./run.sh
```

```bash
# Low latency
VIDEO_WIDTH=640 \
VIDEO_HEIGHT=480 \
VIDEO_FPS=15 \
VIDEO_JPEG_QUALITY=60 \
VIDEO_BUFFER_SIZE=1 \
./run.sh
```

```bash
# Low bandwidth
VIDEO_WIDTH=320 \
VIDEO_HEIGHT=240 \
VIDEO_FPS=10 \
VIDEO_JPEG_QUALITY=50 \
./run.sh
```

### 2. System Optimization

```bash
# Increase GPU memory (for camera)
sudo nano /boot/config.txt
# Add: gpu_mem=256

# Overclock (Pi 4 only, use with cooling)
sudo nano /boot/config.txt
# Add:
# over_voltage=6
# arm_freq=2000

# Disable unnecessary services
sudo systemctl disable bluetooth
sudo systemctl disable avahi-daemon
```

### 3. Network Optimization

```bash
# Increase network buffers
sudo nano /etc/sysctl.conf
# Add:
net.core.rmem_max=26214400
net.core.wmem_max=26214400
net.ipv4.tcp_rmem=4096 87380 26214400
net.ipv4.tcp_wmem=4096 65536 26214400

# Apply
sudo sysctl -p
```

### 4. Python Optimization

```bash
# Use PyPy (faster Python interpreter)
sudo apt install pypy3 pypy3-dev

# Or compile Python with optimizations
# (Advanced, not recommended for beginners)
```

## Monitoring & Logging

### 1. System Monitoring

```bash
# Install monitoring tools
sudo apt install htop iotop nethogs

# Monitor CPU/Memory
htop

# Monitor disk I/O
sudo iotop

# Monitor network
sudo nethogs
```

### 2. Application Logging

```bash
# View systemd logs
sudo journalctl -u surveillance-car -f

# View Mosquitto logs
sudo tail -f /var/log/mosquitto/mosquitto.log

# View system logs
sudo tail -f /var/log/syslog
```

### 3. Log Rotation

Create `/etc/logrotate.d/surveillance-car`:
```
/var/log/surveillance-car/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0640 pi pi
}
```

### 4. Remote Monitoring

Install Prometheus exporter:
```bash
pip install prometheus-client

# Add to main.py
from prometheus_client import start_http_server, Counter, Gauge

# Start metrics server
start_http_server(9090)

# Define metrics
frames_sent = Counter('video_frames_sent', 'Total video frames sent')
clients_connected = Gauge('websocket_clients', 'Connected WebSocket clients')
```

### 5. Health Checks

Create `/usr/local/bin/health_check.sh`:
```bash
#!/bin/bash

# Check if service is running
if ! systemctl is-active --quiet surveillance-car; then
    echo "Service not running"
    exit 1
fi

# Check if MQTT is responding
if ! mosquitto_pub -h localhost -t test -m "ping" -q 0; then
    echo "MQTT not responding"
    exit 1
fi

# Check if WebSocket is responding
if ! curl -s http://localhost:8765 > /dev/null; then
    echo "WebSocket not responding"
    exit 1
fi

echo "All checks passed"
exit 0
```

Add to crontab:
```bash
crontab -e
# Add: */5 * * * * /usr/local/bin/health_check.sh
```

## Backup & Recovery

### 1. Configuration Backup

```bash
# Backup script
#!/bin/bash
BACKUP_DIR="/home/pi/backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup configuration
tar -czf $BACKUP_DIR/config_$DATE.tar.gz \
    /etc/mosquitto/conf.d/ \
    /etc/systemd/system/surveillance-car.service \
    ~/Final/Raspi/Network/WebSockets/config.py

# Backup MQTT data
sudo tar -czf $BACKUP_DIR/mqtt_data_$DATE.tar.gz \
    /var/lib/mosquitto/

# Keep only last 7 backups
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete
```

### 2. Full System Backup

```bash
# Create SD card image (from another computer)
sudo dd if=/dev/sdX of=raspi_backup.img bs=4M status=progress

# Compress
gzip raspi_backup.img
```

### 3. Recovery Procedure

```bash
# Restore configuration
tar -xzf config_backup.tar.gz -C /

# Restore MQTT data
sudo tar -xzf mqtt_data_backup.tar.gz -C /

# Restart services
sudo systemctl restart mosquitto
sudo systemctl restart surveillance-car
```

## Troubleshooting

### Common Issues

#### 1. Camera Not Working

```bash
# Check camera detection
vcgencmd get_camera

# Test camera
raspistill -o test.jpg

# Check permissions
sudo usermod -a -G video $USER

# Enable camera interface
sudo raspi-config
# Interface Options -> Camera -> Enable
```

#### 2. High CPU Usage

```bash
# Check processes
htop

# Reduce video quality
VIDEO_FPS=10 VIDEO_JPEG_QUALITY=50 ./run.sh

# Disable audio
AUDIO_ENABLED=false ./run.sh
```

#### 3. Memory Issues

```bash
# Check memory
free -h

# Increase swap
sudo dphys-swapfile swapoff
sudo nano /etc/dphys-swapfile
# Set: CONF_SWAPSIZE=2048
sudo dphys-swapfile setup
sudo dphys-swapfile swapon
```

#### 4. Network Latency

```bash
# Check network
ping -c 10 8.8.8.8

# Check WiFi signal
iwconfig wlan0

# Use Ethernet instead of WiFi
```

#### 5. Ngrok Connection Issues

```bash
# Check auth token
ngrok config check

# Test manually
ngrok tcp 1883

# Check account limits (free tier)
# Upgrade at ngrok.com if needed
```

### Debug Mode

```bash
# Enable debug logging
LOG_LEVEL=DEBUG ./run.sh

# Or in config.py
export LOG_LEVEL=DEBUG
```

### Performance Profiling

```python
# Add to main.py
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()

# ... your code ...

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(20)
```

## Production Checklist

- [ ] System updated and configured
- [ ] MQTT authentication enabled
- [ ] TLS/SSL configured
- [ ] Firewall configured
- [ ] SSH hardened (key-only)
- [ ] Systemd service enabled
- [ ] Logging configured
- [ ] Monitoring setup
- [ ] Backup script created
- [ ] Health checks configured
- [ ] Performance optimized
- [ ] Documentation updated
- [ ] Testing completed
- [ ] Recovery procedure tested

## Maintenance Schedule

### Daily
- Check system logs
- Monitor resource usage
- Verify service status

### Weekly
- Review security logs
- Check disk space
- Test backup restoration

### Monthly
- Update system packages
- Review and rotate logs
- Performance audit
- Security audit

### Quarterly
- Full system backup
- Update documentation
- Review and update dependencies
- Disaster recovery drill

---

**Deployment Guide Version**: 1.0.0  
**Last Updated**: 2024  
**Support**: See README.md for contact information
