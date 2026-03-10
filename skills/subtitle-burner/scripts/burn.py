#!/usr/bin/env python3
"""Subtitle Burner — burn captions into a video via the ViralFarm API.

Pipeline (server-side):
  1. POST to /subtitles/burn with video URL, style, and words-per-phrase
  2. Poll GET /jobs/{job_id} until the job completes
  3. Download the output video from the returned URL

Supported styles: tiktok, youtube, minimal.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen, urlretrieve
from urllib.error import URLError, HTTPError


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
            msg = json.loads(err_body).get("error", err_body)
        except Exception:
            msg = err_body
        print(f"API error ({e.code}): {msg}", file=sys.stderr)
        sys.exit(1)
    except URLError as e:
        print(f"Connection error: {e.reason}", file=sys.stderr)
        sys.exit(1)


# ---------------------------------------------------------------------------
# Job polling
# ---------------------------------------------------------------------------

POLL_INTERVAL = 5
MAX_POLL_TIME = 600  # 10 minutes


def poll_job(api_url, api_key, job_id):
    """Poll GET /jobs/{job_id} until the job reaches a terminal state."""
    start = time.time()
    while True:
        elapsed = int(time.time() - start)
        result = api_request(f"{api_url}/jobs/{job_id}", api_key)
        status = result.get("status", "unknown")
        print(f"  [{elapsed}s] {status}", file=sys.stderr)

        if status == "completed":
            return result
        elif status in ("failed", "cancelled", "error"):
            error_msg = result.get("error", "Job did not complete successfully")
            print(f"Job {status}: {error_msg}", file=sys.stderr)
            sys.exit(1)

        if elapsed > MAX_POLL_TIME:
            print(f"Timed out after {MAX_POLL_TIME}s waiting for job {job_id}", file=sys.stderr)
            sys.exit(1)

        time.sleep(POLL_INTERVAL)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Burn captions into a video via the ViralFarm API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 burn.py https://example.com/clip.mp4
  python3 burn.py https://example.com/clip.mp4 --style youtube --words-per-phrase 4
  python3 burn.py https://example.com/clip.mp4 --output captioned.mp4
  python3 burn.py --status abc-123-def
""",
    )
    parser.add_argument("video_url", nargs="?", help="Video URL to subtitle (must be a URL, not a local path)")
    parser.add_argument("--style", choices=["tiktok", "youtube", "minimal"], default="tiktok",
                        help="Caption style (default: tiktok)")
    parser.add_argument("--words-per-phrase", type=int, default=3, metavar="N",
                        help="Words per subtitle phrase (default: 3)")
    parser.add_argument("--output", default=None,
                        help="Output file path (default: ./output/subtitled/<name>_captioned.mp4)")
    parser.add_argument("--no-wait", action="store_true",
                        help="Submit the job and exit without waiting for completion")
    parser.add_argument("--status", metavar="JOB_ID", default=None,
                        help="Check status of an existing job instead of submitting a new one")
    args = parser.parse_args()

    # Load config
    api_url, api_key = load_config()
    if not api_url or not api_key:
        print("Error: VIRALFARM_API_URL and VIRALFARM_API_KEY must be set "
              "(via environment or ~/.clawdbot/.env)", file=sys.stderr)
        sys.exit(1)
    api_url = api_url.rstrip("/")

    # --status mode: check an existing job
    if args.status:
        job_id = args.status
        print(f"[subtitle-burner] Checking job {job_id}...", file=sys.stderr)
        result = api_request(f"{api_url}/jobs/{job_id}", api_key)
        status = result.get("status", "unknown")
        print(f"  Status: {status}", file=sys.stderr)

        if status == "completed":
            output = result.get("output", {})
            video_url = output.get("videoUrl")
            word_count = output.get("wordCount", "N/A")
            phrase_count = output.get("phraseCount", "N/A")
            print(f"  Words: {word_count}", file=sys.stderr)
            print(f"  Phrases: {phrase_count}", file=sys.stderr)
            if video_url:
                print(f"  Video URL: {video_url}", file=sys.stderr)
                if args.output:
                    output_path = Path(args.output)
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    print(f"[subtitle-burner] Downloading to {output_path}...", file=sys.stderr)
                    urlretrieve(video_url, str(output_path))
                    print(str(output_path))
                else:
                    print(video_url)
        else:
            print(json.dumps(result, indent=2))
        return

    # Normal mode: submit a new job
    if not args.video_url:
        parser.error("video_url is required when not using --status")

    video_url = args.video_url
    if not video_url.startswith(("http://", "https://")):
        print("Error: video_url must be a URL (http:// or https://), not a local path", file=sys.stderr)
        sys.exit(1)

    print(f"[subtitle-burner] Video:  {video_url}", file=sys.stderr)
    print(f"[subtitle-burner] Style:  {args.style}", file=sys.stderr)
    print(f"[subtitle-burner] Words per phrase: {args.words_per_phrase}", file=sys.stderr)

    # Submit the burn job
    print("[subtitle-burner] Submitting burn job...", file=sys.stderr)
    payload = {
        "videoUrl": video_url,
        "style": args.style,
        "wordsPerPhrase": args.words_per_phrase,
    }
    result = api_request(f"{api_url}/subtitles/burn", api_key, method="POST", data=payload)
    job_id = result.get("jobId") or result.get("id")
    if not job_id:
        print(f"Error: no job ID in response: {json.dumps(result)}", file=sys.stderr)
        sys.exit(1)

    print(f"  Job ID: {job_id}", file=sys.stderr)

    # --no-wait mode: print job ID and exit
    if args.no_wait:
        print(f"Job submitted. Check status with: python3 burn.py --status {job_id}", file=sys.stderr)
        print(job_id)
        return

    # Poll until done
    print("[subtitle-burner] Waiting for job to complete...", file=sys.stderr)
    result = poll_job(api_url, api_key, job_id)

    output = result.get("output", {})
    video_result_url = output.get("videoUrl")
    word_count = output.get("wordCount", "N/A")
    phrase_count = output.get("phraseCount", "N/A")

    print(f"\n  Words: {word_count}", file=sys.stderr)
    print(f"  Phrases: {phrase_count}", file=sys.stderr)

    if not video_result_url:
        print("Error: job completed but no videoUrl in output", file=sys.stderr)
        print(json.dumps(result, indent=2), file=sys.stderr)
        sys.exit(1)

    print(f"  Video URL: {video_result_url}", file=sys.stderr)

    # Download the result
    if args.output:
        output_path = Path(args.output)
    else:
        # Derive filename from the input URL
        url_stem = Path(video_url.split("?")[0].split("#")[0]).stem or "video"
        out_dir = Path("./output/subtitled")
        output_path = out_dir / f"{url_stem}_captioned.mp4"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"[subtitle-burner] Downloading to {output_path}...", file=sys.stderr)
    urlretrieve(video_result_url, str(output_path))

    print(f"\nDone! {output_path}", file=sys.stderr)
    print(str(output_path))


if __name__ == "__main__":
    main()
