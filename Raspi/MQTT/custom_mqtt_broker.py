"""
Custom MQTT Broker - Built from Scratch
A self-implemented MQTT broker without using Mosquitto or HiveMQ
Supports MQTT v3.1.1 protocol
"""

import asyncio
import logging
import struct
import time
from typing import Dict, Set, List, Tuple, Optional
from dataclasses import dataclass, field
from enum import IntEnum

logger = logging.getLogger(__name__)


class MQTTPacketType(IntEnum):
    """MQTT Control Packet Types"""
    CONNECT = 1
    CONNACK = 2
    PUBLISH = 3
    PUBACK = 4
    PUBREC = 5
    PUBREL = 6
    PUBCOMP = 7
    SUBSCRIBE = 8
    SUBACK = 9
    UNSUBSCRIBE = 10
    UNSUBACK = 11
    PINGREQ = 12
    PINGRESP = 13
    DISCONNECT = 14


class MQTTConnectReturnCode(IntEnum):
    """MQTT CONNACK Return Codes"""
    ACCEPTED = 0
    UNACCEPTABLE_PROTOCOL = 1
    IDENTIFIER_REJECTED = 2
    SERVER_UNAVAILABLE = 3
    BAD_CREDENTIALS = 4
    NOT_AUTHORIZED = 5


@dataclass
class MQTTMessage:
    """MQTT Message"""
    topic: str
    payload: bytes
    qos: int = 0
    retain: bool = False
    timestamp: float = field(default_factory=time.time)


@dataclass
class MQTTSubscription:
    """MQTT Subscription"""
    topic: str
    qos: int
    client_id: str


class MQTTClient:
    """Represents a connected MQTT client"""
    
    def __init__(self, client_id: str, reader: asyncio.StreamReader, 
                 writer: asyncio.StreamWriter, clean_session: bool = True):
        self.client_id = client_id
        self.reader = reader
        self.writer = writer
        self.clean_session = clean_session
        self.subscriptions: Dict[str, int] = {}  # topic -> qos
        self.connected = True
        self.last_activity = time.time()
        self.keepalive = 60
        
    async def send_packet(self, packet: bytes):
        """Send MQTT packet to client"""
        try:
            self.writer.write(packet)
            await self.writer.drain()
            self.last_activity = time.time()
        except Exception as e:
            logger.error(f"Error sending packet to {self.client_id}: {e}")
            self.connected = False
    
    def is_alive(self) -> bool:
        """Check if client is still alive based on keepalive"""
        if self.keepalive == 0:
            return self.connected
        return (time.time() - self.last_activity) < (self.keepalive * 1.5)


