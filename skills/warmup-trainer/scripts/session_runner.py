#!/usr/bin/env python3
"""Warmup Session Runner — automated niche engagement via Playwright.

Runs a timed TikTok session: navigates niche hashtag feeds, watches videos,
and ONLY likes content matching the niche. Off-topic content is scrolled past.

Requirements:
  pip install playwright
  playwright install chromium

Usage:
  python3 session_runner.py
  python3 session_runner.py --duration 7
  python3 session_runner.py --phase 2
"""

import argparse
import asyncio
import json
import random
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

try:
    from playwright.async_api import BrowserContext, Page, async_playwright
except ImportError:
    print("playwright not installed.")
    print("Run: pip install playwright && playwright install chromium")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

ACCOUNTS_DIR = Path.home() / ".clawdbot" / "warmup" / "accounts"

# Niche keywords — any video whose description matches at least one gets engaged
NICHE_KEYWORDS = [
    "ai", "a.i.", "artificial intelligence",
    "midjourney", "stable diffusion", "stablediffusion",
    "chatgpt", "gpt-4", "gpt4", "openai",
    "sora", "runway", "runwayml", "kling",
    "pika", "pikalabs", "luma", "lumalabs",
    "generated", "generative", "ai-generated", "ai generated",
    "machine learning", "neural network", "diffusion model",
    "text to video", "image to video", "txt2vid", "img2vid",
    "creative ai", "ai art", "ai film", "ai video",
    "midj", "sd xl", "sdxl", "flux", "comfyui",
]

TIKTOK_HASHTAGS = [
    "aivideo", "aiart", "artificialintelligence",
    "midjourney", "sora", "runwayml", "kling",
    "aigeneratedart", "creativeai", "generativeai",
    "aifilm", "stableai", "aitools", "aitrends",
]

INSTAGRAM_HASHTAGS = [
    "aivideo", "aiart", "aifilm", "artificialintelligence",
    "midjourney", "stablediffusion", "generativeai",
    "runwayml", "kling", "soraai", "aitools",
    "aianimation", "aigeneratedart", "creativeai",
]

TWITTER_SEARCH_QUERIES = [
    "AI video",
    "Midjourney",
    "Sora AI",
    "Runway ML",
    "generative AI art",
    "AI film",
    "Kling AI",
    "AI generated",
]

PHASE_DURATIONS = {1: 5, 2: 7, 3: 10}

COOKIES_DIR = Path.home() / ".clawdbot" / "cookies"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_state(account_key: str) -> dict | None:
    state_file = ACCOUNTS_DIR / account_key / "state.json"
    if state_file.exists():
        with open(state_file) as f:
            return json.load(f)
    return None


def browser_profile_dir(account_key: str) -> Path:
    return ACCOUNTS_DIR / account_key / "browser_profile"


def load_cookies_for_platform(platform: str) -> list:
    """Load JSON cookies file for a platform and return Playwright-compatible list."""
    cookie_file = COOKIES_DIR / f"{platform}.json"
    if not cookie_file.exists():
        return []
    with open(cookie_file) as f:
        raw = json.load(f)
    result = []
    for c in raw:
        entry = {
            "name": c["name"],
            "value": c["value"],
            "domain": c.get("domain", f".{platform}.com"),
            "path": c.get("path", "/"),
            "httpOnly": c.get("httpOnly", False),
            "secure": c.get("secure", True),
        }
        if "expires" in c and isinstance(c["expires"], (int, float)):
            entry["expires"] = int(c["expires"])
        result.append(entry)
    return result


def get_phase_for_state(state: dict) -> int:
    start = datetime.fromisoformat(state["started_at"]).date()
    day_num = (date.today() - start).days + 1
    if day_num <= 7:
        return 1
    elif day_num <= 14:
        return 2
    return 3


def is_niche(text: str) -> bool:
    """Return True if text contains any niche keyword."""
    text_lower = text.lower()
    return any(kw in text_lower for kw in NICHE_KEYWORDS)


async def jitter(min_ms: int = 600, max_ms: int = 2200):
    """Human-like random pause."""
    await asyncio.sleep(random.uniform(min_ms / 1000, max_ms / 1000))


