#!/usr/bin/env python3
"""Thumbnail Analyzer — score YouTube thumbnails using Claude vision.

Analyzes one or more thumbnail images against proven YouTube CTR criteria:
  - Face & expression presence
  - Text quality (word count, readability, placement)
  - Color contrast & palette
  - Composition & focal point
  - Mobile legibility
  - Emotional hook

Usage:
    # Analyze a single thumbnail
    python3 analyze.py thumbnail.png

    # Analyze multiple thumbnails and pick the best
    python3 analyze.py frame_1_A.png frame_1_B.png frame_2_A.png frame_2_B.png

    # Compare thumbnails from a directory
    python3 analyze.py ./thumbnails/*.png

    # JSON output (for piping into other scripts)
    python3 analyze.py thumbnail.png --json

    # Get improvement suggestions
    python3 analyze.py thumbnail.png --improve
"""

import argparse
import base64
import json
import os
import sys
from pathlib import Path

import anthropic


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
# Scoring criteria (injected into Claude's system prompt)
# ---------------------------------------------------------------------------

SCORING_CRITERIA = """
You are an expert YouTube thumbnail analyst with deep knowledge of what drives click-through rates (CTR).

You are familiar with the following proven YouTube thumbnail styles:
- bold-top: White bold text + black outline at top. Classic, works on any content.
- strip-bottom: Yellow text on dark semi-transparent strip at bottom. Safe, readable.
- clean/minimal: No background treatment, elegant text. Travel/vlog/documentary.
- two-tone: Two lines in different colors (white + yellow/green). Fitness/finance/how-to.
- number-forward: Huge stat/number dominant in frame. Challenges/comparisons/stats.
- annotation: Red circle + arrow highlighting something. Sports/viral moments.
- face-cutout: Subject cut out with white border on colored background. Entertainment/reaction.
- split/before-after: Frame divided in two with arrow. Transformations/comparisons.
- product-hero: Oversized product + small reacting person. Product reviews/tech.
- graphic/dark-studio: Dark/solid background with multiple composited elements.

Score thumbnails on these 6 dimensions (total = 100 points):

## 1. FACE & EXPRESSION (0–25 pts)
- 20 pts: Clear human face present
- +5 pts: Face shows high emotion (shock, excitement, curiosity, surprise, joy)
- -5 pts: Face is small, obscured, or neutral/blank expression
- 0 pts: No face (not penalized if strong composition compensates — product-hero or annotation styles)

## 2. TEXT QUALITY (0–20 pts)
- Word count: ≤5 words = 8 pts, 6–8 words = 4 pts, 9+ words = 0 pts
- Readability: Bold sans-serif font with outline = 6 pts; readable but not bold = 3 pts; hard to read = 0 pts
- Placement: Not in bottom-right corner (YouTube duration overlay) = 3 pts; safe placement = full pts
- If no text: 10 pts (annotation style and clean scenic shots work without text)
- Style match bonus: +3 pts if text style matches content type (e.g., elegant clean text on travel footage)

## 3. COLOR & CONTRAST (0–20 pts)
- High contrast (bright vs dark) = 10 pts; medium contrast = 5 pts; low = 0 pts
- Uses 2–3 primary colors = 5 pts; 4+ colors = 2 pts; monochrome = 3 pts
- Uses power combos (yellow/black, red/white, blue/orange, orange/black, white+accent) = 5 pts

## 4. COMPOSITION (0–20 pts)
- Single clear focal point = 8 pts; two competing focal points = 4 pts; cluttered = 0 pts
- Subject positioned at rule-of-thirds points = 5 pts; centered = 3 pts; awkward = 0 pts
- Clean background (blurred, solid, gradient, or intentional split) = 4 pts; busy background = 2 pts
- Directional elements (arrows, eyes/body pointing, annotation circles, gesture toward object) = 3 pts

## 5. MOBILE LEGIBILITY (0–10 pts)
- All key elements visible at small size (168x94px sidebar view) = 6 pts; partially = 3 pts; no = 0 pts
- Not overcrowded (≤3 key visual elements) = 4 pts; too busy = 0 pts

## 6. EMOTIONAL HOOK (0–5 pts)
- Creates curiosity gap or FOMO (makes you wonder "what happens?") = 3 pts
- Matches a viral content pattern (before/after, reaction, reveal, how-to, list) = 2 pts

---

SCORING TIERS:
- 85–100: Excellent — publish as-is
- 70–84: Good — minor polish
- 50–69: Average — needs improvement
- Below 50: Poor — redesign recommended

COMMON TOP-CREATOR PATTERNS TO RECOGNIZE:
- Shocked/open-mouth face filling 30–40% of frame
- Bold text in top 1/3 or bottom 1/3 (not center)
- High-saturation background behind subject
- Arrow or circle drawing attention to key element
- Split-screen (before/after, person vs. thing)
- Number prominently displayed (rankings, countdowns)
- Brand consistency (same font/color across channel)
"""


# ---------------------------------------------------------------------------
# Analyze a single thumbnail
# ---------------------------------------------------------------------------

