"""
websocket_server.py
====================
Core async WebSocket server for the Raspberry Pi surveillance car.

Responsibilities:
  - Accept multiple simultaneous WebSocket clients
  - Broadcast binary video/audio frames to all connected clients
  - Bridge MQTT status messages → WebSocket clients
  - Bridge WebSocket control commands → MQTT topics
  - Handle client reconnects and disconnections gracefully
  - Support WAN access (configurable host/port)

WAN / Network Notes:
  - Port Forwarding : Forward WS_PORT (see config.py) on your router to the Pi.
  - Reverse Proxy   : Place nginx/caddy in front and proxy ws:// → wss://.
    Example nginx snippet:
        location /ws {
            proxy_pass http://127.0.0.1:8765;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "Upgrade";
        }
  - Firewall        : sudo ufw allow <WS_PORT>/tcp
    Restrict to known IPs in production:
        sudo ufw allow from <dashboard_ip> to any port <WS_PORT>

All tunable values are in config.py.

Dependencies:
    pip install websockets paho-mqtt
"""

import asyncio
import json
import logging
import signal
import time
from typing import Optional, Set

import websockets
from websockets.server import WebSocketServerProtocol

import config

# ── Optional MQTT bridge (gracefully disabled if paho not installed) ──────────
try:
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False
    logging.warning("paho-mqtt not installed – MQTT bridge disabled.")

# ─────────────────────────────────────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL, logging.INFO),
    format=config.LOG_FORMAT,
    datefmt=config.LOG_DATE_FORMAT,
)
logger = logging.getLogger("WebSocketServer")


