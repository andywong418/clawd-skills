---
name: tiktok-downloader
description: Download TikTok videos without watermark. Supports single URLs, batch lists, user profiles, audio-only, and metadata extraction. Use when asked to download, save, or repurpose TikTok videos. Enables content repurposing pipeline from TikTok → Instagram/YouTube Shorts.
metadata: {"clawdbot":{"emoji":"⬇️","requires":{"bins":["yt-dlp"]}}}
---

# TikTok Downloader

Download TikTok videos without watermark for repurposing. Works best with Chrome logged into TikTok on the same machine (cookies extracted automatically).

## Quick Start

```bash
# Single video
python3 skills/tiktok-downloader/scripts/download.py https://www.tiktok.com/@user/video/123

# Multiple videos
python3 skills/tiktok-downloader/scripts/download.py URL1 URL2 URL3

# Batch from file (one URL per line)
python3 skills/tiktok-downloader/scripts/download.py --file urls.txt

# User's recent videos (top 10)
python3 skills/tiktok-downloader/scripts/download.py https://www.tiktok.com/@username --user --limit 10

# Audio only (MP3) — great for extracting trending sounds
python3 skills/tiktok-downloader/scripts/download.py URL --audio-only

# Metadata only (no download)
python3 skills/tiktok-downloader/scripts/download.py URL --metadata-only

# JSON output (pipe into other scripts)
python3 skills/tiktok-downloader/scripts/download.py URL --json
```

## Options

| Option | Default | Description |
|--------|---------|-------------|
| `urls` | required | One or more TikTok video URLs |
| `--file` | — | File with one URL per line |
| `--output` | ./downloads | Output directory |
| `--audio-only` | false | Extract audio as MP3 |
| `--metadata-only` | false | Print info without downloading |
| `--user` | false | Download from a user profile |
| `--limit` | 10 | Max videos for `--user` |
| `--json` | false | JSON output |

## Download Strategies (automatic fallback)

1. **yt-dlp + Chrome cookies** — best quality, no watermark. Works when Chrome is logged into TikTok.
2. **yt-dlp + cookie file** — uses `~/.clawdbot/cookies/tiktok.txt` (Netscape format)
3. **yt-dlp unauthenticated** — works for some public videos
4. **tikwm.com API** — no-watermark fallback, no auth needed, rate-limited

## No-Watermark Tips

For consistent watermark-free downloads:
- Keep Chrome logged into TikTok on the server (cookies extracted automatically)
- Or export TikTok cookies as Netscape format → `~/.clawdbot/cookies/tiktok.txt`
  - Use browser extension "Get cookies.txt LOCALLY" on tiktok.com
  - **Note:** `tiktok.txt` (Netscape) not `tiktok.json`

## Metadata Output

```
  ────────────────────────────────────────────────────────
  @khaby.lame — Khaby Lame
  When you overcomplicate things 😂
  Views: 42.1M  Likes: 8.2M  Comments: 45K
  Music: Monkeys Spinning Monkeys — Kevin MacLeod
  Saved: ./downloads/7137149357702893830_khaby.lame.mp4
  ────────────────────────────────────────────────────────
```

## Repurposing Pipeline

```bash
# 1. Download viral TikTok
python3 skills/tiktok-downloader/scripts/download.py URL --output ./raw

# 2. Burn subtitles for Instagram
python3 skills/subtitle-burner/scripts/burn.py ./raw/video.mp4 --output ./edited

# 3. Generate caption
python3 skills/caption-writer/scripts/write.py "viral life hack about X" --platform instagram

# 4. Post
```

## Batch URL File Format

```
# urls.txt — lines starting with # are ignored
https://www.tiktok.com/@user1/video/111
https://www.tiktok.com/@user2/video/222
https://www.tiktok.com/@user3/video/333
```

## Notes

- yt-dlp must be installed: `pip install yt-dlp` or `brew install yt-dlp`
- TikTok actively blocks IP ranges — cookies are often required
- Rate limit tikwm.com fallback — don't hammer it with 100+ requests
- Downloaded videos are saved as MP4, audio as MP3
