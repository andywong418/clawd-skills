#!/usr/bin/env python3
"""Process the post queue — publish any posts that are due now."""

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

QUEUE_FILE = Path.home() / ".clawdbot" / "post-queue.json"


def load_queue() -> list[dict]:
    if not QUEUE_FILE.exists():
        return []
    with open(QUEUE_FILE) as f:
        return json.load(f)


def save_queue(queue: list[dict]):
    with open(QUEUE_FILE, "w") as f:
        json.dump(queue, f, indent=2)


def post_entry(entry: dict) -> str:
    platform = entry["platform"]
    video = entry["video"]
    caption = entry["caption"]

    if platform == "tiktok":
        from platforms.tiktok import post_video
        return post_video(video, caption)

    elif platform == "instagram":
        from platforms.instagram import post_reel
        return post_reel(video, caption)

    elif platform == "youtube":
        from platforms.youtube import upload_video
        # Split caption: first line is title, rest is description
        lines = caption.strip().split("\n", 1)
        title = lines[0].strip()
        description = lines[1].strip() if len(lines) > 1 else ""
        # Extract hashtags from caption for tags list
        tags = [w.lstrip("#") for w in caption.split() if w.startswith("#")]
        return upload_video(
            video_path=video,
            title=title,
            description=description,
            tags=tags,
            privacy=entry.get("yt_privacy", "public"),
            is_shorts=entry.get("yt_shorts", True),
        )

    else:
        raise ValueError(f"Unknown platform: {platform}")


def main():
    queue = load_queue()
    now = datetime.now()

    due = [e for e in queue
           if e["status"] == "pending"
           and datetime.fromisoformat(e["scheduled_at"]) <= now]

    if not due:
        pending = sum(1 for e in queue if e["status"] == "pending")
        print(f"[{now.strftime('%H:%M')}] No posts due. {pending} pending in queue.")
        return

    print(f"[{now.strftime('%H:%M')}] {len(due)} post(s) due.\n")

    for entry in due:
        print(f"→ [{entry['id']}] {entry['platform']} | {Path(entry['video']).name}")
        try:
            result_id = post_entry(entry)
            entry["status"] = "posted"
            entry["result_id"] = result_id
            entry["posted_at"] = now.isoformat()
            print(f"  ✓ Posted — {result_id}\n")
        except Exception as e:
            entry["status"] = "failed"
            entry["error"] = str(e)
            entry["failed_at"] = now.isoformat()
            print(f"  ✗ Failed: {e}\n", file=sys.stderr)

    save_queue(queue)

    posted = sum(1 for e in due if e["status"] == "posted")
    failed = sum(1 for e in due if e["status"] == "failed")
    print(f"Done: {posted} posted, {failed} failed.")


if __name__ == "__main__":
    main()
