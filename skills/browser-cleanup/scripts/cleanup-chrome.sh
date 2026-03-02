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
