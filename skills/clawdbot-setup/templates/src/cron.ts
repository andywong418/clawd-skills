import cron from 'node-cron';
import { query } from '@anthropic-ai/claude-agent-sdk';
import { existsSync, readFileSync } from 'fs';
import { join } from 'path';

const BOT_WORKSPACE = process.env.BOT_WORKSPACE || '/root/clawd';
const SCHEDULES_PATH = join(BOT_WORKSPACE, 'schedules.json');

interface Schedule {
  id: string;
  name: string;
  cronExpression: string;
  prompt: string;
  channelId?: string;
  model?: string;
  maxBudgetUsd?: number;
  enabled: boolean;
}

const activeTasks = new Map<string, cron.ScheduledTask>();

function loadSchedules(): Schedule[] {
  if (existsSync(SCHEDULES_PATH)) {
    try {
      const data = JSON.parse(readFileSync(SCHEDULES_PATH, 'utf-8'));
      return Array.isArray(data) ? data.filter((s: Schedule) => s.enabled) : [];
    } catch (err) {
      console.warn('[cron] Failed to parse schedules.json:', err);
      return [];
    }
  }
  return [];
}

async function executeSchedule(schedule: Schedule): Promise<void> {
  console.log(`[cron] Executing schedule: ${schedule.name}`);
  const startTime = Date.now();

  const systemAppend = schedule.channelId
    ? `\n\nThis is a scheduled task: "${schedule.name}"\nPost results to Slack channel ${schedule.channelId} using the slack_send_message tool.`
    : `\n\nThis is a scheduled task: "${schedule.name}"`;

  try {
    let result = '';
    for await (const message of query({
      prompt: schedule.prompt,
      options: {
        systemPrompt: {
          type: 'preset',
          preset: 'claude_code',
          append: systemAppend,
        },
        allowedTools: [
          'Read', 'Write', 'Edit', 'Bash', 'Glob', 'Grep',
          'WebSearch', 'WebFetch',
        ],
        canUseTool: async () => ({ behavior: 'allow' as const }),
        cwd: BOT_WORKSPACE,
        maxTurns: 30,
        ...(schedule.maxBudgetUsd ? { maxBudgetUsd: schedule.maxBudgetUsd } : {}),
        model: schedule.model || 'claude-sonnet-4-6',
        settingSources: ['project'],
        env: { ...process.env } as Record<string, string>,
      },
    })) {
      if (message.type === 'result') {
        if (message.subtype === 'success') {
          result = message.result;
        } else {
          const errors = 'errors' in message ? (message.errors as string[]).join(', ') : '';
          console.error(`[cron] Schedule "${schedule.name}" ended with ${message.subtype}: ${errors}`);
        }
      }
    }

    const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
    console.log(`[cron] Schedule "${schedule.name}" completed in ${elapsed}s`);
  } catch (err) {
    console.error(`[cron] Schedule "${schedule.name}" failed:`, err);
  }
}

function setupDefaultSchedules(): void {
  // Memory distillation — every 6 hours
  // Auto-captured session logs in memory/YYYY-MM-DD.md get distilled into MEMORY.md
  const memMaintenance = cron.schedule('0 */6 * * *', () => {
    const today = new Date().toISOString().split('T')[0];
    const yesterday = new Date(Date.now() - 86400000).toISOString().split('T')[0];
    executeSchedule({
      id: 'default-memory-maintenance',
      name: 'Memory Distill',
      cronExpression: '0 */6 * * *',
      prompt: `Review memory/${today}.md and memory/${yesterday}.md (the auto-captured session logs). Distill any important lessons, decisions, patterns, or context into MEMORY.md. Remove duplicates and stale entries. Keep MEMORY.md under 150 lines. This is internal housekeeping — do not post to Slack.`,
      enabled: true,
    });
  });
  activeTasks.set('default-memory-maintenance', memMaintenance);
  console.log('[cron] Scheduled default memory-distill — every 6 hours');
}

export async function startCron(): Promise<void> {
  const schedules = loadSchedules();

  if (schedules.length === 0) {
    console.log('[cron] No schedules.json found. Using defaults.');
    setupDefaultSchedules();
    return;
  }

  for (const schedule of schedules) {
    if (!cron.validate(schedule.cronExpression)) {
      console.warn(`[cron] Invalid cron expression for "${schedule.name}": ${schedule.cronExpression}`);
      continue;
    }

    const task = cron.schedule(schedule.cronExpression, () => {
      executeSchedule(schedule);
    });

    activeTasks.set(schedule.id, task);
    console.log(`[cron] Scheduled "${schedule.name}" — ${schedule.cronExpression}`);
  }
}

export function stopCron(): void {
  for (const [id, task] of activeTasks) {
    task.stop();
  }
  activeTasks.clear();
  console.log('[cron] All schedules stopped');
}
