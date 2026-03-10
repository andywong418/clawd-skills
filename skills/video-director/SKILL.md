---
name: video-director
description: Full pipeline — text concept → shot list → Kling clips → assembled video + caption. Orchestrates fal-video, video-editor, trending-sounds, and caption-writer automatically. Use when asked to create a full video from a text prompt or concept.
metadata: {"clawdbot":{"emoji":"🎬","requires":{"env":["ANTHROPIC_API_KEY","FAL_API_KEY"]}}}
---

# Video Director

One command from concept to finished video. Claude writes the shot list using Kling best practices, generates clips in parallel, assembles with trending music, and writes a caption.

## Quick Start

```bash
# Full pipeline — concept → video + caption
python3 skills/video-director/scripts/direct.py \
  "30 second reel about 5 AI tools that will blow your mind"

# See shot list before spending Kling credits
python3 skills/video-director/scripts/direct.py \
  "barber meme with a celebrity reveal" --dry-run

# TikTok format, 4 scenes
python3 skills/video-director/scripts/direct.py \
  "cat chef cooking pasta, absurdist funny" \
  --platform tiktok --scenes 4

# Bring your own music
python3 skills/video-director/scripts/direct.py \
  "motivational quote video" --music ./sounds/track.mp3 --music-volume 0.2

# No music
python3 skills/video-director/scripts/direct.py "product reveal" --no-music
```

## Options

| Option | Default | Description |
|--------|---------|-------------|
| `concept` | required | What the video is about |
| `--platform` | instagram | `instagram`, `tiktok`, `youtube`, `twitter` |
| `--scenes` | 3 | Number of clips to generate (3–5 recommended) |
| `--music` | — | Path to music file (skips trending-sounds fetch) |
| `--music-volume` | 0.25 | Music volume 0.0–1.0 |
| `--no-music` | false | Skip music entirely |
| `--output` | ./output | Output directory |
| `--dry-run` | false | Show shot list only, don't generate video |

## Pipeline

```
concept
  │
  ▼
[Claude — claude-sonnet-4-6]
  Write shot list using kling-prompt-guide.md
  (3–5 scenes, each with duration, Kling prompt, description)
  │
  ▼
[fal.ai — Kling v2/master]
  Generate all clips in PARALLEL
  (5 or 10 seconds each, 9:16 vertical)
  │
  ▼
[trending-sounds]  ←── optional, fetches #1 trending TikTok sound
  │
  ▼
[video-editor]
  Stitch clips → add music → fade out → 9:16 crop
  │
  ▼
[caption-writer]
  Platform-optimized caption + hashtags
  │
  ▼
output/
  final.mp4       ← ready to post
  caption.txt     ← ready to paste
  clips/          ← individual scene clips
  shot_list.json  ← Claude's shot list (dry-run only)
```

## Output

```
output/
  final.mp4
  caption.txt
  clips/
    scene_01.mp4
    scene_02.mp4
    scene_03.mp4
  sounds/
    01_trending_track.mp3
```

## Kling Prompt Guide

`skills/video-director/kling-prompt-guide.md` — Claude reads this before writing every shot list. Contains:
- Prompt structure and length guidelines
- Camera movement terminology
- Shot types and framing
- Style keywords that work
- Image-to-video vs text-to-video rules
- Common mistakes to avoid
- Prompt templates by vibe

Edit this file to tune how Claude writes prompts.

## Environment

- `ANTHROPIC_API_KEY` — for shot list + caption generation
- `FAL_API_KEY` — for Kling video generation
- `ads.tiktok.com` cookies optional — unlocks 100 trending sounds (vs top 3)

## Cost Estimate (per video)

| Step | Cost |
|------|------|
| Shot list (Claude Sonnet) | ~$0.01 |
| 3× Kling clips (v2/master, 5s) | ~$0.30–0.60 |
| Caption (Claude Haiku) | <$0.01 |
| **Total** | **~$0.35–0.70 per video** |
