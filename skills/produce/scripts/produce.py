#!/usr/bin/env python3
"""Produce — end-to-end video production via ViralFarm API.

Submits a full production job to the ViralFarm API: topic/script to finished
video with b-roll, voiceover, subtitles, and platform-specific formatting.

Usage examples:
  # Claude writes a viral script, full pipeline
  python3 produce.py --from-trending "sleep hygiene tips"

  # Provide your own script
  python3 produce.py --script "5 things your doctor won't tell you about sleep..."

  # Target specific platforms with subtitles
  python3 produce.py --from-trending "AI tools that changed my workflow" \
    --platforms tiktok youtube --subtitle-style tiktok

  # Custom b-roll count and background music
  python3 produce.py --from-trending "morning routine hacks" \
    --broll-count 5 --music https://example.com/beat.mp3

  # Skip subtitles for faster processing
  python3 produce.py --from-trending "stoic quotes" --no-subtitles

  # Output to a specific directory
  python3 produce.py --from-trending "sleep tips" --output ./my-videos

  # Dry run (not supported via API)
  python3 produce.py --from-trending "test topic" --dry-run

  # Fire and forget
  python3 produce.py --from-trending "quick tip" --no-wait
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
        description="End-to-end video production via ViralFarm API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 produce.py --from-trending "sleep hygiene tips"
  python3 produce.py --script "5 things your doctor won't tell you..."
  python3 produce.py --from-trending "AI tools" --platforms tiktok youtube
  python3 produce.py --from-trending "morning routine" --no-subtitles --broll-count 5
  python3 produce.py --from-trending "test topic" --dry-run
  python3 produce.py --from-trending "quick tip" --no-wait
""",
    )

    # Script source (mutually exclusive, one required)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--from-trending", metavar="TOPIC", dest="from_trending",
                        help="Use AI to write a viral script about this topic")
    source.add_argument("--script", metavar="TEXT",
                        help="Pre-written narration script")

    # Platforms
    parser.add_argument("--platforms", nargs="*", default=None,
                        help="Target platforms (e.g. tiktok youtube instagram)")

    # Subtitles
    parser.add_argument("--no-subtitles", action="store_true", dest="no_subtitles",
                        help="Skip subtitle burning")
    parser.add_argument("--subtitle-style", default=None,
                        choices=["tiktok", "youtube", "minimal"],
                        dest="subtitle_style",
                        help="Caption style (default: server decides)")

    # B-roll
    parser.add_argument("--broll-count", type=int, default=3, metavar="N",
                        dest="broll_count",
                        help="Number of b-roll clips to use (default: 3)")

    # Music
    parser.add_argument("--music", metavar="URL", default=None,
                        help="Optional background music URL")

    # Output
    parser.add_argument("--output", metavar="DIR", default="./output/produce",
                        help="Output directory (default: ./output/produce)")

    # Modes
    parser.add_argument("--no-wait", action="store_true",
                        help="Submit job and exit without waiting for completion")
    parser.add_argument("--dry-run", action="store_true", dest="dry_run",
                        help="Preview what would be produced (not supported via API)")

    args = parser.parse_args()

    # Handle dry run
    if args.dry_run:
        print("Dry run not supported via API. Submit without --dry-run to produce a video.",
              file=sys.stderr)
        sys.exit(0)

    api_url, api_key = load_config()
    if not api_url or not api_key:
        print("Error: VIRALFARM_API_URL and VIRALFARM_API_KEY must be set "
              "(env vars or ~/.clawdbot/.env)", file=sys.stderr)
        sys.exit(1)

    # Build request payload
    payload = {
        "subtitles": not args.no_subtitles,
        "brollCount": args.broll_count,
    }
    if args.from_trending:
        payload["topic"] = args.from_trending
    if args.script:
        payload["script"] = args.script
    if args.platforms:
        payload["platforms"] = args.platforms
    if args.subtitle_style:
        payload["subtitleStyle"] = args.subtitle_style
    if args.music:
        payload["music"] = args.music

    # Submit job
    source_desc = args.from_trending or f"script ({len(args.script.split())} words)"
    print(f"Submitting production job: {source_desc}")
    result = api_request(f"{api_url}/produce", api_key, method="POST", data=payload)
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
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "produced.mp4"
    print(f"Downloading result to {output_path}...")
    download_file(video_url, str(output_path))
    print(f"\nDone: {output_path}")


if __name__ == "__main__":
    main()