class CustomMQTTBroker:
    """
    Custom MQTT Broker Implementation
    Implements MQTT v3.1.1 protocol from scratch
    """
    
    def __init__(self, host: str = "0.0.0.0", port: int = 1883):
        self.host = host
        self.port = port
        self.clients: Dict[str, MQTTClient] = {}
        self.retained_messages: Dict[str, MQTTMessage] = {}
        self.server = None
        self.running = False
        
        # Statistics
        self.stats = {
            "clients_connected": 0,
            "messages_published": 0,
            "messages_delivered": 0,
            "subscriptions": 0
        }
    
    async def start(self):
        """Start the MQTT broker"""
        logger.info(f"Starting Custom MQTT Broker on {self.host}:{self.port}")
        
        self.server = await asyncio.start_server(
            self.handle_client,
            self.host,
            self.port
        )
        
        self.running = True
        
        # Start keepalive checker
        asyncio.create_task(self.keepalive_checker())
        
        logger.info(f"Custom MQTT Broker started on {self.host}:{self.port}")
        
        async with self.server:
            await self.server.serve_forever()
    
    async def stop(self):
        """Stop the MQTT broker"""
        logger.info("Stopping Custom MQTT Broker...")
        self.running = False
        
        # Disconnect all clients
        for client in list(self.clients.values()):
            await self.disconnect_client(client)
        
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        
        logger.info("Custom MQTT Broker stopped")
    
    async def handle_client(self, reader: asyncio.StreamReader, 
                           writer: asyncio.StreamWriter):
        """Handle new client connection"""
        addr = writer.get_extra_info('peername')
        logger.info(f"New connection from {addr}")
        
        client = None
        
        try:
            # Wait for CONNECT packet
            connect_packet = await asyncio.wait_for(
                self.read_packet(reader),
                timeout=10
            )
            
            if not connect_packet:
                logger.warning(f"No CONNECT packet from {addr}")
                writer.close()
                await writer.wait_closed()
                return
            
            # Parse CONNECT packet
            client_id, clean_session, keepalive = self.parse_connect(connect_packet)
            
            if not client_id:
                # Generate client ID if not provided
                client_id = f"auto_{int(time.time() * 1000)}"
            
            logger.info(f"Client {client_id} connecting (clean_session={clean_session})")
            
            # Check if client already connected
            if client_id in self.clients:
                old_client = self.clients[client_id]
                await self.disconnect_client(old_client)
            
            # Create client
            client = MQTTClient(client_id, reader, writer, clean_session)
            client.keepalive = keepalive
            self.clients[client_id] = client
            self.stats["clients_connected"] += 1
            
            # Send CONNACK
            connack = self.build_connack(MQTTConnectReturnCode.ACCEPTED)
            await client.send_packet(connack)
            
            logger.info(f"Client {client_id} connected successfully")
            
            # Handle client packets
            while client.connected and self.running:
                try:
                    packet = await asyncio.wait_for(
                        self.read_packet(reader),
                        timeout=keepalive * 1.5 if keepalive > 0 else None
                    )
                    
                    if not packet:
                        break
                    
                    await self.handle_packet(client, packet)
                    
                except asyncio.TimeoutError:
                    logger.warning(f"Client {client_id} keepalive timeout")
                    break
                except Exception as e:
                    logger.error(f"Error handling packet from {client_id}: {e}")
                    break
        
        except asyncio.TimeoutError:
            logger.warning(f"Connection timeout from {addr}")
        except Exception as e:
            logger.error(f"Error handling client {addr}: {e}")
        finally:
            if client:
                await self.disconnect_client(client)
            else:
                writer.close()
                await writer.wait_closed()
    
    async def read_packet(self, reader: asyncio.StreamReader) -> Optional[bytes]:
        """Read MQTT packet from stream"""
        try:
            # Read fixed header (first byte)
            first_byte = await reader.readexactly(1)
            if not first_byte:
                return None
            
            # Read remaining length
            remaining_length = 0
            multiplier = 1
            
            while True:
                byte = await reader.readexactly(1)
                remaining_length += (byte[0] & 0x7F) * multiplier
                
                if (byte[0] & 0x80) == 0:
                    break
                
                multiplier *= 128
                
                if multiplier > 128 * 128 * 128:
                    raise ValueError("Remaining length exceeds maximum")
            
            # Read remaining data
            if remaining_length > 0:
                remaining_data = await reader.readexactly(remaining_length)
                return first_byte + self.encode_remaining_length(remaining_length) + remaining_data
            else:
                return first_byte + b'\x00'
        
        except asyncio.IncompleteReadError:
            return None
        except Exception as e:
            logger.error(f"Error reading packet: {e}")
            return None
    
    def encode_remaining_length(self, length: int) -> bytes:
        """Encode remaining length for MQTT packet"""
        result = bytearray()
        
        while True:
            byte = length % 128
            length = length // 128
            
            if length > 0:
                byte |= 0x80
            
            result.append(byte)
            
            if length == 0:
                break
        
        return bytes(result)
    
    def parse_connect(self, packet: bytes) -> Tuple[str, bool, int]:
        """Parse CONNECT packet"""
        # Skip fixed header
        pos = 1
        
        # Skip remaining length
        while packet[pos] & 0x80:
            pos += 1
        pos += 1
        
        # Protocol name length
        protocol_name_len = struct.unpack("!H", packet[pos:pos+2])[0]
        pos += 2
        
        # Protocol name
        protocol_name = packet[pos:pos+protocol_name_len].decode('utf-8')
        pos += protocol_name_len
        
        # Protocol level
        protocol_level = packet[pos]
        pos += 1
        
        # Connect flags
        connect_flags = packet[pos]
        pos += 1
        
        clean_session = bool(connect_flags & 0x02)
        
        # Keep alive
        keepalive = struct.unpack("!H", packet[pos:pos+2])[0]
        pos += 2
        
        # Client ID length
        client_id_len = struct.unpack("!H", packet[pos:pos+2])[0]
        pos += 2
        
        # Client ID
        client_id = packet[pos:pos+client_id_len].decode('utf-8') if client_id_len > 0 else ""
        
        return client_id, clean_session, keepalive
    
    def build_connack(self, return_code: MQTTConnectReturnCode) -> bytes:
        """Build CONNACK packet"""
        fixed_header = (MQTTPacketType.CONNACK << 4).to_bytes(1, 'big')
        remaining_length = b'\x02'
        session_present = b'\x00'
        return_code_byte = return_code.to_bytes(1, 'big')
        
        return fixed_header + remaining_length + session_present + return_code_byte
    
    async def handle_packet(self, client: MQTTClient, packet: bytes):
        """Handle MQTT packet"""
        packet_type = (packet[0] >> 4) & 0x0F
        
        client.last_activity = time.time()
        
        if packet_type == MQTTPacketType.PUBLISH:
            await self.handle_publish(client, packet)
        elif packet_type == MQTTPacketType.SUBSCRIBE:
            await self.handle_subscribe(client, packet)
        elif packet_type == MQTTPacketType.UNSUBSCRIBE:
            await self.handle_unsubscribe(client, packet)
        elif packet_type == MQTTPacketType.PINGREQ:
            await self.handle_pingreq(client)
        elif packet_type == MQTTPacketType.DISCONNECT:
            await self.handle_disconnect(client)
        else:
            logger.warning(f"Unhandled packet type: {packet_type}")
    
    async def handle_publish(self, client: MQTTClient, packet: bytes):
        """Handle PUBLISH packet"""
        flags = packet[0] & 0x0F
        qos = (flags >> 1) & 0x03
        retain = bool(flags & 0x01)
        
        # Skip fixed header and remaining length
        pos = 1
        while packet[pos] & 0x80:
            pos += 1
        pos += 1
        
        # Topic length
        topic_len = struct.unpack("!H", packet[pos:pos+2])[0]
        pos += 2
        
        # Topic
        topic = packet[pos:pos+topic_len].decode('utf-8')
        pos += topic_len
        
        # Packet identifier (if QoS > 0)
        packet_id = None
        if qos > 0:
            packet_id = struct.unpack("!H", packet[pos:pos+2])[0]
            pos += 2
        
        # Payload
        payload = packet[pos:]
        
        logger.info(f"PUBLISH from {client.client_id}: {topic} (QoS {qos})")
        
        # Create message
        message = MQTTMessage(topic, payload, qos, retain)
        
        # Store retained message
        if retain:
            if len(payload) > 0:
                self.retained_messages[topic] = message
            else:
                # Empty payload clears retained message
                self.retained_messages.pop(topic, None)
        
        # Publish to subscribers
        await self.publish_to_subscribers(message)
        
        self.stats["messages_published"] += 1
        
        # Send PUBACK if QoS 1
        if qos == 1 and packet_id is not None:
            puback = self.build_puback(packet_id)
            await client.send_packet(puback)
    
    async def handle_subscribe(self, client: MQTTClient, packet: bytes):
        """Handle SUBSCRIBE packet"""
        # Skip fixed header and remaining length
        pos = 1
        while packet[pos] & 0x80:
            pos += 1
        pos += 1
        
        # Packet identifier
        packet_id = struct.unpack("!H", packet[pos:pos+2])[0]
        pos += 2
        
        # Parse subscriptions
        subscriptions = []
        
        while pos < len(packet):
            # Topic length
            topic_len = struct.unpack("!H", packet[pos:pos+2])[0]
            pos += 2
            
            # Topic
            topic = packet[pos:pos+topic_len].decode('utf-8')
            pos += topic_len
            
            # QoS
            qos = packet[pos]
            pos += 1
            
            subscriptions.append((topic, qos))
            client.subscriptions[topic] = qos
            
            logger.info(f"Client {client.client_id} subscribed to {topic} (QoS {qos})")
        
        self.stats["subscriptions"] += len(subscriptions)
        
        # Send retained messages for matching topics
        for topic, qos in subscriptions:
            for retained_topic, message in self.retained_messages.items():
                if self.topic_matches(topic, retained_topic):
                    await self.send_publish(client, message)
        
        # Send SUBACK
        suback = self.build_suback(packet_id, [qos for _, qos in subscriptions])
        await client.send_packet(suback)
    
    async def handle_unsubscribe(self, client: MQTTClient, packet: bytes):
        """Handle UNSUBSCRIBE packet"""
        # Skip fixed header and remaining length
        pos = 1
        while packet[pos] & 0x80:
            pos += 1
        pos += 1
        
        # Packet identifier
        packet_id = struct.unpack("!H", packet[pos:pos+2])[0]
        pos += 2
        
        # Parse topics
        while pos < len(packet):
            # Topic length
            topic_len = struct.unpack("!H", packet[pos:pos+2])[0]
            pos += 2
            
            # Topic
            topic = packet[pos:pos+topic_len].decode('utf-8')
            pos += topic_len
            
            client.subscriptions.pop(topic, None)
            logger.info(f"Client {client.client_id} unsubscribed from {topic}")
        
        # Send UNSUBACK
        unsuback = self.build_unsuback(packet_id)
        await client.send_packet(unsuback)
    
    async def handle_pingreq(self, client: MQTTClient):
        """Handle PINGREQ packet"""
        logger.debug(f"PINGREQ from {client.client_id}")
        
        # Send PINGRESP
        pingresp = bytes([MQTTPacketType.PINGRESP << 4, 0x00])
        await client.send_packet(pingresp)
    
    async def handle_disconnect(self, client: MQTTClient):
        """Handle DISCONNECT packet"""
        logger.info(f"Client {client.client_id} disconnecting")
        client.connected = False
    
    def build_puback(self, packet_id: int) -> bytes:
        """Build PUBACK packet"""
        fixed_header = (MQTTPacketType.PUBACK << 4).to_bytes(1, 'big')
        remaining_length = b'\x02'
        packet_id_bytes = struct.pack("!H", packet_id)
        
        return fixed_header + remaining_length + packet_id_bytes
    
    def build_suback(self, packet_id: int, qos_list: List[int]) -> bytes:
        """Build SUBACK packet"""
        fixed_header = (MQTTPacketType.SUBACK << 4).to_bytes(1, 'big')
        
        variable_header = struct.pack("!H", packet_id)
        payload = bytes(qos_list)
        
        remaining_length = self.encode_remaining_length(len(variable_header) + len(payload))
        
        return fixed_header + remaining_length + variable_header + payload
    
    def build_unsuback(self, packet_id: int) -> bytes:
        """Build UNSUBACK packet"""
        fixed_header = (MQTTPacketType.UNSUBACK << 4).to_bytes(1, 'big')
        remaining_length = b'\x02'
        packet_id_bytes = struct.pack("!H", packet_id)
        
        return fixed_header + remaining_length + packet_id_bytes
    
    async def publish_to_subscribers(self, message: MQTTMessage):
        """Publish message to all matching subscribers"""
        for client in list(self.clients.values()):
            if not client.connected:
                continue
            
            for sub_topic, sub_qos in client.subscriptions.items():
                if self.topic_matches(sub_topic, message.topic):
                    await self.send_publish(client, message)
                    self.stats["messages_delivered"] += 1
                    break
    
    async def send_publish(self, client: MQTTClient, message: MQTTMessage):
        """Send PUBLISH packet to client"""
        # Fixed header
        flags = (message.qos << 1) | (1 if message.retain else 0)
        fixed_header = ((MQTTPacketType.PUBLISH << 4) | flags).to_bytes(1, 'big')
        
        # Variable header
        topic_bytes = message.topic.encode('utf-8')
        topic_len = struct.pack("!H", len(topic_bytes))
        variable_header = topic_len + topic_bytes
        
        # Payload
        payload = message.payload
        
        # Remaining length
        remaining_length = self.encode_remaining_length(len(variable_header) + len(payload))
        
        packet = fixed_header + remaining_length + variable_header + payload
        
        await client.send_packet(packet)
    
    def topic_matches(self, subscription: str, topic: str) -> bool:
        """Check if topic matches subscription (with wildcards)"""
        sub_parts = subscription.split('/')
        topic_parts = topic.split('/')
        
        if len(sub_parts) > len(topic_parts):
            if sub_parts[-1] != '#':
                return False
        
        for i, sub_part in enumerate(sub_parts):
            if sub_part == '#':
                return True
            
            if i >= len(topic_parts):
                return False
            
            if sub_part != '+' and sub_part != topic_parts[i]:
                return False
        
        return len(sub_parts) == len(topic_parts)
    
    async def disconnect_client(self, client: MQTTClient):
        """Disconnect client"""
        logger.info(f"Disconnecting client {client.client_id}")
        
        client.connected = False
        self.clients.pop(client.client_id, None)
        
        try:
            client.writer.close()
            await client.writer.wait_closed()
        except Exception as e:
            logger.error(f"Error closing connection: {e}")
    
    async def keepalive_checker(self):
        """Check client keepalive timeouts"""
        while self.running:
            await asyncio.sleep(10)
            
            for client in list(self.clients.values()):
                if not client.is_alive():
                    logger.warning(f"Client {client.client_id} keepalive timeout")
                    await self.disconnect_client(client)
    
    def get_stats(self) -> dict:
        """Get broker statistics"""
        return {
            "clients_connected": len(self.clients),
            "total_connections": self.stats["clients_connected"],
            "messages_published": self.stats["messages_published"],
            "messages_delivered": self.stats["messages_delivered"],
            "subscriptions": self.stats["subscriptions"],
            "retained_messages": len(self.retained_messages)
        }


async def main():
    """Test the custom MQTT broker"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    broker = CustomMQTTBroker(host="0.0.0.0", port=1883)
    
    try:
        await broker.start()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        await broker.stop()


if __name__ == "__main__":
    asyncio.run(main())
