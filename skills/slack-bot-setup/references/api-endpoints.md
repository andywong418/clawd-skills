# Slack API Endpoints Reference

Base URL: `https://slack.com/api/`

## Authentication

### auth.test
Verify token and get bot info.
```bash
curl -X POST https://slack.com/api/auth.test \
  -H "Authorization: Bearer $TOKEN"
```
Response: `{ "ok": true, "user": "botname", "user_id": "U...", "team": "...", "team_id": "T..." }`

## Users

### users.list
List workspace members.
```bash
curl "https://slack.com/api/users.list?limit=100" \
  -H "Authorization: Bearer $TOKEN"
```
Requires: `users:read`

### users.info
Get user details.
```bash
curl "https://slack.com/api/users.info?user=U123456" \
  -H "Authorization: Bearer $TOKEN"
```

### users.lookupByEmail
Find user by email.
```bash
curl "https://slack.com/api/users.lookupByEmail?email=user@example.com" \
  -H "Authorization: Bearer $TOKEN"
```
Requires: `users:read.email`

## Conversations

### conversations.open
Open or get existing DM channel.
```bash
curl -X POST https://slack.com/api/conversations.open \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"users": "U123456"}'
```
Requires: `im:write`
Response: `{ "ok": true, "channel": { "id": "D..." } }`

### conversations.list
List channels the bot can see.
```bash
curl "https://slack.com/api/conversations.list?types=public_channel,private_channel,im" \
  -H "Authorization: Bearer $TOKEN"
```

### conversations.history
Get messages from a channel.
```bash
curl "https://slack.com/api/conversations.history?channel=C123456&limit=10" \
  -H "Authorization: Bearer $TOKEN"
```
Requires: `channels:history` or `im:history`

## Messaging

### chat.postMessage
Send a message.
```bash
curl -X POST https://slack.com/api/chat.postMessage \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "channel": "C123456",
    "text": "Hello world!",
    "blocks": [...]  // optional Block Kit
  }'
```
Requires: `chat:write`

### chat.update
Edit a message.
```bash
curl -X POST https://slack.com/api/chat.update \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "channel": "C123456",
    "ts": "1234567890.123456",
    "text": "Updated text"
  }'
```

### chat.delete
Delete a message.
```bash
curl -X POST https://slack.com/api/chat.delete \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "channel": "C123456",
    "ts": "1234567890.123456"
  }'
```

## Reactions

### reactions.add
Add emoji reaction.
```bash
curl -X POST https://slack.com/api/reactions.add \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "channel": "C123456",
    "timestamp": "1234567890.123456",
    "name": "thumbsup"
  }'
```
Requires: `reactions:write`

## Rate Limits

- Most methods: 50+ requests/minute
- `chat.postMessage`: 1 message/second per channel
- `conversations.open`: 100 per minute
- Bulk operations: Use pagination with `cursor`

## Error Codes

| Code | Meaning |
|------|---------|
| `missing_scope` | Need to add OAuth scope |
| `channel_not_found` | Invalid channel ID |
| `not_in_channel` | Bot not in private channel |
| `user_not_found` | Invalid user ID |
| `ratelimited` | Too many requests |
| `invalid_auth` | Bad token |
| `account_inactive` | User deactivated |
