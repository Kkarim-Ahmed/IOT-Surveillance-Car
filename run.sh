#!/bin/bash

# Quick launch script for Face Tracking System

echo "======================================================================"
echo "🎯 Face Recognition & Tracking System"
echo "======================================================================"
echo ""
echo "Select mode:"
echo "1) GUI Application (Recommended)"
echo "2) Command-line Application"
echo "3) Enroll New Face"
echo "4) Test System"
echo "5) Exit"
echo ""
read -p "Enter choice [1-5]: " choice

case $choice in
    1)
        echo ""
        echo "🚀 Launching GUI Application..."
        python3 gui_tracker.py
        ;;
    2)
        echo ""
        echo "🚀 Launching Command-line Application..."
        echo "   Controls: q=quit, r=reset servos, s=save frame"
        python3 main.py
        ;;
    3)
        echo ""
        echo "👤 Face Enrollment"
        echo ""
        read -p "Enter person's name: " name
        read -p "Number of images to capture [5]: " count
        count=${count:-5}
        python3 enroll_faces.py --mode camera --name "$name" --count $count
        ;;
    4)
        echo ""
        echo "🧪 Running System Tests..."
        python3 test_system.py
        ;;
    5)
        echo "Goodbye!"
        exit 0
        ;;
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac
