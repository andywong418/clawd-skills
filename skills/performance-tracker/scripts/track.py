#!/usr/bin/env python3
"""Performance Tracker — pull views/likes/comments/shares from TikTok, Instagram, Twitter.

Stores data to ~/.clawdbot/performance/ and runs Claude analysis of what's working.

Usage:
  python3 track.py @username --platform tiktok
  python3 track.py @username --platform all
  python3 track.py --analyze
  python3 track.py --analyze --platform tiktok
"""

import argparse
import json
import os
import subprocess
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

import anthropic


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _load_env(key: str) -> str | None:
    val = os.environ.get(key)
    if val:
        return val
    env_path = Path.home() / ".clawdbot" / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith(f"{key}="):
                    return line.split("=", 1)[1].strip()
    return None


def find_ytdlp() -> str:
    """Locate yt-dlp — bundled in repo or system-installed."""
    # skills/performance-tracker/scripts/ → repo root = 4 levels up
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    bundled = repo_root / "bin" / "bin" / "yt-dlp"
    if bundled.exists():
        return str(bundled)
    result = subprocess.run(["which", "yt-dlp"], capture_output=True, text=True)
    if result.returncode == 0:
        return result.stdout.strip()
    raise RuntimeError("yt-dlp not found. Run: pip install yt-dlp")


def get_storage_path(platform: str, username: str) -> Path:
    clean = username.lstrip("@").lower()
    storage_dir = Path.home() / ".clawdbot" / "performance"
    storage_dir.mkdir(parents=True, exist_ok=True)
    return storage_dir / f"{platform}_{clean}.json"


def load_stored(path: Path) -> dict:
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {"posts": []}


def save_stored(path: Path, data: dict):
    data["last_updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def compute_engagement_rate(metrics: dict) -> float:
    views = metrics.get("views", 0) or 0
    if views == 0:
        return 0.0
    likes = metrics.get("likes", 0) or 0
    comments = metrics.get("comments", 0) or 0
    shares = metrics.get("shares", 0) or 0
    return round((likes + comments + shares) / views, 4)


def fmt_count(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.0f}K"
    return str(n) if n else "0"


# ---------------------------------------------------------------------------
# Fetchers
# ---------------------------------------------------------------------------

def fetch_tiktok(username: str) -> list[dict]:
    """Fetch TikTok post metrics via yt-dlp (metadata only, no download)."""
    clean = username.lstrip("@")
    ytdlp = find_ytdlp()
    cookies = Path.home() / ".clawdbot" / "cookies" / "tiktok.txt"

    cmd = [ytdlp, "--dump-json", "--flat-playlist", "--no-warnings", "--quiet"]
    if cookies.exists():
        cmd += ["--cookies", str(cookies)]
    cmd.append(f"https://www.tiktok.com/@{clean}")

    print(f"[performance-tracker] Fetching TikTok: @{clean}", file=sys.stderr)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

    if result.returncode != 0 and not result.stdout.strip():
        err = result.stderr[:400] if result.stderr else "(no output)"
        print(f"[yt-dlp error] {err}", file=sys.stderr)
        return []

    posts = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue

        upload_raw = item.get("upload_date", "") or ""
        upload_date = (
            f"{upload_raw[:4]}-{upload_raw[4:6]}-{upload_raw[6:8]}"
            if len(upload_raw) == 8
            else upload_raw
        )

        posts.append({
            "id": str(item.get("id", "") or ""),
            "description": (item.get("description") or item.get("title") or "")[:200],
            "upload_date": upload_date,
            "views": item.get("view_count", 0) or 0,
            "likes": item.get("like_count", 0) or 0,
            "comments": item.get("comment_count", 0) or 0,
            "shares": item.get("repost_count", 0) or 0,
        })

    return posts


def fetch_instagram(username: str) -> list[dict]:
    """Fetch Instagram Reels metrics via yt-dlp (metadata only)."""
    clean = username.lstrip("@")
    ytdlp = find_ytdlp()
    cookies = Path.home() / ".clawdbot" / "cookies" / "instagram.txt"

    cmd = [ytdlp, "--dump-json", "--flat-playlist", "--no-warnings", "--quiet"]
    if cookies.exists():
        cmd += ["--cookies", str(cookies)]
    cmd.append(f"https://www.instagram.com/{clean}/reels/")

    print(f"[performance-tracker] Fetching Instagram: @{clean}", file=sys.stderr)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

    if result.returncode != 0 and not result.stdout.strip():
        err = result.stderr[:400] if result.stderr else "(no output)"
        print(f"[yt-dlp error] {err}", file=sys.stderr)
        return []

    posts = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue

        upload_raw = item.get("upload_date", "") or ""
        upload_date = (
            f"{upload_raw[:4]}-{upload_raw[4:6]}-{upload_raw[6:8]}"
            if len(upload_raw) == 8
            else upload_raw
        )

        posts.append({
            "id": str(item.get("id", "") or ""),
            "description": (item.get("description") or item.get("title") or "")[:200],
            "upload_date": upload_date,
            "views": item.get("view_count", 0) or 0,
            "likes": item.get("like_count", 0) or 0,
            "comments": item.get("comment_count", 0) or 0,
            "shares": 0,  # Instagram does not expose share counts
        })

    return posts


def _yt_access_token() -> str:
    """Get a fresh YouTube access token via refresh token."""
    import urllib.parse
    env = {}
    env_path = Path.home() / ".clawdbot" / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip()

    client_id     = os.environ.get("YOUTUBE_CLIENT_ID")     or env.get("YOUTUBE_CLIENT_ID")
    client_secret = os.environ.get("YOUTUBE_CLIENT_SECRET") or env.get("YOUTUBE_CLIENT_SECRET")
    refresh_token = os.environ.get("YOUTUBE_REFRESH_TOKEN") or env.get("YOUTUBE_REFRESH_TOKEN")

    if not all([client_id, client_secret, refresh_token]):
        raise RuntimeError(
            "YouTube credentials not set.\n"
            "Run: python3 skills/post-scheduler/scripts/queue.py auth youtube"
        )

    data = urllib.parse.urlencode({
        "grant_type":    "refresh_token",
        "client_id":     client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
    }).encode()
    req = urllib.request.Request("https://oauth2.googleapis.com/token", data=data, method="POST")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())["access_token"]


