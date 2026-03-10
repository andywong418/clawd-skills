#!/usr/bin/env python3
"""Video Director — text prompt → full video via Claude shot list + Kling + video-editor.

Pipeline:
  1. Claude writes a shot list (scene descriptions + Kling prompts)
  2. Kling generates all clips in parallel via fal.ai
  3. video-editor assembles clips + trending music
  4. caption-writer generates a ready-to-post caption

Usage:
    python3 direct.py "30 second reel about 5 AI tools, mindblowing vibe"
    python3 direct.py "barber meme with celebrity reveal" --platform tiktok
    python3 direct.py "cat chef cooking pasta" --scenes 3 --music ./sounds/track.mp3
    python3 direct.py "motivational quote video" --no-music --voiceover
"""

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import anthropic


# ---------------------------------------------------------------------------
# Env loader
# ---------------------------------------------------------------------------

def _load_env(key: str) -> str | None:
    val = os.environ.get(key)
    if val:
        return val
    env_path = Path.home() / ".clawdbot" / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith(f"{key}="):
                    return line.split("=", 1)[1].strip()
    return None


# ---------------------------------------------------------------------------
# Kling prompt guide (loaded once, injected into Claude system prompt)
# ---------------------------------------------------------------------------

GUIDE_PATH = Path(__file__).parent.parent / "kling-prompt-guide.md"

def load_guide() -> str:
    if GUIDE_PATH.exists():
        return GUIDE_PATH.read_text()
    return ""


# ---------------------------------------------------------------------------
# Step 1: Claude writes the shot list
# ---------------------------------------------------------------------------

SHOT_LIST_SCHEMA = """
{
  "title": "short title for this video",
  "vibe": "one word mood",
  "platform": "instagram|tiktok|youtube|twitter",
  "scenes": [
    {
      "scene": 1,
      "duration": 5,
      "type": "text-to-video | image-to-video",
      "kling_prompt": "full Kling prompt following the guide",
      "negative_prompt": "optional negative prompt or empty string",
      "description": "one line plain-english description of what happens"
    }
  ],
  "caption_topic": "brief description for caption-writer",
  "music_vibe": "upbeat|chill|dramatic|hype|none — describes what music fits"
}
"""

def write_shot_list(
    concept: str,
    platform: str,
    num_scenes: int,
    client: anthropic.Anthropic,
) -> dict:
    guide = load_guide()

    system = f"""You are an expert AI video director who creates viral short-form videos.
You write shot lists for Kling AI video generation following the prompt guide below.

KLING PROMPT GUIDE:
{guide}

Rules:
- Each scene is ONE clip (5 or 10 seconds). No multi-scene clips.
- Write Kling prompts in the exact style from the guide (30-60 words, director language).
- Choose text-to-video for pure AI scenes. image-to-video only when you have a reference (rare).
- All clips should be 9:16 vertical for social media.
- Vary camera movements between scenes — don't use the same move twice.
- The sequence should tell a story or build toward a payoff.
- Return ONLY valid JSON matching the schema. No other text."""

    user = f"""Create a shot list for this video concept:

"{concept}"

Platform: {platform}
Number of scenes: {num_scenes}

Return JSON matching this schema:
{SHOT_LIST_SCHEMA}"""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=system,
        messages=[{"role": "user", "content": user}]
    )

    raw = message.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    return json.loads(raw)


# ---------------------------------------------------------------------------
# Step 2: Generate clips with Kling via fal.ai
# ---------------------------------------------------------------------------

FAL_BASE = "https://fal.run"
KLING_MODEL = "fal-ai/kling-video/v2/master/text-to-video"


def submit_clip(scene: dict, api_key: str) -> tuple[int, str]:
    """Submit a Kling generation job. Returns (scene_num, request_id)."""
    endpoint = KLING_MODEL
    payload = {
        "prompt": scene["kling_prompt"],
        "duration": str(scene["duration"]),
        "aspect_ratio": "9:16",
    }
    if scene.get("negative_prompt"):
        payload["negative_prompt"] = scene["negative_prompt"]

    url = f"{FAL_BASE}/{endpoint}"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Key {api_key}",
            "Content-Type": "application/json",
        },
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read())

    # fal.ai returns video URL directly for sync calls
    video_url = (
        result.get("video", {}).get("url")
        or result.get("videos", [{}])[0].get("url")
    )
    if not video_url:
        raise RuntimeError(f"No video URL in response: {json.dumps(result)[:300]}")

    return scene["scene"], video_url


