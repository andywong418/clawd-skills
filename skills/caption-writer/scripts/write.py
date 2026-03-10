#!/usr/bin/env python3
"""Caption Writer — generate platform-optimized captions via Claude.

Usage:
    python3 write.py "barber meme, Kendrick gets a Marge Simpson beehive"
    python3 write.py "AI tool that reads your mind" --platform tiktok --vibe mindblowing
    python3 write.py "cat chef cooking pasta" --platform instagram --vibe funny --variants 3
    python3 write.py --json "productivity hack nobody talks about"
"""

import argparse
import json
import os
import sys
from pathlib import Path

import anthropic


# ---------------------------------------------------------------------------
# Platform specs
# ---------------------------------------------------------------------------

PLATFORMS = {
    "instagram": {
        "name": "Instagram Reels",
        "caption_length": "3–8 lines max. Hook on line 1 (shows before 'more'). Body optional. CTA on last line.",
        "hashtags": "5–15 hashtags. Mix 3 niche (under 500K posts) + broad viral tags. Put at end.",
        "emoji_style": "Moderate emojis. 1–2 per line max. Strategic, not spammy.",
        "tone": "Conversational, relatable, slightly aspirational.",
        "cta_examples": ["follow for more", "save this", "comment your thoughts", "tag someone who needs this"],
    },
    "tiktok": {
        "name": "TikTok",
        "caption_length": "1–3 lines. Very short. TikTok shows minimal caption — hook must do the work.",
        "hashtags": "3–6 hashtags max. At least one trending/fyp tag.",
        "emoji_style": "1–3 emojis total. TikTok-native language.",
        "tone": "Gen-Z, lowercase preferred, internet-native, conversational.",
        "cta_examples": ["follow for pt 2", "comment if you agree", "stitch this", "duet this"],
    },
    "twitter": {
        "name": "Twitter / X",
        "caption_length": "1–3 punchy lines. No hashtags (they hurt reach on X now). Thread hook if long.",
        "hashtags": "None, or max 1 if truly relevant.",
        "emoji_style": "Minimal. 0–2 emojis total. Optional.",
        "tone": "Confident, opinionated, quotable. Write like a hot take.",
        "cta_examples": ["RT if you agree", "what do you think?", "follow for more takes", "bookmark this"],
    },
    "youtube": {
        "name": "YouTube Shorts",
        "caption_length": "2–4 lines. Keyword-rich for search. Describe what's in the video.",
        "hashtags": "3–5 hashtags. Use #Shorts. Include topic keywords.",
        "emoji_style": "Light. 1–2 emojis only.",
        "tone": "Slightly more formal than TikTok. SEO-aware. Clear and descriptive.",
        "cta_examples": ["subscribe for more", "watch til the end", "comment below", "like if this helped"],
    },
}

VIBES = {
    "funny":       "Comedic, self-aware, meme energy. Lean into the absurdity.",
    "mindblowing": "Awe-inspiring, 'I didn't know this existed' energy. Use words like 'insane', 'actually', 'no way'.",
    "relatable":   "Everyday struggle, everyone-feels-this energy. POV format works well.",
    "inspiring":   "Motivational, aspirational. Short punchy lines. No toxic positivity.",
    "informative": "Educational, value-forward. Hook with the insight, not the topic.",
    "mysterious":  "Cryptic, makes people want to know more. Cliffhanger energy.",
    "hype":        "Energetic, exclamatory, trending-moment energy. Build excitement.",
    "deadpan":     "Dry, understated, ironic. Say wild things like they're obvious facts.",
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

def generate_captions(
    topic: str,
    platform: str,
    vibe: str,
    variants: int,
    extra_context: str | None,
) -> list[dict]:
    api_key = _load_env("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not found in environment or ~/.clawdbot/.env")

    client = anthropic.Anthropic(api_key=api_key)
    spec = PLATFORMS[platform]
    vibe_desc = VIBES.get(vibe, vibe)

    context_block = f"\nExtra context: {extra_context}" if extra_context else ""

    prompt = f"""You are an expert viral content creator who writes captions that stop the scroll.

Video topic: {topic}{context_block}
Platform: {spec['name']}
Vibe: {vibe} — {vibe_desc}

Platform rules:
- Caption length: {spec['caption_length']}
- Hashtags: {spec['hashtags']}
- Emojis: {spec['emoji_style']}
- Tone: {spec['tone']}
- CTA examples (pick one or write a better one): {', '.join(spec['cta_examples'])}

Generate {variants} distinct caption variant{'s' if variants > 1 else ''}. Each should have a different hook angle.

Return ONLY valid JSON in this exact format, no other text:
{{
  "captions": [
    {{
      "variant": 1,
      "hook": "the first line / hook only",
      "full_caption": "the complete caption including hook, body, cta, and hashtags",
      "angle": "one sentence explaining the hook angle used"
    }}
  ]
}}"""

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
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
    return data["captions"]


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

def print_captions(captions: list[dict], platform: str, vibe: str):
    spec = PLATFORMS[platform]
    print(f"\n{'─' * 60}")
    print(f"  {spec['name']} · {vibe}")
    print(f"{'─' * 60}")
    for cap in captions:
        if len(captions) > 1:
            print(f"\n  Variant {cap['variant']} — {cap['angle']}")
            print(f"  {'─' * 56}")
        print()
        for line in cap["full_caption"].splitlines():
            print(f"  {line}")
        print()
    print(f"{'─' * 60}\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Generate platform-optimized video captions")
    parser.add_argument("topic", nargs="?", help="Video topic or description")
    parser.add_argument("--platform", "-p", default="instagram",
                        choices=list(PLATFORMS.keys()),
                        help="Target platform (default: instagram)")
    parser.add_argument("--vibe", default="relatable",
                        help=f"Content vibe: {', '.join(VIBES.keys())} or freeform (default: relatable)")
    parser.add_argument("--variants", "-n", type=int, default=1,
                        help="Number of caption variants to generate (default: 1)")
    parser.add_argument("--context", "-c", help="Extra context about the video")
    parser.add_argument("--json", action="store_true", dest="json_out",
                        help="Output raw JSON")
    parser.add_argument("--list-vibes", action="store_true",
                        help="Print all vibe options and exit")
    args = parser.parse_args()

    if args.list_vibes:
        print("\nAvailable vibes:")
        for name, desc in VIBES.items():
            print(f"  {name:<14} {desc}")
        print()
        return

    if not args.topic:
        parser.print_help()
        sys.exit(1)

    if args.variants < 1 or args.variants > 5:
        print("ERROR: --variants must be between 1 and 5", file=sys.stderr)
        sys.exit(1)

    print(f"[caption-writer] {args.platform} · {args.vibe} · {args.variants} variant(s)...")

    try:
        captions = generate_captions(
            topic=args.topic,
            platform=args.platform,
            vibe=args.vibe,
            variants=args.variants,
            extra_context=args.context,
        )
    except (RuntimeError, json.JSONDecodeError, KeyError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    if args.json_out:
        print(json.dumps(captions, indent=2))
        return

    print_captions(captions, args.platform, args.vibe)


if __name__ == "__main__":
    main()
