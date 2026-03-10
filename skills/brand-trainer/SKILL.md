---
name: brand-trainer
description: Train and manage brand voice settings for content generation. Set tone, vocabulary, audience, product info, and per-format rules. Stores structured config via the ViralFarm API and fuzzy style memories locally. Use when asked to set brand voice, train brand style, update tone, or configure how content should sound.
metadata: {"clawdbot":{"emoji":"🎨","requires":{"env":["VIRALFARM_API_URL","VIRALFARM_API_KEY"]}}}
---

# Brand Trainer

Train brand voice and format-specific content rules. Two-layer system:

1. **Structured config** (API) — tone, vocabulary, audience, product info, per-format rules
2. **Style memory** (local) — fuzzy preferences learned from conversation ("more casual", "never use emojis")

## Quick Start

```bash
# View current brand voice config
python3 skills/brand-trainer/scripts/brand.py show

# Set brand voice fields
python3 skills/brand-trainer/scripts/brand.py set \
  --name "ViralFarm" \
  --tone "witty, Gen-Z, slightly unhinged" \
  --audience "18-30 social media creators" \
  --description "AI-powered content creation platform" \
  --product-info "Video editing, caption writing, meme generation"

# Add vocabulary / avoid words
python3 skills/brand-trainer/scripts/brand.py vocabulary --add "fire,bussin,no cap"
python3 skills/brand-trainer/scripts/brand.py vocabulary --avoid "synergy,leverage,circle back"

# Add sample posts for tone reference
python3 skills/brand-trainer/scripts/brand.py samples --add "POV: your AI editor understood the assignment 🎬"

# Set format-specific rules
python3 skills/brand-trainer/scripts/brand.py format instagram \
  --style "hook-first, emoji-heavy, hashtag game strong" \
  --rules "Always start with POV: or hook question" "Max 5 lines before CTA" \
  --examples "POV: you found the cheat code for going viral 🧬"

python3 skills/brand-trainer/scripts/brand.py format tiktok \
  --style "lowercase, chaotic, gen-z energy" \
  --rules "No periods ever" "All lowercase"

python3 skills/brand-trainer/scripts/brand.py format twitter \
  --style "hot takes, quotable, punchy" \
  --rules "Under 200 chars" "No hashtags"
```

## Conversational Training

When a user says things like:
- "make our captions more casual"
- "never use the word synergy"
- "our brand is edgy but not offensive"
- "we sound like a cool friend, not a corporation"

Save these as style memories:

```bash
python3 skills/brand-trainer/scripts/brand.py remember "make captions more casual, less corporate"
python3 skills/brand-trainer/scripts/brand.py memories
```

Style memories are stored in `memory/brand/style.md` and loaded by content-generating skills (caption-writer, comment-responder) alongside the structured API config.

## How Other Skills Use This

Content-generating skills should:
1. Fetch structured config: `python3 skills/brand-trainer/scripts/brand.py show --json`
2. Read style memories: `cat memory/brand/style.md`
3. Include both in their prompt context

## Options

| Command | Description |
|---------|-------------|
| `show` | Display current brand voice config |
| `set` | Set brand voice fields (name, tone, description, audience, product-info) |
| `vocabulary` | Add/remove vocabulary and avoid words |
| `samples` | Add/remove sample posts |
| `format <platform>` | Set format-specific rules for a platform |
| `remember <text>` | Save a style memory from conversation |
| `memories` | List all style memories |

## Environment

Requires `VIRALFARM_API_URL` and `VIRALFARM_API_KEY` in `~/.clawdbot/.env`.
