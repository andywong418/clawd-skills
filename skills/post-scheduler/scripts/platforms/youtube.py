"""YouTube Data API v3 — upload videos (Shorts or long-form).

Auth flow (one-time setup):
  python3 skills/post-scheduler/scripts/platforms/youtube_auth.py

Then credentials live in ~/.clawdbot/.env:
  YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, YOUTUBE_REFRESH_TOKEN
"""

import json
import os
import sys
import time
from pathlib import Path
import urllib.request
import urllib.error
import urllib.parse

TOKEN_URL = "https://oauth2.googleapis.com/token"
UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"
CHUNK_SIZE = 5 * 1024 * 1024  # 5 MB chunks


# ---------------------------------------------------------------------------
# Credentials
# ---------------------------------------------------------------------------

def _load_creds() -> dict:
    env = {}
    env_path = Path.home() / ".clawdbot" / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip()

    creds = {
        "client_id":     os.environ.get("YOUTUBE_CLIENT_ID")     or env.get("YOUTUBE_CLIENT_ID"),
        "client_secret": os.environ.get("YOUTUBE_CLIENT_SECRET") or env.get("YOUTUBE_CLIENT_SECRET"),
        "refresh_token": os.environ.get("YOUTUBE_REFRESH_TOKEN") or env.get("YOUTUBE_REFRESH_TOKEN"),
    }

    missing = [k for k, v in creds.items() if not v]
    if missing:
        raise RuntimeError(
            f"Missing YouTube credentials: {', '.join(missing)}\n"
            f"Run: python3 skills/post-scheduler/scripts/platforms/youtube_auth.py"
        )
    return creds


