---
name: fal-video
description: Generate videos using fal.ai API. Supports Kling video models (text-to-video, image-to-video). Use when asked to create videos with Kling, fal.ai, or AI video generation. Requires FAL_API_KEY in environment.
---

# fal.ai Video Generation

Generate videos via fal.ai's API using Kling and other video models.

## Quick Start

```bash
# Text-to-video with Kling
python3 skills/fal-video/scripts/generate.py "a majestic eagle soaring through clouds"

# Image-to-video (animate an image)
python3 skills/fal-video/scripts/generate.py "camera slowly zooms in" --image /path/to/image.png

# With options
python3 skills/fal-video/scripts/generate.py "cinematic scene" --duration 10 --aspect 16:9 --output ./videos
```

## Script Options

| Option | Default | Description |
|--------|---------|-------------|
| `prompt` | required | Text description for video |
| `--image` | none | Image URL/path for image-to-video |
| `--duration` | 5 | Duration in seconds (5 or 10) |
| `--aspect` | 16:9 | Aspect ratio: 16:9, 9:16, 1:1 |
| `--model` | v2/master | Model version (v1.6/pro, v2/master, o3) |
| `--output` | ./output | Output directory |
| `--wait` | true | Wait for completion (set --no-wait to just submit) |

## Available Models

- `v2/master` - Kling v2 Master (default, best quality)
- `v1.6/pro` - Kling v1.6 Pro (faster)
- `o3` - Kling O3 (newest, image-to-video only)

## Environment

Requires `FAL_API_KEY` in `~/.clawdbot/.env` or environment.

## Output

Videos saved as `{output_dir}/{request_id}.mp4`

Script prints video URL and local path when complete.
