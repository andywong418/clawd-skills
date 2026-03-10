---
name: influencer-cpm-tracker
description: Track influencer deal CPMs, flag anything over $1K CPM, and maintain a deal database. Input deal cost + expected/actual views, get instant CPM calculation and go/no-go verdict. Auto-flags overpays and generates weekly spend reports.
---

# influencer-cpm-tracker

Tracks influencer deal costs per mille (CPM), flags overpays, and maintains a persistent deal database. Use it to gut-check deals before signing and audit your portfolio after campaigns.

## CPM Formula

```
CPM = (cost / views) * 1000
```

Example: $500 deal, 250,000 expected views → CPM = ($500 / 250,000) * 1000 = **$2.00**

**Flag threshold: $1,000 CPM.** Anything over gets flagged and triggers a Slack alert.

## Quick Start

```bash
# Check a deal before committing (no save)
python3 skills/influencer-cpm-tracker/scripts/track.py check "Jane Smith" --cost 500 --views 250000

# Add a deal to the database
python3 skills/influencer-cpm-tracker/scripts/track.py add "Jane Smith" --cost 500 --views 250000 --platform instagram --post "https://instagram.com/p/abc" --notes "Q1 brand deal"

# List all deals
python3 skills/influencer-cpm-tracker/scripts/track.py list

# Generate a report
python3 skills/influencer-cpm-tracker/scripts/track.py report

# Send report to Slack
python3 skills/influencer-cpm-tracker/scripts/track.py report --slack
```

## All Commands

### `add` — Add a deal
```bash
python3 skills/influencer-cpm-tracker/scripts/track.py add "<influencer>" \
  --cost <amount> \
  --views <expected_views> \
  [--platform instagram|tiktok|youtube|twitter|other] \
  [--handle "@handle"] \
  [--post "<url>"] \
  [--notes "free text"]
```

Calculates CPM, saves to database. If CPM > $1K, flags the deal and sends a Slack alert immediately.

### `check` — Quick CPM check (no save)
```bash
python3 skills/influencer-cpm-tracker/scripts/track.py check "<influencer>" \
  --cost <amount> \
  --views <views>
```

Prints CPM and go/no-go verdict without writing to database. Good for evaluating deals before deciding.

### `list` — Show all deals
```bash
python3 skills/influencer-cpm-tracker/scripts/track.py list
python3 skills/influencer-cpm-tracker/scripts/track.py list --flagged   # only flagged deals
```

### `report` — Summary report
```bash
python3 skills/influencer-cpm-tracker/scripts/track.py report
python3 skills/influencer-cpm-tracker/scripts/track.py report --slack   # also post to Slack
```

Shows total spend, avg CPM, flagged deals, platform breakdown, and top/worst performers.

### `update` — Update actual views post-campaign
```bash
python3 skills/influencer-cpm-tracker/scripts/track.py update <deal_id> --actual-views 180000
```

Recalculates actual CPM from real view counts. Use after a campaign runs to see true performance.

### `remove` — Delete a deal
```bash
python3 skills/influencer-cpm-tracker/scripts/track.py remove <deal_id>
```

### `analyze` — AI portfolio analysis
```bash
python3 skills/influencer-cpm-tracker/scripts/track.py analyze
```

Uses Claude Haiku to analyze your deal portfolio: identifies best/worst CPMs, platform benchmarks, and gives actionable recommendations.

## Data Storage

Deals are stored at `~/.clawdbot/influencer-cpm-tracker/deals.json`:

```json
{
  "deals": [
    {
      "id": "deal_abc123",
      "influencer": "Jane Smith",
      "handle": "@janesmith",
      "platform": "instagram",
      "post_url": "https://...",
      "cost": 500.0,
      "expected_views": 250000,
      "actual_views": null,
      "cpm_expected": 2.0,
      "cpm_actual": null,
      "flagged": false,
      "notes": "brand deal Q1",
      "added_at": "2026-03-09T12:00:00Z",
      "updated_at": "2026-03-09T12:00:00Z"
    }
  ]
}
```

## Environment Variables

All loaded from `~/.clawdbot/.env`:

| Variable | Required | Purpose |
|----------|----------|---------|
| `SLACK_BOT_TOKEN` | Yes (for Slack features) | Post alerts and reports |
| `ANTHROPIC_API_KEY` | Yes (for `analyze`) | Claude Haiku portfolio analysis |

## Slack Alerts

When a flagged deal is added, an alert is automatically posted to `#viral-hunt-reports` (C0AHBK5E9V3):

```
⚠️ CPM Alert: @mikejones deal is $2,000 CPM (over $1K threshold)
Cost: $2,000 | Views: 1,000 | Platform: TikTok
```

Use `report --slack` to post full reports to the same channel.
