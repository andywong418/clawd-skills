#!/usr/bin/env python3
"""TikTok Downloader — download videos without watermark, with metadata.

Download strategies (in priority order):
  1. yt-dlp + Chrome cookies (best, no watermark, works when Chrome is logged into TikTok)
  2. yt-dlp + cookies file (~/.clawdbot/cookies/tiktok.txt, Netscape format)
  3. yt-dlp unauthenticated (may work for public videos)
  4. tikwm.com API (watermark-free, no auth needed, rate-limited)

Usage:
    # Single video
    python3 download.py https://www.tiktok.com/@user/video/123456789

    # Multiple URLs
    python3 download.py URL1 URL2 URL3

    # From a file (one URL per line)
    python3 download.py --file urls.txt

    # Audio only (MP3)
    python3 download.py URL --audio-only

    # Get metadata without downloading
    python3 download.py URL --metadata-only

    # Batch download a user's recent videos
    python3 download.py https://www.tiktok.com/@username --user --limit 10
"""

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.request
import urllib.error
import urllib.parse
from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

RAPIDAPI_KEY = "9f1125f9efmshdd74e372e4c5bbfp18f0d8jsn883283c7228b"
COOKIES_FILE = Path.home() / ".clawdbot" / "cookies" / "tiktok.txt"


def find_ytdlp() -> str:
    """Find yt-dlp — system install or bundled."""
    # System install (preferred)
    result = subprocess.run(["which", "yt-dlp"], capture_output=True, text=True)
    if result.returncode == 0:
        return result.stdout.strip()
    # Bundled in repo
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    bundled = repo_root / "bin" / "bin" / "yt-dlp"
    if bundled.exists():
        return str(bundled)
    raise RuntimeError(
        "yt-dlp not found. Install with: pip install yt-dlp  or  brew install yt-dlp"
    )


def safe_filename(text: str, max_len: int = 60) -> str:
    return re.sub(r"[^\w\s-]", "_", text)[:max_len].strip()


def extract_video_id(url: str) -> str | None:
    """Extract TikTok video ID from URL."""
    m = re.search(r"/video/(\d+)", url)
    return m.group(1) if m else None


# ---------------------------------------------------------------------------
# Strategy 1 & 2 & 3: yt-dlp
# ---------------------------------------------------------------------------

def build_ytdlp_cmd(
    url: str,
    output_template: str,
    audio_only: bool = False,
    metadata_only: bool = False,
    user_profile: bool = False,
    limit: int | None = None,
) -> list[str]:
    ytdlp = find_ytdlp()
    cmd = [ytdlp]

    if metadata_only:
        cmd += ["--dump-json", "--no-download"]
    elif audio_only:
        cmd += ["--extract-audio", "--audio-format", "mp3", "--audio-quality", "0"]
    else:
        # Prefer no-watermark format
        cmd += [
            "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "--merge-output-format", "mp4",
        ]

    if user_profile and limit:
        cmd += ["--playlist-end", str(limit)]

    if not metadata_only:
        cmd += ["-o", output_template]

    cmd += [
        "--no-warnings",
        "--quiet",
        "--no-playlist",  # single video unless user_profile
    ]

    if user_profile:
        cmd.remove("--no-playlist")
        cmd.append("--yes-playlist")

    cmd.append(url)
    return cmd


def try_ytdlp(
    url: str,
    output_template: str,
    audio_only: bool = False,
    metadata_only: bool = False,
    user_profile: bool = False,
    limit: int | None = None,
) -> tuple[bool, str]:
    """Try yt-dlp with multiple cookie strategies. Returns (success, stderr)."""
    base_cmd = build_ytdlp_cmd(url, output_template, audio_only, metadata_only, user_profile, limit)

    strategies = []

    # 1. Chrome browser cookies (best — no watermark)
    strategies.append(("Chrome cookies", ["--cookies-from-browser", "chrome"]))

    # 2. Cookies file (Netscape format)
    if COOKIES_FILE.exists():
        strategies.append(("Cookie file", ["--cookies", str(COOKIES_FILE)]))

    # 3. No cookies (public videos)
    strategies.append(("No auth", []))

    for label, extra_args in strategies:
        cmd = base_cmd[:-1] + extra_args + [base_cmd[-1]]  # insert before URL
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            return True, label
        if "blocked" in result.stderr.lower() or "private" in result.stderr.lower():
            continue  # try next strategy
        # Other errors — still try next
        continue

    # Return last stderr for debugging
    return False, result.stderr[-500:] if result else "no output"


