---
name: slack
description: Use when you need to control Slack from Clawdbot via the slack tool, including reacting to messages or pinning/unpinning items in Slack channels or DMs.
---

# Slack Actions

## Overview

Use `slack` to react, manage pins, send/edit/delete messages, and fetch member info. The tool uses the bot token configured for Clawdbot.

## Inputs to collect

- `channelId` and `messageId` (Slack message timestamp, e.g. `1712023032.1234`).
- For reactions, an `emoji` (Unicode or `:name:`).
- For message sends, a `to` target (`channel:<id>` or `user:<id>`) and `content`.

Message context lines include `slack message id` and `channel` fields you can reuse directly.

## Actions

### Action groups

| Action group | Default | Notes |
| --- | --- | --- |
| reactions | enabled | React + list reactions |
| messages | enabled | Read/send/edit/delete |
| pins | enabled | Pin/unpin/list |
| memberInfo | enabled | Member info |
| emojiList | enabled | Custom emoji list |

### React to a message

```json
{
  "action": "react",
  "channelId": "C123",
  "messageId": "1712023032.1234",
  "emoji": "✅"
}
```

### List reactions

```json
{
  "action": "reactions",
  "channelId": "C123",
  "messageId": "1712023032.1234"
}
```

### Send a message

```json
{
  "action": "sendMessage",
  "to": "channel:C123",
  "content": "Hello from Clawdbot"
}
```

### Edit a message

```json
{
  "action": "editMessage",
  "channelId": "C123",
  "messageId": "1712023032.1234",
  "content": "Updated text"
}
```

### Delete a message

```json
{
  "action": "deleteMessage",
  "channelId": "C123",
  "messageId": "1712023032.1234"
}
```

### Read channel history

```json
{
  "action": "read",
  "channelId": "C123",
  "limit": 20
}
```

### Read thread replies

To read all replies in a thread, use the parent message's `ts` (timestamp) as `threadId`:

```json
{
  "action": "read",
  "channelId": "C123",
  "threadId": "1712023032.1234",
  "limit": 50
}
```

**Important:** When responding in a thread context, always read the thread first to understand the full conversation. The `thread_ts` from message metadata tells you which thread a message belongs to.

### Reply to a thread

To reply inside a thread (not to the channel), use `replyTo` with the parent message timestamp:

```json
{
  "action": "send",
  "target": "C123",
  "message": "This is a thread reply",
  "replyTo": "1712023032.1234"
}
```

**Note:** If you receive a message that has a `thread_ts` field, you're in a thread! Reply to that `thread_ts` to keep the conversation in the thread.

### Pin a message

```json
{
  "action": "pinMessage",
  "channelId": "C123",
  "messageId": "1712023032.1234"
}
```

### Unpin a message

```json
{
  "action": "unpinMessage",
  "channelId": "C123",
  "messageId": "1712023032.1234"
}
```

### List pinned items

```json
{
  "action": "listPins",
  "channelId": "C123"
}
```

### Member info

```json
{
  "action": "memberInfo",
  "userId": "U123"
}
```

### Emoji list

```json
{
  "action": "emojiList"
}
```

## Thread Context Best Practices

When you receive a message in Slack, check for these context clues:

1. **`thread_ts`** - If present, this message is part of a thread. Read the full thread with:
   ```json
   {"action": "read", "channelId": "...", "threadId": "<thread_ts>", "limit": 50}
   ```

2. **Always reply in-thread** when the incoming message has a `thread_ts`:
   ```json
   {"action": "send", "target": "...", "message": "...", "replyTo": "<thread_ts>"}
   ```

3. **Read before replying** - If someone mentions past messages or context you don't have, fetch the thread or channel history first.

### Example workflow

User sends message in thread → You receive it with `thread_ts: "1712023032.1234"`:

1. Read thread: `{"action": "read", "channelId": "C123", "threadId": "1712023032.1234", "limit": 50}`
2. Understand full context
3. Reply to thread: `{"action": "send", "target": "C123", "message": "...", "replyTo": "1712023032.1234"}`

## Ideas to try

- React with ✅ to mark completed tasks.
- Pin key decisions or weekly status updates.
- Use thread history to understand complex conversations before replying.
