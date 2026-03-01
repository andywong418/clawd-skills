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

# 6. Install recommended skills (see below)
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
├── MEMORY.md        # Long-term memory (created by agent)
└── memory/
    ├── YYYY-MM-DD.md           # Daily logs
    ├── SESSION-STATE.md        # WAL state
    ├── working-buffer.md       # Context buffer
    └── interoceptive-state.json # Memory health
```

## Skill Sources Summary

| Skill | Purpose | Install |
|-------|---------|---------|
| OpenCortex | Self-improving memory | `clawhub install opencortex` |
| Vigil | Safety guardrails | `npm install vigil-agent-safety` |
| memU | Proactive 24/7 agents | `pip install memu` |
| SIAS | WAL + learning system | `git clone iggyswelt/SIAS` |
