#!/usr/bin/env python3
"""Script Writer — generate timed short-form video scripts via Claude.

Usage:
    python3 write.py "this AI tool replaces your marketing team"
    python3 write.py "morning routine hack" --duration 15 --format storytime
    python3 write.py "why your reels flop" --duration 60 --format problem-solution --vibe informative
    python3 write.py "coffee shop productivity" --variants 2 --json
"""

import argparse
import json
import os
import sys
from pathlib import Path

import anthropic


# ---------------------------------------------------------------------------
# Formats
# ---------------------------------------------------------------------------

FORMATS = {
    "storytime": {
        "name": "Storytime",
        "description": "First person narrative with a twist or payoff",
        "structure": "Hook (personal moment) → Build tension → Twist/reveal → CTA",
        "tips": "Start mid-action. Use 'So I was...' or 'Nobody told me...'. The twist makes or breaks it.",
    },
    "listicle": {
        "name": "Listicle",
        "description": "Numbered tips/items delivered rapid-fire",
        "structure": "Hook (promise the list) → Item 1 → Item 2 → Item 3+ → Best one last → CTA",
        "tips": "Each item gets 3-5 seconds. Visual change on every item. Save the best for last. Use on-screen numbers.",
    },
    "pov": {
        "name": "POV",
        "description": "POV: [scenario] — visual storytelling, minimal narration",
        "structure": "POV text on screen → Act out the scenario → Punchline/twist → Reaction",
        "tips": "Narration is optional — let the visual tell the story. Exaggerated expressions. Text overlay carries the context.",
    },
    "problem-solution": {
        "name": "Problem → Solution",
        "description": "Identify a pain point, agitate it, then reveal the solution",
        "structure": "Hook (the problem) → Agitate (why it sucks) → Solution reveal → Demo/proof → CTA",
        "tips": "Spend 40% on the problem. The viewer needs to FEEL the pain before you offer the fix. Show, don't tell.",
    },
    "before-after": {
        "name": "Before / After",
        "description": "Dramatic transformation with a reveal moment",
        "structure": "Hook (tease the result) → Show the 'before' → Transition effect → Reveal 'after' → CTA",
        "tips": "The transition is everything. Use a hand swipe, snap, or dramatic cut. Make the contrast extreme.",
    },
    "hot-take": {
        "name": "Hot Take",
        "description": "Bold controversial claim backed with evidence",
        "structure": "Hook (the hot take) → Why most people are wrong → Your evidence → Mic drop → CTA",
        "tips": "The claim must be genuinely surprising. Don't be contrarian for the sake of it. End with confidence.",
    },
    "tutorial": {
        "name": "Tutorial",
        "description": "Step-by-step walkthrough of how to do something",
        "structure": "Hook (what they'll learn) → Step 1 → Step 2 → Step 3 → Result → CTA",
        "tips": "Keep steps to 3-5. Show your screen or hands. Each step gets its own text overlay. Speed up boring parts.",
    },
    "auto": {
        "name": "Auto (AI picks)",
        "description": "Claude picks the best format for the topic",
        "structure": "",
        "tips": "",
    },
}

VIBES = {
    "funny": "Comedic, self-aware, meme energy. Lean into absurdity. Timing is everything.",
    "mindblowing": "Awe-inspiring, 'wait WHAT' energy. Build to a reveal that makes people replay.",
    "relatable": "Everyday struggle, everyone-feels-this. POV format works well. Nod-along content.",
    "inspiring": "Motivational, aspirational. Short punchy lines. No toxic positivity — keep it real.",
    "informative": "Educational, value-forward. Hook with the insight, not the topic. Teach something specific.",
    "mysterious": "Cryptic, makes people need to watch. Incomplete thoughts, unanswered questions.",
    "hype": "Energetic, exclamatory. Build excitement. Fast cuts, trending energy.",
    "deadpan": "Dry, understated, ironic. Say wild things like they're obvious. Anti-energy energy.",
    "urgent": "Time-sensitive, FOMO-inducing. 'You need to know this NOW' energy.",
    "confident": "Authority, expertise, no-nonsense. Speak like someone who's done this 1000 times.",
}

DURATION_SCENES = {
    15: {"scenes": 3, "hook_seconds": 2, "description": "Ultra-tight. Every word counts. 3 scenes max."},
    30: {"scenes": 4, "hook_seconds": 3, "description": "Standard Reel. 4 scenes. Hook must land in first 3 seconds."},
    45: {"scenes": 5, "hook_seconds": 3, "description": "Extended. 5 scenes. More room for story but keep energy up."},
    60: {"scenes": 6, "hook_seconds": 3, "description": "Full minute. 6 scenes. Needs a midpoint hook to retain viewers."},
}


# ---------------------------------------------------------------------------
# Env loader
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


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------

