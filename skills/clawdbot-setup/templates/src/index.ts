import { config } from 'dotenv';
import { existsSync } from 'fs';
import { SlackAdapter } from './adapters/slack.js';
import { handleMessage, warmAgentPool } from './agent.js';
import { startCron, stopCron } from './cron.js';

// Load env from multiple sources (later files override earlier)
const envPaths = [
  `${process.env.HOME}/.clawdbot/.env`,  // Server-level keys
  '.env',                                  // Local override (optional)
];
for (const p of envPaths) {
  if (existsSync(p)) {
    config({ path: p, override: true });
    console.log(`[env] Loaded ${p}`);
  }
}

async function main() {
  console.log('Bot starting...');

  // Validate required env vars
  const required = ['ANTHROPIC_API_KEY', 'SLACK_BOT_TOKEN', 'SLACK_APP_TOKEN'];
  const missing = required.filter((k) => !process.env[k]);
  if (missing.length > 0) {
    console.error(`Missing required env vars: ${missing.join(', ')}`);
    console.error('Checked: ~/.clawdbot/.env, .env, and environment');
    process.exit(1);
  }

  // Start Slack adapter
  warmAgentPool();
  const slack = new SlackAdapter(handleMessage);
  await slack.start();
  console.log('[bot] Slack adapter connected');

  // Start cron schedules
  await startCron();
  console.log('[bot] Cron schedules loaded');

  console.log('Bot ready');

  // Graceful shutdown
  const shutdown = async () => {
    console.log('\n[bot] Shutting down...');
    stopCron();
    await slack.stop();
    process.exit(0);
  };

  process.on('SIGINT', shutdown);
  process.on('SIGTERM', shutdown);
}

main().catch((err) => {
  console.error('[bot] Fatal error:', err);
  process.exit(1);
});
