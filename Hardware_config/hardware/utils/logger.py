"""
Hardware Logging Utility
Provides centralized logging for all hardware components
"""

import logging
import logging.handlers
from pathlib import Path
from typing import Optional
from datetime import datetime


class HardwareLogger:
    """Centralized hardware logging system"""
    
    _instance: Optional['HardwareLogger'] = None
    _initialized: bool = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self._setup_logging()
            HardwareLogger._initialized = True
    
    def _setup_logging(self):
        """Setup logging configuration"""
        # Create logs directory
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        # Configure root logger
        self.root_logger = logging.getLogger()
        self.root_logger.setLevel(logging.DEBUG)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(levelname)s - %(name)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        
        # File handler - general
        file_handler = logging.handlers.RotatingFileHandler(
            'logs/hardware.log',
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        
        # File handler - errors only
        error_handler = logging.handlers.RotatingFileHandler(
            'logs/errors.log',
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(file_formatter)
        
        # File handler - emergency events
        emergency_handler = logging.handlers.RotatingFileHandler(
            'logs/emergency.log',
            maxBytes=5*1024*1024,  # 5MB
            backupCount=3
        )
        emergency_handler.setLevel(logging.CRITICAL)
        emergency_handler.setFormatter(file_formatter)
        
        # Add handlers
        self.root_logger.addHandler(console_handler)
        self.root_logger.addHandler(file_handler)
        self.root_logger.addHandler(error_handler)
        self.root_logger.addHandler(emergency_handler)
    
    @staticmethod
    def get_logger(name: str) -> logging.Logger:
        """Get logger instance for a component"""
        return logging.getLogger(f"hardware.{name}")
    
    @staticmethod
    def log_emergency(component: str, message: str):
        """Log emergency event"""
        logger = HardwareLogger.get_logger(component)
        logger.critical(f"EMERGENCY: {message}")
    
    @staticmethod
    def log_hardware_state(component: str, state: dict):
        """Log hardware state"""
        logger = HardwareLogger.get_logger(component)
        logger.debug(f"State: {state}")


def get_logger(name: str) -> logging.Logger:
    """Convenience function to get logger"""
    HardwareLogger()  # Ensure initialized
    return HardwareLogger.get_logger(name)
