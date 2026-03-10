#!/usr/bin/env python3
"""Thumbnail Generator — generate thumbnail variants via ViralFarm API.

Submits a thumbnail generation job to the ViralFarm API and polls until
completion. Supports video or image input, multiple styles, and smart mode
(AI-driven title condensing, frame selection, and style picking).

Usage examples:
  # Generate thumbnails from a video URL with a title
  python3 generate.py --video https://example.com/video.mp4 --title "I tried this for 30 days"

  # Generate from an image with specific styles
  python3 generate.py --image https://example.com/frame.jpg \
    --title "Antarctica" --styles C D

  # Smart mode with subtitle
  python3 generate.py --video https://example.com/video.mp4 \
    --title "1000 MPH baseball" --subtitle "You won't believe what happened" --smart

  # Output to a specific directory
  python3 generate.py --video https://example.com/video.mp4 \
    --title "Lost everything" --output ./my-thumbnails

  # Fire and forget
  python3 generate.py --video https://example.com/video.mp4 \
    --title "Quick tip" --no-wait
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
        description="Generate thumbnail variants via ViralFarm API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Styles:
  A  bold-top        White bold text at top (classic YouTube)
  B  strip-bottom    Yellow text on dark strip at bottom
  C  clean           Minimal white text, no treatment (vlog/travel)
  D  two-tone        White + yellow accent lines (fitness/finance)
  E  number-forward  Huge number dominant (stats/challenges)
  F  annotation      Red circle + arrow highlight

Examples:
  python3 generate.py --video https://example.com/video.mp4 --title "I tried this for 30 days"
  python3 generate.py --image https://example.com/frame.jpg --title "Antarctica" --styles C D
  python3 generate.py --video https://example.com/video.mp4 --title "1000 MPH baseball" --smart
""",
    )

    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--video", type=str, help="Video URL to extract frames from")
    source.add_argument("--image", type=str, help="Image URL to use as base frame")

    parser.add_argument("--title", required=True, help="Main title text")
    parser.add_argument("--subtitle", default=None, help="Optional subtitle text")
    parser.add_argument("--styles", nargs="*", default=None,
                        help="Style letters to generate (e.g. A B C). Default: API picks best.")
    parser.add_argument("--smart", action="store_true",
                        help="Enable smart mode (AI title condensing + frame/style selection)")
    parser.add_argument("--output", default="./output/thumbnails",
                        help="Output directory (default: ./output/thumbnails)")
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
        "title": args.title,
    }
    if args.video:
        payload["videoUrl"] = args.video
    if args.image:
        payload["imageUrl"] = args.image
    if args.subtitle:
        payload["subtitle"] = args.subtitle
    if args.styles:
        payload["styles"] = args.styles
    if args.smart:
        payload["smart"] = True

    # Submit job
    print(f"Submitting thumbnail generation job...")
    result = api_request(f"{api_url}/thumbnails", api_key, method="POST", data=payload)
    job_id = result["id"]
    print(f"Job created: {job_id}")

    if args.no_wait:
        print(f"Job submitted. Poll status at: {api_url}/jobs/{job_id}")
        return

    # Poll until completion
    print("Waiting for job to complete...")
    status = poll_job(api_url, api_key, job_id)

    # Download all thumbnails
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    thumbnails = status["output"]["thumbnails"]
    print(f"Downloading {len(thumbnails)} thumbnail(s)...")
    for i, thumb in enumerate(thumbnails):
        url = thumb["url"]
        # Derive filename from URL or use index-based name
        ext = Path(url.split("?")[0]).suffix or ".png"
        name = thumb.get("name", f"thumbnail_{i+1}{ext}")
        out_path = output_dir / name
        download_file(url, str(out_path))
        print(f"  {out_path}")

    print(f"\nDone: {len(thumbnails)} thumbnail(s) saved to {output_dir}")


if __name__ == "__main__":
    main()
