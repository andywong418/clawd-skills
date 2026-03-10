---
name: produce
description: End-to-end content production pipeline — topic or script → viral video → posted across platforms. Claude writes the script, voiceover narrates it, b-roll-finder fetches footage, video-assembler stitches it, cross-poster reformats for each platform, post-scheduler queues it. One command to go from idea to posted. Requires ANTHROPIC_API_KEY + FAL_API_KEY + PEXELS_API_KEY. Platform credentials needed for --post.
metadata: {"clawdbot":{"emoji":"🎬","requires":{"env":["ANTHROPIC_API_KEY","FAL_API_KEY","PEXELS_API_KEY"]}}}
---

# Produce

One command from topic to posted video. Claude writes the script, the pipeline handles everything else.

## Quick Start

```bash
# Idea → video (dry run first to see the script)
python3 skills/produce/scripts/produce.py \
  --from-trending "sleep hygiene tips" --dry-run

# Full pipeline: Claude writes script → produce → schedule for all 3 platforms
python3 skills/produce/scripts/produce.py \
  --from-trending "sleep hygiene tips" --schedule

# Produce + post immediately to TikTok + Instagram
python3 skills/produce/scripts/produce.py \
  --from-trending "AI tools that changed my workflow" \
  --platforms tiktok instagram --post

# Provide your own script (Claude still generates b-roll query)
python3 skills/produce/scripts/produce.py \
  --script "Did you know your phone is destroying your sleep?..."

# Full manual control
python3 skills/produce/scripts/produce.py \
  --script "5 things your doctor won't tell you about sleep..." \
  --broll "doctor office, person lying awake at night, alarm clock" \
  --platforms tiktok --schedule
```

## Options

| Flag | Default | Description |
|------|---------|-------------|
| `--from-trending TOPIC` | — | Claude writes a viral script about this topic |
| `--script TEXT` | — | Pre-written narration script |
| `--broll DESC` | auto | B-roll description (Claude generates if not set) |
| `--broll-count N` | 3 | Number of b-roll clips to fetch |
| `--music FILE` | — | Background music file (ducked) |
| `--no-subtitles` | false | Skip subtitle burning |
| `--platforms P...` | all | `tiktok` `instagram` `youtube` |
| `--post` | false | Post immediately after producing |
| `--schedule` | false | Queue at next optimal window |
| `--output DIR` | `./output/produce` | Output directory |
| `--dry-run` | false | Show script + plan, no video |

`--from-trending` and `--script` are mutually exclusive. One is required.

## Pipeline

```
--from-trending TOPIC
        │
        ▼
  [Claude — Haiku]
  Write viral script (hook-first, 30-60s spoken)
  + suggest b-roll search query
        │
        ▼
  [video-assembler]
  Narrate (Kokoro TTS via fal.ai)
  + fetch b-roll (Pexels)
  + concat + loop to match audio
  + burn subtitles (Wizper via fal.ai)
        │
        ▼
  [cross-poster]
  Crop/scale per platform
  Generate platform captions (Claude Haiku)
  └─ TikTok 1080×1920, max 3min
  └─ Instagram Reels 1080×1920, max 90s
  └─ YouTube Shorts 1080×1920, max 60s
        │
        ▼
  [post-scheduler]        ← --schedule or --post
  Queue at optimal times
  or post immediately
        │
        ▼
  output/produce/
    assembled_{ts}.mp4    ← source video with subtitles
    tiktok/
      video_tiktok.mp4
      video_caption.txt
    instagram/
      video_instagram.mp4
      video_caption.txt
    youtube/
      video_youtube.mp4
      video_caption.txt
```

## Cost per Video

| Step | Tool | Cost |
|------|------|------|
| Script writing | Claude Haiku | ~$0.001 |
| Voiceover (60s) | Kokoro via fal.ai | ~$0.00 (free tier) |
| B-roll (3 clips) | Pexels API | Free |
| Subtitle transcription | Wizper via fal.ai | ~$0.01 |
| Caption writing | Claude Haiku | ~$0.001 |
| **Total** | | **~$0.01–0.02** |

vs. video-director (Kling AI generation): ~$0.50–0.70 per video

## Environment

- `ANTHROPIC_API_KEY` — script + caption generation (required)
- `FAL_API_KEY` — voiceover + subtitle transcription (required)
- `PEXELS_API_KEY` — b-roll footage (required)
- Platform credentials — only for `--post` (see post-scheduler SKILL.md)