def _get_access_token(creds: dict) -> str:
    """Exchange refresh token for a fresh access token."""
    data = urllib.parse.urlencode({
        "grant_type":    "refresh_token",
        "client_id":     creds["client_id"],
        "client_secret": creds["client_secret"],
        "refresh_token": creds["refresh_token"],
    }).encode()

    req = urllib.request.Request(TOKEN_URL, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Token refresh failed {e.code}: {e.read().decode()}")

    if "access_token" not in result:
        raise RuntimeError(f"No access_token in response: {result}")

    return result["access_token"]


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------

def _init_resumable_upload(access_token: str, file_size: int, metadata: dict) -> str:
    """Start a resumable upload session. Returns the upload URL."""
    url = f"{UPLOAD_URL}?uploadType=resumable&part=snippet,status"
    body = json.dumps(metadata).encode()

    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Authorization", f"Bearer {access_token}")
    req.add_header("Content-Type", "application/json; charset=UTF-8")
    req.add_header("X-Upload-Content-Type", "video/mp4")
    req.add_header("X-Upload-Content-Length", str(file_size))

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            location = resp.headers.get("Location")
            if not location:
                raise RuntimeError("No Location header in resumable upload response")
            return location
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Upload init failed {e.code}: {e.read().decode()}")


def _upload_chunks(upload_url: str, video_path: str, file_size: int) -> dict:
    """Upload video in chunks. Returns the completed video resource."""
    uploaded = 0

    with open(video_path, "rb") as f:
        while uploaded < file_size:
            chunk = f.read(CHUNK_SIZE)
            chunk_len = len(chunk)
            content_range = f"bytes {uploaded}-{uploaded + chunk_len - 1}/{file_size}"

            req = urllib.request.Request(upload_url, data=chunk, method="PUT")
            req.add_header("Content-Length", str(chunk_len))
            req.add_header("Content-Range", content_range)

            try:
                with urllib.request.urlopen(req, timeout=300) as resp:
                    uploaded += chunk_len
                    pct = int(uploaded / file_size * 100)
                    print(f"  Uploaded {pct}% ({uploaded / 1024 / 1024:.1f} MB)")

                    # 200/201 means complete
                    if resp.status in (200, 201):
                        return json.loads(resp.read().decode())

            except urllib.error.HTTPError as e:
                if e.code == 308:
                    # 308 Resume Incomplete — expected for non-final chunks
                    uploaded += chunk_len
                    pct = int(uploaded / file_size * 100)
                    print(f"  Uploaded {pct}% ({uploaded / 1024 / 1024:.1f} MB)")
                else:
                    raise RuntimeError(f"Upload chunk failed {e.code}: {e.read().decode()}")

    raise RuntimeError("Upload loop ended without completion response")


def upload_video(
    video_path: str,
    title: str,
    description: str,
    tags: list[str] = None,
    privacy: str = "public",
    category_id: str = "22",   # 22 = People & Blogs; 24 = Entertainment
    is_shorts: bool = True,
    thumbnail_path: str = None,
) -> str:
    """Upload a video to YouTube. Returns the video ID."""
    path = Path(video_path)
    if not path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")

    file_size = path.stat().st_size
    creds = _load_creds()

    print(f"[youtube] Getting access token...")
    access_token = _get_access_token(creds)

    # Shorts: #Shorts must appear in title or description
    full_description = description
    if is_shorts and "#Shorts" not in description and "#Shorts" not in title:
        full_description = description + "\n\n#Shorts"

    metadata = {
        "snippet": {
            "title": title[:100],
            "description": full_description[:5000],
            "tags": (tags or [])[:500],
            "categoryId": category_id,
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
        },
    }

    print(f"[youtube] Initiating upload ({file_size / 1024 / 1024:.1f} MB)...")
    print(f"  Title: {title[:60]}")
    print(f"  Privacy: {privacy} | Shorts: {is_shorts}")

    upload_url = _init_resumable_upload(access_token, file_size, metadata)

    print(f"[youtube] Uploading...")
    result = _upload_chunks(upload_url, video_path, file_size)

    video_id = result.get("id")
    if not video_id:
        raise RuntimeError(f"No video ID in upload response: {result}")

    video_url = f"https://youtube.com/shorts/{video_id}" if is_shorts else f"https://youtube.com/watch?v={video_id}"
    print(f"[youtube] Uploaded: {video_url}")

    # Set custom thumbnail if provided
    if thumbnail_path:
        try:
            upload_thumbnail(video_id, thumbnail_path, access_token)
        except Exception as e:
            print(f"[youtube] Thumbnail upload failed (video still posted): {e}")

    return video_id


def upload_thumbnail(video_id: str, thumbnail_path: str, access_token: str = None) -> bool:
    """Set a custom thumbnail for a YouTube video. Returns True on success."""
    if not access_token:
        creds = _load_creds()
        access_token = _get_access_token(creds)

    path = Path(thumbnail_path)
    if not path.exists():
        raise FileNotFoundError(f"Thumbnail not found: {thumbnail_path}")

    ext = path.suffix.lower().lstrip(".")
    content_type = {"jpg": "image/jpeg", "jpeg": "image/jpeg",
                    "png": "image/png", "gif": "image/gif"}.get(ext, "image/jpeg")

    with open(path, "rb") as f:
        img_data = f.read()

    url = f"https://www.googleapis.com/upload/youtube/v3/thumbnails/set?videoId={video_id}&uploadType=media"
    req = urllib.request.Request(url, data=img_data, method="POST")
    req.add_header("Authorization", f"Bearer {access_token}")
    req.add_header("Content-Type", content_type)
    req.add_header("Content-Length", str(len(img_data)))

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            resp.read()
        print(f"[youtube] Thumbnail set for {video_id}")
        return True
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Thumbnail upload failed {e.code}: {e.read().decode()}")


def update_video(
    video_id: str,
    title: str = None,
    description: str = None,
    tags: list[str] = None,
    privacy: str = None,
    category_id: str = None,
) -> dict:
    """Update metadata for an existing YouTube video. Only provided fields are changed."""
    creds = _load_creds()
    access_token = _get_access_token(creds)

    # Fetch current snippet first so we don't clobber unset fields
    fetch_url = (
        f"https://www.googleapis.com/youtube/v3/videos"
        f"?part=snippet,status&id={video_id}"
    )
    req = urllib.request.Request(fetch_url)
    req.add_header("Authorization", f"Bearer {access_token}")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            current = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Fetch video failed {e.code}: {e.read().decode()}")

    items = current.get("items", [])
    if not items:
        raise RuntimeError(f"Video not found: {video_id}")

    current_snippet = items[0].get("snippet", {})
    current_status = items[0].get("status", {})

    snippet = {
        "title":      title       if title       is not None else current_snippet.get("title", ""),
        "description": description if description is not None else current_snippet.get("description", ""),
        "tags":        tags        if tags        is not None else current_snippet.get("tags", []),
        "categoryId":  category_id if category_id is not None else current_snippet.get("categoryId", "22"),
    }
    status = {
        "privacyStatus": privacy if privacy is not None else current_status.get("privacyStatus", "public"),
    }

    body = json.dumps({"id": video_id, "snippet": snippet, "status": status}).encode()
    update_url = "https://www.googleapis.com/youtube/v3/videos?part=snippet,status"
    req = urllib.request.Request(update_url, data=body, method="PUT")
    req.add_header("Authorization", f"Bearer {access_token}")
    req.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode())
        print(f"[youtube] Updated video {video_id}")
        return result
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Update video failed {e.code}: {e.read().decode()}")
