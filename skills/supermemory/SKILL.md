---
name: supermemory
description: Persistent AI memory using Supermemory API. Auto-extracts facts, tracks changes over time, and provides per-user/per-bot memory isolation.
---

# Supermemory Integration

Supermemory provides intelligent memory for AI agents:
- **Auto-extraction**: Facts extracted automatically from conversations
- **Temporal awareness**: Tracks when facts change
- **User profiles**: Static facts + dynamic context
- **Isolation**: Per-bot and per-user memory containers

## Quick Usage

### Get Context Before Responding
```bash
# Get your profile + relevant memories
./scripts/get-context.sh "what are we working on?"

# Get context for a specific user
./scripts/get-context.sh "database setup" --user andros
```

### Store Important Information
```bash
# Store a conversation or fact
./scripts/add-memory.sh "User prefers PostgreSQL over MySQL for new projects"

# Store with user tag
./scripts/add-memory.sh "Andros wants memory to be super good" --user andros
```

### View Profile
```bash
# See what supermemory knows about this bot
./scripts/get-profile.sh

# See what it knows about a user
./scripts/get-profile.sh --user andros
```

## Container Tags

Each bot has its own memory space:
- `naruto` - Naruto bot's memories
- `viralfarmbot` - viralfarmbot's memories
- `alphawhalebot` - alphawhalebot's memories

Per-user memories use nested tags:
- `viralfarmbot:user:andros` - viralfarmbot's memory of Andros

## When to Use

**Store memories when:**
- User shares preferences or facts about themselves
- Important decisions are made
- Config/credentials are provided
- Project context is established

**Query context when:**
- Starting a new session
- User asks about past conversations
- You need to recall preferences or decisions

## Integration Pattern

At session start or before important responses:
```bash
# 1. Get context
context=$(./scripts/get-context.sh "$user_message")

# 2. Include in your thinking
# "Based on supermemory: $context"

# 3. After conversation, store important bits
./scripts/add-memory.sh "summary of what happened"
```

## Environment

Requires `SUPERMEMORY_API_KEY` in `~/.clawdbot/.env`
