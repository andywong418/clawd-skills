# BOOT.md — Auto-Run on Gateway Startup

This file runs automatically when the gateway starts (via boot-md hook).

## Instructions

1. Run the boot sequence to load context:
   ```bash
   ./scripts/boot.sh "gateway startup"
   ```

2. Check today's date and log that you're online:
   ```bash
   echo "$(date '+%Y-%m-%d %H:%M:%S UTC') - Gateway started, boot sequence complete" >> memory/$(date +%Y-%m-%d).md
   ```

3. If there's a pending task in `memory/SESSION-STATE.md`, mention it in your startup message.

4. Send a brief startup message to confirm you're online (use NO_REPLY after sending via message tool).
