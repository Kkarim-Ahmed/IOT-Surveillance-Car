"""
Audio System - Low Latency Audio Streaming
Handles PCM audio capture and async broadcasting
"""

import asyncio
import logging
import time
from typing import Set, Optional
import threading

try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False
    logging.warning("PyAudio not available, audio streaming disabled")

from . import config

logger = logging.getLogger(__name__)


class AudioSystem:
    """Handles audio capture and streaming"""
    
    def __init__(self):
        self.audio = None
        self.stream = None
        self.running = False
        self.audio_queue = asyncio.Queue(maxsize=config.ASYNC_QUEUE_MAXSIZE)
        self.stats = {
            "chunks_captured": 0,
            "chunks_dropped": 0,
            "chunks_sent": 0
        }
        
    def start(self):
        """Start audio capture"""
        if not PYAUDIO_AVAILABLE or not config.AUDIO_ENABLED:
            logger.warning("Audio streaming is disabled or PyAudio not available")
            return False
        
        try:
            logger.info("Initializing audio system...")
            self.audio = pyaudio.PyAudio()
            
            # Get audio format
            audio_format = self._get_pyaudio_format()
            
            # Determine input device
            device_index = None if config.AUDIO_INPUT_DEVICE_INDEX == -1 else config.AUDIO_INPUT_DEVICE_INDEX
            
            # Open audio stream with callback
            self.stream = self.audio.open(
                format=audio_format,
                channels=config.AUDIO_CHANNELS,
                rate=config.AUDIO_SAMPLE_RATE,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=config.AUDIO_CHUNK_SIZE,
                stream_callback=self._audio_callback
            )
            
            self.running = True
            self.stream.start_stream()
            
            logger.info(f"Audio streaming started: {config.AUDIO_SAMPLE_RATE}Hz, "
                       f"{config.AUDIO_CHANNELS} channel(s), {config.AUDIO_FORMAT}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start audio capture: {e}")
            return False
    
    def _get_pyaudio_format(self):
        """Get PyAudio format constant"""
        if config.AUDIO_FORMAT == "int16":
            return pyaudio.paInt16
        elif config.AUDIO_FORMAT == "int32":
            return pyaudio.paInt32
        elif config.AUDIO_FORMAT == "float32":
            return pyaudio.paFloat32
        else:
            return pyaudio.paInt16
    
    def _audio_callback(self, in_data, frame_count, time_info, status):
        """Audio callback (runs in separate thread)"""
        if status:
            logger.warning(f"Audio callback status: {status}")
        
        try:
            # Put audio chunk in async queue (non-blocking)
            try:
                # Use thread-safe put
                asyncio.run_coroutine_threadsafe(
                    self.audio_queue.put(in_data),
                    asyncio.get_event_loop()
                )
                self.stats["chunks_captured"] += 1
            except:
                # Queue full, drop chunk
                self.stats["chunks_dropped"] += 1
                
        except Exception as e:
            logger.error(f"Error in audio callback: {e}")
        
        return (in_data, pyaudio.paContinue)
    
    async def get_chunk(self) -> Optional[bytes]:
        """Get next audio chunk (async)"""
        try:
            chunk = await asyncio.wait_for(
                self.audio_queue.get(),
                timeout=1.0
            )
            return chunk
        except asyncio.TimeoutError:
            return None
    
    async def broadcast_audio(self, clients: Set):
        """Broadcast audio chunks to all connected WebSocket clients"""
        if not self.running:
            return
        
        while self.running:
            try:
                # Get audio chunk from queue
                chunk = await self.get_chunk()
                
                if chunk is None:
                    continue
                
                # Create packet: [TAG][AUDIO_DATA]
                packet = bytes([config.PACKET_TAG_AUDIO]) + chunk
                
                # Broadcast to all clients (async)
                if clients:
                    send_tasks = []
                    for client in list(clients):
                        send_tasks.append(self._send_chunk_to_client(client, packet))
                    
                    await asyncio.gather(*send_tasks, return_exceptions=True)
                    
                    self.stats["chunks_sent"] += 1
                    
            except Exception as e:
                logger.error(f"Error broadcasting audio: {e}")
                await asyncio.sleep(0.01)
    
    async def _send_chunk_to_client(self, client, packet):
        """Send audio chunk to single client with error handling"""
        try:
            await asyncio.wait_for(
                client.send(packet),
                timeout=0.1
            )
        except asyncio.TimeoutError:
            logger.debug("Client too slow, dropping audio chunk")
        except Exception as e:
            logger.debug(f"Failed to send audio to client: {e}")
    
    def stop(self):
        """Stop audio capture"""
        logger.info("Stopping audio capture...")
        self.running = False
        
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        
        if self.audio:
            self.audio.terminate()
        
        logger.info("Audio capture stopped")
    
    def get_stats(self) -> dict:
        """Get audio statistics"""
        return {
            "chunks_sent": self.stats["chunks_sent"],
            "chunks_dropped": self.stats["chunks_dropped"],
            "queue_size": self.audio_queue.qsize()
        }
