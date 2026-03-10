#!/usr/bin/env python3
"""Batch clip processor — submits clips to the ViralFarm API.

Takes a JSON manifest of clips, submits them to the ViralFarm clipping API,
polls for completion, and downloads the results.

NOTE: The "input" field in each manifest entry must be a URL (not a local path).

Usage:
    # Submit a job and wait for results
    python3 batch_clips.py manifest.json --output ./clips

    # Read manifest from stdin
    cat manifest.json | python3 batch_clips.py - --output ./clips

    # Submit without waiting (fire-and-forget)
    python3 batch_clips.py manifest.json --no-wait

    # Check status of an existing job
    python3 batch_clips.py --status JOB_ID

Manifest format (JSON):
[
  {
    "input": "https://example.com/video.mp4",
    "output": "clip_01_subtitled.mp4",
    "start": "00:01:30",
    "end": "00:02:15",
    "srt": "/local/path/to/clip_01.srt",
    "subtitle_style": "FontSize=24,Bold=1,..."
  },
  ...
]

The "input" field must be a publicly accessible URL to the source video.
If "srt" is a local file path, its contents are read and sent to the API.

Environment:
    VIRALFARM_API_URL  — base URL of the ViralFarm API
    VIRALFARM_API_KEY  — bearer token for authentication

    Alternatively, set these in ~/.clawdbot/.env

Output: JSON summary of results with status per clip.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen, urlretrieve
from urllib.error import URLError, HTTPError

DEFAULT_WORKERS = 3
POLL_INTERVAL = 5
MAX_POLL_TIME = 1800  # 30 minutes


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


def parse_time(ts):
    """Convert 'HH:MM:SS' or 'HH:MM:SS.mmm' to seconds (float)."""
    parts = ts.strip().split(":")
    if len(parts) == 3:
        h, m, s = parts
        return int(h) * 3600 + int(m) * 60 + float(s)
    elif len(parts) == 2:
        m, s = parts
        return int(m) * 60 + float(s)
    else:
        return float(parts[0])


def read_srt_content(srt_field):
    """If srt_field looks like a file path, read and return its content.
    Otherwise return it as-is (already inline content)."""
    if not srt_field:
        return None
    # If it contains newline characters, treat as inline SRT content
    if "\n" in srt_field:
        return srt_field
    # Try reading as a file path
    srt_path = Path(srt_field)
    if srt_path.exists():
        return srt_path.read_text()
    # Return as-is (could be inline single-line or a URL)
    return srt_field


def submit_job(api_url, api_key, clips, workers):
    """Submit a clipping job to the API. Returns the job response."""
    video_url = clips[0]["input"]
    api_clips = []
    for clip in clips:
        entry = {
            "start": parse_time(clip["start"]),
            "end": parse_time(clip["end"]),
        }
        srt = clip.get("srt")
        if srt:
            srt_content = read_srt_content(srt)
            if srt_content:
                entry["srt"] = srt_content
        api_clips.append(entry)

    payload = {
        "videoUrl": video_url,
        "clips": api_clips,
        "workers": workers,
    }

    return api_request(f"{api_url}/clips", api_key, method="POST", data=payload)


def poll_job(api_url, api_key, job_id):
    """Poll job status until completed or failed. Returns the final job object."""
    start = time.time()
    while True:
        elapsed = time.time() - start
        if elapsed > MAX_POLL_TIME:
            print(f"[batch_clips] Timed out after {int(elapsed)}s waiting for job {job_id}", file=sys.stderr)
            sys.exit(1)

        job = api_request(f"{api_url}/jobs/{job_id}", api_key)
        status = job.get("status", "unknown")

        if status == "completed":
            print(f"[batch_clips] Job {job_id} completed", file=sys.stderr)
            return job
        elif status == "failed":
            error = job.get("error", "Unknown error")
            print(f"[batch_clips] Job {job_id} failed: {error}", file=sys.stderr)
            sys.exit(1)
        else:
            progress = job.get("progress", "")
            progress_str = f" ({progress})" if progress else ""
            print(f"[batch_clips] Job {job_id}: {status}{progress_str} [{int(elapsed)}s]", file=sys.stderr)

        time.sleep(POLL_INTERVAL)


def download_clip(url, output_path):
    """Download a clip from URL to local path."""
    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        urlretrieve(url, output_path)
        size_mb = round(os.path.getsize(output_path) / (1024 * 1024), 1)
        return {"output": output_path, "status": "done", "size_mb": size_mb}
    except Exception as e:
        return {"output": output_path, "status": "failed", "error": str(e)}


def check_status(api_url, api_key, job_id):
    """Check and print status of an existing job."""
    job = api_request(f"{api_url}/jobs/{job_id}", api_key)
    print(json.dumps(job, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Batch clip processor via ViralFarm API")
    parser.add_argument("manifest", nargs="?", default=None,
                        help="JSON manifest file (or '-' for stdin)")
    parser.add_argument("--workers", "-w", type=int, default=DEFAULT_WORKERS,
                        help=f"Parallel workers for API processing (default: {DEFAULT_WORKERS})")
    parser.add_argument("--no-wait", action="store_true",
                        help="Submit job and exit without waiting for completion")
    parser.add_argument("--status", metavar="JOB_ID",
                        help="Check status of an existing job instead of submitting")
    parser.add_argument("--output", "-o", metavar="DIR", default=".",
                        help="Directory to download completed clips to (default: current dir)")
    args = parser.parse_args()

    api_url, api_key = load_config()
    if not api_url or not api_key:
        print("Error: VIRALFARM_API_URL and VIRALFARM_API_KEY must be set "
              "(via environment or ~/.clawdbot/.env)", file=sys.stderr)
        sys.exit(1)

    # Strip trailing slash from API URL
    api_url = api_url.rstrip("/")

    # --status mode: just check a job and exit
    if args.status:
        check_status(api_url, api_key, args.status)
        return

    # Need a manifest for submission
    if not args.manifest:
        parser.error("manifest is required (or use --status JOB_ID)")

    # Read manifest
    if args.manifest == "-":
        raw = sys.stdin.read()
    else:
        manifest_path = Path(args.manifest)
        if not manifest_path.exists():
            print(json.dumps({"error": f"Manifest not found: {manifest_path}"}))
            sys.exit(1)
        raw = manifest_path.read_text()

    clips = json.loads(raw)
    if not clips:
        print(json.dumps({"error": "Empty manifest"}))
        sys.exit(1)

    total = len(clips)
    print(f"[batch_clips] Submitting {total} clips to API with {args.workers} workers...", file=sys.stderr)

    # Submit the job
    start_time = time.time()
    response = submit_job(api_url, api_key, clips, args.workers)
    job_id = response.get("jobId") or response.get("id")

    if not job_id:
        print(f"[batch_clips] Error: no job ID in response: {json.dumps(response)}", file=sys.stderr)
        sys.exit(1)

    print(f"[batch_clips] Job submitted: {job_id}", file=sys.stderr)

    # --no-wait mode: print job ID and exit
    if args.no_wait:
        print(json.dumps({"jobId": job_id, "status": "submitted", "total": total}, indent=2))
        return

    # Poll until done
    job = poll_job(api_url, api_key, job_id)
    elapsed = round(time.time() - start_time, 1)

    # Download clips
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    output_clips = job.get("output", {}).get("clips", [])
    results = []

    for i, clip in enumerate(clips):
        clip_output = output_clips[i] if i < len(output_clips) else {}
        clip_url = clip_output.get("url")

        # Determine local output path
        local_output = clip.get("output", f"clip_{i:03d}.mp4")
        # If the manifest output is just a filename, put it in the output dir
        if not os.path.isabs(local_output):
            local_output = str(output_dir / Path(local_output).name)

        if clip_url:
            print(f"[batch_clips] Downloading [{i + 1}/{total}] {Path(local_output).name}...", file=sys.stderr)
            result = download_clip(clip_url, local_output)
        else:
            error = clip_output.get("error", "No URL in response")
            result = {"output": local_output, "status": "failed", "error": error}

        results.append(result)
        if result["status"] == "done":
            print(f"[batch_clips] [{i + 1}/{total}] {Path(local_output).name} ({result['size_mb']}MB)", file=sys.stderr)
        else:
            print(f"[batch_clips] [{i + 1}/{total}] {Path(local_output).name}: FAILED - {result.get('error', '')[:80]}", file=sys.stderr)

    done = sum(1 for r in results if r["status"] == "done")
    print(f"[batch_clips] Done: {done}/{total} clips in {elapsed}s", file=sys.stderr)

    # Output JSON summary to stdout
    print(json.dumps({
        "jobId": job_id,
        "total": total,
        "done": done,
        "elapsed_sec": elapsed,
        "clips": results,
    }, indent=2))


if __name__ == "__main__":
    main()
