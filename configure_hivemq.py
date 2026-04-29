#!/usr/bin/env python3
"""
HiveMQ Configuration Helper
Helps configure your laptop to connect to HiveMQ cloud broker
"""

import json
import os
import sys

def get_hivemq_credentials():
    """Get HiveMQ credentials from user"""
    print("🌐 HiveMQ Cloud Configuration")
    print("=" * 50)
    print("Please provide your HiveMQ cluster details:")
    print("(You can find these in your HiveMQ Cloud Console)")
    print()
    
    cluster_url = input("HiveMQ Cluster URL (e.g., abc123def.s1.eu.hivemq.cloud): ").strip()
    username = input("Username: ").strip()
    password = input("Password: ").strip()
    
    if not cluster_url or not username or not password:
        print("❌ All fields are required!")
        return None
    
    # Ensure cluster URL has the correct format
    if not cluster_url.endswith('.hivemq.cloud'):
        cluster_url += '.hivemq.cloud'
    
    return {
        "host": cluster_url,
        "username": username,
        "password": password
    }

def update_client_config(credentials):
    """Update client_config.json with HiveMQ credentials"""
    config_path = "config/client_config.json"
    
    try:
        # Read current config
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Update cloud broker settings
        config["broker"]["cloud"]["host"] = credentials["host"]
        config["broker"]["cloud"]["username"] = credentials["username"]
        config["broker"]["cloud"]["password"] = credentials["password"]
        
        # Set profile to cloud
        config["broker"]["profile"] = "cloud"
        
        # Write updated config
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"✅ Updated {config_path}")
        return True
        
    except Exception as e:
        print(f"❌ Error updating client config: {e}")
        return False

def update_server_profiles(credentials):
    """Update server_profiles.json with HiveMQ credentials"""
    config_path = "config/server_profiles.json"
    
    try:
        # Read current config
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Update cloud profile
        config["cloud"]["host"] = credentials["host"]
        config["cloud"]["username"] = credentials["username"]
        config["cloud"]["password"] = credentials["password"]
        
        # Write updated config
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"✅ Updated {config_path}")
        return True
        
    except Exception as e:
        print(f"❌ Error updating server profiles: {e}")
        return False

def test_hivemq_connection(credentials):
    """Test connection to HiveMQ"""
    print("\n🧪 Testing HiveMQ Connection...")
    
    try:
        import paho.mqtt.client as mqtt
        import ssl
        import time
        
        connected = False
        
        def on_connect(client, userdata, flags, rc):
            nonlocal connected
            if rc == 0:
                print("✅ Connected to HiveMQ successfully!")
                connected = True
                client.publish('test/hivemq', 'Hello from laptop!')
            else:
                print(f"❌ Connection failed with code {rc}")
                if rc == 4:
                    print("   Check your username and password")
                elif rc == 5:
                    print("   Authentication failed")
        
        def on_message(client, userdata, msg):
            print(f"📨 Received: {msg.topic} -> {msg.payload.decode()}")
        
        # Create MQTT client
        client = mqtt.Client()
        client.username_pw_set(credentials["username"], credentials["password"])
        
        # Configure TLS
        client.tls_set(ca_certs=None, certfile=None, keyfile=None, 
                      cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLS,
                      ciphers=None)
        
        client.on_connect = on_connect
        client.on_message = on_message
        
        # Connect to HiveMQ
        client.connect(credentials["host"], 8883, 60)
        client.subscribe('test/hivemq')
        client.loop_start()
        
        # Wait for connection
        timeout = 10
        while not connected and timeout > 0:
            time.sleep(0.1)
            timeout -= 0.1
        
        if connected:
            time.sleep(2)  # Wait for any messages
            print("✅ HiveMQ connection test successful!")
        else:
            print("❌ HiveMQ connection test failed!")
        
        client.loop_stop()
        client.disconnect()
        
        return connected
        
    except ImportError:
        print("❌ paho-mqtt not installed. Run: pip install paho-mqtt")
        return False
    except Exception as e:
        print(f"❌ Connection test error: {e}")
        return False

def create_hivemq_test_script(credentials):
    """Create a test script for HiveMQ"""
    script_content = f'''#!/usr/bin/env python3
"""
HiveMQ Connection Tester
Auto-generated script to test HiveMQ connection
"""

import paho.mqtt.client as mqtt
import ssl
import json
import time

# HiveMQ Configuration
HIVEMQ_HOST = "{credentials["host"]}"
HIVEMQ_PORT = 8883
HIVEMQ_USERNAME = "{credentials["username"]}"
HIVEMQ_PASSWORD = "{credentials["password"]}"

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ Connected to HiveMQ!")
        client.subscribe("dev/status")
        # Send test command
        test_cmd = {{"direction": "forward", "speed": 50}}
        client.publish("dev/motor", json.dumps(test_cmd))
        print("📤 Sent test motor command")
    else:
        print(f"❌ Connection failed: {{rc}}")

def on_message(client, userdata, msg):
    print(f"📨 {{msg.topic}}: {{msg.payload.decode()}}")

def main():
    client = mqtt.Client()
    client.username_pw_set(HIVEMQ_USERNAME, HIVEMQ_PASSWORD)
    
    # Configure TLS
    client.tls_set(ca_certs=None, certfile=None, keyfile=None,
                  cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLS)
    
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        print(f"🌐 Connecting to HiveMQ: {{HIVEMQ_HOST}}")
        client.connect(HIVEMQ_HOST, HIVEMQ_PORT, 60)
        client.loop_forever()
    except KeyboardInterrupt:
        print("\\n👋 Disconnecting...")
        client.disconnect()

if __name__ == "__main__":
    main()
'''
    
    with open("test_hivemq_connection.py", "w") as f:
        f.write(script_content)
    
    print("✅ Created test_hivemq_connection.py")

def main():
    """Main configuration function"""
    print("🚗 MQTT IoT System - HiveMQ Configuration")
    print("=" * 60)
    
    # Check if we're in the right directory
    if not os.path.exists("config"):
        print("❌ Config directory not found!")
        print("Please run this script from the Development directory")
        return
    
    # Get HiveMQ credentials
    credentials = get_hivemq_credentials()
    if not credentials:
        return
    
    print(f"\n📝 Configuration Summary:")
    print(f"   Host: {credentials['host']}")
    print(f"   Username: {credentials['username']}")
    print(f"   Password: {'*' * len(credentials['password'])}")
    
    confirm = input("\nProceed with configuration? (y/N): ").strip().lower()
    if confirm != 'y':
        print("❌ Configuration cancelled")
        return
    
    # Update configuration files
    print(f"\n🔧 Updating configuration files...")
    
    success = True
    success &= update_client_config(credentials)
    success &= update_server_profiles(credentials)
    
    if not success:
        print("❌ Configuration update failed!")
        return
    
    # Test connection
    if test_hivemq_connection(credentials):
        print("\n🎉 HiveMQ configuration successful!")
        
        # Create test script
        create_hivemq_test_script(credentials)
        
        print(f"\n📋 Next Steps:")
        print(f"1. Make sure your Pi is also configured with the same HiveMQ credentials")
        print(f"2. Start your Pi device controller")
        print(f"3. Test the connection:")
        print(f"   python3 test_hivemq_connection.py")
        print(f"4. Use the GUI with cloud mode:")
        print(f"   python3 mqtt_gui_controller.py")
        print(f"5. Run comprehensive tests:")
        print(f"   python3 test_hivemq_system.py")
        
    else:
        print("\n❌ HiveMQ connection test failed!")
        print("Please check your credentials and try again")

if __name__ == "__main__":
    main()