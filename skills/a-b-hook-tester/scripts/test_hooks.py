#!/usr/bin/env python3
"""A/B Hook Tester — generate 3 hook variants via Claude, log with IDs, mark winners.

Usage:
  python3 test_hooks.py "topic"
  python3 test_hooks.py "topic" --vibe "deadpan Gen-Z barber"
  python3 test_hooks.py --log
  python3 test_hooks.py --winner abc123 --hook 2
"""

import argparse
import json
import os
import re
import sys
import uuid
from datetime import date
from pathlib import Path

import anthropic


# ---------------------------------------------------------------------------
# Hook style definitions (sourced from viral-hooks-reference.md)
# ---------------------------------------------------------------------------

HOOK_STYLES = {
    "pure-visual": {
        "name": "Pure Visual / No Narration",
        "description": "Let the visual speak. No text, no narration. Works for highly visual or meme content.",
        "examples": ["There is no text in the image", "Silent reaction shots", "Time-lapse reveals"],
        "avg_views": "68M-82M",
    },
    "unhinged": {
        "name": "Unhinged Brand Voice",
        "description": "Absurdist, threatening, or meme-native. Speaks like the internet, not a brand.",
        "examples": ["when you ignore my notifications", "end your streak and i'll end you", "Gegagedigedagedago"],
        "avg_views": "25M-68M",
    },
    "interactive": {
        "name": "Interactive Challenge",
        "description": "Forces participation — questions, tests, or challenges that explode comments.",
        "examples": ["Inhale lung test", "How many slices?", "How many cuts?"],
        "avg_views": "10M-36M",
    },
    "provocative": {
        "name": "Provocative / Incomplete Question",
        "description": "An incomplete thought or question that demands the viewer watch to resolution.",
        "examples": ["Guess who's not Korean?", "or extinct", "is educational?"],
        "avg_views": "8M-25M",
    },
    "relatable-absurdism": {
        "name": "Relatable Absurdism",
        "description": "Normal setup followed by an unexpected weird twist.",
        "examples": ["just ate my oreos. think I'll save the other half for later.", "yo check out my new calculator"],
        "avg_views": "5M-20M",
    },
    "trend-hijack": {
        "name": "Trend Hijack",
        "description": "Riding a current audio or meme trend with a brand/niche spin. Requires speed.",
        "examples": ["Pure audio trend surfing with brand spin"],
        "avg_views": "10M-30M",
    },
    "confession": {
        "name": "Confession / Overshare",
        "description": "TMI energy. Oversharing creates instant relatability.",
        "examples": ["I clogged the toilet on the 3rd floor", "I spent $400 on ___"],
        "avg_views": "5M-10M",
    },
}


# ---------------------------------------------------------------------------
# Utilities
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
                if line.startswith(f"{key}="):
                    return line.split("=", 1)[1].strip()
    return None


def get_storage_path() -> Path:
    storage_dir = Path.home() / ".clawdbot" / "hook-tests"
    storage_dir.mkdir(parents=True, exist_ok=True)
    return storage_dir / "tests.json"


def load_tests() -> list:
    path = get_storage_path()
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return []


def save_tests(tests: list):
    path = get_storage_path()
    with open(path, "w") as f:
        json.dump(tests, f, indent=2)


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------

def generate_hooks(topic: str, vibe: str | None) -> list[dict]:
    """Generate 3 hook variants via Claude. Returns list of hook dicts."""
    api_key = _load_env("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not found in environment or ~/.clawdbot/.env")

    client = anthropic.Anthropic(api_key=api_key)

    style_descriptions = "\n".join(
        f"- {k}: {v['description']} (avg {v['avg_views']} views)"
        for k, v in HOOK_STYLES.items()
    )

    vibe_line = f"\nAccount vibe / voice: {vibe}" if vibe else ""

    system = f"""You are a viral content strategist who writes TikTok/Instagram hooks.

Available hook styles:
{style_descriptions}

Return ONLY a raw JSON array with exactly 3 elements. No markdown, no backticks, no explanation.
Each element must have these fields:
  "index": 1, 2, or 3
  "style": one of the style keys listed above (e.g. "unhinged")
  "text": the hook text (15 words or fewer, punchy, scroll-stopping)
  "rationale": 1-2 sentences explaining why this will perform

Pick 3 different styles that would each work well for the topic."""

    user_msg = f"Topic: {topic}{vibe_line}\n\nGenerate 3 hook variants."

    print(f"[hook-tester] Generating hooks for: {topic!r}", file=sys.stderr)
    if vibe:
        print(f"  Vibe: {vibe}", file=sys.stderr)

    with client.messages.stream(
        model="claude-haiku-4-5-20251001",
        max_tokens=600,
        system=system,
        messages=[{"role": "user", "content": user_msg}],
    ) as stream:
        result = stream.get_final_message()

    raw = "\n".join(block.text for block in result.content if block.type == "text").strip()

    # Parse JSON — with regex fallback for rare markdown wrapping
    try:
        hooks = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\[.*\]", raw, re.DOTALL)
        if not match:
            raise RuntimeError(f"Claude returned non-JSON response:\n{raw[:500]}")
        hooks = json.loads(match.group(0))

    return hooks


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

