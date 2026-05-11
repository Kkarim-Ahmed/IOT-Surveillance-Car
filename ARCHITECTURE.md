# System Architecture Documentation

## Overview

This document describes the complete architecture of the Raspberry Pi Surveillance Car system, including component interactions, data flow, and design decisions.

## System Components

```
┌─────────────────────────────────────────────────────────────┐
│                     WAN (Internet)                          │
│                                                             │
│  ┌──────────────┐         ┌──────────────┐                │
│  │ Web Dashboard│         │ MQTT Client  │                │
│  │  (Browser)   │         │  (Mobile)    │                │
│  └──────┬───────┘         └──────┬───────┘                │
│         │                        │                         │
└─────────┼────────────────────────┼─────────────────────────┘
          │                        │
          │    Ngrok Tunnels       │
          │                        │
┌─────────┼────────────────────────┼─────────────────────────┐
│         │                        │                         │
│  ┌──────▼──────┐          ┌──────▼──────┐                │
│  │  WebSocket  │◄────────►│    MQTT     │                │
│  │   Server    │  Bridge  │   Broker    │                │
│  │  (Port 8765)│          │ (Port 1883) │                │
│  └──────┬──────┘          └──────┬──────┘                │
│         │                        │                         │
│         │                        │                         │
│  ┌──────▼──────┐          ┌──────▼──────┐                │
│  │   Video     │          │    MQTT     │                │
│  │  Streaming  │          │ Controller  │                │
│  └──────┬──────┘          └──────┬──────┘                │
│         │                        │                         │
│  ┌──────▼──────┐          ┌──────▼──────┐                │
│  │   Audio     │          │   Device    │                │
│  │  Streaming  │          │  Commands   │                │
│  └──────┬──────┘          └──────┬──────┘                │
│         │                        │                         │
│  ┌──────▼──────┐          ┌──────▼──────┐                │
│  │   Camera    │          │   Motors    │                │
│  │  (OpenCV)   │          │   (GPIO)    │                │
│  └─────────────┘          └─────────────┘                │
│                                                            │
│              Raspberry Pi                                  │
└────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. MQTT Broker (Mosquitto)

**Purpose**: Central message broker for IoT communication

**Configuration**: `Raspi/MQTT/mosquitto.conf`

**Features**:
- QoS 0/1 support
- Persistent sessions
- Topic-based pub/sub
- Reconnection handling

**Topics**:
```
dev/motor     - Motor control commands
dev/status    - System status updates
dev/control   - General control commands
dev/audio     - Audio metadata
dev/video     - Video metadata
```

**Port**: 1883 (TCP)

### 2. MQTT Connection Manager

**File**: `Raspi/MQTT/connection_manager.py`

**Responsibilities**:
- Maintain connection to broker
- Handle reconnection logic
- Subscribe to topics
- Publish messages
- Route incoming messages

**Key Features**:
- Automatic reconnection (max 10 attempts)
- Thread-safe message handling
- Connection statistics
- Callback-based message routing

### 3. MQTT Device Controller

**File**: `Raspi/MQTT/mqtt_device_controller.py`

**Responsibilities**:
- High-level device control
- Command routing
- Status reporting
- Event publishing

**Command Handlers**:
- Motor commands (forward, backward, left, right, stop)
- Control commands (shutdown, restart)
- Status requests

### 4. WebSocket Server

**File**: `Raspi/Network/WebSockets/websocket_server.py`

**Responsibilities**:
- Accept WebSocket connections
- Stream video/audio to clients
- Bridge MQTT ↔ WebSocket
- Handle client commands

**Features**:
- Multiple client support (configurable max)
- Binary protocol with packet tags
- Async broadcasting
- Connection management
- Statistics reporting

**Protocol**:
```
Binary Packet Format:
[TAG_BYTE][DATA]

