---
name: slack-bot-setup
description: Create a new Slack bot app with full DM and messaging capabilities. Use when setting up a Slack bot that can send DMs, read messages, list users, or integrate with a workspace. Covers app creation, OAuth scopes, Socket Mode setup, and token retrieval via browser automation.
---

# Slack Bot Setup

Create a fully-configured Slack bot with DM capabilities in one shot.

## Prerequisites

- Browser automation available (Clawdbot browser or Chrome)
- Logged into Slack workspace at api.slack.com

## Quick Setup Flow

### 1. Create the App

Navigate to `https://api.slack.com/apps` and click "Create New App" → "From scratch".

- **App Name**: Choose a descriptive name (e.g., `mybot`)
- **Workspace**: Select target workspace

### 2. Add Bot Scopes (OAuth & Permissions)

Go to **OAuth & Permissions** in the sidebar. Under **Bot Token Scopes**, add:

| Scope | Purpose |
|-------|---------|
| `im:write` | Open DM conversations with users |
| `im:history` | Read DM message history |
| `chat:write` | Send messages |
| `channels:read` | List public channels |
| `channels:history` | Read channel messages |
| `users:read` | List workspace members |

**Optional scopes** (add as needed):
- `users:read.email` - Get user email addresses
- `chat:write.public` - Post to channels without joining
- `reactions:write` - Add emoji reactions
- `files:write` - Upload files

### 3. Enable Socket Mode (for real-time events)

Go to **Socket Mode** in sidebar:
1. Toggle **Enable Socket Mode** ON
2. Generate an **App-Level Token** with `connections:write` scope
3. Name it (e.g., `socket-token`)
4. Copy the `xapp-...` token

### 4. Subscribe to Events

Go to **Event Subscriptions**:
1. Toggle **Enable Events** ON
2. Under **Subscribe to bot events**, add:
   - `message.im` - DM messages to the bot
   - `message.channels` - Channel messages (if needed)
   - `app_mention` - When bot is @mentioned

### 5. Install to Workspace

Go to **Install App** in sidebar:
1. Click **Install to Workspace**
2. Review permissions and click **Allow**
3. Copy the **Bot User OAuth Token** (`xoxb-...`)

### 6. Reinstall After Scope Changes

After adding new scopes, you MUST reinstall:
1. Go to **OAuth & Permissions**
2. Click **Reinstall to [Workspace]**
3. Approve the updated permissions

## Token Reference

| Token Type | Format | Purpose |
|------------|--------|---------|
| Bot Token | `xoxb-...` | API calls (send messages, list users) |
| App Token | `xapp-...` | Socket Mode connection |

## Test the Bot

```bash
# Verify token works
curl -s -X POST https://slack.com/api/auth.test \
  -H "Authorization: Bearer xoxb-YOUR-TOKEN" | jq .

# List users
curl -s "https://slack.com/api/users.list?limit=10" \
  -H "Authorization: Bearer xoxb-YOUR-TOKEN" | jq '.members[] | {name, id}'

# Open DM with a user
curl -s -X POST https://slack.com/api/conversations.open \
  -H "Authorization: Bearer xoxb-YOUR-TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"users": "USER_ID"}' | jq .

# Send a DM
curl -s -X POST https://slack.com/api/chat.postMessage \
  -H "Authorization: Bearer xoxb-YOUR-TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"channel": "CHANNEL_ID", "text": "Hello!"}' | jq .
```

## Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `missing_scope` | Scope not added or app not reinstalled | Add scope + reinstall app |
| `channel_not_found` | Invalid channel/DM ID | Use `conversations.open` first |
| `not_in_channel` | Bot not in channel | Add `channels:join` scope or invite bot |
| `user_not_found` | Invalid user ID | Check ID with `users.list` |

## Browser Automation Tips

When automating setup via browser:

1. **Scope picker**: Click "Add an OAuth Scope", type scope name, click the option
2. **Reinstall flow**: Navigate directly to the OAuth URL shown in "Reinstall to Workspace" link
3. **Allow button**: After reinstall navigation, click the "Allow" button on the OAuth page
4. **Session persistence**: Use a persistent browser profile to stay logged in

## Clawdbot Integration

To use the bot with Clawdbot, update gateway config:

```json
{
  "channels": {
    "slack": {
      "enabled": true,
      "mode": "socket",
      "botToken": "xoxb-...",
      "appToken": "xapp-..."
    }
  }
}
```

Then restart: `gateway restart`