def print_hooks(test: dict):
    winner = test.get("winner")
    print(f"\n=== HOOK TEST: {test['id']} ===")
    print(f"Topic: {test['topic']}")
    if test.get("vibe"):
        print(f"Vibe: {test['vibe']}")
    print(f"Generated: {test['generated']}")
    if winner is not None:
        print(f"Winner: Hook {winner} *")
    print()

    for hook in test.get("hooks", []):
        idx = hook.get("index", "?")
        style = hook.get("style", "").upper()
        text = hook.get("text", "")
        rationale = hook.get("rationale", "")
        marker = " *" if winner is not None and str(idx) == str(winner) else ""
        print(f"[{idx}] {style}{marker}")
        print(f'"{text}"')
        print(f"Why: {rationale}")
        print()


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_generate(topic: str, vibe: str | None):
    hooks = generate_hooks(topic, vibe)

    test_id = uuid.uuid4().hex[:6]
    test = {
        "id": test_id,
        "topic": topic,
        "vibe": vibe,
        "generated": date.today().isoformat(),
        "hooks": hooks,
        "winner": None,
    }

    tests = load_tests()
    tests.append(test)
    save_tests(tests)

    print_hooks(test)
    print(f"Run with: --winner {test_id} --hook N")


def cmd_log():
    tests = load_tests()
    if not tests:
        print("No hook tests yet. Run: test_hooks.py \"your topic\"")
        return

    for test in reversed(tests):
        print_hooks(test)


def cmd_winner(test_id: str, hook_index: int):
    tests = load_tests()
    for test in tests:
        if test["id"] == test_id:
            test["winner"] = hook_index
            save_tests(tests)
            print(f"[hook-tester] Marked hook {hook_index} as winner for test {test_id}", file=sys.stderr)
            print_hooks(test)
            return

    print(f"Error: test ID '{test_id}' not found", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Generate and track A/B hook variants for viral content",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 test_hooks.py "barbershop meme with Kendrick Lamar"
  python3 test_hooks.py "morning routine" --vibe "deadpan Gen-Z barber"
  python3 test_hooks.py --log
  python3 test_hooks.py --winner abc123 --hook 2
""",
    )
    parser.add_argument(
        "topic",
        nargs="?",
        help="What the video is about",
    )
    parser.add_argument(
        "--vibe",
        type=str,
        default=None,
        help="Account personality or voice (e.g. 'deadpan Gen-Z barber')",
    )
    parser.add_argument(
        "--log",
        action="store_true",
        help="List all hook tests (newest first)",
    )
    parser.add_argument(
        "--winner",
        type=str,
        default=None,
        metavar="TEST_ID",
        help="Mark the winning hook for a test (requires --hook)",
    )
    parser.add_argument(
        "--hook",
        type=int,
        choices=[1, 2, 3],
        default=None,
        help="Which hook won: 1, 2, or 3",
    )

    args = parser.parse_args()

    if args.log:
        cmd_log()
        return

    if args.winner is not None:
        if args.hook is None:
            parser.error("--winner requires --hook N (which hook won: 1, 2, or 3)")
        cmd_winner(args.winner, args.hook)
        return

    if not args.topic:
        parser.error("topic is required (or use --log / --winner)")

    try:
        cmd_generate(args.topic, args.vibe)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