Tags:
0x00 - JSON/MQTT events
0x01 - Video frames (JPEG)
0x02 - Audio chunks (PCM)
```

### 5. Video Stream Handler

**File**: `Raspi/Network/WebSockets/video_stream_handler.py`

**Responsibilities**:
- Capture video from camera
- Encode frames to JPEG
- Queue frames for streaming
- Broadcast to WebSocket clients

**Optimizations**:
- Separate capture thread (non-blocking)
- Frame dropping on queue full
- Configurable buffer size (1 frame)
- JPEG quality control
- FPS limiting

**Performance**:
- Target: 15 FPS @ 640x480
- JPEG quality: 65 (configurable)
- Buffer size: 1 frame (minimal latency)
- Frame drop threshold: 100ms

### 6. Audio System

**File**: `Raspi/Network/WebSockets/audio_system.py`

**Responsibilities**:
- Capture audio from microphone
- Stream PCM audio chunks
- Broadcast to WebSocket clients

**Specifications**:
- Format: PCM 16-bit
- Sample rate: 16kHz
- Channels: Mono
- Chunk size: 1024 samples

**Optimizations**:
- Callback-based capture (non-blocking)
- Async queue bridge
- Chunk dropping on queue full
- Thread-safe operation

### 7. Ngrok Manager

**File**: `Raspi/Network/WebSockets/ngrok_manager.py`

**Responsibilities**:
- Create Ngrok tunnels
- Expose MQTT and WebSocket to WAN
- Retrieve public URLs
- Handle tunnel lifecycle

**Features**:
- Automatic tunnel creation
- Support for pyngrok and subprocess methods
- Region selection
- Auth token management
- Graceful shutdown

**Tunnels**:
- MQTT: TCP tunnel on port 1883
- WebSocket: HTTP tunnel on port 8765 (upgraded to WSS)

### 8. Configuration System

**File**: `Raspi/Network/WebSockets/config.py`

**Purpose**: Centralized configuration with environment variable override

**Categories**:
- WebSocket settings
- MQTT settings
- Video settings
- Audio settings
- Ngrok settings
- Logging settings
- Performance settings

**Override Example**:
```bash
VIDEO_FPS=30 AUDIO_ENABLED=false python -m Raspi.Network.WebSockets.main
```

### 9. Main Orchestrator

**File**: `Raspi/Network/WebSockets/main.py`

**Responsibilities**:
- Initialize all components
- Start services in correct order
- Handle graceful shutdown
- Register signal handlers
- Coordinate component communication

**Startup Sequence**:
1. Initialize MQTT controller
2. Connect to MQTT broker
3. Subscribe to topics
4. Initialize WebSocket server
5. Start Ngrok tunnels
6. Start video/audio streaming
7. Start WebSocket server (blocking)

## Data Flow

### Video Streaming Flow

```
Camera → Capture Thread → Frame Queue → WebSocket Server → Clients
         (OpenCV)         (Async)       (Broadcast)
```

1. **Capture**: Separate thread captures frames from camera
2. **Encode**: Frames encoded to JPEG with quality setting
3. **Queue**: Frames placed in async queue (max 10)
4. **Broadcast**: WebSocket server broadcasts to all clients
5. **Drop**: Slow clients cause frame drops (no backlog)

### Audio Streaming Flow

```
Microphone → Audio Callback → Audio Queue → WebSocket Server → Clients
            (PyAudio)         (Async)       (Broadcast)
```

1. **Capture**: PyAudio callback captures audio chunks
2. **Queue**: Chunks placed in async queue (thread-safe)
3. **Broadcast**: WebSocket server broadcasts to all clients
4. **Drop**: Queue full causes chunk drops

### MQTT → WebSocket Bridge

```
MQTT Broker → Connection Manager → Device Controller → WebSocket Server → Clients
             (Callback)            (Handler)           (Broadcast)
```

1. **Receive**: MQTT message received by connection manager
2. **Route**: Device controller routes to appropriate handler
3. **Forward**: WebSocket server broadcasts to all clients
4. **Format**: Message wrapped in JSON packet with tag 0x00

### WebSocket → MQTT Bridge

```
Client → WebSocket Server → Device Controller → Connection Manager → MQTT Broker
        (JSON Parse)        (Publish)           (MQTT Publish)
