---
name: clawdbot-setup
description: Create and configure new Clawdbot instances with best-practice workspace templates. Use when spinning up a new bot on a server, creating a fresh workspace, or onboarding a new agent.
---

# Clawdbot Setup

Create new Clawdbot instances with optimized workspace templates including:
- **Auto-Boot Sequence** (loads context/credentials/supermemory on gateway start)
- **Session Memory Hook** (saves context when running /new)
- WAL Protocol (Write-Ahead Logging for memory persistence)
- Working Buffer Protocol (context recovery after compaction)
- Interoceptive State tracking (memory health awareness)
- The Covenant (cross-session responsibility)

## Quick Start

### On a New Server

```bash
# 1. Install Node.js (if needed)
curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
apt-get install -y nodejs

# 2. Install Clawdbot
npm install -g clawdbot

# 3. Create workspace
mkdir -p ~/clawd && cd ~/clawd

# 4. Copy templates
# (from this skill's templates/ folder)

# 5. Initialize
clawdbot init

# 6. Create MEMORY.md (IMPORTANT - don't skip!)
# See "Critical: Memory Setup" section below

# 7. Install recommended skills (see below)
```

## Template Files

Copy these to the new workspace:
- `templates/SOUL.md` — Core identity and values
- `templates/AGENTS.md` — Workspace protocols and memory management
- `templates/BOOTSTRAP.md` — First-run onboarding flow
- `templates/USER.md` — Placeholder for human's info
- `templates/TOOLS.md` — Local tool configuration
- `templates/IDENTITY.md` — Agent identity
- `templates/HEARTBEAT.md` — Heartbeat tasks

## Recommended Skills

Install these after setting up workspace:

### 🧠 OpenCortex (Self-Improving Memory)
Full memory architecture with nightly distillation, weekly synthesis, encrypted vault.
```bash
clawhub install opencortex
bash skills/opencortex/scripts/install.sh
```
Source: https://github.com/JD2005L/opencortex

### 🛡️ Vigil (Safety Guardrails)
<2ms safety checks for destructive commands, exfiltration, SSRF, injection.
```bash
npm install vigil-agent-safety
# Or via ClawHub:
npx clawhub install vigil
```
Source: https://github.com/hexitlabs/vigil

### 🤖 memU (Proactive Memory Framework)
Memory framework for 24/7 proactive agents. Intention capture, memory-as-filesystem.
```bash
pip install memu
# Or clone:
git clone https://github.com/NevaMind-AI/memU.git
```
Source: https://github.com/NevaMind-AI/memU (11.9k ⭐)

### Alternative: SIAS (Self-Improving Agent System)
German/English WAL protocol implementation with .learnings/ folder and promotion system.
```bash
git clone https://github.com/iggyswelt/SIAS.git
cp SIAS/templates/SOUL.md ~/clawd/
```
Source: https://github.com/iggyswelt/SIAS

## Skills Distribution

Bots pull skills from the ViralFarm API (private distribution). No git repos needed.

### Setup on New Bot

```bash
# 1. Set env vars (add to ~/.clawdbot/.env)
echo "VIRALFARM_API_URL=https://your-api-url" >> ~/.clawdbot/.env
echo "VIRALFARM_API_KEY=vf_your_key_here" >> ~/.clawdbot/.env

# 2. Copy update script
cp scripts/update-skills.sh ~/clawd/scripts/update-skills.sh
chmod +x ~/clawd/scripts/update-skills.sh

# 3. Pull initial skills
cd ~/clawd && bash scripts/update-skills.sh

# 4. Add to HEARTBEAT.md for auto-updates
cat >> ~/clawd/HEARTBEAT.md << 'EOF'

## Update Skills
Pull latest skills from ViralFarm API. Runs on each heartbeat cycle.
```bash
bash scripts/update-skills.sh
```
EOF
```

Skills are tier-gated: free workspaces get free skills, pro workspaces get everything.
The heartbeat cron (every 30 min) runs HEARTBEAT.md which triggers `update-skills.sh`.

## Key Protocols Included

