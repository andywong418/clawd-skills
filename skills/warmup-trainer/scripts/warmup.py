#!/usr/bin/env python3
"""Account Warmup Trainer — niche-focused algorithm training for TikTok/Instagram.

Supports multiple accounts. Each account gets its own state, session log,
schedule, and browser profile.

Storage layout:
  ~/.clawdbot/warmup/accounts/{platform}_{username}/
    state.json
    sessions.json
    schedule.json
    browser_profile/     ← Playwright persistent context (login saved here)

Commands:
  python3 warmup.py init                      Add a new account
  python3 warmup.py accounts                  List all accounts
  python3 warmup.py schedule                  Today's session times
  python3 warmup.py session                   Run browser engagement session
  python3 warmup.py done                      Log completed session
  python3 warmup.py status                    Show progress

Add --account tiktok_username to target a specific account when multiple exist.
"""

import argparse
import json
import random
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

WARMUP_DIR = Path.home() / ".clawdbot" / "warmup" / "accounts"


def account_key(platform: str, username: str) -> str:
    return f"{platform}_{username.lstrip('@').lower()}"


def account_dir(key: str) -> Path:
    return WARMUP_DIR / key


def list_accounts() -> list[dict]:
    """Return all initialized accounts as list of state dicts."""
    if not WARMUP_DIR.exists():
        return []
    accounts = []
    for d in sorted(WARMUP_DIR.iterdir()):
        state_file = d / "state.json"
        if state_file.exists():
            with open(state_file) as f:
                accounts.append(json.load(f))
    return accounts


def resolve_account(arg: str | None) -> dict:
    """
    Return the state dict for the target account.
    - If --account given, use it.
    - If only one account exists, use it automatically.
    - Otherwise, show a picker.
    """
    accounts = list_accounts()
    if not accounts:
        print("No accounts initialized. Run 'init' first.")
        sys.exit(1)

    if arg:
        # Match by username, platform_username, or just username fragment
        arg_lower = arg.lstrip("@").lower()
        matches = [a for a in accounts
                   if a["username"] == arg_lower
                   or account_key(a["platform"], a["username"]) == arg_lower]
        if not matches:
            print(f"Account '{arg}' not found. Run 'accounts' to list.")
            sys.exit(1)
        return matches[0]

    if len(accounts) == 1:
        return accounts[0]

    # Multiple accounts — interactive picker
    print("Multiple accounts — pick one:\n")
    for i, a in enumerate(accounts, 1):
        day = get_day_number(a)
        phase = get_phase(day)
        print(f"  [{i}] @{a['username']} ({a['platform']}) — Day {day}, {phase['name']}")
    print()
    choice = input("Account number: ").strip()
    try:
        return accounts[int(choice) - 1]
    except (ValueError, IndexError):
        print("Invalid selection.")
        sys.exit(1)


def load_state(key: str) -> dict | None:
    f = account_dir(key) / "state.json"
    return json.loads(f.read_text()) if f.exists() else None


def save_state(key: str, state: dict):
    d = account_dir(key)
    d.mkdir(parents=True, exist_ok=True)
    (d / "state.json").write_text(json.dumps(state, indent=2))


def load_sessions(key: str) -> list:
    f = account_dir(key) / "sessions.json"
    return json.loads(f.read_text()) if f.exists() else []


def save_sessions(key: str, sessions: list):
    d = account_dir(key)
    d.mkdir(parents=True, exist_ok=True)
    (d / "sessions.json").write_text(json.dumps(sessions, indent=2))


def load_schedule(key: str) -> dict | None:
    f = account_dir(key) / "schedule.json"
    if not f.exists():
        return None
    data = json.loads(f.read_text())
    return data if data.get("date") == str(date.today()) else None


def save_schedule(key: str, schedule: dict):
    d = account_dir(key)
    d.mkdir(parents=True, exist_ok=True)
    (d / "schedule.json").write_text(json.dumps(schedule, indent=2))


# ---------------------------------------------------------------------------
# Niche config
# ---------------------------------------------------------------------------

DEFAULT_NICHE = {
    "name": "AI Video & Viral Content",
    "hashtags": [
        "aivideo", "aiart", "artificialintelligence", "viralvideo",
        "midjourney", "sora", "runway", "kling", "aigeneratedart",
        "creativeai", "generativeai", "aifilm", "stableai",
        "aitools", "aitrends", "chatgpt", "machinelearning",
    ],
}


# ---------------------------------------------------------------------------
# Warmup phases
# ---------------------------------------------------------------------------

