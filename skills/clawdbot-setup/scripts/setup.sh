#!/bin/bash
# Clawdbot Full Setup Script
# Creates a new Clawdbot instance with best-practice templates and recommended skills

set -e

WORKSPACE="${1:-$HOME/clawd}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATES_DIR="$(dirname "$SCRIPT_DIR")/templates"

echo "🤖 Clawdbot Setup"
echo "================="
echo "Workspace: $WORKSPACE"
echo ""

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "📦 Installing Node.js..."
    curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
    apt-get install -y nodejs
fi

echo "Node.js: $(node --version)"

# Check if Clawdbot is installed
if ! command -v clawdbot &> /dev/null; then
    echo "📦 Installing Clawdbot..."
    npm install -g clawdbot
fi

echo "Clawdbot: $(clawdbot --version 2>/dev/null || echo 'installed')"

# Create workspace
echo ""
echo "📁 Creating workspace..."
mkdir -p "$WORKSPACE"
mkdir -p "$WORKSPACE/memory"
cd "$WORKSPACE"

# Copy templates
echo "📄 Copying templates..."
if [ -d "$TEMPLATES_DIR" ]; then
    cp -n "$TEMPLATES_DIR"/*.md "$WORKSPACE/" 2>/dev/null || true
    # Copy scripts directory (boot.sh, etc.)
    if [ -d "$TEMPLATES_DIR/scripts" ]; then
        mkdir -p "$WORKSPACE/scripts"
        cp -n "$TEMPLATES_DIR/scripts"/* "$WORKSPACE/scripts/" 2>/dev/null || true
        chmod +x "$WORKSPACE/scripts"/*.sh 2>/dev/null || true
    fi
    echo "   Templates copied from skill"
else
    echo "   ⚠️  Templates not found at $TEMPLATES_DIR"
    echo "   You'll need to copy templates manually"
fi

# Initialize interoceptive state
if [ ! -f "$WORKSPACE/memory/interoceptive-state.json" ]; then
    echo '{"lastConsolidation": null, "stalenessHours": 0, "activeTopics": []}' > "$WORKSPACE/memory/interoceptive-state.json"
fi

# Install recommended skills
echo ""
echo "🧠 Installing OpenCortex (self-improving memory)..."
if command -v clawhub &> /dev/null || command -v npx &> /dev/null; then
    npx clawhub install opencortex 2>/dev/null || echo "   ⚠️  OpenCortex install failed (may need manual install)"
    if [ -f "$WORKSPACE/skills/opencortex/scripts/install.sh" ]; then
        bash "$WORKSPACE/skills/opencortex/scripts/install.sh" --non-interactive 2>/dev/null || true
    fi
else
    echo "   ⚠️  clawhub not available, skip skill install"
fi

echo ""
echo "🛡️  Installing Vigil (safety guardrails)..."
npm install vigil-agent-safety 2>/dev/null || echo "   ⚠️  Vigil install failed (optional)"

echo ""
echo "🪝 Enabling hooks (boot-md, session-memory)..."
clawdbot hooks enable boot-md 2>/dev/null || echo "   ⚠️  boot-md hook failed (may need manual enable)"
clawdbot hooks enable session-memory 2>/dev/null || echo "   ⚠️  session-memory hook failed (may need manual enable)"

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. cd $WORKSPACE"
echo "  2. clawdbot init  (configure API keys)"
echo "  3. clawdbot configure --section slack  (or telegram/discord)"
echo "  4. clawdbot gateway start"
echo ""
echo "The agent will complete BOOTSTRAP.md on first conversation."
