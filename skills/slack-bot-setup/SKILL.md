---
name: slack-bot-setup
description: Create a new Slack bot app with full DM and messaging capabilities. Use when setting up a Slack bot that can send DMs, read messages, list users, or integrate with a workspace. Covers app creation, OAuth scopes, Socket Mode setup, and token retrieval via browser automation.
---

# Slack Bot Setup

Create a fully-configured Slack bot with DM and thread mention capabilities via browser automation.

## Browser Automation Flow

### 1. Start Browser & Login Check

```
browser action=start profile=clawd
browser action=navigate targetUrl="https://api.slack.com/apps"
browser action=snapshot
```

If not logged in, navigate to workspace signin first.

### 2. Create New App

```
browser action=navigate targetUrl="https://api.slack.com/apps"
browser action=snapshot
# Click "Create New App" button
# Click "From scratch" option
# Fill app name in textbox
# Select workspace from dropdown  
# Click "Create App" button
```

### 3. Add Bot Scopes

Navigate to OAuth & Permissions:
```
browser action=navigate targetUrl="https://api.slack.com/apps/APP_ID/oauth"
```

For each scope, repeat:
1. Click "Add an OAuth Scope" button
2. Type scope name in the combobox (e.g., `im:write`)
3. Click the matching option in dropdown

**Required scopes for DM and thread mention bot:**
- `im:write` - Open DM conversations
- `im:history` - Read DM history  
- `chat:write` - Send messages
- `channels:read` - List channels
- `channels:history` - Read channel messages
- `users:read` - List workspace members
- `app_mentions:read` - **REQUIRED for @mention responses in threads**

**Optional but recommended scopes:**
- `groups:read` - Private channel info
- `groups:history` - Private channel messages
- `mpim:read` - Group DM info
- `mpim:history` - Group DM messages
- `reactions:read` - Read reactions
- `reactions:write` - Add reactions
- `pins:read` - Read pins
- `pins:write` - Add pins
- `files:read` - Read file info
- `files:write` - Upload files

### 4. Enable Socket Mode

```
browser action=navigate targetUrl="https://app.slack.com/app-settings/TEAM_ID/APP_ID/socket-mode"
```

1. Toggle "Enable Socket Mode" ON (switch element)
2. A modal may appear to generate a token

**Generate App-Level Token:**
```
browser action=navigate targetUrl="https://api.slack.com/apps/APP_ID/general"
```

1. Scroll to "App-Level Tokens" section
2. Click "Generate Token and Scopes" button
3. Enter a token name (e.g., "socket-token")
4. Click "Add Scope" and select `connections:write`
5. Click "Generate"
6. **Copy the `xapp-...` token from the modal**

### 5. Subscribe to Events (CRITICAL)

```
browser action=navigate targetUrl="https://api.slack.com/apps/APP_ID/event-subscriptions"
```

1. Toggle "Enable Events" ON (if not already enabled by Socket Mode)
2. Click to expand "Subscribe to bot events" section
3. Add these events:

**Required events for DMs and thread mentions:**

| Event | Description | Required Scope |
|-------|-------------|----------------|
| `message.im` | DM messages | `im:history` |
| `app_mention` | @mentions in channels/threads | `app_mentions:read` |

**Optional events for full functionality:**

| Event | Description | Required Scope |
|-------|-------------|----------------|
| `message.channels` | Public channel messages | `channels:history` |
| `message.groups` | Private channel messages | `groups:history` |
| `message.mpim` | Group DM messages | `mpim:history` |
| `reaction_added` | Reaction notifications | `reactions:read` |
| `reaction_removed` | Reaction removal notifications | `reactions:read` |
| `member_joined_channel` | User joins channel | `channels:read` |
| `member_left_channel` | User leaves channel | `channels:read` |

For each event:
1. Click "Add Bot User Event" button
2. Type event name in dropdown
3. Click to select

4. Click "Save Changes" at bottom of page

### 6. Enable App Home (for DMs)

```
browser action=navigate targetUrl="https://api.slack.com/apps/APP_ID/app-home"
```

1. Find "Messages Tab" section
2. Toggle ON "Allow users to send Slash commands and messages from the messages tab"

This enables DM functionality with the bot.

### 7. Enable Agent Mode (Optional but Recommended)

Agent mode gives your bot a top-bar entry point and side-by-side view in Slack.

```
browser action=navigate targetUrl="https://api.slack.com/apps/APP_ID/app-assistant"
```

1. Find "Agent or Assistant" section
2. Toggle ON "Mark this app as an agent app" (switch element)
3. Optionally fill in "Agent or Assistant Overview" description
4. Optionally configure "Suggested Prompts" (Dynamic or Fixed)
5. A banner will appear saying reinstall is required
6. Click "reinstall your app" link and click "Allow"

**This adds the `assistant:write` scope automatically.**

Benefits of Agent mode:
- Bot appears in Slack's top bar for quick access
- Side-by-side conversation view
- Chat and History tabs replace the messages tab
- Better UX for AI assistant interactions

### 8. Install to Workspace

```
browser action=navigate targetUrl="https://api.slack.com/apps/APP_ID/install-on-team"
```

1. Click "Install to Workspace" 
2. On OAuth page, click "Allow" button
3. **Copy the `xoxb-...` Bot Token**

### 9. Reinstall After Scope/Event Changes

After adding scopes or events, you must reinstall:

Option A - Via UI:
1. Go to "Install App" page
2. Click "Reinstall to Workspace"
3. Click "Allow"

