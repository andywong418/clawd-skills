#!/usr/bin/env python3
"""Generate videos via the ViralFarm API."""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError


def load_config():
    """Load API URL and key from environment or .env file."""
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


def api_request(url: str, api_key: str, method: str = "GET", data: dict = None) -> dict:
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


def download_video(url: str, output_path: Path):
    req = Request(url)
    with urlopen(req, timeout=120) as resp:
        with open(output_path, "wb") as f:
            f.write(resp.read())


def cmd_credits(api_url: str, api_key: str):
    result = api_request(f"{api_url}/credits", api_key)
    print(f"Plan: {result['plan']}")
    print(f"Credits: {result['remaining']}/{result['monthlyCredits']} remaining")
    print(f"Used: {result['creditsUsed']}")


def cmd_status(api_url: str, api_key: str, job_id: str):
    result = api_request(f"{api_url}/generate/{job_id}", api_key)
    print(f"Job: {result['id']}")
    print(f"Status: {result['status']}")
    if result.get('progress') is not None:
        print(f"Progress: {result['progress']}%")
    if result.get('progressMessage'):
        print(f"Message: {result['progressMessage']}")
    if result.get('output', {}).get('videoUrl'):
        print(f"Video: {result['output']['videoUrl']}")
    if result.get('error'):
        print(f"Error: {result['error']}")


def cmd_generate(api_url: str, api_key: str, args):
    payload = {}

    if args.prompt:
        payload["prompt"] = args.prompt
    if args.provider:
        payload["provider"] = args.provider
    if args.model:
        payload["model"] = args.model
    if args.duration:
        payload["duration"] = args.duration
    if args.ratio:
        payload["ratio"] = args.ratio

    # Image input
    if args.image:
        img = {"url": args.image}
        if args.image_role:
            img["role"] = args.image_role
        payload["images"] = [img]

    # Submit
    mode = "image-to-video" if args.image else "text-to-video"
    provider_str = args.provider or "default"
    print(f"Submitting {mode} request...")
    print(f"  Provider: {provider_str}")
    if args.model:
        print(f"  Model: {args.model}")
    print(f"  Duration: {args.duration or 5}s")
    print(f"  Ratio: {args.ratio or '16:9'}")
    if args.prompt:
        print(f"  Prompt: {args.prompt[:80]}{'...' if len(args.prompt) > 80 else ''}")

    result = api_request(f"{api_url}/generate", api_key, method="POST", data=payload)

    job_id = result["id"]
    print(f"\nJob ID: {job_id}")
    print(f"Status: {result['status']}")

    if args.no_wait:
        print("\n--no-wait specified. Check status with:")
        print(f"  python3 skills/video-gen/scripts/generate.py --status {job_id}")
        return

    # Poll for completion
    print("\nWaiting for video generation...")
    start_time = time.time()

    while True:
        time.sleep(10)

        status = api_request(f"{api_url}/generate/{job_id}", api_key)
        state = status["status"]
        elapsed = int(time.time() - start_time)

        progress = status.get("progress", 0)
        msg = status.get("progressMessage", "")
        print(f"  [{elapsed}s] {state} - {progress}% {msg}")

        if state == "completed":
            video_url = status.get("output", {}).get("videoUrl")
            if video_url:
                print(f"\nVideo URL: {video_url}")

                # Download
                output_dir = Path(args.output)
                output_dir.mkdir(parents=True, exist_ok=True)
                output_path = output_dir / f"{job_id}.mp4"

                print(f"Downloading to: {output_path}")
                try:
                    download_video(video_url, output_path)
                    print(f"Saved: {output_path}")
                except Exception as e:
                    print(f"Download failed: {e}", file=sys.stderr)
                    print(f"Video still at: {video_url}")
            else:
                print("Completed but no video URL in output")
            return

        if state in ("failed", "cancelled"):
            error = status.get("error", "Unknown error")
            print(f"\nGeneration {state}: {error}", file=sys.stderr)
            sys.exit(1)

        if elapsed > 660:  # 11 min safety
            print("\nTimed out waiting for result", file=sys.stderr)
            sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Generate videos via ViralFarm API")
    parser.add_argument("prompt", nargs="?", help="Text prompt for video generation")
    parser.add_argument("--provider", help="Video provider: kling, runway, sora, seedance, magichour")
    parser.add_argument("--model", help="Model name (provider-specific)")
    parser.add_argument("--image", help="Image URL for image-to-video")
    parser.add_argument("--image-role", choices=["first_frame", "last_frame"],
                        help="Role of the image (for Runway)")
    parser.add_argument("--duration", type=int, help="Duration in seconds")
    parser.add_argument("--ratio", help="Aspect ratio (16:9, 9:16, 1:1)")
    parser.add_argument("--output", default="./output", help="Output directory")
    parser.add_argument("--no-wait", action="store_true", help="Submit without waiting")
    parser.add_argument("--status", metavar="JOB_ID", help="Check status of existing job")
    parser.add_argument("--credits", action="store_true", help="Show remaining credits")

    args = parser.parse_args()

    api_url, api_key = load_config()
    if not api_url or not api_key:
        print("Error: VIRALFARM_API_URL and VIRALFARM_API_KEY required", file=sys.stderr)
        print("Set in environment or ~/.clawdbot/.env", file=sys.stderr)
        sys.exit(1)

    api_url = api_url.rstrip("/")

    if args.credits:
        cmd_credits(api_url, api_key)
        return

    if args.status:
        cmd_status(api_url, api_key, args.status)
        return

    if not args.prompt and not args.image:
        parser.print_help()
        sys.exit(1)

    cmd_generate(api_url, api_key, args)


if __name__ == "__main__":
    main()
