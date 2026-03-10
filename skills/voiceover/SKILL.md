---
name: voiceover
description: Generate voiceover/narration audio from text using fal.ai. Two models — Kokoro (fast, 50+ voices, free) and MiniMax Speech-02 HD (higher quality, emotional control, $0.10/1k chars). Outputs MP3 ready for video-editor. Use when asked to add narration, voiceover, talking audio, or TTS to a video or script.
metadata: {"clawdbot":{"emoji":"🎙️","requires":{"env":["FAL_API_KEY"]}}}
---

# Voiceover

Generate narration audio from text via fal.ai. Outputs MP3 compatible with `video-editor`.

## Models

| Model | Quality | Speed | Cost | Best for |
|-------|---------|-------|------|---------|
| `kokoro` | Good | Fast | Free | Quick VO, many voices, multilingual |
| `minimax` | Excellent | Medium | $0.10/1k chars | Hero content, emotional delivery |

## Quick Start

```bash
# Basic — Kokoro default voice
python3 skills/voiceover/scripts/speak.py "Welcome to the future of AI."

# From script file
python3 skills/voiceover/scripts/speak.py --file script.txt

# Male voice, faster pace
python3 skills/voiceover/scripts/speak.py "Let's go!" --voice am_michael --speed 1.1

# MiniMax with emotion
python3 skills/voiceover/scripts/speak.py "I can't believe this works." \
  --model minimax --voice Lively_Girl --emotion surprised

# List all voices
python3 skills/voiceover/scripts/speak.py --list-voices
```

## Options

| Option | Default | Description |
|--------|---------|-------------|
| `text` | — | Text to speak (positional arg) |
| `--file` | — | Read text from file |
| `--model` | kokoro | `kokoro` or `minimax` |
| `--voice` | af_heart (kokoro) / Friendly_Person (minimax) | Voice ID |
| `--speed` | 1.0 | Speed: 0.5 (slow) to 2.0 (fast) |
| `--emotion` | — | MiniMax only: happy, sad, angry, fearful, disgusted, surprised, neutral |
| `--pitch` | 0 | MiniMax only: -12 to 12 semitones |
| `--output` | ./output/voiceover.mp3 | Output path |
| `--list-voices` | — | Print all voices and exit |

## Kokoro Voices (free)

| Voice | Description |
|-------|-------------|
| `af_heart` | Female, warm (default) |
| `af_bella` | Female, expressive |
| `af_nova` | Female, professional |
| `af_sarah` | Female, friendly |
| `am_michael` | Male, authoritative |
| `am_liam` | Male, casual |
| `am_echo` | Male, smooth |
| `bf_emma` | Female British, polished |
| `bm_george` | Male British, deep |

## MiniMax Voices ($0.10/1k chars)

| Voice | Description |
|-------|-------------|
| `Friendly_Person` | Upbeat, approachable (default) |
| `Wise_Woman` | Calm, authoritative |
| `Inspirational_girl` | Energetic, motivating |
| `Deep_Voice_Man` | Deep, powerful |
| `Calm_Woman` | Soothing, measured |
| `Casual_Guy` | Relaxed, conversational |
| `Lively_Girl` | Bright, enthusiastic |

## Pipeline with video-editor

```bash
# 1. Generate voiceover
python3 skills/voiceover/scripts/speak.py \
  "Five AI tools that will change your life forever." \
  --voice am_michael --speed 1.05 \
  --output ./audio/vo.mp3

# 2. Mix into video (mute original, add VO + background music)
python3 skills/video-editor/scripts/edit.py \
  --clips clip1.mp4 clip2.mp4 clip3.mp4 \
  --music trending_sound.mp3 \
  --music-volume 0.15 \
  --original-volume 0 \
  --output final.mp4

# Note: to layer VO + music, first mix VO into video, then add music
# Or use ffmpeg directly for 3-track mixing
```

## Environment

Requires `FAL_API_KEY` in `~/.clawdbot/.env` or environment.
