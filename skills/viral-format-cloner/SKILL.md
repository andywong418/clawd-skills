---
name: viral-format-cloner
description: Watch your own posted content for viral hits (100K+ IG / 500K+ TikTok). When a post blows up, auto-generate 3 hook variations with the same structure and queue them. Turns one viral hit into a content multiplication engine.
---

# Viral Format Cloner

Monitors your OWN posted content. When something hits viral thresholds, it auto-generates 3 hook variations using Claude and queues them to the post-scheduler. One viral hit becomes four pieces of content.

## The Core Idea

You posted something. It blew up. Rather than manually trying to recreate it, this skill:
1. Detects the hit (by scanning your post queue for posts with high view counts)
2. Generates 3 variations with different hooks but the same structure
3. Queues them automatically at optimal times

## Quick Start

```bash
# Scan for viral hits and auto-queue variations
python3 skills/viral-format-cloner/scripts/clone.py check

# Preview what would be cloned, without actually queuing
python3 skills/viral-format-cloner/scripts/clone.py check --dry-run

# Show all posts that have triggered cloning
python3 skills/viral-format-cloner/scripts/clone.py list-hits

# Manually trigger cloning for a specific post ID
python3 skills/viral-format-cloner/scripts/clone.py clone <post_id>

# Show queued cloned posts and their status
python3 skills/viral-format-cloner/scripts/clone.py status
```

## Commands

| Command | Description |
|---------|-------------|
| `check` | Scan post-queue.json for viral hits, auto-generate and queue variations for new hits |
| `check --dry-run` | Same as check but only previews — no queueing, no Slack |
| `list-hits` | Show all posts that have triggered cloning |
| `clone <post_id>` | Manually trigger cloning for a specific post by ID |
| `status` | Show recently queued cloned posts and their status |

## Options

| Flag | Default | Description |
|------|---------|-------------|
| `--dry-run` | off | Preview mode — show what would happen without doing it |
| `--platform` | all | Filter to a specific platform (instagram, tiktok, twitter, youtube) |
| `--min-views` | platform default | Override the view threshold |
| `--force` | off | Re-clone a post that's already been cloned |

## Thresholds

| Platform | Default Threshold | Signal |
|----------|------------------|--------|
| Instagram | 100,000 views | `view_count` on posted entry |
| TikTok | 500,000 views | `view_count` on posted entry |
| Twitter | 100,000 impressions | `impression_count` on posted entry |
| YouTube | 50,000 views | `view_count` on posted entry |

## How It Works

1. **Scan** — Loads `~/.clawdbot/post-queue.json`, finds entries with `status: "posted"` and a `view_count` above threshold
2. **Dedup** — Checks `~/.clawdbot/viral-format-cloner/hits.json` — skips posts already cloned
3. **Generate** — Calls Claude Haiku with the original caption. Gets back 3 hook variations in JSON
4. **Queue** — Calls `post-scheduler/scripts/queue.py add` for each variation at optimal time
5. **Report** — Sends a Slack summary to `#viral-hunt-reports`
6. **Save** — Writes the hit record to `hits.json` so it won't be re-processed

## Output Format — hits.json

```json
{
  "post_id": {
    "original_url": "https://www.instagram.com/p/ABC123/",
    "platform": "instagram",
    "views": 145000,
    "caption": "The original caption text...",
    "video_path": "/root/clawd/output/video.mp4",
    "cloned_at": "2026-03-09T12:00:00Z",
    "variations": [
      "Hook variation 1...",
      "Hook variation 2...",
      "Hook variation 3..."
    ],
    "queued_ids": ["a1b2c3d4", "e5f6g7h8", "i9j0k1l2"]
  }
}
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Required — Claude API key for variation generation |
| `SLACK_BOT_TOKEN` | Required — Slack bot token for reporting |

Loaded from `~/.clawdbot/.env`.

## Cron Setup

Run every hour to catch hits as they happen:

```bash
# Crontab — runs every hour
0 * * * * cd /root/clawd && python3 skills/viral-format-cloner/scripts/clone.py check >> ~/.clawdbot/viral-format-cloner/cron.log 2>&1
```

## Data Files

- `~/.clawdbot/viral-format-cloner/hits.json` — Record of all posts that triggered cloning (auto-created)
- `~/.clawdbot/post-queue.json` — Read-only source of posted content + view counts

## Cost

- One Claude Haiku call per viral hit detected
- ~$0.002 per hit (3 variations, ~500 tokens)
- Typical run: 0-1 new hits = $0.00-$0.002