### ⚡ WAL Protocol (Write-Ahead Log)
Prevents data loss during context compaction:
- Scan every message for corrections, proper nouns, decisions, values
- Write to `memory/SESSION-STATE.md` BEFORE responding
- "The urge to respond is the enemy. Write first."

### 🛡️ Working Buffer Protocol
Maintains context across compaction events:
- At 60% context, maintain `memory/working-buffer.md`
- Append human message + response summary after each turn
- Read buffer first after compaction

### 🧠 Interoceptive State
Track memory health in `memory/interoceptive-state.json`:
```json
{
  "lastConsolidation": "2024-01-15T10:00:00Z",
  "stalenessHours": 12,
  "activeTopics": ["project-x", "calendar"]
}
```

## Full Setup Script

For automated setup on a fresh server:

```bash
#!/bin/bash
# clawdbot-full-setup.sh

set -e

# Install Node.js
curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
apt-get install -y nodejs

# Install Clawdbot
npm install -g clawdbot

# Create workspace
mkdir -p ~/clawd && cd ~/clawd

# Initialize (will prompt for API keys)
clawdbot init

# Install skills
clawhub install opencortex
bash skills/opencortex/scripts/install.sh

npm install vigil-agent-safety

echo "Setup complete! Configure channels with: clawdbot configure"
```

## Remote Setup

To set up Clawdbot on a remote server:

```bash
# SSH to server
ssh root@<server-ip>

# Run setup
curl -fsSL https://raw.githubusercontent.com/.../setup.sh | bash

# Or manual:
# 1. Copy templates via SCP
scp -r /root/clawd/skills/clawdbot-setup/templates/* root@<server-ip>:~/clawd/

# 2. SSH and install skills
ssh root@<server-ip> "cd ~/clawd && clawhub install opencortex && bash skills/opencortex/scripts/install.sh"
```

## Configuration

After copying templates, configure:

1. **API Keys**: `clawdbot config` to set Anthropic/OpenAI keys
2. **Channels**: Set up Slack/Telegram/Discord as needed
3. **Identity**: Have the agent complete BOOTSTRAP.md on first run

## Files Created

```
~/clawd/
├── SOUL.md          # Identity and values
├── AGENTS.md        # Workspace protocols
├── BOOTSTRAP.md     # First-run flow (deleted after)
├── USER.md          # Human's info
├── TOOLS.md         # Tool configuration
├── IDENTITY.md      # Agent identity
├── HEARTBEAT.md     # Heartbeat tasks
├── MEMORY.md        # Long-term memory (MUST CREATE - see below)
└── memory/
    ├── YYYY-MM-DD.md           # Daily logs
    ├── SESSION-STATE.md        # WAL state
    ├── working-buffer.md       # Context buffer
    └── interoceptive-state.json # Memory health
```

## ⚠️ Critical: Memory Setup

**Don't skip this!** Bots without proper memory setup will be forgetful.

### 1. Create MEMORY.md with Initial Content

```bash
cat > ~/clawd/MEMORY.md << 'EOF'
# [Bot Name] Memory

## Identity
- **Name:** [Bot name]
- **Purpose:** [What this bot does]
- **Workspace:** /root/clawd
- **Server:** [hostname] ([IP])

## Key Context
- [Primary task/purpose]
- [Important files/locations]
- [Key integrations]

## Lessons Learned
- Always write important context to memory files - mental notes dont survive compaction
- [Add lessons as you learn them]

## Current Projects
- [Active work]

---
*Update this file with lessons, decisions, and context worth remembering.*
EOF
```

### 2. Create memory/ Directory Structure

```bash
mkdir -p ~/clawd/memory

# Create initial daily log
cat > ~/clawd/memory/$(date +%Y-%m-%d).md << 'EOF'
# Daily Log - $(date +%Y-%m-%d)

## Setup
- Bot initialized
- Memory structure created

## Notes
EOF

# Create interoceptive state
cat > ~/clawd/memory/interoceptive-state.json << 'EOF'
{
  "lastConsolidation": null,
  "stalenessHours": 0,
  "activeTopics": []
}
EOF
```