PHASES = [
    {
        "name": "Phase 1: Algorithm Seeding",
        "day_range": (1, 7),
        "sessions_per_day": (3, 4),
        "duration_min": 5,
        "actions": [
            "Watch 80%+ of each video (completion rate is king)",
            "Like if the content is genuinely good niche content",
        ],
        "avoid": [
            "Comments — not yet",
            "Follows — not yet",
            "Posting anything",
            "Any content outside AI/viral niche",
        ],
        "tip": "Pure consumer mode. Training the algo what to show you.",
    },
    {
        "name": "Phase 2: Engagement Building",
        "day_range": (8, 14),
        "sessions_per_day": (4, 5),
        "duration_min": 7,
        "actions": [
            "Watch 80%+ of each video",
            "Like good niche content",
            "Follow the top 2–3 niche creators you see",
        ],
        "avoid": [
            "Off-topic content — scroll immediately",
            "Posting your own content",
        ],
        "tip": "Signal that you're an active account in the niche.",
    },
    {
        "name": "Phase 3: Full Engagement",
        "day_range": (15, 9999),
        "sessions_per_day": (3, 4),
        "duration_min": 10,
        "actions": [
            "Watch, like, follow as normal",
            "Start posting your own niche content",
        ],
        "avoid": [
            "Off-topic content — forever",
        ],
        "tip": "Account is warmed. Maintain niche discipline indefinitely.",
    },
]


def get_phase(day_num: int) -> dict:
    for phase in PHASES:
        lo, hi = phase["day_range"]
        if lo <= day_num <= hi:
            return phase
    return PHASES[-1]


def get_day_number(state: dict) -> int:
    start = datetime.fromisoformat(state["started_at"]).date()
    return (date.today() - start).days + 1


# ---------------------------------------------------------------------------
# Schedule generation
# ---------------------------------------------------------------------------

def generate_session_times(count: int) -> list[str]:
    windows = [(7, 10), (11, 13), (14, 17), (18, 22)]
    chosen = random.sample(windows, count) if count <= len(windows) else \
        windows + random.choices(windows, k=count - len(windows))
    times = []
    for start_h, end_h in sorted(chosen, key=lambda w: w[0]):
        times.append(f"{random.randint(start_h, end_h - 1):02d}:{random.randint(0, 59):02d}")
    return sorted(times)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_init(args):
    username = input("Account username (without @): ").strip().lstrip("@")
    platform = input("Platform (tiktok/instagram/twitter) [tiktok]: ").strip().lower() or "tiktok"

    if platform not in ("tiktok", "instagram", "twitter"):
        print("Platform must be 'tiktok', 'instagram', or 'twitter'.")
        sys.exit(1)

    key = account_key(platform, username)
    existing = load_state(key)
    if existing and not args.reset:
        print(f"@{username} on {platform} already exists. Use --reset to start over.")
        return

    state = {
        "username": username,
        "platform": platform,
        "account_key": key,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "niche": DEFAULT_NICHE["name"],
        "hashtags": DEFAULT_NICHE["hashtags"],
    }
    save_state(key, state)

    print(f"\n✓ Initialized @{username} on {platform}  [{key}]")
    print(f"  Niche: {DEFAULT_NICHE['name']}")
    print(f"\nRun 'schedule' to get today's session times.")


def cmd_accounts(args):
    accounts = list_accounts()
    if not accounts:
        print("No accounts. Run 'init' to add one.")
        return

    print(f"\n{'Account':<30} {'Platform':<12} {'Day':<6} {'Phase'}")
    print("-" * 70)
    for a in accounts:
        day = get_day_number(a)
        phase = get_phase(day)
        key = a.get("account_key", account_key(a["platform"], a["username"]))
        sessions = load_sessions(key)
        today = sum(1 for s in sessions if s["date"] == str(date.today()))
        print(f"  @{a['username']:<28} {a['platform']:<12} {day:<6} {phase['name']}  ({today} today)")
    print()


def cmd_schedule(args):
    state = resolve_account(args.account)
    key = state["account_key"]
    day_num = get_day_number(state)
    phase = get_phase(day_num)
    min_s, max_s = phase["sessions_per_day"]

    existing = load_schedule(key)
    if existing and not args.regen:
        schedule = existing
        print(f"@{state['username']} — Day {day_num} ({phase['name']}):\n")
    else:
        count = random.randint(min_s, max_s)
        times = generate_session_times(count)
        schedule = {
            "date": str(date.today()),
            "day": day_num,
            "phase": phase["name"],
            "sessions": [{"time": t, "done": False} for t in times],
            "duration_min": phase["duration_min"],
        }
        save_schedule(key, schedule)
        print(f"@{state['username']} — Day {day_num} ({phase['name']}):\n")

    now = datetime.now().strftime("%H:%M")
    for s in schedule["sessions"]:
        marker = "✓" if s["done"] else ("→" if s["time"] <= now else "·")
        print(f"  {marker} {s['time']}  ({schedule['duration_min']} min)")

    print(f"\n{phase['tip']}")


