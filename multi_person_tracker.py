#!/usr/bin/env python3
"""
Multi-Person Tracking Module
Tracks multiple people simultaneously with priority-based selection.

Features:
- Track up to 5 people simultaneously
- Priority system: VIPs > Known > Unknown
- Smooth target switching
- Individual tracking history per person
- Threat assessment integration ready
"""

import cv2
import numpy as np
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional
import config


@dataclass
class TrackedPerson:
    """Data structure for a tracked person."""
    person_id: int
    name: str
    confidence: float
    position: Tuple[int, int]  # (x, y) center
    bbox: Tuple[int, int, int, int]  # (top, right, bottom, left)
    last_seen: float
    tracking_history: deque
    priority: int  # 0=Unknown, 1=Known, 2=VIP
    threat_level: int  # 0=Low, 1=Medium, 2=High, 3=Critical
    is_active: bool


class MultiPersonTracker:
    """
    Advanced multi-person tracking system with priority-based selection.
    """
    
    def __init__(self, max_persons=5, history_length=30):
        self.max_persons = max_persons
        self.history_length = history_length
        
        # Tracking state
        self.tracked_persons: Dict[int, TrackedPerson] = {}
        self.next_person_id = 1
        self.current_target_id: Optional[int] = None
        
        # Priority lists
        self.vip_names = set()  # VIP persons (highest priority)
        self.known_names = set()  # Known persons (medium priority)
        
        # Tracking parameters
        self.max_distance_threshold = 100  # pixels
        self.lost_person_timeout = 3.0  # seconds
        self.target_switch_cooldown = 2.0  # seconds
        self.last_target_switch = 0
        
        # Statistics
        self.total_persons_seen = 0
        self.tracking_stats = {
            'frames_processed': 0,
            'persons_tracked': 0,
            'target_switches': 0
        }
    
    def add_vip(self, name: str):
        """Add a person to VIP list (highest priority)."""
        self.vip_names.add(name)
        if name in self.known_names:
            self.known_names.remove(name)
    
    def add_known_person(self, name: str):
        """Add a person to known list (medium priority)."""
        if name not in self.vip_names:
            self.known_names.add(name)
    
    def remove_person(self, name: str):
        """Remove person from all priority lists."""
        self.vip_names.discard(name)
        self.known_names.discard(name)
    
    def get_priority(self, name: str) -> int:
        """Get priority level for a person."""
        if name in self.vip_names:
            return 2  # VIP
        elif name in self.known_names:
            return 1  # Known
        else:
            return 0  # Unknown
    
    def calculate_distance(self, pos1: Tuple[int, int], pos2: Tuple[int, int]) -> float:
        """Calculate Euclidean distance between two positions."""
        return np.sqrt((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)
    
    def match_detections_to_tracks(self, face_locations: List, recognition_results: List) -> Dict:
        """
        Match new detections to existing tracks using position and identity.
        
        Returns:
            Dict mapping detection_index -> person_id (or None for new persons)
        """
        current_time = time.time()
        matches = {}
        
        # Calculate centers for all detections
        detection_centers = []
        for top, right, bottom, left in face_locations:
            center_x = (left + right) // 2
            center_y = (top + bottom) // 2
            detection_centers.append((center_x, center_y))
        
        # Try to match each detection to existing tracks
        for det_idx, (center, (name, confidence)) in enumerate(zip(detection_centers, recognition_results)):
            best_match_id = None
            best_distance = float('inf')
            
            # Check against all active tracks
            for person_id, person in self.tracked_persons.items():
                if not person.is_active:
                    continue
                
                # Calculate position distance
                pos_distance = self.calculate_distance(center, person.position)
                
                # Identity bonus (reduce effective distance for same person)
                identity_bonus = 0
                if name != "Unknown" and name == person.name:
                    identity_bonus = 50  # Prefer same identity
                
                effective_distance = pos_distance - identity_bonus
                
                # Check if this is the best match so far
                if (effective_distance < self.max_distance_threshold and 
                    effective_distance < best_distance):
                    best_distance = effective_distance
                    best_match_id = person_id
            
            matches[det_idx] = best_match_id
        
        return matches
    
    def update_tracks(self, face_locations: List, recognition_results: List):
        """
        Update tracking with new detections.
        
        Args:
            face_locations: List of (top, right, bottom, left) bounding boxes
            recognition_results: List of (name, confidence) tuples
        """
        current_time = time.time()
        self.tracking_stats['frames_processed'] += 1
        
        # Match detections to existing tracks
        matches = self.match_detections_to_tracks(face_locations, recognition_results)
        
        # Update matched tracks
        updated_person_ids = set()
        
        for det_idx, person_id in matches.items():
            top, right, bottom, left = face_locations[det_idx]
            name, confidence = recognition_results[det_idx]
            center_x = (left + right) // 2
            center_y = (top + bottom) // 2
            
            if person_id is not None:
                # Update existing track
                person = self.tracked_persons[person_id]
                person.position = (center_x, center_y)
                person.bbox = (top, right, bottom, left)
                person.last_seen = current_time
                person.is_active = True
                
                # Update identity if recognition improved
                if name != "Unknown" and confidence > person.confidence:
                    person.name = name
                    person.confidence = confidence
                    person.priority = self.get_priority(name)
                
                # Add to tracking history
                person.tracking_history.append({
                    'timestamp': current_time,
                    'position': (center_x, center_y),
                    'bbox': (top, right, bottom, left),
                    'confidence': confidence
                })
                
                updated_person_ids.add(person_id)
            
            else:
                # Create new track
                if len(self.tracked_persons) < self.max_persons:
                    new_person = TrackedPerson(
                        person_id=self.next_person_id,
                        name=name,
                        confidence=confidence,
                        position=(center_x, center_y),
                        bbox=(top, right, bottom, left),
                        last_seen=current_time,
                        tracking_history=deque(maxlen=self.history_length),
                        priority=self.get_priority(name),
                        threat_level=0,  # Default to low threat
                        is_active=True
                    )
                    
                    # Add initial history entry
                    new_person.tracking_history.append({
                        'timestamp': current_time,
                        'position': (center_x, center_y),
                        'bbox': (top, right, bottom, left),
                        'confidence': confidence
                    })
                    
                    self.tracked_persons[self.next_person_id] = new_person
                    updated_person_ids.add(self.next_person_id)
                    self.next_person_id += 1
                    self.total_persons_seen += 1
        
        # Mark non-updated tracks as potentially lost
        for person_id, person in self.tracked_persons.items():
            if person_id not in updated_person_ids:
                if current_time - person.last_seen > self.lost_person_timeout:
                    person.is_active = False
        
        # Clean up old inactive tracks
        self.cleanup_inactive_tracks()
        
        # Update statistics
        self.tracking_stats['persons_tracked'] = len([p for p in self.tracked_persons.values() if p.is_active])
    
    def cleanup_inactive_tracks(self):
        """Remove old inactive tracks to free up space."""
        current_time = time.time()
        to_remove = []
        
        for person_id, person in self.tracked_persons.items():
            if (not person.is_active and 
                current_time - person.last_seen > self.lost_person_timeout * 2):
                to_remove.append(person_id)
        
        for person_id in to_remove:
            if person_id == self.current_target_id:
                self.current_target_id = None
            del self.tracked_persons[person_id]
    
    def select_target(self) -> Optional[int]:
        """
        Select the best target to track based on priority and other factors.
        
        Returns:
            person_id of selected target, or None if no suitable target
        """
        current_time = time.time()
        
        # Don't switch targets too frequently
        if (self.current_target_id is not None and 
            current_time - self.last_target_switch < self.target_switch_cooldown):
            # Check if current target is still active
            if (self.current_target_id in self.tracked_persons and 
                self.tracked_persons[self.current_target_id].is_active):
                return self.current_target_id
        
        # Find best target based on priority and other factors
        active_persons = [p for p in self.tracked_persons.values() if p.is_active]
        
        if not active_persons:
            self.current_target_id = None
            return None
        
        # Sort by priority (VIP > Known > Unknown), then by threat level, then by confidence
        def target_score(person):
            return (
                person.priority * 1000 +      # Priority is most important
                person.threat_level * 100 +   # Then threat level
                person.confidence * 10        # Then recognition confidence
            )
        
        best_person = max(active_persons, key=target_score)
        
        # Switch target if needed
        if self.current_target_id != best_person.person_id:
            self.current_target_id = best_person.person_id
            self.last_target_switch = current_time
            self.tracking_stats['target_switches'] += 1
        
        return self.current_target_id
    
    def get_target_position(self) -> Optional[Tuple[int, int]]:
        """Get position of current target."""
        if (self.current_target_id is not None and 
            self.current_target_id in self.tracked_persons):
            return self.tracked_persons[self.current_target_id].position
        return None
    
    def get_target_info(self) -> Optional[TrackedPerson]:
        """Get full info of current target."""
        if (self.current_target_id is not None and 
            self.current_target_id in self.tracked_persons):
            return self.tracked_persons[self.current_target_id]
        return None
    
    def get_all_active_persons(self) -> List[TrackedPerson]:
        """Get list of all active tracked persons."""
        return [p for p in self.tracked_persons.values() if p.is_active]
    
    def draw_tracking_info(self, frame: np.ndarray) -> np.ndarray:
        """
        Draw tracking information on frame.
        
        Args:
            frame: Input frame
            
        Returns:
            Annotated frame
        """
        annotated = frame.copy()
        h, w = frame.shape[:2]
        
        # Draw all tracked persons
        for person in self.tracked_persons.values():
            if not person.is_active:
                continue
            
            top, right, bottom, left = person.bbox
            
            # Choose color based on priority and target status
            if person.person_id == self.current_target_id:
                color = (0, 255, 0)  # Green for current target
                thickness = 3
            elif person.priority == 2:  # VIP
                color = (255, 0, 255)  # Magenta for VIP
                thickness = 2
            elif person.priority == 1:  # Known
                color = (0, 255, 255)  # Yellow for known
                thickness = 2
            else:  # Unknown
                color = (0, 165, 255)  # Orange for unknown
                thickness = 2
            
            # Draw bounding box
            cv2.rectangle(annotated, (left, top), (right, bottom), color, thickness)
            
            # Prepare label
            label_parts = []
            if person.person_id == self.current_target_id:
                label_parts.append("🎯")
            
            if person.priority == 2:
                label_parts.append("VIP")
            
            label_parts.append(f"ID:{person.person_id}")
            label_parts.append(person.name)
            
            if person.confidence > 0:
                label_parts.append(f"{person.confidence:.2f}")
            
            label = " ".join(label_parts)
            
            # Draw label background
            label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            cv2.rectangle(
                annotated,
                (left, top - label_size[1] - 10),
                (left + label_size[0] + 4, top),
                color,
                -1
            )
            
            # Draw label text
            cv2.putText(
                annotated,
                label,
                (left + 2, top - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                2
            )
            
            # Draw person center
            center_x, center_y = person.position
            cv2.circle(annotated, (center_x, center_y), 5, color, -1)
            
            # Draw tracking history (trail)
            if len(person.tracking_history) > 1:
                points = [entry['position'] for entry in person.tracking_history]
                for i in range(1, len(points)):
                    alpha = i / len(points)  # Fade older points
                    trail_color = tuple(int(c * alpha) for c in color)
                    cv2.line(annotated, points[i-1], points[i], trail_color, 1)
        
        # Draw frame center crosshair
        center_x, center_y = w // 2, h // 2
        cv2.line(annotated, (center_x - 20, center_y), (center_x + 20, center_y), (255, 0, 0), 2)
        cv2.line(annotated, (center_x, center_y - 20), (center_x, center_y + 20), (255, 0, 0), 2)
        
        # Draw target line (if target exists)
        target_pos = self.get_target_position()
        if target_pos:
            cv2.line(annotated, target_pos, (center_x, center_y), (0, 255, 0), 2)
        
        # Draw statistics
        stats_y = 30
        stats = [
            f"Active: {self.tracking_stats['persons_tracked']}",
            f"Total Seen: {self.total_persons_seen}",
            f"Target: {self.current_target_id or 'None'}",
            f"Switches: {self.tracking_stats['target_switches']}"
        ]
        
        for i, stat in enumerate(stats):
            cv2.putText(
                annotated,
                stat,
                (10, stats_y + i * 25),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                2
            )
        
        return annotated
    
    def get_statistics(self) -> Dict:
        """Get tracking statistics."""
        return {
            **self.tracking_stats,
            'total_persons_seen': self.total_persons_seen,
            'current_target_id': self.current_target_id,
            'active_persons': len([p for p in self.tracked_persons.values() if p.is_active]),
            'vip_count': len(self.vip_names),
            'known_count': len(self.known_names)
        }


# Example usage and test function
def test_multi_person_tracker():
    """Test the multi-person tracker with live camera."""
    
    print("🎯 Multi-Person Tracker Test")
    print("=" * 40)
    
    # Import required modules
    from camera_utils import open_camera, read_frame
    from blazeface_detector import BlazeFaceDetector
    from face_recognition_module import FaceRecognitionSystem
    
    # Initialize components
    cap = open_camera()
    detector = BlazeFaceDetector()
    recognizer = FaceRecognitionSystem()
    tracker = MultiPersonTracker(max_persons=5)
    
    # Add some example VIPs and known persons
    tracker.add_vip("Mezo")  # Add your name as VIP
    tracker.add_known_person("Example_Person")
    
    print("📷 Camera initialized")
    print("🎯 Tracker initialized")
    print("👥 VIPs: Mezo")
    print("👤 Known: Example_Person")
    print("\nInstructions:")
    print("  - Move around to test tracking")
    print("  - Multiple people will be tracked simultaneously")
    print("  - VIPs get highest priority (magenta box)")
    print("  - Known persons get medium priority (yellow box)")
    print("  - Unknown persons get low priority (orange box)")
    print("  - Current target has green box with 🎯")
    print("  - Press 'q' to quit")
    print("\n▶️  Starting test...")
    
    frame_count = 0
    
    try:
        while True:
            ret, frame = read_frame(cap)
            if not ret:
                break
            
            # Detect faces
            face_locations = detector.detect_faces(frame)
            
            # Recognize faces (every few frames for performance)
            if frame_count % config.PROCESS_EVERY_N_FRAMES == 0:
                recognition_results = recognizer.recognize_faces(frame, face_locations)
            else:
                recognition_results = [("Unknown", 0.0) for _ in face_locations]
            
            # Update tracking
            tracker.update_tracks(face_locations, recognition_results)
            
            # Select target
            target_id = tracker.select_target()
            
            # Draw tracking info
            display = tracker.draw_tracking_info(frame)
            
            # Show display
            cv2.imshow("Multi-Person Tracker Test", display)
            
            # Handle input
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            
            frame_count += 1
    
    except KeyboardInterrupt:
        pass
    
    finally:
        cap.release()
        cv2.destroyAllWindows()
        
        # Print final statistics
        stats = tracker.get_statistics()
        print("\n📊 Final Statistics:")
        for key, value in stats.items():
            print(f"  {key}: {value}")


if __name__ == "__main__":
    test_multi_person_tracker()