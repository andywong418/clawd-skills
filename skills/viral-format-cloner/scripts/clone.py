#!/usr/bin/env python3
"""
Viral Format Cloner — when your content hits, multiply it.

Monitors your own posted content. When something crosses viral thresholds,
auto-generates 3 hook variations and queues them to the post-scheduler.

Usage:
  python3 clone.py check                  # Scan for viral hits, auto-queue variations
  python3 clone.py check --dry-run        # Preview without queuing
  python3 clone.py list-hits              # Show posts that triggered cloning
  python3 clone.py clone <post_id>        # Manually clone a specific post
  python3 clone.py status                 # Show cloned content queue
"""

import argparse
import json
import os
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

ENV_FILE = Path.home() / ".clawdbot" / ".env"
QUEUE_FILE = Path.home() / ".clawdbot" / "post-queue.json"
STATE_DIR = Path.home() / ".clawdbot" / "viral-format-cloner"
HITS_FILE = STATE_DIR / "hits.json"
SLACK_CHANNEL = "C0AHBK5E9V3"
QUEUE_SCRIPT = Path(__file__).parent.parent.parent / "post-scheduler" / "scripts" / "queue.py"

THRESHOLDS = {
    "instagram": 100_000,
    "instagram_story": 100_000,
    "tiktok": 500_000,
    "twitter": 100_000,
    "youtube": 50_000,
    "threads": 100_000,
    "bluesky": 100_000,
}

CLAUDE_MODEL = "claude-haiku-3-5"


# ---------------------------------------------------------------------------
# Env loading
# ---------------------------------------------------------------------------

def load_env() -> dict:
    """Load key=value pairs from ~/.clawdbot/.env into os.environ."""
    env = {}
    if not ENV_FILE.exists():
        return env
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        env[key] = val
        os.environ.setdefault(key, val)
    return env


# ---------------------------------------------------------------------------
# State helpers
# ---------------------------------------------------------------------------

