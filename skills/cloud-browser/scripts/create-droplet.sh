#!/bin/bash
# Create a DigitalOcean droplet with persistent browser setup
# Usage: create-droplet.sh <name> [region] [size]

set -e

NAME="${1:?Usage: create-droplet.sh <name> [region] [size]}"
REGION="${2:-nyc3}"
SIZE="${3:-s-1vcpu-1gb}"
IMAGE="ubuntu-24-04-x64"

# Check for DO token
if [[ -z "$DO_API_TOKEN" ]]; then
    echo "Error: DO_API_TOKEN environment variable not set"
    echo "Get your token at: https://cloud.digitalocean.com/account/api/tokens"
    exit 1
fi

# Check for doctl
if ! command -v doctl &> /dev/null; then
    echo "Installing doctl..."
    cd /tmp
    curl -sL https://github.com/digitalocean/doctl/releases/download/v1.104.0/doctl-1.104.0-linux-amd64.tar.gz | tar xz
    sudo mv doctl /usr/local/bin/
fi

# Authenticate doctl
doctl auth init -t "$DO_API_TOKEN" 2>/dev/null || true

# Get SSH key ID (use first available)
SSH_KEY_ID=$(doctl compute ssh-key list --format ID --no-header | head -1)
if [[ -z "$SSH_KEY_ID" ]]; then
    echo "Error: No SSH keys found in DigitalOcean account"
    echo "Add one at: https://cloud.digitalocean.com/account/security"
    exit 1
fi

echo "Creating droplet '$NAME' in $REGION..."

# Create droplet
DROPLET_ID=$(doctl compute droplet create "$NAME" \
    --region "$REGION" \
    --size "$SIZE" \
    --image "$IMAGE" \
    --ssh-keys "$SSH_KEY_ID" \
    --tag-names "browser,clawdbot" \
    --wait \
    --format ID \
    --no-header)

echo "Droplet created with ID: $DROPLET_ID"

# Get IP address
IP=$(doctl compute droplet get "$DROPLET_ID" --format PublicIPv4 --no-header)
echo "IP Address: $IP"

# Wait for SSH to be ready
echo "Waiting for SSH..."
for i in {1..30}; do
    if ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no "root@$IP" "echo ready" 2>/dev/null; then
        break
    fi
    sleep 5
done

# Run browser setup
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "Setting up browser..."
"$SCRIPT_DIR/setup-browser.sh" "root@$IP"

echo ""
echo "========================================="
echo "Droplet ready!"
echo "========================================="
echo "Name: $NAME"
echo "IP:   $IP"
echo "SSH:  ssh root@$IP"
echo ""
echo "Browser debugging port: http://$IP:9222"
echo "Start browser: $SCRIPT_DIR/browser-session.sh root@$IP start"
echo ""
echo "To connect from Clawdbot, use:"
echo "  controlUrl: http://$IP:9222"
echo "========================================="
