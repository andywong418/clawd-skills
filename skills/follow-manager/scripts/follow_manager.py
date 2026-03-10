#!/usr/bin/env python3
"""Follow Manager — strategic TikTok follow/unfollow automation.

Commands:
  follow-commenters   Follow people who commented on your recent posts
  follow-hashtag      Follow people engaging with a hashtag feed
  follow-fans         Follow followers of a target account
  unfollow            Unfollow accounts that didn't follow back after N days
  status              Show follow stats

Requirements:
  pip install playwright
  playwright install chromium

Usage:
  python3 follow_manager.py --account tiktok_user follow-commenters
  python3 follow_manager.py --account tiktok_user follow-hashtag --hashtag aivideo
  python3 follow_manager.py --account tiktok_user follow-fans --of someaccount
  python3 follow_manager.py --account tiktok_user unfollow --after-days 3
  python3 follow_manager.py --account tiktok_user status
"""

import argparse
import asyncio
import json
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    from playwright.async_api import Page, async_playwright
except ImportError:
    print("playwright not installed.")
    print("Run: pip install playwright && playwright install chromium")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

ACCOUNTS_DIR = Path.home() / ".clawdbot" / "warmup" / "accounts"
FOLLOWS_FILE = "follows.json"

# Safety limits per session
MAX_FOLLOWS_PER_SESSION = 30
MAX_UNFOLLOWS_PER_SESSION = 30
DEFAULT_VIDEOS_TO_CHECK = 5
DEFAULT_UNFOLLOW_AFTER_DAYS = 3

MIN_DELAY_S = 3.0
MAX_DELAY_S = 8.0


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

def load_state(account_key: str) -> dict | None:
    f = ACCOUNTS_DIR / account_key / "state.json"
    return json.loads(f.read_text()) if f.exists() else None


def browser_profile_dir(account_key: str) -> Path:
    return ACCOUNTS_DIR / account_key / "browser_profile"


def load_follows(account_key: str) -> dict:
    f = ACCOUNTS_DIR / account_key / FOLLOWS_FILE
    return json.loads(f.read_text()) if f.exists() else {}


def save_follows(account_key: str, follows: dict):
    f = ACCOUNTS_DIR / account_key / FOLLOWS_FILE
    f.write_text(json.dumps(follows, indent=2))


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Playwright helpers
# ---------------------------------------------------------------------------

async def jitter():
    await asyncio.sleep(random.uniform(MIN_DELAY_S, MAX_DELAY_S))


async def safe_text(page: Page, selector: str) -> str:
    try:
        el = await page.query_selector(selector)
        if el:
            return (await el.inner_text()).strip()
    except Exception:
        pass
    return ""


async def open_browser(account_key: str):
    """Return (playwright, context, page) with the persistent profile."""
    pw = await async_playwright().start()
    profile_dir = browser_profile_dir(account_key)
    profile_dir.mkdir(parents=True, exist_ok=True)

    context = await pw.chromium.launch_persistent_context(
        user_data_dir=str(profile_dir),
        headless=False,
        viewport={"width": 390, "height": 844},
        user_agent=(
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 "
            "Mobile/15E148 Safari/604.1"
        ),
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-first-run",
            "--disable-infobars",
        ],
        ignore_default_args=["--enable-automation"],
    )
    page = context.pages[0] if context.pages else await context.new_page()
    return pw, context, page


async def ensure_logged_in(page: Page):
    await page.goto("https://www.tiktok.com", wait_until="domcontentloaded", timeout=20000)
    await asyncio.sleep(2)
    login_modal = await page.query_selector('[data-e2e="login-button"]')
    if login_modal:
        print("\n⚠ Not logged into TikTok.")
        print("  Log in manually in the browser window, then press Enter.")
        input("  Press Enter once logged in: ")


# ---------------------------------------------------------------------------
# Follow / unfollow actions
# ---------------------------------------------------------------------------

