---
name: clawdbot-setup
description: Create and configure new Clawdbot instances with best-practice workspace templates. Use when spinning up a new bot on a server, creating a fresh workspace, or onboarding a new agent.
---

# Clawdbot Setup

Create new Clawdbot instances with optimized workspace templates including:
- WAL Protocol (Write-Ahead Logging for memory persistence)
- Working Buffer Protocol (context recovery after compaction)
- Interoceptive State tracking (memory health awareness)
- The Covenant (cross-session responsibility)

## Quick Start

### On a New Server

```bash
# 1. Install Clawdbot
npm install -g clawdbot

# 2. Create workspace
mkdir -p ~/clawd && cd ~/clawd

# 3. Copy templates from this skill
cp /path/to/skills/clawdbot-setup/templates/* ~/clawd/

# 4. Initialize
clawdbot init
```

### Template Files

Copy these to the new workspace:
- `templates/SOUL.md` — Core identity and values
- `templates/AGENTS.md` — Workspace protocols and memory management
- `templates/BOOTSTRAP.md` — First-run onboarding flow
- `templates/USER.md` — Placeholder for human's info
- `templates/TOOLS.md` — Local tool configuration

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

## Recommended Skills to Install

After setting up workspace, install these skills:

```bash
# Self-improvement capabilities
clawhub install self-improving-agent

# Enhanced proactive behavior
clawhub install proactive-agent

# Agent safety guardrails
clawhub install vigil
```

## Remote Setup

To set up Clawdbot on a remote server:

```bash
# SSH to server
ssh root@<server-ip>

# Install Node.js if needed
curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
apt-get install -y nodejs

# Install Clawdbot
npm install -g clawdbot

# Create and enter workspace
mkdir -p ~/clawd && cd ~/clawd

# Copy templates (from local machine)
scp /root/clawd/skills/clawdbot-setup/templates/* root@<server-ip>:~/clawd/

# Initialize and configure
clawdbot init
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
├── MEMORY.md        # Long-term memory (created by agent)
└── memory/
    ├── YYYY-MM-DD.md           # Daily logs
    ├── SESSION-STATE.md        # WAL state
    ├── working-buffer.md       # Context buffer
    └── interoceptive-state.json # Memory health
```
