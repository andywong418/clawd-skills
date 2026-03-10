#!/usr/bin/env python3
"""
influencer-cpm-tracker — Track influencer deal CPMs, flag overpays, maintain deal database.
CPM = (cost / views) * 1000. Flag threshold: $1,000 CPM.
"""

import argparse
import json
import os
import sys
import uuid
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

CPM_FLAG_THRESHOLD = 1000.0
SLACK_CHANNEL = "C0AHBK5E9V3"
DATA_DIR = Path.home() / ".clawdbot" / "influencer-cpm-tracker"
DEALS_FILE = DATA_DIR / "deals.json"
ENV_FILE = Path.home() / ".clawdbot" / ".env"


# ---------------------------------------------------------------------------
# Env loader (no dotenv)
# ---------------------------------------------------------------------------

def load_env(path: Path) -> dict:
    env = {}
    if not path.exists():
        return env
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            env[key] = val
    return env


ENV = load_env(ENV_FILE)


def get_env(key: str, required: bool = False) -> str:
    val = ENV.get(key) or os.environ.get(key, "")
    if required and not val:
        print(f"Error: {key} not set in {ENV_FILE}", file=sys.stderr)
        sys.exit(1)
    return val


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def load_deals() -> dict:
    if not DEALS_FILE.exists():
        return {"deals": []}
    with open(DEALS_FILE) as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {"deals": []}