async def is_already_following(page: Page) -> bool:
    """Check if the Follow button on the current profile shows 'Following'."""
    for sel in [
        '[data-e2e="follow-button"]',
        'button[class*="ButtonFollow"]',
        'button[class*="follow"]',
    ]:
        try:
            btn = await page.query_selector(sel)
            if btn:
                label = (await btn.inner_text()).strip().lower()
                aria = (await btn.get_attribute("aria-label") or "").lower()
                if "following" in label or "following" in aria:
                    return True
                if "follow" in label or "follow" in aria:
                    return False
        except Exception:
            continue
    return False


async def follow_profile(page: Page, username: str) -> bool:
    """Navigate to a profile and click Follow. Returns True on success."""
    try:
        url = f"https://www.tiktok.com/@{username.lstrip('@')}"
        await page.goto(url, wait_until="domcontentloaded", timeout=20000)
        await asyncio.sleep(2)

        if await is_already_following(page):
            print(f"    Already following @{username}", file=sys.stderr)
            return False  # not a new follow

        for sel in [
            '[data-e2e="follow-button"]',
            'button[class*="ButtonFollow"]',
        ]:
            btn = await page.query_selector(sel)
            if btn:
                await btn.click()
                await asyncio.sleep(1.5)
                return True

        print(f"    Could not find Follow button for @{username}", file=sys.stderr)
        return False

    except Exception as e:
        print(f"    Error following @{username}: {e}", file=sys.stderr)
        return False


async def follows_you_back(page: Page) -> bool:
    """Check if the current profile has a 'Follows you' indicator."""
    indicators = [
        '[class*="FollowsYou"]',
        '[data-e2e="follows-you"]',
        'span[class*="follows-you"]',
    ]
    for sel in indicators:
        try:
            el = await page.query_selector(sel)
            if el:
                return True
        except Exception:
            continue

    # Fallback: scan page text
    try:
        body = await page.inner_text("body")
        if "Follows you" in body:
            return True
    except Exception:
        pass

    return False


async def unfollow_profile(page: Page, username: str) -> bool:
    """Navigate to profile and unfollow. Returns True on success."""
    try:
        url = f"https://www.tiktok.com/@{username.lstrip('@')}"
        await page.goto(url, wait_until="domcontentloaded", timeout=20000)
        await asyncio.sleep(2)

        # Find "Following" button
        for sel in [
            '[data-e2e="follow-button"]',
            'button[class*="ButtonFollow"]',
        ]:
            btn = await page.query_selector(sel)
            if btn:
                label = (await btn.inner_text()).strip().lower()
                if "following" in label:
                    await btn.click()
                    await asyncio.sleep(1.5)

                    # Confirm unfollow dialog if it appears
                    for confirm_sel in [
                        'button[class*="Confirm"]',
                        'button:has-text("Unfollow")',
                        '[data-e2e="unfollow-button"]',
                    ]:
                        try:
                            confirm = await page.query_selector(confirm_sel)
                            if confirm:
                                await confirm.click()
                                await asyncio.sleep(1)
                                break
                        except Exception:
                            continue

                    return True

        print(f"    Not following @{username} (or button not found)", file=sys.stderr)
        return False

    except Exception as e:
        print(f"    Error unfollowing @{username}: {e}", file=sys.stderr)
        return False


# ---------------------------------------------------------------------------
# Source scrapers
# ---------------------------------------------------------------------------

async def scrape_commenters(page: Page, username: str, video_count: int) -> list[str]:
    """Return list of usernames who commented on recent videos."""
    print(f"  Visiting @{username}'s profile for recent videos...", file=sys.stderr)
    await page.goto(f"https://www.tiktok.com/@{username}", wait_until="domcontentloaded", timeout=25000)
    await asyncio.sleep(3)

    video_urls = []
    for sel in ['a[href*="/video/"]', '[data-e2e="user-post-item"] a']:
        elements = await page.query_selector_all(sel)
        for el in elements:
            href = await el.get_attribute("href")
            if href and "/video/" in href:
                full = href if href.startswith("http") else f"https://www.tiktok.com{href}"
                if full not in video_urls:
                    video_urls.append(full)
        if video_urls:
            break

    commenters = set()

    for url in video_urls[:video_count]:
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=25000)
            await asyncio.sleep(3)

            # Scroll to load more comments
            for _ in range(2):
                await page.keyboard.press("End")
                await asyncio.sleep(1.5)

            for sel in ['[data-e2e="comment-item"]', 'div[class*="DivCommentItemContainer"]']:
                items = await page.query_selector_all(sel)
                if items:
                    for item in items:
                        for usel in ['[data-e2e="comment-username"]', 'span[class*="UniqueId"]']:
                            try:
                                el = await item.query_selector(usel)
                                if el:
                                    uname = (await el.inner_text()).strip().lstrip("@")
                                    if uname and uname.lower() != username.lower():
                                        commenters.add(uname)
                                    break
                            except Exception:
                                continue
                    break

        except Exception as e:
            print(f"    Error scraping {url}: {e}", file=sys.stderr)
            continue

    return list(commenters)


