# Slack OAuth Scopes Reference

## Messaging Scopes

| Scope | Description |
|-------|-------------|
| `chat:write` | Send messages as the bot |
| `chat:write.customize` | Send with custom username/avatar |
| `chat:write.public` | Post to channels without joining |

## DM Scopes

| Scope | Description |
|-------|-------------|
| `im:write` | Open DM conversations |
| `im:read` | View basic DM info |
| `im:history` | Read DM message history |

## Channel Scopes

| Scope | Description |
|-------|-------------|
| `channels:read` | View public channel info |
| `channels:history` | Read public channel messages |
| `channels:join` | Join public channels |
| `channels:manage` | Create/archive/rename channels |

## Private Channel Scopes

| Scope | Description |
|-------|-------------|
| `groups:read` | View private channel info |
| `groups:history` | Read private channel messages |
| `groups:write` | Create private channels |

## User Scopes

| Scope | Description |
|-------|-------------|
| `users:read` | List workspace members |
| `users:read.email` | Access user email addresses |
| `users.profile:read` | View user profiles |

## Reaction Scopes

| Scope | Description |
|-------|-------------|
| `reactions:read` | View emoji reactions |
| `reactions:write` | Add/remove reactions |

## File Scopes

| Scope | Description |
|-------|-------------|
| `files:read` | View files |
| `files:write` | Upload/modify files |

## App-Level Token Scopes

Used for Socket Mode connection (not bot scopes):

| Scope | Description |
|-------|-------------|
| `connections:write` | Required for Socket Mode |
| `authorizations:read` | View app installations |

## Recommended Scope Sets

### Basic Bot (read-only)
```
channels:read, channels:history, users:read
```

### DM Bot (send messages)
```
chat:write, im:write, im:history, users:read
```

### Full Featured Bot
```
chat:write, im:write, im:history, channels:read, channels:history, 
users:read, reactions:write, files:write
```

### Viral/Outreach Bot
```
chat:write, im:write, im:history, users:read, users:read.email
```
