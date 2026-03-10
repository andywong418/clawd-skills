---
name: google-imagen
description: Generate images using Google's Imagen API (Gemini). Use when asked to create, generate, or make images with Google, Gemini, Imagen, or "nano banana". Requires GOOGLE_AI_API_KEY in environment.
---

# Google Imagen Image Generation

Generate images via Google's Generative AI API using Imagen models.

## Quick Start

```bash
# Generate a single image
python3 skills/google-imagen/scripts/generate.py "a cat astronaut floating in space"

# With options
python3 skills/google-imagen/scripts/generate.py "a sunset over mountains" --count 2 --output ./images
```

## Script Options

| Option | Default | Description |
|--------|---------|-------------|
| `prompt` | required | Text description of image to generate |
| `--count` | 1 | Number of images (1-4) |
| `--output` | ./output | Output directory |
| `--model` | imagen-4.0-generate-001 | Model: generate-001, ultra-generate-001, fast-generate-001 |
| `--aspect` | 1:1 | Aspect ratio: 1:1, 16:9, 9:16, 4:3, 3:4 |

## Environment

Requires `GOOGLE_AI_API_KEY` in `~/.clawdbot/.env` or environment.

## Output

Images saved as `{output_dir}/{timestamp}_{index}.png`

Script prints paths to generated images for easy reference.
