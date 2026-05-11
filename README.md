# Face Recognition & Tracking System for Raspberry Pi 4

A real-time face recognition and tracking system optimized for Raspberry Pi 4 with servo motor control, custom face enrollment, and coordinate extraction capabilities.

## 🎯 Features

- **BlazeFace Detection**: Ultra-fast face detection using MediaPipe (optimized for edge devices)
- **Face Recognition**: Custom face enrollment with face_recognition library (dlib-based)
- **Servo Tracking**: PID-controlled pan/tilt servos via PCA9685 I2C driver
- **Multi-Core Processing**: Optimized to use 3 CPU cores, leaving 1 for OS
- **GUI Interface**: Easy-to-use Tkinter GUI for enrollment and monitoring
- **Tiny LLM Assistant (Optional)**: Event-driven local assistant hints using `llama.cpp`/GGUF (Pi-friendly profiles)
- **Three Operating Modes**:
  - 🎯 **Tracking Mode**: Real-time face tracking with servo control
  - 👤 **Enrollment Mode**: Add new faces to the recognition database
  - 📍 **Coordinate Mode**: Extract (X, Y) coordinates of detected faces

## 📋 Requirements

### Hardware
- Raspberry Pi 4 Model B (4GB RAM recommended)
- USB Webcam or Raspberry Pi Camera Module
- PCA9685 16-Channel PWM Servo Driver
- 2x Servo Motors (pan and tilt)
- Power supply for servos (5V, 2-3A)

### Software
- Python 3.7+
- Raspberry Pi OS (Bullseye or later)

## 🚀 Installation

### 1. Clone or Download the Project

```bash
cd ~
mkdir face_tracking_system
cd face_tracking_system
# Copy all project files here
```

### 2. Install System Dependencies

```bash
# Update system
sudo apt-get update
sudo apt-get upgrade -y

# Install required packages
sudo apt-get install -y python3-pip python3-dev
sudo apt-get install -y cmake libopenblas-dev liblapack-dev
sudo apt-get install -y libatlas-base-dev gfortran
sudo apt-get install -y libjpeg-dev libtiff-dev libpng-dev
sudo apt-get install -y libavcodec-dev libavformat-dev libswscale-dev libv4l-dev
sudo apt-get install -y libxvidcore-dev libx264-dev
sudo apt-get install -y python3-tk

# Enable I2C for PCA9685
sudo raspi-config
# Navigate to: Interface Options -> I2C -> Enable
```

### 3. Install Python Dependencies

```bash
# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

**Note**: Installing dlib and face_recognition on Raspberry Pi can take 30-60 minutes due to compilation.

### 4. Configure for Raspberry Pi

Edit `config.py`:

```python
IS_RASPBERRY_PI = True  # Set to True when running on Pi
ENABLE_SERVO_CONTROL = True  # Enable servo motors
```

## 📖 Usage

### Option 1: GUI Application (Recommended)

```bash
python gui_tracker.py
```

The GUI provides:
- Live video feed with face detection/recognition
- Mode selection (Tracking, Enrollment, Coordinate Extraction)
- Servo control and status
- System information
- Tiny LLM assistant panel (enable/disable + Pi/balanced/quality profiles)
- Coordinate export to CSV with stabilized/normalized center values

### Tiny LLM (Optional, local)

1. Install runtime:
```bash
pip install llama-cpp-python
```
2. Put a GGUF model at:
```bash
models/qwen2.5-1.5b-instruct-q4_k_m.gguf
```
3. In GUI, enable **Tiny LLM Assistant** and select **pi_fast** profile for Raspberry Pi.

### Option 2: Command-Line Application

```bash
python main.py
```

Keyboard controls:
- `q`: Quit
- `r`: Reset servos to center
- `s`: Save current frame

## 👤 Enrolling New Faces

### Method 1: Using GUI (Easiest)

1. Launch `python gui_tracker.py`
2. Select "Enroll New Face" mode
3. Click "Start Enrollment"
4. Enter person's name
5. Position face in frame
6. Click "Capture Image" 5 times (different angles/expressions)
7. Click "Finish Enrollment"

### Method 2: Using Command-Line Script

**Capture from camera:**
```bash
python enroll_faces.py --mode camera --name "John Doe" --count 5
```

**From existing images:**
```bash
python enroll_faces.py --mode images --name "John Doe" --images photo1.jpg photo2.jpg photo3.jpg
```

**From directory structure:**
```bash
# Directory structure: known_faces/images/PersonName/*.jpg
python enroll_faces.py --mode directory --directory known_faces/images
```

### Method 3: Manual Directory Setup

1. Create directory structure:
```
known_faces/
└── images/
    ├── John_Doe/
    │   ├── john_1.jpg
    │   ├── john_2.jpg
    │   └── john_3.jpg
    └── Jane_Smith/
        ├── jane_1.jpg
        └── jane_2.jpg
