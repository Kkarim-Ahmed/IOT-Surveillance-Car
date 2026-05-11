"""
System Test Script
Tests MQTT, WebSocket, Video, and Audio components
"""

import asyncio
import json
import time
import sys
import os

# Add to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import paho.mqtt.client as mqtt
    import websockets
    import cv2
    import pyaudio
    DEPENDENCIES_OK = True
except ImportError as e:
    print(f"Missing dependency: {e}")
    DEPENDENCIES_OK = False


class SystemTester:
    """Test all system components"""
    
    def __init__(self):
        self.results = {}
    
    def test_mqtt_broker(self):
        """Test MQTT broker connection"""
        print("\n[TEST] MQTT Broker Connection...")
        
        try:
            client = mqtt.Client("test_client")
            client.connect("localhost", 1883, 60)
            client.loop_start()
            time.sleep(1)
            
            # Test publish
            client.publish("test/topic", "test_message")
            time.sleep(0.5)
            
            client.loop_stop()
            client.disconnect()
            
            print("✓ MQTT broker test PASSED")
            self.results['mqtt'] = True
            return True
            
        except Exception as e:
            print(f"✗ MQTT broker test FAILED: {e}")
            self.results['mqtt'] = False
            return False
    
    def test_video_capture(self):
        """Test video capture"""
        print("\n[TEST] Video Capture...")
        
        try:
            cap = cv2.VideoCapture(0)
            
            if not cap.isOpened():
                raise Exception("Cannot open camera")
            
            ret, frame = cap.read()
            
            if not ret:
                raise Exception("Cannot read frame")
            
            # Test encoding
            ret, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 65])
            
            if not ret:
                raise Exception("Cannot encode frame")
            
            cap.release()
            
            print(f"✓ Video capture test PASSED (Frame: {frame.shape}, JPEG: {len(jpeg)} bytes)")
            self.results['video'] = True
            return True
            
        except Exception as e:
            print(f"✗ Video capture test FAILED: {e}")
            self.results['video'] = False
            return False
    
    def test_audio_capture(self):
        """Test audio capture"""
        print("\n[TEST] Audio Capture...")
        
        try:
            p = pyaudio.PyAudio()
            
            # Get default input device
            info = p.get_default_input_device_info()
            print(f"  Default input device: {info['name']}")
            
            # Open stream
            stream = p.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                input=True,
                frames_per_buffer=1024
            )
            
            # Read chunk
            data = stream.read(1024)
            
            stream.stop_stream()
            stream.close()
            p.terminate()
            
            print(f"✓ Audio capture test PASSED ({len(data)} bytes)")
            self.results['audio'] = True
            return True
            
        except Exception as e:
            print(f"✗ Audio capture test FAILED: {e}")
            self.results['audio'] = False
            return False
    
    async def test_websocket_server(self):
        """Test WebSocket server"""
        print("\n[TEST] WebSocket Server...")
        
        try:
            # Try to connect
            uri = "ws://localhost:8765"
            
            async with websockets.connect(uri) as websocket:
                # Wait for welcome message
                message = await asyncio.wait_for(websocket.recv(), timeout=5)
                
                # Parse message
                data = message[1:]  # Skip tag byte
                json_data = json.loads(data.decode('utf-8'))
                
                print(f"  Received: {json_data}")
                
                # Send ping
                ping_msg = json.dumps({"type": "ping"})
                await websocket.send(ping_msg)
                
                # Wait for pong
                response = await asyncio.wait_for(websocket.recv(), timeout=5)
                
                print("✓ WebSocket server test PASSED")
                self.results['websocket'] = True
                return True
                
        except asyncio.TimeoutError:
            print("✗ WebSocket server test FAILED: Timeout")
            self.results['websocket'] = False
            return False
        except Exception as e:
            print(f"✗ WebSocket server test FAILED: {e}")
            print("  (Make sure the server is running)")
            self.results['websocket'] = False
            return False
    
    def test_ngrok(self):
        """Test Ngrok installation"""
        print("\n[TEST] Ngrok Installation...")
        
        try:
            import subprocess
            result = subprocess.run(['ngrok', 'version'], capture_output=True, text=True)
            
            if result.returncode == 0:
                version = result.stdout.strip()
                print(f"✓ Ngrok test PASSED ({version})")
                self.results['ngrok'] = True
                return True
            else:
                raise Exception("Ngrok command failed")
                
        except FileNotFoundError:
            print("✗ Ngrok test FAILED: Not installed")
            self.results['ngrok'] = False
            return False
        except Exception as e:
            print(f"✗ Ngrok test FAILED: {e}")
            self.results['ngrok'] = False
            return False
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        
        total = len(self.results)
        passed = sum(1 for v in self.results.values() if v)
        
        for test, result in self.results.items():
            status = "✓ PASS" if result else "✗ FAIL"
            print(f"{test.upper():20s} {status}")
        
        print("="*60)
        print(f"Total: {passed}/{total} tests passed")
        print("="*60)
        
        return passed == total


async def main():
    """Run all tests"""
    print("="*60)
    print("RASPBERRY PI SURVEILLANCE CAR - SYSTEM TEST")
    print("="*60)
    
    if not DEPENDENCIES_OK:
        print("\n✗ Missing dependencies. Run: pip install -r requirements.txt")
        return
    
    tester = SystemTester()
    
    # Run tests
    tester.test_mqtt_broker()
    tester.test_video_capture()
    tester.test_audio_capture()
    tester.test_ngrok()
    
    # WebSocket test (requires server running)
    print("\n[INFO] WebSocket test requires server to be running")
    print("[INFO] Start server with: python -m Raspi.Network.WebSockets.main")
    
    try_websocket = input("\nTest WebSocket server? (y/n): ").lower() == 'y'
    
    if try_websocket:
        await tester.test_websocket_server()
    else:
        print("[SKIP] WebSocket server test")
        tester.results['websocket'] = None
    
    # Print summary
    all_passed = tester.print_summary()
    
    if all_passed:
        print("\n✓ All tests passed! System is ready.")
    else:
        print("\n✗ Some tests failed. Check the output above.")


if __name__ == "__main__":
    asyncio.run(main())
