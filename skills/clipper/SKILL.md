---
name: clipper
description: Find viral moments in videos and cut clips with subtitles via API.
metadata: {"clawdbot":{"emoji":"✂️","requires":{"bins":["python3"],"env":[]}}}
---

# Clipper Skill

## ⚠️ CRITICAL RULES
- **NEVER download videos locally.** The API server handles all downloading.
- **NEVER run ffmpeg locally.** The API server handles all video processing.
- **NEVER use yt-dlp, cobalt, pytubefix, or any download tool locally.**
- You MUST use `batch_clips.py` to submit clips to the API. That is the ONLY way to cut clips.

## Workflow

### Step 1: Get the transcript

Use YouTube's caption/transcript API or ask the user for a transcript. Do NOT download the video to transcribe it. For YouTube, you can use the YouTube Data API or scrape captions:

```bash
# For YouTube: get auto-generated captions via yt-dlp (captions only, no video download)
yt-dlp --skip-download --write-auto-sub --sub-lang en --sub-format json3 \
  -o "/root/clawd/clips/subs" "VIDEO_URL" 2>/dev/null

# Or use the RapidAPI transcript endpoint:
VIDEO_ID="XXXXXXXXXXX"  # extract from YouTube URL
curl -s "https://youtube-media-downloader.p.rapidapi.com/v2/video/subtitles?videoId=$VIDEO_ID" \
  -H "x-rapidapi-key: 9f1125f9efmshdd74e372e4c5bbfp18f0d8jsn883283c7228b" \
  -H "x-rapidapi-host: youtube-media-downloader.p.rapidapi.com" \
  -o /root/clawd/clips/captions.json
```

If you cannot get a transcript, analyze the video title/description to identify likely clip segments, or ask the user for timestamps.

### Step 2: Analyze transcript and pick clips

Read the FULL transcript. Find the most viral/insightful moments:
- Strong hooks / opening statements
- Controversial or surprising claims
- Emotional moments / personal stories
- Quotable statements

Target: 5-15 clips per hour of content (30-60 seconds each)

### Step 3: Create SRT subtitle files (optional)

If you have word-level timestamps, create SRT files for each clip:
```
/root/clawd/clips/clip_01.srt
/root/clawd/clips/clip_02.srt
```

### Step 4: Submit clips to the API

Create a manifest and run `batch_clips.py`. This sends the job to the ViralFarm API server which downloads the video, cuts the clips with ffmpeg, burns subtitles, and uploads to S3.

```bash
mkdir -p /root/clawd/clips

# Create manifest with the ORIGINAL video URL (YouTube URL is fine)
cat > /root/clawd/clips/manifest.json << 'EOF'
[
  {
    "input": "https://www.youtube.com/watch?v=VIDEO_ID",
    "output": "clip_01_final.mp4",
    "start": "00:01:30",
    "end": "00:02:15",
    "srt": "/root/clawd/clips/clip_01.srt"
  },
  {
    "input": "https://www.youtube.com/watch?v=VIDEO_ID",
    "output": "clip_02_final.mp4",
    "start": "00:05:10",
    "end": "00:05:55",
    "srt": "/root/clawd/clips/clip_02.srt"
  }
]
EOF

# Submit to API (downloads + cuts + uploads happen on the server)
python3 /root/clawd/skills/clipper/scripts/batch_clips.py \
  /root/clawd/clips/manifest.json \
  --output /root/clawd/clips \
  --workers 3
```

**Manifest fields:**
- `input` — the original video URL, e.g. YouTube URL (required). NOT a local path.
- `output` — output filename (required)
- `start` — start time as HH:MM:SS or seconds (required)
- `end` — end time (required)
- `srt` — local SRT file path (optional, contents sent to API for subtitle burn)

### Step 5: Upload clips to Slack

After `batch_clips.py` completes, upload each clip from `/root/clawd/clips/` to the Slack thread.

## RapidAPI Key
`9f1125f9efmshdd74e372e4c5bbfp18f0d8jsn883283c7228b`
