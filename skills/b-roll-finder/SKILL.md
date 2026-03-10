---
name: b-roll-finder
description: Given a script beat description, find and download matching royalty-free b-roll footage from Pexels. Uses Claude to extract search keywords from natural language beat descriptions, then searches and downloads HD portrait video. Use when asked to find b-roll, stock footage, or background video for a script beat. Requires PEXELS_API_KEY; ANTHROPIC_API_KEY optional (falls back to raw text search).
---

# B-Roll Finder

Find and download royalty-free b-roll footage that matches a script beat.

## Quick Start

```bash
# From a script beat
python3 skills/b-roll-finder/scripts/find.py \
  "person checking their phone nervously in a waiting room"

# Multiple results
python3 skills/b-roll-finder/scripts/find.py \
  "aerial view of city at night, neon lights" \
  --count 3

# Landscape footage (default is portrait for TikTok)
python3 skills/b-roll-finder/scripts/find.py \
  "coffee shop morning routine" \
  --orientation landscape

# Custom output dir
python3 skills/b-roll-finder/scripts/find.py \
  "barber cutting hair close up" \
  --output ./footage/beat1
```

## Options

| Option | Default | Description |
|--------|---------|-------------|
| `beat` | required | Script beat description (natural language) |
| `--count` | 1 | Number of clips to download |
| `--orientation` | portrait | `portrait` (9:16) or `landscape` (16:9) |
| `--output` | ./output/broll | Output directory |

## How It Works

1. Claude extracts 3 search-optimized keywords from your beat description
2. Searches Pexels video library for each keyword set
3. Picks the best HD match (prefers portrait/landscape per `--orientation`)
4. Downloads to output directory

If `ANTHROPIC_API_KEY` is not set, uses your beat text directly as the search query.

## Environment

- `PEXELS_API_KEY` — required (get free key at pexels.com/api)
- `ANTHROPIC_API_KEY` — optional, improves search query quality