### 3. Enable Memory Search (Optional but Recommended)

Memory semantic search requires an OpenAI or Google API key:

```bash
# Add to .env
echo 'OPENAI_API_KEY=sk-...' >> ~/.clawdbot/.env

# Or for Google:
echo 'GOOGLE_API_KEY=...' >> ~/.clawdbot/.env
```

Without this, `memory_search` tool won't work and the bot can only read memory files directly.

### 4. Slack Thread Context (If Using Slack)

Add these to your Slack channel config to prevent thread amnesia:

```json
{
  "channels": {
    "slack": {
      "thread": {
        "inheritParent": true
      },
      "historyLimit": 50
    }
  }
}
```

- `inheritParent: true` - Thread sessions inherit parent channel context
- `historyLimit: 50` - Fetch last 50 messages into context

**Both are required** - `inheritParent` alone won't fetch thread messages!

## ⚠️ Deployment Gotchas (Critical!)

These issues caused significant debugging time. Don't repeat them.

### 1. Enable User Session Lingering (REQUIRED)

Without this, the gateway dies when SSH sessions change:

```bash
loginctl enable-linger root
```

**Symptom:** Gateway keeps getting SIGTERM every 10-30 seconds, constant restarts.
**Cause:** Each SSH connection creates a new user systemd session that takes over.

### 2. API Key Location Hierarchy

Clawdbot checks multiple locations. They can conflict:

1. **Environment variable** (highest priority): `ANTHROPIC_API_KEY` in systemd service
2. **config.yaml**: `provider.anthropic.apiKey` (DEPRECATED - avoid!)
3. **auth-profiles.json**: `~/.clawdbot/agents/main/agent/auth-profiles.json`
4. **.env file**: `~/.clawdbot/.env`

**Common mistake:** Old `config.yaml` with wrong key gets read, or systemd service has stale key in Environment directive.

**Fix:** Check ALL locations and ensure consistency:
```bash
# Check systemd service for hardcoded key
cat ~/.config/systemd/user/clawdbot-gateway.service | grep ANTHROPIC

# Remove old config.yaml if present
rm ~/.clawdbot/config.yaml 2>/dev/null

# Create proper auth-profiles.json
mkdir -p ~/.clawdbot/agents/main/agent
cat > ~/.clawdbot/agents/main/agent/auth-profiles.json << EOF
{
  "profiles": {
    "anthropic:default": {
      "apiKey": "YOUR_KEY_HERE"
    }
  }
}
EOF
```

### 3. Slack Setup Checklist

**Required for DMs:**
- ✅ Socket Mode enabled
- ✅ App Token (xapp-...) with `connections:write` scope
- ✅ Bot Token (xoxb-...)
- ✅ Event Subscription: `message.im`
- ✅ App Home > Messages Tab > "Allow users to send messages" checked

**Required for @mentions in channels:**
- ✅ Event Subscription: `app_mention`
- ✅ OAuth scope: `app_mentions:read`

**After changing scopes, you MUST reinstall the app:**
```
https://slack.com/oauth/v2/authorize?client_id=YOUR_CLIENT_ID&team=YOUR_TEAM_ID&install_redirect=general&scope=im:write,im:read,im:history,app_mentions:read,chat:write
```

### 4. GitHub Deploy Keys

**GitHub doesn't allow the same deploy key on multiple repos.**

Generate a unique key per repo:
```bash
ssh-keygen -t ed25519 -f ~/.ssh/REPO_NAME -N '' -C 'clawdbot-REPO_NAME'

# Add to SSH config
cat >> ~/.ssh/config << EOF
Host github.com
  HostName github.com
  User git
  IdentityFile ~/.ssh/REPO_NAME
  IdentitiesOnly yes
EOF
```

### 5. Test API Key Before Deploying

Always verify the key works:
```bash
curl -s https://api.anthropic.com/v1/messages \
  -H "x-api-key: YOUR_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{"model":"claude-sonnet-4-20250514","max_tokens":5,"messages":[{"role":"user","content":"hi"}]}'
```

