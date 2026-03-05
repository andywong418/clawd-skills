# HEARTBEAT.md

## Auto-update shared skills

Run this every heartbeat to pull latest skills from the public repo:

```bash
bash scripts/update-skills.sh
```

This pulls from https://github.com/wondrous-dev/clawd-skills and symlinks any new skills into your skills directory.
