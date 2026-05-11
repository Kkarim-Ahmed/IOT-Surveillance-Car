"""
MQTT Connection Manager
Handles MQTT broker connection, reconnection, and message routing
"""

import logging
import time
from typing import Callable, Optional, Dict
import json

try:
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False
    logging.error("paho-mqtt not available, MQTT functionality disabled")

logger = logging.getLogger(__name__)


class MQTTConnectionManager:
    """Manages MQTT broker connection and message handling"""
    
    def __init__(self, broker_host: str, broker_port: int, client_id: str, 
                 username: str = None, password: str = None):
        if not MQTT_AVAILABLE:
            raise RuntimeError("paho-mqtt library is required")
        
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.client_id = client_id
        self.username = username
        self.password = password
        self.client = None
        self.connected = False
        self.message_callback = None
        self.subscribed_topics = []
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 10
        
    def set_message_callback(self, callback: Callable):
        """Set callback for incoming MQTT messages"""
        self.message_callback = callback
    
    def connect(self, keepalive: int = 60) -> bool:
        """Connect to MQTT broker"""
        try:
            logger.info(f"Connecting to MQTT broker at {self.broker_host}:{self.broker_port}...")
            
            # Create MQTT client
            self.client = mqtt.Client(client_id=self.client_id, protocol=mqtt.MQTTv311)
            
            # Set username/password if provided
            if self.username and self.password:
                self.client.username_pw_set(self.username, self.password)
                logger.info(f"Using authentication: username={self.username}")
            
            # Set callbacks
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.on_message = self._on_message
            
            # Connect to broker
            self.client.connect(self.broker_host, self.broker_port, keepalive)
            
            # Start network loop in background thread
            self.client.loop_start()
            
            # Wait for connection (with timeout)
            timeout = 10
            start_time = time.time()
            while not self.connected and (time.time() - start_time) < timeout:
                time.sleep(0.1)
            
            if self.connected:
                logger.info("Successfully connected to MQTT broker")
                self.reconnect_attempts = 0
                return True
            else:
                logger.error("Connection timeout")
                return False
                
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            return False
    
    def _on_connect(self, client, userdata, flags, rc):
        """Callback when connected to broker"""
        if rc == 0:
            self.connected = True
            logger.info("MQTT connection established")
            
            # Resubscribe to topics
            if self.subscribed_topics:
                for topic, qos in self.subscribed_topics:
                    self.client.subscribe(topic, qos)
                    logger.info(f"Subscribed to topic: {topic}")
        else:
            self.connected = False
            logger.error(f"MQTT connection failed with code {rc}")
    
    def _on_disconnect(self, client, userdata, rc):
        """Callback when disconnected from broker"""
        self.connected = False
        
        if rc != 0:
            logger.warning(f"Unexpected MQTT disconnection (code {rc})")
            self._attempt_reconnect()
        else:
            logger.info("MQTT disconnected gracefully")
    
    def _on_message(self, client, userdata, msg):
        """Callback when message received"""
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            
            logger.debug(f"MQTT message received: {topic} -> {payload}")
            
            # Call user callback if set
            if self.message_callback:
                self.message_callback(topic, payload)
                
        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}")
    
    def _attempt_reconnect(self):
        """Attempt to reconnect to broker"""
        if self.reconnect_attempts >= self.max_reconnect_attempts:
            logger.error("Max reconnection attempts reached")
            return
        
        self.reconnect_attempts += 1
        logger.info(f"Attempting reconnection ({self.reconnect_attempts}/{self.max_reconnect_attempts})...")
        
        try:
            self.client.reconnect()
        except Exception as e:
            logger.error(f"Reconnection failed: {e}")
    
    def subscribe(self, topic: str, qos: int = 1):
        """Subscribe to MQTT topic"""
        if not self.client:
            logger.error("MQTT client not initialized")
            return False
        
        try:
            # Store subscription for reconnection
            if (topic, qos) not in self.subscribed_topics:
                self.subscribed_topics.append((topic, qos))
            
            # Subscribe
            result, mid = self.client.subscribe(topic, qos)
            
            if result == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"Subscribed to topic: {topic} (QoS {qos})")
                return True
            else:
                logger.error(f"Failed to subscribe to {topic}")
                return False
                
        except Exception as e:
            logger.error(f"Error subscribing to topic: {e}")
            return False
    
    def publish(self, topic: str, payload: str, qos: int = 1, retain: bool = False) -> bool:
        """Publish message to MQTT topic"""
        if not self.client or not self.connected:
            logger.error("MQTT client not connected")
            return False
        
        try:
            result = self.client.publish(topic, payload, qos, retain)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.debug(f"Published to {topic}: {payload}")
                return True
            else:
                logger.error(f"Failed to publish to {topic}")
                return False
                
        except Exception as e:
            logger.error(f"Error publishing message: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from MQTT broker"""
        logger.info("Disconnecting from MQTT broker...")
        
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            self.connected = False
        
        logger.info("MQTT disconnected")
    
    def is_connected(self) -> bool:
        """Check if connected to broker"""
        return self.connected
    
    def get_stats(self) -> Dict:
        """Get connection statistics"""
        return {
            "connected": self.connected,
            "broker": f"{self.broker_host}:{self.broker_port}",
            "subscribed_topics": len(self.subscribed_topics),
            "reconnect_attempts": self.reconnect_attempts
        }
