"""
Main Entry Point - Raspberry Pi Surveillance Car
Orchestrates MQTT, WebSocket, and Ngrok services
"""

import asyncio
import logging
import signal
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from . import config
from .websocket_server import WebSocketServer
from .ngrok_manager import NgrokManager
from MQTT.mqtt_device_controller import MQTTDeviceController

logger = logging.getLogger(__name__)


class SurveillanceCarSystem:
    """Main system orchestrator"""
    
    def __init__(self):
        self.mqtt_controller = None
        self.websocket_server = None
        self.ngrok_manager = None
        self.running = False
        
    async def start(self):
        """Start all system components"""
        logger.info("="*70)
        logger.info("RASPBERRY PI SURVEILLANCE CAR - STARTING")
        logger.info("="*70)
        
        # Print configuration
        config.print_config()
        
        try:
            # 1. Initialize MQTT Controller
            logger.info("Initializing MQTT controller...")
            self.mqtt_controller = MQTTDeviceController(
                broker_host=config.MQTT_BROKER_HOST,
                broker_port=config.MQTT_BROKER_PORT,
                client_id=config.MQTT_CLIENT_ID
            )
            
            # Connect to MQTT broker
            if not self.mqtt_controller.connect(keepalive=config.MQTT_KEEPALIVE):
                logger.error("Failed to connect to MQTT broker")
                return False
            
            # Subscribe to topics
            self.mqtt_controller.subscribe_to_topics(
                config.MQTT_TOPICS_SUBSCRIBE,
                qos=config.MQTT_QOS
            )
            
            # Register command handlers
            self.mqtt_controller.set_command_handler("motor", self.handle_motor_command)
            self.mqtt_controller.set_command_handler("control", self.handle_control_command)
            self.mqtt_controller.set_status_callback(self.get_system_status)
            
            logger.info("MQTT controller initialized ✓")
            
            # 2. Initialize WebSocket Server
            logger.info("Initializing WebSocket server...")
            self.websocket_server = WebSocketServer(self.mqtt_controller)
            
            # Set MQTT message callback for WebSocket forwarding
            self.mqtt_controller.connection.set_message_callback(
                self.websocket_server.mqtt_message_received
            )
            
            logger.info("WebSocket server initialized ✓")
            
            # 3. Initialize Ngrok Manager
            if config.NGROK_ENABLED:
                logger.info("Initializing Ngrok tunnels...")
                self.ngrok_manager = NgrokManager()
                urls = await self.ngrok_manager.start()
                
                if urls:
                    logger.info("Ngrok tunnels initialized ✓")
                else:
                    logger.warning("Ngrok tunnels failed to initialize")
            
            # 4. Start WebSocket Server (blocking)
            self.running = True
            logger.info("\n" + "="*70)
            logger.info("🚀 SYSTEM READY - All services running")
            logger.info("="*70 + "\n")
            
            # Publish startup event
            self.mqtt_controller.publish_event(
                config.MQTT_TOPIC_STATUS,
                "system_started",
                {"message": "Surveillance car system online"}
            )
            
            # Start WebSocket server (this will block)
            await self.websocket_server.start()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to start system: {e}")
            return False
    
    def handle_motor_command(self, command: str, data: dict):
        """Handle motor control commands"""
        logger.info(f"Motor command: {command}")
        
        # Here you would integrate with actual motor control
        # For now, just log and acknowledge
        
        valid_commands = ["forward", "backward", "left", "right", "stop"]
        
        if command in valid_commands:
            logger.info(f"Executing motor command: {command}")
            # TODO: Integrate with GPIO/motor controller
            
            # Publish acknowledgment
            self.mqtt_controller.publish_motor_state(command, {"status": "executed"})
        else:
            logger.warning(f"Invalid motor command: {command}")
    
    def handle_control_command(self, command: str, data: dict):
        """Handle general control commands"""
        logger.info(f"Control command: {command}")
        
        if command == "shutdown":
            logger.info("Shutdown command received")
            asyncio.create_task(self.shutdown())
        elif command == "restart":
            logger.info("Restart command received")
            # TODO: Implement restart logic
        else:
            logger.warning(f"Unknown control command: {command}")
    
    def get_system_status(self) -> dict:
        """Get current system status"""
        status = {
            "system": "online",
            "mqtt_connected": self.mqtt_controller.is_connected(),
            "websocket_clients": len(self.websocket_server.clients) if self.websocket_server else 0,
            "video_enabled": config.VIDEO_ENABLED,
            "audio_enabled": config.AUDIO_ENABLED,
            "ngrok_enabled": config.NGROK_ENABLED
        }
        
        if self.ngrok_manager:
            urls = self.ngrok_manager.get_urls()
            status["ngrok_urls"] = urls
        
        return status
    
    async def shutdown(self):
        """Graceful shutdown"""
        logger.info("\n" + "="*70)
        logger.info("SHUTTING DOWN SYSTEM")
        logger.info("="*70)
        
        self.running = False
        
        # Publish shutdown event
        if self.mqtt_controller and self.mqtt_controller.is_connected():
            self.mqtt_controller.publish_event(
                config.MQTT_TOPIC_STATUS,
                "system_shutdown",
                {"message": "Surveillance car system shutting down"}
            )
        
        # Stop WebSocket server
        if self.websocket_server:
            await self.websocket_server.stop()
        
        # Stop Ngrok tunnels
        if self.ngrok_manager:
            await self.ngrok_manager.stop()
        
        # Disconnect MQTT
        if self.mqtt_controller:
            self.mqtt_controller.disconnect()
        
        logger.info("System shutdown complete")


async def main():
    """Main entry point"""
    system = SurveillanceCarSystem()
    
    # Setup signal handlers for graceful shutdown
    loop = asyncio.get_event_loop()
    
    def signal_handler(sig):
        logger.info(f"Received signal {sig}")
        asyncio.create_task(system.shutdown())
    
    # Register signal handlers
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda s=sig: signal_handler(s))
    
    # Start system
    try:
        await system.start()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    except Exception as e:
        logger.error(f"System error: {e}")
    finally:
        await system.shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Exiting...")
