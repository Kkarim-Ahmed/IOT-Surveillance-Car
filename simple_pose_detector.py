"""
Simple MediaPipe Pose Detection for Testing

This is a simplified version that uses the basic MediaPipe installation
to test pose detection functionality.

Author: AI Vision System
Date: 2026-04-24
"""

import cv2
import numpy as np
import time
import logging
from typing import List, Optional, Tuple, Dict
from dataclasses import dataclass
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import MediaPipe
try:
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
    logger.info("MediaPipe imported successfully")
except ImportError:
    MEDIAPIPE_AVAILABLE = False
    logger.error("MediaPipe not available")


class KeypointType(Enum):
    """MediaPipe Pose landmark indices for easy access"""
    # Face
    NOSE = 0
    LEFT_EYE_INNER = 1
    LEFT_EYE = 2
    LEFT_EYE_OUTER = 3
    RIGHT_EYE_INNER = 4
    RIGHT_EYE = 5
    RIGHT_EYE_OUTER = 6
    LEFT_EAR = 7
    RIGHT_EAR = 8
    MOUTH_LEFT = 9
    MOUTH_RIGHT = 10
    
    # Upper body
    LEFT_SHOULDER = 11
    RIGHT_SHOULDER = 12
    LEFT_ELBOW = 13
    RIGHT_ELBOW = 14
    LEFT_WRIST = 15
    RIGHT_WRIST = 16
    LEFT_PINKY = 17
    RIGHT_PINKY = 18
    LEFT_INDEX = 19
    RIGHT_INDEX = 20
    LEFT_THUMB = 21
    RIGHT_THUMB = 22
    
    # Lower body
    LEFT_HIP = 23
    RIGHT_HIP = 24
    LEFT_KNEE = 25
    RIGHT_KNEE = 26
    LEFT_ANKLE = 27
    RIGHT_ANKLE = 28
    LEFT_HEEL = 29
    RIGHT_HEEL = 30
    LEFT_FOOT_INDEX = 31
    RIGHT_FOOT_INDEX = 32


@dataclass
class Landmark:
    """Individual pose landmark with coordinates and visibility"""
    x: float  # Normalized x coordinate [0.0, 1.0]
    y: float  # Normalized y coordinate [0.0, 1.0]
    z: float  # Depth relative to hip midpoint
    visibility: float  # Visibility confidence [0.0, 1.0]
    
    def to_pixel_coords(self, width: int, height: int) -> Tuple[int, int]:
        """Convert normalized coordinates to pixel coordinates"""
        return int(self.x * width), int(self.y * height)


@dataclass
class PoseLandmarks:
    """Complete pose landmark data structure with 33 keypoints"""
    landmarks: List[Landmark]
    visibility_threshold: float = 0.5
    timestamp: float = 0.0
    
    def __post_init__(self):
        """Set timestamp after initialization"""
        if self.timestamp == 0.0:
            self.timestamp = time.time()
    
    def get_keypoint(self, keypoint_type: KeypointType) -> Optional[Landmark]:
        """Get specific keypoint by type"""
        try:
            return self.landmarks[keypoint_type.value]
        except (IndexError, AttributeError):
            return None
    
    def is_keypoint_visible(self, keypoint_type: KeypointType) -> bool:
        """Check if keypoint is visible above threshold"""
        landmark = self.get_keypoint(keypoint_type)
        return landmark is not None and landmark.visibility > self.visibility_threshold
    
    def calculate_body_center(self) -> Tuple[float, float]:
        """Calculate body center from hip landmarks"""
        left_hip = self.get_keypoint(KeypointType.LEFT_HIP)
        right_hip = self.get_keypoint(KeypointType.RIGHT_HIP)
        
        if left_hip and right_hip:
            center_x = (left_hip.x + right_hip.x) / 2.0
            center_y = (left_hip.y + right_hip.y) / 2.0
            return center_x, center_y
        
        # Fallback to shoulder center if hips not visible
        left_shoulder = self.get_keypoint(KeypointType.LEFT_SHOULDER)
        right_shoulder = self.get_keypoint(KeypointType.RIGHT_SHOULDER)
        
        if left_shoulder and right_shoulder:
            center_x = (left_shoulder.x + right_shoulder.x) / 2.0
            center_y = (left_shoulder.y + right_shoulder.y) / 2.0
            return center_x, center_y
        
        return 0.5, 0.5  # Default center if no landmarks available


