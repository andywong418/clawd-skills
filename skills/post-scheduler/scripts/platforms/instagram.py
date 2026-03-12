"""Instagram Graph API client for posting Reels."""

import json
import os
import time
from pathlib import Path
import urllib.request
import urllib.error
import urllib.parse

GRAPH_URL = "https://graph.instagram.com/v22.0"


def _load_creds() -> tuple[str, str]:
    env = {}
    env_path = Path.home() / ".clawdbot" / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip()
    token = os.environ.get("INSTAGRAM_ACCESS_TOKEN") or env.get("INSTAGRAM_ACCESS_TOKEN")
    user_id = os.environ.get("INSTAGRAM_USER_ID") or env.get("INSTAGRAM_USER_ID")
    if not token or not user_id:
        raise RuntimeError(
            "INSTAGRAM_ACCESS_TOKEN and INSTAGRAM_USER_ID required in ~/.clawdbot/.env\n"
            "Get via Meta Developer Portal → Instagram Graph API → long-lived token."
        )
    return token, user_id


def _upload_to_fal(video_path: str) -> str:
    """Upload video to fal.ai storage and return public URL."""
    fal_key = None
    env_path = Path.home() / ".clawdbot" / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                if line.startswith("FAL_API_KEY="):
                    fal_key = line.split("=", 1)[1].strip()
    fal_key = fal_key or os.environ.get("FAL_API_KEY")
    if not fal_key:
        raise RuntimeError("FAL_API_KEY needed to host video for Instagram API")

    path = Path(video_path)
    with open(path, "rb") as f:
        video_data = f.read()

    init_req = urllib.request.Request(
        "https://fal.run/api/storage/upload/initiate",
        data=json.dumps({"file_name": path.name, "content_type": "video/mp4"}).encode(),
        headers={"Authorization": f"Key {fal_key}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(init_req, timeout=30) as resp:
        upload_info = json.loads(resp.read().decode())

    put_req = urllib.request.Request(upload_info["upload_url"], data=video_data, method="PUT")
    put_req.add_header("Content-Type", "video/mp4")
    with urllib.request.urlopen(put_req, timeout=300):
        pass

    return upload_info["file_url"]


def _graph_post(path: str, token: str, params: dict) -> dict:
    params["access_token"] = token
    req = urllib.request.Request(
        f"{GRAPH_URL}/{path}",
        data=urllib.parse.urlencode(params).encode(),
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Instagram API {e.code}: {e.read().decode()}")


def _graph_get(path: str, token: str, fields: str) -> dict:
    params = urllib.parse.urlencode({"access_token": token, "fields": fields})
    req = urllib.request.Request(f"{GRAPH_URL}/{path}?{params}")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Instagram API {e.code}: {e.read().decode()}")


def post_reel(video_path: str, caption: str) -> str:
    """Upload and publish a Reel to Instagram. Returns media_id."""
    token, user_id = _load_creds()

    print(f"[instagram] Hosting video...")
    video_url = _upload_to_fal(video_path)
    print(f"  URL: {video_url}")

    print(f"[instagram] Creating media container...")
    result = _graph_post(f"{user_id}/media", token, {
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
        "share_to_feed": "true",
    })
    container_id = result.get("id")
    if not container_id:
        raise RuntimeError(f"No container ID: {result}")

    print(f"[instagram] Processing ({container_id})...")
    for _ in range(24):
        time.sleep(5)
        status = _graph_get(container_id, token, "status_code,status")
        code = status.get("status_code", "UNKNOWN")
        print(f"  {code}")
        if code == "FINISHED":
            break
        if code in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Instagram processing failed: {status}")

    result = _graph_post(f"{user_id}/media_publish", token, {"creation_id": container_id})
    media_id = result.get("id")
    if not media_id:
        raise RuntimeError(f"Publish failed: {result}")

    print(f"[instagram] Published. media_id={media_id}")
    return media_id
