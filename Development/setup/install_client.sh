#!/bin/bash
# =============================================================
#  install_client.sh — Install Python dependencies for the
#  MQTT surveillance car client (laptop / dev machine)
#
#  Usage:
#    chmod +x install_client.sh
#    ./install_client.sh
# =============================================================

set -e

echo "============================================="
echo "  Surveillance Car — Client Setup"
echo "============================================="

# ── 1. Check Python ───────────────────────────────────────────────────────────
echo ""
echo "[1/4] Checking Python version..."
python3 --version || { echo "  ERROR: Python 3 not found. Install it first."; exit 1; }

# ── 2. Create virtual environment ────────────────────────────────────────────
VENV_DIR="$(dirname "$0")/../.venv-client"
echo ""
echo "[2/4] Creating virtual environment at $VENV_DIR..."
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

# ── 3. Install dependencies ───────────────────────────────────────────────────
echo ""
echo "[3/4] Installing Python packages..."
pip install --upgrade pip --quiet
pip install \
    paho-mqtt==1.6.1 \
    --quiet

echo "  ✓ paho-mqtt installed"

# ── 4. Verify ─────────────────────────────────────────────────────────────────
echo ""
echo "[4/4] Verifying installation..."
python3 -c "import paho.mqtt.client; print('  ✓ paho-mqtt import OK')"

echo ""
echo "============================================="
echo "  Setup complete!"
echo ""
echo "  Activate the environment:"
echo "    source $VENV_DIR/bin/activate"
echo ""
echo "  Run the GUI controller:"
echo "    python mqtt_gui_controller.py"
echo ""
echo "  Run the CLI tester:"
echo "    python mqtt_client_tester.py"
echo "============================================="
