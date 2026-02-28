# TOOLS.md - Local Notes

Skills define *how* tools work. This file is for *your* specifics — the stuff that's unique to your setup.

## What Goes Here

Things like:
- Camera names and locations
- SSH hosts and aliases  
- Preferred voices for TTS
- Speaker/room names
- Device nicknames
- Anything environment-specific

## Examples

```markdown
### Cameras
- living-room → Main area, 180° wide angle
- front-door → Entrance, motion-triggered

### SSH
- home-server → 192.168.1.100, user: admin

### TTS
- Preferred voice: "Nova" (warm, slightly British)
- Default speaker: Kitchen HomePod
```

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your notes, and share skills without leaking your infrastructure.

---

Add whatever helps you do your job. This is your cheat sheet.

### ⚠️ Chrome / Browser Process Management

**NEVER run any of these commands:**
- `pkill chrome`, `pkill -f chrome`, `kill` on chrome PIDs
- `killall chrome`, `pkill -9 chrome`
- Any command that kills Chrome processes

**Why:** Chrome is YOUR browser process. Killing it kills your own browser capability and can crash the gateway.

**If memory is high or Chrome seems stuck:**
- Run `/usr/local/bin/cleanup-chrome.sh` — this safely kills only stale renderer tabs (>10 min old) while keeping the main browser alive
- A cron job already runs this every 5 minutes automatically
- If the gateway itself needs restarting: `systemctl --user restart clawdbot-gateway.service`

**Memory budget:** This server has 2GB RAM + 2GB swap. Chrome renderers are the main memory consumer. The cleanup script handles it.
