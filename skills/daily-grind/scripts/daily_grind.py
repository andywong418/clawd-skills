#!/usr/bin/env python3
"""Daily Grind — run the full daily TikTok engagement loop.

Orchestrates:
  1. warmup session       — watch + like niche content
  2. comment-responder    — reply to comments on your posts
  3. follow-commenters    — follow people who engaged with you
  4. unfollow             — clean up non-followers after 3 days

Each step runs independently. If one fails, the rest continue.

Usage:
  python3 daily_grind.py --account tiktok_username
  python3 daily_grind.py --account tiktok_username --skip warmup --skip unfollow
  python3 daily_grind.py --account tiktok_username --dry-run
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path


ACCOUNTS_DIR = Path.home() / ".clawdbot" / "warmup" / "accounts"

SKILLS_ROOT = Path(__file__).resolve().parents[3]

WARMUP     = SKILLS_ROOT / "skills/warmup-trainer/scripts/warmup.py"
COMMENTS   = SKILLS_ROOT / "skills/comment-responder/scripts/comment_responder.py"
FOLLOW_MGR = SKILLS_ROOT / "skills/follow-manager/scripts/follow_manager.py"


def load_state(account_key: str) -> dict | None:
    f = ACCOUNTS_DIR / account_key / "state.json"
    return json.loads(f.read_text()) if f.exists() else None


def run_step(label: str, cmd: list[str]) -> bool:
    """Run a subprocess step, stream output, return True on success."""
    print(f"\n{'─'*50}")
    print(f"  {label}")
    print(f"{'─'*50}")
    result = subprocess.run(cmd, text=True)
    ok = result.returncode == 0
    print(f"\n  {'✓' if ok else '✗'} {label} {'done' if ok else 'failed'}")
    return ok


def main():
    parser = argparse.ArgumentParser(description="Run the full daily TikTok engagement loop")
    parser.add_argument("--account", required=True, help="Account key (platform_username)")
    parser.add_argument("--skip", action="append", default=[],
                        metavar="STEP",
                        help="Skip a step: warmup, comments, follow, unfollow")
    parser.add_argument("--dry-run", action="store_true",
                        help="Pass --dry-run to comment-responder (preview replies, don't post)")
    parser.add_argument("--unfollow-after", type=int, default=3,
                        help="Days before unfollowing non-followers (default: 3)")
    args = parser.parse_args()

    skip = {s.lower() for s in args.skip}

    state = load_state(args.account)
    if not state:
        print(f"Account '{args.account}' not found.")
        print("Run: python3 skills/warmup-trainer/scripts/warmup.py init")
        sys.exit(1)

    username = state["username"]
    py = sys.executable

    print(f"\n{'='*50}")
    print(f"  Daily Grind — @{username}")
    print(f"{'='*50}")

    results = {}
    start = time.time()

    # Step 1: Warmup session
    if "warmup" not in skip:
        results["warmup"] = run_step(
            "Step 1/4 — Warmup session (watch + like niche content)",
            [py, str(WARMUP), "--account", args.account, "session"],
        )
    else:
        print("\n  [skip] warmup")

    # Step 2: Comment responder
    if "comments" not in skip:
        cmd = [py, str(COMMENTS), "--account", args.account]
        if args.dry_run:
            cmd.append("--dry-run")
        results["comments"] = run_step(
            "Step 2/4 — Comment responder (reply to comments on your posts)",
            cmd,
        )
    else:
        print("\n  [skip] comments")

    # Step 3: Follow commenters
    if "follow" not in skip:
        results["follow"] = run_step(
            "Step 3/4 — Follow commenters (follow people who engaged with you)",
            [py, str(FOLLOW_MGR), "--account", args.account, "follow-commenters"],
        )
    else:
        print("\n  [skip] follow")

    # Step 4: Unfollow non-followers
    if "unfollow" not in skip:
        results["unfollow"] = run_step(
            f"Step 4/4 — Unfollow non-followers (after {args.unfollow_after} days)",
            [py, str(FOLLOW_MGR), "--account", args.account,
             "unfollow", "--after-days", str(args.unfollow_after)],
        )
    else:
        print("\n  [skip] unfollow")

    elapsed = int(time.time() - start)
    minutes, seconds = divmod(elapsed, 60)

    print(f"\n{'='*50}")
    print(f"  Daily Grind complete — {minutes}m {seconds}s")
    print()
    for step, ok in results.items():
        print(f"  {'✓' if ok else '✗'} {step}")
    print(f"{'='*50}\n")

    if any(not ok for ok in results.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()
