#!/usr/bin/env python3
"""Comment Responder — auto-reply to TikTok comments using Claude.

Visits your recent posts, finds unreplied comments, generates authentic
replies via Claude, and posts them. Shares account storage and browser
profiles with warmup-trainer — no separate account init needed.

Requirements:
  pip install playwright anthropic
  playwright install chromium

Usage:
  python3 comment_responder.py --account tiktok_username
  python3 comment_responder.py --account tiktok_username --dry-run
  python3 comment_responder.py --account tiktok_username --max-replies 5
  python3 comment_responder.py --account tiktok_username --videos 10
"""

import argparse
import asyncio
import json
import os
import random
import sys
import time
import urllib.error
import urllib.request
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

# Shared with warmup-trainer
ACCOUNTS_DIR = Path.home() / ".clawdbot" / "warmup" / "accounts"

REPLIED_FILE = "comments_replied.json"

# Session safety limits
DEFAULT_MAX_REPLIES = 10
DEFAULT_VIDEOS = 5
MIN_DELAY_S = 5
MAX_DELAY_S = 15

REPLY_SYSTEM_PROMPT = """\
You are a TikTok content creator in the AI video / creative AI niche.
You respond to comments on your videos in an authentic, engaging way.

Rules:
- Keep replies SHORT — 1 to 8 words ideally, 2 sentences max
- Sound human and genuine, match the energy of the comment
- If it's a question, answer briefly or tease them to watch more
- If it's a compliment, thank them warmly and naturally
- If it's skeptical, be confident but not defensive
- Occasionally ask a follow-up question to drive more engagement
- Never use hashtags in replies
- Never sound corporate, robotic, or like a bot
- Do not start every reply the same way — vary your openings
- Output ONLY the reply text, nothing else"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_env(key: str) -> str | None:
    val = os.environ.get(key)
    if val:
        return val
    env_path = Path.home() / ".clawdbot" / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith(f"{key}="):
                return line.split("=", 1)[1].strip()
    return None


def load_state(account_key: str) -> dict | None:
    state_file = ACCOUNTS_DIR / account_key / "state.json"
    if state_file.exists():
        return json.loads(state_file.read_text())
    return None


def browser_profile_dir(account_key: str) -> Path:
    return ACCOUNTS_DIR / account_key / "browser_profile"


def load_replied(account_key: str) -> set:
    f = ACCOUNTS_DIR / account_key / REPLIED_FILE
    if f.exists():
        return set(json.loads(f.read_text()))
    return set()


def save_replied(account_key: str, replied: set):
    f = ACCOUNTS_DIR / account_key / REPLIED_FILE
    f.write_text(json.dumps(sorted(replied), indent=2))


async def jitter(min_s: float = MIN_DELAY_S, max_s: float = MAX_DELAY_S):
    await asyncio.sleep(random.uniform(min_s, max_s))


async def safe_text(page: Page, selector: str) -> str:
    try:
        el = await page.query_selector(selector)
        if el:
            return (await el.inner_text()).strip()
    except Exception:
        pass
    return ""


# ---------------------------------------------------------------------------
# Claude reply generation
# ---------------------------------------------------------------------------

def generate_reply(comment_text: str, video_desc: str, api_key: str) -> str:
    """Call Claude to generate a reply for a comment."""
    user_msg = f'My video: "{video_desc[:120] or "(no description)"}"\nComment: "{comment_text}"\n\nWrite a reply.'

    payload = json.dumps({
        "model": "claude-opus-4-6",
        "max_tokens": 100,
        "system": REPLY_SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": user_msg}],
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
            data = json.loads(resp.read().decode())
            return data["content"][0]["text"].strip()
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Claude API error {e.code}: {e.read().decode()}")


# ---------------------------------------------------------------------------
# TikTok interaction
# ---------------------------------------------------------------------------

async def get_recent_video_urls(page: Page, username: str, count: int) -> list[str]:
    """Visit profile and collect URLs of recent videos."""
    print(f"  Visiting @{username}'s profile...", file=sys.stderr)
    await page.goto(
        f"https://www.tiktok.com/@{username}",
        wait_until="domcontentloaded",
        timeout=25000,
    )
    await asyncio.sleep(3)

    urls = []
    for sel in [
        'a[href*="/video/"]',
        '[data-e2e="user-post-item"] a',
        'div[class*="DivItemContainer"] a',
    ]:
        elements = await page.query_selector_all(sel)
        for el in elements:
            href = await el.get_attribute("href")
            if href and "/video/" in href:
                full = href if href.startswith("http") else f"https://www.tiktok.com{href}"
                if full not in urls:
                    urls.append(full)
        if urls:
            break

    print(f"  Found {len(urls)} videos on profile", file=sys.stderr)
    return urls[:count]


async def get_video_description(page: Page) -> str:
    for sel in [
        '[data-e2e="video-desc"]',
        '[data-e2e="browse-video-desc"]',
        'h1[data-e2e="video-desc"]',
        'span[data-e2e="video-desc"]',
    ]:
        text = await safe_text(page, sel)
        if text:
            return text
    return ""


async def scrape_comments(page: Page, username: str) -> list[dict]:
    """Return list of {id, author, text} for top-level comments."""
    comments = []

    # Scroll comments a couple of times to load more
    for _ in range(2):
        await page.keyboard.press("End")
        await asyncio.sleep(1.5)

    # Try multiple selectors for comment items
    items = []
    for sel in [
        '[data-e2e="comment-item"]',
        'div[class*="DivCommentItemContainer"]',
        '[class*="CommentListItem"]',
    ]:
        items = await page.query_selector_all(sel)
        if items:
            break

    for item in items:
        try:
            # Comment text
            text = ""
            for sel in ['[data-e2e="comment-content"]', 'p[data-e2e="comment-text"]', 'span[class*="SpanCommentText"]']:
                try:
                    el = await item.query_selector(sel)
                    if el:
                        text = (await el.inner_text()).strip()
                        break
                except Exception:
                    continue

            if not text:
                continue

            # Author
            author = ""
            for sel in ['[data-e2e="comment-username"]', 'a[class*="UserAvatar"]', 'span[class*="UniqueId"]']:
                try:
                    el = await item.query_selector(sel)
                    if el:
                        author = (await el.inner_text()).strip().lstrip("@")
                        break
                except Exception:
                    continue

            # Skip our own comments
            if author.lower() == username.lower():
                continue

            # Use text hash as stable ID (TikTok comment IDs aren't easily accessible)
            comment_id = f"{author}:{hash(text) & 0xFFFFFFFF:08x}"

            comments.append({"id": comment_id, "author": author, "text": text, "element": item})

        except Exception:
            continue

    return comments


async def post_reply(page: Page, comment_item, reply_text: str) -> bool:
    """Click Reply on a comment, type the reply, and submit."""
    try:
        # Find and click the Reply button within this comment
        reply_btn = None
        for sel in [
            '[data-e2e="comment-reply-btn"]',
            'button[aria-label*="Reply" i]',
            'span[class*="SpanReplyActionText"]',
            'button[class*="ReplyButton"]',
        ]:
            try:
                reply_btn = await comment_item.query_selector(sel)
                if reply_btn:
                    break
            except Exception:
                continue

        if not reply_btn:
            print("    Could not find Reply button", file=sys.stderr)
            return False

        await reply_btn.click()
        await asyncio.sleep(1.5)

        # Find the reply input box
        input_box = None
        for sel in [
            '[data-e2e="comment-input"]',
            'div[contenteditable="true"]',
            'textarea[placeholder*="Reply" i]',
        ]:
            try:
                input_box = await page.query_selector(sel)
                if input_box:
                    break
            except Exception:
                continue

        if not input_box:
            print("    Could not find comment input", file=sys.stderr)
            return False

        await input_box.click()
        await asyncio.sleep(0.5)

        # Type reply with slight human delay
        await page.keyboard.type(reply_text, delay=random.randint(30, 80))
        await asyncio.sleep(random.uniform(0.5, 1.5))

        # Submit — try Enter first, then Post button
        await page.keyboard.press("Enter")
        await asyncio.sleep(2)

        return True

    except Exception as e:
        print(f"    Error posting reply: {e}", file=sys.stderr)
        return False


# ---------------------------------------------------------------------------
# Main session
# ---------------------------------------------------------------------------

async def run_session(
    account_key: str,
    username: str,
    platform: str,
    api_key: str,
    max_replies: int,
    video_count: int,
    dry_run: bool,
) -> dict:
    stats = {"videos_checked": 0, "comments_seen": 0, "replies_posted": 0, "errors": 0}

    replied = load_replied(account_key)
    profile_dir = browser_profile_dir(account_key)
    profile_dir.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as pw:
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

        # Check login
        await page.goto("https://www.tiktok.com", wait_until="domcontentloaded", timeout=20000)
        await asyncio.sleep(2)
        login_modal = await page.query_selector('[data-e2e="login-button"]')
        if login_modal:
            print("\n⚠ Not logged into TikTok.")
            print("  Log in manually in the browser window, then press Enter.")
            input("  Press Enter once logged in: ")

        video_urls = await get_recent_video_urls(page, username, video_count)
        if not video_urls:
            print("  No videos found on profile.", file=sys.stderr)
            await context.close()
            return stats

        for video_url in video_urls:
            if stats["replies_posted"] >= max_replies:
                break

            print(f"\n  → {video_url}", file=sys.stderr)
            try:
                await page.goto(video_url, wait_until="domcontentloaded", timeout=25000)
                await asyncio.sleep(3)
            except Exception as e:
                print(f"    Navigation error: {e}", file=sys.stderr)
                stats["errors"] += 1
                continue

            video_desc = await get_video_description(page)
            stats["videos_checked"] += 1

            comments = await scrape_comments(page, username)
            print(f"    {len(comments)} comments found", file=sys.stderr)
            stats["comments_seen"] += len(comments)

            for comment in comments:
                if stats["replies_posted"] >= max_replies:
                    break

                cid = comment["id"]
                if cid in replied:
                    continue

                print(f"    💬 @{comment['author']}: {comment['text'][:60]}", file=sys.stderr)

                try:
                    reply = generate_reply(comment["text"], video_desc, api_key)
                    print(f"       → {reply}", file=sys.stderr)
                except Exception as e:
                    print(f"       Claude error: {e}", file=sys.stderr)
                    stats["errors"] += 1
                    continue

                if dry_run:
                    print("       [dry-run — not posting]", file=sys.stderr)
                    replied.add(cid)
                    stats["replies_posted"] += 1
                    continue

                await jitter(MIN_DELAY_S, MAX_DELAY_S)
                success = await post_reply(page, comment["element"], reply)
                if success:
                    replied.add(cid)
                    stats["replies_posted"] += 1
                    print("       ✓ posted", file=sys.stderr)
                    save_replied(account_key, replied)
                else:
                    stats["errors"] += 1

        await context.close()

    if not dry_run:
        save_replied(account_key, replied)

    return stats


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Auto-reply to TikTok comments using Claude")
    parser.add_argument("--account", required=True, help="Account key (platform_username)")
    parser.add_argument("--max-replies", type=int, default=DEFAULT_MAX_REPLIES,
                        help=f"Max replies per session (default: {DEFAULT_MAX_REPLIES})")
    parser.add_argument("--videos", type=int, default=DEFAULT_VIDEOS,
                        help=f"Recent videos to check (default: {DEFAULT_VIDEOS})")
    parser.add_argument("--dry-run", action="store_true",
                        help="Generate replies but don't post them")
    args = parser.parse_args()

    state = load_state(args.account)
    if not state:
        print(f"Account '{args.account}' not found.")
        print("Run: python3 skills/warmup-trainer/scripts/warmup.py init")
        sys.exit(1)

    api_key = _load_env("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY not found in environment or ~/.clawdbot/.env")
        sys.exit(1)

    username = state["username"]
    platform = state.get("platform", "tiktok")

    mode = "[DRY RUN] " if args.dry_run else ""
    print(f"[comment-responder] {mode}@{username} ({platform})")
    print(f"  Checking {args.videos} videos, up to {args.max_replies} replies")

    stats = asyncio.run(run_session(
        account_key=args.account,
        username=username,
        platform=platform,
        api_key=api_key,
        max_replies=args.max_replies,
        video_count=args.videos,
        dry_run=args.dry_run,
    ))

    print(f"\n{'='*45}")
    print(f"  Videos checked:  {stats['videos_checked']}")
    print(f"  Comments seen:   {stats['comments_seen']}")
    print(f"  Replies posted:  {stats['replies_posted']}")
    if stats["errors"]:
        print(f"  Errors:          {stats['errors']}")
    print(f"{'='*45}")


if __name__ == "__main__":
    main()
