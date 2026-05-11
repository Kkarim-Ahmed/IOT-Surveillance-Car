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

# Start the system (includes custom MQTT broker)
echo "Starting Raspberry Pi Surveillance Car with Custom MQTT Broker..."
python -m Raspi.Network.WebSockets.main
