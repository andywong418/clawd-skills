#!/usr/bin/env python3
"""
ugc-tracker — Track UGC creator posts, view counts, and bonus payouts.

Usage:
  track.py add <name> --handle @username --platform tiktok --post <url>
  track.py add <name> --post <url>   (add post to existing creator)
  track.py remove <name>
  track.py list
  track.py check [name]
  track.py report [--unpaid] [--slack]
  track.py mark-paid <name> [--base]
"""

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DATA_DIR = Path.home() / ".clawdbot" / "ugc-tracker"
DATA_FILE = DATA_DIR / "creators.json"
ENV_FILE = Path.home() / ".clawdbot" / ".env"

SLACK_CHANNEL = "C0AHBK5E9V3"

BONUS_TIERS = [
    (1_000_000, 250.0),
    (500_000, 100.0),
    (250_000, 50.0),
    (100_000, 25.0),
]

BASE_PAY = 15.0


# ---------------------------------------------------------------------------
# Env loader
# ---------------------------------------------------------------------------

def load_env(path: Path) -> dict:
    env = {}
    if not path.exists():
        return env
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            env[key] = val
    return env


ENV = load_env(ENV_FILE)


def get_env(key: str, default: str = "") -> str:
    return ENV.get(key) or os.environ.get(key, default)


# ---------------------------------------------------------------------------
# Data store
# ---------------------------------------------------------------------------

def load_data() -> dict:
    if not DATA_FILE.exists():
        return {"creators": {}}
    try:
        return json.loads(DATA_FILE.read_text())
    except (json.JSONDecodeError, OSError) as e:
        print(f"Warning: could not load {DATA_FILE}: {e}", file=sys.stderr)
        return {"creators": {}}


def save_data(data: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps(data, indent=2))


