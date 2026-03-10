#!/usr/bin/env python3
"""Video Assembler — stitch clips + audio into a final MP4 via ViralFarm API.

Submits a video assembly job to the ViralFarm API and polls until completion.
Supports text-to-speech narration or pre-made audio, clip concatenation,
background music mixing, and optional subtitle burning.

Usage examples:
  # Narrate text over clip URLs
  python3 assemble.py --narrate "Did you know your phone is ruining your sleep?" \
    --clips https://example.com/b1.mp4 https://example.com/b2.mp4 --output final.mp4

  # Pre-made audio with clips and background music
  python3 assemble.py --audio https://example.com/vo.mp3 \
    --clips https://example.com/bg.mp4 \
    --music https://example.com/music.mp3 --music-volume 0.12 --output final.mp4

  # With TikTok-style subtitles
  python3 assemble.py --narrate "Here are 5 tips for better sleep" \
    --clips https://example.com/b1.mp4 https://example.com/b2.mp4 \
    --subtitles --subtitle-style tiktok --output final.mp4

  # Fire and forget
  python3 assemble.py --narrate "Quick tip" \
    --clips https://example.com/bg.mp4 --no-wait
"""

import argparse, json, os, sys, time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def load_config():
    url = os.environ.get("VIRALFARM_API_URL")
    key = os.environ.get("VIRALFARM_API_KEY")
    if url and key: return url, key
    env_path = Path.home() / ".clawdbot" / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("VIRALFARM_API_URL=") and not url:
                    url = line.split("=", 1)[1].strip()
                elif line.startswith("VIRALFARM_API_KEY=") and not key:
                    key = line.split("=", 1)[1].strip()
    return url, key

def api_request(url, api_key, method="GET", data=None):
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    body = json.dumps(data).encode() if data else None
    req = Request(url, data=body, headers=headers, method=method)
    try:
        with urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except HTTPError as e:
        err_body = e.read().decode()
        try: msg = json.loads(err_body).get("error", err_body)
        except: msg = err_body
        print(f"API error ({e.code}): {msg}", file=sys.stderr); sys.exit(1)
    except URLError as e:
        print(f"Connection error: {e.reason}", file=sys.stderr); sys.exit(1)

def download_file(url, output_path):
    req = Request(url)
    with urlopen(req, timeout=120) as resp:
        with open(output_path, "wb") as f:
            f.write(resp.read())

def poll_job(api_url, api_key, job_id, timeout=600):
    start = time.time()
    while True:
        time.sleep(5)
        status = api_request(f"{api_url}/jobs/{job_id}", api_key)
        elapsed = int(time.time() - start)
        progress = status.get("progress", 0)
        msg = status.get("progressMessage", "")
        print(f"  [{elapsed}s] {status['status']} - {progress}% {msg}")
        if status["status"] == "completed":
            return status
        if status["status"] in ("failed", "cancelled"):
            print(f"\nJob {status['status']}: {status.get('error', 'Unknown')}", file=sys.stderr)
            sys.exit(1)
        if elapsed > timeout:
            print("\nTimed out", file=sys.stderr)
            sys.exit(1)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Assemble a video from clips + audio via ViralFarm API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 assemble.py --narrate "Script text here" \\
    --clips https://example.com/b1.mp4 https://example.com/b2.mp4 --output final.mp4

  python3 assemble.py --audio https://example.com/vo.mp3 \\
    --clips https://example.com/bg.mp4 --music https://example.com/music.mp3 --output final.mp4

  python3 assemble.py --narrate "5 tips" \\
    --clips https://example.com/b1.mp4 --subtitles --subtitle-style tiktok --output final.mp4

  python3 assemble.py --narrate "Quick" --clips https://example.com/bg.mp4 --no-wait
""",
    )

    # Audio source (mutually exclusive)
    audio_group = parser.add_mutually_exclusive_group(required=True)
    audio_group.add_argument("--narrate", metavar="TEXT",
                             help="Text to narrate (server generates voiceover)")
    audio_group.add_argument("--audio", metavar="URL",
                             help="Pre-made audio file URL (MP3/WAV)")

    # Clips
    parser.add_argument("--clips", nargs="+", required=True, metavar="URL",
                        help="One or more video clip URLs to concatenate")

    # Music
    parser.add_argument("--music", metavar="URL", default=None,
                        help="Optional background music URL (ducked under voiceover)")
    parser.add_argument("--music-volume", type=float, default=0.12, metavar="V",
                        dest="music_volume",
                        help="Music volume 0.0-1.0 (default: 0.12)")

    # Subtitles
    parser.add_argument("--subtitles", action="store_true",
                        help="Burn captions into the video")
    parser.add_argument("--subtitle-style", default="tiktok",
                        choices=["tiktok", "youtube", "minimal"],
                        dest="subtitle_style",
                        help="Caption style (default: tiktok)")

    # Output
    parser.add_argument("--output", metavar="FILE", default="./output/assembled.mp4",
                        help="Output file path (default: ./output/assembled.mp4)")
    parser.add_argument("--no-wait", action="store_true",
                        help="Submit job and exit without waiting for completion")

    args = parser.parse_args()

    api_url, api_key = load_config()
    if not api_url or not api_key:
        print("Error: VIRALFARM_API_URL and VIRALFARM_API_KEY must be set "
              "(env vars or ~/.clawdbot/.env)", file=sys.stderr)
        sys.exit(1)

    # Build request payload
    payload = {
        "clips": args.clips,
    }
    if args.narrate:
        payload["narrate"] = args.narrate
    if args.audio:
        payload["audioUrl"] = args.audio
    if args.music:
        payload["music"] = args.music
        payload["musicVolume"] = args.music_volume
    if args.subtitles:
        payload["subtitles"] = True
        payload["subtitleStyle"] = args.subtitle_style

    # Submit job
    print(f"Submitting video assembly job ({len(args.clips)} clip(s))...")
    result = api_request(f"{api_url}/video/assemble", api_key, method="POST", data=payload)
    job_id = result["id"]
    print(f"Job created: {job_id}")

    if args.no_wait:
        print(f"Job submitted. Poll status at: {api_url}/jobs/{job_id}")
        return

    # Poll until completion
    print("Waiting for job to complete...")
    status = poll_job(api_url, api_key, job_id)

    # Download result
    video_url = status["output"]["videoUrl"]
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading result to {output_path}...")
    download_file(video_url, str(output_path))
    print(f"\nDone: {output_path}")


if __name__ == "__main__":
    main()
