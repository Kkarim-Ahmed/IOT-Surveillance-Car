#!/usr/bin/env python3
"""
Main Entry Point for Hardware Control System
Demonstrates hardware initialization and basic operations
"""

import sys
import signal
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from hardware.managers.hardware_manager import hardware_manager
from hardware.utils.logger import get_logger


class HardwareApplication:
    """Main hardware application"""
    
    def __init__(self):
        self.logger = get_logger("main")
        self.running = False
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self):
        """Setup graceful shutdown handlers"""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info(f"Received signal {signum}, initiating shutdown...")
        self.running = False
    
    def run(self):
        """Run the hardware system"""
        self.logger.info("=" * 60)
        self.logger.info("Hardware Control System Starting...")
        self.logger.info("=" * 60)
        
        try:
            # Initialize hardware
            hardware_manager.initialize()
            
            self.running = True
            self.logger.info("System running. Press Ctrl+C to exit.")
            
            # Main loop - send heartbeats and monitor status
            while self.running:
                # Send heartbeats
                hardware_manager.heartbeat('motor')
                hardware_manager.heartbeat('servo')
                hardware_manager.heartbeat('ultrasonic')
                hardware_manager.heartbeat('camera')
                
                # Get status (optional - for monitoring)
                status = hardware_manager.get_status()
                
                # Log status periodically
                if int(time.time()) % 10 == 0:
                    self.logger.info(f"System Status: {status['health']}")
                
                time.sleep(1)
            
        except KeyboardInterrupt:
            self.logger.info("Keyboard interrupt received")
        
        except Exception as e:
            self.logger.critical(f"Critical error: {e}", exc_info=True)
            return 1
        
        finally:
            self.shutdown()
        
        return 0
    
    def shutdown(self):
        """Graceful shutdown"""
        self.logger.info("Shutting down hardware system...")
        hardware_manager.cleanup()
        self.logger.info("Shutdown complete")


def main():
    """Application entry point"""
    app = HardwareApplication()
    return app.run()


if __name__ == "__main__":
    sys.exit(main())
