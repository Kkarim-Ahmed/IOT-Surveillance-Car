"""
Ngrok Manager - WAN Tunnel Management
Handles automatic Ngrok tunnel creation for MQTT and WebSocket
"""

import asyncio
import logging
from typing import Optional, Dict
import subprocess
import json
import time

try:
    from pyngrok import ngrok, conf
    PYNGROK_AVAILABLE = True
except ImportError:
    PYNGROK_AVAILABLE = False
    logging.warning("pyngrok not available, will use subprocess method")

from . import config

logger = logging.getLogger(__name__)


class NgrokManager:
    """Manages Ngrok tunnels for WAN access"""
    
    def __init__(self):
        self.mqtt_tunnel = None
        self.ws_tunnel = None
        self.mqtt_url = None
        self.ws_url = None
        self.process = None
        self.use_pyngrok = PYNGROK_AVAILABLE and config.NGROK_AUTH_TOKEN
        
    async def start(self) -> Dict[str, str]:
        """
        Start Ngrok tunnels for MQTT and WebSocket
        Returns dict with public URLs
        """
        if not config.NGROK_ENABLED:
            logger.info("Ngrok is disabled in configuration")
            return {}
        
        logger.info("Starting Ngrok tunnels...")
        
        try:
            if self.use_pyngrok:
                return await self._start_with_pyngrok()
            else:
                return await self._start_with_subprocess()
        except Exception as e:
            logger.error(f"Failed to start Ngrok: {e}")
            return {}
    
    async def _start_with_pyngrok(self) -> Dict[str, str]:
        """Start tunnels using pyngrok library"""
        try:
            # Set auth token if provided
            if config.NGROK_AUTH_TOKEN:
                ngrok.set_auth_token(config.NGROK_AUTH_TOKEN)
            
            # Configure region
            conf.get_default().region = config.NGROK_REGION
            
            # Create MQTT tunnel (TCP)
            logger.info(f"Creating MQTT TCP tunnel on port {config.NGROK_MQTT_PORT}...")
            self.mqtt_tunnel = ngrok.connect(
                config.NGROK_MQTT_PORT,
                "tcp",
                bind_tls=False
            )
            self.mqtt_url = self.mqtt_tunnel.public_url
            
            # Create WebSocket tunnel (HTTP)
            logger.info(f"Creating WebSocket tunnel on port {config.NGROK_WS_PORT}...")
            self.ws_tunnel = ngrok.connect(
                config.NGROK_WS_PORT,
                "http",
                bind_tls=True
            )
            self.ws_url = self.ws_tunnel.public_url.replace("https://", "wss://")
            
            self._print_tunnel_info()
            
            return {
                "mqtt": self.mqtt_url,
                "websocket": self.ws_url
            }
            
        except Exception as e:
            logger.error(f"pyngrok error: {e}")
            raise
    
    async def _start_with_subprocess(self) -> Dict[str, str]:
        """Start tunnels using ngrok subprocess (fallback method)"""
        try:
            # Create ngrok config file
            config_content = f"""
version: "2"
authtoken: {config.NGROK_AUTH_TOKEN if config.NGROK_AUTH_TOKEN else ''}
region: {config.NGROK_REGION}
tunnels:
  mqtt:
    proto: tcp
    addr: {config.NGROK_MQTT_PORT}
  websocket:
    proto: http
    addr: {config.NGROK_WS_PORT}
"""
            
            with open("/tmp/ngrok.yml", "w") as f:
                f.write(config_content)
            
            # Start ngrok
            logger.info("Starting ngrok subprocess...")
            self.process = subprocess.Popen(
                ["ngrok", "start", "--all", "--config", "/tmp/ngrok.yml"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Wait for tunnels to establish
            await asyncio.sleep(3)
            
            # Get tunnel info from API
            urls = await self._get_tunnel_urls_from_api()
            
            if urls:
                self.mqtt_url = urls.get("mqtt")
                self.ws_url = urls.get("websocket")
                self._print_tunnel_info()
                return urls
            else:
                logger.warning("Could not retrieve tunnel URLs from ngrok API")
                return {}
                
        except FileNotFoundError:
            logger.error("ngrok command not found. Please install ngrok.")
            return {}
        except Exception as e:
            logger.error(f"Subprocess error: {e}")
            return {}
    
    async def _get_tunnel_urls_from_api(self) -> Dict[str, str]:
        """Query ngrok local API for tunnel URLs"""
        try:
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                async with session.get("http://localhost:4040/api/tunnels") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        urls = {}
                        
                        for tunnel in data.get("tunnels", []):
                            name = tunnel.get("name")
                            public_url = tunnel.get("public_url")
                            
                            if name == "mqtt":
                                urls["mqtt"] = public_url
                            elif name == "websocket":
                                urls["websocket"] = public_url.replace("https://", "wss://")
                        
                        return urls
        except Exception as e:
            logger.error(f"Failed to query ngrok API: {e}")
        
        return {}
    
    def _print_tunnel_info(self):
        """Print tunnel information to console"""
        print("\n" + "="*70)
        print("🌐 NGROK WAN TUNNELS ACTIVE")
        print("="*70)
        if self.mqtt_url:
            print(f"📡 MQTT Broker (TCP): {self.mqtt_url}")
            # Extract host and port from tcp://host:port
            if self.mqtt_url.startswith("tcp://"):
                host_port = self.mqtt_url.replace("tcp://", "")
                print(f"   Connect with: mqtt://{host_port}")
        if self.ws_url:
            print(f"🔌 WebSocket Server: {self.ws_url}")
            print(f"   Connect with: {self.ws_url}")
        print("="*70 + "\n")
    
    async def stop(self):
        """Stop all Ngrok tunnels"""
        logger.info("Stopping Ngrok tunnels...")
        
        try:
            if self.use_pyngrok:
                if self.mqtt_tunnel:
                    ngrok.disconnect(self.mqtt_tunnel.public_url)
                if self.ws_tunnel:
                    ngrok.disconnect(self.ws_tunnel.public_url)
                ngrok.kill()
            else:
                if self.process:
                    self.process.terminate()
                    try:
                        self.process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        self.process.kill()
            
            logger.info("Ngrok tunnels stopped")
        except Exception as e:
            logger.error(f"Error stopping Ngrok: {e}")
    
    def get_urls(self) -> Dict[str, str]:
        """Get current tunnel URLs"""
        return {
            "mqtt": self.mqtt_url,
            "websocket": self.ws_url
        }
    
    async def reconnect(self):
        """Reconnect tunnels after failure"""
        logger.info("Attempting to reconnect Ngrok tunnels...")
        await self.stop()
        await asyncio.sleep(config.RECONNECT_DELAY)
        return await self.start()
