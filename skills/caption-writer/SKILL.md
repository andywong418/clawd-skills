---
name: caption-writer
description: Generate platform-optimized captions for Instagram Reels, TikTok, Twitter/X, and YouTube Shorts via Claude. Outputs hook + body + CTA + hashtags tuned per platform. Use when asked to write a caption, post copy, hashtags, or social media text for a video.
metadata: {"clawdbot":{"emoji":"✍️","requires":{"env":["ANTHROPIC_API_KEY"]}}}
---

# Caption Writer

Generate viral-ready captions tuned per platform and vibe. Uses Claude Haiku — fast and cheap.

## Quick Start

```bash
# Instagram, default vibe
python3 skills/caption-writer/scripts/write.py "barber meme, Kendrick gets a Marge Simpson beehive"

# TikTok, funny
python3 skills/caption-writer/scripts/write.py \
  "AI tool that reads your mind" --platform tiktok --vibe mindblowing

# 3 variants to pick from
python3 skills/caption-writer/scripts/write.py \
  "cat chef cooking pasta" --platform instagram --vibe funny --variants 3

# With extra context
python3 skills/caption-writer/scripts/write.py \
  "productivity hack" --platform twitter --vibe informative \
  --context "specifically about batching tasks on Sunday night"

# List vibe options
python3 skills/caption-writer/scripts/write.py --list-vibes
```

## Options

| Option | Default | Description |
|--------|---------|-------------|
| `topic` | required | Video topic or description |
| `--platform` | instagram | `instagram`, `tiktok`, `twitter`, `youtube` |
| `--vibe` | relatable | See vibes table below |
| `--variants` | 1 | Number of caption options (1–5) |
| `--context` | — | Extra detail about the video |
| `--json` | false | Output raw JSON |
| `--list-vibes` | — | Print all vibes and exit |

## Platforms

| Platform | Style |
|----------|-------|
| `instagram` | Hook + body + CTA + 5–15 hashtags |
| `tiktok` | Ultra short, lowercase, Gen-Z, 3–6 hashtags |
| `twitter` | Punchy hot take, no hashtags, quotable |
| `youtube` | Keyword-rich, SEO-aware, #Shorts |

## Vibes

| Vibe | Description |
|------|-------------|
| `funny` | Comedic, meme energy, leans into absurdity |
| `mindblowing` | Awe-inspiring, "I didn't know this existed" |
| `relatable` | Everyday struggle, POV format |
| `inspiring` | Motivational, punchy, aspirational |
| `informative` | Educational, value-forward |
| `mysterious` | Cryptic, cliffhanger energy |
| `hype` | Energetic, exclamatory, trending-moment |
| `deadpan` | Dry, ironic, says wild things like obvious facts |

## Example Output

```
────────────────────────────────────────────────────
  Instagram Reels · funny
────────────────────────────────────────────────────

  POV: you trusted the barber 💈

  Kendrick said hold on lemme think about this one 😭
  At least the drip is immaculate fr

  follow for more unhinged content 🫡

  #barbershop #kendricklamar #hairtransformation
  #funny #viral #reels #fyp #comedy
────────────────────────────────────────────────────
```

## Environment

Requires `ANTHROPIC_API_KEY` in `~/.clawdbot/.env` or environment.