async def safe_text(page: Page, selector: str) -> str:
    """Get inner text from a selector, return empty string on failure."""
    try:
        el = await page.query_selector(selector)
        if el:
            return (await el.inner_text()).strip()
    except Exception:
        pass
    return ""


async def safe_click(page: Page, selector: str) -> bool:
    """Click a selector, return True on success."""
    try:
        el = await page.query_selector(selector)
        if el:
            await el.click()
            return True
    except Exception:
        pass
    return False


# ---------------------------------------------------------------------------
# TikTok
# ---------------------------------------------------------------------------

async def check_tiktok_login(page: Page) -> bool:
    """Return True if we appear to be logged in (fail-open: only False on explicit login wall)."""
    try:
        await page.goto("https://www.tiktok.com", wait_until="domcontentloaded", timeout=25000)
        await asyncio.sleep(4)
        url = page.url
        # Hard redirect to login page = definitely not logged in
        if "/login" in url or "loginType" in url:
            return False
        # Explicit login modal visible = not logged in
        for sel in ['[data-e2e="login-button"]', 'input[name="username"]', 'form[action*="login"]']:
            el = await page.query_selector(sel)
            if el:
                return False
        # If we can't confirm NOT logged in, assume we are (cookies were injected)
        return True
    except Exception:
        return True  # network error etc — attempt the session anyway


async def get_video_description(page: Page) -> str:
    """Try multiple selectors to get the current video's description."""
    for sel in [
        '[data-e2e="video-desc"]',
        '[data-e2e="browse-video-desc"]',
        'span[data-e2e="video-desc"]',
        'h1[data-e2e="video-desc"]',
        'div[class*="DivVideoInfoContainer"] span',
    ]:
        text = await safe_text(page, sel)
        if text:
            return text
    return ""


async def like_current_video(page: Page) -> bool:
    """Like the current video. Return True if like was clicked."""
    for sel in [
        '[data-e2e="like-icon"]',
        '[data-e2e="browse-like-icon"]',
        'button[aria-label*="like" i]',
        'button[class*="LikeButton"]',
    ]:
        try:
            btn = await page.query_selector(sel)
            if btn:
                # Don't double-like
                pressed = await btn.get_attribute("aria-pressed")
                if pressed == "true":
                    return False  # already liked
                await jitter(400, 1200)
                await btn.click()
                await jitter(300, 700)
                return True
        except Exception:
            continue
    return False



async def run_tiktok_session(page: Page, duration_seconds: int, phase: int) -> dict:
    """
    Main session loop: navigate hashtags, watch, like niche content only.
    Returns stats dict.
    """
    stats = {"watched": 0, "liked": 0, "skipped_off_niche": 0}
    start = time.time()

    hashtags = random.sample(TIKTOK_HASHTAGS, min(4, len(TIKTOK_HASHTAGS)))
    print(f"  Hashtags this session: {', '.join('#' + h for h in hashtags)}", file=sys.stderr)

    for hashtag in hashtags:
        elapsed = time.time() - start
        if elapsed >= duration_seconds:
            break

        remaining = duration_seconds - elapsed
        print(f"\n  → #{hashtag} ({int(remaining)}s remaining)", file=sys.stderr)

        try:
            await page.goto(
                f"https://www.tiktok.com/tag/{hashtag}",
                wait_until="domcontentloaded",
                timeout=25000,
            )
            await jitter(2000, 4000)

            # Extract video URLs via JS eval (atomic — no stale element refs)
            # TikTok hashtag pages use challenge-item containers; links are nested inside
            video_urls = await page.evaluate("""
                () => Array.from(document.querySelectorAll('[data-e2e="challenge-item"] a[href*="/video/"], a[href*="/video/"]'))
                          .map(a => a.href)
                          .filter(h => h && h.includes('/video/'))
                          .filter((v, i, a) => a.indexOf(v) === i)
                          .slice(0, 15)
            """)

            if not video_urls:
                print(f"    No video URLs found for #{hashtag}", file=sys.stderr)
                continue

            print(f"    Found {len(video_urls)} videos", file=sys.stderr)

            # Navigate directly to a video
            click_idx = random.randint(0, min(5, len(video_urls) - 1))
            await page.goto(video_urls[click_idx], wait_until="domcontentloaded", timeout=25000)
            await jitter(2500, 4000)

            # Process up to N videos from this hashtag
            max_videos = random.randint(3, 7)
            for _ in range(max_videos):
                if time.time() - start >= duration_seconds:
                    break

                desc = await get_video_description(page)
                niche = is_niche(desc)

                if niche:
                    watch_sec = random.uniform(10, 22)
                    print(f"    ✓ niche  — watching {watch_sec:.0f}s | {desc[:50] or '(no desc)'}",
                          file=sys.stderr)
                    await asyncio.sleep(watch_sec)
                    stats["watched"] += 1

                    # Like it
                    if await like_current_video(page):
                        stats["liked"] += 1
                        print(f"      ♥ liked", file=sys.stderr)

                else:
                    skip_sec = random.uniform(1.5, 3.5)
                    print(f"    ✗ off-niche — skipping ({skip_sec:.0f}s) | {desc[:50] or '(no desc)'}",
                          file=sys.stderr)
                    await asyncio.sleep(skip_sec)
                    stats["skipped_off_niche"] += 1

                # Advance to next video (down arrow)
                await jitter(500, 1200)
                await page.keyboard.press("ArrowDown")
                await jitter(1000, 2000)

        except Exception as e:
            print(f"    Error on #{hashtag}: {e}", file=sys.stderr)
            continue

    return stats