def make_creator_id(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Bonus calculation
# ---------------------------------------------------------------------------

def calculate_bonuses(views: int, bonuses_already_paid: list) -> list:
    """Return list of bonus dicts owed but not yet paid."""
    owed = []
    paid_keys = set(str(k) for k in bonuses_already_paid)
    for threshold, amount in BONUS_TIERS:
        key = str(threshold)
        if views >= threshold and key not in paid_keys:
            owed.append({"threshold": threshold, "amount": amount, "key": key})
    return owed


def total_bonuses_owed(bonuses_owed: list) -> float:
    return sum(b["amount"] for b in bonuses_owed)


# ---------------------------------------------------------------------------
# View count scraping
# ---------------------------------------------------------------------------

def get_view_count(url: str) -> int | None:
    try:
        ytdlp_result = subprocess.run(
            ["which", "yt-dlp"], capture_output=True, text=True
        )
        ytdlp_path = ytdlp_result.stdout.strip() if ytdlp_result.returncode == 0 else "yt-dlp"

        platform = "tiktok" if "tiktok" in url.lower() else "instagram"
        cookies_path = Path.home() / ".clawdbot" / "cookies" / f"{platform}.txt"

        cmd = [ytdlp_path, "--dump-json", "--no-download", "--quiet"]
        if cookies_path.exists():
            cmd += ["--cookies", str(cookies_path)]
        cmd.append(url)

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
        if result.returncode == 0 and result.stdout.strip():
            data = json.loads(result.stdout.strip().splitlines()[0])
            count = data.get("view_count")
            if count is None:
                count = data.get("like_count")
            if count is not None:
                return int(count)
    except subprocess.TimeoutExpired:
        print(f"  Timeout scraping {url}", file=sys.stderr)
    except json.JSONDecodeError as e:
        print(f"  JSON parse error for {url}: {e}", file=sys.stderr)
    except FileNotFoundError:
        print("  yt-dlp not found — install it with: pip install yt-dlp", file=sys.stderr)
    except Exception as e:
        print(f"  Error scraping {url}: {e}", file=sys.stderr)
    return None


# ---------------------------------------------------------------------------
# Slack
# ---------------------------------------------------------------------------

def post_slack(message: str) -> bool:
    token = get_env("SLACK_BOT_TOKEN")
    if not token:
        print("SLACK_BOT_TOKEN not set — skipping Slack post.", file=sys.stderr)
        return False

    payload = json.dumps({
        "channel": SLACK_CHANNEL,
        "text": message,
        "mrkdwn": True,
    }).encode()

    req = urllib.request.Request(
        "https://slack.com/api/chat.postMessage",
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read())
            if not body.get("ok"):
                print(f"Slack error: {body.get('error')}", file=sys.stderr)
                return False
        return True
    except Exception as e:
        print(f"Slack post failed: {e}", file=sys.stderr)
        return False


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_add(args) -> None:
    data = load_data()
    name = args.name
    creator_id = make_creator_id(name)

    if creator_id not in data["creators"]:
        # Brand new creator
        data["creators"][creator_id] = {
            "name": name,
            "handles": {},
            "posts": [],
        }
        print(f"Added creator: {name}")
    else:
        print(f"Creator already exists: {name} — appending post.")

    creator = data["creators"][creator_id]

    # Update handle if provided
    if args.handle:
        platform = args.platform or ("tiktok" if "tiktok" in (args.post or "") else "instagram")
        handle = args.handle.lstrip("@")
        creator["handles"][platform] = f"@{handle}"

    # Add post if provided
    if args.post:
        platform = args.platform
        if not platform:
            platform = "tiktok" if "tiktok" in args.post else "instagram"

        # Check for duplicate URL
        existing_urls = [p["url"] for p in creator["posts"]]
        if args.post in existing_urls:
            print(f"Post already tracked: {args.post}")
        else:
            creator["posts"].append({
                "url": args.post,
                "platform": platform,
                "added_at": now_iso(),
                "base_pay": BASE_PAY,
                "base_paid": False,
                "views": 0,
                "last_checked": None,
                "bonuses_paid": [],
                "bonuses_owed": [],
            })
            print(f"Added post ({platform}): {args.post}")
    elif not args.handle:
        print("Nothing to add — provide --post and/or --handle.")

    save_data(data)


def cmd_remove(args) -> None:
    data = load_data()
    creator_id = make_creator_id(args.name)
    if creator_id not in data["creators"]:
        print(f"Creator not found: {args.name}")
        sys.exit(1)
    del data["creators"][creator_id]
    save_data(data)
    print(f"Removed creator: {args.name}")


def cmd_list(args) -> None:
    data = load_data()
    creators = data.get("creators", {})
    if not creators:
        print("No creators tracked yet.")
        return

    for cid, creator in creators.items():
        handles = ", ".join(f"{p}: {h}" for p, h in creator.get("handles", {}).items())
        print(f"\n{creator['name']}" + (f"  ({handles})" if handles else ""))
        posts = creator.get("posts", [])
        if not posts:
            print("  (no posts)")
        for i, post in enumerate(posts, 1):
            views = post.get("views", 0)
            checked = post.get("last_checked") or "never"
            bonuses_owed = total_bonuses_owed(post.get("bonuses_owed", []))
            base_status = "paid" if post.get("base_paid") else "unpaid"
            print(
                f"  [{i}] {post['url']}\n"
                f"       views={views:,}  checked={checked}  "
                f"base=${post['base_pay']:.0f} ({base_status})  bonuses_owed=${bonuses_owed:.0f}"
            )


def cmd_check(args) -> None:
    data = load_data()
    creators = data.get("creators", {})

    target_id = make_creator_id(args.name) if args.name else None
    if target_id and target_id not in creators:
        print(f"Creator not found: {args.name}")
        sys.exit(1)

    to_check = (
        {target_id: creators[target_id]} if target_id else creators
    )

    if not to_check:
        print("No creators to check.")
        return

    changed = False
    for cid, creator in to_check.items():
        posts = creator.get("posts", [])
        if not posts:
            print(f"{creator['name']}: no posts")
            continue

        print(f"Checking {creator['name']}...")
        for post in posts:
            print(f"  {post['url']} ... ", end="", flush=True)
            views = get_view_count(post["url"])
            if views is None:
                print("failed (skipping)")
                continue

            old_views = post.get("views", 0)
            post["views"] = views
            post["last_checked"] = now_iso()

            # Recalculate bonuses owed
            paid = post.get("bonuses_paid", [])
            post["bonuses_owed"] = calculate_bonuses(views, paid)

            delta = views - old_views
            delta_str = f" (+{delta:,})" if delta > 0 else ""
            bonuses_owed = total_bonuses_owed(post["bonuses_owed"])
            print(f"{views:,}{delta_str}  bonuses_owed=${bonuses_owed:.0f}")
            changed = True

    if changed:
        save_data(data)
        print("Saved.")


def _build_report_lines(data: dict, unpaid_only: bool = False) -> tuple[list[str], float, float, float]:
    """Returns (lines, total_base, total_bonuses, total_owed)."""
    creators = data.get("creators", {})
    today = datetime.now().strftime("%Y-%m-%d")

    header = f"UGC Tracker Report — {today}"
    col_header = f"{'Creator':<20} {'Posts':>5}  {'Base Pay':>9}  {'Bonuses':>9}  {'Total Owed':>10}"
    separator = "-" * 60

    rows = []
    grand_base = 0.0
    grand_bonuses = 0.0
    grand_total = 0.0

    for cid, creator in creators.items():
        posts = creator.get("posts", [])
        post_count = len(posts)

        creator_base = sum(
            p.get("base_pay", BASE_PAY)
            for p in posts
            if not p.get("base_paid", False)
        )
        creator_bonuses = sum(
            total_bonuses_owed(p.get("bonuses_owed", []))
            for p in posts
        )
        creator_total = creator_base + creator_bonuses

        if unpaid_only and creator_total == 0:
            continue

        grand_base += creator_base
        grand_bonuses += creator_bonuses
        grand_total += creator_total

        rows.append(
            f"{creator['name']:<20} {post_count:>5}  "
            f"${creator_base:>8.2f}  ${creator_bonuses:>8.2f}  ${creator_total:>9.2f}"
        )

    lines = [header, "", col_header, separator] + rows + [separator]
    total_line = (
        f"{'TOTAL':<20} {'':>5}  "
        f"${grand_base:>8.2f}  ${grand_bonuses:>8.2f}  ${grand_total:>9.2f}"
    )
    lines.append(total_line)
    return lines, grand_base, grand_bonuses, grand_total


def cmd_report(args) -> None:
    data = load_data()

    lines, grand_base, grand_bonuses, grand_total = _build_report_lines(
        data, unpaid_only=args.unpaid
    )

    report_text = "\n".join(lines)
    print(report_text)

    if args.slack:
        slack_msg = f"```\n{report_text}\n```"
        ok = post_slack(slack_msg)
        if ok:
            print(f"\nPosted to Slack ({SLACK_CHANNEL})")
        else:
            print("\nSlack post failed.")


def cmd_mark_paid(args) -> None:
    data = load_data()
    creator_id = make_creator_id(args.name)
    if creator_id not in data["creators"]:
        print(f"Creator not found: {args.name}")
        sys.exit(1)

    creator = data["creators"][creator_id]
    total_cleared = 0.0

    for post in creator.get("posts", []):
        # Mark bonuses as paid
        for bonus in post.get("bonuses_owed", []):
            if bonus["key"] not in post.get("bonuses_paid", []):
                post.setdefault("bonuses_paid", []).append(bonus["key"])
                total_cleared += bonus["amount"]
        post["bonuses_owed"] = []

        # Optionally mark base pay
        if args.base and not post.get("base_paid", False):
            post["base_paid"] = True
            total_cleared += post.get("base_pay", BASE_PAY)

    save_data(data)
    base_note = " (including base pay)" if args.base else ""
    print(f"Marked {creator['name']} as paid{base_note}. Total cleared: ${total_cleared:.2f}")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        prog="track.py",
        description="UGC creator tracker — manage roster, view counts, and payout calculations.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # add
    add_p = subparsers.add_parser("add", help="Add a creator or post")
    add_p.add_argument("name", help="Creator's full name")
    add_p.add_argument("--handle", help="Platform handle (e.g. @janesmith)")
    add_p.add_argument("--platform", choices=["tiktok", "instagram"], help="Platform for handle/post")
    add_p.add_argument("--post", help="URL of post to track")

    # remove
    rm_p = subparsers.add_parser("remove", help="Remove a creator")
    rm_p.add_argument("name", help="Creator's name")

    # list
    subparsers.add_parser("list", help="List all creators and posts")

    # check
    check_p = subparsers.add_parser("check", help="Scrape view counts")
    check_p.add_argument("name", nargs="?", default=None, help="Creator name (optional — checks all if omitted)")

    # report
    report_p = subparsers.add_parser("report", help="Show payout report")
    report_p.add_argument("--unpaid", action="store_true", help="Show only creators with unpaid amounts")
    report_p.add_argument("--slack", action="store_true", help="Post report to Slack")

    # mark-paid
    paid_p = subparsers.add_parser("mark-paid", help="Mark creator bonuses as paid")
    paid_p.add_argument("name", help="Creator's name")
    paid_p.add_argument("--base", action="store_true", help="Also mark base pay as paid")

    args = parser.parse_args()

    dispatch = {
        "add": cmd_add,
        "remove": cmd_remove,
        "list": cmd_list,
        "check": cmd_check,
        "report": cmd_report,
        "mark-paid": cmd_mark_paid,
    }

    fn = dispatch.get(args.command)
    if fn:
        fn(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