def fetch_youtube(username: str = None) -> list[dict]:
    """Fetch YouTube channel video stats via YouTube Data API v3."""
    import urllib.parse

    print(f"[performance-tracker] Fetching YouTube channel stats", file=sys.stderr)
    access_token = _yt_access_token()
    headers = {"Authorization": f"Bearer {access_token}"}
    YT = "https://www.googleapis.com/youtube/v3"

    def yt_get(endpoint: str, params: dict) -> dict:
        url = f"{YT}/{endpoint}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"YouTube API {e.code}: {e.read().decode()[:400]}")

    # Get own channel ID
    channels = yt_get("channels", {"part": "id,snippet", "mine": "true"})
    items = channels.get("items", [])
    if not items:
        raise RuntimeError("No YouTube channel found for these credentials")

    channel_id = items[0]["id"]
    channel_title = items[0]["snippet"]["title"]
    print(f"[performance-tracker] Channel: {channel_title} ({channel_id})", file=sys.stderr)

    # Get recent 50 videos
    search = yt_get("search", {
        "part": "snippet",
        "channelId": channel_id,
        "type": "video",
        "order": "date",
        "maxResults": 50,
    })
    video_ids = [item["id"]["videoId"] for item in search.get("items", [])]
    if not video_ids:
        print(f"[performance-tracker] No videos found", file=sys.stderr)
        return []

    # Batch fetch stats
    stats_result = yt_get("videos", {
        "part": "statistics,snippet",
        "id": ",".join(video_ids),
    })

    posts = []
    for item in stats_result.get("items", []):
        stats   = item.get("statistics", {})
        snippet = item.get("snippet", {})
        title   = snippet.get("title", "")
        desc    = snippet.get("description", "")
        is_shorts = "#shorts" in (title + " " + desc).lower()

        posts.append({
            "id":          item.get("id", ""),
            "description": f"{title} | {desc[:80]}".strip(" |"),
            "upload_date": snippet.get("publishedAt", "")[:10],
            "views":       int(stats.get("viewCount",   0) or 0),
            "likes":       int(stats.get("likeCount",   0) or 0),
            "comments":    int(stats.get("commentCount", 0) or 0),
            "shares":      0,   # YouTube API does not expose share counts
            "is_shorts":   is_shorts,
            "url":         f"https://youtube.com/{'shorts/' if is_shorts else 'watch?v='}{item.get('id', '')}",
        })

    return posts