# ---------------------------------------------------------------------------
# Instagram
# ---------------------------------------------------------------------------

async def check_instagram_login(page: Page) -> bool:
    """Return True if logged in (fail-open)."""
    try:
        await page.goto("https://www.instagram.com/", wait_until="domcontentloaded", timeout=25000)
        await asyncio.sleep(4)
        url = page.url
        if "/accounts/login" in url:
            return False
        login_input = await page.query_selector('input[name="username"]')
        if login_input:
            return False
        return True
    except Exception:
        return True


async def run_instagram_session(page: Page, duration_seconds: int, phase: int) -> dict:
    """Browse Instagram Reels/hashtags and like niche content."""
    stats = {"watched": 0, "liked": 0, "skipped_off_niche": 0}
    start = time.time()

    hashtags = random.sample(INSTAGRAM_HASHTAGS, min(5, len(INSTAGRAM_HASHTAGS)))
    print(f"  Hashtags this session: {', '.join('#' + h for h in hashtags)}", file=sys.stderr)

    # Start with Reels explore for a natural feel
    try:
        await page.goto("https://www.instagram.com/reels/", wait_until="domcontentloaded", timeout=25000)
        await jitter(3000, 5000)
        # Dismiss any dialogs/cookie banners
        for dismiss_sel in ['button[tabindex="0"][class*="HoLwn"]', 'div[role="dialog"] button']:
            try:
                btn = await page.query_selector(dismiss_sel)
                if btn:
                    await btn.click()
                    await jitter(800, 1500)
                    break
            except Exception:
                pass
    except Exception as e:
        print(f"  Reels nav error: {e}", file=sys.stderr)

    for hashtag in hashtags:
        elapsed = time.time() - start
        if elapsed >= duration_seconds:
            break

        remaining = duration_seconds - elapsed
        print(f"\n  → #{hashtag} ({int(remaining)}s remaining)", file=sys.stderr)

        try:
            await page.goto(
                f"https://www.instagram.com/explore/tags/{hashtag}/",
                wait_until="domcontentloaded",
                timeout=25000,
            )
            await jitter(2500, 4500)

            # Click first post to open
            post_links = await page.query_selector_all('a[href*="/p/"]')
            if not post_links:
                print(f"    No posts found for #{hashtag}", file=sys.stderr)
                continue

            click_idx = random.randint(0, min(8, len(post_links) - 1))
            await post_links[click_idx].click()
            await jitter(2000, 3500)

            # Browse several posts
            max_posts = random.randint(3, 6)
            for _ in range(max_posts):
                if time.time() - start >= duration_seconds:
                    break

                # Get post description
                desc = ""
                for desc_sel in [
                    'h1._aacl',
                    'div._a9zs span',
                    'div[class*="Caption"] span',
                    'span[class*="Caption"]',
                ]:
                    text = await safe_text(page, desc_sel)
                    if text:
                        desc = text
                        break

                niche = is_niche(desc)

                if niche:
                    watch_sec = random.uniform(8, 18)
                    print(f"    ✓ niche  — watching {watch_sec:.0f}s | {desc[:50] or '(no desc)'}",
                          file=sys.stderr)
                    await asyncio.sleep(watch_sec)
                    stats["watched"] += 1

                    # Like — try heart button
                    liked = False
                    for like_sel in [
                        'svg[aria-label="Like"]',
                        'button[type="button"] svg[aria-label="Like"]',
                        'span[aria-label="Like"]',
                    ]:
                        try:
                            btn = await page.query_selector(like_sel)
                            if btn:
                                # Check not already liked
                                parent = await page.query_selector('button[type="button"]:has(svg[aria-label="Like"])')
                                if parent:
                                    await jitter(500, 1200)
                                    await parent.click()
                                    liked = True
                                    stats["liked"] += 1
                                    print(f"      ♥ liked", file=sys.stderr)
                                    await jitter(500, 900)
                                break
                        except Exception:
                            continue
                else:
                    skip_sec = random.uniform(1.5, 3.5)
                    print(f"    ✗ off-niche — skipping | {desc[:50] or '(no desc)'}",
                          file=sys.stderr)
                    await asyncio.sleep(skip_sec)
                    stats["skipped_off_niche"] += 1

                # Next post (right arrow)
                await jitter(600, 1400)
                await page.keyboard.press("ArrowRight")
                await jitter(1200, 2500)

        except Exception as e:
            print(f"    Error on #{hashtag}: {e}", file=sys.stderr)
            continue

    return stats


