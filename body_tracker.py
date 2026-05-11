#!/usr/bin/env python3
"""
Body Tracking Module
Tracks people by their body/silhouette when face is not visible.

Features:
- Person detection using YOLO (detects full body)
- Body pose estimation for unique identification
- Color histogram matching for person re-identification
- Seamless transition between face and body tracking
- Maintains tracking when person turns around
"""

import cv2
import numpy as np
import time
from collections import deque, defaultdict
from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional, Union
import config


@dataclass
class BodyTrack:
    """Data structure for body tracking."""
    track_id: int
    person_name: str  # From face recognition
    confidence: float
    bbox: Tuple[int, int, int, int]  # (x, y, w, h)
    center: Tuple[int, int]
    last_seen: float
    
    # Body characteristics for re-identification
    color_histogram: np.ndarray
    body_size: Tuple[int, int]  # (width, height)
    aspect_ratio: float
    
    # Tracking history
    position_history: deque
    velocity: Tuple[float, float]  # (vx, vy)
    
    # State
    has_face: bool  # Currently has visible face
    tracking_mode: str  # "face", "body", "lost"
    lost_face_time: float  # When face was last seen


class PersonBodyTracker:
    """
    Advanced person tracker that maintains tracking when face is not visible.
    
    Uses multiple methods:
    1. Face detection + recognition (primary)
    2. Body detection (YOLO person class)
    3. Color histogram matching
    4. Motion prediction
    5. Body pose estimation (optional)
    """
    
    def __init__(self, max_tracks=5, history_length=30):
        self.max_tracks = max_tracks
        self.history_length = history_length
        
        # Tracking state
        self.body_tracks: Dict[int, BodyTrack] = {}
        self.next_track_id = 1
        self.current_target_id: Optional[int] = None
        
        # Detection models
        self.yolo_model = None
        self.pose_model = None
        self._init_models()
        
        # Tracking parameters
        self.max_distance_threshold = 150  # pixels
        self.face_lost_timeout = 5.0  # seconds before switching to body tracking
        self.body_lost_timeout = 10.0  # seconds before removing track
        self.color_match_threshold = 0.7  # histogram correlation threshold
        
        # Statistics
        self.stats = {
            'face_tracks': 0,
            'body_tracks': 0,
            'transitions': 0,
            'reidentifications': 0
        }
    
    def _init_models(self):
        """Initialize YOLO and pose estimation models."""
        try:
            # Try to load YOLOv8 for person detection
            from ultralytics import YOLO
            self.yolo_model = YOLO('yolov8n.pt')  # Nano version for speed
            print("✅ YOLO person detection loaded")
        except Exception as e:
            print(f"⚠️  YOLO not available: {e}")
            print("   Will use OpenCV HOG person detector as fallback")
            self.yolo_model = None
        
        try:
            # Try to load MediaPipe Pose for body keypoints
            import mediapipe as mp
            self.mp_pose = mp.solutions.pose
            self.pose_model = self.mp_pose.Pose(
                static_image_mode=False,
                model_complexity=0,  # Fastest model
                enable_segmentation=False,
                min_detection_confidence=0.5
            )
            print("✅ MediaPipe Pose loaded")
        except Exception as e:
            print(f"⚠️  MediaPipe Pose not available: {e}")
            self.pose_model = None
    
    def detect_persons(self, frame: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """
        Detect person bounding boxes in frame.
        
        Returns:
            List of (x, y, w, h) bounding boxes
        """
        persons = []
        
        if self.yolo_model is not None:
            # Use YOLO for person detection
            try:
                results = self.yolo_model(frame, verbose=False)
                for result in results:
                    boxes = result.boxes
                    if boxes is not None:
                        for box in boxes:
                            # Class 0 is 'person' in COCO dataset
                            if int(box.cls) == 0 and float(box.conf) > 0.5:
                                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                                x, y, w, h = int(x1), int(y1), int(x2-x1), int(y2-y1)
                                persons.append((x, y, w, h))
            except Exception as e:
                print(f"YOLO detection error: {e}")
        
        else:
            # Fallback to HOG person detector
            hog = cv2.HOGDescriptor()
            hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
            
            # Detect people
            boxes, weights = hog.detectMultiScale(
                frame, 
                winStride=(8, 8),
                padding=(32, 32),
                scale=1.05,
                hitThreshold=0.5
            )
            
            for (x, y, w, h) in boxes:
                persons.append((x, y, w, h))
        
        return persons
    
    def extract_color_histogram(self, frame: np.ndarray, bbox: Tuple[int, int, int, int]) -> np.ndarray:
        """
        Extract color histogram from person bounding box.
        
        Args:
            frame: Input frame
            bbox: (x, y, w, h) bounding box
            
        Returns:
            Normalized color histogram
        """
        x, y, w, h = bbox
        
        # Crop person region
        person_crop = frame[y:y+h, x:x+w]
        
        if person_crop.size == 0:
            return np.zeros(256)
        
        # Convert to HSV for better color representation
        hsv = cv2.cvtColor(person_crop, cv2.COLOR_BGR2HSV)
        
        # Calculate histogram for Hue and Saturation channels
        hist_h = cv2.calcHist([hsv], [0], None, [50], [0, 180])
        hist_s = cv2.calcHist([hsv], [1], None, [60], [0, 256])
        
        # Combine histograms
        hist = np.concatenate([hist_h.flatten(), hist_s.flatten()])
        
        # Normalize
        hist = hist / (np.sum(hist) + 1e-10)
        
        return hist
    
    def calculate_histogram_similarity(self, hist1: np.ndarray, hist2: np.ndarray) -> float:
        """Calculate similarity between two histograms."""
        return cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)
    
    def get_body_pose_features(self, frame: np.ndarray, bbox: Tuple[int, int, int, int]) -> Optional[np.ndarray]:
        """
        Extract body pose features for person identification.
        
        Returns:
            Pose feature vector or None if pose detection fails
        """
        if self.pose_model is None:
            return None
        
        x, y, w, h = bbox
        person_crop = frame[y:y+h, x:x+w]
        
        if person_crop.size == 0:
            return None
        
        try:
            # Convert to RGB for MediaPipe
            rgb_crop = cv2.cvtColor(person_crop, cv2.COLOR_BGR2RGB)
            results = self.pose_model.process(rgb_crop)
            
            if results.pose_landmarks:
                # Extract key body ratios and angles
                landmarks = results.pose_landmarks.landmark
                
                # Calculate body proportions
                features = []
                
                # Shoulder width to height ratio
                left_shoulder = landmarks[11]
                right_shoulder = landmarks[12]
                shoulder_width = abs(left_shoulder.x - right_shoulder.x)
                
                # Hip width
                left_hip = landmarks[23]
                right_hip = landmarks[24]
                hip_width = abs(left_hip.x - right_hip.x)
                
                # Torso length
                shoulder_y = (left_shoulder.y + right_shoulder.y) / 2
                hip_y = (left_hip.y + right_hip.y) / 2
                torso_length = abs(shoulder_y - hip_y)
                
                features.extend([shoulder_width, hip_width, torso_length])
                
                # Add more features as needed
                return np.array(features)
            
        except Exception as e:
            print(f"Pose estimation error: {e}")
        
        return None
    
    def match_body_to_face_tracks(self, 
                                  body_detections: List[Tuple[int, int, int, int]], 
                                  face_locations: List[Tuple[int, int, int, int]], 
                                  recognition_results: List[Tuple[str, float]],
                                  frame: np.ndarray) -> Dict:
        """
        Match body detections to existing face tracks and create new tracks.
        
        Returns:
            Dictionary mapping body_detection_index -> track_id
        """
        current_time = time.time()
        matches = {}
        
        # Convert face locations to (x, y, w, h) format
        face_boxes = []
        for (top, right, bottom, left) in face_locations:
            x, y, w, h = left, top, right - left, bottom - top
            face_boxes.append((x, y, w, h))
        
        # First, try to match body detections with faces in the same frame
        for body_idx, body_bbox in enumerate(body_detections):
            bx, by, bw, bh = body_bbox
            body_center = (bx + bw // 2, by + bh // 2)
            
            best_face_match = None
            best_distance = float('inf')
            
            # Check if any face is inside this body detection
            for face_idx, face_bbox in enumerate(face_boxes):
                fx, fy, fw, fh = face_bbox
                face_center = (fx + fw // 2, fy + fh // 2)
                
                # Check if face is roughly in the upper part of body
                if (bx <= face_center[0] <= bx + bw and 
                    by <= face_center[1] <= by + bh // 2):  # Face should be in upper half
                    
                    distance = np.sqrt((body_center[0] - face_center[0])**2 + 
                                     (body_center[1] - face_center[1])**2)
                    
                    if distance < best_distance:
                        best_distance = distance
                        best_face_match = face_idx
            
            # If we found a matching face, create or update track
            if best_face_match is not None:
                name, confidence = recognition_results[best_face_match]
                
                # Extract body features
                color_hist = self.extract_color_histogram(frame, body_bbox)
                pose_features = self.get_body_pose_features(frame, body_bbox)
                
                # Create new track or update existing
                track_id = self._create_or_update_track(
                    body_bbox, name, confidence, color_hist, 
                    pose_features, current_time, has_face=True
                )
                matches[body_idx] = track_id
            
            else:
                # No face match - try to match with existing body tracks
                track_id = self._match_to_existing_body_track(body_bbox, frame, current_time)
                if track_id is not None:
                    matches[body_idx] = track_id
        
        return matches
    
    def _create_or_update_track(self, 
                               body_bbox: Tuple[int, int, int, int],
                               name: str, 
                               confidence: float,
                               color_hist: np.ndarray,
                               pose_features: Optional[np.ndarray],
                               current_time: float,
                               has_face: bool) -> int:
        """Create new track or update existing one."""
        
        x, y, w, h = body_bbox
        center = (x + w // 2, y + h // 2)
        
        # Try to find existing track for this person
        existing_track_id = None
        if name != "Unknown":
            for track_id, track in self.body_tracks.items():
                if track.person_name == name and track.tracking_mode != "lost":
                    # Calculate distance to see if it's the same person
                    distance = np.sqrt((center[0] - track.center[0])**2 + 
                                     (center[1] - track.center[1])**2)
                    if distance < self.max_distance_threshold:
                        existing_track_id = track_id
                        break
        
        if existing_track_id is not None:
            # Update existing track
            track = self.body_tracks[existing_track_id]
            
            # Calculate velocity
            dt = current_time - track.last_seen
            if dt > 0:
                vx = (center[0] - track.center[0]) / dt
                vy = (center[1] - track.center[1]) / dt
                track.velocity = (vx, vy)
            
            # Update track data
            track.bbox = body_bbox
            track.center = center
            track.last_seen = current_time
            track.has_face = has_face
            track.tracking_mode = "face" if has_face else "body"
            
            if has_face:
                track.confidence = confidence
                track.lost_face_time = current_time
            
            # Update color histogram (weighted average)
            alpha = 0.3  # Learning rate
            track.color_histogram = (alpha * color_hist + 
                                   (1 - alpha) * track.color_histogram)
            
            # Add to position history
            track.position_history.append({
                'time': current_time,
                'center': center,
                'bbox': body_bbox,
                'has_face': has_face
            })
            
            return existing_track_id
        
        else:
            # Create new track
            new_track = BodyTrack(
                track_id=self.next_track_id,
                person_name=name,
                confidence=confidence,
                bbox=body_bbox,
                center=center,
                last_seen=current_time,
                color_histogram=color_hist,
                body_size=(w, h),
                aspect_ratio=h / w if w > 0 else 1.0,
                position_history=deque(maxlen=self.history_length),
                velocity=(0.0, 0.0),
                has_face=has_face,
                tracking_mode="face" if has_face else "body",
                lost_face_time=current_time if has_face else 0
            )
            
            # Add initial position
            new_track.position_history.append({
                'time': current_time,
                'center': center,
                'bbox': body_bbox,
                'has_face': has_face
            })
            
            self.body_tracks[self.next_track_id] = new_track
            track_id = self.next_track_id
            self.next_track_id += 1
            
            return track_id
    
    def _match_to_existing_body_track(self, 
                                     body_bbox: Tuple[int, int, int, int], 
                                     frame: np.ndarray, 
                                     current_time: float) -> Optional[int]:
        """Try to match body detection to existing track without face."""
        
        x, y, w, h = body_bbox
        center = (x + w // 2, y + h // 2)
        color_hist = self.extract_color_histogram(frame, body_bbox)
        
        best_match_id = None
        best_score = 0
        
        for track_id, track in self.body_tracks.items():
            if track.tracking_mode == "lost":
                continue
            
            # Calculate position distance
            distance = np.sqrt((center[0] - track.center[0])**2 + 
                             (center[1] - track.center[1])**2)
            
            # Predict position based on velocity
            dt = current_time - track.last_seen
            predicted_x = track.center[0] + track.velocity[0] * dt
            predicted_y = track.center[1] + track.velocity[1] * dt
            predicted_distance = np.sqrt((center[0] - predicted_x)**2 + 
                                       (center[1] - predicted_y)**2)
            
            # Use predicted distance if it's better
            final_distance = min(distance, predicted_distance)
            
            # Calculate color similarity
            color_similarity = self.calculate_histogram_similarity(color_hist, track.color_histogram)
            
            # Calculate size similarity
            size_similarity = 1.0 - abs(track.aspect_ratio - (h / w if w > 0 else 1.0)) / 2.0
            size_similarity = max(0, size_similarity)
            
            # Combined score
            if final_distance < self.max_distance_threshold:
                distance_score = 1.0 - (final_distance / self.max_distance_threshold)
                combined_score = (0.4 * distance_score + 
                                0.4 * color_similarity + 
                                0.2 * size_similarity)
                
                if combined_score > best_score and combined_score > 0.5:
                    best_score = combined_score
                    best_match_id = track_id
        
        if best_match_id is not None:
            # Update the matched track
            track = self.body_tracks[best_match_id]
            
            # Calculate velocity
            dt = current_time - track.last_seen
            if dt > 0:
                vx = (center[0] - track.center[0]) / dt
                vy = (center[1] - track.center[1]) / dt
                track.velocity = (vx, vy)
            
            # Update track
            track.bbox = body_bbox
            track.center = center
            track.last_seen = current_time
            track.has_face = False
            track.tracking_mode = "body"
            
            # Update color histogram
            alpha = 0.2  # Slower learning for body-only tracking
            track.color_histogram = (alpha * color_hist + 
                                   (1 - alpha) * track.color_histogram)
            
            # Add to history
            track.position_history.append({
                'time': current_time,
                'center': center,
                'bbox': body_bbox,
                'has_face': False
            })
            
            # Check if we should mark as re-identification
            if (track.tracking_mode == "face" and 
                current_time - track.lost_face_time > self.face_lost_timeout):
                self.stats['reidentifications'] += 1
        
        return best_match_id
    
    def update_tracks(self, 
                     face_locations: List[Tuple[int, int, int, int]], 
                     recognition_results: List[Tuple[str, float]], 
                     frame: np.ndarray):
        """
        Main update function - combines face and body tracking.
        
        Args:
            face_locations: List of (top, right, bottom, left) face boxes
            recognition_results: List of (name, confidence) tuples
            frame: Current frame
        """
        current_time = time.time()
        
        # Detect person bodies
        body_detections = self.detect_persons(frame)
        
        # Match bodies to faces and existing tracks
        matches = self.match_body_to_face_tracks(
            body_detections, face_locations, recognition_results, frame
        )
        
        # Update tracking modes and cleanup
        self._update_tracking_modes(current_time)
        self._cleanup_lost_tracks(current_time)
        
        # Update statistics
        self.stats['face_tracks'] = len([t for t in self.body_tracks.values() 
                                        if t.tracking_mode == "face"])
        self.stats['body_tracks'] = len([t for t in self.body_tracks.values() 
                                        if t.tracking_mode == "body"])
    
    def _update_tracking_modes(self, current_time: float):
        """Update tracking modes based on face visibility."""
        for track in self.body_tracks.values():
            if track.tracking_mode == "lost":
                continue
            
            # Check if face has been lost for too long
            if (track.has_face and 
                current_time - track.lost_face_time > self.face_lost_timeout):
                if track.tracking_mode == "face":
                    track.tracking_mode = "body"
                    self.stats['transitions'] += 1
            
            # Check if body tracking has been lost
            if current_time - track.last_seen > self.body_lost_timeout:
                track.tracking_mode = "lost"
    
    def _cleanup_lost_tracks(self, current_time: float):
        """Remove old lost tracks."""
        to_remove = []
        for track_id, track in self.body_tracks.items():
            if (track.tracking_mode == "lost" and 
                current_time - track.last_seen > self.body_lost_timeout * 2):
                to_remove.append(track_id)
        
        for track_id in to_remove:
            if track_id == self.current_target_id:
                self.current_target_id = None
            del self.body_tracks[track_id]
    
    def select_target(self) -> Optional[int]:
        """Select best target for tracking."""
        active_tracks = [t for t in self.body_tracks.values() 
                        if t.tracking_mode in ["face", "body"]]
        
        if not active_tracks:
            self.current_target_id = None
            return None
        
        # Prioritize known faces, then body tracks
        def track_priority(track):
            priority_score = 0
            
            # Known person bonus
            if track.person_name != "Unknown":
                priority_score += 1000
            
            # Face visibility bonus
            if track.tracking_mode == "face":
                priority_score += 500
            
            # Confidence bonus
            priority_score += track.confidence * 100
            
            # Recency bonus
            time_bonus = max(0, 10 - (time.time() - track.last_seen))
            priority_score += time_bonus * 10
            
            return priority_score
        
        best_track = max(active_tracks, key=track_priority)
        self.current_target_id = best_track.track_id
        
        return self.current_target_id
    
    def get_target_position(self) -> Optional[Tuple[int, int]]:
        """Get position of current target."""
        if (self.current_target_id is not None and 
            self.current_target_id in self.body_tracks):
            return self.body_tracks[self.current_target_id].center
        return None
    
    def draw_tracking_info(self, frame: np.ndarray) -> np.ndarray:
        """Draw tracking visualization on frame."""
        annotated = frame.copy()
        h, w = frame.shape[:2]
        
        # Draw all active tracks
        for track in self.body_tracks.values():
            if track.tracking_mode == "lost":
                continue
            
            x, y, bw, bh = track.bbox
            
            # Choose color based on tracking mode and target status
            if track.track_id == self.current_target_id:
                color = (0, 255, 0)  # Green for current target
                thickness = 3
            elif track.tracking_mode == "face":
                color = (255, 0, 255)  # Magenta for face tracking
                thickness = 2
            elif track.tracking_mode == "body":
                color = (0, 255, 255)  # Yellow for body tracking
                thickness = 2
            else:
                color = (128, 128, 128)  # Gray for uncertain
                thickness = 1
            
            # Draw bounding box
            cv2.rectangle(annotated, (x, y), (x + bw, y + bh), color, thickness)
            
            # Prepare label
            label_parts = []
            if track.track_id == self.current_target_id:
                label_parts.append("🎯")
            
            label_parts.append(f"ID:{track.track_id}")
            label_parts.append(track.person_name)
            label_parts.append(f"[{track.tracking_mode.upper()}]")
            
            if track.confidence > 0:
                label_parts.append(f"{track.confidence:.2f}")
            
            label = " ".join(label_parts)
            
            # Draw label
            label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            cv2.rectangle(annotated, (x, y - label_size[1] - 10), 
                         (x + label_size[0] + 4, y), color, -1)
            cv2.putText(annotated, label, (x + 2, y - 5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
            # Draw center point
            cv2.circle(annotated, track.center, 5, color, -1)
            
            # Draw tracking trail
            if len(track.position_history) > 1:
                points = [entry['center'] for entry in track.position_history]
                for i in range(1, len(points)):
                    alpha = i / len(points)
                    trail_color = tuple(int(c * alpha) for c in color)
                    cv2.line(annotated, points[i-1], points[i], trail_color, 2)
        
        # Draw frame center and target line
        center_x, center_y = w // 2, h // 2
        cv2.line(annotated, (center_x - 20, center_y), (center_x + 20, center_y), (255, 0, 0), 2)
        cv2.line(annotated, (center_x, center_y - 20), (center_x, center_y + 20), (255, 0, 0), 2)
        
        target_pos = self.get_target_position()
        if target_pos:
            cv2.line(annotated, target_pos, (center_x, center_y), (0, 255, 0), 2)
        
        # Draw statistics
        stats_y = 30
        stats_text = [
            f"Face Tracks: {self.stats['face_tracks']}",
            f"Body Tracks: {self.stats['body_tracks']}",
            f"Transitions: {self.stats['transitions']}",
            f"Re-IDs: {self.stats['reidentifications']}",
            f"Target: {self.current_target_id or 'None'}"
        ]
        
        for i, text in enumerate(stats_text):
            cv2.putText(annotated, text, (10, stats_y + i * 25), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        return annotated


# Test function
def test_body_tracker():
    """Test the body tracker with live camera."""
    
    print("🚶 Body Tracker Test")
    print("=" * 40)
    
    from camera_utils import open_camera, read_frame
    from blazeface_detector import BlazeFaceDetector
    from face_recognition_module import FaceRecognitionSystem
    
    # Initialize components
    cap = open_camera()
    face_detector = BlazeFaceDetector()
    recognizer = FaceRecognitionSystem()
    body_tracker = PersonBodyTracker(max_tracks=3)
    
    print("📷 Camera initialized")
    print("🎯 Body tracker initialized")
    print("\nInstructions:")
    print("  - Walk around and turn your back to camera")
    print("  - System should maintain tracking via body detection")
    print("  - Face tracking (MAGENTA) -> Body tracking (YELLOW)")
    print("  - Current target has GREEN box with 🎯")
    print("  - Press 'q' to quit")
    print("\n▶️  Starting test...")
    
    frame_count = 0
    
    try:
        while True:
            ret, frame = read_frame(cap)
            if not ret:
                break
            
            # Face detection and recognition
            face_locations = face_detector.detect_faces(frame)
            
            if frame_count % config.PROCESS_EVERY_N_FRAMES == 0:
                recognition_results = recognizer.recognize_faces(frame, face_locations)
            else:
                recognition_results = [("Unknown", 0.0) for _ in face_locations]
            
            # Update body tracking
            body_tracker.update_tracks(face_locations, recognition_results, frame)
            
            # Select target
            target_id = body_tracker.select_target()
            
            # Draw tracking info
            display = body_tracker.draw_tracking_info(frame)
            
            # Show display
            cv2.imshow("Body Tracker Test", display)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            
            frame_count += 1
    
    except KeyboardInterrupt:
        pass
    
    finally:
        cap.release()
        cv2.destroyAllWindows()
        
        print("\n📊 Final Statistics:")
        stats = body_tracker.stats
        for key, value in stats.items():
            print(f"  {key}: {value}")


if __name__ == "__main__":
    test_body_tracker()