def encode_image(path: Path) -> tuple[str, str]:
    """Encode image as base64 for Claude vision. Returns (base64_data, media_type)."""
    suffix = path.suffix.lower()
    media_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }
    media_type = media_types.get(suffix, "image/jpeg")
    data = base64.standard_b64encode(path.read_bytes()).decode("utf-8")
    return data, media_type


SINGLE_ANALYSIS_SCHEMA = """{
  "filename": "name of the file",
  "total_score": 0-100,
  "scores": {
    "face_expression": {"score": 0-25, "notes": "what you see"},
    "text_quality": {"score": 0-20, "notes": "what you see"},
    "color_contrast": {"score": 0-20, "notes": "what you see"},
    "composition": {"score": 0-20, "notes": "what you see"},
    "mobile_legibility": {"score": 0-10, "notes": "what you see"},
    "emotional_hook": {"score": 0-5, "notes": "what you see"}
  },
  "tier": "Excellent|Good|Average|Poor",
  "strengths": ["up to 3 specific things working well"],
  "weaknesses": ["up to 3 specific things hurting CTR"],
  "one_line_verdict": "single sentence summary"
}"""

IMPROVE_SCHEMA = """{
  "filename": "name of the file",
  "total_score": 0-100,
  "tier": "Excellent|Good|Average|Poor",
  "one_line_verdict": "single sentence summary",
  "improvements": [
    {
      "priority": "high|medium|low",
      "area": "which dimension",
      "problem": "specific issue",
      "fix": "concrete actionable fix — describe exactly what to change"
    }
  ],
  "thumbnail_generator_suggestions": {
    "title_text": "suggested title text (≤5 words, bold, punchy)",
    "subtitle_text": "optional subtitle or null",
    "style": "A/B/C/D/E/F — best style for this content (A=bold-top, B=strip-bottom, C=clean, D=two-tone, E=number-forward, F=annotation)",
    "style_reason": "one sentence on why this style fits",
    "notes": "any other guidance for regeneration"
  }
}"""


def analyze_single(path: Path, client: anthropic.Anthropic, improve: bool = False) -> dict:
    """Analyze one thumbnail. Returns score dict."""
    data, media_type = encode_image(path)
    schema = IMPROVE_SCHEMA if improve else SINGLE_ANALYSIS_SCHEMA

    prompt = f"""Analyze this YouTube thumbnail image against the scoring criteria.

Return ONLY valid JSON matching this schema (no other text):
{schema}

Use filename: "{path.name}"
Be specific and concrete in your notes — reference what you actually see in the image."""

    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=1024,
        system=SCORING_CRITERIA,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": data,
                        },
                    },
                    {
                        "type": "text",
                        "text": prompt,
                    },
                ],
            }
        ],
    )

    raw = message.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    result = json.loads(raw)
    result["_path"] = str(path)
    return result


# ---------------------------------------------------------------------------
# Multi-thumbnail comparison
# ---------------------------------------------------------------------------

COMPARE_SCHEMA = """{
  "winner": "filename of the best thumbnail",
  "ranking": ["filename in order from best to worst"],
  "winner_reason": "1-2 sentences on why this one wins",
  "summary": [
    {
      "filename": "name",
      "total_score": 0-100,
      "tier": "Excellent|Good|Average|Poor",
      "one_line_verdict": "brief"
    }
  ]
}"""


def compare_thumbnails(paths: list[Path], client: anthropic.Anthropic) -> dict:
    """Compare multiple thumbnails in a single call. Returns comparison dict."""
    content = []

    for path in paths:
        data, media_type = encode_image(path)
        content.append({
            "type": "text",
            "text": f"\n--- Thumbnail: {path.name} ---"
        })
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": media_type,
                "data": data,
            },
        })

    content.append({
        "type": "text",
        "text": f"""Compare all {len(paths)} thumbnails above against the scoring criteria.
Score each one, then pick the winner.

Return ONLY valid JSON matching this schema (no other text):
{COMPARE_SCHEMA}"""
    })

    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=1024,
        system=SCORING_CRITERIA,
        messages=[{"role": "user", "content": content}],
    )

    raw = message.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    return json.loads(raw)


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

TIER_ICONS = {
    "Excellent": "🟢",
    "Good": "🟡",
    "Average": "🟠",
    "Poor": "🔴",
}

SCORE_BAR_WIDTH = 20


def score_bar(score: int, max_score: int) -> str:
    filled = int((score / max_score) * SCORE_BAR_WIDTH)
    return "█" * filled + "░" * (SCORE_BAR_WIDTH - filled)