async def scrape_hashtag_creators(page: Page, hashtag: str, limit: int) -> list[str]:
    """Return usernames of creators appearing in a hashtag feed."""
    print(f"  Browsing #{hashtag}...", file=sys.stderr)
    await page.goto(f"https://www.tiktok.com/tag/{hashtag}", wait_until="domcontentloaded", timeout=25000)
    await asyncio.sleep(3)

    # Click first video
    for sel in ['[data-e2e="challenge-item"]', 'a[href*="/video/"]']:
        items = await page.query_selector_all(sel)
        if items:
            await items[0].click()
            await asyncio.sleep(3)
            break

    creators = []
    seen = set()

    for _ in range(limit + 5):  # overshoot to account for dupes
        if len(creators) >= limit:
            break

        # Get current video creator
        for sel in [
            '[data-e2e="video-author-uniqueid"]',
            '[data-e2e="browse-username"]',
            'a[href*="/@"] span',
        ]:
            try:
                el = await page.query_selector(sel)
                if el:
                    uname = (await el.inner_text()).strip().lstrip("@")
                    if uname and uname not in seen:
                        creators.append(uname)
                        seen.add(uname)
                    break
            except Exception:
                continue

        await page.keyboard.press("ArrowDown")
        await asyncio.sleep(random.uniform(1.5, 3))

    return creators