def load_hits() -> dict:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    if not HITS_FILE.exists():
        return {}
    try:
        return json.loads(HITS_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def save_hits(hits: dict):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    HITS_FILE.write_text(json.dumps(hits, indent=2))


def load_queue() -> list:
    if not QUEUE_FILE.exists():
        return []
    try:
        return json.loads(QUEUE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return []


# ---------------------------------------------------------------------------
# Threshold helpers
# ---------------------------------------------------------------------------

def get_threshold(platform: str, override: int | None) -> int:
    if override is not None:
        return override
    return THRESHOLDS.get(platform.lower(), 100_000)


def get_view_count(entry: dict) -> int:
    """Pull view/impression count from a queue entry. Returns 0 if not present."""
    for key in ("view_count", "views", "impression_count", "impressions", "play_count"):
        val = entry.get(key)
        if val is not None:
            try:
                return int(val)
            except (ValueError, TypeError):
                pass
    return 0


# ---------------------------------------------------------------------------
# Claude — generate hook variations
# ---------------------------------------------------------------------------

def generate_variations(caption: str, platform: str, views: int, api_key: str) -> list[str]:
    """Call Claude Haiku to generate 3 hook variations. Returns list of 3 strings."""
    try:
        import anthropic
    except ImportError:
        print("ERROR: anthropic package not installed. Run: pip install anthropic", file=sys.stderr)
        return []

    views_fmt = f"{views:,}"
    prompt = f"""You are a social media content expert specializing in viral content for {platform}.

Here is a post that got {views_fmt} views on {platform}:

---
{caption}
---

Generate exactly 3 variations of this post. Each variation must:
1. Keep the SAME core topic, angle, and value proposition
2. Keep the SAME overall structure and length
3. Keep the SAME call-to-action (if any)
4. Only change the OPENING HOOK (first 1-2 sentences)

Make each hook distinct — try different angles:
- Variation 1: Question or curiosity hook
- Variation 2: Bold/contrarian statement hook
- Variation 3: Story/personal hook ("I was...")

Return ONLY a valid JSON array of 3 strings. No explanation, no markdown, no code blocks. Just the raw JSON array.

Example format:
["Caption variation 1 here...", "Caption variation 2 here...", "Caption variation 3 here..."]"""

    try:
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = message.content[0].text.strip()

        # Strip markdown code fences if Claude wrapped it anyway
        if raw.startswith("```"):
            lines = raw.split("\n")
            raw = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

        variations = json.loads(raw)
        if isinstance(variations, list) and len(variations) >= 3:
            return [str(v) for v in variations[:3]]
        print(f"WARNING: Claude returned unexpected format: {raw[:200]}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"ERROR generating variations: {e}", file=sys.stderr)
        return []


# ---------------------------------------------------------------------------
# Post-scheduler integration
# ---------------------------------------------------------------------------

def queue_variation(platform: str, video_path: str, caption: str, dry_run: bool) -> str | None:
    """Add one variation to the post queue. Returns queue ID on success."""
    if dry_run:
        print(f"  [dry-run] Would queue to {platform}: {caption[:80]}...")
        return None

    if not QUEUE_SCRIPT.exists():
        print(f"WARNING: queue.py not found at {QUEUE_SCRIPT}", file=sys.stderr)
        return None

    cmd = [
        sys.executable, str(QUEUE_SCRIPT),
        "add", platform, video_path, caption,
        "--optimal",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            print(f"WARNING: queue.py returned {result.returncode}: {result.stderr.strip()}", file=sys.stderr)
            return None
        # queue.py prints "Added to queue: <id>" or similar; try to parse the ID
        output = result.stdout.strip()
        for line in output.splitlines():
            # Look for an 8-char hex ID in the output
            parts = line.split()
            for part in parts:
                if len(part) == 8 and all(c in "0123456789abcdef" for c in part.lower()):
                    return part
        # Fallback — return a timestamp-based pseudo ID
        return f"cloned-{datetime.now().strftime('%H%M%S')}"
    except subprocess.TimeoutExpired:
        print("WARNING: queue.py timed out", file=sys.stderr)
        return None
    except Exception as e:
        print(f"WARNING: failed to call queue.py: {e}", file=sys.stderr)
        return None


# ---------------------------------------------------------------------------
# Slack reporting
# ---------------------------------------------------------------------------

def slack_report(message: str, token: str, dry_run: bool):
    if dry_run or not token:
        if not token:
            print("(Slack token missing — skipping report)")
        return
    try:
        data = json.dumps({"channel": SLACK_CHANNEL, "text": message}).encode()
        req = urllib.request.Request(
            "https://slack.com/api/chat.postMessage",
            data=data,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
        )
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"WARNING: Slack report failed: {e}", file=sys.stderr)


def format_slack_report(hit: dict) -> str:
    views_fmt = f"{hit['views']:,}"
    platform = hit["platform"].capitalize()
    n = len(hit.get("variations", []))
    queued = len([q for q in hit.get("queued_ids", []) if q])

    lines = [
        f"*Viral Format Cloner* — hit detected on {platform}",
        f"*Views:* {views_fmt}  |  *Post ID:* `{hit.get('post_id', '?')}`",
        f"*Original caption:* {hit['caption'][:120]}{'...' if len(hit['caption']) > 120 else ''}",
        "",
        f"Generated {n} hook variations, queued {queued}:",
    ]
    for i, variation in enumerate(hit.get("variations", []), 1):
        lines.append(f"  {i}. {variation[:100]}{'...' if len(variation) > 100 else ''}")

    if hit.get("original_url"):
        lines.append(f"\n*Original:* {hit['original_url']}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Core — process one hit
# ---------------------------------------------------------------------------

def process_hit(entry: dict, hits: dict, dry_run: bool, api_key: str, slack_token: str, force: bool = False) -> dict | None:
    """
    Process a single viral hit. Returns the hit record if successful, None otherwise.
    Modifies `hits` dict in-place.
    """
    post_id = entry.get("id", "")
    platform = entry.get("platform", "")
    views = get_view_count(entry)
    caption = entry.get("caption", "")
    video_path = entry.get("video", "")
    original_url = entry.get("url") or entry.get("post_url") or entry.get("original_url") or ""

    if not post_id:
        print(f"WARNING: skipping entry with no ID: {json.dumps(entry)[:100]}", file=sys.stderr)
        return None

    if not force and post_id in hits:
        return None  # Already cloned

    print(f"\nProcessing viral hit: {post_id} ({platform}, {views:,} views)")

    if not caption:
        print(f"  WARNING: no caption found for {post_id}, skipping")
        return None

    # Generate variations
    print(f"  Generating hook variations via Claude...")
    variations = generate_variations(caption, platform, views, api_key)
    if not variations:
        print(f"  ERROR: failed to generate variations for {post_id}")
        return None

    print(f"  Got {len(variations)} variations")

    # Queue each variation
    queued_ids = []
    for i, variation in enumerate(variations, 1):
        print(f"  Queueing variation {i}...")
        if video_path and Path(video_path).exists():
            qid = queue_variation(platform, video_path, variation, dry_run)
            queued_ids.append(qid or "")
            if qid:
                print(f"    Queued as {qid}")
            elif not dry_run:
                print(f"    Failed to queue (no ID returned)")
        else:
            if video_path:
                print(f"  WARNING: video_path {video_path!r} not found — caption queued without video")
            else:
                print(f"  NOTE: no video_path — skipping queue for variation {i}")
            queued_ids.append("")

    hit_record = {
        "post_id": post_id,
        "original_url": original_url,
        "platform": platform,
        "views": views,
        "caption": caption,
        "video_path": video_path,
        "cloned_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "variations": variations,
        "queued_ids": queued_ids,
    }

    if not dry_run:
        hits[post_id] = hit_record
        save_hits(hits)

    # Slack report
    slack_report(format_slack_report(hit_record), slack_token, dry_run)

    return hit_record


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_check(args, env: dict):
    api_key = env.get("ANTHROPIC_API_KEY", "")
    slack_token = env.get("SLACK_BOT_TOKEN", "")

    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set in ~/.clawdbot/.env", file=sys.stderr)
        sys.exit(1)

    queue = load_queue()
    hits = load_hits()

    if not queue:
        print("No posts in queue (queue file missing or empty)")
        return

    platform_filter = getattr(args, "platform", None)
    min_views_override = getattr(args, "min_views", None)
    dry_run = getattr(args, "dry_run", False)

    posted = [
        e for e in queue
        if e.get("status") == "posted"
        and (not platform_filter or e.get("platform") == platform_filter)
    ]

    print(f"Scanning {len(posted)} posted entries...")

    new_hits = 0
    for entry in posted:
        post_id = entry.get("id", "")
        platform = entry.get("platform", "")
        views = get_view_count(entry)
        threshold = get_threshold(platform, min_views_override)

        if views < threshold:
            continue

        if post_id in hits and not getattr(args, "force", False):
            continue  # Already processed

        print(f"\nViral hit: {post_id} | {platform} | {views:,} views (threshold: {threshold:,})")
        result = process_hit(entry, hits, dry_run, api_key, slack_token, force=getattr(args, "force", False))
        if result:
            new_hits += 1

    if new_hits == 0:
        print(f"\nNo new viral hits found. (Scanned {len(posted)} posted entries)")
    else:
        action = "Would clone" if dry_run else "Cloned"
        print(f"\n{action} {new_hits} viral hit(s)")


def cmd_list_hits(args, env: dict):
    hits = load_hits()
    if not hits:
        print("No viral hits recorded yet.")
        return

    platform_filter = getattr(args, "platform", None)
    rows = sorted(hits.values(), key=lambda h: h.get("cloned_at", ""), reverse=True)

    if platform_filter:
        rows = [r for r in rows if r.get("platform") == platform_filter]

    print(f"{'Post ID':<12} {'Platform':<12} {'Views':>10}  {'Cloned At':<22}  {'Variations'}")
    print("-" * 80)
    for hit in rows:
        views_fmt = f"{hit.get('views', 0):,}"
        n_variations = len(hit.get("variations", []))
        cloned_at = hit.get("cloned_at", "?")[:19].replace("T", " ")
        print(f"{hit.get('post_id','?'):<12} {hit.get('platform','?'):<12} {views_fmt:>10}  {cloned_at:<22}  {n_variations} variation(s)")


def cmd_clone(args, env: dict):
    api_key = env.get("ANTHROPIC_API_KEY", "")
    slack_token = env.get("SLACK_BOT_TOKEN", "")

    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set in ~/.clawdbot/.env", file=sys.stderr)
        sys.exit(1)

    post_id = args.post_id
    queue = load_queue()
    hits = load_hits()

    entry = next((e for e in queue if e.get("id") == post_id), None)
    if not entry:
        print(f"ERROR: post ID {post_id!r} not found in queue", file=sys.stderr)
        sys.exit(1)

    dry_run = getattr(args, "dry_run", False)
    result = process_hit(entry, hits, dry_run, api_key, slack_token, force=True)
    if result:
        print(f"\nDone. Cloned {len(result.get('variations', []))} variations.")
    else:
        print("Cloning failed.", file=sys.stderr)
        sys.exit(1)


def cmd_status(args, env: dict):
    hits = load_hits()
    queue = load_queue()

    if not hits:
        print("No cloned posts yet.")
        return

    # Build index of queue entries by ID for status lookup
    queue_index = {e.get("id"): e for e in queue}

    print(f"{'Queued ID':<12} {'Platform':<12} {'Status':<10}  {'Caption preview'}")
    print("-" * 80)

    for post_id, hit in sorted(hits.items(), key=lambda x: x[1].get("cloned_at", ""), reverse=True):
        platform = hit.get("platform", "?")
        for i, (qid, variation) in enumerate(zip(hit.get("queued_ids", []), hit.get("variations", [])), 1):
            if not qid:
                status = "not queued"
            else:
                q_entry = queue_index.get(qid)
                status = q_entry.get("status", "unknown") if q_entry else "not in queue"
            caption_preview = variation[:60] + ("..." if len(variation) > 60 else "")
            print(f"{qid or '(none)':<12} {platform:<12} {status:<10}  {caption_preview}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Viral Format Cloner — multiply your viral hits",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # check
    p_check = sub.add_parser("check", help="Scan for viral hits and auto-queue variations")
    p_check.add_argument("--dry-run", action="store_true", help="Preview without queuing or reporting")
    p_check.add_argument("--platform", help="Filter to specific platform")
    p_check.add_argument("--min-views", type=int, help="Override view threshold")
    p_check.add_argument("--force", action="store_true", help="Re-clone posts already processed")

    # list-hits
    p_list = sub.add_parser("list-hits", help="Show posts that triggered cloning")
    p_list.add_argument("--platform", help="Filter to specific platform")

    # clone
    p_clone = sub.add_parser("clone", help="Manually clone a specific post")
    p_clone.add_argument("post_id", help="Post ID from the queue")
    p_clone.add_argument("--dry-run", action="store_true", help="Preview without queuing")

    # status
    sub.add_parser("status", help="Show cloned content queue")

    args = parser.parse_args()
    env = load_env()

    dispatch = {
        "check": cmd_check,
        "list-hits": cmd_list_hits,
        "clone": cmd_clone,
        "status": cmd_status,
    }
    dispatch[args.command](args, env)


if __name__ == "__main__":
    main()
