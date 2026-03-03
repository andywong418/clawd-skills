#!/bin/bash
# Boot script — run this BEFORE your first response every session.
# Loads credentials, supermemory context, memory files, and tools into one summary.
# Usage: ./scripts/boot.sh ["topic or query"]

set -euo pipefail

WORKSPACE="$(cd "$(dirname "$0")/.." && pwd)"
QUERY="${1:-general context}"
TODAY=$(date +%Y-%m-%d)
YESTERDAY=$(date -d "yesterday" +%Y-%m-%d 2>/dev/null || date -v-1d +%Y-%m-%d 2>/dev/null || echo "")

echo "========================================"
echo "  BOOT SEQUENCE — $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo "========================================"

# --- 1. CREDENTIALS ---
echo ""
echo "--- CREDENTIALS (.env) ---"
ENV_FILE="$HOME/.clawdbot/.env"
if [[ -f "$ENV_FILE" ]]; then
  # Show variable names only, never values
  KEYS=$(grep -E '^[A-Z_]+=.' "$ENV_FILE" 2>/dev/null | cut -d= -f1 | sort)
  if [[ -n "$KEYS" ]]; then
    echo "Available keys in ~/.clawdbot/.env:"
    echo "$KEYS" | sed 's/^/  - /'
  else
    echo "  .env exists but no keys found"
  fi
else
  echo "  WARNING: ~/.clawdbot/.env not found"
fi

# --- 2. SUPERMEMORY ---
echo ""
echo "--- SUPERMEMORY ---"
SUPERMEMORY_SCRIPT="$WORKSPACE/skills/supermemory/scripts/get-context.sh"
if [[ -f "$SUPERMEMORY_SCRIPT" ]] && [[ -f "$ENV_FILE" ]] && grep -q "SUPERMEMORY_API_KEY" "$ENV_FILE" 2>/dev/null; then
  # Run with timeout to avoid hanging
  timeout 10 bash "$SUPERMEMORY_SCRIPT" "$QUERY" 2>/dev/null || echo "  Supermemory query timed out or failed (non-fatal)"
else
  echo "  Supermemory not available (missing script or API key)"
fi

# --- 3. MEMORY FILES ---
echo ""
echo "--- RECENT MEMORY ---"
MEMORY_DIR="$WORKSPACE/memory"
if [[ -d "$MEMORY_DIR" ]]; then
  # Today
  if [[ -f "$MEMORY_DIR/$TODAY.md" ]]; then
    echo "Today ($TODAY):"
    cat "$MEMORY_DIR/$TODAY.md" | head -50
    LINES=$(wc -l < "$MEMORY_DIR/$TODAY.md")
    if [[ $LINES -gt 50 ]]; then
      echo "  ... ($LINES total lines, showing first 50)"
    fi
  else
    echo "No memory file for today ($TODAY)"
  fi
  echo ""
  # Yesterday
  if [[ -n "$YESTERDAY" ]] && [[ -f "$MEMORY_DIR/$YESTERDAY.md" ]]; then
    echo "Yesterday ($YESTERDAY):"
    cat "$MEMORY_DIR/$YESTERDAY.md" | head -30
    LINES=$(wc -l < "$MEMORY_DIR/$YESTERDAY.md")
    if [[ $LINES -gt 30 ]]; then
      echo "  ... ($LINES total lines, showing first 30)"
    fi
  fi
  # Session state
  if [[ -f "$MEMORY_DIR/SESSION-STATE.md" ]]; then
    echo ""
    echo "Session State (WAL):"
    cat "$MEMORY_DIR/SESSION-STATE.md" | head -20
  fi
else
  echo "  No memory/ directory found"
fi

# --- 4. TOOLS & INFRASTRUCTURE ---
echo ""
echo "--- TOOLS & INFRASTRUCTURE ---"
TOOLS_FILE="$WORKSPACE/TOOLS.md"
if [[ -f "$TOOLS_FILE" ]]; then
  # Extract just the infrastructure section (skip the template/examples at top)
  grep -A 1000 "^### Infrastructure" "$TOOLS_FILE" 2>/dev/null | head -40 || echo "  TOOLS.md exists but no Infrastructure section"
else
  echo "  No TOOLS.md found"
fi

# --- 5. AVAILABLE SKILLS ---
echo ""
echo "--- AVAILABLE SKILLS ---"
SKILLS_DIR="$WORKSPACE/skills"
if [[ -d "$SKILLS_DIR" ]]; then
  for skill_dir in "$SKILLS_DIR"/*/; do
    skill_name=$(basename "$skill_dir")
    if [[ -f "$skill_dir/SKILL.md" ]]; then
      desc=$(head -3 "$skill_dir/SKILL.md" | grep -v '^#' | grep -v '^$' | head -1)
      echo "  - $skill_name: $desc"
    else
      echo "  - $skill_name"
    fi
  done
else
  echo "  No skills/ directory found"
fi

echo ""
echo "========================================"
echo "  BOOT COMPLETE — You're ready to go."
echo "  Remember: if you learn something new,"
echo "  write it down IMMEDIATELY with:"
echo "  ./skills/supermemory/scripts/add-memory.sh \"what you learned\""
echo "========================================"
