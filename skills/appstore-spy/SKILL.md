---
name: appstore-spy
description: Track competitor apps on the App Store. Watch a category or keyword, monitor top app rankings, subtitles, ratings, and review velocity over time. Spot rising competitors before they dominate.
metadata: {"clawdbot":{"emoji":"📱","requires":{"bins":[],"pip":[]}}}
---

# App Store Spy

Track competitor apps in any App Store category or keyword. Monitor rankings, ratings, review velocity, and subtitle patterns. Spot rising apps before they dominate.

## Quick Start

```bash
# Watch a keyword — fetch top 50 and store a daily snapshot
python3 skills/appstore-spy/scripts/spy.py watch "social media"

# Watch a category (uses App Store RSS top charts)
python3 skills/appstore-spy/scripts/spy.py watch fitness --category health

# Refresh all watched keywords/categories
python3 skills/appstore-spy/scripts/spy.py fetch

# View current rankings + rank changes since last snapshot
python3 skills/appstore-spy/scripts/spy.py report

# Report for a specific keyword
python3 skills/appstore-spy/scripts/spy.py report "social media"

# Side-by-side app comparison
python3 skills/appstore-spy/scripts/spy.py compare TikTok Instagram

# One-off search without saving anything
python3 skills/appstore-spy/scripts/spy.py search "ai photo editor"

# Stop watching a keyword
python3 skills/appstore-spy/scripts/spy.py unwatch "social media"

# AI analysis of trends (requires ANTHROPIC_API_KEY)
python3 skills/appstore-spy/scripts/spy.py report "social media" --analyze
```

## Commands

| Command | Description |
|---------|-------------|
| `watch <keyword> [--category cat]` | Start watching a keyword or category; fetch + store current top 50 |
| `unwatch <keyword>` | Stop watching |
| `fetch` | Refresh all watched keywords/categories |
| `report [keyword] [--analyze]` | Rankings + rank change table; `--analyze` adds Claude insights |
| `compare <app1> <app2>` | Side-by-side metadata comparison |
| `search <term>` | One-off search, no state saved |
| `list` | Show all watched keywords |

## Categories

Use `--category <name>` with the `watch` command to pull from App Store top charts:

| Name | App Store Genre |
|------|----------------|
| `gaming` | Games |
| `productivity` | Productivity |
| `social` | Social Networking |
| `photo` | Photo & Video |
| `entertainment` | Entertainment |
| `health` | Health & Fitness |
| `finance` | Finance |
| `education` | Education |
| `business` | Business |
| `lifestyle` | Lifestyle |
| `music` | Music |
| `news` | News |
| `sports` | Sports |
| `travel` | Travel |
| `utilities` | Utilities |

Without `--category`, uses the iTunes Search API to find apps matching the keyword.

## Report Output

```
Top 10 — "social media" — 2026-03-09
Rank  App                  Subtitle                     Rating  Reviews    Change
#1    TikTok               Make Your Day                4.7     8.2M        →
#2    Instagram            —                            4.6     12.5M       ▲2
#3    Snapchat             Snap & Chat                  4.5     3.1M        ▼1
#4    Threads              Say More                     4.3     890K        ▲1
...
```

Change indicators: `→` (same), `▲N` (climbed N ranks), `▼N` (dropped N ranks), `NEW` (new entry)

## Data Storage

```
~/.clawdbot/appstore-spy/
  watchlist.json                  — watched keywords/categories
  data/
    social-media/
      2026-03-09.json             — daily snapshot (top 50 apps)
      2026-03-10.json
    health/
      2026-03-09.json
```

Each daily snapshot is a JSON array of app records:

```json
[
  {
    "rank": 1,
    "app_id": "835599320",
    "name": "TikTok",
    "developer": "TikTok Ltd.",
    "subtitle": "Make Your Day",
    "category": "Social Networking",
    "rating": 4.7,
    "rating_count": 8200000,
    "price": 0.0,
    "version": "36.4.0",
    "size_bytes": 315621376,
    "icon_url": "https://...",
    "store_url": "https://apps.apple.com/us/app/tiktok/id835599320",
    "description": "...",
    "snapshot_date": "2026-03-09"
  }
]
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Optional | For `--analyze` flag (Claude Haiku insights) |
| `SLACK_BOT_TOKEN` | Optional | Post reports to Slack (#viral-hunt-reports) |

Both are loaded automatically from `~/.clawdbot/.env`.

## Cron Setup

```cron
# Fetch new data daily at 8am
0 8 * * * cd /root/clawd && python3 skills/appstore-spy/scripts/spy.py fetch >> ~/.clawdbot/appstore-spy/fetch.log 2>&1

# Post weekly report every Monday at 9am
0 9 * * 1 cd /root/clawd && python3 skills/appstore-spy/scripts/spy.py report --analyze >> ~/.clawdbot/appstore-spy/report.log 2>&1
```

## Notes

- Uses iTunes Search API (free, no auth, rate-limited — sleeps 0.5s between calls)
- Uses Apple Marketing Tools RSS feeds for category top charts
- No authentication required — fully public APIs
- Daily snapshots accumulate over time for trend tracking
- Run `fetch` on a cron to build rank history
- `report` compares today's snapshot vs the most recent previous snapshot
