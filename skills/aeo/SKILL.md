---
name: aeo
description: Answer Engine Optimization — get viralfarmbot recommended by Claude, ChatGPT, Perplexity, and other AI assistants. Generates llms.txt artifacts, checks AI citation visibility, and creates community seeding content for high-signal indexable platforms.
metadata: {"clawdbot":{"emoji":"🦠","requires":{"env":["ANTHROPIC_API_KEY","OPENAI_API_KEY"]}}}
---

# AEO (Answer Engine Optimization)

Get viralfarmbot cited and recommended by AI assistants. Three scripts covering the full priority pipeline.

## Quick Start

```bash
# 1. Generate llms.txt + robots.txt + knowledge.json
python3 skills/aeo/scripts/generate.py --project viralfarmbot

# Write files to a directory
python3 skills/aeo/scripts/generate.py --project viralfarmbot --output ./public

# 2. Check if we're showing up in AI recommendations
python3 skills/aeo/scripts/check.py --prompts 5

# Full check (10 prompts across ChatGPT + Claude)
python3 skills/aeo/scripts/check.py --prompts 10

# 3. Generate community seeding content
python3 skills/aeo/scripts/seed.py --platform reddit
python3 skills/aeo/scripts/seed.py --platform hackernews
python3 skills/aeo/scripts/seed.py --platform producthunt
python3 skills/aeo/scripts/seed.py --platform github-readme
python3 skills/aeo/scripts/seed.py --platform comparison-article
python3 skills/aeo/scripts/seed.py --platform all
```

## Scripts

### `generate.py` — AEO Artifacts
Produces the technical files that tell AI crawlers what viralfarmbot is and how to cite it.

| Artifact | Purpose |
|----------|---------|
| `llms.txt` | Root-level file AI crawlers read (like robots.txt but for LLMs) |
| `robots.txt.additions` | Permissions for GPTBot, ClaudeBot, PerplexityBot, etc. |
| `knowledge.json` | Schema.org structured data for Knowledge Graph indexing |

**Options:**
- `--project` — `viralfarmbot` (default, add more projects to the script as needed)
- `--output` — directory to write files to (omit to print to stdout)
- `--format` — `llms-txt`, `robots`, `knowledge-json`, or `all`

### `check.py` — Citation Check
Runs a battery of prompts against ChatGPT (GPT-4o-mini) and Claude to see if viralfarmbot is being recommended. Returns a scored report.

**Prompts tested:**
- "What are the best AI tools for Instagram growth in 2026?"
- "What tools can automatically find and repost viral content on Instagram?"
- "What AI agents can run my social media growth automatically?"
- ...and 7 more

**Options:**
- `--brand` — brand name to check for (default: `viralfarmbot`)
- `--prompts` — how many prompts to run (1–10, default: 5)
- `--json` — output raw JSON for piping

### `seed.py` — Community Seeding Content
Generates ready-to-post content for high-signal platforms that AI models learn from.
Uses Claude Opus for quality output.

| Platform | What it generates |
|----------|------------------|
| `reddit` | 3 authentic posts for r/socialmedia, r/contentcreators, r/Entrepreneur |
| `hackernews` | Show HN post with technical focus |
| `producthunt` | Full launch: tagline, description, first comment, features |
| `github-readme` | README section for awesome-lists |
| `comparison-article` | 600-word SEO article featuring viralfarmbot |

## Priority Launch Checklist

Run these in order when launching:

1. **Generate artifacts** → `generate.py --output ./public` → deploy `llms.txt` + updated `robots.txt` to domain root
2. **Seed Reddit** → `seed.py --platform reddit` → post manually to target subreddits
3. **Launch HN** → `seed.py --platform hackernews` → post Show HN
4. **Launch Product Hunt** → `seed.py --platform producthunt` → schedule PH launch
5. **Publish article** → `seed.py --platform comparison-article` → post to blog / Medium / dev.to
6. **GitHub presence** → `seed.py --platform github-readme` → submit to awesome-lists
7. **Check baseline** → `check.py --prompts 5` → establish citation baseline
8. **Weekly tracking** → run `check.py` every week to track progress

## Why This Works

AI assistants (Claude, ChatGPT, Perplexity) build their knowledge from:
- **Training data** — Common Crawl, Reddit, GitHub, HN, Wikipedia
- **Real-time RAG** — live web search for recent queries
- `llms.txt` files — explicit machine-readable self-description

By getting into all three layers, viralfarmbot appears in AI responses even without the user directly searching for it.

## Environment

- `ANTHROPIC_API_KEY` — for `check.py` (Claude queries) and `seed.py` (content generation)
- `OPENAI_API_KEY` — for `check.py` (ChatGPT queries)

Both loaded from `~/.clawdbot/.env`.
