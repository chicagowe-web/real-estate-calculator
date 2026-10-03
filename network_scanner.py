#!/usr/bin/env python3
"""
Network IP change scanner - tracks device IPs and reports changes.
Can scan local ARP and remote via Tailscale for garage infrastructure.
"""

import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime

BASELINE_DIR = Path.home() / ".claude" / "network_scans"
BASELINE_DIR.mkdir(parents=True, exist_ok=True)

KNOWN_DEVICES = {
    "192.168.1.200": {"name": "garage-core", "type": "compute", "description": "RTX 3080 - Diagnostic engine + Ollama + RAG", "network": "garage"},
    "192.168.1.79": {"name": "tp-laptop", "type": "control", "description": "Hermes control plane", "network": "garage"},
    "192.168.1.1": {"name": "gateway", "type": "network", "description": "Network gateway/router", "network": "garage"},
    "100.87.86.4": {"name": "garage-core-tailscale", "type": "compute", "description": "garage-core via Tailscale", "network": "tailscale"},
}

def get_arp_table():
    """Get current ARP table entries for local network."""
    try:
        result = subprocess.run(["arp", "-a"], capture_output=True, text=True, timeout=10)
        devices = {}
        for line in result.stdout.split('\n'):
            if not line.strip() or '?' in line:
                continue
            parts = line.split()
            if len(parts) >= 4 and parts[0]:
                try:
                    ip = parts[1].strip('()')
                    mac = parts[3]
                    if ip.startswith('192.168.'):
                        devices[ip] = {"mac": mac, "hostname": parts[0], "network": "local"}
                except (IndexError, ValueError):
                    pass
        return devices
    except Exception as e:
        print(f"⚠️  ARP scan failed: {e}", file=sys.stderr)
        return {}

def check_device_ping(ip, timeout=2):
    """Check if device responds to ping."""
    try:
        result = subprocess.run(
            ["ping", "-c", "1", "-W", str(timeout)],
            input=ip,
            capture_output=True,
            timeout=timeout+1
        )
        return result.returncode == 0
    except Exception:
        return False

def get_tailscale_peers():
    """Get connected Tailscale peers."""
    try:
        result = subprocess.run(["tailscale", "status", "--json"], capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            return {}

        try:
            data = json.loads(result.stdout)
            devices = {}
            if "Peer" in data:
                for peer_key, peer_info in data["Peer"].items():
                    for addr in peer_info.get("TailscaleIPs", []):
                        if addr.startswith('100.'):
                            devices[addr] = {
                                "hostname": peer_info.get("HostName", "unknown"),
                                "network": "tailscale"
                            }
            return devices
        except json.JSONDecodeError:
            return {}
    except FileNotFoundError:
        return {}
    except Exception as e:
        print(f"⚠️  Tailscale check failed: {e}", file=sys.stderr)
        return {}

def load_baseline():
    """Load last known network state."""
    latest = sorted(BASELINE_DIR.glob("network_scan_*.json"))
    if latest:
        try:
            with open(latest[-1]) as f:
                return json.load(f)
        except Exception as e:
            print(f"Could not load baseline: {e}", file=sys.stderr)
    return None

def save_snapshot(devices):
    """Save current network snapshot."""
    timestamp = datetime.now().isoformat().replace(':', '-').split('.')[0]
    path = BASELINE_DIR / f"network_scan_{timestamp}.json"

    with open(path, 'w') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "devices": devices,
        }, f, indent=2)

    return path

def report_changes(baseline, current):
    """Compare baseline to current and report changes."""
    baseline_ips = set(baseline.get("devices", {}).keys())
    current_ips = set(current.keys())

    new_devices = current_ips - baseline_ips
    offline_devices = baseline_ips - current_ips
    unchanged = baseline_ips & current_ips

    print("\n" + "="*70)
    print("NETWORK SCAN REPORT")
    print("="*70)

    print(f"\n📊 Summary:")
    print(f"   Previous: {len(baseline_ips)} devices | Current: {len(current)} devices")
    print(f"   Status: {len(new_devices)} new, {len(offline_devices)} offline, {len(unchanged)} unchanged")

    print(f"\n✅ Known Devices Online ({len([ip for ip in current_ips if ip in KNOWN_DEVICES])}):")
    for ip in sorted(current_ips):
        if ip in KNOWN_DEVICES:
            info = KNOWN_DEVICES[ip]
            device = current[ip]
            print(f"   {ip:20} | {info['name']:20} | {info['description']}")

    if new_devices:
        print(f"\n🆕 New Devices ({len(new_devices)}):")
        for ip in sorted(new_devices):
            device = current[ip]
            hostname = device.get("hostname", "unknown")
            print(f"   {ip:20} | {hostname:20} | NEW")
    else:
        print(f"\n🆕 New Devices: None")

    if offline_devices:
        print(f"\n⚠️  Offline Devices ({len(offline_devices)}):")
        for ip in sorted(offline_devices):
            if ip in KNOWN_DEVICES:
                info = KNOWN_DEVICES[ip]
                print(f"   {ip:20} | {info['name']:20} (expected)")
            else:
                print(f"   {ip:20} | (previously seen)")
    else:
        print(f"\n⚠️  Offline Devices: None")

    print("="*70 + "\n")

    if new_devices or offline_devices:
        return True
    return False

def main():
    print("🔍 Scanning network...\n")

    devices = {}

    # Get local ARP
    print("  • Scanning local ARP...")
    arp_devices = get_arp_table()
    devices.update(arp_devices)

    # Get Tailscale peers
    print("  • Checking Tailscale peers...")
    ts_devices = get_tailscale_peers()
    devices.update(ts_devices)

    # Check connectivity of known devices
    print("  • Verifying device connectivity...\n")
    for ip in KNOWN_DEVICES:
        if ip not in devices:
            online = check_device_ping(ip)
            if online:
                devices[ip] = {
                    "hostname": KNOWN_DEVICES[ip]["name"],
                    "network": KNOWN_DEVICES[ip]["network"]
                }

    # Load baseline and compare
    baseline = load_baseline()
    path = save_snapshot(devices)
    print(f"📁 Snapshot saved: {path}\n")

    if baseline:
        has_changes = report_changes(baseline, devices)
        if has_changes:
            sys.exit(1)
    else:
        print(f"📊 First scan: {len(devices)} devices found")
        print("   Baseline created. Run again to detect changes.\n")

        print("Devices found:")
        by_network = {}
        for ip in sorted(devices.keys()):
            net = "unknown"
            if ip in KNOWN_DEVICES:
                info = KNOWN_DEVICES[ip]
                net = info["network"]
                print(f"   {ip:20} | {info['name']:20} | {info['description']}")
            else:
                device = devices[ip]
                net = device.get("network", "unknown")
                hostname = device.get("hostname", "?")
                print(f"   {ip:20} | {hostname:20} | (unknown device)")
        print()

if __name__ == "__main__":
    main()
