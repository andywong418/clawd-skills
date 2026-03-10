---
name: comment-responder
description: Auto-reply to TikTok comments using Claude. Visits your recent posts, finds unreplied comments, generates authentic short replies tuned to the AI video niche, and posts them. Shares account storage and browser profiles with warmup-trainer — no separate init needed. Use when you want to boost engagement on recent posts or run a comment reply session.
---

# Comment Responder

Auto-reply to TikTok comments with Claude-generated responses that sound human, stay on-niche, and drive more engagement.

## Quick Start

```bash
# Reply to comments on recent posts (dry-run first to preview)
python3 skills/comment-responder/scripts/comment_responder.py --account tiktok_username --dry-run

# Run for real
python3 skills/comment-responder/scripts/comment_responder.py --account tiktok_username

# Control how many replies per session
python3 skills/comment-responder/scripts/comment_responder.py --account tiktok_username --max-replies 5

# Check more videos
python3 skills/comment-responder/scripts/comment_responder.py --account tiktok_username --videos 10
```

## How It Works

1. Opens your TikTok profile using the saved browser session (from warmup-trainer)
2. Visits your N most recent videos (default: 5)
3. Scans comments — skips ones you've already replied to
4. Sends each comment + video context to Claude
5. Claude generates a short, authentic reply in your niche voice
6. Posts the reply with human-like timing (random 5–15s delays)
7. Logs every reply to `~/.clawdbot/warmup/accounts/{key}/comments_replied.json`

## Reply Style

Replies are:
- **Short** — 1–2 sentences max, often just a few words
- **Authentic** — no corporate language, no hashtags
- **Niche-aware** — references AI video, creative AI, generative content
- **Engagement-driving** — questions, reactions, teases for more content

## Safety Limits

- Max 10 replies per session by default (configurable)
- Random 5–15s delay between each reply
- Tracks replied comment IDs — never double-replies
- `--dry-run` mode to preview all replies before posting

## Setup

Requires the account to already be initialized in warmup-trainer (shares browser profile):

```bash
# If not already done
python3 skills/warmup-trainer/scripts/warmup.py init

# Then run comment responder
python3 skills/comment-responder/scripts/comment_responder.py --account tiktok_username
```

Also requires `ANTHROPIC_API_KEY` in environment or `~/.clawdbot/.env`.

```bash
pip install playwright anthropic
playwright install chromium
```

## Storage

Uses warmup-trainer's account directories — no separate storage:
```
~/.clawdbot/warmup/accounts/{platform}_{username}/
  browser_profile/           ← shared with warmup-trainer
  state.json                 ← shared account state
  comments_replied.json      ← reply log (new, created by this skill)
```