# ---------------------------------------------------------------------------
# Strategy 4: tikwm.com (no-watermark, no auth, rate-limited)
# ---------------------------------------------------------------------------

TIKWM_API = "https://www.tikwm.com/api/"


def tikwm_fetch(url: str) -> dict | None:
    """Fetch video info from tikwm.com API."""
    data = urllib.parse.urlencode({"url": url, "hd": "1"}).encode()
    req = urllib.request.Request(
        TIKWM_API, data=data,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Mozilla/5.0 Chrome/120.0.0.0",
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read())
        if result.get("code") == 0:
            return result.get("data")
    except Exception:
        pass
    return None


def tikwm_download(url: str, output_dir: Path) -> dict | None:
    """Download via tikwm.com. Returns metadata dict or None."""
    data = tikwm_fetch(url)
    if not data:
        return None

    video_url = data.get("hdplay") or data.get("play")
    if not video_url:
        return None

    title = safe_filename(data.get("title", "tiktok_video"))
    video_id = data.get("id", extract_video_id(url) or "unknown")
    out_path = output_dir / f"{video_id}_{title}.mp4"

    req = urllib.request.Request(video_url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        out_path.write_bytes(resp.read())

    return {
        "path": str(out_path),
        "id": video_id,
        "title": data.get("title", ""),
        "author": data.get("author", {}).get("nickname", ""),
        "author_username": data.get("author", {}).get("unique_id", ""),
        "views": data.get("play_count", 0),
        "likes": data.get("digg_count", 0),
        "comments": data.get("comment_count", 0),
        "shares": data.get("share_count", 0),
        "duration": data.get("duration", 0),
        "music_title": data.get("music_info", {}).get("title", ""),
        "music_author": data.get("music_info", {}).get("author", ""),
        "url": url,
        "source": "tikwm",
    }


# ---------------------------------------------------------------------------
# Metadata extraction
# ---------------------------------------------------------------------------

def get_metadata(url: str) -> dict | None:
    """Get video metadata without downloading."""
    # Try yt-dlp first
    ytdlp = find_ytdlp()
    strategies = [
        ["--cookies-from-browser", "chrome"],
        ["--cookies", str(COOKIES_FILE)] if COOKIES_FILE.exists() else None,
        [],
    ]
    for extra in strategies:
        if extra is None:
            continue
        cmd = [ytdlp, "--dump-json", "--no-download", "--quiet", "--no-warnings"] + extra + [url]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            try:
                d = json.loads(result.stdout)
                return {
                    "id": d.get("id"),
                    "title": d.get("title"),
                    "author": d.get("uploader"),
                    "author_username": d.get("uploader_id"),
                    "views": d.get("view_count"),
                    "likes": d.get("like_count"),
                    "comments": d.get("comment_count"),
                    "shares": d.get("repost_count"),
                    "duration": d.get("duration"),
                    "thumbnail": d.get("thumbnail"),
                    "music_title": d.get("track"),
                    "music_author": d.get("artist"),
                    "url": url,
                    "source": "yt-dlp",
                }
            except json.JSONDecodeError:
                pass

    # Fall back to tikwm
    data = tikwm_fetch(url)
    if data:
        return {
            "id": data.get("id"),
            "title": data.get("title"),
            "author": data.get("author", {}).get("nickname"),
            "author_username": data.get("author", {}).get("unique_id"),
            "views": data.get("play_count"),
            "likes": data.get("digg_count"),
            "comments": data.get("comment_count"),
            "shares": data.get("share_count"),
            "duration": data.get("duration"),
            "thumbnail": data.get("cover"),
            "music_title": data.get("music_info", {}).get("title"),
            "music_author": data.get("music_info", {}).get("author"),
            "url": url,
            "source": "tikwm",
        }

    return None


# ---------------------------------------------------------------------------
# Download single video
# ---------------------------------------------------------------------------

def download_video(url: str, output_dir: Path, audio_only: bool = False) -> dict | None:
    """Download a single TikTok video. Returns metadata dict or None."""
    output_dir.mkdir(parents=True, exist_ok=True)
    video_id = extract_video_id(url) or "%(id)s"
    template = str(output_dir / f"{video_id}_%(uploader)s.%(ext)s")

    print(f"  Downloading: {url}")

    # Try yt-dlp strategies
    success, label = try_ytdlp(url, template, audio_only=audio_only)
    if success:
        # Find the downloaded file
        files = sorted(output_dir.glob(f"{video_id}*"), key=lambda p: p.stat().st_mtime)
        out_path = files[-1] if files else None
        print(f"  ✓ {out_path.name if out_path else 'downloaded'} [{label}]")
        meta = get_metadata(url) or {}
        if out_path:
            meta["path"] = str(out_path)
        meta["url"] = url
        return meta

    # Fall back to tikwm (no watermark, no auth)
    print(f"  yt-dlp failed — trying tikwm.com...")
    result = tikwm_download(url, output_dir)
    if result:
        print(f"  ✓ {Path(result['path']).name} [tikwm]")
        return result

    print(f"  ✗ All strategies failed for {url}", file=sys.stderr)
    return None


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

def fmt_count(n: int | None) -> str:
    if not n:
        return "—"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.0f}K"
    return str(n)