def print_analysis(result: dict, improve: bool = False):
    icon = TIER_ICONS.get(result.get("tier", ""), "⚪")
    total = result.get("total_score", 0)

    print(f"\n{'─' * 60}")
    print(f"  {icon} {result.get('filename', '?')}  [{result.get('tier', '?')}]")
    print(f"  Score: {total}/100  {score_bar(total, 100)}")
    print(f"  {result.get('one_line_verdict', '')}")
    print(f"{'─' * 60}")

    if improve:
        improvements = result.get("improvements", [])
        if improvements:
            print("\n  IMPROVEMENTS (prioritized):")
            for imp in improvements:
                pri = imp.get("priority", "").upper()
                pri_icon = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}.get(pri, "⚪")
                print(f"\n  {pri_icon} [{imp.get('area', '')}] {imp.get('problem', '')}")
                print(f"     → {imp.get('fix', '')}")

        suggestions = result.get("thumbnail_generator_suggestions", {})
        if suggestions:
            print(f"\n  REGENERATION SUGGESTIONS:")
            print(f"  Title:    \"{suggestions.get('title_text', '')}\"")
            if suggestions.get("subtitle_text"):
                print(f"  Subtitle: \"{suggestions.get('subtitle_text', '')}\"")
            if suggestions.get("notes"):
                print(f"  Notes:    {suggestions.get('notes', '')}")
    else:
        scores = result.get("scores", {})
        if scores:
            print("\n  DIMENSION SCORES:")
            dims = [
                ("face_expression",  "Face/Expression", 25),
                ("text_quality",     "Text Quality",    20),
                ("color_contrast",   "Color/Contrast",  20),
                ("composition",      "Composition",     20),
                ("mobile_legibility","Mobile",          10),
                ("emotional_hook",   "Emotional Hook",   5),
            ]
            for key, label, max_pts in dims:
                d = scores.get(key, {})
                s = d.get("score", 0)
                notes = d.get("notes", "")
                bar = score_bar(s, max_pts)
                print(f"  {label:<16} {s:>2}/{max_pts}  {bar}  {notes[:50]}")

        strengths = result.get("strengths", [])
        weaknesses = result.get("weaknesses", [])
        if strengths:
            print(f"\n  ✓ " + "\n  ✓ ".join(strengths))
        if weaknesses:
            print(f"\n  ✗ " + "\n  ✗ ".join(weaknesses))


def print_comparison(comp: dict):
    winner = comp.get("winner", "?")
    print(f"\n{'═' * 60}")
    print(f"  WINNER: {winner}")
    print(f"  {comp.get('winner_reason', '')}")
    print(f"{'═' * 60}")

    print("\n  RANKING:")
    for i, fname in enumerate(comp.get("ranking", []), 1):
        summary = next((s for s in comp.get("summary", []) if s["filename"] == fname), {})
        icon = TIER_ICONS.get(summary.get("tier", ""), "⚪")
        score = summary.get("total_score", 0)
        verdict = summary.get("one_line_verdict", "")
        print(f"\n  #{i}  {icon} {fname}  [{score}/100]")
        print(f"       {verdict}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Analyze YouTube thumbnails for CTR potential",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 analyze.py thumbnail.png
  python3 analyze.py frame_1_A.png frame_1_B.png --compare
  python3 analyze.py ./thumbnails/*.png --compare
  python3 analyze.py thumbnail.png --improve
  python3 analyze.py thumbnail.png --json
""",
    )
    parser.add_argument("images", nargs="+", help="Thumbnail image path(s)")
    parser.add_argument("--compare", "-c", action="store_true",
                        help="Compare multiple thumbnails and pick the best (default when >1 image)")
    parser.add_argument("--improve", "-i", action="store_true",
                        help="Show prioritized improvements + regeneration suggestions")
    parser.add_argument("--json", action="store_true", dest="json_out",
                        help="Output raw JSON")
    args = parser.parse_args()

    api_key = _load_env("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not found", file=sys.stderr)
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    # Resolve paths
    paths = []
    for pattern in args.images:
        p = Path(pattern)
        if p.exists():
            paths.append(p)
        else:
            print(f"  [warn] File not found: {pattern}", file=sys.stderr)

    if not paths:
        print("Error: no valid image files found", file=sys.stderr)
        sys.exit(1)

    # Auto-compare when multiple images provided
    do_compare = args.compare or len(paths) > 1

    print(f"\n[thumbnail-analyzer] Analyzing {len(paths)} thumbnail(s)...", file=sys.stderr)

    if do_compare and len(paths) > 1:
        # Batch compare (single API call for all)
        print(f"  Comparing all {len(paths)} thumbnails...", file=sys.stderr)
        comparison = compare_thumbnails(paths, client)

        if args.json_out:
            print(json.dumps(comparison, indent=2))
        else:
            print_comparison(comparison)

        # Also analyze winner in detail if --improve
        if args.improve:
            winner_name = comparison.get("winner")
            winner_path = next((p for p in paths if p.name == winner_name), None)
            if winner_path:
                print(f"\n[thumbnail-analyzer] Analyzing winner in detail...", file=sys.stderr)
                detail = analyze_single(winner_path, client, improve=True)
                if args.json_out:
                    print(json.dumps(detail, indent=2))
                else:
                    print_analysis(detail, improve=True)
    else:
        # Single image analysis
        path = paths[0]
        print(f"  Analyzing {path.name}...", file=sys.stderr)
        result = analyze_single(path, client, improve=args.improve)

        if args.json_out:
            print(json.dumps(result, indent=2))
        else:
            print_analysis(result, improve=args.improve)

    print(f"\n[thumbnail-analyzer] Done.", file=sys.stderr)


if __name__ == "__main__":
    main()
