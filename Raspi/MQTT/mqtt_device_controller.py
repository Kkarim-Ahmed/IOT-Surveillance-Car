"""
MQTT Device Controller
Handles device-specific MQTT communication and control logic
"""

import logging
import json
from typing import Optional, Callable
from .connection_manager import MQTTConnectionManager

logger = logging.getLogger(__name__)


class MQTTDeviceController:
    """
    High-level MQTT controller for surveillance car
    Handles motor control, status updates, and command processing
    """
    
    def __init__(self, broker_host: str, broker_port: int, client_id: str,
                 username: str = None, password: str = None):
        self.connection = MQTTConnectionManager(broker_host, broker_port, client_id, username, password)
        self.command_handlers = {}
        self.status_callback = None
        
    def set_command_handler(self, command_type: str, handler: Callable):
        """Register handler for specific command type"""
        self.command_handlers[command_type] = handler
        logger.info(f"Registered handler for command: {command_type}")
    
    def set_status_callback(self, callback: Callable):
        """Set callback for status updates"""
        self.status_callback = callback
    
    def connect(self, keepalive: int = 60) -> bool:
        """Connect to MQTT broker"""
        # Set message callback
        self.connection.set_message_callback(self._handle_mqtt_message)
        
        # Connect
        return self.connection.connect(keepalive)
    
    def subscribe_to_topics(self, topics: list, qos: int = 1):
        """Subscribe to multiple topics"""
        for topic in topics:
            self.connection.subscribe(topic, qos)
    
    def _handle_mqtt_message(self, topic: str, payload: str):
        """Handle incoming MQTT messages"""
        try:
            logger.info(f"Processing message from {topic}: {payload}")
            
            # Try to parse as JSON
            try:
                data = json.loads(payload)
            except json.JSONDecodeError:
                # Plain text payload
                data = {"raw": payload}
            
            # Route to appropriate handler
            if topic == "dev/motor":
                self._handle_motor_command(data)
            elif topic == "dev/control":
                self._handle_control_command(data)
            elif topic == "dev/status":
                self._handle_status_request(data)
            else:
                logger.warning(f"No handler for topic: {topic}")
                
        except Exception as e:
            logger.error(f"Error handling MQTT message: {e}")
    
    def _handle_motor_command(self, data: dict):
        """Handle motor control commands"""
        command = data.get("command") or data.get("raw")
        
        if not command:
            logger.warning("Motor command missing")
            return
        
        logger.info(f"Motor command: {command}")
        
        # Call registered handler
        if "motor" in self.command_handlers:
            self.command_handlers["motor"](command, data)
        else:
            logger.warning("No motor command handler registered")
    
    def _handle_control_command(self, data: dict):
        """Handle general control commands"""
        command = data.get("command") or data.get("raw")
        
        if not command:
            logger.warning("Control command missing")
            return
        
        logger.info(f"Control command: {command}")
        
        # Call registered handler
        if "control" in self.command_handlers:
            self.command_handlers["control"](command, data)
        else:
            logger.warning("No control command handler registered")
    
    def _handle_status_request(self, data: dict):
        """Handle status request"""
        logger.info("Status request received")
        
        # Call status callback
        if self.status_callback:
            status = self.status_callback()
            self.publish_status(status)
    
    def publish_motor_state(self, state: str, details: dict = None):
        """Publish motor state"""
        payload = {
            "state": state,
            "timestamp": self._get_timestamp()
        }
        
        if details:
            payload.update(details)
        
        self.connection.publish("dev/motor", json.dumps(payload))
    
    def publish_status(self, status: dict):
        """Publish device status"""
        payload = {
            "status": status,
            "timestamp": self._get_timestamp()
        }
        
        self.connection.publish("dev/status", json.dumps(payload))
    
    def publish_event(self, topic: str, event_type: str, data: dict = None):
        """Publish generic event"""
        payload = {
            "event": event_type,
            "timestamp": self._get_timestamp()
        }
        
        if data:
            payload.update(data)
        
        self.connection.publish(topic, json.dumps(payload))
    
    def disconnect(self):
        """Disconnect from MQTT broker"""
        self.connection.disconnect()
    
    def is_connected(self) -> bool:
        """Check connection status"""
        return self.connection.is_connected()
    
    def get_stats(self) -> dict:
        """Get connection statistics"""
        return self.connection.get_stats()
    
    @staticmethod
    def _get_timestamp() -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().isoformat()