def print_metadata(meta: dict):
    print(f"\n  {'─' * 56}")
    print(f"  @{meta.get('author_username', '?')} — {meta.get('author', '')}")
    title = meta.get("title", "")
    if title:
        print(f"  {title[:80]}")
    print(f"  Views: {fmt_count(meta.get('views'))}  "
          f"Likes: {fmt_count(meta.get('likes'))}  "
          f"Comments: {fmt_count(meta.get('comments'))}")
    if meta.get("music_title"):
        print(f"  Music: {meta['music_title']} — {meta.get('music_author', '')}")
    if meta.get("path"):
        print(f"  Saved: {meta['path']}")
    print(f"  {'─' * 56}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Download TikTok videos without watermark")
    parser.add_argument("urls", nargs="*", help="TikTok video URL(s)")
    parser.add_argument("--file", "-f", help="File with one URL per line")
    parser.add_argument("--output", "-o", default="./downloads", help="Output directory (default: ./downloads)")
    parser.add_argument("--audio-only", action="store_true", help="Download audio as MP3 only")
    parser.add_argument("--metadata-only", action="store_true", help="Print metadata, don't download")
    parser.add_argument("--user", action="store_true", help="Download from a user profile URL")
    parser.add_argument("--limit", type=int, default=10, help="Max videos for --user (default: 10)")
    parser.add_argument("--json", action="store_true", dest="json_out", help="Output JSON")
    args = parser.parse_args()

    # Collect URLs
    urls = list(args.urls)
    if args.file:
        urls += [line.strip() for line in Path(args.file).read_text().splitlines()
                 if line.strip() and not line.startswith("#")]

    if not urls:
        parser.print_help()
        sys.exit(1)

    output_dir = Path(args.output)
    results = []

    if args.metadata_only:
        for url in urls:
            meta = get_metadata(url)
            if meta:
                if args.json_out:
                    results.append(meta)
                else:
                    print_metadata(meta)
            else:
                print(f"  ✗ Could not fetch metadata for {url}", file=sys.stderr)
    elif args.user:
        # Batch user profile download
        for url in urls:
            print(f"\n[tiktok-dl] Downloading up to {args.limit} videos from {url}")
            ytdlp = find_ytdlp()
            template = str(output_dir / "%(uploader_id)s_%(id)s.%(ext)s")
            cmd = [
                ytdlp,
                "--cookies-from-browser", "chrome",
                "--playlist-end", str(args.limit),
                "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
                "--merge-output-format", "mp4",
                "-o", template,
                "--quiet", "--progress",
                url,
            ]
            result = subprocess.run(cmd, timeout=300)
            if result.returncode != 0:
                print(f"  ✗ Failed", file=sys.stderr)
    else:
        print(f"\n[tiktok-dl] Downloading {len(urls)} video(s) → {output_dir}/")
        for url in urls:
            meta = download_video(url, output_dir, audio_only=args.audio_only)
            if meta:
                results.append(meta)
                if not args.json_out:
                    print_metadata(meta)

        print(f"\n[tiktok-dl] {len(results)}/{len(urls)} downloaded")

    if args.json_out and results:
        print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
