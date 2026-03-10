---
name: warmup-trainer
description: TikTok/Instagram account warmup trainer. Schedules multiple short engagement sessions per day at randomized times, enforces strict niche focus (AI video, viral content, creative AI), and tracks warmup progress through 3 phases. Use when starting a new account or retraining a stale algorithm.
---

# Warmup Trainer

Train your TikTok/Instagram algorithm through disciplined, niche-focused engagement sessions.

## The Strategy

**Multiple short sessions** (5–10 min), **several times per day**, at **random timing**.

Every like, comment, and watch completion tells the algorithm what to show you. Consistency + niche purity = a FYP that only serves your target content.

**Golden rule: Never engage off-topic. One random like pollutes the feed.**

## Quick Start

```bash
# 1. Initialize for a new account
python3 skills/warmup-trainer/scripts/warmup.py init

# 2. Generate today's session schedule
python3 skills/warmup-trainer/scripts/warmup.py schedule

# 3. When it's time — get your engagement queue
python3 skills/warmup-trainer/scripts/warmup.py session

# 4. Log it when done
python3 skills/warmup-trainer/scripts/warmup.py done

# Check overall progress
python3 skills/warmup-trainer/scripts/warmup.py status
```

## Warmup Phases

### Phase 1: Algorithm Seeding (Days 1–7)
- **Sessions:** 3–4/day, 5 min each
- **Actions:** Watch 80%+ of each video, like if genuinely good niche content
- **Avoid:** Comments, follows, shares, posting anything
- **Why:** Pure consumer mode — train the algo what content to serve you

### Phase 2: Engagement Building (Days 8–14)
- **Sessions:** 4–5/day, 7 min each
- **Actions:** Watch, like, short comments (1–4 words), follow top niche creators
- **Avoid:** Off-topic content (scroll immediately), posting
- **Why:** Signal you're an active niche account — boosts your reach

### Phase 3: Full Engagement (Day 15+)
- **Sessions:** 3–4/day, 10 min each
- **Actions:** Full engagement + start posting niche content
- **Avoid:** Off-topic engagement — forever
- **Why:** Account is warmed. Maintain niche discipline indefinitely.

## Default Niche

**AI video, viral content, creative AI**

Hashtags: `#AIvideo` `#AIart` `#artificialintelligence` `#viralvideo` `#midjourney` `#sora` `#runway` `#kling` `#AIgenerated` `#CreativeAI`

## Commands

| Command | Description |
|---------|-------------|
| `init` | Initialize warmup (prompts for account + platform) |
| `schedule` | Generate randomized session times for today |
| `schedule --regen` | Regenerate today's schedule |
| `session` | Show hashtags + actions for your current session |
| `done` | Log a completed session, shows next session time |
| `status` | Progress, streak, sessions today/week/total |

## Storage

All data stored in `~/.clawdbot/warmup/`:
- `state.json` — account info, niche, start date
- `sessions.json` — log of all completed sessions
- `schedule.json` — today's randomized session schedule

## Setup

```bash
pip install playwright
playwright install chromium
```

First run opens a real Chrome window. Log in to TikTok manually once — the session is saved to `~/.clawdbot/warmup/browser_profile/` and reused every session after that.

## How the Automation Works

- Opens real Chrome (not headless) with a persistent profile
- Navigates to 3–4 random niche hashtag feeds per session
- For each video: reads the description and checks it against niche keywords
- **Niche match** → watches 10–22 seconds, then likes
- **Off-niche** → scrolls past after 2–3 seconds, no like
- Phase 2+: 20% chance to leave a short comment on liked videos
- Randomized delays between all actions to mimic human behavior

## Niche Keywords

Any video description containing these triggers engagement:
`ai`, `midjourney`, `stable diffusion`, `sora`, `runway`, `kling`, `pika`, `generated`, `generative`, `chatgpt`, `ai art`, `ai video`, `creative ai`, `comfyui`, `flux`, and more.

## No API Keys Required

Uses only Playwright (browser automation) — no external APIs.
