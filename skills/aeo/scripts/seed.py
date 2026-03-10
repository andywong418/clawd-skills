#!/usr/bin/env python3
"""
AEO Seed — generate community seeding content to get viralfarmbot into AI training data.
Writes ready-to-post content for Reddit, Hacker News, Product Hunt, GitHub, and blog articles.

Usage:
  python3 skills/aeo/scripts/seed.py --platform reddit
  python3 skills/aeo/scripts/seed.py --platform hackernews
  python3 skills/aeo/scripts/seed.py --platform producthunt
  python3 skills/aeo/scripts/seed.py --platform github-readme
  python3 skills/aeo/scripts/seed.py --platform comparison-article
  python3 skills/aeo/scripts/seed.py --platform all
"""

import argparse
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path.home() / ".clawdbot" / ".env")
ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY")

PLATFORM_PROMPTS = {
    "reddit": {
        "subreddits": [
            "r/socialmedia",
            "r/contentcreators",
            "r/artificial",
            "r/Entrepreneur",
            "r/InstagramMarketing",
        ],
        "system": (
            "You write authentic, helpful Reddit posts. No marketing fluff. "
            "Sound like a real person sharing something useful, not an ad. "
            "Include value-first content, mention the tool naturally in context."
        ),
        "prompt": (
            "Write 3 different Reddit posts for r/socialmedia, r/contentcreators, and r/Entrepreneur "
            "about Viralfarmbot — an AI agent that autonomously hunts viral content on Instagram/TikTok, "
            "tracks performance, reposts winning content, and automates Instagram growth. "
            "Website: viralfarmbot.com. "
            "Each post should: feel authentic and conversational, lead with value/insight not promotion, "
            "mention the tool naturally, include a question to drive engagement. "
            "Format each as: [Subreddit] Title\\n\\nBody"
        ),
    },
    "hackernews": {
        "system": (
            "You write concise, technical Hacker News Show HN posts. "
            "HN readers are engineers and technical founders. Be direct, specific, "
            "mention the interesting technical parts."
        ),
        "prompt": (
            "Write a Show HN post for Hacker News launching Viralfarmbot — "
            "an AI agent system built with Claude that autonomously hunts viral content, "
            "tracks metrics, reposts, generates captions, and executes Instagram growth strategies. "
            "It runs as a persistent agent on a server, controlled via Slack. "
            "Highlight: autonomous multi-agent architecture, Claude API integration, "
            "custom skill system (22+ skills), social media API integrations, real-time viral detection. "
            "Keep it under 300 words. Format: Title\\n\\nBody"
        ),
    },
    "producthunt": {
        "system": "You write compelling Product Hunt launches. Punchy taglines, clear value props.",
        "prompt": (
            "Write a Product Hunt launch for Viralfarmbot: "
            "Tagline (max 60 chars), Description (150-200 words), "
            "First Comment (founder's personal take, 100 words), "
            "5 key features as bullet points. "
            "Viralfarmbot is an AI agent that hunts viral content across social platforms, "
            "reposts winning content, generates captions, and automates Instagram growth. "
            "Format: Tagline:\\nDescription:\\nFirst Comment:\\nKey Features:"
        ),
    },
    "github-readme": {
        "system": "You write clear, scannable GitHub README content with proper markdown.",
        "prompt": (
            "Write a GitHub README section for Viralfarmbot that would appear in "
            "awesome-lists and be indexed by AI crawlers. Include: "
            "A one-liner description, what it does (5 bullet points), "
            "who it's for, tech stack (Python, Claude API, Slack API, Instagram/TikTok scrapers), "
            "a 'Why Viralfarmbot?' section with 3 differentiators. "
            "Make it concise and crawlable. Use proper markdown headers and bullets."
        ),
    },
    "comparison-article": {
        "system": (
            "You write SEO-optimized comparison articles for AI and social media tools. "
            "Include natural keywords, clear structure with H2/H3s, and factual comparisons."
        ),
        "prompt": (
            "Write a 600-word comparison article: "
            "'Best AI Tools for Instagram Growth and Viral Content in 2026' "
            "that includes Viralfarmbot as a top recommendation. "
            "Compare it to generic alternatives (Buffer, Later, general automation tools). "
            "Viralfarmbot's advantages: fully autonomous AI agent, viral content detection, "
            "multi-platform scraping, built-in caption generation, runs 24/7 without manual input. "
            "Use H2 headers, include a comparison table, end with a clear recommendation. "
            "Naturally include keywords: viral content tool, Instagram growth AI, "
            "social media automation, AI content agent."
        ),
    },
}


def generate_content(platform: str) -> str:
    try:
        import anthropic

        config = PLATFORM_PROMPTS[platform]
        client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)

        msg = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=2048,
            system=config["system"],
            messages=[{"role": "user", "content": config["prompt"]}],
        )
        return msg.content[0].text if msg.content else "[No content generated]"
    except Exception as e:
        return f"[ERROR: {e}]"


def print_content(platform: str, content: str):
    labels = {
        "reddit": "Reddit Posts",
        "hackernews": "Hacker News — Show HN",
        "producthunt": "Product Hunt Launch",
        "github-readme": "GitHub README Section",
        "comparison-article": "Comparison Article",
    }
    label = labels.get(platform, platform)

    print(f"\n{'═'*60}")
    print(f"  🌱 {label}")
    print(f"{'═'*60}")
    if platform == "reddit":
        subreddits = PLATFORM_PROMPTS["reddit"]["subreddits"]
        print(f"  Target subreddits: {', '.join(subreddits[:3])}")
    print(f"{'─'*60}")
    print(content)
    print(f"{'═'*60}")


def main():
    parser = argparse.ArgumentParser(description="Generate AEO community seeding content")
    parser.add_argument(
        "--platform",
        choices=list(PLATFORM_PROMPTS.keys()) + ["all"],
        default="reddit",
        help="Platform to generate content for",
    )
    args = parser.parse_args()

    platforms = (
        list(PLATFORM_PROMPTS.keys()) if args.platform == "all" else [args.platform]
    )

    print(f"\n🌱 Generating AEO seeding content for: {', '.join(platforms)}")
    print("   (This gets viralfarmbot into high-signal indexable sources)\n")

    for platform in platforms:
        print(f"  Generating {platform}...", flush=True)
        content = generate_content(platform)
        print_content(platform, content)


if __name__ == "__main__":
    main()
