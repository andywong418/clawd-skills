import type { IncomingMessage, StreamCallback, ToolProgressCallback } from './adapters/types.js';
import { lookupSession, logSessionEvent } from './sessions.js';
import { AgentSessionPool } from './agent-session-pool.js';
import { existsSync, readFileSync, statSync } from 'fs';
import { join } from 'path';

// Config getters - read at runtime to ensure env is loaded
const getConfig = () => ({
  workspace: process.env.BOT_WORKSPACE || '/root/clawd',
  model: process.env.BOT_MODEL || 'claude-opus-4-6',
  maxTurns: parseInt(process.env.BOT_MAX_TURNS || '25', 10),
  maxBudget: parseFloat(process.env.BOT_MAX_BUDGET || '0'),
  maxSessions: parseInt(process.env.BOT_MAX_SESSIONS || '3', 10),
  sessionTtlMs: parseInt(process.env.BOT_SESSION_TTL_MS || `${60 * 60 * 1000}`, 10),
  warmPool: parseInt(process.env.BOT_WARM_POOL || '1', 10),
});

const ALLOWED_TOOLS = ['Read', 'Write', 'Edit', 'Bash', 'Glob', 'Grep', 'WebSearch', 'WebFetch'] as const;

let defaultPool: AgentSessionPool | null = null;
let opusPool: AgentSessionPool | null = null;

function buildPrompt(msg: IncomingMessage, sessionState?: string | null): string {
  const lines = [
    `Platform: ${msg.platform}`,
    `Channel: ${msg.channelName ? `#${msg.channelName} (${msg.channelId})` : msg.channelId}`,
    `Thread: ${msg.threadId}`,
    `User: ${msg.userName}`,
    `DM: ${msg.isDM}`,
  ];

  if (msg.attachments.length > 0) {
    const atts = msg.attachments
      .map((a) => {
        const loc = (a as any).localPath || a.url;
        const label = a.filename || a.type;
        return `${label} — saved at ${loc} (use Read tool to view)`;
      })
      .join(', ');
    lines.push(`Attachments: [${atts}]`);
  }

  if (sessionState) {
    lines.push('', '--- Session State (from memory/SESSION-STATE.md) ---', sessionState, '--- End Session State ---');
  }

  lines.push('', `Message: ${msg.text}`);
  return lines.join('\n');
}

function loadEnvVars(): Record<string, string> {
  const env: Record<string, string> = {};
  for (const [key, val] of Object.entries(process.env)) {
    if (val) env[key] = val;
  }
  return env;
}

function loadSessionState(workspace: string): string | null {
  const statePath = join(workspace, 'memory', 'SESSION-STATE.md');
  try {
    if (!existsSync(statePath)) return null;
    const stat = statSync(statePath);
    const ageMs = Date.now() - stat.mtimeMs;
    if (ageMs > 2 * 60 * 60 * 1000) return null; // ignore if > 2 hours old
    const content = readFileSync(statePath, 'utf8').trim();
    return content || null;
  } catch {
    return null;
  }
}

function threadKey(msg: IncomingMessage): string {
  if (msg.isDM) return `${msg.platform}:${msg.channelId}`;
  return `${msg.platform}:${msg.channelId}:${msg.threadId}`;
}

function getDefaultPool(): AgentSessionPool {
  if (!defaultPool) {
    const cfg = getConfig();
    console.log(`[agent] Creating default pool: maxTurns=${cfg.maxTurns}, model=${cfg.model}, maxSessions=${cfg.maxSessions}`);
    defaultPool = new AgentSessionPool({
      sessionOptions: {
        model: cfg.model,
        maxTurns: cfg.maxTurns,
        maxBudgetUsd: cfg.maxBudget,
        cwd: cfg.workspace,
        allowedTools: [...ALLOWED_TOOLS],
        settingSources: ['project'],
        env: loadEnvVars(),
      },
      maxSessions: cfg.maxSessions,
      sessionTtlMs: cfg.sessionTtlMs,
      warmPool: cfg.warmPool,
    });
    defaultPool.startCleanup(5 * 60 * 1000);
  }
  return defaultPool;
}

function getOpusPool(): AgentSessionPool {
  if (!opusPool) {
    const cfg = getConfig();
    console.log(`[agent] Creating opus pool: maxTurns=${cfg.maxTurns}`);
    opusPool = new AgentSessionPool({
      sessionOptions: {
        model: 'claude-opus-4-6',
        maxTurns: cfg.maxTurns,
        maxBudgetUsd: cfg.maxBudget,
        cwd: cfg.workspace,
        allowedTools: [...ALLOWED_TOOLS],
        settingSources: ['project'],
        env: loadEnvVars(),
      },
      maxSessions: Math.max(1, Math.floor(cfg.maxSessions / 2)),
      sessionTtlMs: cfg.sessionTtlMs,
      warmPool: 0,
    });
    opusPool.startCleanup(5 * 60 * 1000);
  }
  return opusPool;
}

export function warmAgentPool(): void {
  getDefaultPool();
}

export function closeAllPools(): void {
  defaultPool?.closeAll();
  opusPool?.closeAll();
}

export async function handleMessage(msg: IncomingMessage, onStream?: StreamCallback, onToolProgress?: ToolProgressCallback): Promise<string> {
  const session = await lookupSession(msg);
  if (session) {
    await logSessionEvent(session.id, 'message', {
      from: msg.userName,
      text: msg.text,
      platform: msg.platform,
    });
  }

  const cfg = getConfig();
  const sessionState = loadSessionState(cfg.workspace);
  const prompt = buildPrompt(msg, sessionState);
  console.log(`[agent] Starting query for ${msg.userName}: ${msg.text.slice(0, 60)}`);

  let result = '';
  try {
    const pool = getDefaultPool();
    result = await pool.run(threadKey(msg), prompt, onStream, onToolProgress);
    console.log(`[agent] Query succeeded (${result.length} chars): ${result.slice(0, 100)}`);
  } catch (err) {
    console.error('[agent] Query failed:', err);
    result = err instanceof Error && err.message.includes('capacity')
      ? 'I am at capacity right now — try again in a minute?'
      : 'Sorry, I hit an error processing that. Try again?';
  }

  console.log(`[agent] Done. Result length: ${result.length}`);

  if (session && result) {
    await logSessionEvent(session.id, 'response', {
      from: 'naruto',
      text: result.slice(0, 500),
    });
  }

  return result;
}

/** Force-close a stuck session by its thread key. Called on hard timeout. */
export function cancelAgentSession(key: string): void {
  const pool = getDefaultPool();
  pool.forceCloseSession(key);
}

// For complex tasks, use Opus
export async function handleComplexMessage(msg: IncomingMessage, onStream?: StreamCallback, onToolProgress?: ToolProgressCallback): Promise<string> {
  const prompt = buildPrompt(msg);
  try {
    const pool = getOpusPool();
    return await pool.run(threadKey(msg), prompt, onStream, onToolProgress);
  } catch (err) {
    console.error('[agent] Opus query failed:', err);
    return 'Sorry, I hit an error processing that. Try again?';
  }
}
