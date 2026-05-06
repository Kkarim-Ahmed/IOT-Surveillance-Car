"""
MediaPipe Pose Detection Module for AI Vision System

This module provides real-time human pose estimation using MediaPipe Pose,
optimized for Raspberry Pi 4 performance. It extracts 33 body keypoints
for comprehensive skeleton tracking and body analysis.

Author: AI Vision System
Date: 2026-04-24
"""

import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from typing import List, Optional, Tuple, Dict, Any
from dataclasses import dataclass
from enum import Enum
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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


@dataclass
class BodyMetrics:
    """Body measurement and proportion data"""
    height_estimate: float = 0.0      # Estimated height in pixels
    shoulder_width: float = 0.0       # Shoulder span in pixels
    torso_length: float = 0.0         # Shoulder to hip distance in pixels
    arm_span: float = 0.0             # Full arm span in pixels
    leg_length: float = 0.0           # Hip to ankle distance in pixels
    aspect_ratio: float = 0.0         # Height to width ratio
    confidence: float = 0.0           # Overall measurement confidence
    
    def normalize_measurements(self, reference_height: float):
        """Normalize measurements to reference scale"""
        if reference_height > 0:
            scale_factor = reference_height / max(self.height_estimate, 1.0)
            self.height_estimate *= scale_factor
            self.shoulder_width *= scale_factor
            self.torso_length *= scale_factor
            self.arm_span *= scale_factor
            self.leg_length *= scale_factor