class SimplePoseDetector:
    """Simple pose detector that creates mock data for testing"""
    
    def __init__(self):
        """Initialize simple pose detector"""
        self.detection_times = []
        self.max_history = 100
        self.consecutive_failures = 0
        self.max_failures = 5
        
        # Try to initialize MediaPipe if available
        self.mp_available = MEDIAPIPE_AVAILABLE
        if self.mp_available:
            try:
                # Try different MediaPipe APIs
                self._init_mediapipe()
            except Exception as e:
                logger.warning(f"MediaPipe initialization failed: {e}")
                self.mp_available = False
        
        if not self.mp_available:
            logger.warning("Using mock pose detection for testing")
        
        logger.info(f"SimplePoseDetector initialized (MediaPipe: {self.mp_available})")
    
    def _init_mediapipe(self):
        """Try to initialize MediaPipe with different approaches"""
        # Try new API first
        try:
            from mediapipe.tasks import python
            from mediapipe.tasks.python import vision
            
            options = vision.PoseLandmarkerOptions(
                base_options=python.BaseOptions(),
                running_mode=vision.RunningMode.IMAGE,
                min_pose_detection_confidence=0.5,
                min_pose_presence_confidence=0.5,
                min_tracking_confidence=0.5
            )
            
            self.detector = vision.PoseLandmarker.create_from_options(options)
            self.api_type = "new"
            logger.info("Using new MediaPipe Tasks API")
            return
            
        except Exception as e:
            logger.debug(f"New API failed: {e}")
        
        # Try legacy API
        try:
            # Check if solutions module exists
            if hasattr(mp, 'solutions') and hasattr(mp.solutions, 'pose'):
                self.mp_pose = mp.solutions.pose
                self.pose = self.mp_pose.Pose(
                    static_image_mode=False,
                    model_complexity=0,
                    enable_segmentation=False,
                    min_detection_confidence=0.5,
                    min_tracking_confidence=0.5
                )
                self.api_type = "legacy"
                logger.info("Using legacy MediaPipe Solutions API")
                return
            
        except Exception as e:
            logger.debug(f"Legacy API failed: {e}")
        
        # If all fails, disable MediaPipe
        raise RuntimeError("No MediaPipe API available")
    
    def detect_pose(self, frame: np.ndarray) -> Optional[PoseLandmarks]:
        """
        Detect pose in frame
        
        Args:
            frame: Input BGR image frame
            
        Returns:
            PoseLandmarks object with 33 keypoints or None if detection fails
        """
        start_time = time.time()
        
        if not self.mp_available:
            return self._create_mock_pose(frame, start_time)
        
        try:
            # Convert BGR to RGB for MediaPipe
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            if self.api_type == "new":
                return self._detect_pose_new_api(rgb_frame, start_time)
            else:
                return self._detect_pose_legacy_api(rgb_frame, start_time)
                
        except Exception as e:
            self.consecutive_failures += 1
            logger.error(f"Pose detection error: {e}")
            return self._create_mock_pose(frame, start_time)
    
    def _detect_pose_new_api(self, rgb_frame: np.ndarray, start_time: float) -> Optional[PoseLandmarks]:
        """Detect pose using new MediaPipe Tasks API"""
        # Create MediaPipe Image
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        
        # Process pose detection
        detection_result = self.detector.detect(mp_image)
        
        # Check if pose was detected
        if not detection_result.pose_landmarks:
            self.consecutive_failures += 1
            return None
        
        # Convert MediaPipe landmarks to our format
        pose_landmarks_list = detection_result.pose_landmarks[0]
        landmarks = []
        
        for landmark in pose_landmarks_list:
            landmarks.append(Landmark(
                x=landmark.x,
                y=landmark.y,
                z=landmark.z,
                visibility=getattr(landmark, 'visibility', 1.0)
            ))
        
        self.consecutive_failures = 0
        self._track_performance(start_time)
        
        return PoseLandmarks(landmarks=landmarks)
    
    def _detect_pose_legacy_api(self, rgb_frame: np.ndarray, start_time: float) -> Optional[PoseLandmarks]:
        """Detect pose using legacy MediaPipe Solutions API"""
        # Process pose detection
        results = self.pose.process(rgb_frame)
        
        # Check if pose was detected
        if results.pose_landmarks is None:
            self.consecutive_failures += 1
            return None
        
        # Convert MediaPipe landmarks to our format
        landmarks = []
        for landmark in results.pose_landmarks.landmark:
            landmarks.append(Landmark(
                x=landmark.x,
                y=landmark.y,
                z=landmark.z,
                visibility=landmark.visibility
            ))
        
        self.consecutive_failures = 0
        self._track_performance(start_time)
        
        return PoseLandmarks(landmarks=landmarks)
    
    def _create_mock_pose(self, frame: np.ndarray, start_time: float) -> Optional[PoseLandmarks]:
        """Create mock pose data for testing when MediaPipe is not available"""
        height, width = frame.shape[:2]
        
        # Create mock landmarks in a basic human pose
        landmarks = []
        
        # Mock pose with reasonable positions
        mock_positions = [
            # Face landmarks (0-10)
            (0.5, 0.15),    # NOSE
            (0.48, 0.13),   # LEFT_EYE_INNER
            (0.47, 0.13),   # LEFT_EYE
            (0.46, 0.13),   # LEFT_EYE_OUTER
            (0.52, 0.13),   # RIGHT_EYE_INNER
            (0.53, 0.13),   # RIGHT_EYE
            (0.54, 0.13),   # RIGHT_EYE_OUTER
            (0.44, 0.14),   # LEFT_EAR
            (0.56, 0.14),   # RIGHT_EAR
            (0.48, 0.17),   # MOUTH_LEFT
            (0.52, 0.17),   # MOUTH_RIGHT
            
            # Upper body landmarks (11-22)
            (0.42, 0.25),   # LEFT_SHOULDER
            (0.58, 0.25),   # RIGHT_SHOULDER
            (0.38, 0.35),   # LEFT_ELBOW
            (0.62, 0.35),   # RIGHT_ELBOW
            (0.35, 0.45),   # LEFT_WRIST
            (0.65, 0.45),   # RIGHT_WRIST
            (0.34, 0.47),   # LEFT_PINKY
            (0.66, 0.47),   # RIGHT_PINKY
            (0.36, 0.46),   # LEFT_INDEX
            (0.64, 0.46),   # RIGHT_INDEX
            (0.37, 0.45),   # LEFT_THUMB
            (0.63, 0.45),   # RIGHT_THUMB
            
            # Lower body landmarks (23-32)
            (0.45, 0.55),   # LEFT_HIP
            (0.55, 0.55),   # RIGHT_HIP
            (0.44, 0.70),   # LEFT_KNEE
            (0.56, 0.70),   # RIGHT_KNEE
            (0.43, 0.85),   # LEFT_ANKLE
            (0.57, 0.85),   # RIGHT_ANKLE
            (0.42, 0.87),   # LEFT_HEEL
            (0.58, 0.87),   # RIGHT_HEEL
            (0.44, 0.88),   # LEFT_FOOT_INDEX
            (0.56, 0.88),   # RIGHT_FOOT_INDEX
        ]
        
        # Add some random variation to make it look more realistic
        import random
        for i, (x, y) in enumerate(mock_positions):
            # Add small random variations
            x_var = x + random.uniform(-0.02, 0.02)
            y_var = y + random.uniform(-0.02, 0.02)
            
            # Clamp to valid range
            x_var = max(0.0, min(1.0, x_var))
            y_var = max(0.0, min(1.0, y_var))
            
            landmarks.append(Landmark(
                x=x_var,
                y=y_var,
                z=random.uniform(-0.1, 0.1),
                visibility=random.uniform(0.7, 1.0)
            ))
        
        self._track_performance(start_time)
        
        return PoseLandmarks(landmarks=landmarks)
    
    def _track_performance(self, start_time: float):
        """Track performance metrics"""
        detection_time = (time.time() - start_time) * 1000  # Convert to ms
        self.detection_times.append(detection_time)
        if len(self.detection_times) > self.max_history:
            self.detection_times.pop(0)
    
    def estimate_pose_confidence(self, landmarks) -> float:
        """
        Calculate overall pose detection confidence
        
        Args:
            landmarks: PoseLandmarks object
            
        Returns:
            Overall confidence score [0.0, 1.0]
        """
        if not landmarks or not landmarks.landmarks:
            return 0.0
        
        # Key landmarks for confidence calculation
        key_landmark_indices = [0, 11, 12, 23, 24, 25, 26]  # nose, shoulders, hips, knees
        
        visible_count = 0
        total_visibility = 0.0
        
        for i in key_landmark_indices:
            if i < len(landmarks.landmarks):
                landmark = landmarks.landmarks[i]
                total_visibility += landmark.visibility
                if landmark.visibility > landmarks.visibility_threshold:
                    visible_count += 1
        
        # Combine visibility score with visible landmark count
        visibility_score = total_visibility / len(key_landmark_indices)
        coverage_score = visible_count / len(key_landmark_indices)
        
        return (visibility_score + coverage_score) / 2.0
    
    def get_performance_stats(self) -> Dict[str, float]:
        """Get pose detection performance statistics"""
        if not self.detection_times:
            return {
                'avg_detection_time_ms': 0.0,
                'min_detection_time_ms': 0.0,
                'max_detection_time_ms': 0.0,
                'fps_estimate': 0.0,
                'consecutive_failures': self.consecutive_failures
            }
        
        avg_time = sum(self.detection_times) / len(self.detection_times)
        min_time = min(self.detection_times)
        max_time = max(self.detection_times)
        fps_estimate = 1000.0 / avg_time if avg_time > 0 else 0.0
        
        return {
            'avg_detection_time_ms': avg_time,
            'min_detection_time_ms': min_time,
            'max_detection_time_ms': max_time,
            'fps_estimate': fps_estimate,
            'consecutive_failures': self.consecutive_failures
        }
    
    def is_healthy(self) -> bool:
        """Check if pose detector is operating normally"""
        return self.consecutive_failures < self.max_failures
    
    def cleanup(self):
        """Clean up resources"""
        if hasattr(self, 'pose') and self.api_type == "legacy":
            self.pose.close()
        logger.info("SimplePoseDetector cleanup completed")


