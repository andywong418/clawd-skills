#!/usr/bin/env python3
"""
Magic Hour Face Swap via ViralFarm API

Submits face-swap jobs through the ViralFarm API, which proxies to Magic Hour.
Requires VIRALFARM_API_URL and VIRALFARM_API_KEY (env vars or ~/.clawdbot/.env).

Usage:
    # Start a face swap and wait for result
    python magichour_faceswap.py https://example.com/face.jpg https://example.com/video.mp4 -o output.mp4

    # Start without waiting (prints job ID)
    python magichour_faceswap.py https://example.com/face.jpg https://example.com/video.mp4 --no-wait

    # Check status of an existing job
    python magichour_faceswap.py --status JOB_ID

    # Options
    python magichour_faceswap.py SOURCE TARGET --duration 10 --single-face -o result.mp4
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

POLL_INTERVAL = 3  # seconds
MAX_POLL_ATTEMPTS = 120  # 6 minutes max


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def load_config():
    url = os.environ.get("VIRALFARM_API_URL")
    key = os.environ.get("VIRALFARM_API_KEY")
    if url and key:
        return url, key
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
        try:
            err = json.loads(err_body)
            msg = err.get("error", err_body)
        except json.JSONDecodeError:
            msg = err_body
        print(f"API error ({e.code}): {msg}", file=sys.stderr)
        sys.exit(1)
    except URLError as e:
        print(f"Connection error: {e.reason}", file=sys.stderr)
        sys.exit(1)


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def is_url(value: str) -> bool:
    return value.startswith("http://") or value.startswith("https://")


def submit_face_swap(api_url, api_key, source_url, target_url, duration, single_face):
    """POST a face-swap job to the ViralFarm API."""
    payload = {
        "sourceUrl": source_url,
        "targetUrl": target_url,
        "duration": duration,
        "singleFace": single_face,
    }
    result = api_request(f"{api_url}/face-swap", api_key, method="POST", data=payload)
    job_id = result.get("id") or result.get("jobId")
    if not job_id:
        print("Error: no job ID returned from API", file=sys.stderr)
        sys.exit(1)
    return job_id, result


def poll_job(api_url, api_key, job_id):
    """Poll GET /jobs/{job_id} until the job reaches a terminal state."""
    print(f"Waiting for job {job_id}...")
    for attempt in range(MAX_POLL_ATTEMPTS):
        result = api_request(f"{api_url}/jobs/{job_id}", api_key)
        status = result.get("status", "unknown")

        if status == "completed":
            video_url = (result.get("output") or {}).get("videoUrl")
            if not video_url:
                print("Error: job completed but no videoUrl in output", file=sys.stderr)
                sys.exit(1)
            return video_url

        if status in ("failed", "error"):
            msg = result.get("error") or "Face swap job failed"
            print(f"Error: {msg}", file=sys.stderr)
            sys.exit(1)

        if status in ("cancelled", "canceled"):
            print("Error: job was cancelled", file=sys.stderr)
            sys.exit(1)

        if attempt % 10 == 0:
            print(f"  Still processing... ({attempt * POLL_INTERVAL}s)")

        time.sleep(POLL_INTERVAL)

    print("Error: timed out waiting for face swap to complete", file=sys.stderr)
    sys.exit(1)


def download_video(video_url, output_path):
    """Download the result video to a local file."""
    req = Request(video_url)
    try:
        with urlopen(req, timeout=120) as resp:
            with open(output_path, "wb") as f:
                while True:
                    chunk = resp.read(8192)
                    if not chunk:
                        break
                    f.write(chunk)
    except (HTTPError, URLError) as e:
        print(f"Error downloading video: {e}", file=sys.stderr)
        sys.exit(1)


def check_status(api_url, api_key, job_id):
    """Print the current status of a job."""
    result = api_request(f"{api_url}/jobs/{job_id}", api_key)
    print(json.dumps(result, indent=2))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Face swap via ViralFarm API (Magic Hour provider)"
    )
    parser.add_argument("source", nargs="?", help="Source face image URL")
    parser.add_argument("target", nargs="?", help="Target video URL")
    parser.add_argument("--duration", type=float, default=6, help="Duration in seconds (default: 6)")
    parser.add_argument("--single-face", action="store_true", help="Only swap the primary face")
    parser.add_argument("--output", "-o", default=None, help="Output file path")
    parser.add_argument("--no-wait", action="store_true", help="Submit job and exit without waiting")
    parser.add_argument("--status", metavar="JOB_ID", default=None, help="Check status of an existing job")
    args = parser.parse_args()

    api_url, api_key = load_config()
    if not api_url or not api_key:
        print(
            "Error: VIRALFARM_API_URL and VIRALFARM_API_KEY must be set "
            "(environment variables or ~/.clawdbot/.env)",
            file=sys.stderr,
        )
        sys.exit(1)

    # Strip trailing slash from API URL
    api_url = api_url.rstrip("/")

    # --status mode: just check job status and exit
    if args.status:
        check_status(api_url, api_key, args.status)
        return

    # Normal mode: source and target are required
    if not args.source or not args.target:
        parser.error("source and target are required (unless using --status)")

    # Validate that inputs are URLs, not local paths
    for label, value in [("source", args.source), ("target", args.target)]:
        if not is_url(value):
            print(
                f"Error: {label} must be a URL (http:// or https://). "
                f"Local file paths are not supported — the API cannot access local files.",
                file=sys.stderr,
            )
            sys.exit(1)

    # Submit the face-swap job
    print("Submitting face swap job...")
    job_id, result = submit_face_swap(
        api_url, api_key, args.source, args.target, args.duration, args.single_face
    )
    print(f"Job submitted: {job_id}")

    if args.no_wait:
        print(f"Use --status {job_id} to check progress.")
        return

    # Poll until done
    video_url = poll_job(api_url, api_key, job_id)
    print(f"Face swap complete: {video_url}")

    # Download if output path given
    if args.output:
        print("Downloading result...")
        download_video(video_url, args.output)
        print(f"Output saved: {args.output}")
    else:
        print(f"Video URL: {video_url}")
        print("(Use --output/-o to download automatically)")


if __name__ == "__main__":
    main()
