import cron from 'node-cron';
import { query } from '@anthropic-ai/claude-agent-sdk';
import { spawn, type ChildProcess } from 'child_process';
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

/** Kill a subprocess tree (process + children). */
function killProcessTree(proc: ChildProcess): void {
  if (!proc.pid || proc.killed) return;
  try {
    process.kill(-proc.pid, 'SIGTERM');
  } catch {
    try { proc.kill('SIGTERM'); } catch { /* already dead */ }
  }
  setTimeout(() => {
    if (!proc.killed) {
      try { proc.kill('SIGKILL'); } catch { /* ignore */ }
    }
  }, 5000);
}

async function executeSchedule(schedule: Schedule): Promise<void> {
  console.log(`[cron] Executing schedule: ${schedule.name}`);
  const startTime = Date.now();
  let childProc: ChildProcess | null = null;

  const systemAppend = schedule.channelId
    ? `\n\nThis is a scheduled task: "${schedule.name}"\nPost results to Slack channel ${schedule.channelId} using the slack_send_message tool.`
    : `\n\nThis is a scheduled task: "${schedule.name}"`;

  try {
    let result = '';
    const q = query({
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
        thinking: { type: 'adaptive' as const },
        effort: 'high' as const,
        canUseTool: async () => ({ behavior: 'allow' as const }),
        cwd: BOT_WORKSPACE,
        maxTurns: 30,
        ...(schedule.maxBudgetUsd ? { maxBudgetUsd: schedule.maxBudgetUsd } : {}),
        model: schedule.model || 'claude-opus-4-6',
        settingSources: ['project'],
        env: { ...process.env } as Record<string, string>,
        spawnClaudeCodeProcess: (opts: { command: string; args: string[]; cwd: string; env: Record<string, string> }) => {
          const proc = spawn(opts.command, opts.args, {
            cwd: opts.cwd,
            env: opts.env,
            stdio: ['pipe', 'pipe', 'pipe'],
            detached: false,
          });
          childProc = proc;
          return proc;
        },
      },
    });

    for await (const message of q) {
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
  } finally {
    if (childProc) {
      killProcessTree(childProc);
      console.log(`[cron] Killed subprocess for "${schedule.name}"`);
    }
  }
}

/** Kill orphaned agent-sdk processes older than 20 minutes. Safety net. */
async function cleanupOrphanedProcesses(): Promise<void> {
  try {
    const proc = Bun.spawn(['bash', '-c',
      `ps aux | grep 'claude-agent-sdk' | grep -v grep | awk '{print $2}' | while read pid; do
        if [ "$pid" != "$$" ] && [ "$pid" != "${process.pid}" ]; then
          elapsed=$(ps -o etimes= -p $pid 2>/dev/null | tr -d ' ')
          if [ -n "$elapsed" ] && [ "$elapsed" -gt 1200 ]; then
            echo "Killing orphaned agent-sdk process $pid (age: ${elapsed}s)"
            kill -TERM $pid 2>/dev/null
            sleep 2
            kill -9 $pid 2>/dev/null
          fi
        fi
      done`
    ], { stdout: 'pipe', stderr: 'pipe' });
    await proc.exited;
    const stdout = await new Response(proc.stdout).text();
    if (stdout.trim()) {
      console.log(`[cron:cleanup] ${stdout.trim()}`);
    }
  } catch {
    // Ignore cleanup errors
  }
}

function setupDefaultSchedules(): void {
  // Heartbeat — every 30 minutes
  const heartbeat = cron.schedule('*/30 * * * *', () => {
    executeSchedule({
      id: 'default-heartbeat',
      name: 'Heartbeat',
      cronExpression: '*/30 * * * *',
      prompt: 'Read HEARTBEAT.md if it exists (workspace context). Follow it strictly. Do not infer or repeat old tasks from prior chats. If nothing needs attention, reply HEARTBEAT_OK.',
      enabled: true,
    });
  });
  activeTasks.set('default-heartbeat', heartbeat);
  console.log('[cron] Scheduled default heartbeat — every 30 minutes');

  // Memory maintenance — every 6 hours
  const memMaintenance = cron.schedule('0 */6 * * *', () => {
    executeSchedule({
      id: 'default-memory-maintenance',
      name: 'Memory Maintenance',
      cronExpression: '0 */6 * * *',
      prompt: 'Review recent memory files in memory/. Distill important events and lessons into MEMORY.md. Clean up stale entries.',
      enabled: true,
    });
  });
  activeTasks.set('default-memory-maintenance', memMaintenance);
  console.log('[cron] Scheduled default memory-maintenance — every 6 hours');
}

export async function startCron(): Promise<void> {
  const schedules = loadSchedules();

  if (schedules.length === 0) {
    console.log('[cron] No schedules.json found. Using defaults.');
    setupDefaultSchedules();
  } else {
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

  // Always run: orphan process cleanup every 10 minutes
  cron.schedule('*/10 * * * *', () => {
    cleanupOrphanedProcesses();
  });
  console.log('[cron] Scheduled orphan process cleanup — every 10 minutes');
}

export function stopCron(): void {
  for (const [id, task] of activeTasks) {
    task.stop();
  }
  activeTasks.clear();
  console.log('[cron] All schedules stopped');
}