Option B - Direct OAuth URL:
```
browser action=navigate targetUrl="https://slack.com/oauth/v2/authorize?client_id=CLIENT_ID&team=TEAM_ID&install_redirect=oauth&scope=COMMA_SEPARATED_SCOPES"
```

Then click "Allow" button.

## Extracting Tokens

**Bot Token (`xoxb-...`)**: 
- Location: OAuth & Permissions page
- Look for: `textbox [disabled]` containing `xoxb-...`
- Label: "Bot User OAuth Token"

**App Token (`xapp-...`)**: 
- Location: Basic Information page → App-Level Tokens section
- Click on token name to reveal value in modal
- Look for: `textbox` containing `xapp-...`

## Complete Bot Configuration Checklist

Before your bot can respond to DMs and thread mentions:

- [ ] Bot scopes include: `im:write`, `im:history`, `chat:write`, `app_mentions:read`, `users:read`
- [ ] Socket Mode is enabled
- [ ] App-Level Token generated with `connections:write` scope
- [ ] Agent mode enabled (adds `assistant:write` scope) — recommended for AI bots
- [ ] Event subscriptions include: `message.im`, `app_mention`
- [ ] App Home Messages Tab is enabled
- [ ] App is installed/reinstalled to workspace after all changes

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
| No DM events received | `message.im` not subscribed | Add event in Event Subscriptions |
| No @mention events | `app_mention` not subscribed | Add event + `app_mentions:read` scope |
| Socket not connecting | Missing `xapp-...` token | Generate App-Level Token |
| Bot forgets thread context | Thread sessions are isolated | Add `thread.inheritParent: true` to config |

## Browser Automation Notes

**Scope picker workflow:**
1. Click "Add an OAuth Scope" button (look for `ref` with text "Add an OAuth Scope")
2. A combobox appears with `expanded` state - type the scope name
3. Options filter - click the exact match option
4. Scope appears in table, warning banner shows "reinstall required"

**Event subscription workflow:**
1. Click "Add Bot User Event" button
2. Type event name (e.g., `message.im`)
3. Click matching option
4. Repeat for each event
5. Click "Save Changes" at page bottom

**Reinstall without UI navigation:**
Extract the OAuth URL from "Reinstall to Workspace" link, navigate directly:
```
https://slack.com/oauth/v2/authorize?client_id=XXX&team=TEAM_ID&install_redirect=oauth&scope=scope1,scope2,scope3
```

**Common element patterns in snapshots:**
- App dropdown: `combobox "app_select"`
- Scope table: `table` with `rowgroup` containing scope rows
- Add scope button: `button "Add an OAuth Scope"`
- Add event button: `button "Add Bot User Event"`
- Reinstall link: `link "Reinstall to [Workspace]"`
- Token textbox: `textbox [disabled]` containing `xoxb-...`
- Save button: `button "Save Changes"`
- Toggle switch: `switch` or `generic [cursor=pointer]` with "On"/"Off" text

**Session persistence:**
Use `profile=clawd` to maintain login state across browser restarts.

## Clawdbot Integration

To use the bot with Clawdbot, update gateway config:

### Open Access (Recommended for most bots)

Anyone can DM the bot and it responds in any channel:

```json
{
  "channels": {
    "slack": {
      "enabled": true,
      "mode": "socket",
      "botToken": "xoxb-...",
      "appToken": "xapp-...",
      "dm": {
        "policy": "open",
        "allowFrom": ["*"]
      },
      "groupPolicy": "open",
      "thread": {
        "inheritParent": true
      }
    }
  }
}
```

### Thread Context (Important!)

By default, Slack threads create **isolated sessions** without parent message context. This causes the bot to lose track of what a thread is about:

❌ **Without `inheritParent`:**
- Bot posts: "Here's my SSH key..."
- User replies in thread: "@bot done" 
- Bot: "What's done?" (has no context)

✅ **With `inheritParent: true`:**
- Thread sessions inherit the parent channel transcript
- Bot understands thread replies reference the parent message

**Always add this to your Slack config:**
```json
"thread": {
  "inheritParent": true
}
```

Other thread options:
- `historyScope: "thread"` (default) — each thread has its own history
- `historyScope: "channel"` — threads share the channel's history

**Important settings:**
- `dm.policy: "open"` — Anyone can DM without approval
- `dm.allowFrom: ["*"]` — Allow all users (or list specific user IDs)
- `groupPolicy: "open"` — Respond in any channel the bot is in

⚠️ **Without these settings, users get a pairing code instead of a response!**

### Restricted Access (For private/internal bots)

Require approval before responding to new users:

```json
{
  "channels": {
    "slack": {
      "enabled": true,
      "mode": "socket", 
      "botToken": "xoxb-...",
      "appToken": "xapp-...",
      "dm": {
        "policy": "pairing",
        "allowFrom": ["U123ABC", "U456DEF"]
      },
      "groupPolicy": "allowlist",
      "channels": {
        "#general": { "allow": true, "requireMention": true }
      }
    }
  }
}
```

With `policy: "pairing"`, unknown users get a pairing code they must have approved:
```bash
clawdbot pairing approve slack <code>
```

Then restart: `gateway action=restart`

## Multi-Bot Setup (Same Workspace)

When running multiple Clawdbot instances with different Slack apps:
1. Each app needs its own `botToken` and `appToken`
2. Each app should have unique event subscriptions
3. Use `allowBots: true` in channel config if bots need to see each other's messages
4. Be careful of bot-to-bot reply loops - use `requireMention` to prevent

To allow bots to DM each other:
1. Both bots need `im:write` and `im:history` scopes
2. Both bots need `message.im` event subscription
3. One bot opens conversation with `conversations.open`
4. Messages flow via DM channel