```

1. **Receive**: WebSocket server receives JSON message
2. **Parse**: Extract topic and payload
3. **Publish**: Device controller publishes to MQTT
4. **Broadcast**: Message also broadcast to other WebSocket clients

## Async Architecture

### Event Loop Structure

```python
asyncio.gather(
    websocket_server.start(),      # Main WebSocket server
    video_handler.broadcast_frames(), # Video broadcasting
    audio_system.broadcast_audio(),   # Audio broadcasting
    stats_reporter()                  # Statistics logging
)
```

### Thread Safety

**Threads**:
1. Main thread: asyncio event loop
2. Video capture thread: OpenCV frame capture
3. Audio callback thread: PyAudio capture
4. MQTT network thread: Paho MQTT loop

**Synchronization**:
- Async queues for thread → async communication
- `asyncio.run_coroutine_threadsafe()` for callbacks
- Thread-safe MQTT client operations

### Queue Management

**Video Queue**:
- Max size: 10 frames
- Behavior: Drop oldest on full
- Purpose: Prevent memory buildup

**Audio Queue**:
- Max size: 10 chunks
- Behavior: Drop oldest on full
- Purpose: Maintain real-time streaming

## Network Protocol

### WebSocket Messages

**Client → Server**:

```json
{
  "type": "mqtt_publish",
  "topic": "dev/motor",
  "payload": "forward"
}
```

```json
{
  "type": "command",
  "command": "motor",
  "params": {"direction": "forward"}
}
```

```json
{
  "type": "get_stats"
}
```

**Server → Client**:

```json
{
  "type": "welcome",
  "message": "Connected",
  "video_enabled": true,
  "audio_enabled": true
}
```

```json
{
  "type": "mqtt_message",
  "topic": "dev/motor",
  "payload": "{\"state\":\"forward\"}"
}
```

### Binary Protocol

**Packet Structure**:
```
Byte 0: Tag (0x00, 0x01, 0x02)
Byte 1-N: Data
```

**Tag Meanings**:
- `0x00`: JSON data (UTF-8 encoded)
- `0x01`: JPEG image data
- `0x02`: PCM audio data (16-bit little-endian)

## Performance Characteristics

### Latency

- **Video**: ~100-200ms (capture + encode + network)
- **Audio**: ~50-100ms (capture + network)
- **MQTT**: ~10-50ms (local broker)
- **WebSocket**: ~10-50ms (local network)

### Throughput

- **Video**: ~500KB/s @ 15fps, 640x480, quality 65
- **Audio**: ~32KB/s @ 16kHz, 16-bit, mono
- **MQTT**: Minimal (text messages)

### Resource Usage

- **CPU**: 30-50% (video encoding dominant)
- **Memory**: ~100-200MB
- **Network**: ~600KB/s total

## Security Considerations

### Current State (Development)

- MQTT: Anonymous access allowed
- WebSocket: No authentication
- Ngrok: Public URLs (obscurity-based)

### Production Recommendations

1. **MQTT Authentication**:
   ```bash
   mosquitto_passwd -c /etc/mosquitto/passwd username
   ```

2. **TLS/SSL**:
   - Configure Mosquitto with certificates
   - Use WSS for WebSocket

3. **Access Control**:
   - Implement ACL in Mosquitto
   - Add WebSocket authentication

4. **Firewall**:
   ```bash
   sudo ufw allow 1883/tcp
   sudo ufw allow 8765/tcp
   ```

## Scalability

### Current Limits

- **WebSocket clients**: 10 (configurable)
- **MQTT clients**: Unlimited (broker dependent)
- **Video resolution**: 1280x720 max (Pi hardware)
- **Frame rate**: 30 FPS max (Pi hardware)

### Scaling Options

1. **More clients**: Increase `WS_MAX_CLIENTS`
2. **Better quality**: Increase resolution/quality (requires Pi 4)
3. **Multiple cameras**: Add more video handlers
4. **Cloud MQTT**: Bridge to cloud broker

## Error Handling

### Connection Failures

- **MQTT**: Automatic reconnection (max 10 attempts)
- **WebSocket**: Client reconnection required
- **Ngrok**: Manual restart required

### Resource Failures

- **Camera**: Graceful degradation (video disabled)
- **Audio**: Graceful degradation (audio disabled)
- **Queue full**: Drop frames/chunks (no blocking)

### Recovery Strategies

1. **Reconnection**: Automatic for MQTT
2. **Restart**: Systemd service auto-restart
3. **Logging**: Comprehensive error logging
4. **Monitoring**: Statistics reporting

## Testing Strategy

### Unit Tests

- Component initialization
- Message routing
- Queue management
- Protocol encoding/decoding

### Integration Tests

- MQTT ↔ WebSocket bridge
- Video/audio streaming
- Command execution
- Ngrok tunnel creation

### System Tests

- End-to-end communication
- Performance benchmarks
- Stress testing
- Failure recovery

### Test Script

```bash
python test_system.py
```

Tests:
- MQTT broker connection
- Video capture
- Audio capture
- WebSocket server
- Ngrok installation

## Deployment

### Development

```bash
./run.sh
```

### Production

```bash
sudo systemctl enable surveillance-car
sudo systemctl start surveillance-car
```

### Monitoring

```bash
sudo journalctl -u surveillance-car -f
mosquitto_sub -h localhost -t 'dev/#' -v
```

## Future Enhancements

1. **Object Detection**: Integrate TensorFlow Lite
2. **Autonomous Driving**: Path planning algorithms
3. **Sensor Integration**: Ultrasonic, IR, IMU
4. **Recording**: Save video/audio streams
5. **Cloud Storage**: Upload recordings
6. **Mobile App**: Native iOS/Android clients
7. **Multi-car**: Fleet management
8. **AI Control**: Voice commands, gesture control

---

**Architecture Version**: 1.0.0  
**Last Updated**: 2024  
**Author**: IoT Systems Engineer
