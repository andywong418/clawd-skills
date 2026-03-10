---
name: video-editor
description: Programmatic video editing via FFmpeg. Concatenate clips, mix audio tracks (original + background music + voiceover simultaneously), control per-track volume, fade in/out, burn text overlays, crop to aspect ratio. Use when asked to combine videos, add music, add voiceover, mix audio, assemble a final video, or do any post-production editing.
metadata: {"clawdbot":{"emoji":"🎬","requires":{"bins":["ffmpeg","ffprobe"]}}}
---

# Video Editor

Assemble and edit videos with full audio mixing — original audio, background music, and voiceover all simultaneously controllable.

## Quick Start

```bash
# Clips + background music
python3 skills/video-editor/scripts/edit.py \
  --clips clip1.mp4 clip2.mp4 \
  --music beat.mp3 --music-volume 0.2 \
  --output final.mp4

# Voiceover only (mute original audio)
python3 skills/video-editor/scripts/edit.py \
  --clips clip.mp4 \
  --voiceover narration.mp3 \
  --original-volume 0 \
  --output out.mp4

# Full 3-track mix: ducked original + music bed + narration VO
python3 skills/video-editor/scripts/edit.py \
  --clips clip1.mp4 clip2.mp4 \
  --music beat.mp3 --music-volume 0.12 \
  --voiceover vo.mp3 --vo-volume 1.0 \
  --original-volume 0.2 \
  --fade-in 0.5 --fade-out 1.0 \
  --output final.mp4

# From a JSON spec file
python3 skills/video-editor/scripts/edit.py --spec edit.json
```

## Audio Mixing

Up to 3 simultaneous audio tracks, mixed with `amix`:

| Track | Flag | Default Vol | Notes |
|-------|------|-------------|-------|
| Original clip audio | `--original-volume` | 1.0 | Set 0 to mute clips entirely |
| Background music | `--music` + `--music-volume` | 0.25 | Loops if shorter than video; trims if longer |
| Voiceover / narration | `--voiceover` + `--vo-volume` | 1.0 | Use with `voiceover` skill output |

Volume range: `0.0` (silent) → `1.0` (full) → `2.0+` (boost).

## All Options

| Option | Default | Description |
|--------|---------|-------------|
| `--clips` | required | One or more video files (concatenated in order) |
| `--music` | none | Background music file (mp3/wav/m4a) |
| `--music-volume` | 0.25 | Music track volume |
| `--voiceover` | none | Voiceover/narration audio file |
| `--vo-volume` | 1.0 | Voiceover track volume |
| `--original-volume` | 1.0 | Original clip audio volume (0 = mute) |
| `--fade-in` | 0 | Video + audio fade in (seconds) |
| `--fade-out` | 0 | Video + audio fade out (seconds) |
| `--text` | none | Text overlay burned into video |
| `--text-position` | bottom | top / center / bottom |
| `--aspect` | none | Force crop: 9:16, 16:9, 1:1 |
| `--output` | ./output/final.mp4 | Output file path |
| `--spec` | none | JSON spec file (overrides all flags) |

## JSON Spec Format

```json
{
  "clips": ["clip1.mp4", "clip2.mp4"],
  "music": "beat.mp3",
  "music_volume": 0.2,
  "voiceover": "vo.mp3",
  "vo_volume": 1.0,
  "original_audio_volume": 0.0,
  "fade_in": 0.5,
  "fade_out": 1.0,
  "text": "Follow for more",
  "text_position": "bottom",
  "aspect": "9:16",
  "output": "final.mp4"
}
```

## Pipelines

### UGC video with trending sound
```bash
# 1. Get trending sound
python3 skills/trending-sounds/scripts/trending.py --download --limit 1 --output ./sounds

# 2. Mix into UGC clip (music low, original audio intact)
python3 skills/video-editor/scripts/edit.py \
  --clips ugc_clip.mp4 \
  --music ./sounds/01_*.mp3 --music-volume 0.18 \
  --output ugc_final.mp4
```

### Script video with voiceover + music bed
```bash
# 1. Generate voiceover from script
python3 skills/voiceover/scripts/speak.py \
  "Five skincare products that actually changed my skin." \
  --voice af_nova --speed 1.05 --output ./vo.mp3

# 2. Assemble: mute original, VO loud, music quiet underneath
python3 skills/video-editor/scripts/edit.py \
  --clips broll1.mp4 broll2.mp4 broll3.mp4 \
  --voiceover ./vo.mp3 --vo-volume 1.0 \
  --music beat.mp3 --music-volume 0.12 \
  --original-volume 0 \
  --fade-in 0.3 --fade-out 0.8 \
  --output final.mp4
```

### Cross-post with captions
```bash
# 1. Edit video
python3 skills/video-editor/scripts/edit.py \
  --clips clip.mp4 --music beat.mp3 --output edited.mp4

# 2. Burn captions
python3 skills/subtitle-burner/scripts/burn.py edited.mp4 --output captioned.mp4

# 3. Cross-post to all platforms
python3 skills/cross-poster/scripts/cross_post.py captioned.mp4 "video description"
```

## Notes

- All clips are normalized to a common format before concatenation (prevents A/V sync issues)
- Music loops automatically if shorter than total video duration
- Music is trimmed if longer than total video duration
- Clips without audio get a silent track added so mixing works cleanly
- Requires `ffmpeg` and `ffprobe` in PATH
