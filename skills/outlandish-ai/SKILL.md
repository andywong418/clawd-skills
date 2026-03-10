---
name: outlandish-ai
description: Generate outlandish, unhinged AI animated video concepts. Absurdist fever dream content designed for viral sharing. Use when asked for weird, surreal, cursed, or outlandish video ideas for AI generation.
---

# Outlandish AI Content Generator

Generate viral-ready concepts for AI-animated video content. Absurdist, surreal, unhinged.

## Content Philosophy

**Core principle:** Make people stop scrolling and ask "what did I just watch?"

### What Works:
- **Absurdist juxtaposition** — Normal situation + completely wrong element
- **Uncanny valley** — Almost normal but deeply off
- **Confident nonsense** — Presented with total sincerity
- **Visual chaos** — Overwhelming but hypnotic
- **Anti-humor** — So unfunny it loops back to funny

### Formats:
1. **Corporate Fever Dream** — Business/corporate aesthetic + completely unhinged content
2. **Renaissance Shitpost** — Classical art doing modern absurd things
3. **Nature Documentary Gone Wrong** — David Attenborough energy for nonsense
4. **Motivational Nightmare** — Inspirational format with cursed message
5. **POV Chaos** — First-person perspective of increasingly weird situation

## Output Format

Each concept should include:
```
CONCEPT: [Title]
VIBE: [1-3 word mood]
VISUAL: [What AI should generate - be specific for Imagen/Kling]
TEXT OVERLAY: [On-screen text if any]
AUDIO: [Sound design notes]
WHY IT WORKS: [Viral mechanic]
```

## Generation Guidelines

- Keep videos 5-15 seconds
- Hook in first frame (thumbnail must intrigue)
- No context needed — should work with zero explanation
- Slightly unsettling > conventionally beautiful
- Confidence is key — commit to the bit
- Loop-friendly when possible

## Production Pipeline

1. Generate concept (this skill)
2. Create key frame with Google Imagen (`skills/google-imagen`)
3. Animate with Kling via fal.ai (`skills/fal-video`)
4. Add text overlays (CapCut/editing)
5. Post

## Example Concepts

**CONCEPT:** Quarterly Breath Report
**VIBE:** Corporate dread
**VISUAL:** AI businessman in pristine suit, aggressively inhaling in slow motion. Boardroom full of realistic fish in suits watching attentively. Glass table, fluorescent lighting.
**TEXT OVERLAY:** "quarterly breath report exceeded expectations by 340%"
**AUDIO:** Muffled corporate muzak, one loud inhale
**WHY IT WORKS:** Absurdist corporate satire, unexpected fish, confident nonsense

**CONCEPT:** The Last Brain Cell
**VIBE:** Existential chaos
**VISUAL:** Single glowing orb floating in vast empty void. Increasingly chaotic colorful swirls approaching from all sides. Orb remains calm.
**TEXT OVERLAY:** "pov: you're my last brain cell during the meeting"
**AUDIO:** Elevator music, progressively more distorted
**WHY IT WORKS:** Relatable setup, hypnotic visuals, meme format

**CONCEPT:** WiFi Renaissance
**VIBE:** Unhinged joy
**VISUAL:** Classical renaissance painting of nobles in a gallery. One painting (Mona Lisa style) suddenly starts doing modern dance moves. Other paintings remain frozen. Museum visitors walk by normally.
**TEXT OVERLAY:** "when the wifi reconnects"
**AUDIO:** Silent → sudden trap beat drop
**WHY IT WORKS:** Unexpected animation, relatable trigger, contrast humor
