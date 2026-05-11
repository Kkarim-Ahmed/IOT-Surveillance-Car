"""
WebSocket Server - Core Server Implementation
Handles client connections, MQTT bridge, and message routing
"""

import asyncio
import logging
import json
from typing import Set
import signal

try:
    import websockets
    from websockets.server import WebSocketServerProtocol
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    logging.error("websockets library not available")

from . import config
from .video_stream_handler import VideoStreamHandler
from .audio_system import AudioSystem

logger = logging.getLogger(__name__)


class WebSocketServer:
    """Main WebSocket server with MQTT bridge"""
    
    def __init__(self, mqtt_controller):
        if not WEBSOCKETS_AVAILABLE:
            raise RuntimeError("websockets library is required")
        
        self.mqtt_controller = mqtt_controller
        self.clients: Set[WebSocketServerProtocol] = set()
        self.video_handler = VideoStreamHandler()
        self.audio_system = AudioSystem()
        self.server = None
        self.running = False
        
    async def start(self):
        """Start WebSocket server and streaming"""
        logger.info(f"Starting WebSocket server on {config.WS_HOST}:{config.WS_PORT}...")
        
        try:
            # Start video streaming
            if config.VIDEO_ENABLED:
                if self.video_handler.start():
                    logger.info("Video streaming initialized")
                else:
                    logger.warning("Video streaming failed to initialize")
            
            # Start audio streaming
            if config.AUDIO_ENABLED:
                if self.audio_system.start():
                    logger.info("Audio streaming initialized")
                else:
                    logger.warning("Audio streaming failed to initialize")
            
            # Start WebSocket server
            self.server = await websockets.serve(
                self.handle_client,
                config.WS_HOST,
                config.WS_PORT,
                ping_interval=config.WS_PING_INTERVAL,
                ping_timeout=config.WS_PING_TIMEOUT,
                max_size=10 * 1024 * 1024  # 10MB max message size
            )
            
            self.running = True
            logger.info(f"WebSocket server started on ws://{config.WS_HOST}:{config.WS_PORT}")
            
            # Start broadcasting tasks
            await asyncio.gather(
                self.video_handler.broadcast_frames(self.clients),
                self.audio_system.broadcast_audio(self.clients),
                self.stats_reporter()
            )
            
        except Exception as e:
            logger.error(f"Failed to start WebSocket server: {e}")
            raise
    
    async def handle_client(self, websocket: WebSocketServerProtocol, path: str):
        """Handle individual WebSocket client connection"""
        client_id = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        logger.info(f"Client connected: {client_id}")
        
        # Check max clients
        if len(self.clients) >= config.WS_MAX_CLIENTS:
            logger.warning(f"Max clients reached, rejecting {client_id}")
            await websocket.close(1008, "Server full")
            return
        
        # Add client
        self.clients.add(websocket)
        
        try:
            # Send welcome message
            await self.send_json(websocket, {
                "type": "welcome",
                "message": "Connected to Raspberry Pi Surveillance Car",
                "video_enabled": config.VIDEO_ENABLED,
                "audio_enabled": config.AUDIO_ENABLED
            })
            
            # Handle incoming messages
            async for message in websocket:
                await self.handle_message(websocket, message)
                
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client disconnected: {client_id}")
        except Exception as e:
            logger.error(f"Error handling client {client_id}: {e}")
        finally:
            # Remove client
            self.clients.discard(websocket)
            logger.info(f"Client removed: {client_id} (Total: {len(self.clients)})")
    
    async def handle_message(self, websocket: WebSocketServerProtocol, message):
        """Handle incoming WebSocket message"""
        try:
            # Parse JSON message
            if isinstance(message, bytes):
                message = message.decode('utf-8')
            
            data = json.loads(message)
            msg_type = data.get("type")
            
            logger.debug(f"Received message type: {msg_type}")
            
            # Route message
            if msg_type == "mqtt_publish":
                await self.handle_mqtt_publish(data)
            elif msg_type == "command":
                await self.handle_command(data)
            elif msg_type == "ping":
                await self.send_json(websocket, {"type": "pong"})
            elif msg_type == "get_stats":
                await self.send_stats(websocket)
            else:
                logger.warning(f"Unknown message type: {msg_type}")
                
        except json.JSONDecodeError:
            logger.error("Invalid JSON received")
        except Exception as e:
            logger.error(f"Error handling message: {e}")
    
    async def handle_mqtt_publish(self, data: dict):
        """Handle MQTT publish request from WebSocket client"""
        topic = data.get("topic")
        payload = data.get("payload")
        
        if not topic or payload is None:
            logger.warning("MQTT publish missing topic or payload")
            return
        
        # Convert payload to string if needed
        if isinstance(payload, dict):
            payload = json.dumps(payload)
        elif not isinstance(payload, str):
            payload = str(payload)
        
        # Publish to MQTT
        logger.info(f"Publishing to MQTT: {topic} -> {payload}")
        self.mqtt_controller.connection.publish(topic, payload, qos=config.MQTT_QOS)
        
        # Broadcast to all WebSocket clients
        await self.broadcast_json({
            "type": "mqtt_message",
            "topic": topic,
            "payload": payload
        })
    
    async def handle_command(self, data: dict):
        """Handle control command"""
        command = data.get("command")
        params = data.get("params", {})
        
        logger.info(f"Command received: {command}")
        
        # Process command
        if command == "motor":
            direction = params.get("direction")
            if direction:
                # Publish to MQTT motor topic
                self.mqtt_controller.connection.publish(
                    config.MQTT_TOPIC_MOTOR,
                    json.dumps({"command": direction}),
                    qos=config.MQTT_QOS
                )
        elif command == "status":
            # Request status
            self.mqtt_controller.connection.publish(
                config.MQTT_TOPIC_STATUS,
                json.dumps({"command": "get_status"}),
                qos=config.MQTT_QOS
            )
    
    async def send_json(self, websocket: WebSocketServerProtocol, data: dict):
        """Send JSON message to specific client"""
        try:
            # Create packet: [TAG][JSON_DATA]
            json_str = json.dumps(data)
            packet = bytes([config.PACKET_TAG_JSON]) + json_str.encode('utf-8')
            await websocket.send(packet)
        except Exception as e:
            logger.error(f"Error sending JSON: {e}")
    
    async def broadcast_json(self, data: dict):
        """Broadcast JSON message to all clients"""
        if not self.clients:
            return
        
        # Create packet
        json_str = json.dumps(data)
        packet = bytes([config.PACKET_TAG_JSON]) + json_str.encode('utf-8')
        
        # Send to all clients
        tasks = []
        for client in list(self.clients):
            tasks.append(self._safe_send(client, packet))
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _safe_send(self, client, data):
        """Send data with error handling"""
        try:
            await asyncio.wait_for(client.send(data), timeout=1.0)
        except asyncio.TimeoutError:
            logger.debug("Client send timeout")
        except Exception as e:
            logger.debug(f"Error sending to client: {e}")
    
    async def send_stats(self, websocket: WebSocketServerProtocol):
        """Send statistics to client"""
        stats = {
            "type": "stats",
            "clients": len(self.clients),
            "video": self.video_handler.get_stats() if config.VIDEO_ENABLED else {},
            "audio": self.audio_system.get_stats() if config.AUDIO_ENABLED else {},
            "mqtt": self.mqtt_controller.get_stats()
        }
        await self.send_json(websocket, stats)
    
    async def stats_reporter(self):
        """Periodically log statistics"""
        while self.running:
            await asyncio.sleep(30)
            
            logger.info(f"=== STATS === Clients: {len(self.clients)}")
            
            if config.VIDEO_ENABLED:
                video_stats = self.video_handler.get_stats()
                logger.info(f"Video: {video_stats['fps']} fps, "
                          f"sent: {video_stats['frames_sent']}, "
                          f"dropped: {video_stats['frames_dropped']}")
            
            if config.AUDIO_ENABLED:
                audio_stats = self.audio_system.get_stats()
                logger.info(f"Audio: sent: {audio_stats['chunks_sent']}, "
                          f"dropped: {audio_stats['chunks_dropped']}")
    
    async def stop(self):
        """Stop WebSocket server"""
        logger.info("Stopping WebSocket server...")
        self.running = False
        
        # Close all client connections
        if self.clients:
            close_tasks = []
            for client in list(self.clients):
                close_tasks.append(client.close(1001, "Server shutting down"))
            await asyncio.gather(*close_tasks, return_exceptions=True)
        
        # Stop streaming
        self.video_handler.stop()
        self.audio_system.stop()
        
        # Close server
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        
        logger.info("WebSocket server stopped")
    
    def mqtt_message_received(self, topic: str, payload: str):
        """
        Callback for MQTT messages (called from MQTT thread)
        Forward to WebSocket clients
        """
        # Schedule async broadcast
        asyncio.create_task(self.broadcast_json({
            "type": "mqtt_message",
            "topic": topic,
            "payload": payload
        }))
