
<!-- Last distilled: 2026-03-11 (scheduled maintenance) from daily files + git commits through 8c99f53 -->

## Context Recovery
When losing context:
1. Check the current message thread
2. Check past message interactions with the user
3. Read memory/YYYY-MM-DD.md files
4. Use message tool to read recent history if needed

## Architecture: Agent SDK (Current)

Migrated from clawdbot gateway → **Bun + Claude Agent SDK** (commit `3a764fb`, 2026-03-03):
- Multi-session agent pooling with warm starts (`src/agent-session-pool.ts`)
- Real-time Slack streaming UX: thinking → streaming → final
- MCP Slack tools: send, react, upload, read thread/channel
- Concurrency: max 3 concurrent queries
- Sessions stored locally in `memory/sessions/` (not API)
- Cron via `schedules.json`, defaults to memory maintenance
- Config via `CLAUDE.md` as primary (settingSources: `['project']`)
- **Auto-reads thread context** when bot is tagged in a thread (commit `7b8631b`)
- **No budget limits** on any bot — removed from all bots and templates (commit `b5f1521`)
- **Stuck timer** — posts user warning after `BOT_STUCK_THRESHOLD_MS` (default 5min) if still thinking; clears on completion/error (commit `src/adapters/slack.ts`)
- **Force-close on hard timeout** — `cancelAgentSession(key)` / `pool.forceCloseSession(key)` in `src/agent.ts` + `src/agent-session-pool.ts`; extends stuck handling beyond warning to actually killing the session
- **file_share subtype** allowed through message handler (commit `34ac26e`)
- **Auto-memory capture** — saves session summary to daily memory on session close, compaction, and shutdown (commit `d6cadfc`)
- **SESSION-STATE.md** — created at session start, updated every ~10 tool calls and before major responses; survives context compaction + session restarts (commit `8c99f53`)
- **BOT_MAX_TURNS fix** — dotenv now loaded BEFORE module imports in `src/index.ts`; `agent.ts` uses `getConfig()` at runtime instead of reading env at import time (commit `c99febd`)

clawdbot-setup templates also updated to use Agent SDK pattern.

## Bot Infrastructure

| Bot | App ID | Server | IP | Notes |
|-----|--------|--------|----|-------|
| Naruto (me) | A0AHMHKE0Q6 | clawdbot-1 | 143.198.96.99 | 2GB RAM, browser on :18800 |
| viralfarmbot | A0AJ549031P | openclaw-2 | 24.199.102.212 | browser on :9223 (socat proxy) |
| alphawhalebot | A0AHSBCJU3X | alphawhalebot | 167.71.171.101 | Alpha Whale Intern app |

All bots run Agent SDK on their respective servers.

**openclaw-2 WARP safety:** `warp-svc` (Cloudflare WARP) is installed and hijacks networking on boot. **Before any reboot/resize/power cycle:** `sudo systemctl disable warp-svc` first, then reboot, then verify SSH. Skipping this makes the droplet completely unreachable (no SSH, no DO console).

**Slack scopes on all bots:** `app_mentions:read, channels:history, channels:read, chat:write, files:read, files:write, im:history, im:write, users:read`

## Credentials & Config Locations
- API keys: `~/.clawdbot/.env` (ANTHROPIC_API_KEY, OPENAI_API_KEY, SUPERMEMORY_API_KEY, DATABASE_URL, SUPERMEMORY_BOT_ID)
- Slack tokens: `~/.clawdbot/clawdbot.json`
- Browser cookies: `~/.clawdbot/cookies/`
- SSH keys: standard locations, clawdbot-1 key added to DigitalOcean (fingerprint: eb:77:46:d7:c2:32:4f:b0:f4:59:df:3b:57:e3:61:54)
- DATABASE_URL is set on viralfarmbot and alphawhalebot (they have DB access)

**ALWAYS check `~/.clawdbot/.env`, `TOOLS.md`, and `memory/*.md` before asking Andros for credentials.**

## Memory & Intelligence Stack

All 3 bots have:
- **Vector memory search** via OpenAI text-embedding-3-small (hybrid: 70% vector, 30% keyword)
- **Supermemory** integration — skill at `/root/clawd/skills/supermemory/` with per-bot container tags (`naruto`, `viralfarmbot`, `alphawhalebot`)
- Session transcript indexing enabled

