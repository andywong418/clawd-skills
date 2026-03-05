#!/bin/bash
# Auto-update shared skills from clawd-skills repo
SKILLS_DIR="${CLAWD_SKILLS_DIR:-/root/clawd-skills}"
BOT_SKILLS_DIR="${BOT_SKILLS_DIR:-/root/clawd/skills}"

if [ ! -d "$SKILLS_DIR" ]; then
  git clone https://github.com/wondrous-dev/clawd-skills.git "$SKILLS_DIR" 2>&1
  # Symlink new skills
  for skill in "$SKILLS_DIR"/*/; do
    name=$(basename "$skill")
    ln -sf "$skill" "$BOT_SKILLS_DIR/$name" 2>/dev/null
  done
  echo "Cloned and linked clawd-skills"
  exit 0
fi

cd "$SKILLS_DIR"
LOCAL=$(git rev-parse HEAD)
git fetch origin main --quiet 2>&1
REMOTE=$(git rev-parse origin/main)

if [ "$LOCAL" != "$REMOTE" ]; then
  git pull origin main --quiet 2>&1
  # Link any new skills
  for skill in "$SKILLS_DIR"/*/; do
    name=$(basename "$skill")
    ln -sf "$skill" "$BOT_SKILLS_DIR/$name" 2>/dev/null
  done
  echo "Updated skills: $(git log --oneline $LOCAL..$REMOTE | head -5)"
else
  echo "Skills up to date"
fi
