---
name: cloud-browser
description: Create and manage cloud VPCs with persistent browser environments. Use when setting up headless Chrome instances on cloud servers (DigitalOcean), managing browser sessions that persist across restarts, or creating browser automation infrastructure.
---

# Cloud Browser

Create cloud-based persistent browser environments for automation, web scraping, session persistence, and multi-account management.

## Quick Start

1. **Create a droplet with browser**: `scripts/create-droplet.sh <name> [region]`
2. **Setup browser on existing server**: `scripts/setup-browser.sh <ssh-target>`
3. **Manage browser session**: `scripts/browser-session.sh <ssh-target> <start|stop|status>`

## Workflow

### Creating a New Browser Instance

```bash
# Create droplet (includes browser setup)
./scripts/create-droplet.sh my-browser nyc3

# Output: IP address and SSH command
# Browser will be accessible at http://<ip>:9222
```

### Setting Up Browser on Existing Server

```bash
# SSH target can be IP, hostname, or SSH alias
./scripts/setup-browser.sh root@192.168.1.100

# Or with SSH config alias
./scripts/setup-browser.sh my-server
```

### Managing Browser Sessions

```bash
# Start browser with persistent profile
./scripts/browser-session.sh my-server start

# Check status
./scripts/browser-session.sh my-server status

# Stop browser
./scripts/browser-session.sh my-server stop

# Start with specific profile name
./scripts/browser-session.sh my-server start telegram
```

## Architecture

```
Cloud Server (DigitalOcean Droplet)
├── Chrome (headless, remote debugging on :9222)
├── User Data Dir: /root/.browser-profiles/<profile>/
├── Xvfb (virtual display)
└── Persistent sessions via systemd
```

## Connecting from Clawdbot

Once a cloud browser is running, connect via:

```javascript
// In browser tool, use controlUrl
browser.action = "open"
browser.controlUrl = "http://<droplet-ip>:9222"
browser.targetUrl = "https://web.telegram.org"
```

Or via SSH tunnel for security:

```bash
ssh -L 9222:localhost:9222 root@<droplet-ip> -N &
# Then connect to http://localhost:9222
```

## Configuration Options

See `references/browser-config.md` for:
- Chrome flags and options
- Profile management
- Proxy configuration
- Resource limits

See `references/digitalocean.md` for:
- Droplet sizing recommendations
- Region selection
- API token setup
- Firewall configuration

## Common Use Cases

1. **Telegram Web persistence** — Stay logged in across sessions
2. **Multi-account management** — Separate profiles per account
3. **Web scraping** — Headless automation at scale
4. **Session isolation** — Each browser in its own VM

## Requirements

- DigitalOcean API token (set as `DO_API_TOKEN` env var)
- SSH key configured with DigitalOcean
- `doctl` CLI (installed automatically if missing)
