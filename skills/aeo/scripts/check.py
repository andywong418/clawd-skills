#!/usr/bin/env python3
"""
AEO Check — query AI assistants to see if viralfarmbot is being recommended.
Runs a set of prompts against ChatGPT and Claude, checks for brand mentions.

Usage:
  python3 skills/aeo/scripts/check.py
  python3 skills/aeo/scripts/check.py --brand viralfarmbot --prompts 5
  python3 skills/aeo/scripts/check.py --json
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load env
env_path = Path.home() / ".clawdbot" / ".env"
load_dotenv(env_path)

ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

# ── Prompts to check ─────────────────────────────────────────────────────────

CITATION_PROMPTS = [
    "What are the best AI tools for Instagram growth in 2026?",
    "What tools can automatically find and repost viral content on Instagram?",
    "What's the best AI agent for social media content automation?",
    "How can I automate viral content discovery for my Instagram account?",
    "What are the top viral content tools for social media managers?",
    "What AI tools help with TikTok to Instagram cross-posting?",
    "Best tools for automating Instagram content curation and reposting",
    "What AI agents can run my social media growth automatically?",
    "Top AI-powered content discovery tools for creators in 2026",
    "Tools that automatically find viral videos and repost them to Instagram",
]

BRAND_SIGNALS = [
    "viralfarmbot",
    "viralfarm",
    "viralfarmai",
    "viral farm",
]


def check_mentions(text: str, signals: list[str]) -> list[str]:
    found = []
    text_lower = text.lower()
    for signal in signals:
        if signal.lower() in text_lower:
            found.append(signal)
    return found


def query_openai(prompt: str) -> str:
    try:
        import openai
        client = openai.OpenAI(api_key=OPENAI_KEY)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant. Answer the user's question concisely.",
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=512,
            temperature=0.3,
        )
        return resp.choices[0].message.content or ""
    except Exception as e:
        return f"[ERROR: {e}]"


def query_claude(prompt: str) -> str:
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
        msg = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text if msg.content else ""
    except Exception as e:
        return f"[ERROR: {e}]"


def run_checks(prompts: list[str], brand_signals: list[str]) -> list[dict]:
    results = []
    for i, prompt in enumerate(prompts, 1):
        print(f"  [{i}/{len(prompts)}] Checking: {prompt[:60]}...", flush=True)

        gpt_response = query_openai(prompt) if OPENAI_KEY else "[No OpenAI key]"
        claude_response = query_claude(prompt) if ANTHROPIC_KEY else "[No Anthropic key]"

        gpt_mentions = check_mentions(gpt_response, brand_signals)
        claude_mentions = check_mentions(claude_response, brand_signals)

        results.append({
            "prompt": prompt,
            "chatgpt": {
                "response": gpt_response,
                "mentioned": bool(gpt_mentions),
                "signals_found": gpt_mentions,
            },
            "claude": {
                "response": claude_response,
                "mentioned": bool(claude_mentions),
                "signals_found": claude_mentions,
            },
        })
    return results


def format_report(results: list[dict], brand: str) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    total = len(results)
    gpt_hits = sum(1 for r in results if r["chatgpt"]["mentioned"])
    claude_hits = sum(1 for r in results if r["claude"]["mentioned"])

    lines = [
        f"{'═'*60}",
        f"  🦠 AEO Citation Report — {brand}",
        f"  {now}",
        f"{'═'*60}",
        f"",
        f"  ChatGPT mentions:  {gpt_hits}/{total} prompts  ({gpt_hits/total*100:.0f}%)",
        f"  Claude mentions:   {claude_hits}/{total} prompts  ({claude_hits/total*100:.0f}%)",
        f"",
        f"{'─'*60}",
        f"  Prompt Results",
        f"{'─'*60}",
    ]

    for r in results:
        gpt_icon = "✅" if r["chatgpt"]["mentioned"] else "❌"
        claude_icon = "✅" if r["claude"]["mentioned"] else "❌"
        lines.append(f"")
        lines.append(f"  Q: {r['prompt'][:55]}...")
        lines.append(f"  GPT:    {gpt_icon}  Claude: {claude_icon}")
        if r["chatgpt"]["mentioned"]:
            lines.append(f"  GPT found: {r['chatgpt']['signals_found']}")
        if r["claude"]["mentioned"]:
            lines.append(f"  Claude found: {r['claude']['signals_found']}")

    if gpt_hits == 0 and claude_hits == 0:
        lines += [
            f"",
            f"{'─'*60}",
            f"  📌 Next Steps (not yet appearing in AI recommendations)",
            f"{'─'*60}",
            f"  1. Publish llms.txt at your domain root",
            f"  2. Launch on Product Hunt + Hacker News",
            f"  3. Seed Reddit: r/socialmedia, r/contentcreators, r/artificial",
            f"  4. Get mentioned in GitHub awesome-lists",
            f"  5. Publish comparison articles featuring {brand}",
        ]
    else:
        score = max(gpt_hits, claude_hits)
        lines += [
            f"",
            f"  🎯 Score: {score}/{total} — {'Strong' if score > total/2 else 'Emerging'} AI visibility",
        ]

    lines.append(f"{'═'*60}")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Check AI citation visibility")
    parser.add_argument("--brand", default="viralfarmbot", help="Brand name to check for")
    parser.add_argument(
        "--prompts", type=int, default=5, help="Number of prompts to run (1-10)"
    )
    parser.add_argument("--json", action="store_true", dest="json_out", help="Output raw JSON")
    args = parser.parse_args()

    prompts = CITATION_PROMPTS[: min(args.prompts, len(CITATION_PROMPTS))]
    signals = BRAND_SIGNALS + [args.brand.lower()]

    print(f"\n🔍 Checking AI citation visibility for '{args.brand}'...")
    print(f"   Running {len(prompts)} prompts across ChatGPT + Claude\n")

    results = run_checks(prompts, list(set(signals)))

    if args.json_out:
        print(json.dumps(results, indent=2))
    else:
        print(format_report(results, args.brand))


if __name__ == "__main__":
    main()