def fetch_twitter(username: str) -> list[dict]:
    """Fetch Twitter/X post metrics via Twitter API v2."""
    clean = username.lstrip("@")
    token = _load_env("TWITTER_BEARER_TOKEN")
    if not token:
        raise RuntimeError(
            "TWITTER_BEARER_TOKEN not set. Add it to ~/.clawdbot/.env\n"
            "Get a free bearer token at https://developer.twitter.com/"
        )

    headers = {"Authorization": f"Bearer {token}"}

    # Step 1: resolve username → user ID
    print(f"[performance-tracker] Fetching Twitter: @{clean}", file=sys.stderr)
    user_url = f"https://api.twitter.com/2/users/by/username/{clean}"
    req = urllib.request.Request(user_url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            user_data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:400]
        raise RuntimeError(f"Twitter API error {e.code}: {body}") from e

    user_id = user_data.get("data", {}).get("id")
    if not user_id:
        raise RuntimeError(f"Could not find Twitter user: @{clean}")

    # Step 2: fetch recent tweets with public metrics
    tweets_url = (
        f"https://api.twitter.com/2/users/{user_id}/tweets"
        f"?tweet.fields=public_metrics,created_at,text"
        f"&max_results=20"
        f"&exclude=retweets,replies"
    )
    req = urllib.request.Request(tweets_url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            tweets_data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:400]
        raise RuntimeError(f"Twitter API error {e.code}: {body}") from e

    posts = []
    for tweet in tweets_data.get("data", []):
        metrics = tweet.get("public_metrics", {})
        created = tweet.get("created_at", "")
        upload_date = created[:10] if created else ""  # YYYY-MM-DD

        posts.append({
            "id": tweet.get("id", ""),
            "description": (tweet.get("text") or "")[:200],
            "upload_date": upload_date,
            "views": metrics.get("impression_count", 0) or 0,
            "likes": metrics.get("like_count", 0) or 0,
            "comments": metrics.get("reply_count", 0) or 0,
            "shares": (metrics.get("retweet_count", 0) or 0) + (metrics.get("quote_count", 0) or 0),
        })

    return posts


# ---------------------------------------------------------------------------
# Track + merge
# ---------------------------------------------------------------------------

def track_platform(username: str, platform: str) -> dict:
    """Fetch metrics for one platform, merge with stored data, return updated data."""
    clean = username.lstrip("@").lower()
    path = get_storage_path(platform, clean)
    stored = load_stored(path)

    fetch_fn = {
        "tiktok":    fetch_tiktok,
        "instagram": fetch_instagram,
        "twitter":   fetch_twitter,
        "youtube":   fetch_youtube,
    }[platform]

    new_posts = fetch_fn(username)

    if not new_posts:
        print(
            f"[performance-tracker] Warning: 0 posts returned for @{clean} on {platform}. "
            "Check cookies or account visibility.",
            file=sys.stderr,
        )
    else:
        print(f"[performance-tracker] Got {len(new_posts)} posts from {platform}", file=sys.stderr)

    # Merge by post ID
    existing = {p["id"]: p for p in stored.get("posts", [])}
    for post in new_posts:
        post["engagement_rate"] = compute_engagement_rate(post)
        existing[post["id"]] = post

    data = {
        "platform": platform,
        "username": clean,
        "posts": list(existing.values()),
    }

    save_stored(path, data)
    print(f"[performance-tracker] Saved {len(data['posts'])} posts → {path}", file=sys.stderr)
    return data


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

def print_summary(data: dict):
    posts = data.get("posts", [])
    platform = data.get("platform", "")
    username = data.get("username", "")

    print(f"\n=== {platform.upper()} @{username} — {len(posts)} posts ===\n")
    if not posts:
        print("  (no posts)\n")
        return

    sorted_posts = sorted(posts, key=lambda p: p.get("views", 0), reverse=True)[:20]
    header = f"  {'#':<3} {'Views':<9} {'Likes':<8} {'Cmts':<7} {'Shares':<8} {'ER%':<6} Description"
    print(header)
    print("  " + "-" * 80)
    for i, post in enumerate(sorted_posts, 1):
        desc = post.get("description", "")[:45].replace("\n", " ")
        er = f"{post.get('engagement_rate', 0) * 100:.2f}%"
        print(
            f"  {i:<3} {fmt_count(post.get('views', 0)):<9} "
            f"{fmt_count(post.get('likes', 0)):<8} "
            f"{fmt_count(post.get('comments', 0)):<7} "
            f"{fmt_count(post.get('shares', 0)):<8} "
            f"{er:<6} {desc}"
        )
    print()