## Git Setup
- Workspace: `~/clawd`
- Remote: `git@github.com:andywong418/clawd-skills.git` (personal skill workspace)
- Shared public skills pulled from: `https://github.com/wondrous-dev/clawd-skills`
- Git identity: `clawdbot@wonderverse.xyz`

## Runtime

- **Bun** is the package manager/runtime (bun.lock in project root)

## Skills

Skills auto-update via heartbeat cron from `https://github.com/wondrous-dev/clawd-skills` (symlinked into `skills/`). Full manifest at `skills/.manifest.json`. Update script: `bash /root/clawd/scripts/update-skills.sh`.

**Infra / Setup:**
- **cloud-browser** — spin up DigitalOcean droplets with persistent browsers
  - Chrome ignores `--remote-debugging-address=0.0.0.0` — use socat proxy on :9223 → localhost:9222
- **clawdbot-setup** — templates for new Clawdbot instances (SOUL.md, AGENTS.md, BOOTSTRAP.md, USER.md, TOOLS.md, IDENTITY.md, HEARTBEAT.md)
  - Recommended skills for new instances:
    - **OpenCortex** (`JD2005L/opencortex`) — memory architecture, nightly distillation, encrypted vault
    - **SIAS** (`iggyswelt/SIAS`) — WAL protocol, .learnings/ folder, promotion system
    - **memU** (`NevaMind-AI/memU`) — memory-as-filesystem, intention capture, 24/7 agents
    - **Vigil** (`hexitlabs/vigil`) — <2ms guardrails, blocks destructive commands/exfiltration/SSRF
- **supermemory** — scripts: get-context.sh, add-memory.sh, get-profile.sh
- **sessions** — persistent workflow tracking via Sessions API; log pipeline events and recover state
- **slack** — control Slack from bot (react, pin, etc.)
- **seedance-api** — log video/content production tasks for tracking in web dashboard
  - `SEEDANCE_API_URL` + `SEEDANCE_WORKSPACE_ID` in ~/.clawdbot/.env
  - Flow: create-session → get webUrl → log events → share webUrl in Slack
  - Types: video_creation, edit, research, meme_remix, ugc_creation, general

**Content / Captions / Branding:**
- **brand-trainer** — train/manage brand voice via ViralFarm API; requires `VIRALFARM_API_URL`, `VIRALFARM_API_KEY`
- **caption-writer** — platform-optimized captions (IG, TikTok, Twitter, YouTube) via Claude
- **a-b-hook-tester** — generate 3 hook variants, track winners over time
- **business-profiler** — analyze a business website → structured content strategy
- **aeo** — Answer Engine Optimization; get viralfarmbot cited by Claude/ChatGPT/Perplexity
- **viral-templates** — proven viral video templates with AI generation prompts
- **outlandish-ai** — absurdist/unhinged viral video concepts
- **appstore-spy** — track competitor apps on the App Store; monitor rankings, subtitles, ratings, review velocity; spot rising competitors early
- **influencer-cpm-tracker** — track influencer deal CPMs, flag anything over $1K CPM, maintain deal DB; auto-flags overpays, weekly spend reports

**Video Production Pipeline:**
- **produce** — end-to-end pipeline: topic → script → voiceover → b-roll → assembled video → posted
- **video-director** — text concept → shot list → Kling clips → assembled video + caption
- **video-gen** — generate via ViralFarm API (Kling, Runway, Sora, Seedance, MagicHour); preferred over fal-video (credit tracking)
- **fal-video** — generate via fal.ai directly (Kling); requires `FAL_API_KEY`
- **voiceover** — TTS audio via fal.ai: Kokoro (fast, 50+ voices) or MiniMax Speech-02 HD (quality)
- **b-roll-finder** — find/download royalty-free b-roll from Pexels; requires `PEXELS_API_KEY`
- **video-assembler** — stitch clips + audio (voiceover + music) into final MP4 via ffmpeg
- **video-editor** — ffmpeg editing: concat, audio mix, fade, text overlays, crop
- **subtitle-burner** — transcribe + burn TikTok-style captions via fal.ai Whisper + ffmpeg
- **cross-poster** — reformat video for TikTok/IG Reels/YouTube Shorts in one shot
- **thumbnail-generator** — generate A/B thumbnail variants with text overlays
- **thumbnail-analyzer** — score thumbnails for CTR via Claude vision
- **ugc-creator** — AI UGC creator images (Google Imagen) + animated with Kling
- **google-imagen** — generate images via Google Imagen/Gemini; requires `GOOGLE_AI_API_KEY`
- **meme-remix** — (see skill for docs)
- **clipper** — download videos, transcribe, detect viral moments, cut clips with subtitles

