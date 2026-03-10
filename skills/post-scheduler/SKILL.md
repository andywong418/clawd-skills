---
name: post-scheduler
description: Queue and schedule video posts to TikTok, Instagram, and YouTube at optimal times. Add posts with captions, schedule at research-based optimal windows, run queue to publish. Use when asked to schedule, queue, or post content to TikTok, Instagram, or YouTube. Requires platform credentials in ~/.clawdbot/.env.
---

# Post Scheduler

Queue video posts to TikTok, Instagram, and YouTube with captions and optimal timing.

## Quick Start

```bash
# Add to queue at next optimal time
python3 skills/post-scheduler/scripts/queue.py add tiktok ./video.mp4 \
  "This changed my skincare routine 🤯" \
  --hashtags "skincare skintok glowup fyp" --optimal

python3 skills/post-scheduler/scripts/queue.py add instagram ./reel.mp4 \
  "Morning routine that actually works ✨" --optimal

python3 skills/post-scheduler/scripts/queue.py add youtube ./shorts.mp4 \
  "I tested this viral skincare hack so you don't have to" --optimal

# View queue
python3 skills/post-scheduler/scripts/queue.py list

# Run queue (post anything due)
python3 skills/post-scheduler/scripts/run.py

# Set up YouTube credentials (one-time)
python3 skills/post-scheduler/scripts/queue.py auth youtube
```

## Commands

| Command | Description |
|---------|-------------|
| `add <platform> <video> "<caption>"` | Add post to queue |
| `list [--status pending\|posted\|failed]` | View queue |
| `remove <id>` | Remove a post |
| `clear [--posted]` | Clear queue (or just posted entries) |
| `optimal` | Show next optimal times per platform |
| `auth <platform>` | Set up credentials |

### `add` Options

| Option | Default | Description |
|--------|---------|-------------|
| `--hashtags` | none | Space-separated tags (with or without #) |
| `--at` | now+5min | Exact time (ISO: `2026-03-02T19:00`) |
| `--optimal` | false | Next optimal posting window |
| `--privacy` | public | YouTube only: public / private / unlisted |
| `--no-shorts` | false | YouTube only: treat as regular video, not Shorts |

## Optimal Posting Windows

| Platform | Windows (local time) |
|----------|---------------------|
| TikTok | 6–10am, 12–3pm, 7–9pm |
| Instagram | 6–9am, 11am–1pm, 7–9pm |
| YouTube | 8–10am, 12–2pm, 5–8pm |

## Credentials

Add to `~/.clawdbot/.env`:

```bash
# TikTok
TIKTOK_ACCESS_TOKEN=...      # TikTok Developer Portal → Content Posting API

# Instagram
INSTAGRAM_ACCESS_TOKEN=...   # Meta Developer Portal → Instagram Graph API
INSTAGRAM_USER_ID=...        # GET /me?fields=id with your access token

# YouTube (run auth script below — it saves these automatically)
YOUTUBE_CLIENT_ID=...
YOUTUBE_CLIENT_SECRET=...
YOUTUBE_REFRESH_TOKEN=...

# fal.ai (for Instagram video hosting — likely already set)
FAL_API_KEY=...
```

### YouTube Setup (one-time)

```bash
# Interactive setup — opens browser for OAuth
python3 skills/post-scheduler/scripts/queue.py auth youtube
```

Needs: Google Cloud project → YouTube Data API v3 enabled → OAuth2 Desktop credentials.

## Queue File

Stored at `~/.clawdbot/post-queue.json`. Each entry:
```json
{
  "id": "a1b2c3d4",
  "platform": "youtube",
  "video": "/path/to/video.mp4",
  "caption": "Title line\n\nDescription text #Shorts",
  "scheduled_at": "2026-03-02T19:00:00",
  "status": "pending",
  "yt_privacy": "public",
  "yt_shorts": true
}
```

## Cron Setup

```bash
# Run queue processor every 15 minutes
*/15 * * * * cd /path/to/viralfarmbot && python3 skills/post-scheduler/scripts/run.py >> ~/.clawdbot/post-scheduler.log 2>&1
```

## YouTube Extras

Beyond basic upload, the YouTube platform module also supports:

```python
from skills.post-scheduler.scripts.platforms.youtube import upload_thumbnail, update_video

# Set a custom thumbnail after upload
upload_thumbnail(video_id="abc123", thumbnail_path="thumbnail.jpg")

# Update title/description/tags/privacy on an existing video
update_video(
    video_id="abc123",
    title="New Title",
    description="Updated description #Shorts",
    tags=["ugc", "skincare"],
    privacy="public",   # public | private | unlisted
)
```

## Platform Notes

- **TikTok**: Direct file upload. Max 3 min (10 min eligible accounts).
- **Instagram**: Video hosted on fal.ai temporarily. Max 90s via API.
- **YouTube**: Resumable chunked upload. `#Shorts` auto-added if missing. Max 60s for Shorts. Supports custom thumbnails and post-upload metadata edits.
