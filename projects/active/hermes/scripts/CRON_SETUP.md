# 🕐 Hermes Automated Sync Cron Setup

**Purpose:** Keep remote Hermes deployments (garage-core, future Pi 5 nodes) in sync with main repo automatically

**Timing:** Daily at 2 AM (configurable)

---

## Quick Setup (3 steps)

### Step 1: Verify sync script exists

```bash
ssh garage-core
ls -la ~/hermes/scripts/sync-from-main.sh
# Should show: -rwxrwxr-x (executable)
```

### Step 2: Add cron job

```bash
ssh garage-core
crontab -e

# Add this line to the editor that opens:
0 2 * * * /home/garage_core/hermes/scripts/sync-from-main.sh >> /var/log/hermes-sync.log 2>&1
```

### Step 3: Verify it's installed

```bash
crontab -l
# Should show the line you just added
```

---

## Understanding the Cron Entry

```
0 2 * * * /home/garage_core/hermes/scripts/sync-from-main.sh >> /var/log/hermes-sync.log 2>&1
│ │ │ │ │
│ │ │ │ └─ Day of week (0-6, 0=Sunday) — * means every day
│ │ │ └─── Month (1-12) — * means every month
│ │ └───── Day of month (1-31) — * means every day
│ └─────── Hour (0-23) — 2 means 2 AM
└───────── Minute (0-59) — 0 means start of hour
```

**What happens at 2 AM daily:**
1. Sync script runs
2. Fetches latest code from origin/master
3. Updates if changes detected
4. Restarts Hermes services
5. Logs all output to `/var/log/hermes-sync.log`

---

## Monitoring & Troubleshooting

### Check if cron job ran

```bash
tail -f /var/log/hermes-sync.log

# Should see entries like:
# [2026-09-28 02:00:01] === Starting Hermes code sync ===
# [2026-09-28 02:00:02] [INFO] Repository: /home/garage_core/hermes
# [2026-09-28 02:00:05] [SUCCESS] Fetch completed
# [2026-09-28 02:00:15] [SUCCESS] Code updated to latest version
# [2026-09-28 02:00:20] [SUCCESS] hermes-api restarted
```

### Check cron daemon is running

```bash
ps aux | grep crond
# Should show: /usr/sbin/cron (or similar)

# If not running:
sudo systemctl start cron
sudo systemctl enable cron  # Auto-start on reboot
```

### Test the sync script manually

```bash
cd ~/hermes
./scripts/sync-from-main.sh

# Should complete successfully and show:
# [SUCCESS] Hermes code is now up to date
```

### Change sync time

```bash
crontab -e

# To change from 2 AM to 3 AM:
0 3 * * * /home/garage_core/hermes/scripts/sync-from-main.sh >> /var/log/hermes-sync.log 2>&1

# Other common times:
# 0 0 * * * = midnight
# 0 6 * * * = 6 AM
# 0 22 * * * = 10 PM
```

### Disable syncing (temporarily)

```bash
crontab -e
# Comment out the line:
# 0 2 * * * /home/garage_core/hermes/scripts/sync-from-main.sh >> /var/log/hermes-sync.log 2>&1
```

### Disable service restart (only sync code, don't restart)

```bash
# Edit cron line to:
RESTART_SERVICES=false 0 2 * * * /home/garage_core/hermes/scripts/sync-from-main.sh >> /var/log/hermes-sync.log 2>&1
```

---

## Environment Variables

The sync script respects these environment variables:

| Variable | Default | Purpose |
|----------|---------|---------|
| `HERMES_DIR` | `.` (current dir) | Path to Hermes repository |
| `REPO_BRANCH` | `master` | Branch to sync from |
| `LOG_FILE` | `/var/log/hermes-sync.log` | Where to log output |
| `RESTART_SERVICES` | `true` | Whether to restart services after update |

### Example: Use custom location

```bash
# In crontab:
0 2 * * * HERMES_DIR=/opt/hermes /opt/hermes/scripts/sync-from-main.sh >> /var/log/hermes-sync.log 2>&1
```

---

## Common Issues

### "Permission denied" when running script

**Cause:** Script is not executable  
**Fix:**
```bash
chmod +x ~/hermes/scripts/sync-from-main.sh
```

### Cron job doesn't run

**Cause:** Cron daemon not running or job not installed  
**Fix:**
```bash
# Check if cron is running
systemctl status cron

# If not, start it:
sudo systemctl start cron
sudo systemctl enable cron
```

### Service restart fails

**Symptom:** Log shows "Failed to restart hermes-api"  
**Cause:** Service doesn't exist or permissions issue  
**Fix:**
```bash
# Check if service exists:
systemctl list-units --type=service | grep hermes

# If not, create it or disable auto-restart:
RESTART_SERVICES=false crontab -e
```

### Log file grows too large

**Symptom:** `/var/log/hermes-sync.log` becomes huge  
**Fix:**
```bash
# Add logrotate rule
sudo bash -c 'cat > /etc/logrotate.d/hermes << EOF
/var/log/hermes-sync.log {
    weekly
    rotate 4
    compress
    delaycompress
    notifempty
    create 0644 garage_core garage_core
}
EOF'

# Test it:
sudo logrotate -f /etc/logrotate.d/hermes
```

---

## What Gets Synced

The sync script updates:
- ✅ All Python source code (`hermes/` package)
- ✅ Tests (`tests/`)
- ✅ Documentation (`docs/`)
- ✅ Deployment scripts (`scripts/`)
- ✅ Configuration files (`pyproject.toml`, `Dockerfile`, etc.)

The sync script does **NOT** touch:
- ❌ `~/.hermes_data/` (isolated data directory)
- ❌ `api_venv/` (Python environment)
- ❌ Local configuration files outside `.hermes_data/`

---

## Multi-Machine Sync

To add more machines (e.g., Pi 5 nodes), repeat the setup on each:

```bash
ssh pi5-node-1
cd ~
git clone <your-repo-url> hermes
mkdir -p ~/.hermes_data

# Configure ~/.hermes_data/config.json for this machine's Ollama

# Add same cron job
crontab -e
# 0 2 * * * /home/pi5_user/hermes/scripts/sync-from-main.sh >> /var/log/hermes-sync.log 2>&1
```

Each machine:
- Has its own git clone
- Syncs independently at 2 AM
- Has isolated `~/.hermes_data/`
- Can fail independently without affecting others

---

## Reference

**Script location:** `projects/active/hermes/scripts/sync-from-main.sh`  
**Log location:** `/var/log/hermes-sync.log`  
**Typical setup time:** 5 minutes per machine  
**Maintenance:** Zero — it runs automatically

For full Hermes deployment documentation, see [.hermes_setup.md](.hermes_setup.md)