def save_deals(db: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(DEALS_FILE, "w") as f:
        json.dump(db, f, indent=2)


def find_deal(db: dict, deal_id: str) -> dict | None:
    for deal in db["deals"]:
        if deal["id"] == deal_id:
            return deal
    return None


def generate_id() -> str:
    return "deal_" + uuid.uuid4().hex[:8]


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# CPM logic
# ---------------------------------------------------------------------------

def calculate_cpm(cost: float, views: int) -> float:
    if views == 0:
        return 0.0
    return (cost / views) * 1000


def is_flagged(cpm: float) -> bool:
    return cpm > CPM_FLAG_THRESHOLD


def cpm_label(cpm: float) -> str:
    if cpm == 0.0:
        return "N/A (no views)"
    if is_flagged(cpm):
        return f"${cpm:,.2f} \u2190 FLAGGED (over $1K CPM threshold!)"
    return f"${cpm:,.2f} \u2190 GOOD (under $1K threshold)"


# ---------------------------------------------------------------------------
# Slack
# ---------------------------------------------------------------------------

def slack_post(text: str) -> bool:
    token = get_env("SLACK_BOT_TOKEN")
    if not token:
        print("Warning: SLACK_BOT_TOKEN not set, skipping Slack post", file=sys.stderr)
        return False
    payload = json.dumps({"channel": SLACK_CHANNEL, "text": text}).encode()
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
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.load(resp)
            return result.get("ok", False)
    except Exception as e:
        print(f"Warning: Slack post failed: {e}", file=sys.stderr)
        return False


def slack_flag_alert(deal: dict) -> None:
    handle = deal.get("handle") or deal["influencer"]
    platform = deal.get("platform", "unknown").capitalize()
    cpm = deal.get("cpm_expected", 0.0)
    cost = deal.get("cost", 0.0)
    views = deal.get("expected_views", 0)
    text = (
        f"\u26a0\ufe0f CPM Alert: {handle} deal is ${cpm:,.2f} CPM (over $1K threshold)\n"
        f"Cost: ${cost:,.0f} | Views: {views:,} | Platform: {platform}"
    )
    slack_post(text)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_check(args: argparse.Namespace) -> None:
    cpm = calculate_cpm(args.cost, args.views)
    flagged = is_flagged(cpm)
    flag_str = "\u26a0\ufe0f  FLAGGED" if flagged else "\u2705 GOOD"
    print(f"\nCPM Check: {args.influencer}")
    print(f"   Cost: ${args.cost:,.2f} | Views: {args.views:,}")
    print(f"   CPM: {cpm_label(cpm)}")
    print(f"   Verdict: {flag_str}")
    print()


def cmd_add(args: argparse.Namespace) -> None:
    db = load_deals()

    cost = args.cost
    views = args.views
    cpm = calculate_cpm(cost, views)
    flagged = is_flagged(cpm)

    deal_id = generate_id()
    ts = now_iso()

    handle = args.handle or ""
    display_handle = handle if handle else args.influencer

    deal = {
        "id": deal_id,
        "influencer": args.influencer,
        "handle": handle,
        "platform": args.platform,
        "post_url": args.post or "",
        "cost": cost,
        "expected_views": views,
        "actual_views": None,
        "cpm_expected": round(cpm, 4),
        "cpm_actual": None,
        "flagged": flagged,
        "notes": args.notes or "",
        "added_at": ts,
        "updated_at": ts,
    }

    db["deals"].append(deal)
    save_deals(db)

    platform_str = args.platform.capitalize()
    flag_line = f"   CPM: {cpm_label(cpm)}"

    if flagged:
        print(f"\n\u26a0\ufe0f  Deal added: {args.influencer} ({display_handle}) \u2014 {platform_str}")
    else:
        print(f"\n\u2705 Deal added: {args.influencer} ({display_handle}) \u2014 {platform_str}")

    print(f"   Cost: ${cost:,.2f} | Views: {views:,}")
    print(flag_line)
    print(f"   Deal ID: {deal_id}")
    print()

    if flagged:
        ok = slack_flag_alert(deal)
        if ok:
            print("   Slack alert sent to #viral-hunt-reports")


def cmd_list(args: argparse.Namespace) -> None:
    db = load_deals()
    deals = db["deals"]

    if args.flagged:
        deals = [d for d in deals if d.get("flagged")]
        header = "Flagged Deals (over $1K CPM)"
    else:
        header = "All Deals"

    if not deals:
        print(f"\nNo deals found." + (" (none flagged)" if args.flagged else ""))
        return

    print(f"\n{header} ({len(deals)} total)\n")
    print(f"{'ID':<14} {'Influencer':<22} {'Platform':<12} {'Cost':>10} {'Views':>12} {'CPM (exp)':>12} {'Flag':<6} {'Added':<12}")
    print("-" * 100)

    for d in deals:
        flag = "\u26a0\ufe0f " if d.get("flagged") else "  "
        cpm_exp = d.get("cpm_expected", 0.0)
        cpm_str = f"${cpm_exp:,.2f}"
        views = d.get("expected_views", 0)
        added = d.get("added_at", "")[:10]
        platform = d.get("platform", "").capitalize()
        handle = d.get("handle") or ""
        name = d["influencer"]
        if handle:
            name = f"{name} ({handle})"
        name = name[:22]
        print(f"{d['id']:<14} {name:<22} {platform:<12} ${d['cost']:>9,.2f} {views:>12,} {cpm_str:>12} {flag:<6} {added:<12}")

    print()


def cmd_report(args: argparse.Namespace) -> None:
    db = load_deals()
    deals = db["deals"]

    today = datetime.now().strftime("%Y-%m-%d")
    lines = [f"\U0001f4ca Influencer CPM Report \u2014 {today}", ""]

    if not deals:
        lines.append("No deals recorded yet.")
        report = "\n".join(lines)
        print(report)
        if args.slack:
            slack_post(report)
        return

    total_spend = sum(d.get("cost", 0.0) for d in deals)
    flagged = [d for d in deals if d.get("flagged")]

    # Avg CPM (expected) across all deals with views
    cpms = [d["cpm_expected"] for d in deals if d.get("cpm_expected") is not None]
    avg_cpm = sum(cpms) / len(cpms) if cpms else 0.0

    lines.append(f"Total Deals: {len(deals)}")
    lines.append(f"Total Spend: ${total_spend:,.2f}")
    lines.append(f"Avg CPM: ${avg_cpm:,.2f}")
    lines.append(f"Flagged Deals: {len(flagged)}" + (" \u26a0\ufe0f" if flagged else ""))
    lines.append("")

    # Platform breakdown
    platforms: dict[str, list] = {}
    for d in deals:
        p = d.get("platform", "other")
        platforms.setdefault(p, []).append(d)

    lines.append("By Platform:")
    for p, pdeals in sorted(platforms.items()):
        p_spend = sum(d.get("cost", 0.0) for d in pdeals)
        p_cpms = [d["cpm_expected"] for d in pdeals if d.get("cpm_expected") is not None]
        p_avg = sum(p_cpms) / len(p_cpms) if p_cpms else 0.0
        lines.append(f"  {p.capitalize():<12} {len(pdeals)} deal{'s' if len(pdeals)!=1 else ''}  avg CPM ${p_avg:,.2f}  spend ${p_spend:,.2f}")

    lines.append("")

    if flagged:
        lines.append("\u26a0\ufe0f  Flagged (over $1K CPM):")
        for d in flagged:
            handle = d.get("handle") or d["influencer"]
            platform = d.get("platform", "").capitalize()
            cpm = d.get("cpm_expected", 0.0)
            cost = d.get("cost", 0.0)
            views = d.get("expected_views", 0)
            lines.append(f"  {d['influencer']} ({handle}) {platform} ${cpm:,.2f} CPM \u2014 ${cost:,.0f} for {views:,} views")
        lines.append("")

    # Top performers (lowest CPM), skip zero
    ranked = sorted([d for d in deals if d.get("cpm_expected", 0) > 0], key=lambda d: d["cpm_expected"])
    if ranked:
        lines.append("Top Performers (lowest CPM):")
        for d in ranked[:3]:
            handle = d.get("handle") or d["influencer"]
            platform = d.get("platform", "").capitalize()
            cpm = d.get("cpm_expected", 0.0)
            lines.append(f"  {d['influencer']} ({handle}) {platform} ${cpm:,.2f} CPM")
        lines.append("")

    # Worst performers (highest CPM)
    if len(ranked) > 3:
        lines.append("Worst Performers (highest CPM):")
        for d in reversed(ranked[-3:]):
            handle = d.get("handle") or d["influencer"]
            platform = d.get("platform", "").capitalize()
            cpm = d.get("cpm_expected", 0.0)
            lines.append(f"  {d['influencer']} ({handle}) {platform} ${cpm:,.2f} CPM")
        lines.append("")

    report = "\n".join(lines)
    print(report)

    if args.slack:
        ok = slack_post(report)
        if ok:
            print("Report sent to #viral-hunt-reports")
        else:
            print("Slack post failed")


def cmd_update(args: argparse.Namespace) -> None:
    db = load_deals()
    deal = find_deal(db, args.deal_id)
    if not deal:
        print(f"Error: Deal '{args.deal_id}' not found.", file=sys.stderr)
        sys.exit(1)

    deal["actual_views"] = args.actual_views
    actual_cpm = calculate_cpm(deal["cost"], args.actual_views)
    deal["cpm_actual"] = round(actual_cpm, 4)
    deal["updated_at"] = now_iso()

    # Re-evaluate flag based on actual CPM
    if is_flagged(actual_cpm):
        deal["flagged"] = True

    save_deals(db)

    print(f"\nUpdated: {deal['influencer']} ({deal['id']})")
    print(f"   Actual Views: {args.actual_views:,}")
    print(f"   Actual CPM: {cpm_label(actual_cpm)}")
    print(f"   Expected CPM was: ${deal.get('cpm_expected', 0):,.2f}")
    print()


def cmd_remove(args: argparse.Namespace) -> None:
    db = load_deals()
    before = len(db["deals"])
    db["deals"] = [d for d in db["deals"] if d["id"] != args.deal_id]
    after = len(db["deals"])

    if before == after:
        print(f"Error: Deal '{args.deal_id}' not found.", file=sys.stderr)
        sys.exit(1)

    save_deals(db)
    print(f"Removed deal {args.deal_id}")


def cmd_analyze(args: argparse.Namespace) -> None:
    api_key = get_env("ANTHROPIC_API_KEY", required=True)
    db = load_deals()
    deals = db["deals"]

    if not deals:
        print("No deals to analyze.")
        return

    # Build a summary for the AI
    summary_lines = []
    for d in deals:
        handle = d.get("handle") or d["influencer"]
        summary_lines.append(
            f"- {d['influencer']} ({handle}), {d.get('platform', 'unknown')}, "
            f"cost ${d.get('cost', 0):,.2f}, expected views {d.get('expected_views', 0):,}, "
            f"expected CPM ${d.get('cpm_expected', 0):,.2f}, "
            f"actual views {d.get('actual_views') or 'N/A'}, "
            f"actual CPM ${d.get('cpm_actual') or 'N/A'}, "
            f"flagged: {d.get('flagged', False)}, notes: {d.get('notes', '')}"
        )

    prompt = (
        "You are an influencer marketing analyst. Analyze this deal portfolio and give actionable recommendations.\n\n"
        "Deals:\n" + "\n".join(summary_lines) + "\n\n"
        "Provide:\n"
        "1. Best and worst CPM deals and why\n"
        "2. Platform benchmarks (which platforms perform best)\n"
        "3. 3-5 specific recommendations to improve CPM efficiency\n"
        "4. Any red flags beyond just CPM (e.g., low-view deals at any cost)\n\n"
        "Be direct and concise. Skip fluff."
    )

    payload = json.dumps({
        "model": "claude-haiku-4-5",
        "max_tokens": 1024,
        "messages": [{"role": "user", "content": prompt}],
    }).encode()

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        method="POST",
    )

    print("\nAnalyzing deal portfolio...\n")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.load(resp)
            text = result["content"][0]["text"]
            print(text)
            print()
    except Exception as e:
        print(f"Error calling Anthropic API: {e}", file=sys.stderr)
        sys.exit(1)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="track.py",
        description="Influencer CPM Tracker — flag anything over $1K CPM",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # check
    p_check = sub.add_parser("check", help="Quick CPM check without saving")
    p_check.add_argument("influencer", help="Influencer name")
    p_check.add_argument("--cost", type=float, required=True, help="Deal cost in USD")
    p_check.add_argument("--views", type=int, required=True, help="Expected/actual views")

    # add
    p_add = sub.add_parser("add", help="Add a deal to the database")
    p_add.add_argument("influencer", help="Influencer name")
    p_add.add_argument("--cost", type=float, required=True, help="Deal cost in USD")
    p_add.add_argument("--views", type=int, required=True, help="Expected views")
    p_add.add_argument("--platform", default="instagram",
                       choices=["instagram", "tiktok", "youtube", "twitter", "other"],
                       help="Platform (default: instagram)")
    p_add.add_argument("--handle", default="", help="Social handle e.g. @janesmith")
    p_add.add_argument("--post", default="", help="Post URL")
    p_add.add_argument("--notes", default="", help="Free-text notes")

    # list
    p_list = sub.add_parser("list", help="List deals")
    p_list.add_argument("--flagged", action="store_true", help="Show only flagged deals")

    # report
    p_report = sub.add_parser("report", help="Summary report")
    p_report.add_argument("--slack", action="store_true", help="Also post to Slack")

    # update
    p_update = sub.add_parser("update", help="Update actual views post-campaign")
    p_update.add_argument("deal_id", help="Deal ID to update")
    p_update.add_argument("--actual-views", type=int, required=True, help="Actual view count")

    # remove
    p_remove = sub.add_parser("remove", help="Remove a deal")
    p_remove.add_argument("deal_id", help="Deal ID to remove")

    # analyze
    sub.add_parser("analyze", help="Claude Haiku portfolio analysis")

    args = parser.parse_args()

    dispatch = {
        "check": cmd_check,
        "add": cmd_add,
        "list": cmd_list,
        "report": cmd_report,
        "update": cmd_update,
        "remove": cmd_remove,
        "analyze": cmd_analyze,
    }

    dispatch[args.command](args)


if __name__ == "__main__":
    main()
