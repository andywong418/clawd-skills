---
name: browser-cleanup
description: Manage Chrome browser memory on low-RAM servers. Use when browser snapshots timeout, memory is high, or Chrome processes accumulate. Includes cleanup script and cron setup.
---

# Browser Memory Cleanup

Manage Chrome/browser memory usage on Clawdbot servers, especially important for 2GB RAM droplets.

## The Problem

Clawdbot uses headless Chrome for browser automation. Chrome renderer processes accumulate over time and can exhaust memory, causing:
- Browser snapshot timeouts
- Gateway crashes (OOM)
- Slow response times

## Quick Fix

If browser is unresponsive:
```bash
/usr/local/bin/cleanup-chrome.sh
```

If that doesn't help, restart the gateway:
```bash
gateway action=restart
# or
systemctl --user restart clawdbot-gateway.service
```

## ⚠️ NEVER Do This

**Do NOT kill Chrome directly:**
```bash
# WRONG - will crash your browser capability
pkill chrome
pkill -f chrome
killall chrome
kill <chrome-pid>
```

The cleanup script safely kills only **renderer** processes while keeping the main browser alive.

## Install Cleanup Script

```bash
cat > /usr/local/bin/cleanup-chrome.sh << 'EOF'
#!/bin/bash
# Browser memory cleanup for low-memory servers (2GB)
# Keeps the main browser process alive while cleaning up stale tabs/renderers

LOG_TAG="cleanup-chrome"
log() { logger -t "$LOG_TAG" "$1"; }

GATEWAY_PID=$(pgrep -f "clawdbot-gateway" | head -1)

if [ -z "$GATEWAY_PID" ]; then
    pkill -9 chrome 2>/dev/null
    exit 0
fi

# Get memory stats
MEM_TOTAL=$(free -m | awk '/Mem:/ {print $2}')
MEM_USED=$(free -m | awk '/Mem:/ {print $3}')
MEM_USED_PCT=$((MEM_USED * 100 / MEM_TOTAL))
SWAP_USED=$(free -m | awk '/Swap:/ {print $3}')

RENDERER_COUNT=$(pgrep -c -f "chrome --type=renderer" 2>/dev/null || echo 0)

# Thresholds based on available memory
if [ "$MEM_TOTAL" -lt 2500 ]; then
    MAX_AGE_SECONDS=300      # 5 minutes
    MEMORY_WARN_PCT=60
    MEMORY_CRIT_PCT=70
    MAX_RENDERERS=3
else
    MAX_AGE_SECONDS=600      # 10 minutes
    MEMORY_WARN_PCT=70
    MEMORY_CRIT_PCT=80
    MAX_RENDERERS=8
fi

# Kill old renderer processes
killed_old=0
for pid in $(pgrep -f "chrome --type=renderer"); do
    age_seconds=$(ps -o etimes= -p $pid 2>/dev/null | tr -d " ")
    if [ -n "$age_seconds" ] && [ "$age_seconds" -gt "$MAX_AGE_SECONDS" ]; then
        kill -9 $pid 2>/dev/null && ((killed_old++))
    fi
done
[ $killed_old -gt 0 ] && log "killed $killed_old old renderer(s)"

# If too many renderers, kill oldest ones
if [ "$RENDERER_COUNT" -gt "$MAX_RENDERERS" ]; then
    excess=$((RENDERER_COUNT - MAX_RENDERERS))
    pgrep -f "chrome --type=renderer" | while read pid; do
        ps -o etimes=,pid= -p $pid 2>/dev/null
    done | sort -rn | head -$excess | awk '{print $2}' | while read pid; do
        kill -9 $pid 2>/dev/null
    done
    log "killed $excess excess renderer(s)"
fi

# Critical memory: kill ALL Chrome renderers
if [ "$MEM_USED_PCT" -gt "$MEMORY_CRIT_PCT" ]; then
    pkill -9 -f "chrome --type=renderer" 2>/dev/null
    pkill -9 -f "chrome --type=utility.*network" 2>/dev/null
    log "CRITICAL: memory at ${MEM_USED_PCT}%, killed Chrome renderers"
fi

# Warning level: kill idle renderers
if [ "$MEM_USED_PCT" -gt "$MEMORY_WARN_PCT" ]; then
    half_age=$((MAX_AGE_SECONDS / 2))
    for pid in $(pgrep -f "chrome --type=renderer"); do
        age_seconds=$(ps -o etimes= -p $pid 2>/dev/null | tr -d " ")
        if [ -n "$age_seconds" ] && [ "$age_seconds" -gt "$half_age" ]; then
            kill -9 $pid 2>/dev/null
        fi
    done
    log "WARNING: memory at ${MEM_USED_PCT}%, cleaned old renderers"
fi

# Clean up zombie Chrome processes
for pid in $(ps aux | awk '/chrome/ && $8 ~ /Z/ {print $2}'); do
    kill -9 $pid 2>/dev/null
done
EOF

chmod +x /usr/local/bin/cleanup-chrome.sh
```

## Setup Cron Job

For 2GB servers, run every 2 minutes:
```bash
(crontab -l 2>/dev/null | grep -v cleanup-chrome; echo "*/2 * * * * /usr/local/bin/cleanup-chrome.sh") | crontab -
```

For larger servers (4GB+), every 5 minutes is fine:
```bash
(crontab -l 2>/dev/null | grep -v cleanup-chrome; echo "*/5 * * * * /usr/local/bin/cleanup-chrome.sh") | crontab -
```

Verify:
```bash
crontab -l | grep chrome
```

## Memory Thresholds

| Server RAM | Max Renderer Age | Max Renderers | Warning % | Critical % |
|------------|------------------|---------------|-----------|------------|
| < 2.5GB    | 5 minutes        | 3             | 60%       | 70%        |
| ≥ 2.5GB    | 10 minutes       | 8             | 70%       | 80%        |

## Monitoring

Check current memory:
```bash
free -h
```

Check Chrome processes:
```bash
pgrep -c -f "chrome --type=renderer"
ps aux | grep chrome | grep -v grep
```

Check cleanup logs:
```bash
journalctl -t cleanup-chrome --since "1 hour ago"
# or
grep cleanup-chrome /var/log/syslog | tail -20
```

## Troubleshooting

### Browser snapshots timing out
1. Run cleanup: `/usr/local/bin/cleanup-chrome.sh`
2. Check memory: `free -h`
3. If still failing, restart gateway: `gateway action=restart`

### Gateway keeps crashing with OOM
1. Add swap if not present:
   ```bash
   fallocate -l 2G /swapfile
   chmod 600 /swapfile
   mkswap /swapfile
   swapon /swapfile
   echo '/swapfile none swap sw 0 0' >> /etc/fstab
   ```
2. Consider upgrading to more RAM (2GB minimum recommended)

### High swap usage
If swap > 500MB consistently, gateway may need restart to reclaim memory:
```bash
gateway action=restart
```

## Server Sizing

**Minimum for Clawdbot with browser:** 2GB RAM + 2GB swap

| RAM   | Browser Use | Notes |
|-------|-------------|-------|
| 1GB   | ❌ Not enough | OOM during npm install and operation |
| 2GB   | ✅ Works | Needs aggressive cleanup, swap recommended |
| 4GB+  | ✅ Comfortable | Relaxed cleanup settings |