def generate_scripts(
    topic: str,
    duration: int,
    fmt: str,
    vibe: str,
    variants: int,
    extra_context: str | None,
) -> list[dict]:
    api_key = _load_env("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not found in environment or ~/.clawdbot/.env")

    client = anthropic.Anthropic(api_key=api_key)
    dur_spec = DURATION_SCENES[duration]
    vibe_desc = VIBES.get(vibe, vibe)

    # Build format instructions
    if fmt == "auto":
        format_block = "Pick the best format for this topic from: storytime, listicle, pov, problem-solution, before-after, hot-take, tutorial. State which you chose."
    else:
        f = FORMATS[fmt]
        format_block = f"""Format: {f['name']}
Description: {f['description']}
Structure: {f['structure']}
Tips: {f['tips']}"""

    context_block = f"\nExtra context: {extra_context}" if extra_context else ""

    prompt = f"""You are an expert short-form video scriptwriter who creates scripts that go viral on Instagram Reels, TikTok, and YouTube Shorts.

Topic: {topic}{context_block}
Duration: {duration} seconds
Target scenes: {dur_spec['scenes']}
Hook window: First {dur_spec['hook_seconds']} seconds
Vibe: {vibe} — {vibe_desc}

{format_block}

RULES:
- The HOOK is everything. First {dur_spec['hook_seconds']} seconds must stop the scroll or they swipe away.
- Every scene needs: time range, narration (exact words to say), visual direction, and text overlay
- Narration should be conversational — written for speaking out loud, not reading
- Text overlays are SHORT (2-6 words) — they reinforce, not duplicate the narration
- Visual direction should be specific and actionable (camera angle, what's on screen, transitions)
- Total narration word count should match ~{duration * 2.5:.0f} words ({duration} seconds at 2.5 words/sec)
- Include a scene label for each scene: HOOK, SETUP, BODY, REVEAL, CTA, etc.
- Last scene is always a CTA

Generate {variants} distinct script variant{'s' if variants > 1 else ''}.{' Each should use a completely different hook angle.' if variants > 1 else ''}

Return ONLY valid JSON in this exact format, no other text:
{{
  "scripts": [
    {{
      "variant": 1,
      "format": "the format used",
      "hook_text": "the first line of narration (just the hook)",
      "total_words": 0,
      "scenes": [
        {{
          "time": "0-3s",
          "label": "HOOK",
          "narration": "exact words to say",
          "visual": "what the viewer sees — camera, action, setting",
          "text_overlay": "SHORT text on screen (2-6 words)"
        }}
      ]
    }}
  ]
}}"""

    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = message.content[0].text.strip()

    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    data = json.loads(raw)
    return data["scripts"]


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

def print_scripts(scripts: list[dict], duration: int, vibe: str):
    for script in scripts:
        print(f"\n{'━' * 64}")
        if len(scripts) > 1:
            print(f"  VARIANT {script['variant']}")
        print(f"  {script.get('format', 'auto').upper()} · {duration}s · {vibe}")
        print(f"  Hook: \"{script['hook_text']}\"")
        print(f"  Words: ~{script.get('total_words', '?')}")
        print(f"{'━' * 64}")

        for scene in script["scenes"]:
            print(f"\n  [{scene['time']}] {scene['label']}")
            print(f"  NARRATION: \"{scene['narration']}\"")
            print(f"  VISUAL:    {scene['visual']}")
            print(f"  TEXT:      {scene['text_overlay']}")

        print(f"\n{'━' * 64}")
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Generate timed short-form video scripts")
    parser.add_argument("topic", nargs="?", help="What the video is about")
    parser.add_argument("--duration", "-d", type=int, default=30, choices=[15, 30, 45, 60],
                        help="Target duration in seconds (default: 30)")
    parser.add_argument("--format", "-f", default="auto", choices=list(FORMATS.keys()),
                        help="Script format (default: auto)")
    parser.add_argument("--vibe", default="relatable",
                        help=f"Tone: {', '.join(VIBES.keys())} or freeform (default: relatable)")
    parser.add_argument("--variants", "-n", type=int, default=1,
                        help="Number of script variants (1-3, default: 1)")
    parser.add_argument("--context", "-c", help="Extra context (product, audience, etc.)")
    parser.add_argument("--json", action="store_true", dest="json_out",
                        help="Output raw JSON")
    parser.add_argument("--list-formats", action="store_true",
                        help="Print all format options and exit")

    args = parser.parse_args()

    if args.list_formats:
        print("\nAvailable formats:")
        for name, f in FORMATS.items():
            print(f"  {name:<20} {f['description']}")
        print()
        return

    if not args.topic:
        parser.print_help()
        sys.exit(1)

    if args.variants < 1 or args.variants > 3:
        print("ERROR: --variants must be between 1 and 3", file=sys.stderr)
        sys.exit(1)

    print(f"[script-writer] {args.duration}s · {args.format} · {args.vibe} · {args.variants} variant(s)...")

    try:
        scripts = generate_scripts(
            topic=args.topic,
            duration=args.duration,
            fmt=args.format,
            vibe=args.vibe,
            variants=args.variants,
            extra_context=args.context,
        )
    except (RuntimeError, json.JSONDecodeError, KeyError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    if args.json_out:
        print(json.dumps(scripts, indent=2))
        return

    print_scripts(scripts, args.duration, args.vibe)


if __name__ == "__main__":
    main()