```

2. Run enrollment:
```bash
python enroll_faces.py --mode directory --directory known_faces/images
```

## 🎛️ PID Tuning Guide

The PID controller parameters are in `config.py`:

```python
# PAN (Horizontal) PID parameters
PAN_KP = 0.08  # Proportional gain - responsiveness
PAN_KI = 0.001  # Integral gain - eliminates steady-state error
PAN_KD = 0.02  # Derivative gain - reduces overshoot

# TILT (Vertical) PID parameters
TILT_KP = 0.08
TILT_KI = 0.001
TILT_KD = 0.02
```

### Tuning Process:

1. **Start with P only** (set KI=0, KD=0):
   - Increase KP until system oscillates
   - Reduce KP by 50%

2. **Add D term**:
   - Increase KD to reduce overshoot
   - Typical range: KD = 0.1 to 0.5 × KP

3. **Add I term** (optional):
   - Small KI (0.001-0.01) to eliminate drift
   - Too high causes instability

### Symptoms and Solutions:

| Symptom | Solution |
|---------|----------|
| Slow response | Increase KP |
| Oscillation | Decrease KP, increase KD |
| Overshoot | Increase KD |
| Steady-state error | Increase KI (slightly) |
| Jittery movement | Decrease KP, increase SMOOTHING_FACTOR |

## ⚙️ Configuration Options

Edit `config.py` to customize:

### Camera Settings
```python
CAMERA_INDEX = 0  # Camera device index
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
FPS_TARGET = 30
```

### Detection Settings
```python
YOLO_CONFIDENCE = 0.5  # Detection confidence threshold
MIN_FACE_SIZE = 50  # Minimum face size in pixels
PROCESS_EVERY_N_FRAMES = 2  # Process recognition every N frames
```

### Servo Settings
```python
PAN_MIN = 0  # Minimum pan angle
PAN_MAX = 180  # Maximum pan angle
PAN_CENTER = 90  # Center position

TILT_MIN = 0
TILT_MAX = 180
TILT_CENTER = 90

MAX_SERVO_SPEED = 5  # Max degrees per frame
```

### Tracking Settings
```python
DEADZONE_X = 30  # Pixels - don't move if within this range
DEADZONE_Y = 30
SMOOTHING_FACTOR = 0.3  # 0-1, lower = smoother
```

## 🔧 Hardware Setup

### PCA9685 Wiring

```
PCA9685 -> Raspberry Pi
VCC     -> 3.3V (Pin 1)
GND     -> GND (Pin 6)
SDA     -> GPIO 2 (Pin 3)
SCL     -> GPIO 3 (Pin 5)

PCA9685 -> Servos
V+      -> 5V Power Supply (+)
GND     -> 5V Power Supply (-) and Pi GND
Channel 0 -> Pan Servo Signal
Channel 1 -> Tilt Servo Signal
```

**Important**: 
- Servos need external 5V power supply (2-3A)
- Connect power supply GND to Pi GND (common ground)
- Do NOT power servos from Pi's 5V pin

### Servo Mounting

```
        [Camera]
           |
      [Tilt Servo]
           |
      [Pan Servo]
           |
        [Base]
```

## 📊 Performance Optimization

### For Raspberry Pi 4:

1. **Use BlazeFace** (default): Fastest detection (~15-20 FPS)
2. **Frame skipping**: Process recognition every 2-5 frames
3. **Resolution**: 640x480 is optimal balance
4. **CPU cores**: System uses 3 cores, leaves 1 for OS

### Performance Modes:

**High Performance** (config.py):
```python
PROCESS_EVERY_N_FRAMES = 5  # Process every 5th frame
FRAME_WIDTH = 320
FRAME_HEIGHT = 240
FACE_RECOGNITION_MODEL = "hog"  # Faster than CNN
```

**High Accuracy** (config.py):
```python
PROCESS_EVERY_N_FRAMES = 1  # Every frame
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
RECOGNITION_TOLERANCE = 0.5  # Stricter matching
```

## 📍 Coordinate Extraction Mode

Extract face coordinates for custom applications:

1. Switch to "Coordinate Extraction" mode in GUI
2. Click "Extract Coordinates"
3. View coordinates in the text panel:
   ```
   Face 1: John Doe
     Center: (320, 240)
     BBox: (150, 450, 350, 250)
   ```

Coordinates are relative to frame:
- Center: (X, Y) of face center
- BBox: (top, right, bottom, left) in pixels

## 🐛 Troubleshooting

### Camera not detected
```bash
# List video devices
ls /dev/video*