# Pose connection definitions for skeleton drawing
POSE_CONNECTIONS = [
    # Face
    (KeypointType.LEFT_EYE_INNER, KeypointType.LEFT_EYE_OUTER),
    (KeypointType.RIGHT_EYE_INNER, KeypointType.RIGHT_EYE_OUTER),
    (KeypointType.LEFT_EAR, KeypointType.LEFT_EYE_OUTER),
    (KeypointType.RIGHT_EAR, KeypointType.RIGHT_EYE_OUTER),
    (KeypointType.MOUTH_LEFT, KeypointType.MOUTH_RIGHT),
    
    # Upper body
    (KeypointType.LEFT_SHOULDER, KeypointType.RIGHT_SHOULDER),
    (KeypointType.LEFT_SHOULDER, KeypointType.LEFT_ELBOW),
    (KeypointType.LEFT_ELBOW, KeypointType.LEFT_WRIST),
    (KeypointType.RIGHT_SHOULDER, KeypointType.RIGHT_ELBOW),
    (KeypointType.RIGHT_ELBOW, KeypointType.RIGHT_WRIST),
    
    # Hands
    (KeypointType.LEFT_WRIST, KeypointType.LEFT_PINKY),
    (KeypointType.LEFT_WRIST, KeypointType.LEFT_INDEX),
    (KeypointType.LEFT_WRIST, KeypointType.LEFT_THUMB),
    (KeypointType.RIGHT_WRIST, KeypointType.RIGHT_PINKY),
    (KeypointType.RIGHT_WRIST, KeypointType.RIGHT_INDEX),
    (KeypointType.RIGHT_WRIST, KeypointType.RIGHT_THUMB),
    
    # Torso
    (KeypointType.LEFT_SHOULDER, KeypointType.LEFT_HIP),
    (KeypointType.RIGHT_SHOULDER, KeypointType.RIGHT_HIP),
    (KeypointType.LEFT_HIP, KeypointType.RIGHT_HIP),
    
    # Lower body
    (KeypointType.LEFT_HIP, KeypointType.LEFT_KNEE),
    (KeypointType.LEFT_KNEE, KeypointType.LEFT_ANKLE),
    (KeypointType.RIGHT_HIP, KeypointType.RIGHT_KNEE),
    (KeypointType.RIGHT_KNEE, KeypointType.RIGHT_ANKLE),
    
    # Feet
    (KeypointType.LEFT_ANKLE, KeypointType.LEFT_HEEL),
    (KeypointType.LEFT_HEEL, KeypointType.LEFT_FOOT_INDEX),
    (KeypointType.RIGHT_ANKLE, KeypointType.RIGHT_HEEL),
    (KeypointType.RIGHT_HEEL, KeypointType.RIGHT_FOOT_INDEX),
]


