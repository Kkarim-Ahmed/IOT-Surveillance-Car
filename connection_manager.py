"""
connection_manager.py — MQTT connection manager with local / WAN broker switching.

Responsibilities:
  1. Load broker settings from client_config.json
  2. Build a configured paho-mqtt Client instance
  3. Connect to either the local broker or the cloud broker
  4. Handle automatic reconnection with exponential back-off
  5. Expose broker info for UI display
  6. Support TLS for HiveMQ cloud connections

Usage:
  manager = ConnectionManager(config_path="path/to/client_config.json")
  client  = manager.build_client("my-client-id", on_connect, on_disconnect, on_message)
  manager.connect(client, mode="local")   # or mode="cloud"
  client.loop_start()
"""

import json
import os
import time
import threading
import ssl

import paho.mqtt.client as mqtt


# ─── Defaults (used when config file is missing or incomplete) ────────────────
_DEFAULTS = {
    "local": {
        "host": "localhost",
        "port": 1883,
    },
    "cloud": {
        "host": "broker.hivemq.com",
        "port": 1883,
    },
}

# Reconnect back-off: start at 1 s, double each attempt, cap at 60 s
_RECONNECT_MIN_DELAY = 1
_RECONNECT_MAX_DELAY = 60


class ConnectionManager:
    """
    Manages MQTT broker connections for both local and WAN (cloud) modes.

    The config file (client_config.json) is expected to contain:
      {
        "local_broker":  { "host": "192.168.x.x", "port": 1883 },
        "cloud_broker":  { "host": "cluster.hivemq.cloud", "port": 8883 },
        "credentials":   { "username": "user", "password": "pass" },
        "client_id":     "surveillance-car-pi",
        "topics": { ... }
      }
    """

    def __init__(self, config_path: str = None):
        self._config      = {}
        self._config_path = config_path
        self._mode        = "local"
        self._client      = None
        self._reconnect_delay = _RECONNECT_MIN_DELAY

        if config_path:
            self._load_config(config_path)

    # ─── Config loading ───────────────────────────────────────────────────────

    def _load_config(self, path: str):
        """Load and parse client_config.json."""
        try:
            with open(path, "r") as f:
                self._config = json.load(f)
            print(f"[CONN_MGR] Config loaded from {path}")
        except FileNotFoundError:
            print(f"[CONN_MGR] Config not found at {path} — using defaults")
            self._config = {}
        except json.JSONDecodeError as e:
            print(f"[CONN_MGR] Config parse error: {e} — using defaults")
            self._config = {}

    def reload_config(self):
        """Reload config from disk (useful after editing client_config.json)."""
        if self._config_path:
            self._load_config(self._config_path)

    # ─── Broker info ──────────────────────────────────────────────────────────

    def get_broker_info(self, mode: str = None) -> dict:
        """
        Return { host, port, use_tls } for the requested mode.
        Falls back to _DEFAULTS if the config file doesn't specify the broker.
        """
        mode = mode or self._mode
        key  = "local_broker" if mode == "local" else "cloud_broker"
        cfg  = self._config.get(key, {})
        
        # Determine if TLS should be used (HiveMQ cloud uses port 8883 with TLS)
        port = int(cfg.get("port", _DEFAULTS[mode]["port"]))
        use_tls = (port == 8883) or (mode == "cloud" and "hivemq.cloud" in cfg.get("host", ""))
        
        return {
            "host": cfg.get("host", _DEFAULTS[mode]["host"]),
            "port": port,
            "use_tls": use_tls,
        }

    # ─── Client factory ───────────────────────────────────────────────────────

    def build_client(
        self,
        client_id    : str  = None,
        on_connect   = None,
        on_disconnect= None,
        on_message   = None,
    ) -> mqtt.Client:
        """
        Create and configure a paho-mqtt Client.

        Parameters
        ----------
        client_id     : MQTT client identifier (falls back to config value)
        on_connect    : callback(client, userdata, flags, rc)
        on_disconnect : callback(client, userdata, rc)
        on_message    : callback(client, userdata, msg)

        Returns
        -------
        Configured mqtt.Client (not yet connected)
        """
        cid = client_id or self._config.get("client_id", "surveillance-car-client")

        client = mqtt.Client(client_id=cid, clean_session=True)

        # Optional credentials
        creds = self._config.get("credentials", {})
        username = creds.get("username", "")
        password = creds.get("password", "")
        if username:
            client.username_pw_set(username, password)
            print(f"[CONN_MGR] Auth configured for user: {username}")

        # Attach callbacks
        if on_connect:
            client.on_connect = on_connect
        if on_message:
            client.on_message = on_message

        # Wrap on_disconnect to add reconnect logic
        client.on_disconnect = self._make_disconnect_handler(client, on_disconnect)

        self._client = client
        return client

    # ─── Connection ───────────────────────────────────────────────────────────

    def connect(self, client: mqtt.Client = None, mode: str = None):
        """
        Connect the client to the broker for the given mode.

        Parameters
        ----------
        client : mqtt.Client — if None, uses the last client built by build_client()
        mode   : "local" | "cloud" — if None, uses the current mode
        """
        client = client or self._client
        if client is None:
            raise RuntimeError("[CONN_MGR] No client available — call build_client() first")

        mode = mode or self._mode
        self._mode = mode

        info = self.get_broker_info(mode)
        host = info["host"]
        port = info["port"]
        use_tls = info["use_tls"]

        # Configure TLS if needed (for HiveMQ cloud)
        if use_tls:
            print(f"[CONN_MGR] Configuring TLS for {mode} broker")
            client.tls_set(ca_certs=None, certfile=None, keyfile=None,
                          cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLS,
                          ciphers=None)

        print(f"[CONN_MGR] Connecting to {mode} broker: {host}:{port} (TLS: {use_tls})")
        try:
            client.connect(host, port, keepalive=60)
            self._reconnect_delay = _RECONNECT_MIN_DELAY   # reset back-off on success
        except Exception as e:
            print(f"[CONN_MGR] Connection error: {e}")
            self._schedule_reconnect(client)

    def switch_mode(self, new_mode: str, client: mqtt.Client = None):
        """
        Disconnect from the current broker and reconnect to the other one.

        Parameters
        ----------
        new_mode : "local" | "cloud"
        client   : mqtt.Client — if None, uses the last built client
        """
        client = client or self._client
        if client is None:
            raise RuntimeError("[CONN_MGR] No client to switch")

        if new_mode == self._mode:
            print(f"[CONN_MGR] Already in {new_mode} mode")
            return

        print(f"[CONN_MGR] Switching from {self._mode} → {new_mode}")
        try:
            client.disconnect()
        except Exception:
            pass

        self._mode = new_mode
        time.sleep(0.5)   # brief pause before reconnecting
        self.connect(client, mode=new_mode)

    # ─── Reconnect logic ──────────────────────────────────────────────────────

    def _make_disconnect_handler(self, client: mqtt.Client, user_callback):
        """
        Wrap the user's on_disconnect callback with automatic reconnect logic.
        Uses exponential back-off: 1 s → 2 s → 4 s … capped at 60 s.
        """
        manager = self   # capture self for the closure

        def _handler(c, userdata, rc):
            if user_callback:
                user_callback(c, userdata, rc)

            if rc != 0:
                print(f"[CONN_MGR] Unexpected disconnect (rc={rc}) — scheduling reconnect")
                manager._schedule_reconnect(client)

        return _handler

    def _schedule_reconnect(self, client: mqtt.Client):
        """Schedule a reconnect attempt after the current back-off delay."""
        delay = self._reconnect_delay
        print(f"[CONN_MGR] Reconnecting in {delay}s…")

        def _attempt():
            try:
                self.connect(client)
            except Exception as e:
                print(f"[CONN_MGR] Reconnect failed: {e}")
                self._reconnect_delay = min(
                    self._reconnect_delay * 2, _RECONNECT_MAX_DELAY
                )
                self._schedule_reconnect(client)

        timer = threading.Timer(delay, _attempt)
        timer.daemon = True
        timer.start()

        # Increase back-off for next potential failure
        self._reconnect_delay = min(self._reconnect_delay * 2, _RECONNECT_MAX_DELAY)

    # ─── Convenience properties ───────────────────────────────────────────────

    @property
    def mode(self) -> str:
        """Current broker mode: "local" or "cloud"."""
        return self._mode

    @property
    def topics(self) -> dict:
        """Return the topics dict from config (or empty dict if not set)."""
        return self._config.get("topics", {})

    def set_mode(self, mode: str):
        """Set the connection mode without connecting."""
        self._mode = mode
