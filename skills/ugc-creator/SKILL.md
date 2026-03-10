---
name: ugc-creator
description: Generate AI UGC (user-generated content) creator images and videos. Creates realistic influencer-style photos using Nano Banana 2 (Google Gemini 3.1 Flash Image), then animates them with Kling via fal.ai. Use when asked to create UGC content, AI influencer images, or content creator videos.
---

# UGC Creator

Generate AI UGC creator images and animate them into videos.

## Quick Start

```bash
# Generate a UGC creator image
python3 skills/ugc-creator/scripts/generate_image.py "woman at coffee shop"

# Animate an image to video
python3 skills/ugc-creator/scripts/animate.py /path/to/image.png "subtle head movement, natural blink"

# Full pipeline: image → video
python3 skills/ugc-creator/scripts/create.py "woman reviewing skincare product" --animate
```

## Image Generation Options

| Option | Default | Description |
|--------|---------|-------------|
| `prompt` | required | Scene/setting description |
| `--gender` | female | Gender: male, female |
| `--setting` | cafe | Setting: cafe, home, office, outdoor, gym |
| `--output` | ./output | Output directory |

## Animation Options

| Option | Default | Description |
|--------|---------|-------------|
| `image` | required | Path to image |
| `prompt` | required | Motion description |
| `--duration` | 5 | Duration: 5 or 10 seconds |
| `--output` | ./output | Output directory |

## Environment

Requires in `~/.clawdbot/.env`:
- `GOOGLE_AI_API_KEY` - For Imagen image generation
- `FAL_API_KEY` - For Kling video animation

## Quality Prompt Template

All images use this quality suffix (see references/quality-prompt.md):
- iPhone 15 Pro Max candid style
- 24mm lens at f/11 (sharp background)
- Natural window light with HDR
- No text, grain, blur, or filters
