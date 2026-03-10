---
name: a-b-hook-tester
description: Generate 3 hook variants in different styles via Claude, log with IDs, mark winners over time to learn what stops the scroll.
---

# A/B Hook Tester

Generate multiple hook variants for any topic, test them in the wild, and track which ones win. Builds a personal knowledge base of what actually works for your audience.

## Quick Start

```bash
# Generate 3 hooks for a topic
python3 skills/a-b-hook-tester/scripts/test_hooks.py "barbershop meme with Kendrick Lamar"

# Generate with a specific account vibe
python3 skills/a-b-hook-tester/scripts/test_hooks.py "morning routine" --vibe "deadpan Gen-Z barber"

# View all tests (newest first)
python3 skills/a-b-hook-tester/scripts/test_hooks.py --log

# Mark a winner after testing in the wild
python3 skills/a-b-hook-tester/scripts/test_hooks.py --winner abc123 --hook 2
```

## Options

| Option | Description |
|--------|-------------|
| `topic` | What the video is about (positional argument) |
| `--vibe` | Account personality/voice (e.g. "deadpan Gen-Z barber") |
| `--log` | List all tests, newest first |
| `--winner TEST_ID` | Mark the winning hook for a test |
| `--hook 1\|2\|3` | Which hook won (required with `--winner`) |

## Output Sample

```
=== HOOK TEST: abc123 ===
Topic: barbershop meme with Kendrick Lamar
Generated: 2026-03-02

[1] UNHINGED
"when you ask for a trim and he plays not like us"
Why: Combines trending audio with meme format — stops scroll instantly

[2] PROVOCATIVE
"this barber knew something we didn't..."
Why: Incomplete thought forces watch-through

[3] RELATABLE-ABSURDISM
"just went to the barber. now i'm kendrick lamar."
Why: Absurd normal→weird structure with viral reference

Run with: --winner abc123 --hook N
```

## Data Storage

All tests stored at `~/.clawdbot/hook-tests/tests.json`.

```json
[
  {
    "id": "abc123",
    "topic": "barbershop meme with Kendrick Lamar",
    "vibe": "deadpan Gen-Z barber",
    "generated": "2026-03-02",
    "hooks": [
      {"index": 1, "style": "unhinged", "text": "...", "rationale": "..."},
      {"index": 2, "style": "provocative", "text": "...", "rationale": "..."},
      {"index": 3, "style": "relatable-absurdism", "text": "...", "rationale": "..."}
    ],
    "winner": 2
  }
]
```

## Environment

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Claude API key |

Set in `~/.clawdbot/.env`:
```
ANTHROPIC_API_KEY=sk-ant-...
```

## Hook Styles

Hooks are selected from these proven viral styles:

| Style | Description | Avg Views |
|-------|-------------|-----------|
| `pure-visual` | No narration — visual speaks for itself | 68M–82M |
| `unhinged` | Absurdist, meme-native, speaks like the internet | 25M–68M |
| `interactive` | Forces participation — questions, tests, challenges | 10M–36M |
| `provocative` | Incomplete thought that demands the viewer watch | 8M–25M |
| `relatable-absurdism` | Normal setup → unexpected weird twist | 5M–20M |
| `trend-hijack` | Riding current audio/meme with brand spin | 10M–30M |
| `confession` | Oversharing creates instant relatability | 5M–10M |
