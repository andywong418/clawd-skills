---
name: thumbnail-generator
description: Generate A/B thumbnail variants for a TikTok or YouTube video. Extracts frames from a video (or uses a provided image) and composites bold text overlays in two styles. Use when asked to create thumbnails, A/B test thumbnail options, or add text to a video frame. Requires ffmpeg.
---

# Thumbnail Generator

Extract frames from a video and generate A/B thumbnail variants with text+face composition.

## Quick Start

```bash
# From video — extracts 3 frames, generates 2 variants each (6 thumbnails)
python3 skills/thumbnail-generator/scripts/generate.py \
  video.mp4 \
  --title "I tried this for 30 days" \
  --subtitle "the results shocked me"

# From image — generate 2 variants
python3 skills/thumbnail-generator/scripts/generate.py \
  frame.jpg \
  --title "POV: your barber asks what you want"

# Custom output dir
python3 skills/thumbnail-generator/scripts/generate.py \
  video.mp4 \
  --title "This changed everything" \
  --output ./thumbnails
```

## Options

| Option | Default | Description |
|--------|---------|-------------|
| `input` | required | Video or image path |
| `--title` | required | Main text (bold, large) |
| `--subtitle` | none | Secondary text line |
| `--frames` | 3 | Number of frames to extract from video (1-5) |
| `--output` | ./output/thumbnails | Output directory |

## Output

For each extracted frame, generates two variants:
- `frame_N_A.png` — White bold text + black outline at **top**
- `frame_N_B.png` — Yellow bold text on dark strip at **bottom**

Pick the frame with the clearest face, then pick the text layout that doesn't cover it.

## No API Keys Required

Uses only ffmpeg (system) and Pillow (pip).