def download_clip(video_url: str, out_path: Path):
    req = urllib.request.Request(video_url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        out_path.write_bytes(resp.read())


def generate_clips(scenes: list[dict], output_dir: Path, api_key: str) -> dict[int, Path]:
    """Generate all clips in parallel. Returns {scene_num: local_path}."""
    output_dir.mkdir(parents=True, exist_ok=True)
    results = {}

    print(f"\n[director] Submitting {len(scenes)} clip(s) to Kling (parallel)...")

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(submit_clip, scene, api_key): scene
            for scene in scenes
        }
        for future in as_completed(futures):
            scene = futures[future]
            try:
                scene_num, video_url = future.result()
                out_path = output_dir / f"scene_{scene_num:02d}.mp4"
                print(f"  [scene {scene_num}] Downloading...")
                download_clip(video_url, out_path)
                results[scene_num] = out_path
                print(f"  [scene {scene_num}] ✓ {out_path.name}")
            except Exception as e:
                print(f"  [scene {scene['scene']}] FAILED: {e}", file=sys.stderr)

    return results


# ---------------------------------------------------------------------------
# Step 3: Assemble with video-editor
# ---------------------------------------------------------------------------

def find_script(name: str) -> Path:
    """Find a sibling skill script."""
    base = Path(__file__).parent.parent.parent
    path = base / name
    if not path.exists():
        raise FileNotFoundError(f"Script not found: {path}")
    return path


