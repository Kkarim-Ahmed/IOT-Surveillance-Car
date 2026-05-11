#!/bin/bash
# start_with_ngrok.sh
# Quick start script for Raspberry Pi surveillance system with Ngrok tunneling

set -e  # Exit on error

echo "=========================================="
echo "Raspberry Pi Surveillance System"
echo "Starting with Ngrok WAN Access"
echo "=========================================="
echo ""

# Check if auth token is set
if [ -z "$NGROK_AUTH_TOKEN" ]; then
    echo "⚠️  NGROK_AUTH_TOKEN not set!"
    echo ""
    echo "Please set your Ngrok auth token:"
    echo "  1. Get token from: https://dashboard.ngrok.com/get-started/your-authtoken"
    echo "  2. Run: export NGROK_AUTH_TOKEN='your_token_here'"
    echo "  3. Run this script again"
    echo ""
    exit 1
fi

# Enable Ngrok
export NGROK_ENABLED=true

# Set default region if not specified
if [ -z "$NGROK_REGION" ]; then
    export NGROK_REGION=us
    echo "Using default region: us"
    echo "To change: export NGROK_REGION=eu (or ap, au, sa, jp, in)"
    echo ""
fi

# Check Python dependencies
echo "Checking dependencies..."
python3 -c "import pyngrok" 2>/dev/null || {
    echo "⚠️  pyngrok not installed. Installing..."
    pip3 install pyngrok
}

python3 -c "import websockets" 2>/dev/null || {
    echo "⚠️  websockets not installed. Installing all dependencies..."
    pip3 install -r requirements.txt
}

echo "✓ Dependencies OK"
echo ""

# Start the system
echo "Starting surveillance system..."
echo "Press Ctrl+C to stop"
echo ""

python3 main.py