async def scrape_fans_of(page: Page, target_account: str, limit: int) -> list[str]:
    """Return usernames from a target account's followers list."""
    target = target_account.lstrip("@")
    print(f"  Visiting @{target}'s followers...", file=sys.stderr)

    await page.goto(f"https://www.tiktok.com/@{target}", wait_until="domcontentloaded", timeout=25000)
    await asyncio.sleep(3)

    # Click followers count to open modal
    for sel in [
        '[data-e2e="followers-count"]',
        'strong[title*="Followers"]',
        'a[href*="followers"]',
    ]:
        try:
            el = await page.query_selector(sel)
            if el:
                await el.click()
                await asyncio.sleep(2)
                break
        except Exception:
            continue

    followers = []
    seen = set()

    # Scroll the followers modal
    for _ in range(limit // 5 + 3):
        for sel in [
            '[data-e2e="follower-item"] [data-e2e="user-unique-id"]',
            'div[class*="DivFollowerContainer"] span[class*="UniqueId"]',
            '[class*="FollowerItem"] a',
        ]:
            items = await page.query_selector_all(sel)
            for item in items:
                try:
                    uname = (await item.inner_text()).strip().lstrip("@")
                    if uname and uname not in seen:
                        followers.append(uname)
                        seen.add(uname)
                except Exception:
                    continue

        if len(followers) >= limit:
            break

        # Scroll the modal
        try:
            modal = await page.query_selector('[class*="DivFollowerModal"], [class*="ModalContainer"]')
            if modal:
                await modal.evaluate("el => el.scrollTop += 600")
            else:
                await page.keyboard.press("End")
            await asyncio.sleep(1.5)
        except Exception:
            break

    return followers[:limit]


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

async def cmd_follow(account_key: str, username: str, targets: list[str], source: str):
    follows = load_follows(account_key)
    already_tracked = set(follows.keys())

    new_targets = [u for u in targets if u.lower() not in {k.lower() for k in already_tracked}]
    print(f"\n  {len(targets)} candidates, {len(new_targets)} not yet followed", file=sys.stderr)

    if not new_targets:
        print("  Nothing new to follow.", file=sys.stderr)
        return 0

    pw, context, page = await open_browser(account_key)
    await ensure_logged_in(page)

    followed = 0
    for uname in new_targets[:MAX_FOLLOWS_PER_SESSION]:
        print(f"  → @{uname}", file=sys.stderr)
        success = await follow_profile(page, uname)
        if success:
            follows[uname] = {
                "followed_at": now_iso(),
                "source": source,
                "followed_back": False,
                "unfollowed_at": None,
            }
            save_follows(account_key, follows)
            followed += 1
            print(f"    ✓ followed ({followed}/{MAX_FOLLOWS_PER_SESSION})", file=sys.stderr)
            await jitter()
        else:
            await asyncio.sleep(1)

    await context.close()
    await pw.stop()
    return followed


async def cmd_unfollow(account_key: str, username: str, after_days: int):
    follows = load_follows(account_key)
    cutoff = datetime.now(timezone.utc) - timedelta(days=after_days)

    candidates = [
        (uname, data) for uname, data in follows.items()
        if not data.get("unfollowed_at")
        and not data.get("followed_back")
        and datetime.fromisoformat(data["followed_at"]) < cutoff
    ]

    print(f"\n  {len(candidates)} accounts eligible to unfollow (followed >{after_days}d ago, no follow-back)",
          file=sys.stderr)

    if not candidates:
        print("  Nothing to unfollow.", file=sys.stderr)
        return 0

    pw, context, page = await open_browser(account_key)
    await ensure_logged_in(page)

    unfollowed = 0
    for uname, data in candidates[:MAX_UNFOLLOWS_PER_SESSION]:
        print(f"  → @{uname} (followed {data['followed_at'][:10]})", file=sys.stderr)

        # Navigate to check if they followed back before unfollowing
        try:
            await page.goto(f"https://www.tiktok.com/@{uname.lstrip('@')}",
                            wait_until="domcontentloaded", timeout=20000)
            await asyncio.sleep(2)

            if await follows_you_back(page):
                print(f"    ↩ follows you back — keeping", file=sys.stderr)
                follows[uname]["followed_back"] = True
                save_follows(account_key, follows)
                await asyncio.sleep(1)
                continue
        except Exception:
            pass

        success = await unfollow_profile(page, uname)
        if success:
            follows[uname]["unfollowed_at"] = now_iso()
            save_follows(account_key, follows)
            unfollowed += 1
            print(f"    ✓ unfollowed ({unfollowed}/{MAX_UNFOLLOWS_PER_SESSION})", file=sys.stderr)
            await jitter()
        else:
            await asyncio.sleep(1)

    await context.close()
    await pw.stop()
    return unfollowed


def cmd_status(account_key: str):
    follows = load_follows(account_key)

    if not follows:
        print("No follow history yet.")
        return

    total = len(follows)
    active = [f for f in follows.values() if not f.get("unfollowed_at")]
    unfollowed = [f for f in follows.values() if f.get("unfollowed_at")]
    followed_back = [f for f in follows.values() if f.get("followed_back")]

    pending_unfollow = [
        (u, f) for u, f in follows.items()
        if not f.get("unfollowed_at") and not f.get("followed_back")
    ]

    # Source breakdown
    sources: dict[str, int] = {}
    for f in follows.values():
        src = f.get("source", "unknown")
        sources[src] = sources.get(src, 0) + 1

    print(f"\n=== Follow Stats ===")
    print(f"  Total followed (ever): {total}")
    print(f"  Currently following:   {len(active)}")
    print(f"  Followed back:         {len(followed_back)}")
    print(f"  Unfollowed:            {len(unfollowed)}")
    print(f"  Pending unfollow:      {len(pending_unfollow)}")
    print(f"\n  By source:")
    for src, count in sorted(sources.items(), key=lambda x: -x[1]):
        print(f"    {src}: {count}")

    if pending_unfollow:
        oldest = sorted(pending_unfollow, key=lambda x: x[1]["followed_at"])[:3]
        print(f"\n  Oldest pending unfollows:")
        for u, f in oldest:
            print(f"    @{u} — followed {f['followed_at'][:10]}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Strategic TikTok follow/unfollow management",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--account", required=True, help="Account key (platform_username)")

    sub = parser.add_subparsers(dest="command")

    p_fc = sub.add_parser("follow-commenters", help="Follow people who commented on your recent posts")
    p_fc.add_argument("--videos", type=int, default=DEFAULT_VIDEOS_TO_CHECK,
                      help=f"Recent videos to scan (default: {DEFAULT_VIDEOS_TO_CHECK})")
    p_fc.add_argument("--max", type=int, default=MAX_FOLLOWS_PER_SESSION,
                      help=f"Max follows (default: {MAX_FOLLOWS_PER_SESSION})")

    p_fh = sub.add_parser("follow-hashtag", help="Follow creators from a hashtag feed")
    p_fh.add_argument("--hashtag", required=True, help="Hashtag to browse (without #)")
    p_fh.add_argument("--max", type=int, default=MAX_FOLLOWS_PER_SESSION,
                      help=f"Max follows (default: {MAX_FOLLOWS_PER_SESSION})")

    p_ff = sub.add_parser("follow-fans", help="Follow followers of a target account")
    p_ff.add_argument("--of", required=True, dest="target", help="Target account username")
    p_ff.add_argument("--max", type=int, default=MAX_FOLLOWS_PER_SESSION,
                      help=f"Max follows (default: {MAX_FOLLOWS_PER_SESSION})")

    p_un = sub.add_parser("unfollow", help="Unfollow non-followers after N days")
    p_un.add_argument("--after-days", type=int, default=DEFAULT_UNFOLLOW_AFTER_DAYS,
                      help=f"Days to wait before unfollowing (default: {DEFAULT_UNFOLLOW_AFTER_DAYS})")

    sub.add_parser("status", help="Show follow stats")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    state = load_state(args.account)
    if not state:
        print(f"Account '{args.account}' not found.")
        print("Run: python3 skills/warmup-trainer/scripts/warmup.py init")
        sys.exit(1)

    username = state["username"]
    print(f"[follow-manager] @{username}")

    if args.command == "status":
        cmd_status(args.account)
        return

    if args.command == "follow-commenters":
        async def run():
            pw, context, page = await open_browser(args.account)
            await ensure_logged_in(page)
            targets = await scrape_commenters(page, username, args.videos)
            await context.close()
            await pw.stop()
            print(f"  Found {len(targets)} commenters to follow", file=sys.stderr)
            n = await cmd_follow(args.account, username, targets[:args.max], source="commenters")
            print(f"\n✓ Followed {n} new accounts from commenters")
        asyncio.run(run())

    elif args.command == "follow-hashtag":
        async def run():
            pw, context, page = await open_browser(args.account)
            await ensure_logged_in(page)
            targets = await scrape_hashtag_creators(page, args.hashtag, args.max * 2)
            await context.close()
            await pw.stop()
            print(f"  Found {len(targets)} creators in #{args.hashtag}", file=sys.stderr)
            n = await cmd_follow(args.account, username, targets[:args.max],
                                 source=f"hashtag:{args.hashtag}")
            print(f"\n✓ Followed {n} new accounts from #{args.hashtag}")
        asyncio.run(run())

    elif args.command == "follow-fans":
        async def run():
            pw, context, page = await open_browser(args.account)
            await ensure_logged_in(page)
            targets = await scrape_fans_of(page, args.target, args.max * 2)
            await context.close()
            await pw.stop()
            print(f"  Found {len(targets)} followers of @{args.target}", file=sys.stderr)
            n = await cmd_follow(args.account, username, targets[:args.max],
                                 source=f"fans:{args.target}")
            print(f"\n✓ Followed {n} new accounts from @{args.target}'s followers")
        asyncio.run(run())

    elif args.command == "unfollow":
        n = asyncio.run(cmd_unfollow(args.account, username, args.after_days))
        print(f"\n✓ Unfollowed {n} accounts")


if __name__ == "__main__":
    main()
