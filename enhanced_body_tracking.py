#!/usr/bin/env python3
"""
Enhanced Body Tracking
Better color histogram and texture features for robust tracking.
"""

import cv2
import numpy as np
from typing import Tuple, Dict, Optional


class EnhancedBodyTracker:
    """Enhanced body tracking with better color and texture features."""
    
    def __init__(self):
        # HSV histogram parameters
        self.h_bins = 30  # Hue bins
        self.s_bins = 32  # Saturation bins
        self.hist_range = [0, 180, 0, 256]  # H: 0-180, S: 0-256
    
    def extract_body_signature(self, body_img: np.ndarray) -> Dict:
        """
        Extract comprehensive body signature.
        
        Args:
            body_img: BGR body image
            
        Returns:
            Dictionary with color_hist, texture, proportions
        """
        if body_img is None or body_img.size == 0:
            return None
        
        signature = {
            'color_hist': self._extract_color_histogram(body_img),
            'texture': self._extract_texture_features(body_img),
            'proportions': self._extract_proportions(body_img),
        }
        
        return signature
    
    def _extract_color_histogram(self, body_img: np.ndarray) -> np.ndarray:
        """
        Extract robust color histogram.
        Uses HSV color space and region-based approach.
        """
        try:
            # Convert to HSV (more robust than BGR)
            hsv = cv2.cvtColor(body_img, cv2.COLOR_BGR2HSV)
            
            h, w = body_img.shape[:2]
            
            # Split body into regions
            upper = hsv[0:h//3, :]           # Upper body (shirt/jacket)
            middle = hsv[h//3:2*h//3, :]     # Middle (waist)
            lower = hsv[2*h//3:, :]          # Lower (pants/legs)
            
            # Calculate histograms for each region
            hist_upper = cv2.calcHist([upper], [0, 1], None, 
                                     [self.h_bins, self.s_bins], 
                                     self.hist_range)
            hist_middle = cv2.calcHist([middle], [0, 1], None,
                                      [self.h_bins, self.s_bins],
                                      self.hist_range)
            hist_lower = cv2.calcHist([lower], [0, 1], None,
                                     [self.h_bins, self.s_bins],
                                     self.hist_range)
            
            # Normalize each histogram
            hist_upper = cv2.normalize(hist_upper, hist_upper).flatten()
            hist_middle = cv2.normalize(hist_middle, hist_middle).flatten()
            hist_lower = cv2.normalize(hist_lower, hist_lower).flatten()
            
            # Combine with weights (upper body most important)
            combined_hist = np.concatenate([
                hist_upper * 0.5,    # 50% weight
                hist_middle * 0.3,   # 30% weight
                hist_lower * 0.2     # 20% weight
            ])
            
            return combined_hist
            
        except Exception as e:
            print(f"Color histogram error: {e}")
            return np.zeros(self.h_bins * self.s_bins * 3)
    
    def _extract_texture_features(self, body_img: np.ndarray) -> np.ndarray:
        """
        Extract texture features using edge histogram.
        Simpler than LBP but effective.
        """
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(body_img, cv2.COLOR_BGR2GRAY)
            
            # Calculate edges
            edges = cv2.Canny(gray, 50, 150)
            
            # Edge histogram
            edge_hist, _ = np.histogram(edges.ravel(), bins=16, range=(0, 256))
            edge_hist = edge_hist.astype(float)
            edge_hist /= (edge_hist.sum() + 1e-6)
            
            # Gradient magnitude histogram
            grad_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
            grad_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
            grad_mag = np.sqrt(grad_x**2 + grad_y**2)
            
            grad_hist, _ = np.histogram(grad_mag.ravel(), bins=16, range=(0, 256))
            grad_hist = grad_hist.astype(float)
            grad_hist /= (grad_hist.sum() + 1e-6)
            
            # Combine
            texture_features = np.concatenate([edge_hist, grad_hist])
            
            return texture_features
            
        except Exception as e:
            print(f"Texture extraction error: {e}")
            return np.zeros(32)
    
    def _extract_proportions(self, body_img: np.ndarray) -> Dict:
        """Extract body proportions."""
        h, w = body_img.shape[:2]
        
        proportions = {
            'aspect_ratio': h / (w + 1e-6),
            'width': w,
            'height': h,
            'area': w * h,
        }
        
        return proportions
    
    def compare_signatures(self, sig1: Dict, sig2: Dict) -> float:
        """
        Compare two body signatures.
        
        Returns:
            Similarity score (0-1)
        """
        if sig1 is None or sig2 is None:
            return 0.0
        
        try:
            # Color similarity (correlation)
            color_sim = cv2.compareHist(
                sig1['color_hist'].reshape(-1, 1).astype(np.float32),
                sig2['color_hist'].reshape(-1, 1).astype(np.float32),
                cv2.HISTCMP_CORREL
            )
            color_sim = max(0, color_sim)  # Clamp to 0-1
            
            # Texture similarity (dot product)
            texture_sim = np.dot(sig1['texture'], sig2['texture'])
            texture_sim = max(0, min(1, texture_sim))  # Clamp to 0-1
            
            # Proportion similarity
            prop_sim = self._compare_proportions(sig1['proportions'], sig2['proportions'])
            
            # Weighted combination
            total_sim = (
                0.60 * color_sim +      # 60% color
                0.25 * texture_sim +    # 25% texture
                0.15 * prop_sim         # 15% proportions
            )
            
            return total_sim
            
        except Exception as e:
            print(f"Signature comparison error: {e}")
            return 0.0
    
    def _compare_proportions(self, props1: Dict, props2: Dict, tolerance: float = 0.20) -> float:
        """Compare body proportions."""
        try:
            # Calculate differences
            aspect_diff = abs(props1['aspect_ratio'] - props2['aspect_ratio']) / props1['aspect_ratio']
            width_diff = abs(props1['width'] - props2['width']) / props1['width']
            height_diff = abs(props1['height'] - props2['height']) / props1['height']
            
            # Average difference
            avg_diff = (aspect_diff + width_diff + height_diff) / 3
            
            # Convert to similarity (0-1)
            if avg_diff < tolerance:
                similarity = 1.0 - (avg_diff / tolerance)
            else:
                similarity = 0.0
            
            return similarity
            
        except Exception as e:
            print(f"Proportion comparison error: {e}")
            return 0.0


class MotionPatternTracker:
    """Track motion patterns for better re-identification."""
    
    def __init__(self, history_length: int = 30):
        self.history_length = history_length
        self.position_history = {}  # person_id -> deque of positions
    
    def update_position(self, person_id: int, position: Tuple[int, int]) -> None:
        """Update position for person."""
        from collections import deque
        
        if person_id not in self.position_history:
            self.position_history[person_id] = deque(maxlen=self.history_length)
        
        self.position_history[person_id].append(position)
    
    def get_motion_pattern(self, person_id: int) -> Optional[Dict]:
        """Get motion pattern for person."""
        if person_id not in self.position_history:
            return None
        
        positions = list(self.position_history[person_id])
        
        if len(positions) < 5:
            return None
        
        # Calculate velocities
        velocities = []
        for i in range(1, len(positions)):
            dx = positions[i][0] - positions[i-1][0]
            dy = positions[i][1] - positions[i-1][1]
            velocity = np.sqrt(dx**2 + dy**2)
            velocities.append(velocity)
        
        # Calculate directions
        directions = []
        for i in range(1, len(positions)):
            dx = positions[i][0] - positions[i-1][0]
            dy = positions[i][1] - positions[i-1][1]
            angle = np.arctan2(dy, dx)
            directions.append(angle)
        
        motion_pattern = {
            'avg_speed': np.mean(velocities),
            'speed_variance': np.var(velocities),
            'avg_direction': np.mean(directions),
            'direction_variance': np.var(directions),
        }
        
        return motion_pattern
    
    def compare_motion_patterns(self, pattern1: Dict, pattern2: Dict) -> float:
        """Compare two motion patterns."""
        if pattern1 is None or pattern2 is None:
            return 0.0
        
        try:
            speed_diff = abs(pattern1['avg_speed'] - pattern2['avg_speed'])
            direction_diff = abs(pattern1['avg_direction'] - pattern2['avg_direction'])
            
            # Normalize to 0-1 similarity
            speed_sim = 1.0 / (1.0 + speed_diff / 10)
            direction_sim = 1.0 / (1.0 + direction_diff)
            
            total_sim = (speed_sim + direction_sim) / 2
            
            return total_sim
            
        except Exception as e:
            print(f"Motion pattern comparison error: {e}")
            return 0.0
