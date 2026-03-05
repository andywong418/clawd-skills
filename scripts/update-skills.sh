#!/usr/bin/env bash
# update-skills.sh — Pull skills from ViralFarm API
# Called from HEARTBEAT.md on each heartbeat cycle.
# Requires: VIRALFARM_API_URL, VIRALFARM_API_KEY
set -euo pipefail

SKILLS_DIR="${BOT_WORKSPACE:-/root/clawd}/skills"
MANIFEST_FILE="${SKILLS_DIR}/.manifest.json"
API_URL="${VIRALFARM_API_URL:?VIRALFARM_API_URL not set}"
API_KEY="${VIRALFARM_API_KEY:?VIRALFARM_API_KEY not set}"

mkdir -p "$SKILLS_DIR"

# Fetch remote manifest
REMOTE=$(curl -sf -H "Authorization: Bearer ${API_KEY}" "${API_URL}/skills/manifest") || {
  echo "[update-skills] Failed to fetch manifest" >&2
  exit 1
}

REMOTE_SKILLS=$(echo "$REMOTE" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for s in data.get('skills', []):
    print(f\"{s['name']}\t{s['hash']}\")
" 2>/dev/null)

# Load local manifest (name→hash map)
declare -A LOCAL_HASHES
if [ -f "$MANIFEST_FILE" ]; then
  while IFS=$'\t' read -r name hash; do
    LOCAL_HASHES["$name"]="$hash"
  done < <(python3 -c "
import sys, json
data = json.load(open('$MANIFEST_FILE'))
for s in data.get('skills', []):
    print(f\"{s['name']}\t{s['hash']}\")
" 2>/dev/null)
fi

# Track which skills are still in remote manifest
declare -A REMOTE_NAMES
UPDATED=0

while IFS=$'\t' read -r name hash; do
  [ -z "$name" ] && continue
  REMOTE_NAMES["$name"]=1

  # Skip if hash matches
  if [ "${LOCAL_HASHES[$name]:-}" = "$hash" ]; then
    continue
  fi

  echo "[update-skills] Updating skill: $name"

  # Download and extract bundle
  TMP_FILE=$(mktemp /tmp/skill-XXXXXX.tar.gz)
  HTTP_CODE=$(curl -sf -o "$TMP_FILE" -w "%{http_code}" \
    -H "Authorization: Bearer ${API_KEY}" \
    "${API_URL}/skills/${name}/bundle") || true

  if [ "$HTTP_CODE" != "200" ]; then
    echo "[update-skills] Failed to download $name (HTTP $HTTP_CODE)" >&2
    rm -f "$TMP_FILE"
    continue
  fi

  # Remove old skill dir and extract new one
  rm -rf "${SKILLS_DIR:?}/${name}"
  mkdir -p "${SKILLS_DIR}/${name}"
  tar xzf "$TMP_FILE" -C "$SKILLS_DIR" 2>/dev/null || {
    # Some tar versions strip the top-level dir differently
    tar xzf "$TMP_FILE" --strip-components=1 -C "${SKILLS_DIR}/${name}" 2>/dev/null || {
      echo "[update-skills] Failed to extract $name" >&2
      rm -f "$TMP_FILE"
      continue
    }
  }
  rm -f "$TMP_FILE"

  # Make scripts executable
  find "${SKILLS_DIR}/${name}/scripts" -type f -name "*.sh" -exec chmod +x {} \; 2>/dev/null || true
  find "${SKILLS_DIR}/${name}/scripts" -type f -name "*.py" -exec chmod +x {} \; 2>/dev/null || true

  UPDATED=$((UPDATED + 1))
done <<< "$REMOTE_SKILLS"

# Remove skills no longer in manifest (access revoked or deleted)
REMOVED=0
for name in "${!LOCAL_HASHES[@]}"; do
  if [ -z "${REMOTE_NAMES[$name]:-}" ]; then
    echo "[update-skills] Removing revoked skill: $name"
    rm -rf "${SKILLS_DIR:?}/${name}"
    REMOVED=$((REMOVED + 1))
  fi
done

# Save updated manifest
echo "$REMOTE" > "$MANIFEST_FILE"

if [ $UPDATED -gt 0 ] || [ $REMOVED -gt 0 ]; then
  echo "[update-skills] Done: $UPDATED updated, $REMOVED removed"
else
  echo "[update-skills] Skills up to date"
fi