# ─────────────────────────────────────────────────────────────────────────────
# WebSocketServer
# ─────────────────────────────────────────────────────────────────────────────
class WebSocketServer:
    """
    Async WebSocket server that:
      - Maintains a set of connected clients
      - Broadcasts binary frames (video/audio) to all clients
      - Bridges MQTT ↔ WebSocket messages
    """

    def __init__(
        self,
        host: str = config.WS_HOST,
        port: int = config.WS_PORT,
        mqtt_broker: str = config.MQTT_BROKER,
        mqtt_port: int = config.MQTT_PORT,
    ) -> None:
        self.host = host
        self.port = port
        self.mqtt_broker = mqtt_broker
        self.mqtt_port = mqtt_port

        # Connected WebSocket clients
        self._clients: Set[WebSocketServerProtocol] = set()

        # Per-client asyncio queues for backpressure control
        self._client_queues: dict[WebSocketServerProtocol, asyncio.Queue] = {}

        # MQTT client (optional)
        self._mqtt_client: Optional[mqtt.Client] = None

        # asyncio event loop reference (set on start)
        self._loop: Optional[asyncio.AbstractEventLoop] = None

        # Broadcast statistics
        self._frame_count: int = 0
        self._last_stat_time: float = time.time()

    # ── Public API ────────────────────────────────────────────────────────────

    async def broadcast_frame(self, data: bytes, frame_type: str = "video") -> None:
        """
        Broadcast a binary frame to all connected clients.
        Prepends a 1-byte type tag so the dashboard can demux streams:
            0x01 = video JPEG
            0x02 = audio PCM
        Drops the frame for any client whose queue is full (backpressure).
        """
        if not self._clients:
            return

        tag = b"\x01" if frame_type == "video" else b"\x02"
        payload = tag + data

        for client in list(self._clients):
            q = self._client_queues.get(client)
            if q is None:
                continue
            if q.full():
                # Drop oldest frame to keep latency low
                try:
                    q.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:
                pass  # Still full after drain – skip this client this frame

        self._frame_count += 1
        now = time.time()
        if now - self._last_stat_time >= config.WS_STATS_INTERVAL:
            fps = self._frame_count / (now - self._last_stat_time)
            logger.info(
                "Broadcast stats: %.1f fps | %d client(s) connected",
                fps,
                len(self._clients),
            )
            self._frame_count = 0
            self._last_stat_time = now

    async def broadcast_json(self, message: dict) -> None:
        """Broadcast a JSON control/status message to all clients."""
        if not self._clients:
            return
        payload = json.dumps(message).encode()
        tag = b"\x00"  # 0x00 = JSON message
        tagged = tag + payload
        for client in list(self._clients):
            q = self._client_queues.get(client)
            if q:
                try:
                    q.put_nowait(tagged)
                except asyncio.QueueFull:
                    pass

    async def start(self) -> None:
        """Start the WebSocket server and optional MQTT bridge."""
        self._loop = asyncio.get_running_loop()

        # Graceful shutdown on SIGINT / SIGTERM
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                self._loop.add_signal_handler(sig, self._request_shutdown)
            except NotImplementedError:
                pass  # Windows doesn't support add_signal_handler

        if MQTT_AVAILABLE:
            self._start_mqtt_bridge()

        logger.info("WebSocket server starting on ws://%s:%d", self.host, self.port)
        
        if not config.NGROK_ENABLED:
            logger.info("Local network only. For WAN access:")
            logger.info("  Option 1: Forward port %d on your router to this device", self.port)
            logger.info("  Option 2: Enable Ngrok (NGROK_ENABLED=true NGROK_AUTH_TOKEN=token)")
        else:
            logger.info("Ngrok tunneling enabled - public URL will be displayed shortly")

        async with websockets.serve(
            self._client_handler,
            self.host,
            self.port,
            ping_interval=config.WS_PING_INTERVAL,
            ping_timeout=config.WS_PING_TIMEOUT,
            max_size=config.WS_MAX_MESSAGE_SIZE,
            compression=None,           # Disable per-message compression (we pre-compress)
        ):
            logger.info("Server ready. Waiting for clients…")
            await asyncio.Future()  # Run forever until shutdown signal

    # ── Internal handlers ─────────────────────────────────────────────────────

    async def _client_handler(self, websocket: WebSocketServerProtocol) -> None:
        """Handle a single client connection lifecycle."""
        remote = websocket.remote_address
        logger.info("Client connected: %s:%s", *remote)

        # Register client with a bounded send queue
        queue: asyncio.Queue = asyncio.Queue(maxsize=config.WS_CLIENT_QUEUE_MAX)
        self._clients.add(websocket)
        self._client_queues[websocket] = queue

        # Send a welcome JSON so the dashboard knows the stream is live
        await websocket.send(
            b"\x00" + json.dumps({"event": "connected", "server": "surveillance-car"}).encode()
        )

        # Spawn a dedicated sender task to drain the queue
        sender_task = asyncio.create_task(self._sender(websocket, queue))

        try:
            async for raw_message in websocket:
                await self._handle_client_message(raw_message)
        except websockets.exceptions.ConnectionClosedOK:
            logger.info("Client disconnected (clean): %s:%s", *remote)
        except websockets.exceptions.ConnectionClosedError as exc:
            logger.warning("Client disconnected (error): %s:%s – %s", *remote, exc)
        except Exception as exc:
            logger.error("Unexpected error for %s:%s – %s", *remote, exc)
        finally:
            sender_task.cancel()
            self._clients.discard(websocket)
            self._client_queues.pop(websocket, None)
            logger.info("Client cleaned up: %s:%s | Remaining: %d", *remote, len(self._clients))

    async def _sender(self, websocket: WebSocketServerProtocol, queue: asyncio.Queue) -> None:
        """Drain the per-client queue and send frames as fast as possible."""
        try:
            while True:
                payload = await queue.get()
                await websocket.send(payload)
        except (asyncio.CancelledError, websockets.exceptions.ConnectionClosed):
            pass

    async def _handle_client_message(self, raw: bytes | str) -> None:
        """
        Parse incoming WebSocket messages from the dashboard.
        JSON messages with a 'topic' key are forwarded to MQTT.
        Expected format: {"topic": "dev/motor", "payload": "forward"}
        """
        try:
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")
            msg = json.loads(raw)
            topic = msg.get("topic", "")
            payload = msg.get("payload", "")
            logger.debug("WS→MQTT: topic=%s payload=%s", topic, payload)
            if self._mqtt_client and topic:
                self._mqtt_client.publish(topic, str(payload))
        except (json.JSONDecodeError, UnicodeDecodeError):
            logger.warning("Received non-JSON message from client, ignoring.")

    # ── MQTT Bridge ───────────────────────────────────────────────────────────

    def _start_mqtt_bridge(self) -> None:
        """Connect to the MQTT broker and subscribe to status topics."""
        self._mqtt_client = mqtt.Client(client_id=config.MQTT_CLIENT_ID, clean_session=True)
        self._mqtt_client.on_connect = self._on_mqtt_connect
        self._mqtt_client.on_message = self._on_mqtt_message
        self._mqtt_client.on_disconnect = self._on_mqtt_disconnect

        try:
            self._mqtt_client.connect(self.mqtt_broker, self.mqtt_port, keepalive=config.MQTT_KEEPALIVE)
            self._mqtt_client.loop_start()
            logger.info("MQTT bridge connected to %s:%d", self.mqtt_broker, self.mqtt_port)
        except Exception as exc:
            logger.error("MQTT bridge failed to connect: %s", exc)
            self._mqtt_client = None

    def _on_mqtt_connect(self, client, userdata, flags, rc: int) -> None:
        if rc == 0:
            client.subscribe(config.MQTT_TOPIC_STATUS)
            client.subscribe(config.MQTT_TOPIC_MOTOR)
            logger.info("MQTT subscribed to %s, %s", config.MQTT_TOPIC_STATUS, config.MQTT_TOPIC_MOTOR)
        else:
            logger.error("MQTT connect failed with code %d", rc)

    def _on_mqtt_message(self, client, userdata, msg: mqtt.MQTTMessage) -> None:
        """Forward MQTT messages to all WebSocket clients."""
        if self._loop is None:
            return
        envelope = {"event": "mqtt", "topic": msg.topic, "payload": msg.payload.decode("utf-8", errors="replace")}
        asyncio.run_coroutine_threadsafe(self.broadcast_json(envelope), self._loop)

    def _on_mqtt_disconnect(self, client, userdata, rc: int) -> None:
        logger.warning("MQTT disconnected (rc=%d). Will auto-reconnect.", rc)

    # ── Shutdown ──────────────────────────────────────────────────────────────

    def _request_shutdown(self) -> None:
        logger.info("Shutdown signal received.")
        if self._mqtt_client:
            self._mqtt_client.loop_stop()
            self._mqtt_client.disconnect()
        if self._loop:
            self._loop.stop()


# ─────────────────────────────────────────────────────────────────────────────
# Entry point (run server standalone for testing)
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    server = WebSocketServer()
    asyncio.run(server.start())
