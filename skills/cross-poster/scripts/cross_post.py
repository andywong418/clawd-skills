#!/usr/bin/env python3
"""Cross-poster — reformat one video for TikTok, IG Reels, and YouTube Shorts.

Steps per platform:
  1. Smart center-crop to 9:16 (if not already vertical)
  2. Scale to 1080x1920, enforce platform duration limit
  3. Re-encode H.264/AAC
  4. Generate platform-specific caption via Claude
  5. Optionally post immediately via post-scheduler
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
import urllib.request
import urllib.error

PLATFORMS = {
    "tiktok": {
        "label":            "TikTok",
        "max_duration":     180,
        "width":            1080,
        "height":           1920,
        "fps":              30,
        "caption_style":    "tiktok",
    },
    "instagram": {
        "label":            "IG Reels",
        "max_duration":     90,
        "width":            1080,
        "height":           1920,
        "fps":              30,
        "caption_style":    "instagram",
    },
    "youtube": {
        "label":            "YouTube Shorts",
        "max_duration":     60,
        "width":            1080,
        "height":           1920,
        "fps":              30,
        "caption_style":    "youtube",
    },
}

CAPTION_PROMPTS = {
    "tiktok": (
        "Write a TikTok caption. Rules:\n"
        "- 2-3 short punchy lines\n"
        "- 2-4 emojis placed naturally\n"
        "- End with 5-8 content-specific hashtags on a new line\n"
        "- Conversational, Gen-Z energy, feels typed fast\n"
        "- Max 150 chars before hashtags\n"
        "Output ONLY the caption text."
    ),
    "instagram": (
        "Write an Instagram Reels caption. Rules:\n"
        "- 3-5 lines, warm and personal\n"
        "- 2-3 emojis placed naturally\n"
        "- End with a soft CTA (save this, share with a friend, etc.)\n"
        "- 10-15 targeted hashtags on a new line (niche + medium + broad)\n"
        "Output ONLY the caption text."
    ),
    "youtube": (
        "Write a YouTube Shorts title AND description. Rules:\n"
        "Line 1 (TITLE): max 70 chars, curiosity-gap or value-forward, no clickbait\n"
        "Blank line\n"
        "Description: 2-3 sentences expanding on the video with natural keywords\n"
        "End with: #Shorts plus 3-5 relevant hashtags\n"
        "Output ONLY: title on line 1, blank line, description. Nothing else."
    ),
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def probe(path: str) -> dict:
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json",
         "-show_streams", "-show_format", path],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr}")
    data = json.loads(result.stdout)
    info = {"duration": 0.0, "width": 0, "height": 0, "has_audio": False}
    for s in data.get("streams", []):
        if s.get("codec_type") == "video":
            info["width"] = int(s.get("width", 0))
            info["height"] = int(s.get("height", 0))
            dur = float(s.get("duration") or data.get("format", {}).get("duration") or 0)
            info["duration"] = max(info["duration"], dur)
        elif s.get("codec_type") == "audio":
            info["has_audio"] = True
    if not info["duration"]:
        info["duration"] = float(data.get("format", {}).get("duration", 0))
    return info


def load_api_key() -> str | None:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        return key
    env_path = Path.home() / ".clawdbot" / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                if line.startswith("ANTHROPIC_API_KEY="):
                    return line.split("=", 1)[1].strip()
    return None


def generate_caption(context: str, platform: str, api_key: str) -> str:
    prompt = f"{CAPTION_PROMPTS[platform]}\n\nVideo context: {context}"
    payload = {
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 500,
        "messages": [{"role": "user", "content": prompt}],
    }
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(payload).encode(),
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode())
        return result["content"][0]["text"].strip()
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Claude API {e.code}: {e.read().decode()}")


# ---------------------------------------------------------------------------
# FFmpeg processing
# ---------------------------------------------------------------------------

def process_video(input_path: str, info: dict, platform: str,
                  output_dir: Path, trim: bool = True) -> Path:
    spec = PLATFORMS[platform]
    target_w, target_h = spec["width"], spec["height"]
    src_w, src_h = info["width"], info["height"]
    duration = info["duration"]

    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"{Path(input_path).stem}_{platform}.mp4"

    filters = []

    # Crop to 9:16 if needed
    target_ratio = target_w / target_h   # 0.5625
    src_ratio = src_w / src_h if src_h else 1

    if abs(src_ratio - target_ratio) > 0.01:
        if src_ratio > target_ratio:
            crop_w = int(src_h * target_ratio)
            filters.append(f"crop={crop_w}:{src_h}:{(src_w - crop_w) // 2}:0")
        else:
            crop_h = int(src_w / target_ratio)
            filters.append(f"crop={src_w}:{crop_h}:0:{(src_h - crop_h) // 2}")

    filters.append(f"scale={target_w}:{target_h}:flags=lanczos")
    filters.append(f"fps={spec['fps']}")

    trim_args = []
    if trim and duration > spec["max_duration"]:
        print(f"  Trimming {duration:.0f}s → {spec['max_duration']}s")
        trim_args = ["-t", str(spec["max_duration"])]

    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        *trim_args,
        "-vf", ",".join(filters),
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-profile:v", "high", "-level", "4.0",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
    ]
    if info["has_audio"]:
        cmd += ["-c:a", "aac", "-b:a", "128k", "-ar", "44100"]
    else:
        cmd += ["-an"]
    cmd.append(str(out_path))

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg error: {result.stderr[-1000:]}")

    return out_path


# ---------------------------------------------------------------------------
# Posting
# ---------------------------------------------------------------------------

def post_to_platform(platform: str, video_path: str, caption: str,
                     privacy: str = "public") -> str:
    """Post video to the platform. Returns result ID."""
    scheduler_dir = Path(__file__).parent.parent.parent.parent / "post-scheduler" / "scripts"
    sys.path.insert(0, str(scheduler_dir))

    if platform == "tiktok":
        from platforms.tiktok import post_video
        return post_video(video_path, caption)

    elif platform == "instagram":
        from platforms.instagram import post_reel
        return post_reel(video_path, caption)

    elif platform == "youtube":
        from platforms.youtube import upload_video
        lines = caption.strip().split("\n", 1)
        title = lines[0].strip()
        description = lines[1].strip() if len(lines) > 1 else ""
        tags = [w.lstrip("#") for w in caption.split() if w.startswith("#")]
        return upload_video(
            video_path=video_path,
            title=title,
            description=description,
            tags=tags,
            privacy=privacy,
            is_shorts=True,
        )

    raise ValueError(f"Unknown platform: {platform}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Reformat one video for TikTok, IG Reels, and YouTube Shorts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Reformat + generate captions for all 3 platforms
  python3 cross_post.py video.mp4 "girl doing morning skincare routine"

  # Reformat AND post immediately to all platforms
  python3 cross_post.py video.mp4 "skincare review" --post

  # Only TikTok and Instagram
  python3 cross_post.py video.mp4 "travel vlog" --platforms tiktok instagram

  # No captions, no posting — just the reformatted files
  python3 cross_post.py video.mp4 --no-captions
""",
    )
    parser.add_argument("video", help="Input video file")
    parser.add_argument("context", nargs="?", default="",
                        help="Brief video description for caption generation")
    parser.add_argument("--platforms", nargs="+",
                        choices=list(PLATFORMS.keys()),
                        default=list(PLATFORMS.keys()),
                        help="Target platforms (default: all three)")
    parser.add_argument("--no-captions", action="store_true",
                        help="Skip Claude caption generation")
    parser.add_argument("--no-trim", action="store_true",
                        help="Don't trim to platform duration limits")
    parser.add_argument("--post", action="store_true",
                        help="Post to platforms immediately after processing")
    parser.add_argument("--privacy", choices=["public", "private", "unlisted"],
                        default="public", help="YouTube privacy setting (default: public)")
    parser.add_argument("--output", type=str, default="./output")

    args = parser.parse_args()

    if not Path(args.video).exists():
        print(f"Error: video not found: {args.video}", file=sys.stderr)
        sys.exit(1)

    output_base = Path(args.output)

    print(f"Probing: {args.video}")
    info = probe(args.video)
    print(f"  {info['width']}x{info['height']}, {info['duration']:.1f}s, "
          f"audio={'yes' if info['has_audio'] else 'no'}\n")

    api_key = None
    if not args.no_captions and args.context:
        api_key = load_api_key()
        if not api_key:
            print("Warning: ANTHROPIC_API_KEY not found — skipping captions\n", file=sys.stderr)

    results = {}

    for platform in args.platforms:
        spec = PLATFORMS[platform]
        print(f"[{spec['label']}]")

        try:
            out_path = process_video(
                args.video, info, platform,
                output_dir=output_base / platform,
                trim=not args.no_trim,
            )
            results[platform] = {"video": str(out_path)}
            print(f"  Saved: {out_path}")
        except Exception as e:
            print(f"  Error: {e}", file=sys.stderr)
            results[platform] = {"error": str(e)}
            continue

        if api_key and args.context:
            try:
                caption = generate_caption(args.context, platform, api_key)
                results[platform]["caption"] = caption
                cap_path = output_base / platform / f"{Path(args.video).stem}_caption.txt"
                cap_path.write_text(caption)
                preview = caption.split("\n")[0][:60]
                print(f"  Caption: {preview}...")
            except Exception as e:
                print(f"  Caption error: {e}", file=sys.stderr)

        if args.post and "video" in results[platform]:
            caption = results[platform].get("caption", args.context or "")
            try:
                print(f"  Posting to {platform}...")
                result_id = post_to_platform(platform, results[platform]["video"],
                                             caption, privacy=args.privacy)
                results[platform]["posted"] = result_id
                print(f"  Posted: {result_id}")
            except Exception as e:
                print(f"  Post failed: {e}", file=sys.stderr)
                results[platform]["post_error"] = str(e)

        print()

    # Summary
    print("=" * 50)
    print("Summary\n")
    for platform, result in results.items():
        label = PLATFORMS[platform]["label"]
        if "error" in result:
            print(f"  {label}: FAILED — {result['error']}")
        else:
            print(f"  {label}: {result['video']}")
            if result.get("posted"):
                print(f"    Posted: {result['posted']}")
            elif not args.post:
                # Show scheduling hint
                cap_line = result.get("caption", "").split("\n")[0]
                caption_arg = f'"{cap_line}"' if cap_line else '"<caption>"'
                if platform != "youtube":
                    print(f"    Schedule: python3 skills/post-scheduler/scripts/queue.py "
                          f"add {platform} {result['video']} {caption_arg} --optimal")
                else:
                    print(f"    Schedule: python3 skills/post-scheduler/scripts/queue.py "
                          f"add youtube {result['video']} {caption_arg} --optimal")


if __name__ == "__main__":
    main()
