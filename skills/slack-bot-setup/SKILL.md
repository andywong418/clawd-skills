---
name: slack-bot-setup
description: Create a new Slack bot app with full DM and messaging capabilities. Use when setting up a Slack bot that can send DMs, read messages, list users, or integrate with a workspace. Covers app creation, OAuth scopes, Socket Mode setup, and token retrieval via browser automation.
---

# Slack Bot Setup

Create a fully-configured Slack bot with DM capabilities via browser automation.

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

**Required scopes for DM bot:**
- `im:write` - Open DM conversations
- `im:history` - Read DM history  
- `chat:write` - Send messages
- `channels:read` - List channels
- `channels:history` - Read channel messages
- `users:read` - List workspace members

### 4. Enable Socket Mode

```
browser action=navigate targetUrl="https://api.slack.com/apps/APP_ID/general"
```

1. Find Socket Mode toggle, click to enable
2. When prompted, click "Generate Token"
3. Enter token name, select `connections:write` scope
4. Click Generate
5. **Copy the `xapp-...` token from the page**

### 5. Subscribe to Events

```
browser action=navigate targetUrl="https://api.slack.com/apps/APP_ID/event-subscriptions"
```

1. Toggle "Enable Events" ON
2. Expand "Subscribe to bot events"
3. Click "Add Bot User Event"
4. Add: `message.im`, `app_mention`

### 6. Install to Workspace

```
browser action=navigate targetUrl="https://api.slack.com/apps/APP_ID/install-on-team"
```

1. Click "Install to Workspace" 
2. On OAuth page, click "Allow" button
3. **Copy the `xoxb-...` Bot Token**

### 7. Reinstall After Scope Changes

After adding scopes, navigate directly to OAuth URL:
```
browser action=navigate targetUrl="https://slack.com/oauth/v2/authorize?client_id=CLIENT_ID&team=TEAM_ID&install_redirect=oauth&scope=COMMA_SEPARATED_SCOPES"
```

Then click "Allow" button.

## Extracting Tokens

**Bot Token**: On OAuth & Permissions page, find textbox with `xoxb-...` value
**App Token**: On Basic Information page under App-Level Tokens section

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

## Browser Automation Notes

**Scope picker workflow:**
1. Click "Add an OAuth Scope" button (look for `ref` with text "Add an OAuth Scope")
2. A combobox appears with `expanded` state - type the scope name
3. Options filter - click the exact match option
4. Scope appears in table, warning banner shows "reinstall required"

**Reinstall without UI navigation:**
Extract the OAuth URL from "Reinstall to Workspace" link, navigate directly:
```
https://slack.com/oauth/v2/authorize?client_id=XXX&team=TEAM_ID&install_redirect=oauth&scope=scope1,scope2,scope3
```

**Common element patterns in snapshots:**
- App dropdown: `combobox "app_select"`
- Scope table: `table` with `rowgroup` containing scope rows
- Add scope button: `button "Add an OAuth Scope"`
- Reinstall link: `link "Reinstall to [Workspace]"`
- Token textbox: `textbox [disabled]` containing `xoxb-...`

**Session persistence:**
Use `profile=clawd` to maintain login state across browser restarts.

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
