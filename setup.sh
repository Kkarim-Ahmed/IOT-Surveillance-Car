#!/bin/bash

# Raspberry Pi Surveillance Car - Setup Script
# This script installs all dependencies and configures the system

set -e

echo "=========================================="
echo "Raspberry Pi Surveillance Car Setup"
echo "=========================================="
echo ""

# Check if running on Raspberry Pi
if [ -f /proc/device-tree/model ]; then
    MODEL=$(cat /proc/device-tree/model)
    echo "Detected: $MODEL"
else
    echo "Warning: Not running on Raspberry Pi"
fi

echo ""

# Update system
echo "Step 1: Updating system packages..."
sudo apt-get update
sudo apt-get upgrade -y

echo ""

# Install system dependencies
echo "Step 2: Installing system dependencies..."
sudo apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    python3-venv \
    mosquitto \
    mosquitto-clients \
    libportaudio2 \
    portaudio19-dev \
    libopencv-dev \
    python3-opencv \
    ffmpeg \
    git \
    curl \
    wget

echo ""

# Install Ngrok
echo "Step 3: Installing Ngrok..."
if ! command -v ngrok &> /dev/null; then
    echo "Downloading Ngrok..."
    curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null
    echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | sudo tee /etc/apt/sources.list.d/ngrok.list
    sudo apt-get update
    sudo apt-get install -y ngrok
    echo "Ngrok installed successfully"
else
    echo "Ngrok already installed"
fi

echo ""

# Create virtual environment
echo "Step 4: Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

echo ""

# Install Python dependencies
echo "Step 5: Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo ""

# Configure Mosquitto
echo "Step 6: Configuring Mosquitto MQTT broker..."
sudo cp Raspi/MQTT/mosquitto.conf /etc/mosquitto/conf.d/surveillance_car.conf

# Create log directory
sudo mkdir -p /var/log/mosquitto
sudo chown mosquitto:mosquitto /var/log/mosquitto

# Enable and start Mosquitto
sudo systemctl enable mosquitto
sudo systemctl restart mosquitto

echo "Mosquitto configured and started"

echo ""

# Configure Ngrok (if auth token provided)
echo "Step 7: Configuring Ngrok..."
if [ ! -z "$NGROK_AUTH_TOKEN" ]; then
    ngrok config add-authtoken $NGROK_AUTH_TOKEN
    echo "Ngrok auth token configured"
else
    echo "No NGROK_AUTH_TOKEN environment variable set"
    echo "You can set it later with: ngrok config add-authtoken YOUR_TOKEN"
fi

echo ""

# Create systemd service (optional)
echo "Step 8: Creating systemd service..."
cat > /tmp/surveillance-car.service << EOF
[Unit]
Description=Raspberry Pi Surveillance Car
After=network.target mosquitto.service

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
Environment="PATH=$(pwd)/venv/bin"
ExecStart=$(pwd)/venv/bin/python -m Raspi.Network.WebSockets.main
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo mv /tmp/surveillance-car.service /etc/systemd/system/
sudo systemctl daemon-reload

echo "Systemd service created (not enabled by default)"
echo "To enable: sudo systemctl enable surveillance-car"
echo "To start: sudo systemctl start surveillance-car"

echo ""

# Test installations
echo "Step 9: Testing installations..."
echo -n "Python: "
python --version
echo -n "Mosquitto: "
mosquitto -h | head -n 1
echo -n "Ngrok: "
ngrok version

echo ""

# Create run script
echo "Step 10: Creating run script..."
cat > run.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
python -m Raspi.Network.WebSockets.main
EOF

chmod +x run.sh

echo ""

echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Configure Ngrok auth token (if not done):"
echo "   export NGROK_AUTH_TOKEN=your_token_here"
echo "   ngrok config add-authtoken \$NGROK_AUTH_TOKEN"
echo ""
echo "2. Test MQTT broker:"
echo "   mosquitto_sub -h localhost -t 'dev/#' -v"
echo ""
echo "3. Start the system:"
echo "   ./run.sh"
echo ""
echo "4. Or use systemd service:"
echo "   sudo systemctl start surveillance-car"
echo ""
echo "Configuration file: Raspi/Network/WebSockets/config.py"
echo "Logs: journalctl -u surveillance-car -f"
echo ""
