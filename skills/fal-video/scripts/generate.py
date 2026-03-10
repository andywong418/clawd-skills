#!/usr/bin/env python3
"""Generate videos using fal.ai API (Kling models)."""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
import urllib.request
import urllib.error

def load_api_key():
    """Load API key from environment or .env file."""
    key = os.environ.get("FAL_API_KEY")
    if key:
        return key
    
    env_path = Path.home() / ".clawdbot" / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                if line.startswith("FAL_API_KEY="):
                    return line.split("=", 1)[1].strip()
    
    return None

def api_request(url: str, api_key: str, data: dict = None, method: str = "POST") -> dict:
    """Make API request to fal.ai."""
    headers = {
        "Authorization": f"Key {api_key}",
        "Content-Type": "application/json"
    }
    
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8") if data else None,
        headers=headers,
        method=method
    )
    
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        raise RuntimeError(f"API error {e.code}: {error_body}")

def upload_image(image_path: str, api_key: str) -> str:
    """Upload local image and return URL."""
    # If already a URL, return as-is
    if image_path.startswith(("http://", "https://")):
        return image_path
    
    # Read local file
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")
    
    with open(path, "rb") as f:
        image_data = f.read()
    
    # Get upload URL from fal.ai
    upload_info = api_request(
        "https://fal.ai/api/storage/upload/initiate",
        api_key,
        {"file_name": path.name, "content_type": f"image/{path.suffix[1:]}"}
    )
    
    # Upload to the URL
    upload_req = urllib.request.Request(
        upload_info["upload_url"],
        data=image_data,
        method="PUT"
    )
    upload_req.add_header("Content-Type", f"image/{path.suffix[1:]}")
    
    with urllib.request.urlopen(upload_req, timeout=60):
        pass
    
    return upload_info["file_url"]

def submit_video(prompt: str, api_key: str, image_url: str = None,
                 duration: int = 5, aspect_ratio: str = "16:9",
                 model: str = "v1.6/pro") -> dict:
    """Submit video generation request to queue."""
    
    # Determine endpoint
    if image_url:
        endpoint = f"https://queue.fal.run/fal-ai/kling-video/{model}/image-to-video"
        payload = {
            "prompt": prompt,
            "image_url": image_url,
            "duration": str(duration),
            "aspect_ratio": aspect_ratio
        }
    else:
        endpoint = f"https://queue.fal.run/fal-ai/kling-video/{model}/text-to-video"
        payload = {
            "prompt": prompt,
            "duration": str(duration),
            "aspect_ratio": aspect_ratio
        }
    
    return api_request(endpoint, api_key, payload)

def check_status(request_id: str, api_key: str) -> dict:
    """Check status of a queued request."""
    url = f"https://queue.fal.run/fal-ai/kling-video/requests/{request_id}/status"
    
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Key {api_key}")
    
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))

def get_result(request_id: str, api_key: str) -> dict:
    """Get result of a completed request."""
    url = f"https://queue.fal.run/fal-ai/kling-video/requests/{request_id}"
    
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Key {api_key}")
    
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))

def download_video(url: str, output_path: Path) -> Path:
    """Download video from URL."""
    req = urllib.request.Request(url)
    
    with urllib.request.urlopen(req, timeout=120) as resp:
        with open(output_path, "wb") as f:
            f.write(resp.read())
    
    return output_path

def main():
    parser = argparse.ArgumentParser(description="Generate videos with fal.ai Kling")
    parser.add_argument("prompt", help="Text prompt for video generation")
    parser.add_argument("--image", type=str, help="Image URL/path for image-to-video")
    parser.add_argument("--duration", type=int, default=5, choices=[5, 10],
                       help="Duration in seconds (5 or 10)")
    parser.add_argument("--aspect", type=str, default="16:9",
                       choices=["16:9", "9:16", "1:1"],
                       help="Aspect ratio")
    parser.add_argument("--model", type=str, default="v1.6/pro",
                       choices=["v1.6/pro", "v2/master", "o3"],
                       help="Kling model version")
    parser.add_argument("--output", type=str, default="./output",
                       help="Output directory")
    parser.add_argument("--no-wait", action="store_true",
                       help="Submit and exit without waiting")
    
    args = parser.parse_args()
    
    api_key = load_api_key()
    if not api_key:
        print("Error: FAL_API_KEY not found", file=sys.stderr)
        sys.exit(1)
    
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Upload image if provided
    image_url = None
    if args.image:
        print(f"Uploading image: {args.image}")
        try:
            image_url = upload_image(args.image, api_key)
            print(f"Image URL: {image_url}")
        except Exception as e:
            print(f"Error uploading image: {e}", file=sys.stderr)
            sys.exit(1)
    
    mode = "image-to-video" if image_url else "text-to-video"
    print(f"Submitting {mode} request...")
    print(f"  Model: Kling {args.model}")
    print(f"  Duration: {args.duration}s")
    print(f"  Aspect: {args.aspect}")
    print(f"  Prompt: {args.prompt[:80]}...")
    
    try:
        result = submit_video(
            prompt=args.prompt,
            api_key=api_key,
            image_url=image_url,
            duration=args.duration,
            aspect_ratio=args.aspect,
            model=args.model
        )
    except Exception as e:
        print(f"Error submitting request: {e}", file=sys.stderr)
        sys.exit(1)
    
    request_id = result["request_id"]
    print(f"\nRequest ID: {request_id}")
    print(f"Status URL: {result['status_url']}")
    
    if args.no_wait:
        print("\n--no-wait specified, exiting. Check status manually.")
        sys.exit(0)
    
    # Poll for completion
    print("\nWaiting for video generation...")
    start_time = time.time()
    
    while True:
        status = check_status(request_id, api_key)
        state = status.get("status", "UNKNOWN")
        
        elapsed = int(time.time() - start_time)
        print(f"  [{elapsed}s] Status: {state}", end="")
        
        if "queue_position" in status and status["queue_position"] > 0:
            print(f" (queue position: {status['queue_position']})", end="")
        print()
        
        if state == "COMPLETED":
            break
        elif state in ("FAILED", "CANCELLED"):
            print(f"Request {state}", file=sys.stderr)
            sys.exit(1)
        
        time.sleep(5)
    
    # Get result
    result = get_result(request_id, api_key)
    
    # Extract video URL
    video_url = None
    if "video" in result and "url" in result["video"]:
        video_url = result["video"]["url"]
    elif "output" in result and "url" in result["output"]:
        video_url = result["output"]["url"]
    
    if not video_url:
        print(f"No video URL in result: {json.dumps(result, indent=2)}", file=sys.stderr)
        sys.exit(1)
    
    print(f"\nVideo URL: {video_url}")
    
    # Download video
    output_path = output_dir / f"{request_id}.mp4"
    print(f"Downloading to: {output_path}")
    
    try:
        download_video(video_url, output_path)
        print(f"\nSaved: {output_path}")
    except Exception as e:
        print(f"Download failed: {e}", file=sys.stderr)
        print(f"Video URL still accessible: {video_url}")
        sys.exit(1)

if __name__ == "__main__":
    main()
