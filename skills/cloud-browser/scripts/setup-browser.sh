#!/bin/bash
# Set up Chrome with persistent profile on a remote server
# Usage: setup-browser.sh <ssh-target>

set -e

SSH_TARGET="${1:?Usage: setup-browser.sh <ssh-target>}"

echo "Setting up browser on $SSH_TARGET..."

ssh -o StrictHostKeyChecking=no "$SSH_TARGET" bash -s << 'REMOTE_SCRIPT'
set -e
export DEBIAN_FRONTEND=noninteractive

echo "[1/6] Updating system..."
apt-get update -qq

echo "[2/6] Installing dependencies..."
# Note: libasound2 renamed to libasound2t64 in Ubuntu 24.04
apt-get install -y -qq \
    wget \
    gnupg \
    xvfb \
    socat \
    fonts-liberation \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    xdg-utils \
    2>&1 | tail -5

echo "[3/6] Installing Chrome..."
if ! command -v google-chrome-stable &> /dev/null; then
    wget -q -O /tmp/chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
    apt-get install -y -qq /tmp/chrome.deb 2>&1 | tail -3
    rm /tmp/chrome.deb
fi

echo "[4/6] Creating profile directories..."
mkdir -p /root/.browser-profiles/default
mkdir -p /var/log/browser

echo "[5/6] Creating browser service..."
# Chrome ignores --remote-debugging-address in newer versions
# We use socat to expose the port externally
cat > /etc/systemd/system/chrome-browser@.service << 'EOF'
[Unit]
Description=Chrome Browser (%i profile)
After=network.target

[Service]
Type=simple
Environment=DISPLAY=:99
ExecStartPre=/bin/bash -c 'pgrep Xvfb || Xvfb :99 -screen 0 1920x1080x24 &'
ExecStart=/usr/bin/google-chrome-stable \
    --remote-debugging-port=9222 \
    --user-data-dir=/root/.browser-profiles/%i \
    --no-first-run \
    --no-default-browser-check \
    --disable-gpu \
    --disable-dev-shm-usage \
    --no-sandbox \
    --headless=new
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Socat service to expose Chrome debugging port externally
cat > /etc/systemd/system/chrome-proxy.service << 'EOF'
[Unit]
Description=Chrome Debug Port Proxy
After=chrome-browser@default.service

[Service]
Type=simple
ExecStart=/usr/bin/socat TCP-LISTEN:9223,fork,reuseaddr TCP:127.0.0.1:9222
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload

echo "[6/6] Configuring firewall..."
if command -v ufw &> /dev/null && ufw status | grep -q "active"; then
    ufw allow 9223/tcp > /dev/null 2>&1 || true
fi

echo ""
echo "Browser setup complete!"
echo "Profiles: /root/.browser-profiles/"
echo "Internal port: 9222 (localhost only)"
echo "External port: 9223 (via socat proxy)"
echo ""
echo "Start with: systemctl start chrome-browser@default chrome-proxy"
google-chrome-stable --version
REMOTE_SCRIPT

echo ""
echo "Setup complete on $SSH_TARGET"
echo "Start browser with: $(dirname "$0")/browser-session.sh $SSH_TARGET start"
