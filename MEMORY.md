
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

clawdbot-setup templates also updated to use Agent SDK pattern.

## Bot Infrastructure

| Bot | App ID | Server | IP | Notes |
|-----|--------|--------|----|-------|
| Naruto (me) | A0AHMHKE0Q6 | clawdbot-1 | 143.198.96.99 | 2GB RAM, browser on :18800 |
| viralfarmbot | A0AJ549031P | openclaw-2 | 24.199.102.212 | browser on :9223 (socat proxy) |
| alphawhalebot | A0AHSBCJU3X | alphawhalebot | 167.71.171.101 | Alpha Whale Intern app |

All bots run Agent SDK on their respective servers.

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
- Remote: `git@github.com:andywong418/clawd-skills.git`
- Git identity: `clawdbot@wonderverse.xyz`

## Runtime

- **Bun** is the package manager/runtime (bun.lock in project root)

## Skills Created

- **cloud-browser** — spin up DigitalOcean droplets with persistent browsers
  - Chrome ignores `--remote-debugging-address=0.0.0.0` in newer versions — use socat proxy on :9223 → localhost:9222
- **clawdbot-setup** — templates for new Clawdbot instances (SOUL.md, AGENTS.md, BOOTSTRAP.md, USER.md, TOOLS.md, IDENTITY.md, HEARTBEAT.md)
  - Recommended skills to install on new instances: OpenCortex (memory), SIAS (WAL protocol), memU (proactive), Vigil (safety guardrails)
- **supermemory** — scripts: get-context.sh, add-memory.sh, get-profile.sh
- **seedance-api** — log video/content production tasks for tracking in web dashboard
  - `SEEDANCE_API_URL` + `SEEDANCE_WORKSPACE_ID` in ~/.clawdbot/.env
  - Flow: create-session → get webUrl → log events → share webUrl in Slack
  - Types: video_creation, edit, research, meme_remix, ugc_creation, general

## Clawdbot Setup Lessons (Critical Gotchas)

1. **Enable lingering** — `loginctl enable-linger root` is REQUIRED or gateway dies on SSH session changes
2. **API key location conflicts** — systemd Environment, config.yaml, auth-profiles.json, .env can all have different keys. Check ALL.
3. **Slack @mentions need `app_mention` event** — not just DM events
4. **Reinstall app after scope changes** — OAuth flow required, reinstall from scratch
5. **GitHub deploy keys are unique per repo** — cannot reuse across repos
6. **Slack file access** — bots get Slack login page instead of files if `files:read`/`files:write` scopes are missing

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