# Test camera
raspistill -o test.jpg  # For Pi Camera
```

### I2C not working
```bash
# Check I2C devices
sudo i2cdetect -y 1

# Should show device at 0x40 (PCA9685)
```

### Servos not moving
1. Check power supply (5V, 2-3A minimum)
2. Verify I2C connection: `sudo i2cdetect -y 1`
3. Check `config.py`: `ENABLE_SERVO_CONTROL = True`
4. Test servos manually:
```python
from adafruit_servokit import ServoKit
kit = ServoKit(channels=16)
kit.servo[0].angle = 90  # Pan center
kit.servo[1].angle = 90  # Tilt center
```

### Low FPS
1. Reduce resolution in `config.py`
2. Increase `PROCESS_EVERY_N_FRAMES`
3. Use BlazeFace instead of YOLO
4. Close other applications

### Face recognition not working
1. Ensure faces are enrolled: `python enroll_faces.py --mode directory --directory known_faces/images`
2. Check `known_faces/encodings.pkl` exists
3. Adjust `RECOGNITION_TOLERANCE` (higher = more lenient)

## 📁 Project Structure

```
face_tracking_system/
├── main.py                      # Command-line application
├── gui_tracker.py               # GUI application
├── enroll_faces.py              # Face enrollment script
├── config.py                    # Configuration settings
├── blazeface_detector.py        # BlazeFace detection module
├── yolo_face_detector.py        # YOLO detection module (alternative)
├── face_recognition_module.py   # Face recognition system
├── servo_control.py             # Servo motor control
├── pid_controller.py            # PID controller implementation
├── requirements.txt             # Python dependencies
├── README.md                    # This file
└── known_faces/
    ├── images/                  # Face images for enrollment
    │   ├── Person1/
    │   └── Person2/
    └── encodings.pkl            # Stored face encodings
```

## 🎓 How It Works

### 1. Face Detection
- **BlazeFace** (MediaPipe): Ultra-fast CNN optimized for mobile/edge devices
- Detects faces in real-time at 15-20 FPS on Raspberry Pi 4
- Returns bounding boxes for each detected face

### 2. Face Recognition
- Uses **dlib's face recognition** model (128-dimensional embeddings)
- Compares detected faces against enrolled face database
- Returns name and confidence score for each face

### 3. Coordinate Computation
- Calculates face center: `(x, y) = ((left + right) / 2, (top + bottom) / 2)`
- Computes error from frame center: `error = frame_center - face_center`
- Applies exponential smoothing to reduce jitter

### 4. PID Control
- **Proportional (P)**: Responds to current error
- **Integral (I)**: Eliminates steady-state error
- **Derivative (D)**: Reduces overshoot and oscillation
- Output: servo angle adjustment in degrees

### 5. Servo Control
- PCA9685 generates PWM signals for servos
- Pan servo: horizontal tracking (0-180°)
- Tilt servo: vertical tracking (0-180°)
- Speed limiting prevents jerky movements

## 🔒 Privacy & Security

- All face data stored locally (no cloud)
- Face encodings are one-way (cannot reconstruct original image)
- Delete `known_faces/encodings.pkl` to remove all enrolled faces

## 📝 License

This project is provided as-is for educational and personal use.

## 🤝 Contributing

Feel free to submit issues, fork the repository, and create pull requests for any improvements.

## 📧 Support

For issues and questions:
1. Check the Troubleshooting section
2. Review configuration in `config.py`
3. Test individual components (camera, servos, detection)

## 🎉 Acknowledgments

- **MediaPipe** (Google) for BlazeFace
- **dlib** for face recognition
- **Adafruit** for PCA9685 libraries
- **Ultralytics** for YOLOv8

---

**Happy Tracking! 🎯**
