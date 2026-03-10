#!/usr/bin/env python3
"""Warmup cron runner — checks every minute for due sessions and runs them.

Designed to be called by cron: * * * * * python3 .../cron_runner.py

Flow per tick:
  1. For each account, check today's schedule.json
  2. If current UTC time is within [scheduled_time, scheduled_time + 3 min]
     and session not done → run session, then mark done
  3. If schedule.json is from a past date → regenerate it
  4. Uses a lock file to prevent concurrent runs
"""

import json
import os
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path

try:
    import requests
except ImportError:
    requests = None

WARMUP_DIR = Path.home() / ".clawdbot" / "warmup" / "accounts"
SCRIPT = Path(__file__).parent / "warmup.py"
LOG_FILE = Path.home() / ".clawdbot" / "warmup" / "cron.log"
LOCK_FILE = Path("/tmp/warmup_cron.lock")
WINDOW_MINUTES = 3   # how long after scheduled time we'll still run

SLACK_CHANNEL = "C0AHBK5E9V3"   # #viralfarm


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def log(msg: str):
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    line = f"[{timestamp}] {msg}"
    print(line)
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass


def notify_slack(msg: str):
    """Post a message to #viralfarm."""
    if not requests:
        return
    token = os.environ.get("SLACK_BOT_TOKEN")
    if not token:
        env_file = Path.home() / ".clawdbot" / ".env"
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if line.startswith("SLACK_BOT_TOKEN="):
                    token = line.split("=", 1)[1].strip()
                    break
    if not token:
        return
    try:
        requests.post(
            "https://slack.com/api/chat.postMessage",
            headers={"Authorization": f"Bearer {token}"},
            json={"channel": SLACK_CHANNEL, "text": msg},
            timeout=10,
        )
    except Exception:
        pass


def acquire_lock() -> bool:
    """Return True if we got the lock, False if another instance is running."""
    if LOCK_FILE.exists():
        # Check if the PID inside is still alive
        try:
            pid = int(LOCK_FILE.read_text().strip())
            os.kill(pid, 0)   # raises if not alive
            return False      # still running
        except (ProcessLookupError, ValueError):
            pass  # stale lock — take it
    LOCK_FILE.write_text(str(os.getpid()))
    return True


def release_lock():
    try:
        LOCK_FILE.unlink()
    except FileNotFoundError:
        pass


def run_warmup(*args, timeout=600) -> tuple[int, str, str]:
    """Run warmup.py with given args. Returns (returncode, stdout, stderr)."""
    env = os.environ.copy()
    # Ensure DISPLAY is set for Playwright (uses virtual display on server)
    if "DISPLAY" not in env:
        env["DISPLAY"] = ":99"
    result = subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True, text=True, timeout=timeout, env=env,
        cwd=str(SCRIPT.parent)
    )
    return result.returncode, result.stdout, result.stderr


def account_key_parts(acc_dir: Path) -> tuple[str, str]:
    """Split 'instagram_viralfarmai' → ('instagram', 'viralfarmai')."""
    name = acc_dir.name
    idx = name.index("_")
    return name[:idx], name[idx + 1:]


# ---------------------------------------------------------------------------
# Main logic
# ---------------------------------------------------------------------------

def check_accounts():
    if not WARMUP_DIR.exists():
        log("No accounts dir — nothing to do.")
        return

    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")
    current_minutes = now.hour * 60 + now.minute

    for acc_dir in sorted(WARMUP_DIR.iterdir()):
        if not acc_dir.is_dir():
            continue

        schedule_file = acc_dir / "schedule.json"
        state_file = acc_dir / "state.json"

        if not state_file.exists():
            continue

        platform, username = account_key_parts(acc_dir)
        account_arg = acc_dir.name   # e.g. "instagram_viralfarmai"

        # ── Regenerate stale schedule ──────────────────────────────────────
        if not schedule_file.exists():
            log(f"{account_arg}: No schedule — generating.")
            rc, out, err = run_warmup("--account", account_arg, "schedule", timeout=30)
            if rc != 0:
                log(f"{account_arg}: schedule regen failed: {err.strip()[:200]}")
            continue

        with open(schedule_file) as f:
            schedule = json.load(f)

        if schedule.get("date") != today:
            log(f"{account_arg}: Stale schedule ({schedule.get('date')}) — regenerating for {today}.")
            rc, out, err = run_warmup("--account", account_arg, "schedule", timeout=30)
            if rc != 0:
                log(f"{account_arg}: schedule regen failed: {err.strip()[:200]}")
            continue

        # ── Check each session slot ────────────────────────────────────────
        for session in schedule.get("sessions", []):
            if session.get("done"):
                continue

            session_hhmm = session["time"]   # "HH:MM"
            sh, sm = map(int, session_hhmm.split(":"))
            session_minutes = sh * 60 + sm

            delta = current_minutes - session_minutes
            if 0 <= delta < WINDOW_MINUTES:
                log(f"{account_arg}: Session due at {session_hhmm} (Δ{delta}m) — starting.")

                rc, out, err = run_warmup("--account", account_arg, "session", timeout=660)

                if rc == 0:
                    log(f"{account_arg}: Session completed. Marking done.")
                    rc2, out2, err2 = run_warmup("--account", account_arg, "done", timeout=15)
                    log(f"{account_arg}: {out2.strip() or 'done logged'}")
                    notify_slack(f"🦠 *Warmup done* — `@{username}` ({platform}) session complete ✓")
                else:
                    log(f"{account_arg}: Session FAILED (rc={rc}). stderr: {err.strip()[:300]}")
                    notify_slack(f"⚠️ *Warmup failed* — `@{username}` ({platform}) — check cron.log")

                # Only run one session per account per tick
                break


def main():
    if not acquire_lock():
        # Another instance is running — silently exit
        sys.exit(0)

    try:
        check_accounts()
    except Exception as e:
        log(f"ERROR: {e}")
    finally:
        release_lock()


if __name__ == "__main__":
    main()
