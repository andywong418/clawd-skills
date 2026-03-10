---
name: twitter
description: Fetch tweets and user info from X/Twitter using API credentials. Use when needing to read tweet content, get user profiles, or search tweets. Triggers on X/Twitter URLs or requests to fetch/lookup tweets.
---

# Twitter/X API Skill

Credentials are in `~/.clawdbot/.env` (TWITTER_BEARER_TOKEN, etc.).

## Fetching a Tweet

```bash
source ~/.clawdbot/.env
scripts/fetch_tweet.sh <tweet_id_or_url>
```

Extracts tweet ID from URLs automatically. Returns JSON with text, author, metrics.

## Get User Info

```bash
source ~/.clawdbot/.env
curl -s -H "Authorization: Bearer $TWITTER_BEARER_TOKEN" \
  "https://api.twitter.com/2/users/by/username/<username>?user.fields=description,public_metrics"
```

## Search Recent Tweets

```bash
source ~/.clawdbot/.env
curl -s -H "Authorization: Bearer $TWITTER_BEARER_TOKEN" \
  "https://api.twitter.com/2/tweets/search/recent?query=<query>&max_results=10&tweet.fields=text,author_id,created_at"
```

## Common Issues

- **"Could not find tweet"**: Tweet may be deleted, from a private account, or ID is incorrect
- **Rate limits**: Free tier = 1500 tweets/month read, 1500 tweets/month post
- **Bearer token**: URL-encoded in .env, works as-is with curl
