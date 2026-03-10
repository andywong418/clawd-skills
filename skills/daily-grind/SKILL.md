---
name: daily-grind
description: Run the full daily TikTok engagement loop for an account. Orchestrates warmup session → comment replies → follow commenters → unfollow non-followers in one command. Use when you want to run the daily routine, set up a cron job, or automate account growth end-to-end.
---

# Daily Grind

One command to run the full daily engagement loop.

## Quick Start

```bash
# Run everything
python3 skills/daily-grind/scripts/daily_grind.py --account tiktok_username

# Skip specific steps
python3 skills/daily-grind/scripts/daily_grind.py --account tiktok_username --skip warmup
python3 skills/daily-grind/scripts/daily_grind.py --account tiktok_username --skip unfollow

# Dry-run (comment replies preview only, no posts)
python3 skills/daily-grind/scripts/daily_grind.py --account tiktok_username --dry-run
```

## What It Runs

| Step | Skill | What it does |
|------|-------|--------------|
| 1 | warmup-trainer | One session of watching + liking niche content |
| 2 | comment-responder | Reply to comments on your recent posts |
| 3 | follow-manager | Follow everyone who commented on your posts |
| 4 | follow-manager | Unfollow non-followers after 3 days |

Each step runs independently — if one fails, the rest continue.

## Automate with Cron

Run once a day automatically:

```bash
# Edit crontab
crontab -e

# Add (runs at 9am daily — adjust path and account)
0 9 * * * cd /path/to/viralfarmbot && python3 skills/daily-grind/scripts/daily_grind.py --account tiktok_username >> ~/.clawdbot/daily-grind.log 2>&1
```

For multiple accounts, add one line per account at staggered times:
```bash
0  9 * * * cd /path/to/viralfarmbot && python3 skills/daily-grind/scripts/daily_grind.py --account tiktok_account1 >> ~/.clawdbot/grind-account1.log 2>&1
0 11 * * * cd /path/to/viralfarmbot && python3 skills/daily-grind/scripts/daily_grind.py --account tiktok_account2 >> ~/.clawdbot/grind-account2.log 2>&1
```

## Setup

All three underlying skills must be set up first:

```bash
# 1. Initialize the account
python3 skills/warmup-trainer/scripts/warmup.py init

# 2. Install deps
pip install playwright anthropic
playwright install chromium

# 3. Set API key
echo "ANTHROPIC_API_KEY=sk-..." >> ~/.clawdbot/.env
```
