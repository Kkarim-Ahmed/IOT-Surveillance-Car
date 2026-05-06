#!/usr/bin/env python3
"""
Simple Webcam Streaming Server for Raspberry Pi
Provides MJPEG stream over HTTP without AI processing
Perfect for testing camera connectivity
"""

import cv2
from flask import Flask, Response, render_template_string
import threading
import time
import argparse

app = Flask(__name__)

# Global variables
camera = None
camera_lock = threading.Lock()
frame_count = 0
fps = 0
last_time = time.time()

# HTML template for viewing stream
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Raspberry Pi Camera Stream</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background-color: #1a1a1a;
            color: #ffffff;
            margin: 0;
            padding: 20px;
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        h1 {
            color: #4CAF50;
            margin-bottom: 10px;
        }
        .info {
            background-color: #2a2a2a;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            max-width: 640px;
            width: 100%;
        }
        .info p {
            margin: 5px 0;
        }
        .stream-container {
            background-color: #000;
            padding: 10px;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        }
        img {
            display: block;
            max-width: 100%;
            height: auto;
            border-radius: 4px;
        }
        .status {
            color: #4CAF50;
            font-weight: bold;
        }
        .controls {
            margin-top: 20px;
            display: flex;
            gap: 10px;
        }
        button {
            background-color: #4CAF50;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
        }
        button:hover {
            background-color: #45a049;
        }
        button:active {
            background-color: #3d8b40;
        }
    </style>
    <script>
        function refreshStream() {
            var img = document.getElementById('stream');
            img.src = img.src.split('?')[0] + '?t=' + new Date().getTime();
        }
        
        function updateInfo() {
            fetch('/info')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('fps').textContent = data.fps.toFixed(1);
                    document.getElementById('frames').textContent = data.frame_count;
                });
        }
        
        setInterval(updateInfo, 1000);
    </script>
</head>
<body>
    <h1>🎥 Raspberry Pi Camera Stream</h1>
    
    <div class="info">
        <p><span class="status">● LIVE</span></p>
        <p>Resolution: {{ width }}x{{ height }}</p>
        <p>FPS: <span id="fps">0</span></p>
        <p>Frames Captured: <span id="frames">0</span></p>
        <p>Device: /dev/video{{ device }}</p>
    </div>
    
    <div class="stream-container">
        <img id="stream" src="{{ url_for('video_feed') }}" width="{{ width }}" height="{{ height }}">
    </div>
    
    <div class="controls">
        <button onclick="refreshStream()">🔄 Refresh Stream</button>
        <button onclick="window.location.href='/snapshot'">📸 Take Snapshot</button>
    </div>
