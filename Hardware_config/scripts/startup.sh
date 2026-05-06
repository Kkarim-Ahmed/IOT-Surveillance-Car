#!/bin/bash
# Startup script for hardware control system

echo "=========================================="
echo "Hardware Control System - Starting"
echo "=========================================="

# Check if running on Raspberry Pi
if [ ! -f /proc/device-tree/model ]; then
    echo "WARNING: Not running on Raspberry Pi"
    echo "Running in simulation mode..."
fi

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python version: $PYTHON_VERSION"

# Create necessary directories
echo "Creating directories..."
mkdir -p logs
mkdir -p snapshots

# Check GPIO permissions
if [ -e /dev/gpiomem ]; then
    if [ ! -r /dev/gpiomem ] || [ ! -w /dev/gpiomem ]; then
        echo "WARNING: No GPIO permissions"
        echo "Run: sudo usermod -a -G gpio $USER"
        echo "Then reboot"
    fi
fi

# Start the application
echo ""
echo "Starting hardware control system..."
echo "=========================================="
python3 main.py

# Cleanup on exit
echo ""
echo "=========================================="
echo "System stopped"
echo "=========================================="
