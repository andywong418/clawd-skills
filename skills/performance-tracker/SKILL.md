---
name: performance-tracker
description: Pull views/likes/comments/shares from TikTok, Instagram, Twitter/X, and YouTube — store to JSON, run Claude analysis of what's working. Use when asked to check analytics, track performance, or see what content is doing well.
---

# Performance Tracker

Track engagement metrics across platforms and get AI-powered analysis of your top-performing content.

## Quick Start

```bash
# Track a TikTok account
python3 skills/performance-tracker/scripts/track.py @viralfarm.ai --platform tiktok

# Track your own YouTube channel (no username needed — uses OAuth credentials)
python3 skills/performance-tracker/scripts/track.py --platform youtube

# Track all platforms at once
python3 skills/performance-tracker/scripts/track.py @viralfarm.ai --platform all

# Analyze stored data across all accounts
python3 skills/performance-tracker/scripts/track.py --analyze

# Analyze a specific platform only
python3 skills/performance-tracker/scripts/track.py --analyze --platform youtube
```

## Options

| Option | Description |
|--------|-------------|
| `username` | Account handle (with or without @). Not needed for YouTube. |
| `--platform` | `tiktok` \| `instagram` \| `twitter` \| `youtube` \| `all` (default: `tiktok`) |
| `--analyze` | Run Claude analysis on stored performance data |

## Output Format

Each platform stores data at `~/.clawdbot/performance/{platform}_{username}.json`:

```json
{
  "platform": "tiktok",
  "username": "realskytan",
  "last_updated": "2026-03-02T12:00:00Z",
  "posts": [
    {
      "id": "7321...",
      "description": "when you ask for a trim...",
      "upload_date": "2026-02-28",
      "views": 1250000,
      "likes": 87000,
      "comments": 3400,
      "shares": 12000,
      "engagement_rate": 0.0819
    }
  ]
}
```

## Environment

| Variable | Required for | Description |
|----------|-------------|-------------|
| `ANTHROPIC_API_KEY` | `--analyze` | Claude API key |
| `TWITTER_BEARER_TOKEN` | Twitter | Twitter API v2 bearer token |
| `YOUTUBE_CLIENT_ID` | YouTube | Google OAuth2 client ID |
| `YOUTUBE_CLIENT_SECRET` | YouTube | Google OAuth2 client secret |
| `YOUTUBE_REFRESH_TOKEN` | YouTube | OAuth refresh token (set via auth script) |

Set in `~/.clawdbot/.env`. YouTube credentials are set automatically by:
```bash
python3 skills/post-scheduler/scripts/queue.py auth youtube
```

## Cookies (TikTok & Instagram)

yt-dlp works best with browser cookies. Export using "Get cookies.txt LOCALLY" extension:

- TikTok: save to `~/.clawdbot/cookies/tiktok.txt`
- Instagram: save to `~/.clawdbot/cookies/instagram.txt`

## Notes

- **TikTok / Instagram**: uses yt-dlp to dump playlist metadata (no video download)
- **Twitter**: Twitter API v2 free tier — `impression_count` may be 0 on free tier
- **YouTube**: YouTube Data API v3 — fetches your own channel's videos via OAuth; share counts not available via API
- Results are merged by post ID on each run — metrics updated in place, new posts appended
- YouTube `is_shorts` flag detected from `#Shorts` in title/description
