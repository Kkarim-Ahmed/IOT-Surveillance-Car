#!/usr/bin/env python3
"""
Smart Alert System
Configurable alerts for various events.
"""

import time
from datetime import datetime
from typing import Dict, List, Callable
from collections import deque
import winsound  # For Windows sound alerts


class AlertType:
    """Alert type constants."""
    UNKNOWN_PERSON = "unknown_person"
    VIP_DETECTED = "vip_detected"
    WATCHLIST_DETECTED = "watchlist_detected"
    LOITERING = "loitering"
    LOW_CONFIDENCE = "low_confidence"
    PERSON_REAPPEARED = "person_reappeared"


class Alert:
    """Alert data structure."""
    
    def __init__(self, alert_type: str, message: str, person_name: str = None,
                 confidence: float = None, timestamp: datetime = None):
        self.alert_type = alert_type
        self.message = message
        self.person_name = person_name
        self.confidence = confidence
        self.timestamp = timestamp or datetime.now()
    
    def __str__(self):
        time_str = self.timestamp.strftime("%H:%M:%S")
        return f"[{time_str}] {self.message}"


class AlertSystem:
    """Smart alert system with configurable rules."""
    
    def __init__(self):
        # Alert configuration
        self.enabled_alerts = {
            AlertType.UNKNOWN_PERSON: True,
            AlertType.VIP_DETECTED: True,
            AlertType.WATCHLIST_DETECTED: True,
            AlertType.LOITERING: True,
            AlertType.LOW_CONFIDENCE: False,
            AlertType.PERSON_REAPPEARED: False,
        }
        
        # Alert thresholds
        self.loitering_threshold = 30.0  # seconds
        self.low_confidence_threshold = 0.50  # 50%
        
        # Alert methods
        self.sound_enabled = True
        self.log_enabled = True
        
        # Alert history
        self.alert_history = deque(maxlen=100)
        
        # Tracking data
        self.person_first_seen = {}  # person_id -> timestamp
        self.person_last_alerted = {}  # person_id -> timestamp
        self.alert_cooldown = 10.0  # seconds between same alerts
        
        # VIP and watchlist
        self.vip_list = set()
        self.watchlist = set()
        
        # Alert callbacks
        self.alert_callbacks = []
    
    def add_callback(self, callback: Callable):
        """Add callback function to be called on alert."""
        self.alert_callbacks.append(callback)
    
    def add_to_vip(self, person_name: str):
        """Add person to VIP list."""
        self.vip_list.add(person_name)
        print(f"⭐ Added {person_name} to VIP list")
    
    def remove_from_vip(self, person_name: str):
        """Remove person from VIP list."""
        self.vip_list.discard(person_name)
        print(f"Removed {person_name} from VIP list")
    
    def add_to_watchlist(self, person_name: str):
        """Add person to watchlist."""
        self.watchlist.add(person_name)
        print(f"🚫 Added {person_name} to watchlist")
    
    def remove_from_watchlist(self, person_name: str):
        """Remove person from watchlist."""
        self.watchlist.discard(person_name)
        print(f"Removed {person_name} from watchlist")
    
    def check_detection(self, person_name: str, confidence: float, person_id: int = None):
        """Check detection and trigger alerts if needed."""
        current_time = time.time()
        
        # Check cooldown
        if person_id and person_id in self.person_last_alerted:
            if current_time - self.person_last_alerted[person_id] < self.alert_cooldown:
                return  # Still in cooldown
        
        # Unknown person alert
        if person_name == "Unknown" and self.enabled_alerts[AlertType.UNKNOWN_PERSON]:
            self._trigger_alert(
                AlertType.UNKNOWN_PERSON,
                "⚠️ Unknown person detected",
                person_name,
                confidence
            )
            if person_id:
                self.person_last_alerted[person_id] = current_time
        
        # VIP alert
        elif person_name in self.vip_list and self.enabled_alerts[AlertType.VIP_DETECTED]:
            self._trigger_alert(
                AlertType.VIP_DETECTED,
                f"⭐ VIP detected: {person_name}",
                person_name,
                confidence
            )
            if person_id:
                self.person_last_alerted[person_id] = current_time
        
        # Watchlist alert
        elif person_name in self.watchlist and self.enabled_alerts[AlertType.WATCHLIST_DETECTED]:
            self._trigger_alert(
                AlertType.WATCHLIST_DETECTED,
                f"🚨 WATCHLIST: {person_name} detected!",
                person_name,
                confidence
            )
            if person_id:
                self.person_last_alerted[person_id] = current_time
        
        # Low confidence alert
        elif confidence < self.low_confidence_threshold and self.enabled_alerts[AlertType.LOW_CONFIDENCE]:
            self._trigger_alert(
                AlertType.LOW_CONFIDENCE,
                f"📉 Low confidence: {person_name} ({confidence:.0%})",
                person_name,
                confidence
            )
    
    def check_loitering(self, person_id: int, person_name: str, duration: float):
        """Check if person is loitering."""
        if not self.enabled_alerts[AlertType.LOITERING]:
            return
        
        if duration >= self.loitering_threshold:
            # Check cooldown
            current_time = time.time()
            if person_id in self.person_last_alerted:
                if current_time - self.person_last_alerted[person_id] < self.alert_cooldown:
                    return
            
            self._trigger_alert(
                AlertType.LOITERING,
                f"⏱️ Loitering detected: {person_name} ({duration:.0f}s)",
                person_name
            )
            self.person_last_alerted[person_id] = current_time
    
    def _trigger_alert(self, alert_type: str, message: str, person_name: str = None,
                      confidence: float = None):
        """Trigger an alert."""
        alert = Alert(alert_type, message, person_name, confidence)
        
        # Add to history
        self.alert_history.append(alert)
        
        # Log
        if self.log_enabled:
            print(f"🔔 ALERT: {alert}")
        
        # Sound
        if self.sound_enabled:
            self._play_alert_sound(alert_type)
        
        # Call callbacks
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                print(f"Alert callback error: {e}")
    
    def _play_alert_sound(self, alert_type: str):
        """Play alert sound (Windows)."""
        try:
            if alert_type == AlertType.WATCHLIST_DETECTED:
                # High priority - multiple beeps
                winsound.Beep(1000, 200)
                time.sleep(0.1)
                winsound.Beep(1000, 200)
            elif alert_type == AlertType.VIP_DETECTED:
                # VIP - pleasant tone
                winsound.Beep(800, 300)
            elif alert_type == AlertType.UNKNOWN_PERSON:
                # Unknown - single beep
                winsound.Beep(600, 200)
            else:
                # Default beep
                winsound.Beep(500, 150)
        except:
            pass  # Sound not available
    
    def get_recent_alerts(self, count: int = 10) -> List[Alert]:
        """Get recent alerts."""
        return list(self.alert_history)[-count:]
    
    def clear_alerts(self):
        """Clear alert history."""
        self.alert_history.clear()
        print("🗑️ Alert history cleared")
    
    def get_alert_count(self) -> Dict[str, int]:
        """Get count of each alert type."""
        counts = {}
        for alert in self.alert_history:
            counts[alert.alert_type] = counts.get(alert.alert_type, 0) + 1
        return counts
