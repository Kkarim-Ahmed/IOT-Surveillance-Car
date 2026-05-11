"""
ngrok_manager.py
=================
Manages Ngrok tunnels for WebSocket and MQTT broker access over WAN.

Provides automatic tunnel creation, public URL retrieval, and graceful shutdown
without requiring router port forwarding. Works behind CGNAT and mobile hotspots.

Features:
  - WebSocket tunnel (wss:// public URL)
  - MQTT TCP tunnel (tcp:// public endpoint)
  - Automatic reconnection on tunnel failure
  - Clean shutdown and resource cleanup
  - Environment variable configuration

Dependencies:
    pip install pyngrok

Ngrok Setup:
    1. Sign up at https://ngrok.com (free tier works)
    2. Get your auth token from https://dashboard.ngrok.com/get-started/your-authtoken
    3. Set NGROK_AUTH_TOKEN environment variable or add to config.py

Architecture:
    NgrokManager runs in the asyncio event loop and manages subprocess-based
    ngrok tunnels. It monitors tunnel health and provides public URLs.
"""

import asyncio
import logging
import os
from typing import Optional, Dict
from dataclasses import dataclass

import config

logger = logging.getLogger("NgrokManager")

# Check if pyngrok is available
try:
    from pyngrok import ngrok, conf
    NGROK_AVAILABLE = True
except ImportError:
    NGROK_AVAILABLE = False
    logger.warning("pyngrok not installed – Ngrok tunneling disabled. Install: pip install pyngrok")


@dataclass
class TunnelInfo:
    """Information about an active Ngrok tunnel."""
    name: str
    public_url: str
    local_port: int
    protocol: str
    tunnel_obj: Optional[object] = None


