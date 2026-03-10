---
name: thumbnail-analyzer
description: Analyze YouTube thumbnails for CTR potential using Claude vision. Scores thumbnails on face/expression, text quality, color contrast, composition, mobile legibility, and emotional hook. Use when asked to analyze, score, compare, or improve thumbnails. Works great combined with thumbnail-generator — generate variants then analyze which performs best.
metadata: {"clawdbot":{"emoji":"🔍","requires":{"pip":["anthropic"]}}}
---

# Thumbnail Analyzer

Score YouTube thumbnails against proven CTR criteria using Claude's vision. Analyze single images or compare A/B variants to pick the winner.

## Quick Start

```bash
# Analyze a single thumbnail
python3 skills/thumbnail-analyzer/scripts/analyze.py thumbnail.png

# Compare A/B variants (auto-picks winner)
python3 skills/thumbnail-analyzer/scripts/analyze.py frame_1_A.png frame_1_B.png

# Compare all thumbnails in a folder
python3 skills/thumbnail-analyzer/scripts/analyze.py ./output/thumbnails/*.png

# Get prioritized improvement suggestions
python3 skills/thumbnail-analyzer/scripts/analyze.py thumbnail.png --improve

# JSON output (pipe into other scripts)
python3 skills/thumbnail-analyzer/scripts/analyze.py thumbnail.png --json
```

## Options

| Option | Description |
|--------|-------------|
| `images` | One or more thumbnail image paths |
| `--compare` | Force comparison mode (default when >1 image) |
| `--improve` | Show prioritized fixes + thumbnail-generator suggestions |
| `--json` | Raw JSON output |

## Scoring Dimensions

| Dimension | Max Points | What it measures |
|-----------|-----------|-----------------|
| Face & Expression | 25 | Human face present + emotional intensity |
| Text Quality | 20 | Word count, font weight, safe placement |
| Color & Contrast | 20 | Contrast ratio, palette, power combos |
| Composition | 20 | Focal point, rule of thirds, background clarity |
| Mobile Legibility | 10 | Readable at 168×94px sidebar size |
| Emotional Hook | 5 | Curiosity gap, viral pattern recognition |
| **Total** | **100** | |

## Score Tiers

| Score | Tier | Meaning |
|-------|------|---------|
| 85–100 | 🟢 Excellent | Publish as-is |
| 70–84 | 🟡 Good | Minor polish needed |
| 50–69 | 🟠 Average | Improve 2–3 areas |
| < 50 | 🔴 Poor | Redesign recommended |

## Example Output

```
────────────────────────────────────────────────────────────
  🟡 frame_1_A.png  [Good]
  Score: 74/100  ███████████████░░░░░
  Strong face + expression, text slightly crowded
────────────────────────────────────────────────────────────

  DIMENSION SCORES:
  Face/Expression   22/25  ████████████████████  Clear shocked face, 35% of frame
  Text Quality      14/20  ██████████████░░░░░░  7 words — trim to 5
  Color/Contrast    17/20  █████████████████░░░  Good yellow/black contrast
  Composition       13/20  █████████████░░░░░░░  Slightly centered, try rule of thirds
  Mobile             8/10  ████████████████░░░░  Readable at small size
  Emotional Hook     0/ 5  ░░░░░░░░░░░░░░░░░░░░  No curiosity gap in text

  ✓ High-emotion face fills upper half
  ✓ Bold white text with black outline
  ✓ Clean blurred background

  ✗ Text word count is 7 (target ≤5)
  ✗ Subject too centered — try rule of thirds
  ✗ No curiosity gap — text states fact instead of teasing
```

## Full Pipeline Example

```bash
# 1. Generate A/B thumbnail variants
python3 skills/thumbnail-generator/scripts/generate.py video.mp4 \
  --title "I quit my job for this" --frames 3

# 2. Analyze and pick the winner
python3 skills/thumbnail-analyzer/scripts/analyze.py ./output/thumbnails/*.png

# 3. Get improvement suggestions for the winner
python3 skills/thumbnail-analyzer/scripts/analyze.py ./output/thumbnails/frame_2_A.png --improve
```

## What "Good" Looks Like

Based on top YouTube creator patterns:
- **Shocked face** filling 30–40% of frame → +30% CTR
- **≤5 word title** in bold with outline → clearly readable at small size
- **High saturation colors** (yellows, reds) against dark background
- **Rule-of-thirds** positioning (not dead-center)
- **Curiosity gap** in text — tease the reveal, don't give it away
- **Single focal point** — face OR text OR object, not all three competing
