"""
Face Recognition and Tracking System
Main application with real-time face detection, recognition, and servo tracking
"""
import cv2
import time
import numpy as np
from collections import deque
import config
from camera_utils import open_camera, read_frame
from blazeface_detector import BlazeFaceDetector
from yolo_face_detector import YOLOFaceDetector, HOGFaceDetector
from face_recognition_module import FaceRecognitionSystem
from servo_control import FaceTrackingServo


class FaceTrackingSystem:
    """
    Complete face tracking system with detection, recognition, and servo control
    """
    
    def __init__(self, detector_type="blazeface"):
        """
        Initialize face tracking system
        
        Args:
            detector_type: "blazeface" (fastest), "yolo", or "hog"
        """
        print("=" * 60)
        print("🚀 Initializing Face Recognition & Tracking System")
        print("=" * 60)
        
        # Initialize face detector
        if detector_type == "blazeface":
            try:
                self.detector = BlazeFaceDetector()
            except Exception as e:
                print(f"⚠️  BlazeFace initialization failed: {e}")
                print("   Falling back to HOG detector")
                self.detector = HOGFaceDetector()
        elif detector_type == "yolo":
            try:
                self.detector = YOLOFaceDetector()
            except Exception as e:
                print(f"⚠️  YOLO initialization failed: {e}")
                print("   Falling back to HOG detector")
                self.detector = HOGFaceDetector()
        else:
            self.detector = HOGFaceDetector()
        
        # Initialize face recognition
        self.recognizer = FaceRecognitionSystem()
        print(f"📊 Loaded {self.recognizer.get_face_count()} known faces")
        
        # Initialize servo control
        self.servo = FaceTrackingServo()
        
        # Initialize camera
        self.cap = open_camera()
        if not self.cap.isOpened():
            raise RuntimeError("❌ Failed to open camera")
        
        print(f"📷 Camera initialized: {config.FRAME_WIDTH}x{config.FRAME_HEIGHT} @ {config.FPS_TARGET}fps")
        
        # Performance tracking
        self.fps_queue = deque(maxlen=30)
        self.frame_count = 0
        
        # Tracking state
        self.tracked_face = None  # (center_x, center_y, name)
        self.smoothed_position = None
        
        print("=" * 60)
        print("✅ System initialized successfully!")
        print("=" * 60)
    
    def calculate_face_center(self, face_location):
        """
        Calculate center coordinates of face bounding box
        
        Args:
            face_location: (top, right, bottom, left)
            
        Returns:
            Tuple (center_x, center_y)
        """
        top, right, bottom, left = face_location
        center_x = (left + right) // 2
        center_y = (top + bottom) // 2
        return center_x, center_y
    
    def smooth_position(self, new_x, new_y):
        """
        Apply exponential smoothing to face position
        
        Args:
            new_x, new_y: New face center coordinates
            
        Returns:
            Smoothed (x, y) coordinates
        """
        if self.smoothed_position is None:
            self.smoothed_position = (new_x, new_y)
            return new_x, new_y
        
        alpha = config.SMOOTHING_FACTOR
        smooth_x = int(alpha * new_x + (1 - alpha) * self.smoothed_position[0])
        smooth_y = int(alpha * new_y + (1 - alpha) * self.smoothed_position[1])
        
        self.smoothed_position = (smooth_x, smooth_y)
        return smooth_x, smooth_y
    
    def select_tracking_target(self, face_locations, recognition_results):
        """
        Select which face to track (prioritize known faces)
        
        Args:
            face_locations: List of face bounding boxes
            recognition_results: List of (name, confidence) tuples
            
        Returns:
            Index of face to track, or None
        """
        if len(face_locations) == 0:
            return None
        
        # If only one face, track it
        if len(face_locations) == 1:
            return 0
        
        # Prioritize known faces
        for i, (name, confidence) in enumerate(recognition_results):
            if name != "Unknown" and confidence > 0.5:
                return i
        
        # If no known faces, track the largest face
        largest_area = 0
        largest_index = 0
        
        for i, (top, right, bottom, left) in enumerate(face_locations):
            area = (right - left) * (bottom - top)
            if area > largest_area:
                largest_area = area
                largest_index = i
        
        return largest_index
    
    def draw_ui(self, frame, face_locations, recognition_results, fps):
        """
        Draw UI elements on frame
        
        Args:
            frame: Image to draw on
            face_locations: List of face bounding boxes
            recognition_results: List of (name, confidence) tuples
            fps: Current FPS
            
        Returns:
            Annotated frame
        """
        annotated = frame.copy()
        
        # Draw face boxes and labels
        for i, (top, right, bottom, left) in enumerate(face_locations):
            name, confidence = recognition_results[i] if i < len(recognition_results) else ("Unknown", 0.0)
            
            # Choose color based on recognition
            if name != "Unknown":
                color = (0, 255, 0)  # Green for known faces
            else:
                color = (0, 165, 255)  # Orange for unknown faces
            
            # Draw bounding box
            cv2.rectangle(annotated, (left, top), (right, bottom), color, 2)
            
            # Draw label background
            label = f"{name} ({confidence:.2f})" if name != "Unknown" else "Unknown"
            label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            cv2.rectangle(
                annotated,
                (left, top - label_size[1] - 10),
                (left + label_size[0], top),
                color,
                -1
            )
            
            # Draw label text
            cv2.putText(
                annotated,
                label,
                (left, top - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                2
            )
            
            # Draw face center
            center_x, center_y = self.calculate_face_center((top, right, bottom, left))
            cv2.circle(annotated, (center_x, center_y), 5, color, -1)
        
        # Draw frame center crosshair
        frame_h, frame_w = frame.shape[:2]
        center_x, center_y = frame_w // 2, frame_h // 2
        cv2.line(annotated, (center_x - 20, center_y), (center_x + 20, center_y), (255, 0, 0), 2)
        cv2.line(annotated, (center_x, center_y - 20), (center_x, center_y + 20), (255, 0, 0), 2)
        
        # Draw deadzone
        cv2.rectangle(
            annotated,
            (center_x - config.DEADZONE_X, center_y - config.DEADZONE_Y),
            (center_x + config.DEADZONE_X, center_y + config.DEADZONE_Y),
            (255, 0, 0),
            1
        )
        
        # Draw FPS
        if config.SHOW_FPS:
            cv2.putText(
                annotated,
                f"FPS: {fps:.1f}",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2
            )
        
        # Draw servo status
        servo_status = self.servo.get_status()
        if servo_status["enabled"]:
            status_text = f"Pan: {servo_status['pan_angle']:.1f}° | Tilt: {servo_status['tilt_angle']:.1f}°"
            cv2.putText(
                annotated,
                status_text,
                (10, 60),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 255),
                2
            )
        
        # Draw tracking indicator
        if self.tracked_face:
            cv2.putText(
                annotated,
                "🎯 TRACKING",
                (10, 90),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0),
                2
            )
        
        return annotated
    
    def run(self):
        """Main tracking loop"""
        print("\n▶️  Starting face tracking...")
        print("   Press 'q' to quit")
        print("   Press 'r' to reset servos")
        print("   Press 's' to save current frame")
        
        try:
            while True:
                start_time = time.time()
                
                # Capture frame
                ret, frame = read_frame(self.cap)   # flip applied here
                if not ret:
                    print("❌ Failed to capture frame")
                    break
                
                # Detect faces
                face_locations = self.detector.detect_faces(frame)
                
                # Recognize faces (every N frames for performance)
                recognition_results = []
                if self.frame_count % config.PROCESS_EVERY_N_FRAMES == 0:
                    recognition_results = self.recognizer.recognize_faces(frame, face_locations)
                else:
                    # Use previous results or mark as unknown
                    recognition_results = [("Unknown", 0.0) for _ in face_locations]
                
                # Select tracking target
                target_index = self.select_tracking_target(face_locations, recognition_results)
                
                # Update servo tracking
                if target_index is not None:
                    face_location = face_locations[target_index]
                    center_x, center_y = self.calculate_face_center(face_location)
                    
                    # Apply smoothing
                    smooth_x, smooth_y = self.smooth_position(center_x, center_y)
                    
                    # Update servos
                    self.servo.update(smooth_x, smooth_y)
                    
                    # Store tracked face
                    name = recognition_results[target_index][0] if target_index < len(recognition_results) else "Unknown"
                    self.tracked_face = (smooth_x, smooth_y, name)
                else:
                    self.tracked_face = None
                    self.smoothed_position = None
                
                # Calculate FPS
                elapsed = time.time() - start_time
                fps = 1.0 / elapsed if elapsed > 0 else 0
                self.fps_queue.append(fps)
                avg_fps = sum(self.fps_queue) / len(self.fps_queue)
                
                # Draw UI
                display_frame = self.draw_ui(frame, face_locations, recognition_results, avg_fps)
                
                # Display
                cv2.imshow("Face Recognition & Tracking", display_frame)
                
                # Handle keyboard input
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    print("\n⏹️  Stopping...")
                    break
                elif key == ord('r'):
                    print("\n🔄 Resetting servos...")
                    self.servo.reset()
                elif key == ord('s'):
                    filename = f"capture_{int(time.time())}.jpg"
                    cv2.imwrite(filename, display_frame)
                    print(f"\n📸 Saved frame to {filename}")
                
                self.frame_count += 1
                
        except KeyboardInterrupt:
            print("\n⏹️  Interrupted by user")
        
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources"""
        print("\n🧹 Cleaning up...")
        self.servo.reset()
        self.cap.release()
        cv2.destroyAllWindows()
        print("✅ Cleanup complete")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Face Recognition & Tracking System")
    parser.add_argument(
        "--detector",
        choices=["blazeface", "yolo", "hog"],
        default="blazeface",
        help="Face detector to use (default: blazeface)"
    )
    
    args = parser.parse_args()
    
    try:
        # Create and run tracking system
        system = FaceTrackingSystem(detector_type=args.detector)
        system.run()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
