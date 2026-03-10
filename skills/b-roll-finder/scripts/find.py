#!/usr/bin/env python3
"""B-Roll Finder — search and download royalty-free footage matching a script beat.

Pipeline:
  1. Use Claude (optional) to extract 3 Pexels search queries from beat description
  2. Search Pexels video API for each query
  3. Download the best HD match
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


# ---------------------------------------------------------------------------
# Env helper
# ---------------------------------------------------------------------------

def _load_env(key: str) -> str | None:
    val = os.environ.get(key)
    if val:
        return val
    env_path = Path.home() / ".clawdbot" / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                if line.startswith(f"{key}="):
                    return line.split("=", 1)[1].strip()
    return None


# ---------------------------------------------------------------------------
# Claude: extract search queries from beat description
# ---------------------------------------------------------------------------

def extract_search_queries(beat: str, api_key: str) -> list[str]:
    """Use Claude haiku to extract 3 Pexels-friendly search queries."""
    import anthropic

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=256,
        messages=[{
            "role": "user",
            "content": (
                f"Given this script beat description, give me 3 short search queries "
                f"(2-4 words each) to find matching royalty-free b-roll footage on Pexels. "
                f"Return ONLY a JSON array of 3 strings, nothing else.\n\n"
                f"Beat: {beat}"
            ),
        }],
    )
    text = response.content[0].text.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    queries = json.loads(text.strip())
    return [str(q) for q in queries[:3]]


def fallback_queries(beat: str) -> list[str]:
    """Simple keyword extraction without Claude."""
    # Remove common filler words
    stop = {"a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
            "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
            "have", "has", "that", "this", "it", "as", "into", "show", "shows",
            "showing", "person", "someone", "people"}
    words = [w.strip(".,!?;:") for w in beat.lower().split() if w.strip(".,!?;:") not in stop]
    # Return the full beat + a shortened version
    return [
        beat[:60],
        " ".join(words[:4]),
        " ".join(words[:3]),
    ]


# ---------------------------------------------------------------------------
# Pexels API
# ---------------------------------------------------------------------------

def search_pexels_videos(
    query: str,
    api_key: str,
    orientation: str = "portrait",
    per_page: int = 5,
) -> list[dict]:
    params = urllib.parse.urlencode({
        "query": query,
        "orientation": orientation,
        "per_page": per_page,
        "size": "medium",
    })
    url = f"https://api.pexels.com/videos/search?{params}"
    req = urllib.request.Request(url, headers={"Authorization": api_key})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
            return data.get("videos", [])
    except urllib.error.HTTPError as e:
        print(f"  Pexels error {e.code} for query '{query}': {e.read().decode()[:200]}", file=sys.stderr)
        return []


def select_best_video_file(video: dict, orientation: str) -> dict | None:
    """Pick the best quality video file from a Pexels video result."""
    files = video.get("video_files", [])
    if not files:
        return None

    # Filter by orientation/aspect ratio
    if orientation == "portrait":
        preferred = [f for f in files if f.get("height", 0) > f.get("width", 0)]
    else:
        preferred = [f for f in files if f.get("width", 0) >= f.get("height", 0)]

    candidates = preferred if preferred else files

    # Sort by resolution preference: HD (1080p) > SD (720p) > others
    def quality_score(f):
        h = f.get("height", 0)
        q = f.get("quality", "")
        if q == "hd" or h >= 1080:
            return 3
        if q == "sd" or h >= 720:
            return 2
        return 1

    candidates.sort(key=quality_score, reverse=True)
    return candidates[0]


def download_video(url: str, output_path: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        total = int(resp.headers.get("Content-Length", 0))
        downloaded = 0
        chunk_size = 1024 * 64
        with open(output_path, "wb") as f:
            while True:
                chunk = resp.read(chunk_size)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                if total:
                    pct = downloaded / total * 100
                    print(f"\r  Downloading... {pct:.0f}% ({downloaded // 1024} KB)", end="", file=sys.stderr)
    print(file=sys.stderr)  # newline after progress


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Find and download royalty-free b-roll for a script beat",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 find.py "person checking their phone nervously in a waiting room"
  python3 find.py "aerial city at night neon lights" --count 3
  python3 find.py "barber cutting hair close up" --orientation portrait --output ./footage/beat1
""",
    )
    parser.add_argument("beat", help="Script beat description (natural language)")
    parser.add_argument("--count", type=int, default=1,
                        help="Number of clips to download (default: 1)")
    parser.add_argument("--orientation", choices=["portrait", "landscape"], default="portrait",
                        help="Video orientation (default: portrait for TikTok)")
    parser.add_argument("--output", default="./output/broll",
                        help="Output directory (default: ./output/broll)")
    args = parser.parse_args()

    pexels_key = _load_env("PEXELS_API_KEY")
    if not pexels_key:
        print("Error: PEXELS_API_KEY not found in environment or ~/.clawdbot/.env", file=sys.stderr)
        print("Get a free key at https://www.pexels.com/api/", file=sys.stderr)
        sys.exit(1)

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate search queries
    anthropic_key = _load_env("ANTHROPIC_API_KEY")
    if anthropic_key:
        print("[b-roll-finder] Generating search queries with Claude...", file=sys.stderr)
        try:
            queries = extract_search_queries(args.beat, anthropic_key)
            print(f"  Queries: {queries}", file=sys.stderr)
        except Exception as e:
            print(f"  Claude failed ({e}), falling back to keyword extraction", file=sys.stderr)
            queries = fallback_queries(args.beat)
    else:
        print("[b-roll-finder] No ANTHROPIC_API_KEY — using keyword extraction", file=sys.stderr)
        queries = fallback_queries(args.beat)
        print(f"  Queries: {queries}", file=sys.stderr)

    # Search Pexels with each query, collect unique results
    print(f"\n[b-roll-finder] Searching Pexels ({args.orientation})...", file=sys.stderr)
    seen_ids = set()
    candidates = []

    for query in queries:
        videos = search_pexels_videos(query, pexels_key, args.orientation, per_page=5)
        print(f"  '{query}' → {len(videos)} results", file=sys.stderr)
        for v in videos:
            if v["id"] not in seen_ids:
                seen_ids.add(v["id"])
                best_file = select_best_video_file(v, args.orientation)
                if best_file:
                    candidates.append({
                        "id": v["id"],
                        "duration": v.get("duration", 0),
                        "url": v.get("url", ""),
                        "file": best_file,
                    })
        if len(candidates) >= args.count * 3:
            break

    if not candidates:
        # Fallback: try landscape if portrait had no results
        if args.orientation == "portrait":
            print("  No portrait results — retrying with landscape...", file=sys.stderr)
            for query in queries[:2]:
                videos = search_pexels_videos(query, pexels_key, "landscape", per_page=5)
                for v in videos:
                    if v["id"] not in seen_ids:
                        seen_ids.add(v["id"])
                        best_file = select_best_video_file(v, "landscape")
                        if best_file:
                            candidates.append({
                                "id": v["id"],
                                "duration": v.get("duration", 0),
                                "url": v.get("url", ""),
                                "file": best_file,
                            })

    if not candidates:
        print("Error: no results found on Pexels for this beat", file=sys.stderr)
        sys.exit(1)

    # Download top N
    to_download = candidates[:args.count]
    downloaded = []

    print(f"\n[b-roll-finder] Downloading {len(to_download)} clip(s)...", file=sys.stderr)
    for i, item in enumerate(to_download, 1):
        file_info = item["file"]
        ext = file_info.get("file_type", "video/mp4").split("/")[-1]
        out_path = output_dir / f"broll_{i}_{item['id']}.{ext}"

        quality = file_info.get("quality", "?")
        w = file_info.get("width", 0)
        h = file_info.get("height", 0)
        print(f"  [{i}] {quality} {w}x{h}, {item['duration']}s → {out_path.name}", file=sys.stderr)

        download_video(file_info["link"], out_path)
        downloaded.append(out_path)

    print(f"\n✓ Downloaded {len(downloaded)} clip(s) to {output_dir}", file=sys.stderr)
    for p in downloaded:
        print(str(p))


if __name__ == "__main__":
    main()
