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

### Infrastructure

**Droplets:**
- **clawdbot-1** (143.198.96.99) - Main server, 2GB RAM, this instance (Naruto bot)
- **openclaw-2** (24.199.102.212) - Secondary server, 2GB RAM, viralfarmbot

**Slack Bots:**
- **Naruto** (A0AHMHKE0Q6) - My bot, runs on clawdbot-1
- **viralfarmbot** (A0AJ549031P) - U0AHKS555U3, runs on openclaw-2
- **Clawvicular** (A0AHV51MTQ8) - Publicly distributed app

### ⚠️ Chrome / Browser Process Management

**NEVER run any of these commands:**
- `pkill chrome`, `pkill -f chrome`, `kill` on chrome PIDs
- `killall chrome`, `pkill -9 chrome`
- Any command that kills Chrome processes

**Why:** Chrome is YOUR browser process. Killing it kills your own browser capability and can crash the gateway.

**If memory is high or Chrome seems stuck:**
- Run `/usr/local/bin/cleanup-chrome.sh` — safely kills stale renderer tabs while keeping main browser alive
- Cron runs this every **2 minutes** automatically
- For manual cleanup: `/usr/local/bin/cleanup-chrome.sh`
- If gateway itself needs restarting: `systemctl --user restart clawdbot-gateway.service`

**Memory thresholds (2GB servers):**
- Max renderer age: 5 minutes (vs 10 min on larger servers)
- Max renderers: 3 (vs 8 on larger servers)
- Warning at 60% RAM → clean renderers >2.5min old
- Critical at 70% RAM → kill ALL renderers

**Browser timeout issues:**
- If browser snapshots timeout, the cleanup script should help
- If persistent, restart gateway: `gateway action=restart`
- Check memory: `free -h`
