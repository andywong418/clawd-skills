import type { IncomingMessage, StreamCallback, ToolProgressCallback } from './adapters/types.js';
import { lookupSession, logSessionEvent } from './sessions.js';
import { AgentSessionPool } from './agent-session-pool.js';

const BOT_WORKSPACE = process.env.BOT_WORKSPACE || '/root/clawd';
const DEFAULT_MODEL = process.env.BOT_MODEL || 'claude-sonnet-4-6';
const MAX_TURNS = parseInt(process.env.BOT_MAX_TURNS || '25', 10);
const MAX_BUDGET = parseFloat(process.env.BOT_MAX_BUDGET || '0');
const MAX_SESSIONS = parseInt(process.env.BOT_MAX_SESSIONS || '3', 10);
const SESSION_TTL_MS = parseInt(process.env.BOT_SESSION_TTL_MS || `${60 * 60 * 1000}`, 10);
const WARM_POOL = parseInt(process.env.BOT_WARM_POOL || '1', 10);
const ALLOWED_TOOLS = ['Read', 'Write', 'Edit', 'Bash', 'Glob', 'Grep', 'WebSearch', 'WebFetch'] as const;

// Bot name for session logging — change this for your bot
const BOT_NAME = process.env.BOT_NAME || 'bot';

let defaultPool: AgentSessionPool | null = null;
let opusPool: AgentSessionPool | null = null;

function buildPrompt(msg: IncomingMessage): string {
  const lines = [
    `Platform: ${msg.platform}`,
    `Channel: ${msg.channelName ? `#${msg.channelName} (${msg.channelId})` : msg.channelId}`,
    `Thread: ${msg.threadId}`,
    `User: ${msg.userName}`,
    `DM: ${msg.isDM}`,
  ];

  if (msg.attachments.length > 0) {
    const atts = msg.attachments
      .map((a) => `${a.filename || a.type} — ${a.url}`)
      .join(', ');
    lines.push(`Attachments: [${atts}]`);
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

function threadKey(msg: IncomingMessage): string {
  if (msg.isDM) return `${msg.platform}:${msg.channelId}`;
  return `${msg.platform}:${msg.channelId}:${msg.threadId}`;
}

function getDefaultPool(): AgentSessionPool {
  if (!defaultPool) {
    defaultPool = new AgentSessionPool({
      sessionOptions: {
        model: DEFAULT_MODEL,
        maxTurns: MAX_TURNS,
        maxBudgetUsd: MAX_BUDGET,
        cwd: BOT_WORKSPACE,
        allowedTools: [...ALLOWED_TOOLS],
        settingSources: ['project'],
        env: loadEnvVars(),
      },
      maxSessions: MAX_SESSIONS,
      sessionTtlMs: SESSION_TTL_MS,
      warmPool: WARM_POOL,
    });
    defaultPool.startCleanup(5 * 60 * 1000);
  }
  return defaultPool;
}

function getOpusPool(): AgentSessionPool {
  if (!opusPool) {
    opusPool = new AgentSessionPool({
      sessionOptions: {
        model: 'claude-opus-4-6',
        maxTurns: MAX_TURNS,
        maxBudgetUsd: MAX_BUDGET,
        cwd: BOT_WORKSPACE,
        allowedTools: [...ALLOWED_TOOLS],
        settingSources: ['project'],
        env: loadEnvVars(),
      },
      maxSessions: Math.max(1, Math.floor(MAX_SESSIONS / 2)),
      sessionTtlMs: SESSION_TTL_MS,
      warmPool: 0,
    });
    opusPool.startCleanup(5 * 60 * 1000);
  }
  return opusPool;
}

export function warmAgentPool(): void {
  getDefaultPool();
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

  const prompt = buildPrompt(msg);
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
      from: BOT_NAME,
      text: result.slice(0, 500),
    });
  }

  return result;
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
