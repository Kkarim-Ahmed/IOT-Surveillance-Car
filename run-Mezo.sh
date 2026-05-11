#!/bin/bash

# Quick launch script for Face Tracking System

echo "======================================================================"
echo "Face Recognition & Tracking System"
echo "======================================================================"
echo ""
echo "1) Launch GUI"
echo "2) Exit"
echo ""
read -p "Enter choice [1-2]: " choice

case $choice in
    1)
        echo ""
        echo "Launching GUI..."
        cd desktop && python3 gui_tracker.py
        ;;
    2)
        echo "Goodbye!"
        exit 0
        ;;
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac
