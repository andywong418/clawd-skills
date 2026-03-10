#!/usr/bin/env python3
"""App Store Spy — track competitor apps by keyword or category.

Usage:
  python3 spy.py watch "social media"
  python3 spy.py watch fitness --category health
  python3 spy.py fetch
  python3 spy.py report
  python3 spy.py report "social media"
  python3 spy.py report "social media" --analyze
  python3 spy.py compare TikTok Instagram
  python3 spy.py search "ai photo editor"
  python3 spy.py unwatch "social media"
  python3 spy.py list
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BASE_DIR = Path.home() / ".clawdbot" / "appstore-spy"
WATCHLIST_PATH = BASE_DIR / "watchlist.json"
DATA_DIR = BASE_DIR / "data"
TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")

SLACK_CHANNEL = "C0AHBK5E9V3"

CATEGORIES = {
    "gaming": "6014",
    "productivity": "6007",
    "social": "6005",
    "photo": "6008",
    "entertainment": "6016",
    "health": "6013",
    "finance": "6015",
    "education": "6017",
    "business": "6000",
    "lifestyle": "6012",
    "music": "6011",
    "news": "6009",
    "sports": "6004",
    "travel": "6003",
    "utilities": "6002",
}

# Maps iTunes genreId → friendly name
GENRE_ID_TO_NAME = {v: k for k, v in CATEGORIES.items()}


# ---------------------------------------------------------------------------
# Env / Config
# ---------------------------------------------------------------------------

def _load_env(key: str) -> str | None:
    val = os.environ.get(key)
    if val:
        return val
    env_path = Path.home() / ".clawdbot" / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith(f"{key}="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def slugify(text: str) -> str:
    """Convert 'social media' → 'social-media'."""
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def fmt_count(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.0f}K"
    return str(n) if n else "0"


def ensure_dirs():
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def http_get(url: str, timeout: int = 15) -> dict | list:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; AppStoreSpy/1.0)"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


# ---------------------------------------------------------------------------
# Watchlist
# ---------------------------------------------------------------------------

def load_watchlist() -> list[dict]:
    if WATCHLIST_PATH.exists():
        with open(WATCHLIST_PATH) as f:
            return json.load(f)
    return []


def save_watchlist(wl: list[dict]):
    ensure_dirs()
    with open(WATCHLIST_PATH, "w") as f:
        json.dump(wl, f, indent=2)


def watchlist_add(keyword: str, category: str | None = None):
    wl = load_watchlist()
    slug = slugify(keyword)
    for entry in wl:
        if entry["slug"] == slug:
            print(f"Already watching: {keyword}")
            return
    entry = {"keyword": keyword, "slug": slug, "category": category, "added": TODAY}
    wl.append(entry)
    save_watchlist(wl)
    print(f"Now watching: {keyword}" + (f" (category: {category})" if category else ""))


def watchlist_remove(keyword: str):
    wl = load_watchlist()
    slug = slugify(keyword)
    before = len(wl)
    wl = [e for e in wl if e["slug"] != slug]
    if len(wl) == before:
        print(f"Not in watchlist: {keyword}")
    else:
        save_watchlist(wl)
        print(f"Removed: {keyword}")


def watchlist_list():
    wl = load_watchlist()
    if not wl:
        print("Nothing in watchlist. Use: spy.py watch <keyword>")
        return
    print(f"Watching {len(wl)} keyword(s):")
    for e in wl:
        cat = f" [{e['category']}]" if e.get("category") else ""
        print(f"  • {e['keyword']}{cat}  (since {e['added']})")


# ---------------------------------------------------------------------------
# Snapshot storage
# ---------------------------------------------------------------------------

def snapshot_dir(slug: str) -> Path:
    d = DATA_DIR / slug
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_snapshot(slug: str, apps: list[dict], date: str = TODAY):
    path = snapshot_dir(slug) / f"{date}.json"
    with open(path, "w") as f:
        json.dump(apps, f, indent=2)
    return path


def load_snapshot(slug: str, date: str = TODAY) -> list[dict] | None:
    path = snapshot_dir(slug) / f"{date}.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return None


def load_previous_snapshot(slug: str, before_date: str = TODAY) -> list[dict] | None:
    """Load the most recent snapshot strictly before before_date."""
    sdir = snapshot_dir(slug)
    dates = sorted(
        p.stem for p in sdir.glob("*.json") if p.stem < before_date
    )
    if not dates:
        return None
    with open(sdir / f"{dates[-1]}.json") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# iTunes / App Store APIs
# ---------------------------------------------------------------------------

def search_apps(term: str, limit: int = 50) -> list[dict]:
    """Search iTunes API for apps matching term."""
    url = (
        "https://itunes.apple.com/search"
        f"?term={urllib.parse.quote(term)}"
        f"&entity=software&media=software&country=us&limit={limit}"
    )
    try:
        data = http_get(url)
        return data.get("results", [])
    except Exception as e:
        print(f"  [warn] iTunes search failed for '{term}': {e}", file=sys.stderr)
        return []


def fetch_category_top(category_id: str, limit: int = 50) -> list[dict]:
    """Fetch top free apps from App Store RSS for a category."""
    # Apple Marketing Tools RSS — returns JSON
    url = f"https://rss.applemarketingtools.com/api/v2/us/apps/top-free/{limit}/apps.json"
    try:
        data = http_get(url)
        feed = data.get("feed", {})
        results = feed.get("results", [])
        # Filter to category if a genreId is available
        if category_id:
            results = [r for r in results if r.get("genreId") == category_id]
        # Now look up each app via iTunes to get full metadata
        enriched = []
        for i, r in enumerate(results[:limit]):
            app_id = r.get("id", "")
            if not app_id:
                continue
            try:
                detail = lookup_app(app_id)
                if detail:
                    enriched.append(detail)
            except Exception as e:
                print(f"  [warn] lookup failed for {app_id}: {e}", file=sys.stderr)
            if i > 0 and i % 10 == 0:
                time.sleep(0.5)
        return enriched
    except Exception as e:
        print(f"  [warn] RSS feed failed for category {category_id}: {e}", file=sys.stderr)
        return []


def lookup_app(app_id: str) -> dict | None:
    """Fetch full metadata for a single app by ID."""
    url = f"https://itunes.apple.com/lookup?id={app_id}&country=us&entity=software"
    try:
        data = http_get(url)
        results = data.get("results", [])
        if results:
            return results[0]
    except Exception as e:
        print(f"  [warn] lookup failed for {app_id}: {e}", file=sys.stderr)
    return None


def normalize_app(raw: dict, rank: int = 0) -> dict:
    """Normalize an iTunes API result into our canonical format."""
    app_id = str(raw.get("trackId", raw.get("id", "")))
    name = raw.get("trackName", raw.get("name", ""))
    developer = raw.get("artistName", raw.get("sellerName", ""))
    subtitle = raw.get("subtitle", "")
    category = raw.get("primaryGenreName", raw.get("genres", [""])[0] if raw.get("genres") else "")
    rating = raw.get("averageUserRating", 0.0)
    rating_count = raw.get("userRatingCount", 0)
    price = raw.get("price", 0.0)
    description = (raw.get("description", "") or "")[:500]
    icon_url = raw.get("artworkUrl100", raw.get("artworkUrl512", ""))
    version = raw.get("version", "")
    size_bytes = raw.get("fileSizeBytes", 0)
    bundle_id = raw.get("bundleId", "")

    # Build store URL
    track_id = raw.get("trackId", "")
    track_view_url = raw.get("trackViewUrl", "")
    if not track_view_url and track_id:
        track_view_url = f"https://apps.apple.com/us/app/id{track_id}"

    return {
        "rank": rank,
        "app_id": app_id,
        "name": name,
        "developer": developer,
        "subtitle": subtitle,
        "category": category,
        "rating": round(float(rating), 1) if rating else 0.0,
        "rating_count": int(rating_count) if rating_count else 0,
        "price": float(price) if price else 0.0,
        "version": version,
        "size_bytes": int(size_bytes) if size_bytes else 0,
        "bundle_id": bundle_id,
        "icon_url": icon_url,
        "store_url": track_view_url,
        "description": description,
        "snapshot_date": TODAY,
    }


# ---------------------------------------------------------------------------
# Fetch command
# ---------------------------------------------------------------------------

def do_fetch_keyword(entry: dict) -> list[dict]:
    keyword = entry["keyword"]
    slug = entry["slug"]
    category = entry.get("category")

    print(f"Fetching: {keyword}" + (f" [{category}]" if category else ""))

    raw_apps = []
    if category and category in CATEGORIES:
        cat_id = CATEGORIES[category]
        # Try RSS feed first for category top charts
        raw_apps = fetch_category_top(cat_id, limit=50)
        if not raw_apps:
            # Fallback to search
            print(f"  RSS fallback → iTunes search for '{keyword}'")
            raw_apps = search_apps(keyword, limit=50)
    else:
        raw_apps = search_apps(keyword, limit=50)

    apps = []
    for i, raw in enumerate(raw_apps[:50]):
        app = normalize_app(raw, rank=i + 1)
        apps.append(app)

    if apps:
        path = save_snapshot(slug, apps)
        print(f"  Saved {len(apps)} apps → {path}")
    else:
        print(f"  No apps found for '{keyword}'")

    return apps


def cmd_watch(keyword: str, category: str | None):
    ensure_dirs()
    watchlist_add(keyword, category)
    entry = {"keyword": keyword, "slug": slugify(keyword), "category": category, "added": TODAY}
    do_fetch_keyword(entry)


def cmd_fetch():
    ensure_dirs()
    wl = load_watchlist()
    if not wl:
        print("Nothing to fetch. Use: spy.py watch <keyword>")
        return
    for i, entry in enumerate(wl):
        do_fetch_keyword(entry)
        if i < len(wl) - 1:
            time.sleep(0.5)
    print(f"\nFetched {len(wl)} keyword(s).")


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def rank_change_symbol(old_rank: int | None, new_rank: int) -> str:
    if old_rank is None:
        return "NEW"
    diff = old_rank - new_rank  # positive = climbed
    if diff == 0:
        return "→"
    if diff > 0:
        return f"▲{diff}"
    return f"▼{abs(diff)}"


def build_report_text(keyword: str, apps: list[dict], prev_apps: list[dict] | None, top: int = 10) -> str:
    prev_rank_map: dict[str, int] = {}
    if prev_apps:
        for a in prev_apps:
            prev_rank_map[a["app_id"]] = a["rank"]

    lines = [
        f"Top {top} — \"{keyword}\" — {TODAY}",
        f"{'Rank':<6}{'App':<22}{'Subtitle':<30}{'Rating':<8}{'Reviews':<11}Change",
        "─" * 85,
    ]

    for app in apps[:top]:
        rank = app["rank"]
        name = (app["name"] or "")[:20]
        subtitle = (app["subtitle"] or "—")[:28]
        rating = f"{app['rating']:.1f}★" if app["rating"] else "—"
        reviews = fmt_count(app["rating_count"])
        old_rank = prev_rank_map.get(app["app_id"])
        change = rank_change_symbol(old_rank, rank)

        lines.append(
            f"#{rank:<5}{name:<22}{subtitle:<30}{rating:<8}{reviews:<11}{change}"
        )

    return "\n".join(lines)


def cmd_report(keyword: str | None, analyze: bool, post_slack: bool):
    ensure_dirs()
    wl = load_watchlist()

    if keyword:
        slug = slugify(keyword)
        entries = [e for e in wl if e["slug"] == slug]
        if not entries:
            # Still try if snapshot exists
            entries = [{"keyword": keyword, "slug": slug, "category": None}]
    else:
        entries = wl

    if not entries:
        print("Nothing to report. Use: spy.py watch <keyword>")
        return

    full_report_parts = []

    for entry in entries:
        kw = entry["keyword"]
        slug = entry["slug"]
        apps = load_snapshot(slug, TODAY)
        if not apps:
            print(f"No data for '{kw}' today. Run: spy.py fetch")
            continue
        prev = load_previous_snapshot(slug, TODAY)
        text = build_report_text(kw, apps, prev, top=10)
        full_report_parts.append(text)

        if analyze:
            insight = run_analysis(kw, apps[:10])
            if insight:
                full_report_parts.append(f"\n--- Claude Analysis ---\n{insight}")

    if not full_report_parts:
        return

    full_report = "\n\n".join(full_report_parts)
    print(full_report)

    if post_slack:
        slack_post(f"```\n{full_report}\n```")


# ---------------------------------------------------------------------------
# Compare
# ---------------------------------------------------------------------------

def cmd_compare(app_name1: str, app_name2: str):
    print(f"Searching for '{app_name1}' and '{app_name2}'...")
    r1 = search_apps(app_name1, limit=5)
    time.sleep(0.5)
    r2 = search_apps(app_name2, limit=5)

    if not r1:
        print(f"No results for '{app_name1}'")
        return
    if not r2:
        print(f"No results for '{app_name2}'")
        return

    a1 = normalize_app(r1[0])
    a2 = normalize_app(r2[0])

    fields = [
        ("App", "name"),
        ("Developer", "developer"),
        ("Subtitle", "subtitle"),
        ("Category", "category"),
        ("Rating", "rating"),
        ("Reviews", "rating_count"),
        ("Price", "price"),
        ("Version", "version"),
    ]

    print(f"\n{'Field':<14}{a1['name'][:30]:<32}{a2['name'][:30]:<32}")
    print("─" * 80)
    for label, field in fields:
        v1 = a1.get(field, "")
        v2 = a2.get(field, "")
        if field == "rating_count":
            v1 = fmt_count(int(v1))
            v2 = fmt_count(int(v2))
        elif field == "rating":
            v1 = f"{v1:.1f}★" if v1 else "—"
            v2 = f"{v2:.1f}★" if v2 else "—"
        elif field == "price":
            v1 = "Free" if v1 == 0.0 else f"${v1:.2f}"
            v2 = "Free" if v2 == 0.0 else f"${v2:.2f}"
        print(f"{label:<14}{str(v1)[:30]:<32}{str(v2)[:30]:<32}")

    print(f"\n{'Store URL':<14}{a1['store_url']}")
    print(f"{'':14}{a2['store_url']}")


# ---------------------------------------------------------------------------
# Search (one-off)
# ---------------------------------------------------------------------------

def cmd_search(term: str, limit: int = 10):
    print(f"Searching App Store: '{term}'...")
    raw = search_apps(term, limit=limit)
    if not raw:
        print("No results.")
        return

    print(f"\n{'#':<5}{'App':<25}{'Subtitle':<28}{'Rating':<8}{'Reviews':<10}{'Price'}")
    print("─" * 82)
    for i, r in enumerate(raw[:limit], 1):
        app = normalize_app(r, rank=i)
        name = (app["name"] or "")[:23]
        subtitle = (app["subtitle"] or "—")[:26]
        rating = f"{app['rating']:.1f}★" if app["rating"] else "—"
        reviews = fmt_count(app["rating_count"])
        price = "Free" if app["price"] == 0.0 else f"${app['price']:.2f}"
        print(f"#{i:<4}{name:<25}{subtitle:<28}{rating:<8}{reviews:<10}{price}")
        print(f"      {app['store_url']}")


# ---------------------------------------------------------------------------
# Claude analysis
# ---------------------------------------------------------------------------

def run_analysis(keyword: str, apps: list[dict]) -> str | None:
    api_key = _load_env("ANTHROPIC_API_KEY")
    if not api_key:
        print("[warn] ANTHROPIC_API_KEY not set — skipping analysis")
        return None

    app_list = "\n".join(
        f"#{a['rank']} {a['name']} — subtitle: \"{a['subtitle'] or 'none'}\" "
        f"— rating: {a['rating']} ({fmt_count(a['rating_count'])} reviews) "
        f"— developer: {a['developer']}"
        for a in apps
    )

    prompt = f"""You are analyzing App Store ranking data for the keyword/category: "{keyword}".

