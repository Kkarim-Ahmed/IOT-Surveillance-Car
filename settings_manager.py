#!/usr/bin/env python3
"""
Settings Manager
Handles loading, saving, and managing system settings.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any
import config


class SettingsManager:
    """Manage system settings with persistence."""
    
    DEFAULT_SETTINGS = {
        # Recognition settings
        "recognition_threshold": 0.30,
        
        # Camera settings
        "camera_index": 0,
        "frame_width": 640,
        "frame_height": 480,
        "fps_target": 30,
        "flip_horizontal": True,
        "flip_vertical": False,
        
        # Tracking settings
        "face_lost_timeout": 1.0,
        "body_tracking_enabled": True,
        "smoothing_factor": 0.3,
        "deadzone_x": 30,
        "deadzone_y": 30,
        
        # PID settings
        "pid_preset": "Normal",
        "pan_kp": 0.08,
        "pan_ki": 0.001,
        "pan_kd": 0.02,
        "tilt_kp": 0.08,
        "tilt_ki": 0.001,
        "tilt_kd": 0.02,
        
        # Performance settings
        "process_every_n_frames": 5,

        # Tiny LLM settings
        "tiny_llm_enabled": False,
        "tiny_llm_model_path": "models/qwen2.5-1.5b-instruct-q4_k_m.gguf",
        "tiny_llm_profile": "pi_fast",
        "tiny_llm_max_event_rate_sec": 2.0,

        # Coordinate settings
        "coordinate_smoothing_window": 5,
        
        # Display settings
        "show_confidence": True,
        "show_quality_metrics": True,
    }
    
    PID_PRESETS = {
        "Slow": {
            "pan_kp": 0.05, "pan_ki": 0.0005, "pan_kd": 0.01,
            "tilt_kp": 0.05, "tilt_ki": 0.0005, "tilt_kd": 0.01,
        },
        "Normal": {
            "pan_kp": 0.08, "pan_ki": 0.001, "pan_kd": 0.02,
            "tilt_kp": 0.08, "tilt_ki": 0.001, "tilt_kd": 0.02,
        },
        "Fast": {
            "pan_kp": 0.12, "pan_ki": 0.002, "pan_kd": 0.03,
            "tilt_kp": 0.12, "tilt_ki": 0.002, "tilt_kd": 0.03,
        },
        "Custom": {}  # User-defined
    }
    
    def __init__(self, settings_file: str = "settings.json"):
        self.settings_file = settings_file
        self.settings = self.DEFAULT_SETTINGS.copy()
        self.load_settings()
    
    def load_settings(self) -> bool:
        """Load settings from file."""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    loaded = json.load(f)
                    self.settings.update(loaded)
                print(f"✅ Settings loaded from {self.settings_file}")
                return True
            else:
                print(f"ℹ️  No settings file found, using defaults")
                return False
        except Exception as e:
            print(f"❌ Failed to load settings: {e}")
            return False
    
    def save_settings(self) -> bool:
        """Save settings to file."""
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(self.settings, f, indent=2)
            print(f"💾 Settings saved to {self.settings_file}")
            return True
        except Exception as e:
            print(f"❌ Failed to save settings: {e}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value."""
        return self.settings.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set a setting value."""
        self.settings[key] = value
    
    def apply_pid_preset(self, preset_name: str) -> bool:
        """Apply a PID preset."""
        if preset_name not in self.PID_PRESETS:
            return False
        
        preset = self.PID_PRESETS[preset_name]
        if preset:  # Not empty (Custom is empty)
            self.settings.update(preset)
        self.settings["pid_preset"] = preset_name
        return True
    
    def reset_to_defaults(self) -> None:
        """Reset all settings to defaults."""
        self.settings = self.DEFAULT_SETTINGS.copy()
        print("🔄 Settings reset to defaults")
    
    def export_settings(self, filename: str) -> bool:
        """Export settings to a file."""
        try:
            with open(filename, 'w') as f:
                json.dump(self.settings, f, indent=2)
            print(f"📤 Settings exported to {filename}")
            return True
        except Exception as e:
            print(f"❌ Failed to export settings: {e}")
            return False
    
    def import_settings(self, filename: str) -> bool:
        """Import settings from a file."""
        try:
            with open(filename, 'r') as f:
                imported = json.load(f)
                self.settings.update(imported)
            print(f"📥 Settings imported from {filename}")
            return True
        except Exception as e:
            print(f"❌ Failed to import settings: {e}")
            return False
    
    def validate_settings(self) -> bool:
        """Validate all settings are within acceptable ranges."""
        try:
            # Recognition threshold
            threshold = self.settings.get("recognition_threshold", 0.30)
            if not (0.15 <= threshold <= 0.60):
                print(f"⚠️  Recognition threshold {threshold} out of range, resetting to 0.30")
                self.settings["recognition_threshold"] = 0.30
            
            # Camera settings
            width = self.settings.get("frame_width", 640)
            if width not in [320, 640, 1280, 1920]:
                print(f"⚠️  Invalid frame width {width}, resetting to 640")
                self.settings["frame_width"] = 640
            
            height = self.settings.get("frame_height", 480)
            if height not in [240, 480, 720, 1080]:
                print(f"⚠️  Invalid frame height {height}, resetting to 480")
                self.settings["frame_height"] = 480
            
            fps = self.settings.get("fps_target", 30)
            if not (10 <= fps <= 60):
                print(f"⚠️  FPS {fps} out of range, resetting to 30")
                self.settings["fps_target"] = 30
            
            # Tracking settings
            timeout = self.settings.get("face_lost_timeout", 1.0)
            if not (0.5 <= timeout <= 10.0):
                print(f"⚠️  Face lost timeout {timeout} out of range, resetting to 1.0")
                self.settings["face_lost_timeout"] = 1.0
            
            smoothing = self.settings.get("smoothing_factor", 0.3)
            if not (0.1 <= smoothing <= 0.9):
                print(f"⚠️  Smoothing factor {smoothing} out of range, resetting to 0.3")
                self.settings["smoothing_factor"] = 0.3

            # Tiny LLM settings
            profile = self.settings.get("tiny_llm_profile", "pi_fast")
            if profile not in ["pi_fast", "balanced", "quality"]:
                print(f"⚠️  Invalid tiny LLM profile {profile}, resetting to pi_fast")
                self.settings["tiny_llm_profile"] = "pi_fast"

            event_rate = self.settings.get("tiny_llm_max_event_rate_sec", 2.0)
            if not (0.5 <= event_rate <= 30.0):
                print(f"⚠️  tiny_llm_max_event_rate_sec {event_rate} out of range, resetting to 2.0")
                self.settings["tiny_llm_max_event_rate_sec"] = 2.0

            coord_window = self.settings.get("coordinate_smoothing_window", 5)
            if not (1 <= coord_window <= 30):
                print(f"⚠️  coordinate_smoothing_window {coord_window} out of range, resetting to 5")
                self.settings["coordinate_smoothing_window"] = 5
             
            return True
        except Exception as e:
            print(f"❌ Settings validation error: {e}")
            return False


# Global settings instance
_settings_instance = None


def get_settings() -> SettingsManager:
    """Get the global settings instance."""
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = SettingsManager()
    return _settings_instance
