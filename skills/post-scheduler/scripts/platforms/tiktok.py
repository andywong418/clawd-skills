"""TikTok Content Posting API client."""

import json
import os
import time
from pathlib import Path
import urllib.request
import urllib.error

BASE_URL = "https://open.tiktokapis.com/v2"


def _load_token() -> str:
    token = os.environ.get("TIKTOK_ACCESS_TOKEN")
    if token:
        return token
    env_path = Path.home() / ".clawdbot" / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                if line.startswith("TIKTOK_ACCESS_TOKEN="):
                    return line.split("=", 1)[1].strip()
    raise RuntimeError(
        "TIKTOK_ACCESS_TOKEN not found in ~/.clawdbot/.env\n"
        "Get one via TikTok Developer Portal → Content Posting API OAuth flow."
    )


def _api(endpoint: str, token: str, data: dict) -> dict:
    req = urllib.request.Request(
        f"{BASE_URL}{endpoint}",
        data=json.dumps(data).encode(),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"TikTok API {e.code}: {e.read().decode()}")


def post_video(video_path: str, caption: str) -> str:
    """Upload and publish a video to TikTok. Returns publish_id."""
    token = _load_token()
    path = Path(video_path)
    if not path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")

    file_size = path.stat().st_size
    print(f"[tiktok] Initializing post ({file_size / 1024 / 1024:.1f} MB)...")

    result = _api("/post/publish/video/init/", token, {
        "post_info": {
            "title": caption[:2200],
            "privacy_level": "PUBLIC_TO_EVERYONE",
            "disable_duet": False,
            "disable_comment": False,
            "disable_stitch": False,
        },
        "source_info": {
            "source": "FILE_UPLOAD",
            "video_size": file_size,
            "chunk_size": file_size,
            "total_chunk_count": 1,
        },
    })

    if result.get("error", {}).get("code", "ok") != "ok":
        raise RuntimeError(f"TikTok init error: {result}")

    upload_url = result["data"]["upload_url"]
    publish_id = result["data"]["publish_id"]

    print(f"[tiktok] Uploading...")
    with open(path, "rb") as f:
        video_data = f.read()

    put_req = urllib.request.Request(upload_url, data=video_data, method="PUT")
    put_req.add_header("Content-Type", "video/mp4")
    put_req.add_header("Content-Range", f"bytes 0-{file_size - 1}/{file_size}")
    with urllib.request.urlopen(put_req, timeout=300):
        pass

    print(f"[tiktok] Polling status...")
    for _ in range(24):
        time.sleep(5)
        status = _api("/post/publish/status/fetch/", token, {"publish_id": publish_id})
        state = status.get("data", {}).get("status", "UNKNOWN")
        print(f"  {state}")
        if state == "PUBLISH_COMPLETE":
            print(f"[tiktok] Published. publish_id={publish_id}")
            return publish_id
        if state in ("FAILED", "PUBLISH_FAIL"):
            raise RuntimeError(f"TikTok publish failed: {status.get('data', {}).get('fail_reason', 'unknown')}")

    raise RuntimeError("TikTok publish timed out after 2 minutes")
