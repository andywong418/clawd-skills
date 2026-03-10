#!/usr/bin/env python3
"""Full UGC creator pipeline: generate image and optionally animate to video via ViralFarm API."""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError


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
            msg = json.loads(err_body).get("error", err_body)
        except Exception:
            msg = err_body
        print(f"API error ({e.code}): {msg}", file=sys.stderr)
        sys.exit(1)
    except URLError as e:
        print(f"Connection error: {e.reason}", file=sys.stderr)
        sys.exit(1)


def download_file(url, dest_path):
    """Download a file from a URL to a local path."""
    req = Request(url)
    try:
        with urlopen(req, timeout=120) as resp:
            Path(dest_path).parent.mkdir(parents=True, exist_ok=True)
            with open(dest_path, "wb") as f:
                f.write(resp.read())
    except (HTTPError, URLError) as e:
        print(f"Download error: {e}", file=sys.stderr)
        sys.exit(1)


def poll_job(api_url, api_key, job_id, interval=5):
    """Poll a job until it reaches a terminal state. Returns the job result."""
    print(f"[ugc-creator] Job submitted: {job_id}", file=sys.stderr)
    while True:
        time.sleep(interval)
        result = api_request(f"{api_url}/jobs/{job_id}", api_key)
        status = result.get("status", "unknown")
        print(f"  Status: {status}", file=sys.stderr)

        if status == "completed":
            return result
        elif status in ("failed", "cancelled", "error"):
            error_msg = result.get("error", "Unknown error")
            print(f"Job failed: {error_msg}", file=sys.stderr)
            sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Create UGC content (image + optional video)")
    parser.add_argument("prompt", help="Scene/pose description")
    parser.add_argument("--gender", choices=["male", "female"], default="female", help="Gender of creator")
    parser.add_argument("--setting", choices=["cafe", "home", "office", "outdoor", "gym"], default="cafe", help="Setting")
    parser.add_argument("--animate", action="store_true", help="Also generate video from image")
    parser.add_argument("--duration", type=int, choices=[5, 10], default=5, help="Video duration")
    parser.add_argument("--output", default="./output", help="Output directory")
    parser.add_argument("--no-wait", action="store_true", help="Submit job and exit without waiting for completion")

    args = parser.parse_args()

    api_url, api_key = load_config()
    if not api_url or not api_key:
        print("Error: VIRALFARM_API_URL and VIRALFARM_API_KEY must be set (env vars or ~/.clawdbot/.env)", file=sys.stderr)
        sys.exit(1)

    # Strip trailing slash
    api_url = api_url.rstrip("/")

    payload = {
        "prompt": args.prompt,
        "gender": args.gender,
        "setting": args.setting,
        "animate": args.animate,
        "duration": args.duration,
    }

    print("=" * 50, file=sys.stderr)
    print("Submitting UGC creation job to ViralFarm API", file=sys.stderr)
    print(f"  Prompt: {args.prompt}", file=sys.stderr)
    print(f"  Gender: {args.gender}, Setting: {args.setting}", file=sys.stderr)
    if args.animate:
        print(f"  Animate: yes, Duration: {args.duration}s", file=sys.stderr)
    print("=" * 50, file=sys.stderr)

    result = api_request(f"{api_url}/ugc", api_key, method="POST", data=payload)
    job_id = result.get("jobId") or result.get("id")

    if not job_id:
        print(f"Error: No job ID in response: {result}", file=sys.stderr)
        sys.exit(1)

    if args.no_wait:
        print(f"Job submitted: {job_id}", file=sys.stderr)
        print(json.dumps({"jobId": job_id}))
        return

    # Poll until completed
    job_result = poll_job(api_url, api_key, job_id)
    output = job_result.get("output", {})

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Download image
    image_url = output.get("imageUrl")
    image_path = None
    if image_url:
        image_path = output_dir / f"ugc_{timestamp}.png"
        print(f"[ugc-creator] Downloading image...", file=sys.stderr)
        download_file(image_url, str(image_path))
        print(f"  Saved: {image_path}", file=sys.stderr)

    # Download video if present
    video_url = output.get("videoUrl")
    video_path = None
    if video_url:
        video_path = output_dir / f"ugc_video_{timestamp}.mp4"
        print(f"[ugc-creator] Downloading video...", file=sys.stderr)
        download_file(video_url, str(video_path))
        print(f"  Saved: {video_path}", file=sys.stderr)

    # Summary
    print("", file=sys.stderr)
    if image_path and video_path:
        print(f"Complete! Image: {image_path}, Video: {video_path}", file=sys.stderr)
    elif image_path:
        print(f"Complete! Image: {image_path}", file=sys.stderr)
        if not args.animate:
            print("Tip: Add --animate to also generate a video", file=sys.stderr)
    else:
        print("Warning: No output files in job result", file=sys.stderr)

    # Print paths to stdout for programmatic use
    paths = {}
    if image_path:
        paths["image"] = str(image_path)
    if video_path:
        paths["video"] = str(video_path)
    print(json.dumps(paths))


if __name__ == "__main__":
    main()