### 6. Gateway Service Won't Start

Check in order:
1. `journalctl --user -u clawdbot-gateway.service -n 50`
2. `cat /tmp/clawdbot/clawdbot-$(date +%Y-%m-%d).log | tail -50`
3. `clawdbot doctor --fix`

Common fixes:
```bash
# Missing gateway mode
# Add to ~/.clawdbot/clawdbot.json:
# "gateway": { "mode": "local" }

# Run doctor to auto-fix
clawdbot doctor --fix
```

### 7. Browser Memory Cleanup (For 2GB Servers)

Install the cleanup script and cron job:
```bash
# Copy cleanup script
scp /root/clawd/skills/browser-cleanup/scripts/cleanup-chrome.sh root@SERVER:/usr/local/bin/
ssh root@SERVER "chmod +x /usr/local/bin/cleanup-chrome.sh"

# Add cron (every 2 minutes for 2GB servers)
ssh root@SERVER "(crontab -l 2>/dev/null | grep -v cleanup-chrome; echo '*/2 * * * * /usr/local/bin/cleanup-chrome.sh') | crontab -"
```

**Agent instructions** — Add to TOOLS.md on the new server:
```markdown
### Browser Timeout Recovery
If browser snapshot times out:
1. Run: `/usr/local/bin/cleanup-chrome.sh`
2. Wait 3 seconds, retry (up to 2 times)
3. If still failing: `gateway action=restart`
Never use pkill/kill on chrome directly.
```

## Complete Remote Deployment Script

Based on lessons learned, here's a bulletproof deployment:

```bash
#!/bin/bash
# deploy-clawdbot.sh <server-ip> <anthropic-key>
set -e

SERVER=$1
API_KEY=$2

if [ -z "$SERVER" ] || [ -z "$API_KEY" ]; then
  echo "Usage: $0 <server-ip> <anthropic-api-key>"
  exit 1
fi

ssh root@$SERVER << ENDSSH
set -e

# Install Node.js if needed
if ! command -v node &> /dev/null; then
  curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
  apt-get install -y nodejs
fi

# Install Clawdbot
npm install -g clawdbot

# Create workspace
mkdir -p ~/clawd/memory

# Enable lingering (CRITICAL!)
loginctl enable-linger root

# Setup API key in auth-profiles
mkdir -p ~/.clawdbot/agents/main/agent
cat > ~/.clawdbot/agents/main/agent/auth-profiles.json << EOF
{
  "profiles": {
    "anthropic:default": {
      "apiKey": "$API_KEY"
    }
  }
}
EOF

# Also set in .env as backup
echo "ANTHROPIC_API_KEY=$API_KEY" > ~/.clawdbot/.env

# Run initial setup
cd ~/clawd
clawdbot doctor --fix

# Install and start gateway
clawdbot gateway install
systemctl --user enable clawdbot-gateway.service
systemctl --user start clawdbot-gateway.service

# Verify
sleep 5
systemctl --user status clawdbot-gateway.service | head -10

echo "✅ Deployment complete!"
ENDSSH
```

## Troubleshooting Quick Reference

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| HTTP 401 invalid x-api-key | Wrong API key in config | Check all key locations (see #2 above) |
| Gateway restarts every 10-30s | Missing lingering | `loginctl enable-linger root` |
| Bot doesn't respond to @mentions | Missing app_mention event | Add in Slack Event Subscriptions |
| Bot can't DM | Messages Tab disabled | Enable in App Home settings |
| "No credentials found" | Missing auth-profiles.json | Create at correct path |
| Deploy key in use | GitHub key reuse | Generate unique key per repo |

## Skill Sources Summary

| Skill | Purpose | Install |
|-------|---------|---------|
| OpenCortex | Self-improving memory | `clawhub install opencortex` |
| Vigil | Safety guardrails | `npm install vigil-agent-safety` |
| memU | Proactive 24/7 agents | `pip install memu` |
| SIAS | WAL + learning system | `git clone iggyswelt/SIAS` |
