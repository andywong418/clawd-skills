---
name: script-writer
description: Generate timed 15–60 second video scripts for Instagram Reels, TikTok, and YouTube Shorts. Outputs scene-by-scene breakdown with narration, visual direction, and text overlays. Use when asked to write a script, plan a video, create a reel script, or outline a short-form video.
metadata: {"clawdbot":{"emoji":"🎬","requires":{"env":["ANTHROPIC_API_KEY"]}}}
---

# Script Writer

Generate production-ready short-form video scripts with timed scenes, narration, visual direction, and text overlays.

## Quick Start

```bash
# 30-second Instagram Reel
python3 skills/script-writer/scripts/write.py "this AI tool replaces your entire marketing team"

# 15-second TikTok with specific format
python3 skills/script-writer/scripts/write.py "morning routine that 10x'd my productivity" \
  --duration 15 --format storytime

# 60-second YouTube Short, problem-solution style
python3 skills/script-writer/scripts/write.py "why your reels get 200 views" \
  --duration 60 --format problem-solution --vibe informative

# Multiple variants
python3 skills/script-writer/scripts/write.py "coffee shop productivity hack" --variants 2

# JSON output for pipeline integration
python3 skills/script-writer/scripts/write.py "AI side hustle" --json
```

## Options

| Option | Default | Description |
|--------|---------|-------------|
| `topic` | required | What the video is about |
| `--duration` | 30 | Target length in seconds (15, 30, 45, 60) |
| `--format` | auto | Script format (see table below) |
| `--vibe` | relatable | Tone/energy of the script |
| `--variants` | 1 | Number of script options (1–3) |
| `--context` | — | Extra detail (product, audience, etc.) |
| `--json` | false | Output raw JSON |
| `--list-formats` | — | Print all formats and exit |

## Formats

| Format | Description | Best For |
|--------|-------------|----------|
| `storytime` | First person narrative with a twist | Personal anecdotes, day-in-life |
| `listicle` | Numbered tips/items rapid fire | Educational, value content |
| `pov` | POV: [scenario] — visual-first, minimal narration | Relatable moments, comedy |
| `problem-solution` | Pain point → reveal → solution | Product demos, tutorials |
| `before-after` | Transformation with dramatic reveal | Glow-ups, tool showcases |
| `hot-take` | Bold claim → evidence → mic drop | Thought leadership, controversy |
| `tutorial` | Step-by-step walkthrough | How-to, educational |
| `auto` | AI picks the best format for the topic | When you're not sure |

## Output Format

Each script outputs timed scenes:

```
[0-3s]  HOOK
        NARRATION: "Stop scrolling if you want to 10x your content"
        VISUAL: Close-up face, direct eye contact, hand gesture
        TEXT: "10X YOUR CONTENT 🚀"

[3-10s] SETUP
        NARRATION: "I found this AI tool that..."
        VISUAL: Screen recording of the tool
        TEXT: "this changed everything"

[10-25s] BODY
        NARRATION: "Here's exactly what I do..."
        VISUAL: Step-by-step demo with cuts every 3s
        TEXT: "Step 1: ..." / "Step 2: ..."

[25-30s] CTA
        NARRATION: "Follow for part 2"
        VISUAL: Point at camera, smile
        TEXT: "FOLLOW FOR MORE"
```

## Environment

Requires `ANTHROPIC_API_KEY` in `~/.clawdbot/.env` or environment.