class NgrokManager:
    """
    Manages Ngrok tunnels for WebSocket and MQTT services.
    
    Usage:
        manager = NgrokManager()
        await manager.start()
        print(f"WebSocket URL: {manager.websocket_url}")
        print(f"MQTT URL: {manager.mqtt_url}")
        # ... run your services ...
        await manager.stop()
    """

    def __init__(self) -> None:
        self._tunnels: Dict[str, TunnelInfo] = {}
        self._running = False
        self._monitor_task: Optional[asyncio.Task] = None

    # ── Public API ────────────────────────────────────────────────────────────

    async def start(self) -> None:
        """
        Start Ngrok tunnels based on configuration.
        Creates tunnels for enabled services and prints public URLs.
        """
        if not NGROK_AVAILABLE:
            logger.error("Cannot start Ngrok: pyngrok not installed")
            return

        if not config.NGROK_ENABLED:
            logger.info("Ngrok is disabled in configuration")
            return

        if not config.NGROK_AUTH_TOKEN:
            logger.error("NGROK_AUTH_TOKEN not set. Get your token from https://dashboard.ngrok.com")
            return

        logger.info("Starting Ngrok tunnels...")
        self._running = True

        # Configure Ngrok with auth token and region
        try:
            ngrok_config = conf.get_default()
            ngrok_config.auth_token = config.NGROK_AUTH_TOKEN
            ngrok_config.region = config.NGROK_REGION
            logger.info(f"Ngrok configured: region={config.NGROK_REGION}")
        except Exception as exc:
            logger.error(f"Failed to configure Ngrok: {exc}")
            return

        # Create WebSocket tunnel
        if config.NGROK_WEBSOCKET_ENABLED:
            await self._create_websocket_tunnel()

        # Create MQTT tunnel
        if config.NGROK_MQTT_ENABLED:
            await self._create_mqtt_tunnel()

        # Print summary
        self._print_tunnel_summary()

        # Start monitoring task
        self._monitor_task = asyncio.create_task(self._monitor_tunnels())

    async def stop(self) -> None:
        """Stop all Ngrok tunnels and cleanup resources."""
        logger.info("Stopping Ngrok tunnels...")
        self._running = False

        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

        # Disconnect all tunnels
        if NGROK_AVAILABLE:
            try:
                ngrok.kill()
                logger.info("All Ngrok tunnels closed")
            except Exception as exc:
                logger.warning(f"Error closing Ngrok tunnels: {exc}")

        self._tunnels.clear()

    @property
    def websocket_url(self) -> Optional[str]:
        """Get the public WebSocket URL (wss://)."""
        tunnel = self._tunnels.get("websocket")
        return tunnel.public_url if tunnel else None

    @property
    def mqtt_url(self) -> Optional[str]:
        """Get the public MQTT URL (tcp://)."""
        tunnel = self._tunnels.get("mqtt")
        return tunnel.public_url if tunnel else None

    @property
    def is_running(self) -> bool:
        """Check if Ngrok manager is running."""
        return self._running

    # ── Tunnel Creation ───────────────────────────────────────────────────────

    async def _create_websocket_tunnel(self) -> None:
        """Create Ngrok tunnel for WebSocket server."""
        try:
            port = config.NGROK_WS_PORT
            logger.info(f"Creating WebSocket tunnel for port {port}...")

            # Create tunnel (runs in executor to avoid blocking)
            loop = asyncio.get_running_loop()
            tunnel = await loop.run_in_executor(
                None,
                lambda: ngrok.connect(
                    port,
                    "http",  # Ngrok will upgrade to WebSocket automatically
                    bind_tls=True  # Force HTTPS/WSS
                )
            )

            public_url = tunnel.public_url.replace("https://", "wss://")
            
            self._tunnels["websocket"] = TunnelInfo(
                name="websocket",
                public_url=public_url,
                local_port=port,
                protocol="wss",
                tunnel_obj=tunnel
            )

            logger.info(f"✓ WebSocket tunnel created: {public_url}")

        except Exception as exc:
            logger.error(f"Failed to create WebSocket tunnel: {exc}")

    async def _create_mqtt_tunnel(self) -> None:
        """Create Ngrok tunnel for MQTT broker."""
        try:
            port = config.NGROK_MQTT_PORT
            logger.info(f"Creating MQTT tunnel for port {port}...")

            # Create TCP tunnel for MQTT
            loop = asyncio.get_running_loop()
            tunnel = await loop.run_in_executor(
                None,
                lambda: ngrok.connect(port, "tcp")
            )

            public_url = tunnel.public_url
            
            self._tunnels["mqtt"] = TunnelInfo(
                name="mqtt",
                public_url=public_url,
                local_port=port,
                protocol="tcp",
                tunnel_obj=tunnel
            )

            logger.info(f"✓ MQTT tunnel created: {public_url}")

        except Exception as exc:
            logger.error(f"Failed to create MQTT tunnel: {exc}")

    # ── Monitoring ────────────────────────────────────────────────────────────

    async def _monitor_tunnels(self) -> None:
        """
        Monitor tunnel health and attempt reconnection if needed.
        Runs as a background task.
        """
        logger.info("Tunnel monitoring started")
        
        while self._running:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds

                if not NGROK_AVAILABLE:
                    break

                # Get current tunnels from Ngrok
                loop = asyncio.get_running_loop()
                active_tunnels = await loop.run_in_executor(
                    None,
                    ngrok.get_tunnels
                )

                # Check if our tunnels are still active
                active_urls = {t.public_url for t in active_tunnels}
                
                for name, tunnel_info in list(self._tunnels.items()):
                    # Convert wss:// back to https:// for comparison
                    check_url = tunnel_info.public_url.replace("wss://", "https://")
                    
                    if check_url not in active_urls and tunnel_info.public_url not in active_urls:
                        logger.warning(f"Tunnel {name} appears down, attempting reconnect...")
                        
                        # Attempt reconnection
                        if name == "websocket" and config.NGROK_WEBSOCKET_ENABLED:
                            await self._create_websocket_tunnel()
                        elif name == "mqtt" and config.NGROK_MQTT_ENABLED:
                            await self._create_mqtt_tunnel()

            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error(f"Tunnel monitoring error: {exc}")
                await asyncio.sleep(5)

        logger.info("Tunnel monitoring stopped")

    # ── Utilities ─────────────────────────────────────────────────────────────

    def _print_tunnel_summary(self) -> None:
        """Print a formatted summary of all active tunnels."""
        if not self._tunnels:
            logger.warning("No Ngrok tunnels created")
            return

        logger.info("=" * 80)
        logger.info("🌐 NGROK TUNNELS ACTIVE - WAN ACCESS ENABLED")
        logger.info("=" * 80)

        for name, tunnel in self._tunnels.items():
            logger.info(f"")
            logger.info(f"  {name.upper()} Service:")
            logger.info(f"    Local:  {tunnel.protocol}://localhost:{tunnel.local_port}")
            logger.info(f"    Public: {tunnel.public_url}")
            logger.info(f"")

        logger.info("=" * 80)
        logger.info("📱 Use the PUBLIC URLs above to connect from anywhere on the internet")
        logger.info("🔒 Ngrok provides automatic HTTPS/WSS encryption")
        logger.info("⚠️  Free tier has connection limits - upgrade at https://ngrok.com/pricing")
        logger.info("=" * 80)

    def get_tunnel_info(self, service: str) -> Optional[TunnelInfo]:
        """Get tunnel information for a specific service."""
        return self._tunnels.get(service)

    def get_all_tunnels(self) -> Dict[str, TunnelInfo]:
        """Get information about all active tunnels."""
        return self._tunnels.copy()


# ─────────────────────────────────────────────────────────────────────────────
# Standalone test
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )

    async def test():
        manager = NgrokManager()
        
        try:
            await manager.start()
            
            if manager.websocket_url:
                print(f"\n✓ WebSocket accessible at: {manager.websocket_url}")
            if manager.mqtt_url:
                print(f"✓ MQTT accessible at: {manager.mqtt_url}")
            
            print("\nPress Ctrl+C to stop...")
            await asyncio.Future()  # Run forever
            
        except KeyboardInterrupt:
            print("\nShutting down...")
        finally:
            await manager.stop()

    asyncio.run(test())
