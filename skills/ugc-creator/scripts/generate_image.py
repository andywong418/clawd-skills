#!/usr/bin/env python3
"""Generate AI UGC creator images via the ViralFarm API."""

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


def generate_image(prompt, gender="female", setting="cafe", output_dir="./output"):
    """Generate a UGC creator image via the ViralFarm API. Returns the saved file path."""
    api_url, api_key = load_config()
    if not api_url or not api_key:
        print("Error: VIRALFARM_API_URL and VIRALFARM_API_KEY must be set (env vars or ~/.clawdbot/.env)", file=sys.stderr)
        sys.exit(1)

    api_url = api_url.rstrip("/")

    payload = {
        "prompt": prompt,
        "gender": gender,
        "setting": setting,
        "animate": False,
    }

    print(f"[ugc-creator] Generating image via ViralFarm API...", file=sys.stderr)
    print(f"  Setting: {setting}, Gender: {gender}", file=sys.stderr)

    result = api_request(f"{api_url}/ugc", api_key, method="POST", data=payload)
    job_id = result.get("jobId") or result.get("id")

    if not job_id:
        print(f"Error: No job ID in response: {result}", file=sys.stderr)
        sys.exit(1)

    job_result = poll_job(api_url, api_key, job_id)
    output = job_result.get("output", {})

    image_url = output.get("imageUrl")
    if not image_url:
        print(f"Error: No image URL in job result: {job_result}", file=sys.stderr)
        sys.exit(1)

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = output_path / f"ugc_{timestamp}.png"

    print(f"[ugc-creator] Downloading image...", file=sys.stderr)
    download_file(image_url, str(filename))
    print(f"  Saved: {filename}", file=sys.stderr)
    return str(filename)


def main():
    parser = argparse.ArgumentParser(description="Generate AI UGC creator images via ViralFarm API")
    parser.add_argument("prompt", help="Scene/pose description (e.g., 'holding coffee, smiling')")
    parser.add_argument("--gender", choices=["male", "female"], default="female")
    parser.add_argument("--setting", choices=["cafe", "home", "office", "outdoor", "gym"], default="cafe")
    parser.add_argument("--output", default="./output")
    args = parser.parse_args()
    print(generate_image(args.prompt, args.gender, args.setting, args.output))


if __name__ == "__main__":
    main()