def assemble_video(
    clip_paths: list[Path],
    output_path: Path,
    music_path: Path | None,
    music_volume: float,
) -> Path:
    editor = find_script("video-editor/scripts/edit.py")
    cmd = [
        sys.executable, str(editor),
        "--clips", *[str(p) for p in clip_paths],
        "--aspect", "9:16",
        "--fade-out", "1.0",
        "--output", str(output_path),
    ]
    if music_path and music_path.exists():
        cmd += ["--music", str(music_path), "--music-volume", str(music_volume)]

    print(f"\n[director] Assembling {len(clip_paths)} clip(s)...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"video-editor failed:\n{result.stderr[-1000:]}")
    return output_path


# ---------------------------------------------------------------------------
# Step 4: Get trending music
# ---------------------------------------------------------------------------

def get_trending_music(output_dir: Path) -> Path | None:
    try:
        trending = find_script("trending-sounds/scripts/trending.py")
    except FileNotFoundError:
        return None

    sounds_dir = output_dir / "sounds"
    sounds_dir.mkdir(exist_ok=True)

    print("\n[director] Fetching trending sound...")
    result = subprocess.run(
        [sys.executable, str(trending), "--download", "--limit", "1", "--output", str(sounds_dir)],
        capture_output=True, text=True, timeout=120
    )
    if result.returncode != 0:
        print(f"  [warning] Could not fetch trending sound: {result.stderr[:200]}")
        return None

    mp3s = list(sounds_dir.glob("*.mp3"))
    return mp3s[0] if mp3s else None


# ---------------------------------------------------------------------------
# Step 5: Generate caption
# ---------------------------------------------------------------------------

def generate_caption(topic: str, platform: str) -> str | None:
    try:
        writer = find_script("caption-writer/scripts/write.py")
    except FileNotFoundError:
        return None

    result = subprocess.run(
        [sys.executable, str(writer), topic, "--platform", platform, "--json"],
        capture_output=True, text=True, timeout=30
    )
    if result.returncode != 0:
        return None

    try:
        captions = json.loads(result.stdout)
        return captions[0]["full_caption"]
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="AI Video Director — concept → full video")
    parser.add_argument("concept", help="Video concept or topic")
    parser.add_argument("--platform", "-p", default="instagram",
                        choices=["instagram", "tiktok", "youtube", "twitter"],
                        help="Target platform (default: instagram)")
    parser.add_argument("--scenes", "-n", type=int, default=3,
                        help="Number of scenes/clips (default: 3)")
    parser.add_argument("--music", help="Path to music file (skips trending-sounds fetch)")
    parser.add_argument("--music-volume", type=float, default=0.25,
                        help="Music volume 0.0–1.0 (default: 0.25)")
    parser.add_argument("--no-music", action="store_true", help="Skip music entirely")
    parser.add_argument("--output", "-o", default="./output",
                        help="Output directory (default: ./output)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show shot list only, don't generate videos")
    args = parser.parse_args()

    anthropic_key = _load_env("ANTHROPIC_API_KEY")
    fal_key = _load_env("FAL_API_KEY")

    if not anthropic_key:
        print("ERROR: ANTHROPIC_API_KEY not found", file=sys.stderr)
        sys.exit(1)
    if not fal_key and not args.dry_run:
        print("ERROR: FAL_API_KEY not found", file=sys.stderr)
        sys.exit(1)

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    client = anthropic.Anthropic(api_key=anthropic_key)

    # ── Step 1: Shot list ──────────────────────────────────────────────────
    print(f"\n[director] Writing shot list for: \"{args.concept}\"")
    shot_list = write_shot_list(args.concept, args.platform, args.scenes, client)

    print(f"\n{'─' * 60}")
    print(f"  {shot_list['title']}")
    print(f"  Vibe: {shot_list['vibe']} · Platform: {shot_list['platform']}")
    print(f"{'─' * 60}")
    for scene in shot_list["scenes"]:
        print(f"\n  Scene {scene['scene']} ({scene['duration']}s) — {scene['description']}")
        print(f"  Prompt: {scene['kling_prompt'][:100]}...")
    print(f"\n  Music vibe: {shot_list.get('music_vibe', 'n/a')}")
    print(f"{'─' * 60}\n")

    if args.dry_run:
        print("[director] Dry run — shot list written. Not generating clips.")
        shot_list_path = output_dir / "shot_list.json"
        shot_list_path.write_text(json.dumps(shot_list, indent=2))
        print(f"[director] Shot list saved to {shot_list_path}")
        return

    # ── Step 2: Generate clips ─────────────────────────────────────────────
    clips_dir = output_dir / "clips"
    clip_results = generate_clips(shot_list["scenes"], clips_dir, fal_key)

    if not clip_results:
        print("ERROR: No clips were generated successfully", file=sys.stderr)
        sys.exit(1)

    # Sort by scene number
    ordered_clips = [clip_results[n] for n in sorted(clip_results.keys())]
    print(f"\n[director] {len(ordered_clips)}/{len(shot_list['scenes'])} clips generated")

    # ── Step 3: Music ──────────────────────────────────────────────────────
    music_path = None
    if not args.no_music:
        if args.music:
            music_path = Path(args.music)
            print(f"\n[director] Using provided music: {music_path.name}")
        else:
            music_path = get_trending_music(output_dir)
            if music_path:
                print(f"  Using: {music_path.name}")
            else:
                print("  No music — assembling without audio track")

    # ── Step 4: Assemble ───────────────────────────────────────────────────
    final_path = output_dir / "final.mp4"
    assemble_video(ordered_clips, final_path, music_path, args.music_volume)

    # ── Step 5: Caption ────────────────────────────────────────────────────
    print(f"\n[director] Generating caption...")
    caption = generate_caption(shot_list.get("caption_topic", args.concept), args.platform)
    if caption:
        caption_path = output_dir / "caption.txt"
        caption_path.write_text(caption)
        print(f"\n{'─' * 60}")
        print("  CAPTION:")
        print(f"{'─' * 60}")
        for line in caption.splitlines():
            print(f"  {line}")
        print(f"{'─' * 60}")

    # ── Done ───────────────────────────────────────────────────────────────
    print(f"\n[director] Done!")
    print(f"  Video:   {final_path}")
    if caption:
        print(f"  Caption: {output_dir / 'caption.txt'}")
    print(f"  Clips:   {clips_dir}/\n")


if __name__ == "__main__":
    main()
