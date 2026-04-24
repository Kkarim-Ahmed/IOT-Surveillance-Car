#!/bin/bash
# =============================================================
#  setup_mqtt_broker.sh — Install and start Mosquitto MQTT broker
#
#  Tested on: Ubuntu 20.04+, Raspberry Pi OS (Debian-based)
#
#  Usage:
#    chmod +x setup_mqtt_broker.sh
#    ./setup_mqtt_broker.sh
# =============================================================

set -e   # exit immediately on error

echo "============================================="
echo "  Mosquitto MQTT Broker — Setup Script"
echo "============================================="

# ── 1. Update package list ────────────────────────────────────────────────────
echo ""
echo "[1/4] Updating package list..."
sudo apt-get update -y

# ── 2. Install Mosquitto ──────────────────────────────────────────────────────
echo ""
echo "[2/4] Installing mosquitto and mosquitto-clients..."
sudo apt-get install -y mosquitto mosquitto-clients

# ── 3. Copy config file ───────────────────────────────────────────────────────
echo ""
echo "[3/4] Copying mosquitto.conf..."
CONF_SRC="$(dirname "$0")/mosquitto.conf"
CONF_DST="/etc/mosquitto/conf.d/surveillance-car.conf"

if [ -f "$CONF_SRC" ]; then
    sudo cp "$CONF_SRC" "$CONF_DST"
    echo "  Config copied to $CONF_DST"
else
    echo "  mosquitto.conf not found at $CONF_SRC — using Mosquitto defaults"
fi

# ── 4. Enable and start service ───────────────────────────────────────────────
echo ""
echo "[4/4] Enabling and starting Mosquitto service..."
sudo systemctl enable mosquitto
sudo systemctl restart mosquitto

# ── Status check ──────────────────────────────────────────────────────────────
echo ""
echo "============================================="
if systemctl is-active --quiet mosquitto; then
    echo "  ✓ Mosquitto is running on port 1883"
    echo "  Test with:"
    echo "    mosquitto_sub -t 'dev/status' &"
    echo "    mosquitto_pub -t 'dev/motor' -m '{\"direction\":\"forward\",\"speed\":80}'"
else
    echo "  ✗ Mosquitto failed to start — check: sudo journalctl -u mosquitto"
fi
echo "============================================="
