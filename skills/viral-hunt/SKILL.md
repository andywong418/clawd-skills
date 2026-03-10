# Viral Hunt Skill

Hunt viral content from Instagram, prepare for cross-posting to TikTok/Twitter/IG.

## Trigger
- "viral hunt", "find viral reels", "scan for viral content"
- Cron job: `viral-hunt-4h` (every 4 hours)

## Workflow

### 0. Anti-Bot Detection: Random Delays
**CRITICAL** — Add random delays between all browser actions to avoid being flagged as a bot.

```bash
# Between page loads: 2-5 seconds
sleep $((RANDOM % 4 + 2))

# Between clicks: 1-3 seconds  
sleep $((RANDOM % 3 + 1))

# Between typing characters (if needed): 50-150ms
```

**Rules:**
- Never execute actions back-to-back without delay
- Vary timing to appear human-like
- Add extra delay (5-10s) after uploads

### 1. Pre-Flight: Browser Memory Management
**CRITICAL** — Server has limited RAM (1.9GB). Always run cleanup before scraping.

```
# Close all tabs except essential ones
browser action=tabs profile=clawd
# Close any tabs not needed for current operation
browser action=close profile=clawd targetId=<id>

# Verify memory is adequate (need 400MB+ free)
exec command="free -h | grep Mem"
```

**Rules:**
- Max 3 tabs open at any time
- Close tab immediately after scraping each page
- If snapshot times out, close tabs and retry

### 2. Load Tracked Accounts
Read from `/root/clawd/viralfarm/crawler.json`:
- `queue` — accounts to scan
- `visited` — already processed
- `ai_video_accounts` — curated list with metadata

### 3. Scan Each Account
For each account in the tracked list:

```
# Open profile page
browser action=open profile=clawd targetUrl=https://www.instagram.com/{handle}/reels/

# Take snapshot (compact mode to save memory)
browser action=snapshot profile=clawd targetId=<id> compact=true

# Extract reel links and view counts from snapshot
# Look for patterns like "1.2M views", "500K views"

# CLOSE TAB IMMEDIATELY after extraction
browser action=close profile=clawd targetId=<id>
```

### 4. Filter Viral Content
- Minimum threshold: 100K views
- Prefer content from last 24-48 hours
- Rank by views descending

### 5. Save Results
Update `/root/clawd/viralfarm/viral-queue.json`:
```json
{
  "last_scan": "ISO timestamp",
  "top_viral": [
    {
      "account": "@handle",
      "url": "reel URL",
      "views": "1.2M",
      "content_type": "AI/lifehack/etc",
      "status": "new"
    }
  ]
}
```

### 6. Post Report for Approval
Send to Slack #viralfarm (C0AHBK5E9V3):
- Top 5 picks with view counts
- Links to each reel
- Prompt: "Reply with numbers to approve (e.g. '1, 3, 5') or 'all'"

### 7. On Approval
When user approves:
1. Download video using yt-dlp or browser
2. Post to connected accounts:
   - TikTok @viralfarm.ai (browser automation)
   - Instagram @viralfarmai (browser automation)
   - Twitter @viralfarmbot (API)

## Connected Accounts
| Platform | Account | Method |
|----------|---------|--------|
| Instagram | @viralfarmai | Browser (clawd profile) |
| TikTok | @viralfarm.ai | Browser (clawd profile) |
| Twitter | @viralfarmbot | API (credentials in ~/.clawdbot/.env) |

## Troubleshooting

### Browser Timeout
1. Check memory: `free -h`
2. Close unused tabs
3. Restart browser: `browser action=stop profile=clawd` then `browser action=start profile=clawd`

### Instagram Login Expired
Re-inject cookies or log in manually via browser.

### Rate Limits
- Instagram: Max ~100 page loads/hour
- Space out requests by 5-10 seconds

## Files
- `/root/clawd/viralfarm/crawler.json` — tracked accounts
- `/root/clawd/viralfarm/viral-queue.json` — viral content queue
- `/root/clawd/viralfarm/twitter_post.py` — Twitter posting script