class PoseDetector:
    """Real-time human pose estimation using MediaPipe Pose"""
    
    def __init__(self, 
                 model_asset_path: Optional[str] = None,
                 min_pose_detection_confidence: float = 0.5,
                 min_pose_presence_confidence: float = 0.5,
                 min_tracking_confidence: float = 0.5,
                 output_segmentation_masks: bool = False):
        """
        Initialize MediaPipe Pose with optimized settings for Raspberry Pi
        
        Args:
            model_asset_path: Path to pose landmarker model (None for default)
            min_pose_detection_confidence: Minimum confidence for pose detection
            min_pose_presence_confidence: Minimum confidence for pose presence
            min_tracking_confidence: Minimum confidence for pose tracking
            output_segmentation_masks: Enable pose segmentation (heavier processing)
        """
        self.min_pose_detection_confidence = min_pose_detection_confidence
        self.min_pose_presence_confidence = min_pose_presence_confidence
        self.min_tracking_confidence = min_tracking_confidence
        self.output_segmentation_masks = output_segmentation_masks
        
        try:
            # Create pose landmarker options
            base_options = python.BaseOptions(model_asset_path=model_asset_path)
            options = vision.PoseLandmarkerOptions(
                base_options=base_options,
                running_mode=vision.RunningMode.IMAGE,
                min_pose_detection_confidence=min_pose_detection_confidence,
                min_pose_presence_confidence=min_pose_presence_confidence,
                min_tracking_confidence=min_tracking_confidence,
                output_segmentation_masks=output_segmentation_masks
            )
            
            # Initialize MediaPipe Pose Landmarker
            self.detector = vision.PoseLandmarker.create_from_options(options)
            self.use_new_api = True
            
        except Exception as e:
            logger.warning(f"Failed to initialize new MediaPipe API: {e}")
            logger.info("Falling back to legacy MediaPipe API")
            
            # Try legacy API as fallback
            try:
                import mediapipe.python.solutions.pose as mp_pose
                self.mp_pose = mp_pose
                self.pose = self.mp_pose.Pose(
                    static_image_mode=False,
                    model_complexity=0,  # Fastest for Pi
                    enable_segmentation=output_segmentation_masks,
                    min_detection_confidence=min_pose_detection_confidence,
                    min_tracking_confidence=min_tracking_confidence
                )
                self.use_new_api = False
                
            except Exception as e2:
                logger.error(f"Failed to initialize legacy MediaPipe API: {e2}")
                raise RuntimeError("Could not initialize MediaPipe Pose with either new or legacy API")
        
        # Performance tracking
        self.detection_times = []
        self.max_history = 100
        self.consecutive_failures = 0
        self.max_failures = 5
        
        api_type = "new" if self.use_new_api else "legacy"
        logger.info(f"PoseDetector initialized with {api_type} API - "
                   f"detection_conf={min_pose_detection_confidence}, "
                   f"presence_conf={min_pose_presence_confidence}, "
                   f"tracking_conf={min_tracking_confidence}")
    
    def detect_pose(self, frame: np.ndarray) -> Optional[PoseLandmarks]:
        """
        Extract 33 body keypoints from frame
        
        Args:
            frame: Input BGR image frame
            
        Returns:
            PoseLandmarks object with 33 keypoints or None if detection fails
        """
        start_time = time.time()
        
        try:
            # Convert BGR to RGB for MediaPipe
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            if self.use_new_api:
                return self._detect_pose_new_api(rgb_frame, start_time)
            else:
                return self._detect_pose_legacy_api(rgb_frame, start_time)
                
        except Exception as e:
            self.consecutive_failures += 1
            logger.error(f"Pose detection error: {e}")
            return None
    
    def _detect_pose_new_api(self, rgb_frame: np.ndarray, start_time: float) -> Optional[PoseLandmarks]:
        """Detect pose using new MediaPipe Tasks API"""
        # Create MediaPipe Image
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        
        # Process pose detection
        detection_result = self.detector.detect(mp_image)
        
        # Check if pose was detected
        if not detection_result.pose_landmarks:
            self.consecutive_failures += 1
            logger.debug("No pose detected in frame")
            return None
        
        # Convert MediaPipe landmarks to our format (use first detected pose)
        pose_landmarks_list = detection_result.pose_landmarks[0]
        landmarks = []
        
        for landmark in pose_landmarks_list:
            landmarks.append(Landmark(
                x=landmark.x,
                y=landmark.y,
                z=landmark.z,
                visibility=landmark.visibility if hasattr(landmark, 'visibility') else 1.0
            ))
        
        # Reset failure counter on successful detection
        self.consecutive_failures = 0
        
        # Track performance
        detection_time = (time.time() - start_time) * 1000  # Convert to ms
        self.detection_times.append(detection_time)
        if len(self.detection_times) > self.max_history:
            self.detection_times.pop(0)
        
        return PoseLandmarks(landmarks=landmarks)
    
    def _detect_pose_legacy_api(self, rgb_frame: np.ndarray, start_time: float) -> Optional[PoseLandmarks]:
        """Detect pose using legacy MediaPipe Solutions API"""
        # Process pose detection
        results = self.pose.process(rgb_frame)
        
        # Check if pose was detected
        if results.pose_landmarks is None:
            self.consecutive_failures += 1
            logger.debug("No pose detected in frame")
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
        
        # Reset failure counter on successful detection
        self.consecutive_failures = 0
        
        # Track performance
        detection_time = (time.time() - start_time) * 1000  # Convert to ms
        self.detection_times.append(detection_time)
        if len(self.detection_times) > self.max_history:
            self.detection_times.pop(0)
        
        return PoseLandmarks(landmarks=landmarks)
    
    def get_body_measurements(self, landmarks: PoseLandmarks, 
                            frame_width: int, frame_height: int) -> BodyMetrics:
        """
        Calculate body proportions and measurements from pose landmarks
        
        Args:
            landmarks: Pose landmarks data
            frame_width: Frame width in pixels
            frame_height: Frame height in pixels
            
        Returns:
            BodyMetrics with calculated measurements
        """
        metrics = BodyMetrics()
        
        try:
            # Get key landmarks
            left_shoulder = landmarks.get_keypoint(KeypointType.LEFT_SHOULDER)
            right_shoulder = landmarks.get_keypoint(KeypointType.RIGHT_SHOULDER)
            left_hip = landmarks.get_keypoint(KeypointType.LEFT_HIP)
            right_hip = landmarks.get_keypoint(KeypointType.RIGHT_HIP)
            left_ankle = landmarks.get_keypoint(KeypointType.LEFT_ANKLE)
            right_ankle = landmarks.get_keypoint(KeypointType.RIGHT_ANKLE)
            left_wrist = landmarks.get_keypoint(KeypointType.LEFT_WRIST)
            right_wrist = landmarks.get_keypoint(KeypointType.RIGHT_WRIST)
            nose = landmarks.get_keypoint(KeypointType.NOSE)
            
            visible_count = 0
            
            # Calculate shoulder width
            if left_shoulder and right_shoulder:
                shoulder_dx = abs(left_shoulder.x - right_shoulder.x) * frame_width
                metrics.shoulder_width = shoulder_dx
                visible_count += 1
            
            # Calculate torso length (shoulder to hip)
            if left_shoulder and right_shoulder and left_hip and right_hip:
                shoulder_center_y = (left_shoulder.y + right_shoulder.y) / 2.0
                hip_center_y = (left_hip.y + right_hip.y) / 2.0
                torso_dy = abs(shoulder_center_y - hip_center_y) * frame_height
                metrics.torso_length = torso_dy
                visible_count += 1
            
            # Calculate leg length (hip to ankle)
            if left_hip and left_ankle:
                leg_dy = abs(left_hip.y - left_ankle.y) * frame_height
                metrics.leg_length = max(metrics.leg_length, leg_dy)
                visible_count += 1
            if right_hip and right_ankle:
                leg_dy = abs(right_hip.y - right_ankle.y) * frame_height
                metrics.leg_length = max(metrics.leg_length, leg_dy)
                visible_count += 1
            
            # Calculate arm span
            if left_wrist and right_wrist:
                arm_dx = abs(left_wrist.x - right_wrist.x) * frame_width
                metrics.arm_span = arm_dx
                visible_count += 1
            
            # Estimate total height
            if nose and left_ankle and right_ankle:
                ankle_y = min(left_ankle.y, right_ankle.y)
                height_dy = abs(nose.y - ankle_y) * frame_height
                metrics.height_estimate = height_dy
                visible_count += 1
            
            # Calculate aspect ratio
            if metrics.height_estimate > 0 and metrics.shoulder_width > 0:
                metrics.aspect_ratio = metrics.height_estimate / metrics.shoulder_width
            
            # Calculate confidence based on visible landmarks
            metrics.confidence = min(visible_count / 6.0, 1.0)  # Max 6 measurements
            
        except Exception as e:
            logger.error(f"Body measurement calculation error: {e}")
            metrics.confidence = 0.0
        
        return metrics
    
    def estimate_pose_confidence(self, landmarks: PoseLandmarks) -> float:
        """
        Calculate overall pose detection confidence
        
        Args:
            landmarks: Pose landmarks data
            
        Returns:
            Overall confidence score [0.0, 1.0]
        """
        if not landmarks or not landmarks.landmarks:
            return 0.0
        
        # Key landmarks for confidence calculation
        key_landmarks = [
            KeypointType.NOSE,
            KeypointType.LEFT_SHOULDER,
            KeypointType.RIGHT_SHOULDER,
            KeypointType.LEFT_HIP,
            KeypointType.RIGHT_HIP,
            KeypointType.LEFT_KNEE,
            KeypointType.RIGHT_KNEE
        ]
        
        visible_count = 0
        total_visibility = 0.0
        
        for keypoint_type in key_landmarks:
            landmark = landmarks.get_keypoint(keypoint_type)
            if landmark:
                total_visibility += landmark.visibility
                if landmark.visibility > landmarks.visibility_threshold:
                    visible_count += 1
        
        # Combine visibility score with visible landmark count
        visibility_score = total_visibility / len(key_landmarks)
        coverage_score = visible_count / len(key_landmarks)
        
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
    
    def reset_failure_count(self):
        """Reset consecutive failure counter"""
        self.consecutive_failures = 0
    
    def cleanup(self):
        """Clean up MediaPipe resources"""
        if hasattr(self, 'detector') and self.use_new_api:
            # MediaPipe tasks don't require explicit cleanup
            pass
        elif hasattr(self, 'pose') and not self.use_new_api:
            self.pose.close()
        logger.info("PoseDetector cleanup completed")


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
    # Test the pose detector
    import sys
    
    # Initialize pose detector
    detector = PoseDetector(model_complexity=0, min_detection_confidence=0.5)
    
    # Test with camera if available
    try:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("No camera available for testing")
            sys.exit(1)
        
        print("Testing pose detection... Press 'q' to quit")
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Detect pose
            pose_landmarks = detector.detect_pose(frame)
            
            if pose_landmarks:
                # Calculate body metrics
                metrics = detector.get_body_measurements(
                    pose_landmarks, frame.shape[1], frame.shape[0]
                )
                
                # Get confidence
                confidence = detector.estimate_pose_confidence(pose_landmarks)
                
                # Display info
                cv2.putText(frame, f"Pose Confidence: {confidence:.2f}", 
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.putText(frame, f"Height: {metrics.height_estimate:.0f}px", 
                           (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.putText(frame, f"Shoulder Width: {metrics.shoulder_width:.0f}px", 
                           (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            else:
                cv2.putText(frame, "No pose detected", 
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
            # Show performance stats
            stats = detector.get_performance_stats()
            cv2.putText(frame, f"FPS: {stats['fps_estimate']:.1f}", 
                       (10, frame.shape[0] - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
            
            cv2.imshow('Pose Detection Test', frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        cap.release()
        cv2.destroyAllWindows()
        detector.cleanup()
        
    except Exception as e:
        print(f"Test error: {e}")
        detector.cleanup()