# ---------------------------------------------------------------------------
# Claude analysis
# ---------------------------------------------------------------------------

def analyze(platform: str | None = None):
    storage_dir = Path.home() / ".clawdbot" / "performance"
    if not storage_dir.exists():
        print("No performance data found. Run track.py first.", file=sys.stderr)
        sys.exit(1)

    pattern = f"{platform}_*.json" if platform else "*.json"
    files = list(storage_dir.glob(pattern))
    if not files:
        print(f"No data files matching {pattern} in {storage_dir}", file=sys.stderr)
        sys.exit(1)

    all_data = []
    for f in files:
        with open(f) as fp:
            all_data.append(json.load(fp))

    # Build summary for Claude
    summary_parts = []
    for data in all_data:
        plat = data.get("platform", "unknown")
        user = data.get("username", "unknown")
        posts = sorted(data.get("posts", []), key=lambda p: p.get("views", 0), reverse=True)
        top = posts[:10]

        lines = [f"\n## {plat.upper()} @{user} ({len(posts)} total posts)\n"]
        for i, p in enumerate(top, 1):
            er = f"{p.get('engagement_rate', 0) * 100:.2f}%"
            desc = p.get("description", "")[:100].replace("\n", " ")
            lines.append(
                f"{i}. Views: {fmt_count(p.get('views', 0))} | "
                f"Likes: {fmt_count(p.get('likes', 0))} | "
                f"ER: {er} | "
                f"Date: {p.get('upload_date', '?')} | "
                f"{desc}"
            )
        summary_parts.append("\n".join(lines))

    summary = "\n".join(summary_parts)

    api_key = _load_env("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not found in environment or ~/.clawdbot/.env")

    client = anthropic.Anthropic(api_key=api_key)

    system = """You are a viral content strategist analyzing social media performance data.
Given metrics from TikTok, Instagram, and/or Twitter, provide actionable insights.

Structure your analysis with these sections:
1. **Top 3 Posts** — what made them perform (hook type, topic, timing, format)
2. **What's Working** — patterns across high-performers (content themes, formats, posting times)
3. **Engagement Patterns** — which posts get comments vs saves vs shares, and why
4. **What To Do More Of** — 3-5 specific, actionable content ideas based on the data

Be specific — reference actual post descriptions and metrics. Avoid generic advice."""

    print("[performance-tracker] Running Claude analysis...\n", file=sys.stderr)

    with client.messages.stream(
        model="claude-haiku-4-5-20251001",
        max_tokens=1500,
        system=system,
        messages=[{"role": "user", "content": f"Analyze this performance data:\n{summary}"}],
    ) as stream:
        result = stream.get_final_message()

    text = "\n".join(block.text for block in result.content if block.type == "text")
    print(text.strip())


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Track social media performance metrics across platforms",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 track.py @realskytan --platform tiktok
  python3 track.py @realskytan --platform all
  python3 track.py --analyze
  python3 track.py --analyze --platform tiktok
""",
    )
    parser.add_argument(
        "username",
        nargs="?",
        help="Account handle (with or without @). Not needed with --analyze.",
    )
    parser.add_argument(
        "--platform",
        choices=["tiktok", "instagram", "twitter", "youtube", "all"],
        default="tiktok",
        help="Platform to fetch from (default: tiktok)",
    )
    parser.add_argument(
        "--analyze",
        action="store_true",
        help="Run Claude analysis on all stored performance data",
    )

    args = parser.parse_args()

    if args.analyze:
        plat = None if args.platform == "all" else args.platform
        try:
            analyze(platform=plat)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        return

    if not args.username:
        parser.error("username is required unless --analyze is specified")

    if args.platform == "all":
        for platform in ["tiktok", "instagram", "twitter", "youtube"]:
            try:
                data = track_platform(args.username, platform)
                print_summary(data)
            except Exception as e:
                print(f"[{platform}] Error: {e}", file=sys.stderr)
                continue
    else:
        try:
            data = track_platform(args.username, args.platform)
            print_summary(data)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
