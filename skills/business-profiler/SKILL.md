---
name: business-profiler
description: Analyze a business website to extract target market, offering, use cases, and brand persona. Use when asked to research a company, understand a business, profile a brand, or prepare for content creation for a client. Outputs structured markdown for content strategy.
---

# Business Profiler

Research and profile a business from their website to inform content strategy.

## Usage

```bash
# Profile a business
python3 skills/business-profiler/scripts/profile.py https://example.com

# With custom output location
python3 skills/business-profiler/scripts/profile.py https://example.com --output ~/clawd/clients/example/
```

## What It Extracts

1. **Company Overview** — What they do, founding story, mission
2. **Target Market** — Who they serve (demographics, psychographics, B2B/B2C)
3. **Offering** — Products/services, pricing tiers, key features
4. **Use Cases** — How customers use it, problems solved
5. **Brand Persona** — Voice, tone, visual style, personality
6. **Content Angles** — Suggested hooks/themes based on their niche
7. **Competitors** — If mentioned or obvious

## Output

Saves to `{output}/BUSINESS_PROFILE.md` with structured sections.

## Workflow

1. Fetches homepage, about, product/pricing pages
2. Analyzes content for key business attributes
3. Generates structured markdown profile
4. Profile can be referenced by viral-ideation job for niche-specific content

## Integration with Video Ideation

After profiling, update the ideation cron job or run manually:
```
"Generate viral video ideas for [BUSINESS] using their profile at clients/[name]/BUSINESS_PROFILE.md"
```
