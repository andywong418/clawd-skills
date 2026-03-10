---
name: viral-templates
description: Collection of proven viral video templates with exact prompts for AI generation. Use when asked to create content using popular formats like barbershop meme, before/after reveals, POV formats, etc. Each template includes image prompts for Imagen and video direction for Kling.
---

# Viral Templates

Proven viral formats with production-ready prompts for AI generation.

## Available Templates

| Template | Format | Best For |
|----------|--------|----------|
| `barbershop` | Image → Video | Reveals, transformations, "say no more" memes |
| `pov-reaction` | Image → Video | Relatable moments, first-person scenarios |
| `before-after` | Image pair → Video | Transformations, glow-ups, comparisons |

## Usage

1. Pick a template from `templates/`
2. Customize the variables (name, text, scenario)
3. Generate image with Imagen (`skills/google-imagen`)
4. Animate with Kling (`skills/fal-video`)
5. Add text/audio in editing

## Template Format

Each template file contains:
```
TEMPLATE: [Name]
VIRAL MECHANIC: Why this format works
IMAGE PROMPT: Detailed prompt for Imagen (with [VARIABLES])
VIDEO DIRECTION: How to animate with Kling
TEXT OVERLAY: On-screen text format
AUDIO: Sound design notes
EXAMPLES: Successful uses of this format
```

## Quick Start

```bash
# Read the template
cat skills/viral-templates/templates/barbershop.md

# Generate image (replace variables)
python3 skills/google-imagen/scripts/generate.py "[customized prompt]"

# Animate
python3 skills/fal-video/scripts/generate.py "slow zoom, person looks up at camera" --image output/image.png
```
