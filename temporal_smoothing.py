#!/usr/bin/env python3
"""
Temporal Smoothing for Recognition
Reduces flickering by voting across multiple frames.
Fast identity-change detection flushes stale votes immediately.
"""

import numpy as np
from collections import deque, Counter
from typing import Tuple, Optional


class TemporalRecognitionSmoothing:
    """Smooth recognition results over time to reduce flickering.
    
    Includes fast identity-switch detection: if the raw recognizer
    returns a *different* identity for SWITCH_THRESHOLD consecutive
    frames, the history is flushed and restarted with the new identity.
    This eliminates the 2-3 second lag when switching faces.
    """
    
    # Number of consecutive "different identity" frames needed to flush history
    SWITCH_THRESHOLD = 2

    def __init__(self, window_size: int = 5, min_agreement: float = 0.5):
        """
        Args:
            window_size: Number of frames to consider (reduced for faster switching)
            min_agreement: Minimum vote ratio to accept result (0.5 = 50%)
        """
        self.window_size = window_size
        self.min_agreement = min_agreement
        self.recognition_history = deque(maxlen=window_size)
        self.confidence_history = deque(maxlen=window_size)
        
        # Fast identity-switch detection state
        self._last_committed_name: Optional[str] = None
        self._switch_candidate: Optional[str] = None
        self._switch_streak: int = 0
    
    def add_recognition(self, name: str, confidence: float) -> None:
        """Add recognition result to history with identity-change detection."""
        
        # ── Fast identity-switch detection ────────────────────────────────
        if self._last_committed_name is not None and name != self._last_committed_name:
            # A different identity appeared
            if name == self._switch_candidate:
                self._switch_streak += 1
            else:
                # New candidate — start counting
                self._switch_candidate = name
                self._switch_streak = 1
            
            # Enough consecutive different-identity frames → flush history
            if self._switch_streak >= self.SWITCH_THRESHOLD:
                self.recognition_history.clear()
                self.confidence_history.clear()
                self._last_committed_name = name
                self._switch_candidate = None
                self._switch_streak = 0
        elif name == self._last_committed_name:
            # Same identity as committed — reset switch detection
            self._switch_candidate = None
            self._switch_streak = 0
        
        # If this is the very first recognition, commit it immediately
        if self._last_committed_name is None:
            self._last_committed_name = name
        
        # ── Normal vote accumulation ──────────────────────────────────────
        self.recognition_history.append(name)
        self.confidence_history.append(confidence)
    
    def get_smoothed_result(self) -> Tuple[str, float]:
        """
        Get most consistent result over time.
        
        Returns:
            (name, confidence) - Smoothed recognition result
        """
        if not self.recognition_history:
            return "Unknown", 0.0
        
        # Count votes for each name
        name_counts = Counter(self.recognition_history)
        
        # Get name with most votes
        best_name, vote_count = name_counts.most_common(1)[0]
        
        # Calculate vote ratio
        vote_ratio = vote_count / len(self.recognition_history)
        
        # Require minimum agreement
        if vote_ratio < self.min_agreement:
            return "Unknown", 0.0
        
        # Calculate average confidence for best name
        confidences = [
            conf for name, conf in zip(self.recognition_history, self.confidence_history)
            if name == best_name
        ]
        avg_confidence = np.mean(confidences) if confidences else 0.0
        
        # Boost confidence based on agreement
        boosted_confidence = avg_confidence * (0.5 + 0.5 * vote_ratio)
        
        # Update committed name
        self._last_committed_name = best_name
        
        return best_name, boosted_confidence
    
    def get_vote_distribution(self) -> dict:
        """Get vote distribution for debugging."""
        if not self.recognition_history:
            return {}
        
        name_counts = Counter(self.recognition_history)
        total = len(self.recognition_history)
        
        return {
            name: count / total
            for name, count in name_counts.items()
        }
    
    def reset(self) -> None:
        """Reset history."""
        self.recognition_history.clear()
        self.confidence_history.clear()
        self._last_committed_name = None
        self._switch_candidate = None
        self._switch_streak = 0
    
    def is_stable(self) -> bool:
        """Check if recognition is stable (high agreement)."""
        if len(self.recognition_history) < self.window_size:
            return False
        
        name_counts = Counter(self.recognition_history)
        if not name_counts:
            return False
        
        most_common_count = name_counts.most_common(1)[0][1]
        vote_ratio = most_common_count / len(self.recognition_history)
        
        return vote_ratio >= 0.8  # 80% agreement = stable


class MultiPersonTemporalSmoothing:
    """Temporal smoothing for multiple people."""
    
    def __init__(self, window_size: int = 5, min_agreement: float = 0.5):
        self.window_size = window_size
        self.min_agreement = min_agreement
        self.person_smoothers = {}  # person_id -> TemporalRecognitionSmoothing
    
    def add_recognition(self, person_id: int, name: str, confidence: float) -> None:
        """Add recognition for specific person."""
        if person_id not in self.person_smoothers:
            self.person_smoothers[person_id] = TemporalRecognitionSmoothing(
                self.window_size, self.min_agreement
            )
        
        self.person_smoothers[person_id].add_recognition(name, confidence)
    
    def get_smoothed_result(self, person_id: int) -> Tuple[str, float]:
        """Get smoothed result for specific person."""
        if person_id not in self.person_smoothers:
            return "Unknown", 0.0
        
        return self.person_smoothers[person_id].get_smoothed_result()
    
    def cleanup_old_people(self, active_person_ids: set, max_age: float = 5.0) -> None:
        """Remove smoothers for people no longer tracked."""
        # Remove person IDs not in active set
        inactive_ids = set(self.person_smoothers.keys()) - active_person_ids
        for person_id in inactive_ids:
            del self.person_smoothers[person_id]
