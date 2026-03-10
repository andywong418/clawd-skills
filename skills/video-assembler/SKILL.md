---
name: video-assembler
description: Stitch video clips and audio into a final MP4 using ffmpeg. Concat or loop clips, mix voiceover + background music (ducked), optionally burn subtitles. Can orchestrate the full pipeline by calling voiceover + b-roll-finder as subprocesses. Use when asked to assemble, produce, or render a final video from components. Requires ffmpeg/ffprobe; FAL_API_KEY + PEXELS_API_KEY needed only for --narrate/--find-broll modes.
---

# Video Assembler

Assemble a final MP4 from clips + audio. Can operate on pre-made files or orchestrate the full pipeline (voiceover → b-roll → assemble → subtitles).

## Quick Start

```bash
# Pre-made clips + audio
python3 skills/video-assembler/scripts/assemble.py \
  --audio voiceover.mp3 --clips broll1.mp4 broll2.mp4 --output final.mp4

# Loop a single clip to match audio length
python3 skills/video-assembler/scripts/assemble.py \
  --audio voiceover.mp3 --loop broll.mp4 --output final.mp4

# Add ducked background music
python3 skills/video-assembler/scripts/assemble.py \
  --audio voiceover.mp3 --clips broll.mp4 --music trending.mp3 --output final.mp4

# Full pipeline: generate voiceover + find b-roll + assemble + subtitles
python3 skills/video-assembler/scripts/assemble.py \
  --narrate "Your script here" \
  --find-broll "coffee shop morning routine" \
  --subtitles \
  --output final.mp4
```

## Options

| Flag | Default | Description |
|------|---------|-------------|
| `--audio FILE` | — | Pre-made audio file (MP3/WAV) |
| `--narrate TEXT` | — | Text to speak (calls voiceover skill) |
| `--clips FILE...` | — | One or more video clips to concat |
| `--loop FILE` | — | Single clip to loop to audio duration |
| `--find-broll DESC` | — | Natural language description → calls b-roll-finder |
| `--broll-count N` | 3 | How many b-roll clips to fetch |
| `--music FILE` | — | Optional background music (ducked) |
| `--music-volume V` | 0.12 | Music volume 0.0–1.0 |
| `--subtitles` | False | Burn captions via subtitle-burner |
| `--subtitle-style` | tiktok | `tiktok` / `youtube` / `minimal` |
| `--output FILE` | auto | Output path |

Must provide `--audio` OR `--narrate` (not both).
Must provide `--clips`, `--loop`, OR `--find-broll` (not multiple).

## Pipeline

1. Resolve audio (pre-made or generate via voiceover skill)
2. Resolve clips (pre-made, or fetch via b-roll-finder skill)
3. Build background video (concat clips, loop if shorter than audio)
4. Mix audio (voiceover + optional ducked music)
5. Optionally burn subtitles (via subtitle-burner skill)
6. Output final MP4

## Output

Default: `./output/assembled/assembled_{timestamp}.mp4`
Progress/status printed to stderr. Final output path printed to stdout.

## Environment

- `FAL_API_KEY` — required only for `--narrate` or `--subtitles`
- `PEXELS_API_KEY` — required only for `--find-broll`
- `ANTHROPIC_API_KEY` — optional, improves b-roll search quality