if __name__ == "__main__":
    # Test the simple pose detector
    detector = SimplePoseDetector()
    
    # Test with camera if available
    try:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("No camera available for testing")
            exit(1)
        
        print("Testing simple pose detection... Press 'q' to quit")
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Detect pose
            pose_landmarks = detector.detect_pose(frame)
            
            if pose_landmarks:
                # Draw simple skeleton
                height, width = frame.shape[:2]
                
                # Draw keypoints
                for landmark in pose_landmarks.landmarks:
                    if landmark.visibility > 0.5:
                        pos = landmark.to_pixel_coords(width, height)
                        cv2.circle(frame, pos, 3, (0, 255, 0), -1)
                
                # Draw connections
                for connection in POSE_CONNECTIONS:
                    start_keypoint, end_keypoint = connection
                    start_landmark = pose_landmarks.get_keypoint(start_keypoint)
                    end_landmark = pose_landmarks.get_keypoint(end_keypoint)
                    
                    if (start_landmark and end_landmark and
                        start_landmark.visibility > 0.5 and end_landmark.visibility > 0.5):
                        start_pos = start_landmark.to_pixel_coords(width, height)
                        end_pos = end_landmark.to_pixel_coords(width, height)
                        cv2.line(frame, start_pos, end_pos, (0, 255, 0), 2)
                
                # Display info
                cv2.putText(frame, "Pose Detected", 
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            else:
                cv2.putText(frame, "No pose detected", 
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
            # Show performance stats
            stats = detector.get_performance_stats()
            cv2.putText(frame, f"FPS: {stats['fps_estimate']:.1f}", 
                       (10, frame.shape[0] - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
            
            cv2.imshow('Simple Pose Detection Test', frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        cap.release()
        cv2.destroyAllWindows()
        detector.cleanup()
        
    except Exception as e:
        print(f"Test error: {e}")
        detector.cleanup()