# Network IP Scan Results — 2026-10-03

## Summary
✓ **Network Status: Stable**
- Total devices discovered: 6
- New devices: 0 (since baseline)
- Offline devices: 0
- Changes detected: No

## Devices Found

### Local Network (192.168.12.x)
| IP | Hostname | MAC | Status |
|---|---|---|---|
| 192.168.12.1 | TMO-G4SE.lan | 64:67:72:62:37:ae | ✅ Online |
| 192.168.12.20 | pop-os.lan | 30:85:a9:96:7e:8e | ✅ Online |
| 192.168.12.90 | **canfd.lan** | 2c:cf:67:83:4d:0c | ✅ Online |

### Tailscale Network (100.x.x.x)
| IP | Hostname | Status | Notes |
|---|---|---|---|
| 100.87.86.4 | **garage-core** | ✅ Online | RTX 3080, Diagnostic Engine |
| 100.67.167.44 | kali | ✅ Online | Security/test instance |
| 100.75.183.56 | localhost | ✅ Online | — |

## Expected vs Found

### Known Garage Infrastructure
| Device | Expected IP | Status |
|---|---|---|
| garage-core (RTX 3080) | 192.168.1.200 (local) / 100.87.86.4 (Tailscale) | ✅ Reachable via Tailscale |
| garage-core laptop | 192.168.1.79 (local) | ⚠️ Not found (expected, may be on different network) |
| canfd (Pi 5) | 192.168.1.? (local garage) | ✅ Found on local network as 192.168.12.90 |

### Network Migration Status
- **Old subnet:** 192.168.0.x (migrated 2026-10-03)
- **New subnet:** 192.168.1.x
- **Current environment:** 192.168.12.x (different network)
- **Tunnels:** Tailscale provides access to garage infrastructure

## Scanner Details

### Scan Tool
- **Location:** `/home/tp/network_scanner.py`
- **Capabilities:**
  - Local ARP table scanning
  - Tailscale peer discovery
  - Ping-based connectivity verification
  - Baseline comparison via JSON snapshots
  - Change detection (new devices, offline devices)

### Snapshot Storage
- **Location:** `~/.claude/network_scans/`
- **Format:** JSON with timestamp, device list
- **Retention:** All scans kept for historical comparison

### Usage
```bash
python3 ~/network_scanner.py
```

Run repeatedly to track IP changes. Script exits with status code 1 if changes detected.

## Findings

### ✅ Confirmed Connectivity
1. **garage-core** accessible via Tailscale (100.87.86.4)
2. **canfd** (Raspberry Pi 5) accessible on local network (192.168.12.90)
3. Network migration to 192.168.1.x appears successful

### ⚠️ Notes
- This environment (job host) is on 192.168.12.x, not garage's 192.168.1.x
- garage-core laptop not found (likely offline or on garage network)
- Kali instance online on Tailscale (may be VM or test device)

## Recommendations

1. **Regular Scans:** Schedule scanner to run periodically (e.g., hourly/daily) to track IP stability
2. **Garage Network Check:** SSH into garage-core to verify 192.168.1.x devices (from garage-core's vantage point)
3. **IP Assignment:** Consider static IPs for critical devices (garage-core, canfd, gateway)

---
Generated: 2026-10-03 15:17:21 UTC
