---
name: video-gen
description: Generate videos via the ViralFarm API. Supports multiple providers (Kling, Runway, Sora, Seedance, MagicHour) with text-to-video and image-to-video. Use when asked to generate, create, or make a video with AI. Preferred over fal-video as it goes through the centralized API with credit tracking.
metadata: {"clawdbot":{"emoji":"🎬","requires":{"env":["VIRALFARM_API_URL","VIRALFARM_API_KEY"]}}}
---

# Video Gen

Generate videos through the ViralFarm API. Supports multiple providers and tracks credits.

## Quick Start

```bash
# Text-to-video (uses default provider)
python3 skills/video-gen/scripts/generate.py "a cat cooking pasta in a tiny kitchen"

# With specific provider
python3 skills/video-gen/scripts/generate.py "cinematic drone shot over mountains" --provider runway

# Image-to-video
python3 skills/video-gen/scripts/generate.py "bring this to life" --image https://example.com/photo.jpg

# Image-to-video with provider + model
python3 skills/video-gen/scripts/generate.py "slow zoom in" \
  --image https://example.com/photo.jpg \
  --provider runway --model runway-veo3.1

# Check job status
python3 skills/video-gen/scripts/generate.py --status JOB_ID

# Check remaining credits
python3 skills/video-gen/scripts/generate.py --credits
```

## Options

| Option | Default | Description |
|--------|---------|-------------|
| `prompt` | required | Text prompt for video generation |
| `--provider` | (server default) | `kling`, `runway`, `sora`, `seedance`, `magichour` |
| `--model` | (provider default) | Model name (see below) |
| `--image` | none | Image URL for image-to-video |
| `--image-role` | none | `first_frame` or `last_frame` (for Runway) |
| `--duration` | 5 | Duration in seconds |
| `--ratio` | 16:9 | Aspect ratio: `16:9`, `9:16`, `1:1` |
| `--no-wait` | false | Submit and exit without waiting |
| `--status` | none | Check status of existing job |
| `--credits` | false | Show remaining credits |
| `--output` | ./output | Output directory for downloaded video |

## Providers & Models

| Provider | Models | Notes |
|----------|--------|-------|
| `kling` | (default) | Good all-rounder |
| `runway` | `runway-gen4-turbo`, `runway-veo3.1`, `runway-veo3.1-fast`, `runway-gen4.5` | Best for image-to-video |
| `sora` | (default) | OpenAI's model |
| `seedance` | (default) | Fast generation |
| `magichour` | (default) | Face swap support |

## Credits

Each generation costs 10 credits. Check balance with `--credits`.

## Environment

Requires `VIRALFARM_API_URL` and `VIRALFARM_API_KEY` in `~/.clawdbot/.env`.
