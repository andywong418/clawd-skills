# Kling Prompt Guide

Reference for writing effective Kling video generation prompts. Used by video-director to write shot lists.

---

## Prompt Structure (always this order)

```
[Camera shot + movement] [Subject] [Action] [Environment] [Style/mood]
```

**Optimal length: 30–60 words.** Over 100 words causes contradictions.

**Write like a director, not a keyword list.**
- ✅ "A slow dolly pushes in on a man's face as he reads a letter, candlelit room, soft shadows, cinematic grain"
- ❌ "man, letter, candle, cinematic, 4K, dramatic, shadows, zoom"

---

## Camera Movements

| Term | What it does | Use for |
|------|-------------|---------|
| `slow dolly in` / `push-in` | Camera physically moves closer | Intimacy, tension, reveals |
| `dolly out` / `pull-back` | Camera moves away | Context reveals, distancing |
| `orbit left/right` | Arc around subject | Dramatic reveals, 360 looks |
| `pan left/right` | Camera rotates horizontally | Scanning scenes, following action |
| `tilt up/down` | Camera rotates vertically | Revealing height, looking up/down |
| `tracking shot` | Camera follows subject | Character movement, chase |
| `crane up` | Camera lifts upward | Establishing shots, grand reveals |
| `static` | No camera movement | Subjects doing the moving, stability |
| `handheld` | Subtle natural shake | Documentary, urgency, realism |
| `whip pan` | Fast horizontal sweep | Dynamic transitions, action beats |

**Note:** In Kling, "pan" = horizontal. "Tilt" = vertical. Don't mix them up.

---

## Shot Types

| Shot | Framing | Use for |
|------|---------|---------|
| `wide shot` | Full scene visible | Establishing, context |
| `medium shot` | Waist up | Conversation, character |
| `close-up` | Face / object | Emotion, detail |
| `extreme close-up` | Eyes / hands only | Intense emotion, texture |
| `POV shot` | First-person | Immersion, viewer perspective |
| `over-the-shoulder` | Behind character | Dialogue, confrontation |
| `overhead / bird's eye` | Looking straight down | Patterns, scale |
| `low angle` | Camera below subject | Power, dominance |
| `high angle` | Camera above subject | Vulnerability, surveillance |

---

## Style Keywords That Work

**Cinematic quality:**
`cinematic`, `film grain`, `35mm film`, `shallow depth of field`, `bokeh`, `lens flare`, `anamorphic`

**Lighting:**
`golden hour`, `blue hour`, `soft diffused light`, `dramatic side lighting`, `candlelit`, `neon glow`, `practical lighting`

**Motion:**
`slow motion`, `natural motion blur`, `hyper-smooth`, `subtle movement`

**Mood:**
`moody`, `atmospheric`, `dreamy`, `high contrast`, `muted tones`, `vibrant saturated`

**Avoid:** `cool`, `awesome`, `beautiful`, `amazing` — too vague, ignored by model.

---

## Image-to-Video Rules

When you have a reference image, **only describe what changes** — the scene is already established.

Focus on:
- What moves (subject action)
- Camera movement
- Motion intensity (0.1 = subtle, 0.5 = moderate, 0.9 = dynamic)

Let Kling infer: background, colors, scene context (already in image).

**Example:**
```
Reference: person sitting in barber chair
Prompt: "Subject slowly turns head toward camera and blinks once.
Static high-angle camera. Motion intensity 0.3."
```

---

## Text-to-Video Rules

Include everything — Kling has no reference image to pull from.

**Template:**
```
[Shot type], [subject description], [action], [environment],
[camera movement if any], [lighting], [style]
```

**Example:**
```
"Medium shot, young woman in white lab coat examines glowing vial,
clean futuristic laboratory background, static camera, soft blue
overhead lighting, cinematic, shallow depth of field."
```

---

## Duration Guide

| Duration | Use for | Prompt strategy |
|----------|---------|----------------|
| 5s | Hooks, reactions, simple reveals | One action, one camera move |
| 10s | Full scenes, story beats | One scene with setup + payoff |

Never try to fit multiple scenes in one clip. Generate separate clips and stitch in video-editor.

---

## Negative Prompts (use sparingly)

Only add negatives for things you've seen go wrong:

`blurry, low quality, watermark, text overlay, extra limbs, distorted face, morphing, floating objects, unnatural movement`

---

## Model Guide

| Model | Best for |
|-------|---------|
| `v1.6/pro` | Simple scenes, fast generation |
| `v2/master` | Cinematic work, complex motion, best quality |
| `v2.5/turbo` (if available) | Realistic physics, natural movement |

Default to `v2/master` for all director output.

---

## Common Mistakes

1. **Too many actions in one clip** — pick ONE thing that happens
2. **No camera specified** — always state camera behavior, even if `static`
3. **Contradictory styles** — don't mix `photorealistic` + `cartoon`
4. **Vague motion** — "moves dramatically" tells Kling nothing. Say how.
5. **Ignoring motion intensity for image-to-video** — always set 0.1–0.9

---

## Prompt Templates by Vibe

### Cinematic / Story
```
"[Shot type], [subject], [action verb + how], [environment details],
[camera movement], cinematic lighting, film grain, shallow depth of field."
```

### UGC / Authentic
```
"[Shot type], [subject description], [natural action], [real-world location],
handheld camera, natural lighting, candid iPhone feel, no filters."
```

### Product / Commercial
```
"Static [shot type], [product] [action], clean [color] studio background,
dramatic [side/top] lighting, slow motion, 4K, professional commercial aesthetic."
```

### Viral / Absurdist
```
"[Unexpected subject] doing [normal thing] in [wrong context],
[shot type], [camera move], [contrasting mood], photorealistic,
presented with complete sincerity."
```

### Action / Dynamic
```
"[Shot type] tracking [subject] [fast action], [environment],
handheld camera shake, lens flares, motion blur, [high intensity],
fast-paced, [style]."
```
