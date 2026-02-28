#!/bin/bash
# Manage browser sessions on a remote server
# Usage: browser-session.sh <ssh-target> <start|stop|status|restart> [profile]

set -e

SSH_TARGET="${1:?Usage: browser-session.sh <ssh-target> <start|stop|status|restart> [profile]}"
ACTION="${2:?Usage: browser-session.sh <ssh-target> <start|stop|status|restart> [profile]}"
PROFILE="${3:-default}"

case "$ACTION" in
    start)
        echo "Starting browser on $SSH_TARGET (profile: $PROFILE)..."
        ssh "$SSH_TARGET" bash -s << EOF
            # Start Xvfb if not running
            if ! pgrep -x Xvfb > /dev/null; then
                Xvfb :99 -screen 0 1920x1080x24 &
                sleep 2
            fi
            export DISPLAY=:99
            
            # Kill existing browser on this profile if any
            pkill -f "user-data-dir=/root/.browser-profiles/$PROFILE" 2>/dev/null || true
            pkill -f "socat.*9223" 2>/dev/null || true
            sleep 1
            
            # Start Chrome (binds to localhost only)
            nohup google-chrome-stable \
                --remote-debugging-port=9222 \
                --user-data-dir=/root/.browser-profiles/$PROFILE \
                --no-first-run \
                --no-default-browser-check \
                --disable-gpu \
                --disable-dev-shm-usage \
                --no-sandbox \
                --headless=new \
                > /var/log/browser/$PROFILE.log 2>&1 &
            
            sleep 3
            
            # Start socat proxy to expose externally on 9223
            nohup socat TCP-LISTEN:9223,fork,reuseaddr TCP:127.0.0.1:9222 \
                > /var/log/browser/socat.log 2>&1 &
            
            sleep 2
            
            # Verify it started
            if pgrep -f "user-data-dir=/root/.browser-profiles/$PROFILE" > /dev/null; then
                IP=\$(hostname -I | awk '{print \$1}')
                echo "Browser started successfully"
                echo "Internal: http://localhost:9222"
                echo "External: http://\$IP:9223"
            else
                echo "Failed to start browser. Check /var/log/browser/$PROFILE.log"
                exit 1
            fi
EOF
        ;;
    
    stop)
        echo "Stopping browser on $SSH_TARGET (profile: $PROFILE)..."
        ssh "$SSH_TARGET" "pkill -f 'user-data-dir=/root/.browser-profiles/$PROFILE' 2>/dev/null || echo 'No browser running'"
        ;;
    
    status)
        echo "Checking browser status on $SSH_TARGET..."
        ssh "$SSH_TARGET" bash -s << 'EOF'
            echo "=== Running browsers ==="
            ps aux | grep -E "chrome.*user-data-dir" | grep -v grep || echo "No browsers running"
            
            echo ""
            echo "=== Profiles ==="
            ls -la /root/.browser-profiles/ 2>/dev/null || echo "No profiles yet"
            
            echo ""
            echo "=== Debug endpoint ==="
            if curl -s http://localhost:9222/json/version > /dev/null 2>&1; then
                echo "Browser accessible at http://$(hostname -I | awk '{print $1}'):9222"
                curl -s http://localhost:9222/json/version | head -5
            else
                echo "No browser responding on :9222"
            fi
EOF
        ;;
    
    restart)
        "$0" "$SSH_TARGET" stop "$PROFILE"
        sleep 2
        "$0" "$SSH_TARGET" start "$PROFILE"
        ;;
    
    *)
        echo "Unknown action: $ACTION"
        echo "Usage: browser-session.sh <ssh-target> <start|stop|status|restart> [profile]"
        exit 1
        ;;
esac
