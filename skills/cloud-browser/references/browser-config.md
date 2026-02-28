# Browser Configuration Reference

## Chrome Flags

### Essential flags (already included in scripts)
```
--remote-debugging-port=9222     # CDP debug port
--remote-debugging-address=0.0.0.0  # Allow remote connections
--user-data-dir=/path/to/profile # Persistent profile
--no-first-run                   # Skip setup wizard
--no-default-browser-check       # Skip default browser prompt
--no-sandbox                     # Required for root
--disable-gpu                    # Headless stability
--disable-dev-shm-usage          # Prevent crashes in Docker/VM
```

### Optional flags
```
--headless=new                   # True headless (no display needed)
--window-size=1920,1080          # Browser dimensions
--disable-extensions             # No extensions
--disable-background-networking  # Reduce background activity
--disable-sync                   # No Google sync
--disable-translate              # No translate prompts
--mute-audio                     # Silence audio
--incognito                      # Incognito mode (no persistence!)
```

### Proxy configuration
```
--proxy-server=socks5://127.0.0.1:1080
--proxy-server=http://proxy.example.com:8080
--proxy-bypass-list="localhost,127.0.0.1"
```

## Profile Management

### Profile locations
```
/root/.browser-profiles/default/     # Default profile
/root/.browser-profiles/telegram/    # Telegram-specific
/root/.browser-profiles/account-1/   # Multi-account
```

### What's stored in a profile
- Cookies and sessions
- Local storage
- IndexedDB
- Extensions and settings
- Autofill data
- History (optional)

### Backing up profiles
```bash
# Backup
tar -czf profile-backup.tar.gz /root/.browser-profiles/telegram

# Restore
tar -xzf profile-backup.tar.gz -C /
```

## CDP (Chrome DevTools Protocol)

### Verify browser is running
```bash
curl http://localhost:9222/json/version
```

### List open tabs
```bash
curl http://localhost:9222/json/list
```

### Open new tab
```bash
curl "http://localhost:9222/json/new?https://example.com"
```

## Resource Limits

### Memory usage by browser size
| Tabs | Approx RAM |
|------|------------|
| 1-3  | 300-500MB  |
| 5-10 | 500MB-1GB  |
| 10+  | 1GB+       |

### Recommended droplet sizing
- Light (1-3 tabs): s-1vcpu-1gb
- Moderate (5-10 tabs): s-1vcpu-2gb  
- Heavy (10+ tabs): s-2vcpu-4gb

## Troubleshooting

### Browser won't start
```bash
# Check Xvfb
pgrep Xvfb || Xvfb :99 -screen 0 1920x1080x24 &
export DISPLAY=:99

# Check logs
cat /var/log/browser/default.log

# Test Chrome directly
google-chrome-stable --version
```

### Connection refused on :9222
```bash
# Check if listening
ss -tlnp | grep 9222

# Check firewall
ufw status
ufw allow 9222/tcp
```

### Session expired / logged out
- Ensure using same profile path
- Don't use `--incognito` (no persistence)
- Check if cookies are being cleared