**TikTok / Account Growth:**
- **warmup-trainer** — account warmup: scheduled engagement sessions, 3-phase progression
- **comment-responder** — auto-reply to TikTok comments via Claude; shares storage with warmup-trainer
- **follow-manager** — strategic follow/unfollow automation (commenters, hashtag engagers, target followers)
- **daily-grind** — full daily TikTok engagement loop: warmup → replies → follow → unfollow
- **tiktok-downloader** — download TikTok videos without watermark; enables repurposing pipeline
- **post-scheduler** — queue and schedule posts to TikTok/IG/YouTube at optimal times
- **performance-tracker** — pull analytics from TikTok/IG/Twitter/YouTube → Claude analysis
- **twitter** — fetch tweets/user info via X API; requires Twitter API credentials
- **viral-hunt** — (see skill for docs)
- **ugc-tracker** — track UGC creator performance; manage roster, monitor views, calculate base pay + performance bonuses ($15/video + 100K/250K/500K/1M tiers)
- **viral-format-cloner** — watch posted content for viral hits (100K+ IG / 500K+ TikTok), auto-generate 3 hook variations to multiply viral content

**Key API Credentials for Skills:** `FAL_API_KEY`, `PEXELS_API_KEY`, `GOOGLE_AI_API_KEY`, `VIRALFARM_API_URL`, `VIRALFARM_API_KEY` — check `~/.clawdbot/.env`

## Clawdbot Setup Lessons (Critical Gotchas)

1. **Enable lingering** — `loginctl enable-linger root` is REQUIRED or gateway dies on SSH session changes
2. **API key location conflicts** — systemd Environment, config.yaml, auth-profiles.json, .env can all have different keys. Check ALL.
3. **Slack @mentions need `app_mention` event** — not just DM events
4. **Reinstall app after scope changes** — OAuth flow required, reinstall from scratch
5. **GitHub deploy keys are unique per repo** — cannot reuse across repos
6. **Slack file access** — bots get Slack login page instead of files if `files:read`/`files:write` scopes are missing
   - viralfarmbot needs `files:read`; alphawhalebot needs both `files:read` and `files:write`
7. **Slack file download timeout** — set 15s timeout on file downloads or sessions can freeze indefinitely (commit `9117826`)

## Protocols Adopted (from SantaClawd)

- **WAL Protocol** — write-ahead logging for corrections, proper nouns, decisions, values
- **Working Buffer** — maintain `memory/working-buffer.md` at 60% context for recovery
- **Interoceptive State** — track memory health in `memory/interoceptive-state.json`
- **The Covenant** — cross-session responsibility: "What do I owe the person who wakes up next?"

## Projects Context

- **AlphaWhale** — prediction markets / copy-trading product on Polymarket (app.alphawhale.trade)
- **Wonderverse** — Andros's company, andros@wonderverse.xyz
- **fantasy-market** — GitHub repo, deploy key needed on alphawhalebot server

## Ethical Boundaries

- Declined mass DM outreach to Telegram group members (spam, regardless of rate limiting)
- Declined infrastructure for other agents to do the same
- Line: unsolicited promotional messages = off-limits

## Browser / Chrome Notes

- **NEVER** `pkill chrome` or `killall chrome` — run `/usr/local/bin/cleanup-chrome.sh` instead
- cleanup-chrome.sh configured for 2GB servers: max renderer age 5min, max renderers 3, cron every 2min
- Browser retry protocol: timeout → cleanup + retry → gateway restart + retry → check `free -h` → ask
