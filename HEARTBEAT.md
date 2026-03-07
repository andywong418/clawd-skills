# HEARTBEAT.md

## Update Skills
Pull latest skills from ViralFarm API / clawd-skills repo. Runs on each heartbeat cycle.
```bash
bash /root/clawd/scripts/update-skills.sh
```

This pulls from https://github.com/wondrous-dev/clawd-skills and symlinks any new skills into your skills directory.
