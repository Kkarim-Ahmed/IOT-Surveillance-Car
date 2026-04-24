"""
network_scanner.py — Print the local machine's IP address and subnet range.

Useful for finding the correct host value to put in server_profiles.json
when running the broker on a local network.

Usage:
    python network_scanner.py
"""

import socket
import subprocess
import platform


def get_local_ip() -> str:
    """Return the primary local IP address of this machine."""
    try:
        # Connect to an external address (no data sent) to discover local IP
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"


def get_ip_range(ip: str) -> str:
    """Return the /24 subnet range for a given IP (e.g. 192.168.1.0/24)."""
    parts = ip.split(".")
    return f"{parts[0]}.{parts[1]}.{parts[2]}.0/24"


def get_hostname() -> str:
    return socket.gethostname()


def scan_summary():
    ip       = get_local_ip()
    ip_range = get_ip_range(ip)
    hostname = get_hostname()

    print("=" * 45)
    print("  Network Scanner — Local Info")
    print("=" * 45)
    print(f"  Hostname   : {hostname}")
    print(f"  Local IP   : {ip}")
    print(f"  Subnet     : {ip_range}")
    print(f"  Platform   : {platform.system()} {platform.release()}")
    print("=" * 45)
    print()
    print("  Use this IP as 'host' in server_profiles.json")
    print(f"  → \"host\": \"{ip}\"")
    print()

    # Optionally ping the broker to check reachability
    broker = "broker.hivemq.com"
    param  = "-n" if platform.system().lower() == "windows" else "-c"
    try:
        result = subprocess.run(
            ["ping", param, "1", broker],
            capture_output=True, timeout=5,
        )
        reachable = result.returncode == 0
    except Exception:
        reachable = False

    status = "✓ reachable" if reachable else "✗ unreachable"
    print(f"  Cloud broker ({broker}): {status}")


if __name__ == "__main__":
    scan_summary()