</body>
</html>
'''

def get_camera(device_index, width, height, fps_target):
    """Initialize and return camera object"""
    global camera
    if camera is None:
        print(f"[CAMERA] Initializing camera on /dev/video{device_index}")
        camera = cv2.VideoCapture(device_index)
        
        if not camera.isOpened():
            print(f"[ERROR] Cannot open camera /dev/video{device_index}")
            return None
        
        # Set camera properties
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        camera.set(cv2.CAP_PROP_FPS, fps_target)
        
        # Verify settings
        actual_width = camera.get(cv2.CAP_PROP_FRAME_WIDTH)
        actual_height = camera.get(cv2.CAP_PROP_FRAME_HEIGHT)
        actual_fps = camera.get(cv2.CAP_PROP_FPS)
        
        print(f"[CAMERA] Resolution: {int(actual_width)}x{int(actual_height)}")
        print(f"[CAMERA] FPS: {int(actual_fps)}")
        print(f"[CAMERA] Camera initialized successfully!")
        
    return camera

def generate_frames(device_index, width, height, fps_target, quality):
    """Generate frames for MJPEG stream"""
    global frame_count, fps, last_time
    
    cam = get_camera(device_index, width, height, fps_target)
    if cam is None:
        return
    
    while True:
        with camera_lock:
            success, frame = cam.read()
        
        if not success:
            print("[WARNING] Failed to read frame")
            time.sleep(0.1)
            continue
        
        # Update FPS counter
        frame_count += 1
        current_time = time.time()
        if current_time - last_time >= 1.0:
            fps = frame_count / (current_time - last_time)
            frame_count = 0
            last_time = current_time
        
        # Add FPS overlay
        cv2.putText(frame, f"FPS: {fps:.1f}", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        # Encode frame as JPEG
        ret, buffer = cv2.imencode('.jpg', frame, 
                                   [cv2.IMWRITE_JPEG_QUALITY, quality])
        
        if not ret:
            continue
        
        frame_bytes = buffer.tobytes()
        
        # Yield frame in multipart format
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.route('/video_feed')
def video_feed():
    """Video streaming route"""
    return Response(generate_frames(
        app.config['DEVICE_INDEX'],
        app.config['WIDTH'],
        app.config['HEIGHT'],
        app.config['FPS'],
        app.config['QUALITY']
    ), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/')
def index():
    """Main page with video stream"""
    return render_template_string(
        HTML_TEMPLATE,
        width=app.config['WIDTH'],
        height=app.config['HEIGHT'],
        device=app.config['DEVICE_INDEX']
    )

@app.route('/info')
def info():
    """Return stream information as JSON"""
    return {
        'fps': fps,
        'frame_count': frame_count,
        'resolution': f"{app.config['WIDTH']}x{app.config['HEIGHT']}",
        'device': app.config['DEVICE_INDEX']
    }

@app.route('/snapshot')
def snapshot():
    """Capture and return a single frame"""
    cam = get_camera(
        app.config['DEVICE_INDEX'],
        app.config['WIDTH'],
        app.config['HEIGHT'],
        app.config['FPS']
    )
    
    if cam is None:
        return "Camera not available", 500
    
    with camera_lock:
        success, frame = cam.read()
    
    if not success:
        return "Failed to capture frame", 500
    
    # Encode as JPEG
    ret, buffer = cv2.imencode('.jpg', frame, 
                               [cv2.IMWRITE_JPEG_QUALITY, app.config['QUALITY']])
    
    if not ret:
        return "Failed to encode frame", 500
    
    return Response(buffer.tobytes(), mimetype='image/jpeg')

def cleanup():
    """Cleanup camera resources"""
    global camera
    if camera is not None:
        camera.release()
        print("[CAMERA] Camera released")

def main():
    parser = argparse.ArgumentParser(description='Simple Webcam Streaming Server')
    parser.add_argument('--device', type=int, default=0,
                       help='Camera device index (default: 0 for /dev/video0)')
    parser.add_argument('--width', type=int, default=640,
                       help='Frame width (default: 640)')
    parser.add_argument('--height', type=int, default=480,
                       help='Frame height (default: 480)')
    parser.add_argument('--fps', type=int, default=30,
                       help='Target FPS (default: 30)')
    parser.add_argument('--quality', type=int, default=70,
                       help='JPEG quality 1-100 (default: 70)')
    parser.add_argument('--port', type=int, default=5000,
                       help='Server port (default: 5000)')
    parser.add_argument('--host', type=str, default='0.0.0.0',
                       help='Server host (default: 0.0.0.0)')
    
    args = parser.parse_args()
    
    # Store configuration in Flask app
    app.config['DEVICE_INDEX'] = args.device
    app.config['WIDTH'] = args.width
    app.config['HEIGHT'] = args.height
    app.config['FPS'] = args.fps
    app.config['QUALITY'] = args.quality
    
    print("=" * 60)
    print("🎥 Raspberry Pi Webcam Streaming Server")
    print("=" * 60)
    print(f"Camera Device: /dev/video{args.device}")
    print(f"Resolution: {args.width}x{args.height}")
    print(f"Target FPS: {args.fps}")
    print(f"JPEG Quality: {args.quality}")
    print(f"Server: http://{args.host}:{args.port}")
    print("=" * 60)
    print("\n📡 Starting server...")
    print(f"🌐 Access stream at: http://<raspberry-pi-ip>:{args.port}")
    print("Press Ctrl+C to stop\n")
    
    try:
        app.run(host=args.host, port=args.port, threaded=True, debug=False)
    except KeyboardInterrupt:
        print("\n[SYSTEM] Shutting down...")
    finally:
        cleanup()

if __name__ == '__main__':
    main()
