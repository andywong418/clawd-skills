---
name: follow-manager
description: Strategic TikTok follow/unfollow automation. Follow people who commented on your posts, people engaging with niche hashtags, or followers of a target account. Automatically unfollows non-followers after N days. Tracks all follows with timestamps and source. Shares account storage and browser profiles with warmup-trainer.
---

# Follow Manager

Grow faster with strategic follows and clean up non-followers automatically.

## Commands

```bash
# Follow people who commented on your recent posts (highest intent)
python3 skills/follow-manager/scripts/follow_manager.py --account tiktok_user follow-commenters

# Follow people engaging with a niche hashtag
python3 skills/follow-manager/scripts/follow_manager.py --account tiktok_user follow-hashtag --hashtag aivideo

# Follow followers of a specific account (competitor research)
python3 skills/follow-manager/scripts/follow_manager.py --account tiktok_user follow-fans --of someaccount

# Unfollow people who didn't follow back after 3 days
python3 skills/follow-manager/scripts/follow_manager.py --account tiktok_user unfollow

# Unfollow after custom days
python3 skills/follow-manager/scripts/follow_manager.py --account tiktok_user unfollow --after-days 5

# Show follow stats
python3 skills/follow-manager/scripts/follow_manager.py --account tiktok_user status
```

## Strategy

**Follow commenters first** — they already watched your video and engaged. Highest chance of follow-back.

**Follow hashtag engagers** — people actively in your niche right now.

**Unfollow non-followers** — keep your follower ratio healthy. TikTok suppresses accounts with high following/follower disparity.

**Safe daily limits:**
- Max 30 follows per session, ~150/day across sessions
- Max 30 unfollows per session
- 3–8s random delay between each action

## How It Works

- `follow-commenters`: visits your recent posts, scrapes commenters, follows each
- `follow-hashtag`: browses a hashtag feed, follows video creators
- `follow-fans`: visits a target account's followers list, follows them
- `unfollow`: loads your follow log, visits each non-follower's profile, detects "Follows you" badge, unfollows anyone who didn't follow back after N days
- All actions logged to `follows.json` with timestamp + source

## Storage

Shared with warmup-trainer:
```
~/.clawdbot/warmup/accounts/{platform}_{username}/
  browser_profile/     ← shared with warmup-trainer
  state.json           ← shared account state
  follows.json         ← follow log (created by this skill)
```

## Setup

Account must be initialized in warmup-trainer first:
```bash
python3 skills/warmup-trainer/scripts/warmup.py init

pip install playwright
playwright install chromium
```
