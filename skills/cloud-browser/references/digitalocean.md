# DigitalOcean Reference

## API Token Setup

1. Go to https://cloud.digitalocean.com/account/api/tokens
2. Generate a new token with read/write access
3. Set as environment variable: `export DO_API_TOKEN=your_token`

## Droplet Sizes

| Size | vCPUs | RAM | Disk | Price/mo | Use Case |
|------|-------|-----|------|----------|----------|
| s-1vcpu-1gb | 1 | 1GB | 25GB | $6 | Single browser, light use |
| s-1vcpu-2gb | 1 | 2GB | 50GB | $12 | Single browser, moderate use |
| s-2vcpu-2gb | 2 | 2GB | 60GB | $18 | Multiple tabs, scraping |
| s-2vcpu-4gb | 2 | 4GB | 80GB | $24 | Heavy automation |

**Recommendation:** Start with `s-1vcpu-2gb` for most browser automation tasks.

## Regions

| Code | Location | Latency (US) |
|------|----------|--------------|
| nyc1, nyc3 | New York | Low |
| sfo3 | San Francisco | Low |
| tor1 | Toronto | Low |
| lon1 | London | Medium |
| ams3 | Amsterdam | Medium |
| sgp1 | Singapore | High |

## SSH Key Setup

```bash
# Generate key if needed
ssh-keygen -t ed25519 -C "clawdbot-browser"

# Add to DigitalOcean via CLI
doctl compute ssh-key create my-key --public-key "$(cat ~/.ssh/id_ed25519.pub)"

# Or add via web UI at:
# https://cloud.digitalocean.com/account/security
```

## Firewall Configuration

For security, restrict port 9222 to your IP:

```bash
# Using doctl
doctl compute firewall create \
    --name browser-access \
    --inbound-rules "protocol:tcp,ports:9222,address:<YOUR_IP>/32" \
    --droplet-ids <DROPLET_ID>
```

Or use SSH tunnel (more secure):
```bash
ssh -L 9222:localhost:9222 root@<droplet-ip> -N
# Connect to http://localhost:9222
```

## Useful doctl Commands

```bash
# List droplets
doctl compute droplet list

# Get droplet info
doctl compute droplet get <id>

# Delete droplet
doctl compute droplet delete <id>

# List SSH keys
doctl compute ssh-key list

# List regions
doctl compute region list

# List sizes
doctl compute size list
```