Top 10 apps right now:
{app_list}

In 4-6 bullet points, identify:
- Rising apps or surprising entrants
- Subtitle patterns that seem to work (short punchy vs descriptive)
- Rating/review quality signals (high ratings with low reviews = newer; high both = established)
- Any clear market gaps or underserved angles
- One tactical recommendation for a new app trying to enter this space

Be specific and concise. No fluff."""

    payload = json.dumps({
        "model": "claude-haiku-4-5",
        "max_tokens": 400,
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
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
        return data["content"][0]["text"].strip()
    except Exception as e:
        print(f"[warn] Claude analysis failed: {e}", file=sys.stderr)
        return None


# ---------------------------------------------------------------------------
# Slack
# ---------------------------------------------------------------------------

def slack_post(text: str, channel: str = SLACK_CHANNEL):
    token = _load_env("SLACK_BOT_TOKEN")
    if not token:
        print("[warn] SLACK_BOT_TOKEN not set — skipping Slack post")
        return

    payload = json.dumps({
        "channel": channel,
        "text": text,
    }).encode()

    req = urllib.request.Request(
        "https://slack.com/api/chat.postMessage",
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
        if result.get("ok"):
            print(f"[slack] Posted to {channel}")
        else:
            print(f"[slack] Error: {result.get('error')}", file=sys.stderr)
    except Exception as e:
        print(f"[slack] Post failed: {e}", file=sys.stderr)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="spy.py",
        description="App Store Spy — track competitor apps by keyword or category",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # watch
    p_watch = sub.add_parser("watch", help="Start watching a keyword or category")
    p_watch.add_argument("keyword", help="Keyword or category label to watch")
    p_watch.add_argument(
        "--category",
        choices=list(CATEGORIES.keys()),
        help="Use App Store top charts for this category instead of keyword search",
    )

    # unwatch
    p_unwatch = sub.add_parser("unwatch", help="Stop watching a keyword")
    p_unwatch.add_argument("keyword")

    # fetch
    sub.add_parser("fetch", help="Refresh all watched keywords/categories")

    # report
    p_report = sub.add_parser("report", help="Show current rankings + rank changes")
    p_report.add_argument("keyword", nargs="?", help="Specific keyword (optional)")
    p_report.add_argument("--analyze", action="store_true", help="Add Claude AI insights")
    p_report.add_argument("--slack", action="store_true", help="Post report to Slack")
    p_report.add_argument("--top", type=int, default=10, help="Number of apps to show")

    # compare
    p_compare = sub.add_parser("compare", help="Side-by-side app comparison")
    p_compare.add_argument("app1", help="First app name")
    p_compare.add_argument("app2", help="Second app name")

    # search
    p_search = sub.add_parser("search", help="One-off search without saving")
    p_search.add_argument("term", help="Search term")
    p_search.add_argument("--limit", type=int, default=10, help="Max results (default: 10)")

    # list
    sub.add_parser("list", help="Show all watched keywords")

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    ensure_dirs()

    if args.cmd == "watch":
        cmd_watch(args.keyword, args.category)

    elif args.cmd == "unwatch":
        watchlist_remove(args.keyword)

    elif args.cmd == "fetch":
        cmd_fetch()

    elif args.cmd == "report":
        cmd_report(
            keyword=getattr(args, "keyword", None),
            analyze=getattr(args, "analyze", False),
            post_slack=getattr(args, "slack", False),
        )

    elif args.cmd == "compare":
        cmd_compare(args.app1, args.app2)

    elif args.cmd == "search":
        cmd_search(args.term, limit=args.limit)

    elif args.cmd == "list":
        watchlist_list()


if __name__ == "__main__":
    main()
