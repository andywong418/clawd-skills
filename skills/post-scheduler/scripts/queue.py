#!/usr/bin/env python3
"""Manage the post queue — add, list, remove scheduled posts."""

import argparse
import json
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path

QUEUE_FILE = Path.home() / ".clawdbot" / "post-queue.json"

OPTIMAL_WINDOWS = {
    "tiktok":    [(6, 10), (12, 15), (19, 21)],
    "instagram": [(6, 9),  (11, 13), (19, 21)],
    "youtube":   [(8, 10), (12, 14), (17, 20)],
}

PLATFORMS = ["tiktok", "instagram", "youtube"]


def load_queue() -> list[dict]:
    if not QUEUE_FILE.exists():
        return []
    with open(QUEUE_FILE) as f:
        return json.load(f)


def save_queue(queue: list[dict]):
    QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(QUEUE_FILE, "w") as f:
        json.dump(queue, f, indent=2)


def next_optimal_time(platform: str) -> datetime:
    windows = OPTIMAL_WINDOWS.get(platform, OPTIMAL_WINDOWS["tiktok"])
    now = datetime.now()
    for day_offset in range(2):
        base = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=day_offset)
        for start_h, end_h in windows:
            candidate = base.replace(hour=(start_h + end_h) // 2, minute=0)
            if candidate > now + timedelta(minutes=5):
                return candidate
    return now + timedelta(hours=24)


def cmd_add(args):
    queue = load_queue()

    if args.optimal:
        scheduled_at = next_optimal_time(args.platform)
        print(f"Next optimal time for {args.platform}: {scheduled_at.strftime('%Y-%m-%d %H:%M')}")
    elif args.at:
        try:
            scheduled_at = datetime.fromisoformat(args.at)
        except ValueError:
            print(f"Error: --at must be ISO format, e.g. '2026-03-02T19:00'", file=sys.stderr)
            sys.exit(1)
    else:
        scheduled_at = datetime.now() + timedelta(minutes=5)

    caption_parts = [args.caption]
    if args.hashtags:
        tags = " ".join(f"#{t.lstrip('#')}" for t in args.hashtags.split())
        caption_parts.append(tags)
    caption = "\n\n".join(caption_parts)

    entry = {
        "id": str(uuid.uuid4())[:8],
        "platform": args.platform,
        "video": str(Path(args.video).resolve()),
        "caption": caption,
        "scheduled_at": scheduled_at.isoformat(),
        "status": "pending",
        "created_at": datetime.now().isoformat(),
    }

    # YouTube-specific fields
    if args.platform == "youtube":
        entry["yt_privacy"] = getattr(args, "privacy", "public")
        entry["yt_shorts"] = not getattr(args, "no_shorts", False)

    queue.append(entry)
    save_queue(queue)

    print(f"Queued [{entry['id']}] → {args.platform} at {scheduled_at.strftime('%Y-%m-%d %H:%M')}")
    print(f"  Video:   {entry['video']}")
    print(f"  Caption: {caption[:80]}{'...' if len(caption) > 80 else ''}")


def cmd_list(args):
    queue = load_queue()
    if not queue:
        print("Queue is empty.")
        return

    now = datetime.now()
    shown = 0
    print(f"\n{'ID':<10} {'Platform':<12} {'Status':<10} {'Scheduled':<20} {'Video'}")
    print("-" * 80)
    for entry in queue:
        if args.status and entry["status"] != args.status:
            continue
        sched = datetime.fromisoformat(entry["scheduled_at"])
        delta = sched - now
        if delta.total_seconds() > 0:
            h, rem = divmod(int(delta.total_seconds()), 3600)
            time_str = f"in {h}h{rem // 60}m"
        else:
            time_str = sched.strftime("%m/%d %H:%M")
        print(f"{entry['id']:<10} {entry['platform']:<12} {entry['status']:<10} {time_str:<20} {Path(entry['video']).name}")
        shown += 1

    if shown == 0:
        print(f"No entries with status '{args.status}'.")
    else:
        print(f"\n{shown} post(s).")


def cmd_remove(args):
    queue = load_queue()
    original = len(queue)
    queue = [e for e in queue if e["id"] != args.id]
    if len(queue) == original:
        print(f"No entry with id '{args.id}'", file=sys.stderr)
        sys.exit(1)
    save_queue(queue)
    print(f"Removed {args.id}")


def cmd_clear(args):
    queue = load_queue()
    if args.posted:
        queue = [e for e in queue if e["status"] != "posted"]
        print("Cleared posted entries.")
    else:
        queue = []
        print("Queue cleared.")
    save_queue(queue)


def cmd_optimal(args):
    print("Next optimal posting times:")
    for platform in PLATFORMS:
        t = next_optimal_time(platform)
        windows = OPTIMAL_WINDOWS[platform]
        print(f"  {platform:<12} → {t.strftime('%Y-%m-%d %H:%M')}  "
              f"(windows: {', '.join(f'{s}-{e}h' for s, e in windows)})")


def main():
    parser = argparse.ArgumentParser(description="Manage post queue")
    sub = parser.add_subparsers(dest="cmd", required=True)

    # add
    p_add = sub.add_parser("add", help="Add a post to the queue")
    p_add.add_argument("platform", choices=PLATFORMS)
    p_add.add_argument("video", help="Path to video file")
    p_add.add_argument("caption", help="Post caption / YouTube title")
    p_add.add_argument("--hashtags", help="Space-separated hashtags (without #)")
    p_add.add_argument("--at", help="Schedule time (ISO: 2026-03-02T19:00)")
    p_add.add_argument("--optimal", action="store_true", help="Use next optimal posting time")
    # YouTube-specific
    p_add.add_argument("--privacy", choices=["public", "private", "unlisted"],
                       default="public", help="YouTube privacy (default: public)")
    p_add.add_argument("--no-shorts", action="store_true",
                       help="YouTube: treat as regular video, not Shorts")

    # list
    p_list = sub.add_parser("list", help="Show queue")
    p_list.add_argument("--status", choices=["pending", "posted", "failed"])

    # remove
    p_rm = sub.add_parser("remove", help="Remove by ID")
    p_rm.add_argument("id")

    # clear
    p_clear = sub.add_parser("clear", help="Clear the queue")
    p_clear.add_argument("--posted", action="store_true", help="Only clear posted entries")

    # optimal
    sub.add_parser("optimal", help="Show next optimal times per platform")

    # auth
    p_auth = sub.add_parser("auth", help="Set up platform credentials")
    p_auth.add_argument("platform", choices=PLATFORMS)

    args = parser.parse_args()

    if args.cmd == "auth":
        if args.platform == "youtube":
            import subprocess, sys as _sys
            auth_script = Path(__file__).parent / "platforms" / "youtube_auth.py"
            subprocess.run([_sys.executable, str(auth_script)], check=True)
        else:
            print(f"Auth for {args.platform}: add credentials to ~/.clawdbot/.env")
            print(f"  TikTok:    TIKTOK_ACCESS_TOKEN")
            print(f"  Instagram: INSTAGRAM_ACCESS_TOKEN + INSTAGRAM_USER_ID")
        return

    {"add": cmd_add, "list": cmd_list, "remove": cmd_remove,
     "clear": cmd_clear, "optimal": cmd_optimal}[args.cmd](args)


if __name__ == "__main__":
    main()