def cmd_session(args):
    state = resolve_account(args.account)
    key = state["account_key"]

    runner = Path(__file__).parent / "session_runner.py"
    if not runner.exists():
        print("session_runner.py not found.", file=sys.stderr)
        sys.exit(1)

    cmd = [sys.executable, str(runner), "--account", key]
    if args.duration:
        cmd += ["--duration", str(args.duration)]

    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError:
        print("Session runner exited with an error.", file=sys.stderr)
    except KeyboardInterrupt:
        print("\nSession interrupted.")


def cmd_done(args):
    state = resolve_account(args.account)
    key = state["account_key"]
    day_num = get_day_number(state)

    sessions = load_sessions(key)
    sessions.append({
        "date": str(date.today()),
        "day": day_num,
        "time": datetime.now().strftime("%H:%M"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    save_sessions(key, sessions)

    schedule = load_schedule(key)
    if schedule:
        for s in schedule["sessions"]:
            if not s["done"]:
                s["done"] = True
                break
        save_schedule(key, schedule)

    today_done = sum(1 for s in sessions if s["date"] == str(date.today()))
    print(f"✓ @{state['username']} — Day {day_num}, session {today_done} today ({len(sessions)} total)")

    if schedule:
        remaining = [s for s in schedule["sessions"] if not s["done"]]
        if remaining:
            print(f"  Next session: {remaining[0]['time']}")
        else:
            print(f"  All sessions done for today.")


def cmd_status(args):
    if args.account == "all":
        # Show all accounts
        for a in list_accounts():
            _print_status(a)
            print()
        return

    state = resolve_account(args.account)
    _print_status(state)


def _print_status(state: dict):
    key = state["account_key"]
    day_num = get_day_number(state)
    phase = get_phase(day_num)
    sessions = load_sessions(key)

    today = str(date.today())
    today_sessions = [s for s in sessions if s["date"] == today]
    week_sessions = [s for s in sessions
                     if (date.today() - date.fromisoformat(s["date"])).days < 7]

    # Streak
    streak = 0
    import datetime as dt
    for i in range(day_num):
        check = str(date.today() - dt.timedelta(days=i))
        if any(s["date"] == check for s in sessions):
            streak += 1
        else:
            break

    print(f"=== @{state['username']} ({state['platform']}) ===")
    print(f"  Day {day_num} — {phase['name']}")
    print(f"  Streak: {streak} day{'s' if streak != 1 else ''}")
    print(f"  Sessions today / week / total: {len(today_sessions)} / {len(week_sessions)} / {len(sessions)}")

    schedule = load_schedule(key)
    if schedule:
        done = sum(1 for s in schedule["sessions"] if s["done"])
        total_sched = len(schedule["sessions"])
        slots = "  ".join(
            ("✓" if s["done"] else "·") + s["time"]
            for s in schedule["sessions"]
        )
        print(f"  Today ({done}/{total_sched}): {slots}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Account warmup trainer — multi-account niche algorithm training",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--account", default=None, metavar="USERNAME",
                        help="Target account (username or platform_username). "
                             "Auto-selected if only one exists.")

    sub = parser.add_subparsers(dest="command")

    p_init = sub.add_parser("init", help="Add a new account")
    p_init.add_argument("--reset", action="store_true", help="Reset existing account")

    sub.add_parser("accounts", help="List all accounts")

    p_sched = sub.add_parser("schedule", help="Generate/show today's session schedule")
    p_sched.add_argument("--regen", action="store_true", help="Regenerate today's schedule")

    p_session = sub.add_parser("session", help="Run browser engagement session")
    p_session.add_argument("--duration", type=int, default=None, help="Override duration (minutes)")

    sub.add_parser("done", help="Log a completed session")

    p_status = sub.add_parser("status", help="Show warmup progress")
    p_status.add_argument("--all", dest="account", action="store_const", const="all",
                          help="Show all accounts")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Propagate top-level --account into subcommand args
    if not hasattr(args, "account") or args.account is None:
        args.account = parser.parse_known_args()[0].account

    {
        "init": cmd_init,
        "accounts": cmd_accounts,
        "schedule": cmd_schedule,
        "session": cmd_session,
        "done": cmd_done,
        "status": cmd_status,
    }[args.command](args)


if __name__ == "__main__":
    main()
