#!/bin/bash

# Raspberry Pi Surveillance Car - Run Script
# Activates virtual environment and starts the system

cd "$(dirname "$0")"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Error: Virtual environment not found"
    echo "Run setup.sh first: ./setup.sh"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Check if Mosquitto is running
if ! systemctl is-active --quiet mosquitto; then
    echo "Warning: Mosquitto MQTT broker is not running"
    echo "Starting Mosquitto..."
    sudo systemctl start mosquitto
fi

# Start the system
echo "Starting Raspberry Pi Surveillance Car..."
python -m Raspi.Network.WebSockets.main
