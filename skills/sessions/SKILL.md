---
name: sessions
description: Persistent creative workflow tracking via the viralfarm-server Sessions API. Use to maintain context across long Slack threads, log creative pipeline events, and recover state after context loss. Sessions are the bot's memory — invisible to users.
---

# Sessions

Sessions are persistent, structured records of creative tasks stored in the viralfarm-server database. Each Slack thread maps to a session. The bot reads/writes session events via API instead of relying on Slack thread history.

Sessions are invisible to users — they're the bot's persistent memory.

## When to Create a Session

**DO create** when:
- User starts a creative task (video creation, meme, UGC, script)
- A scheduled/cron job begins execution
- User kicks off a multi-step request (viral hunt, research pipeline)
- A skill is invoked that will produce assets (barber-meme, fal-video, ugc-creator)

**DO NOT create** when:
- Simple question or one-off command ("what time is it?", "list my posts")
- Casual chat or greetings
- Quick lookups that don't produce artifacts

## Slack Thread Flow

1. Message arrives with `thread_ts` → look up session via `GET /sessions/lookup`
2. Session exists → load events for context recovery
3. No session → create one if this is a creative task
4. Log user messages, bot actions, generations, assets, approvals as events
5. Close session (status → `completed`) when work finishes

## API Reference

**Base URL:** `$VIRALFARM_API_URL` (from `~/.clawdbot/.env`)

### Lookup Session (the critical bot path)

```bash
curl "$VIRALFARM_API_URL/sessions/lookup?platform=slack&platformChannelId=$CHANNEL&platformThreadId=$THREAD_TS"
```

Returns 404 if no session exists for this thread. Create one if needed.

### Create Session

```bash
curl -X POST "$VIRALFARM_API_URL/sessions" \
  -H "Content-Type: application/json" \
  -d '{
    "workspaceId": "...",
    "title": "Barbershop meme: Elon Musk",
    "type": "video_creation",
    "platform": "slack",
    "platformChannelId": "C123",
    "platformThreadId": "1712023032.1234"
  }'
```

**Session types:** `video_creation`, `viral_hunt`, `research`, `edit`, `meme_remix`, `ugc_creation`, `general`

### Add Event

```bash
curl -X POST "$VIRALFARM_API_URL/sessions/$SESSION_ID/events" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "generation_started",
    "content": "Generating base image with Imagen",
    "metadata": {"provider": "google-imagen", "model": "imagen-4.0-ultra-generate-001"}
  }'
```

**Event types and when to log them:**

| Event Type | When | Example metadata |
|------------|------|------------------|
| `message` | User or bot sends a message | `role: "user"` or `role: "assistant"` |
| `skill_invoked` | A skill starts | `skillName: "barber-meme"` |
| `generation_started` | Image/video gen begins | `provider`, `model`, `prompt` |
| `generation_completed` | Gen succeeds | `assetUrl`, `provider`, `duration` |
| `generation_failed` | Gen fails | `errorCode`, `provider`, `error` |
| `asset_created` | Final asset produced | `assetUrl`, `assetType: "video"` |
| `approval_requested` | Asking user to approve | `question` |
| `approved` | User approves | `approvedBy` |
| `rejected` | User rejects | `rejectedBy`, `reason` |
| `error` | Something broke | `errorCode`, `message` |
| `status_change` | Session status changes | `from: "active"`, `to: "completed"` |
| `system` | Auto-generated insights | `insights`, `summary` |

### Get Session with Events

```bash
curl "$VIRALFARM_API_URL/sessions/$SESSION_ID?includeEvents=true&eventLimit=100"
```

### Update Session

```bash
curl -X PATCH "$VIRALFARM_API_URL/sessions/$SESSION_ID" \
  -H "Content-Type: application/json" \
  -d '{"status": "completed", "summary": "Created barbershop meme of Elon Musk"}'
```

### Get Messages Only

```bash
curl "$VIRALFARM_API_URL/sessions/$SESSION_ID/messages"
```

## Context Recovery

When a thread has many messages and context is getting long, use session events instead of re-reading the entire Slack thread:

1. Look up session by thread
2. Load events — they contain: all messages, what was generated, what failed, what assets exist, current status
3. Use event timeline to reconstruct what happened without reading Slack history

This is the primary value of sessions — they're a structured, queryable alternative to raw thread history.

## Session Insights (on completion)

When closing a session, generate a summary and learnings:

```bash
curl -X PATCH "$VIRALFARM_API_URL/sessions/$SESSION_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "completed",
    "summary": "Created barbershop meme of Elon Musk. Imagen → Kling pipeline. 7 generations total.",
    "insights": "First draft approved — no revisions needed. Imagen base image quality was high. Kling 2.5 turbo clips rendered in ~45s each."
  }'
```

**What to include in insights:**
- What worked well
- What failed and why
- Pipeline stats (generation count, time, revisions)
- Improved prompt suggestions for next time

## Parent-Child Sessions

For workflows that spawn sub-tasks (e.g., viral-hunt finds 5 reels → each reel's video creation is a child session):

```bash
curl -X POST "$VIRALFARM_API_URL/sessions" \
  -H "Content-Type: application/json" \
  -d '{
    "workspaceId": "...",
    "parentSessionId": "parent-session-uuid",
    "title": "Reel remix: @realskytan #42",
    "type": "meme_remix"
  }'
```

List children: `GET /sessions?workspaceId=...&parentSessionId=parent-uuid`

## Scheduled Sessions

Users can say "run viral hunt every 4 hours" or "create a fitness reel every Monday at 9am". The bot creates a schedule:

```bash
curl -X POST "$VIRALFARM_API_URL/schedules" \
  -H "Content-Type: application/json" \
  -d '{
    "workspaceId": "...",
    "title": "Daily viral hunt",
    "prompt": "Scan top AI video accounts for reels with 1M+ views in last 24h",
    "sessionType": "viral_hunt",
    "cronExpression": "0 */4 * * *",
    "metadata": {"skillsToInvoke": ["viral-hunt"]}
  }'
```

**Schedule management:**
- Pause: `PATCH /schedules/:id` with `{"status": "paused"}`
- Resume: `PATCH /schedules/:id` with `{"status": "active"}`
- Run now: `POST /schedules/:id/run`
- Delete: `DELETE /schedules/:id`
- List: `GET /schedules?workspaceId=...`

Each scheduled run creates a session with `metadata.scheduleId` linking back to the schedule.

## Example Session Lifecycle (Barbershop Meme)

```
 1. [message]              role:user      "make me a barbershop meme of Elon Musk"
 2. [skill_invoked]        -              skill:barber-meme
 3. [generation_started]   -              provider:google-imagen
 4. [message]              role:assistant "Starting on Elon's barbershop meme!"
 5. [generation_completed] -              assetUrl:.../base.png
 6. [generation_started]   -              provider:fal-video (clips 1-5)
 7. [generation_completed] -              assetUrl:.../clip1.mp4 ... clip5.mp4
 8. [asset_created]        -              assetUrl:.../final.mp4
 9. [message]              role:assistant "Here's your barbershop meme! [video]"
10. [approval_requested]   -              "Does this look good?"
11. [message]              role:user      "perfect, post it"
12. [approved]             -              approvedBy:andros
13. [system]               -              insights: "Completed in 7 gens. No revisions."
14. [status_change]        -              active → completed
```

## Helper Script

Use `skills/sessions/scripts/session.sh` for quick session operations from the command line. See script for usage.

## Files

| File | Purpose |
|------|---------|
| `skills/sessions/SKILL.md` | This file — session usage guide |
| `skills/sessions/scripts/session.sh` | Shell helper for session API operations |
