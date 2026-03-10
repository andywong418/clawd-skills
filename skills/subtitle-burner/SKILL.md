---
name: subtitle-burner
description: Auto-transcribe a video clip and burn TikTok-style captions directly into the video. Uses fal.ai Whisper for transcription, groups words into short phrases, and burns them with ffmpeg. Use when asked to add captions, subtitles, or text overlays to a video. Requires FAL_API_KEY and ffmpeg.
---

# Subtitle Burner

Transcribe a video and burn styled captions (TikTok big-text style) directly into the clip.

## Quick Start

```bash
# Default TikTok style (90pt white bold text, black outline)
python3 skills/subtitle-burner/scripts/burn.py clip.mp4

# YouTube style (70pt, positioned lower)
python3 skills/subtitle-burner/scripts/burn.py clip.mp4 --style youtube

# Custom output path
python3 skills/subtitle-burner/scripts/burn.py clip.mp4 --output captioned.mp4
```

## Options

| Option | Default | Description |
|--------|---------|-------------|
| `input` | required | Input video path |
| `--style` | tiktok | Caption style: `tiktok`, `youtube`, `minimal` |
| `--words` | 3 | Words per subtitle phrase (1-5) |
| `--lang` | en | Language code for transcription |
| `--output` | ./output/subtitled/ | Output path or directory |

## Caption Styles

| Style | Font Size | Position | Use For |
|-------|-----------|----------|---------|
| `tiktok` | 90pt | Bottom, pushed up | TikTok, Reels |
| `youtube` | 70pt | Bottom | YouTube Shorts, long-form |
| `minimal` | 55pt | Very bottom | Clean/editorial |

All styles: Arial bold, white text, black outline, centered.

## Pipeline

1. Extract audio (ffmpeg) — smaller upload than full video
2. Upload audio to fal.ai storage
3. Transcribe with `fal-ai/wizper` (word-level timestamps)
4. Group words into short phrases
5. Generate ASS subtitle file
6. Burn with ffmpeg `ass` filter

## Environment

- `FAL_API_KEY` — required (loaded from `~/.clawdbot/.env` or environment)
