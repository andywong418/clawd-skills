---
name: seedance-api
description: Log video generation and editing tasks to the Seedance API so they appear in the web dashboard. Use this whenever you create a video, edit content, or run a production task that the user should be able to track.
---

# Seedance API

Track video generation and editing tasks in the shared Seedance platform. Sessions created here are visible in the web app and can be continued from either Slack or web.

## Config

Environment variables (set in ~/.clawdbot/.env):
- `SEEDANCE_API_URL` — API base URL (e.g. https://your-api.up.railway.app)
- `SEEDANCE_WORKSPACE_ID` — Workspace UUID

## When to Use

Use this skill when:
- Generating a video (video_creation)
- Editing content (edit)
- Running research tasks (research)
- Any production task the user should track in the web dashboard

Do NOT use for casual conversation or general questions.

## API Calls

All calls use `curl` via Bash. The helper script handles the base URL and workspace ID.

### 1. Create a Session

Call this at the START of a video/editing task:

```bash
bash skills/seedance-api/scripts/api.sh create-session \
  --title Short description of the task \
  --type video_creation \
  --channel-id  \
  --thread-id 
```

Types: `video_creation`, `edit`, `research`, `meme_remix`, `ugc_creation`, `general`

Returns JSON with the session `id`. Save it for subsequent event logging.

### 2. Log Events

Log events as the task progresses:

```bash
# User message
bash skills/seedance-api/scripts/api.sh add-event SESSION_ID \
  --type message --role user --content the user prompt

# Assistant message
bash skills/seedance-api/scripts/api.sh add-event SESSION_ID \
  --type message --role assistant --content your response

# Generation started
bash skills/seedance-api/scripts/api.sh add-event SESSION_ID \
  --type generation_started --content Generating video for: prompt

# Generation completed (include the video URL)
bash skills/seedance-api/scripts/api.sh add-event SESSION_ID \
  --type generation_completed --content https://video-url.mp4

# Generation failed
bash skills/seedance-api/scripts/api.sh add-event SESSION_ID \
  --type generation_failed --content Error message
```

### 3. Get Web Link

After creating a session, the response includes a `webUrl` field. Share this in Slack so the user can view the session in the web dashboard.

## Typical Flow

1. User asks to generate a video in Slack
2. Create a session → get session ID and webUrl
3. Log the user message event
4. Start video generation, log generation_started
5. Share webUrl in Slack: "Track this at: {webUrl}"
6. When generation completes, log generation_completed with the video URL
7. Share the result in Slack