# ---------------------------------------------------------------------------
# Twitter / X
# ---------------------------------------------------------------------------

async def check_twitter_login(page: Page) -> bool:
    """Return True if logged in (fail-open)."""
    try:
        await page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=25000)
        await asyncio.sleep(4)
        url = page.url
        if "login" in url or "i/flow" in url:
            return False
        return True
    except Exception:
        return True


async def run_twitter_session(page: Page, duration_seconds: int, phase: int) -> dict:
    """Browse Twitter/X For You feed and like niche tweets."""
    stats = {"watched": 0, "liked": 0, "skipped_off_niche": 0}
    start = time.time()

    print(f"  Starting Twitter/X session — {duration_seconds}s", file=sys.stderr)

    # Already on home feed from check_twitter_login — wait for tweets to actually render
    try:
        # Scroll slightly to trigger lazy-load, then wait
        await page.evaluate("window.scrollBy(0, 200)")
        await asyncio.sleep(2)
        await page.wait_for_selector('[data-testid="tweet"]', timeout=45000)
        await jitter(2000, 4000)
        print(f"  Feed loaded — starting scroll", file=sys.stderr)
    except Exception as e:
        # Take debug screenshot to see what's on screen
        try:
            await page.screenshot(path="/tmp/twitter_warmup_debug.png")
            print(f"  Debug screenshot: /tmp/twitter_warmup_debug.png", file=sys.stderr)
        except Exception:
            pass
        print(f"  Feed didn't load tweets ({e}) — aborting session", file=sys.stderr)
        return stats

    # Browse home feed for a bit
    feed_end = start + duration_seconds * 0.4  # 40% of time on home feed
    scroll_count = 0
    while time.time() < feed_end:
        if page.is_closed():
            break
        tweets = await page.query_selector_all('[data-testid="tweet"]')
        for tweet in tweets:
            if time.time() >= feed_end:
                break
            try:
                # Get tweet text
                text_el = await tweet.query_selector('[data-testid="tweetText"]')
                desc = (await text_el.inner_text()).strip() if text_el else ""
                niche = is_niche(desc)

                if niche:
                    watch_sec = random.uniform(4, 10)
                    print(f"    ✓ niche  — reading {watch_sec:.0f}s | {desc[:60] or '(no text)'}",
                          file=sys.stderr)
                    # Scroll tweet into view + pause
                    await tweet.scroll_into_view_if_needed()
                    await asyncio.sleep(watch_sec)
                    stats["watched"] += 1

                    # Like it
                    like_btn = await tweet.query_selector('[data-testid="like"]')
                    if like_btn:
                        await jitter(400, 1000)
                        await like_btn.click()
                        stats["liked"] += 1
                        print(f"      ♥ liked", file=sys.stderr)
                        await jitter(500, 1200)
                else:
                    skip_sec = random.uniform(0.8, 2.5)
                    print(f"    ✗ skip  — {desc[:50] or '(no text)'}", file=sys.stderr)
                    await tweet.scroll_into_view_if_needed()
                    await asyncio.sleep(skip_sec)
                    stats["skipped_off_niche"] += 1
            except Exception:
                continue

        # Scroll down
        if page.is_closed():
            break
        await page.keyboard.press("End")
        await jitter(1500, 3000)
        scroll_count += 1
        if scroll_count > 20:
            break

    # Then search niche topics
    queries = random.sample(TWITTER_SEARCH_QUERIES, min(3, len(TWITTER_SEARCH_QUERIES)))
    for query in queries:
        elapsed = time.time() - start
        if elapsed >= duration_seconds or page.is_closed():
            break

        remaining = duration_seconds - elapsed
        print(f"\n  → Search: \"{query}\" ({int(remaining)}s remaining)", file=sys.stderr)

        try:
            search_url = f"https://x.com/search?q={query.replace(' ', '%20')}&f=live"
            await page.goto(search_url, wait_until="domcontentloaded", timeout=25000)
            await jitter(2500, 4000)

            max_tweets = random.randint(4, 8)
            processed = 0
            scroll_attempts = 0

            while processed < max_tweets and time.time() - start < duration_seconds:
                tweets = await page.query_selector_all('[data-testid="tweet"]')
                for tweet in tweets[processed:]:
                    if processed >= max_tweets or time.time() - start >= duration_seconds:
                        break
                    try:
                        text_el = await tweet.query_selector('[data-testid="tweetText"]')
                        desc = (await text_el.inner_text()).strip() if text_el else ""
                        niche = is_niche(desc) or True  # search results are pre-filtered, engage more

                        if niche:
                            watch_sec = random.uniform(5, 12)
                            await tweet.scroll_into_view_if_needed()
                            await asyncio.sleep(watch_sec)
                            stats["watched"] += 1
                            print(f"    ✓ reading {watch_sec:.0f}s | {desc[:60] or '(no text)'}",
                                  file=sys.stderr)

                            # Like
                            like_btn = await tweet.query_selector('[data-testid="like"]')
                            if like_btn:
                                await jitter(400, 900)
                                await like_btn.click()
                                stats["liked"] += 1
                                print(f"      ♥ liked", file=sys.stderr)
                                await jitter(600, 1400)

                                # Occasionally bookmark (Phase 2+)
                                if phase >= 2 and random.random() < 0.25:
                                    bm_btn = await tweet.query_selector('[data-testid="bookmark"]')
                                    if bm_btn:
                                        await jitter(300, 700)
                                        await bm_btn.click()
                                        print(f"      🔖 bookmarked", file=sys.stderr)
                                        await jitter(400, 800)
                        else:
                            skip_sec = random.uniform(1, 3)
                            await tweet.scroll_into_view_if_needed()
                            await asyncio.sleep(skip_sec)
                            stats["skipped_off_niche"] += 1

                        processed += 1
                    except Exception:
                        processed += 1
                        continue

                # Scroll for more tweets
                await page.keyboard.press("End")
                await jitter(1500, 2500)
                scroll_attempts += 1
                if scroll_attempts > 5:
                    break

        except Exception as e:
            print(f"    Error searching '{query}': {e}", file=sys.stderr)
            continue

    return stats


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main_async(account_key: str, platform: str, duration_min: int, phase: int):
    profile_dir = browser_profile_dir(account_key)
    profile_dir.mkdir(parents=True, exist_ok=True)

    # Platform-specific viewport / UA
    if platform == "tiktok":
        viewport = {"width": 1280, "height": 900}
        user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    else:
        viewport = {"width": 1280, "height": 900}
        user_agent = (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        )

    # Twitter needs more JS heap (heavy SPA) — only cap for TikTok/IG
    chrome_args = [
        "--disable-blink-features=AutomationControlled",
        "--no-first-run",
        "--disable-infobars",
        "--disable-dev-shm-usage",        # use /tmp instead of /dev/shm (low RAM VPS)
        "--disable-gpu",
        "--no-sandbox",
        "--disable-extensions",
    ]
    if platform == "instagram":
        chrome_args.append("--js-flags=--max-old-space-size=256")  # cap JS heap at 256MB (IG is lighter)
    elif platform == "tiktok":
        chrome_args.append("--js-flags=--max-old-space-size=512")  # TikTok needs more headroom

    async with async_playwright() as pw:
        context: BrowserContext = await pw.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=True,
            viewport=viewport,
            user_agent=user_agent,
            args=chrome_args,
            ignore_default_args=["--enable-automation"],
        )

        page = context.pages[0] if context.pages else await context.new_page()

        # Inject cookies from file if available
        if platform in ("instagram", "twitter", "tiktok"):
            cookies = load_cookies_for_platform(platform)
            if cookies:
                await context.add_cookies(cookies)
                print(f"  Injected {len(cookies)} cookies for {platform}", file=sys.stderr)

        if platform == "tiktok":
            logged_in = await check_tiktok_login(page)
            if not logged_in:
                print("\n⚠ Not logged into TikTok — cookies stale or not loaded.", file=sys.stderr)
                await context.close()
                sys.exit(1)
            print(f"\n[warmup] TikTok session — Phase {phase} — {duration_min} min", file=sys.stderr)
            stats = await run_tiktok_session(page, duration_min * 60, phase)

        elif platform == "instagram":
            logged_in = await check_instagram_login(page)
            if not logged_in:
                print("\n⚠ Not logged into Instagram — cookies may be stale.", file=sys.stderr)
                await context.close()
                sys.exit(1)
            print(f"\n[warmup] Instagram session — Phase {phase} — {duration_min} min", file=sys.stderr)
            stats = await run_instagram_session(page, duration_min * 60, phase)

        elif platform == "twitter":
            logged_in = await check_twitter_login(page)
            if not logged_in:
                print("\n⚠ Not logged into Twitter/X — cookies may be stale.", file=sys.stderr)
                await context.close()
                sys.exit(1)
            print(f"\n[warmup] Twitter/X session — Phase {phase} — {duration_min} min", file=sys.stderr)
            stats = await run_twitter_session(page, duration_min * 60, phase)

        else:
            print(f"Platform '{platform}' not supported. Use tiktok/instagram/twitter.")
            await context.close()
            return

        await context.close()

    print(f"\n{'='*45}")
    print(f"  Session complete — {duration_min} min")
    print(f"  Watched/Read:     {stats['watched']}")
    print(f"  Liked (niche):    {stats['liked']}")
    print(f"  Skipped off-niche:{stats['skipped_off_niche']}")
    print(f"{'='*45}")
    print(f"\nRun: python3 warmup.py done   ← to log this session")


def main():
    parser = argparse.ArgumentParser(description="Run a warmup engagement session")
    parser.add_argument("--account", required=True, help="Account key (platform_username)")
    parser.add_argument("--platform", default=None, help="Platform override (tiktok)")
    parser.add_argument("--duration", type=int, default=None, help="Duration in minutes")
    parser.add_argument("--phase", type=int, default=None, choices=[1, 2, 3],
                        help="Phase override (1/2/3)")
    args = parser.parse_args()

    state = load_state(args.account)
    if not state:
        print(f"Account '{args.account}' not found. Run: python3 warmup.py init")
        sys.exit(1)

    platform = args.platform or state.get("platform", "tiktok")
    phase = args.phase or get_phase_for_state(state)
    duration = args.duration or PHASE_DURATIONS.get(phase, 7)

    print(f"[warmup] @{state['username']} ({platform}) — Phase {phase} — {duration} min")
    asyncio.run(main_async(args.account, platform, duration, phase))


if __name__ == "__main__":
    main()
