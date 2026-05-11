#!/bin/bash

# Face Tracking System Installation Script
# For Raspberry Pi 4 and Linux systems

set -e  # Exit on error

echo "======================================================================"
echo "🚀 Face Recognition & Tracking System - Installation"
echo "======================================================================"
echo ""

# Detect platform
if [ -f /proc/device-tree/model ]; then
    MODEL=$(cat /proc/device-tree/model)
    if [[ $MODEL == *"Raspberry Pi"* ]]; then
        IS_RPI=true
        echo "✅ Detected: Raspberry Pi"
    else
        IS_RPI=false
        echo "✅ Detected: Linux system"
    fi
else
    IS_RPI=false
    echo "✅ Detected: Linux system"
fi

echo ""
echo "======================================================================"
echo "📦 Installing System Dependencies"
echo "======================================================================"

# Update system
echo "Updating package lists..."
sudo apt-get update

# Install build tools
echo "Installing build tools..."
sudo apt-get install -y \
    python3-pip \
    python3-dev \
    python3-venv \
    cmake \
    build-essential

# Install libraries
echo "Installing required libraries..."
sudo apt-get install -y \
    libopenblas-dev \
    liblapack-dev \
    libatlas-base-dev \
    gfortran \
    libjpeg-dev \
    libtiff-dev \
    libpng-dev \
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    libv4l-dev \
    libxvidcore-dev \
    libx264-dev \
    python3-tk

# Enable I2C for Raspberry Pi
if [ "$IS_RPI" = true ]; then
    echo ""
    echo "======================================================================"
    echo "🔧 Configuring Raspberry Pi"
    echo "======================================================================"
    
    # Enable I2C
    echo "Enabling I2C..."
    sudo raspi-config nonint do_i2c 0
    
    # Add user to i2c group
    sudo usermod -a -G i2c $USER
    
    echo "✅ I2C enabled"
    echo "   You may need to reboot for changes to take effect"
fi

echo ""
echo "======================================================================"
echo "🐍 Setting Up Python Environment"
echo "======================================================================"

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

echo ""
echo "======================================================================"
echo "📚 Installing Python Dependencies"
echo "======================================================================"

# Install dependencies
echo "Installing packages (this may take 30-60 minutes on Raspberry Pi)..."
echo ""

# Install in stages for better error handling
echo "Stage 1/4: Installing NumPy..."
pip install numpy==1.24.3

echo "Stage 2/4: Installing OpenCV..."
pip install opencv-python==4.8.1.78

echo "Stage 3/4: Installing MediaPipe (BlazeFace)..."
pip install mediapipe==0.10.9

echo "Stage 4/4: Installing face_recognition (this takes longest)..."
pip install face-recognition==1.3.0

# Install remaining packages
echo "Installing remaining packages..."
pip install Pillow scipy imutils

# Install servo libraries for Raspberry Pi
if [ "$IS_RPI" = true ]; then
    echo "Installing servo control libraries..."
    pip install adafruit-circuitpython-servokit adafruit-circuitpython-pca9685
fi

# Optional: Install YOLO
read -p "📥 Install YOLOv8 (optional, for alternative detection)? (y/N): " install_yolo
if [[ $install_yolo =~ ^[Yy]$ ]]; then
    echo "Installing YOLOv8..."
    pip install ultralytics==8.1.0
fi

echo ""
echo "======================================================================"
echo "🔧 Setting Up Project"
echo "======================================================================"

# Run setup script
python download_models.py

# Update config for Raspberry Pi
if [ "$IS_RPI" = true ]; then
    echo ""
    echo "Configuring for Raspberry Pi..."
    
    # Update config.py
    sed -i 's/IS_RASPBERRY_PI = False/IS_RASPBERRY_PI = True/' config.py
    
    echo "✅ Configuration updated for Raspberry Pi"
    echo ""
    echo "⚠️  IMPORTANT: To enable servo control, edit config.py and set:"
    echo "   ENABLE_SERVO_CONTROL = True"
fi

echo ""
echo "======================================================================"
echo "✅ Installation Complete!"
echo "======================================================================"
echo ""
echo "📋 Next Steps:"
echo ""
echo "1. Activate virtual environment:"
echo "   source venv/bin/activate"
echo ""
echo "2. Test the system:"
echo "   python test_system.py"
echo ""
echo "3. Enroll your face:"
echo "   python gui_tracker.py"
echo "   (Select 'Enroll New Face' mode)"
echo ""
echo "4. Start tracking:"
echo "   python gui_tracker.py"
echo ""

if [ "$IS_RPI" = true ]; then
    echo "🤖 Raspberry Pi Specific:"
    echo ""
    echo "- I2C has been enabled"
    echo "- Reboot recommended: sudo reboot"
    echo "- Wire servos to PCA9685 board"
    echo "- Test I2C: sudo i2cdetect -y 1"
    echo "- Enable servos in config.py: ENABLE_SERVO_CONTROL = True"
    echo ""
fi

echo "📚 Documentation:"
echo "- Quick Start: QUICK_START.md"
echo "- Full Guide: README.md"
echo ""
echo "======================================================================"
echo "Happy Tracking! 🎯"
echo "======================================================================"
