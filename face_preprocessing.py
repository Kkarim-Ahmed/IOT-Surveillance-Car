#!/usr/bin/env python3
"""
Face Preprocessing for Better Recognition
Enhances face images before recognition.
"""

import cv2
import numpy as np
from typing import Tuple, Optional


class FacePreprocessor:
    """Preprocess faces for better recognition accuracy."""
    
    def __init__(self, enable_denoising: bool = True, enable_sharpening: bool = True):
        self.enable_denoising = enable_denoising
        self.enable_sharpening = enable_sharpening
        
        # Sharpening kernel
        self.sharpen_kernel = np.array([
            [-1, -1, -1],
            [-1,  9, -1],
            [-1, -1, -1]
        ])
        
        # CLAHE for contrast enhancement
        self.clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    
    def preprocess(self, face_img: np.ndarray) -> np.ndarray:
        """
        Preprocess face image for better recognition.
        
        Args:
            face_img: BGR face image
            
        Returns:
            Preprocessed face image
        """
        if face_img is None or face_img.size == 0:
            return face_img
        
        # 1. Normalize brightness using CLAHE
        face_img = self._normalize_brightness(face_img)
        
        # 2. Denoise (optional)
        if self.enable_denoising:
            face_img = self._denoise(face_img)
        
        # 3. Sharpen (optional)
        if self.enable_sharpening:
            face_img = self._sharpen(face_img)
        
        return face_img
    
    def _normalize_brightness(self, img: np.ndarray) -> np.ndarray:
        """Normalize brightness using CLAHE."""
        try:
            # Convert to LAB color space
            lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            
            # Apply CLAHE to L channel
            l = self.clahe.apply(l)
            
            # Merge and convert back
            lab = cv2.merge([l, a, b])
            img = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
            
            return img
        except:
            return img
    
    def _denoise(self, img: np.ndarray) -> np.ndarray:
        """Remove noise from image."""
        try:
            # Fast denoising
            img = cv2.fastNlMeansDenoisingColored(img, None, 10, 10, 7, 21)
            return img
        except:
            return img
    
    def _sharpen(self, img: np.ndarray) -> np.ndarray:
        """Sharpen image to enhance details."""
        try:
            # Apply sharpening kernel
            img = cv2.filter2D(img, -1, self.sharpen_kernel)
            return img
        except:
            return img
    
    def preprocess_with_histogram_eq(self, face_img: np.ndarray) -> np.ndarray:
        """Alternative: Simple histogram equalization (faster)."""
        try:
            # Convert to YUV
            yuv = cv2.cvtColor(face_img, cv2.COLOR_BGR2YUV)
            
            # Equalize Y channel
            yuv[:, :, 0] = cv2.equalizeHist(yuv[:, :, 0])
            
            # Convert back
            face_img = cv2.cvtColor(yuv, cv2.COLOR_YUV2BGR)
            
            return face_img
        except:
            return face_img


class FaceAligner:
    """Align faces to frontal position."""
    
    def __init__(self):
        pass
    
    def align_face(self, frame: np.ndarray, face_box: Tuple[int, int, int, int],
                   left_eye: Optional[Tuple[int, int]] = None,
                   right_eye: Optional[Tuple[int, int]] = None) -> np.ndarray:
        """
        Align face to frontal position.
        
        Args:
            frame: Full frame
            face_box: (top, right, bottom, left)
            left_eye: (x, y) position of left eye
            right_eye: (x, y) position of right eye
            
        Returns:
            Aligned face image
        """
        top, right, bottom, left = face_box
        
        # If no eye positions, return unaligned face
        if left_eye is None or right_eye is None:
            return frame[top:bottom, left:right]
        
        # Calculate angle between eyes
        dx = right_eye[0] - left_eye[0]
        dy = right_eye[1] - left_eye[1]
        angle = np.degrees(np.arctan2(dy, dx))
        
        # Get face center
        center = ((left + right) // 2, (top + bottom) // 2)
        
        # Rotate image
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        aligned = cv2.warpAffine(frame, M, (frame.shape[1], frame.shape[0]),
                                flags=cv2.INTER_CUBIC)
        
        # Extract aligned face
        aligned_face = aligned[top:bottom, left:right]
        
        return aligned_face
    
    def estimate_eye_positions(self, face_box: Tuple[int, int, int, int]) -> Tuple[Tuple[int, int], Tuple[int, int]]:
        """
        Estimate eye positions from face box (rough approximation).
        
        Args:
            face_box: (top, right, bottom, left)
            
        Returns:
            (left_eye, right_eye) positions
        """
        top, right, bottom, left = face_box
        
        width = right - left
        height = bottom - top
        
        # Eyes are roughly 1/3 down from top, 1/4 and 3/4 across
        eye_y = top + int(height * 0.35)
        left_eye_x = left + int(width * 0.35)
        right_eye_x = left + int(width * 0.65)
        
        left_eye = (left_eye_x, eye_y)
        right_eye = (right_eye_x, eye_y)
        
        return left_eye, right_eye


class MultiCropRecognition:
    """Try multiple crops for better recognition."""
    
    def __init__(self):
        self.crop_configs = [
            {'name': 'original', 'pad_ratio': 0.0},
            {'name': 'padded', 'pad_ratio': 0.1},
            {'name': 'tight', 'pad_ratio': -0.15},
        ]
    
    def get_crops(self, frame: np.ndarray, face_box: Tuple[int, int, int, int]) -> list:
        """
        Get multiple crops of face.
        
        Args:
            frame: Full frame
            face_box: (top, right, bottom, left)
            
        Returns:
            List of (crop_name, crop_image) tuples
        """
        top, right, bottom, left = face_box
        width = right - left
        height = bottom - top
        
        crops = []
        
        for config in self.crop_configs:
            pad_ratio = config['pad_ratio']
            pad_w = int(width * abs(pad_ratio))
            pad_h = int(height * abs(pad_ratio))
            
            if pad_ratio >= 0:
                # Add padding
                crop_top = max(0, top - pad_h)
                crop_bottom = min(frame.shape[0], bottom + pad_h)
                crop_left = max(0, left - pad_w)
                crop_right = min(frame.shape[1], right + pad_w)
            else:
                # Tighter crop
                crop_top = top + pad_h
                crop_bottom = bottom - pad_h
                crop_left = left + pad_w
                crop_right = right - pad_w
            
            # Extract crop
            crop = frame[crop_top:crop_bottom, crop_left:crop_right]
            
            if crop.size > 0:
                crops.append((config['name'], crop))
        
        return crops
