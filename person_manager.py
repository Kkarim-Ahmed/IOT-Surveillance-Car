#!/usr/bin/env python3
"""
Person Manager Module
Manage enrolled people, add images, view profiles.
"""

import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from collections import defaultdict


class PersonProfile:
    """Person profile with statistics."""
    
    def __init__(self, name: str):
        self.name = name
        self.image_count = 0
        self.total_detections = 0
        self.avg_confidence = 0.0
        self.first_seen = datetime.now()
        self.last_seen = datetime.now()
        self.confidence_history = []
        self.detection_times = []
        
    def update_detection(self, confidence: float):
        """Update profile with new detection."""
        self.total_detections += 1
        self.last_seen = datetime.now()
        self.confidence_history.append(confidence)
        self.detection_times.append(time.time())
        
        # Keep only last 100 detections
        if len(self.confidence_history) > 100:
            self.confidence_history.pop(0)
            self.detection_times.pop(0)
        
        # Update average
        self.avg_confidence = sum(self.confidence_history) / len(self.confidence_history)
    
    def get_stats(self) -> Dict:
        """Get profile statistics."""
        return {
            'name': self.name,
            'image_count': self.image_count,
            'total_detections': self.total_detections,
            'avg_confidence': self.avg_confidence,
            'first_seen': self.first_seen,
            'last_seen': self.last_seen,
            'recent_confidence': self.confidence_history[-10:] if self.confidence_history else [],
        }


class PersonManager:
    """Manage enrolled people and their profiles."""
    
    def __init__(self, face_images_dir: str = "known_faces/images"):
        self.face_images_dir = Path(face_images_dir)
        self.profiles = {}  # name -> PersonProfile
        
        # Load existing profiles
        self._load_profiles()
    
    def _load_profiles(self):
        """Load profiles from face images directory."""
        if not self.face_images_dir.exists():
            return
        
        for person_dir in self.face_images_dir.iterdir():
            if person_dir.is_dir():
                name = person_dir.name
                profile = PersonProfile(name)
                
                # Count images
                image_files = list(person_dir.glob("*.jpg")) + list(person_dir.glob("*.png"))
                profile.image_count = len(image_files)
                
                self.profiles[name] = profile
        
        print(f"✅ Loaded {len(self.profiles)} person profile(s)")
    
    def get_profile(self, name: str) -> Optional[PersonProfile]:
        """Get person profile."""
        if name not in self.profiles:
            self.profiles[name] = PersonProfile(name)
        return self.profiles[name]
    
    def update_detection(self, name: str, confidence: float):
        """Update person profile with detection."""
        if name == "Unknown":
            return
        
        profile = self.get_profile(name)
        profile.update_detection(confidence)
    
    def get_all_profiles(self) -> List[PersonProfile]:
        """Get all person profiles."""
        return list(self.profiles.values())
    
    def get_sorted_profiles(self, sort_by: str = "name") -> List[PersonProfile]:
        """
        Get sorted person profiles.
        
        Args:
            sort_by: 'name', 'detections', 'confidence', 'last_seen'
        """
        profiles = self.get_all_profiles()
        
        if sort_by == "name":
            return sorted(profiles, key=lambda p: p.name)
        elif sort_by == "detections":
            return sorted(profiles, key=lambda p: p.total_detections, reverse=True)
        elif sort_by == "confidence":
            return sorted(profiles, key=lambda p: p.avg_confidence, reverse=True)
        elif sort_by == "last_seen":
            return sorted(profiles, key=lambda p: p.last_seen, reverse=True)
        else:
            return profiles
    
    def search_profiles(self, query: str) -> List[PersonProfile]:
        """Search profiles by name."""
        query = query.lower()
        return [p for p in self.profiles.values() if query in p.name.lower()]
    
    def get_person_images(self, name: str) -> List[str]:
        """Get list of image paths for person."""
        person_dir = self.face_images_dir / name
        if not person_dir.exists():
            return []
        
        image_files = []
        for ext in ['*.jpg', '*.jpeg', '*.png']:
            image_files.extend(person_dir.glob(ext))
        
        return [str(f) for f in sorted(image_files)]
    
    def get_image_count(self, name: str) -> int:
        """Get number of images for person."""
        return len(self.get_person_images(name))
    
    def delete_person(self, name: str) -> bool:
        """Delete person profile (does not delete images)."""
        if name in self.profiles:
            del self.profiles[name]
            print(f"🗑️ Deleted profile: {name}")
            return True
        return False
    
    def rename_person(self, old_name: str, new_name: str) -> bool:
        """Rename person."""
        if old_name not in self.profiles:
            return False
        
        if new_name in self.profiles:
            print(f"❌ Person '{new_name}' already exists")
            return False
        
        # Rename profile
        profile = self.profiles[old_name]
        profile.name = new_name
        self.profiles[new_name] = profile
        del self.profiles[old_name]
        
        # Rename directory
        old_dir = self.face_images_dir / old_name
        new_dir = self.face_images_dir / new_name
        
        if old_dir.exists():
            old_dir.rename(new_dir)
        
        print(f"✏️ Renamed: {old_name} → {new_name}")
        return True
    
    def get_statistics(self) -> Dict:
        """Get overall statistics."""
        total_people = len(self.profiles)
        total_images = sum(p.image_count for p in self.profiles.values())
        total_detections = sum(p.total_detections for p in self.profiles.values())
        
        if self.profiles:
            avg_confidence = sum(p.avg_confidence for p in self.profiles.values()) / total_people
        else:
            avg_confidence = 0.0
        
        return {
            'total_people': total_people,
            'total_images': total_images,
            'total_detections': total_detections,
            'avg_confidence': avg_confidence,
        }
    
    def get_detection_history(self, hours: int = 24) -> Dict[str, int]:
        """Get detection counts for last N hours."""
        cutoff_time = time.time() - (hours * 3600)
        history = defaultdict(int)
        
        for profile in self.profiles.values():
            count = sum(1 for t in profile.detection_times if t >= cutoff_time)
            if count > 0:
                history[profile.name] = count
        
        return dict(history)
