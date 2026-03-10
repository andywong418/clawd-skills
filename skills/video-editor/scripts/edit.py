#!/usr/bin/env python3
"""Video editor — assemble clips, mix audio tracks, burn text overlays via ViralFarm API.

Submits a video editing job to the ViralFarm API and polls until completion.
Supports up to 3 audio tracks (original, music, voiceover) and text overlays.

Usage examples:
  # Concatenate clips with background music
  python3 edit.py --clips https://example.com/a.mp4 https://example.com/b.mp4 \
    --music https://example.com/beat.mp3 --volume-music 0.2 --output final.mp4

  # Voiceover only (mute original)
  python3 edit.py --clips https://example.com/clip.mp4 \
    --voiceover https://example.com/vo.mp3 --volume-original 0 --output out.mp4

  # Full mix: original audio low + music + voiceover
  python3 edit.py --clips https://example.com/clip.mp4 \
    --music https://example.com/beat.mp3 --volume-music 0.15 \
    --voiceover https://example.com/narration.mp3 --volume-voiceover 1.0 \
    --volume-original 0.3 --output final.mp4

  # With text overlay and forced aspect ratio
  python3 edit.py --clips https://example.com/a.mp4 \
    --text "Subscribe" --text-position bottom \
    --aspect 9:16 --output vertical.mp4

  # Fire and forget (don't wait for completion)
  python3 edit.py --clips https://example.com/a.mp4 --no-wait
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
        description="Edit video via ViralFarm API — clips, audio mixing, text overlays",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 edit.py --clips https://example.com/a.mp4 https://example.com/b.mp4 \\
    --music https://example.com/beat.mp3 --volume-music 0.2 --output final.mp4

  python3 edit.py --clips https://example.com/clip.mp4 \\
    --voiceover https://example.com/vo.mp3 --volume-original 0 --output out.mp4

  python3 edit.py --clips https://example.com/clip.mp4 \\
    --text "Subscribe" --text-position bottom --aspect 9:16 --output vertical.mp4

  python3 edit.py --clips https://example.com/a.mp4 --no-wait
""",
    )

    parser.add_argument("--clips", nargs="+", required=True,
                        help="Input video clip URL(s)")
    parser.add_argument("--music", type=str, default=None,
                        help="Background music URL (mp3/wav/m4a)")
    parser.add_argument("--voiceover", type=str, default=None,
                        help="Voiceover/narration audio URL")
    parser.add_argument("--volume-original", type=float, default=0.3,
                        help="Original clip audio volume 0.0-1.0 (default: 0.3)")
    parser.add_argument("--volume-music", type=float, default=0.15,
                        help="Music volume 0.0-1.0 (default: 0.15)")
    parser.add_argument("--volume-voiceover", type=float, default=1.0,
                        help="Voiceover volume 0.0-1.0 (default: 1.0)")
    parser.add_argument("--aspect", type=str, default=None,
                        choices=["9:16", "16:9", "1:1"],
                        help="Force aspect ratio crop")
    parser.add_argument("--text", type=str, default=None,
                        help="Text overlay burned into video")
    parser.add_argument("--text-position", type=str, default="bottom",
                        choices=["top", "bottom", "center"],
                        help="Text overlay position (default: bottom)")
    parser.add_argument("--output", type=str, default="./output/final.mp4",
                        help="Output file path (default: ./output/final.mp4)")
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
        "volumes": {
            "original": args.volume_original,
            "music": args.volume_music,
            "voiceover": args.volume_voiceover,
        },
    }
    if args.music:
        payload["music"] = args.music
    if args.voiceover:
        payload["voiceover"] = args.voiceover
    if args.aspect:
        payload["aspect"] = args.aspect
    if args.text:
        payload["text"] = args.text
        payload["textPosition"] = args.text_position

    # Submit job
    print(f"Submitting video edit job ({len(args.clips)} clip(s))...")
    result = api_request(f"{api_url}/video/edit", api_key, method="POST", data=payload)
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
