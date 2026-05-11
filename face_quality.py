#!/usr/bin/env python3
"""
Face Quality Metrics
Analyzes face image quality and provides feedback for better recognition.
"""

import cv2
import numpy as np
from typing import Tuple, Dict, Optional


class FaceQualityAnalyzer:
    """Analyze face quality for optimal recognition."""
    
    # Quality thresholds
    BLUR_THRESHOLD_GOOD = 100.0      # Laplacian variance
    BLUR_THRESHOLD_ACCEPTABLE = 50.0
    
    BRIGHTNESS_MIN_GOOD = 80
    BRIGHTNESS_MAX_GOOD = 180
    BRIGHTNESS_MIN_ACCEPTABLE = 40
    BRIGHTNESS_MAX_ACCEPTABLE = 220
    
    FACE_SIZE_MIN_GOOD = 120         # pixels
    FACE_SIZE_MIN_ACCEPTABLE = 80
    
    ANGLE_THRESHOLD_GOOD = 15        # degrees
    ANGLE_THRESHOLD_ACCEPTABLE = 30
    
    def __init__(self):
        self.last_quality = None
    
    def analyze_face(self, frame: np.ndarray, face_box: Tuple[int, int, int, int]) -> Dict:
        """
        Analyze face quality from frame and bounding box.
        
        Args:
            frame: BGR image
            face_box: (top, right, bottom, left) bounding box
            
        Returns:
            Dictionary with quality metrics and suggestions
        """
        top, right, bottom, left = face_box
        
        # Extract face region
        face_img = frame[top:bottom, left:right]
        
        if face_img.size == 0:
            return self._empty_quality()
        
        # Calculate metrics
        blur_score, blur_level = self._check_blur(face_img)
        brightness_score, brightness_level = self._check_brightness(face_img)
        size_score, size_level = self._check_size(face_box)
        angle_score, angle_level = self._estimate_angle(face_img)
        
        # Overall quality score (0-100)
        overall_score = int((blur_score + brightness_score + size_score + angle_score) / 4)
        
        # Determine overall quality level
        if overall_score >= 80:
            overall_level = "Excellent"
            color = (0, 255, 0)  # Green
        elif overall_score >= 60:
            overall_level = "Good"
            color = (0, 255, 0)  # Green
        elif overall_score >= 40:
            overall_level = "Fair"
            color = (0, 255, 255)  # Yellow
        else:
            overall_level = "Poor"
            color = (0, 0, 255)  # Red
        
        # Generate suggestions
        suggestions = self._generate_suggestions(
            blur_level, brightness_level, size_level, angle_level
        )
        
        quality = {
            'overall_score': overall_score,
            'overall_level': overall_level,
            'color': color,
            'blur_score': blur_score,
            'blur_level': blur_level,
            'brightness_score': brightness_score,
            'brightness_level': brightness_level,
            'size_score': size_score,
            'size_level': size_level,
            'angle_score': angle_score,
            'angle_level': angle_level,
            'suggestions': suggestions,
        }
        
        self.last_quality = quality
        return quality
    
    def _check_blur(self, face_img: np.ndarray) -> Tuple[float, str]:
        """Check image sharpness using Laplacian variance."""
        try:
            gray = cv2.cvtColor(face_img, cv2.COLOR_BGR2GRAY)
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            
            if laplacian_var >= self.BLUR_THRESHOLD_GOOD:
                score = 100
                level = "Sharp"
            elif laplacian_var >= self.BLUR_THRESHOLD_ACCEPTABLE:
                score = 50 + (laplacian_var - self.BLUR_THRESHOLD_ACCEPTABLE) / \
                        (self.BLUR_THRESHOLD_GOOD - self.BLUR_THRESHOLD_ACCEPTABLE) * 50
                level = "Acceptable"
            else:
                score = (laplacian_var / self.BLUR_THRESHOLD_ACCEPTABLE) * 50
                level = "Blurry"
            
            return min(100, score), level
        except:
            return 50.0, "Unknown"
    
    def _check_brightness(self, face_img: np.ndarray) -> Tuple[float, str]:
        """Check lighting conditions."""
        try:
            gray = cv2.cvtColor(face_img, cv2.COLOR_BGR2GRAY)
            mean_brightness = np.mean(gray)
            
            if self.BRIGHTNESS_MIN_GOOD <= mean_brightness <= self.BRIGHTNESS_MAX_GOOD:
                score = 100
                level = "Good"
            elif self.BRIGHTNESS_MIN_ACCEPTABLE <= mean_brightness <= self.BRIGHTNESS_MAX_ACCEPTABLE:
                # Calculate score based on distance from ideal range
                if mean_brightness < self.BRIGHTNESS_MIN_GOOD:
                    score = 50 + (mean_brightness - self.BRIGHTNESS_MIN_ACCEPTABLE) / \
                            (self.BRIGHTNESS_MIN_GOOD - self.BRIGHTNESS_MIN_ACCEPTABLE) * 50
                    level = "Dark"
                else:
                    score = 50 + (self.BRIGHTNESS_MAX_ACCEPTABLE - mean_brightness) / \
                            (self.BRIGHTNESS_MAX_ACCEPTABLE - self.BRIGHTNESS_MAX_GOOD) * 50
                    level = "Bright"
            else:
                if mean_brightness < self.BRIGHTNESS_MIN_ACCEPTABLE:
                    score = (mean_brightness / self.BRIGHTNESS_MIN_ACCEPTABLE) * 50
                    level = "Too Dark"
                else:
                    score = (1 - (mean_brightness - self.BRIGHTNESS_MAX_ACCEPTABLE) / \
                            (255 - self.BRIGHTNESS_MAX_ACCEPTABLE)) * 50
                    level = "Too Bright"
            
            return min(100, score), level
        except:
            return 50.0, "Unknown"
    
    def _check_size(self, face_box: Tuple[int, int, int, int]) -> Tuple[float, str]:
        """Check face size in frame."""
        top, right, bottom, left = face_box
        width = right - left
        height = bottom - top
        size = min(width, height)
        
        if size >= self.FACE_SIZE_MIN_GOOD:
            score = 100
            level = "Good Size"
        elif size >= self.FACE_SIZE_MIN_ACCEPTABLE:
            score = 50 + (size - self.FACE_SIZE_MIN_ACCEPTABLE) / \
                    (self.FACE_SIZE_MIN_GOOD - self.FACE_SIZE_MIN_ACCEPTABLE) * 50
            level = "Acceptable"
        else:
            score = (size / self.FACE_SIZE_MIN_ACCEPTABLE) * 50
            level = "Too Small"
        
        return min(100, score), level
    
    def _estimate_angle(self, face_img: np.ndarray) -> Tuple[float, str]:
        """Estimate face angle (simplified - checks symmetry)."""
        try:
            # Simple symmetry check
            h, w = face_img.shape[:2]
            left_half = face_img[:, :w//2]
            right_half = cv2.flip(face_img[:, w//2:], 1)
            
            # Resize to match if needed
            if left_half.shape != right_half.shape:
                min_w = min(left_half.shape[1], right_half.shape[1])
                left_half = left_half[:, :min_w]
                right_half = right_half[:, :min_w]
            
            # Calculate difference
            diff = cv2.absdiff(left_half, right_half)
            symmetry_score = 100 - (np.mean(diff) / 255 * 100)
            
            if symmetry_score >= 70:
                score = 100
                level = "Frontal"
            elif symmetry_score >= 50:
                score = 70
                level = "Slight Angle"
            else:
                score = 40
                level = "Angled"
            
            return score, level
        except:
            return 70.0, "Unknown"
    
    def _generate_suggestions(self, blur: str, brightness: str, size: str, angle: str) -> list:
        """Generate actionable suggestions based on quality issues."""
        suggestions = []
        
        if blur == "Blurry":
            suggestions.append("📷 Hold camera steady")
        
        if brightness == "Too Dark":
            suggestions.append("💡 Add more light")
        elif brightness == "Dark":
            suggestions.append("💡 Improve lighting")
        elif brightness == "Too Bright":
            suggestions.append("☀️ Reduce brightness")
        elif brightness == "Bright":
            suggestions.append("☀️ Adjust lighting")
        
        if size == "Too Small":
            suggestions.append("🔍 Move closer to camera")
        elif size == "Acceptable":
            suggestions.append("🔍 Slightly closer is better")
        
        if angle == "Angled":
            suggestions.append("👤 Face camera directly")
        elif angle == "Slight Angle":
            suggestions.append("👤 Center your face")
        
        if not suggestions:
            suggestions.append("✅ Quality is good!")
        
        return suggestions
    
    def _empty_quality(self) -> Dict:
        """Return empty quality metrics."""
        return {
            'overall_score': 0,
            'overall_level': "No Face",
            'color': (128, 128, 128),
            'blur_score': 0,
            'blur_level': "N/A",
            'brightness_score': 0,
            'brightness_level': "N/A",
            'size_score': 0,
            'size_level': "N/A",
            'angle_score': 0,
            'angle_level': "N/A",
            'suggestions': ["No face detected"],
        }
    
    def get_quality_color(self, score: float) -> Tuple[int, int, int]:
        """Get color based on quality score."""
        if score >= 70:
            return (0, 255, 0)  # Green
        elif score >= 40:
            return (0, 255, 255)  # Yellow
        else:
            return (0, 0, 255)  # Red
