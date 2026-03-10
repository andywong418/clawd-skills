---
name: cross-poster
description: Reformat one video for TikTok, IG Reels, and YouTube Shorts in one shot. Crops to 9:16, enforces platform duration limits, re-encodes, generates platform-specific captions, and can post immediately. Use when asked to cross-post, reformat for multiple platforms, or repurpose a video. Requires ffmpeg. Optional: ANTHROPIC_API_KEY for captions, platform credentials for --post.
---

# Cross-Poster

Take one video → output TikTok + IG Reels + YouTube Shorts versions with captions. Can post immediately.

## Quick Start

```bash
# Reformat + captions for all 3 platforms
python3 skills/cross-poster/scripts/cross_post.py \
  video.mp4 "girl trying viral skincare hack, honest reaction"

# Reformat AND post to all platforms immediately
python3 skills/cross-poster/scripts/cross_post.py \
  video.mp4 "skincare hack review" --post

# Specific platforms only
python3 skills/cross-poster/scripts/cross_post.py \
  video.mp4 "travel vlog" --platforms tiktok instagram

# No captions (files only)
python3 skills/cross-poster/scripts/cross_post.py video.mp4 --no-captions
```

## What It Does Per Platform

1. **Crop to 9:16** — smart center crop if not vertical
2. **Scale to 1080×1920** — platform native resolution
3. **Trim to duration limit** — TikTok 3min, Reels 90s, Shorts 60s
4. **Re-encode** — H.264 / AAC, mobile-optimized
5. **Generate caption** — platform-specific tone via Claude Haiku
6. **Post** (if `--post`) — via post-scheduler platform modules

## Platform Specs

| Platform | Max Duration | Resolution | Caption Style |
|----------|-------------|------------|---------------|
| TikTok | 3 min | 1080×1920 | Short, punchy, Gen-Z, content hashtags |
| IG Reels | 90s | 1080×1920 | Warm, authentic, soft CTA, 10–15 hashtags |
| YouTube Shorts | 60s | 1080×1920 | Title (70 chars) + description + #Shorts |

## Options

| Option | Default | Description |
|--------|---------|-------------|
| `video` | required | Input video file |
| `context` | optional | Video description for caption generation |
| `--platforms` | all | tiktok instagram youtube |
| `--no-captions` | false | Skip Claude captions |
| `--no-trim` | false | Don't trim to duration limits |
| `--post` | false | Post immediately after processing |
| `--privacy` | public | YouTube privacy (public/private/unlisted) |
| `--output` | ./output | Output base directory |

## Output Structure

```
output/
  tiktok/
    video_tiktok.mp4
    video_caption.txt
  instagram/
    video_instagram.mp4
    video_caption.txt
  youtube/
    video_youtube.mp4
    video_caption.txt
```

## Full Pipeline

```bash
# 1. Generate UGC video
python3 skills/ugc-creator/scripts/create_ugc.py \
  "Woman with brown hair" --motion "taking selfie in bathroom mirror" \
  --output ./ugc

# 2. Cross-post to all platforms + post immediately
python3 skills/cross-poster/scripts/cross_post.py \
  ./ugc/videos/*.mp4 \
  "morning routine check-in vibe, natural lighting, relatable" \
  --post

# OR: cross-post to get files, then schedule for optimal times
python3 skills/cross-poster/scripts/cross_post.py ./ugc/videos/*.mp4 "morning routine"
python3 skills/post-scheduler/scripts/queue.py add tiktok output/tiktok/video_tiktok.mp4 \
  "$(cat output/tiktok/video_caption.txt)" --optimal
python3 skills/post-scheduler/scripts/queue.py add youtube output/youtube/video_youtube.mp4 \
  "$(cat output/youtube/video_caption.txt)" --optimal
```

## Environment

- `ffmpeg` + `ffprobe` — required
- `ANTHROPIC_API_KEY` — for caption generation
- Platform credentials — only needed for `--post` (see post-scheduler SKILL.md)
