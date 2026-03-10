import { query, type SDKUserMessage, type SDKMessage, type SDKResultMessage, type SettingSource } from '@anthropic-ai/claude-agent-sdk';
import { appendFileSync, mkdirSync } from 'fs';
import { join, dirname } from 'path';
import type { StreamCallback, ToolProgressCallback } from './adapters/types.js';
import { appendFileSync, mkdirSync } from 'fs';
import { join, dirname } from 'path';

type AgentSessionOptions = {
  model: string;
  maxTurns: number;
  maxBudgetUsd: number;
  cwd: string;
  allowedTools: string[];
  settingSources: SettingSource[];
  env: Record<string, string>;
};

class AsyncQueue<T> implements AsyncIterable<T>, AsyncIterator<T> {
  private queue: T[] = [];
  private resolvers: Array<(value: IteratorResult<T>) => void> = [];
  private closed = false;

  push(item: T): void {
    if (this.closed) {
      throw new Error('AsyncQueue is closed');
    }
    const resolve = this.resolvers.shift();
    if (resolve) {
      resolve({ value: item, done: false });
    } else {
      this.queue.push(item);
    }
  }

  close(): void {
    this.closed = true;
    while (this.resolvers.length > 0) {
      const resolve = this.resolvers.shift();
      if (resolve) resolve({ value: undefined as unknown as T, done: true });
    }
  }

  [Symbol.asyncIterator](): AsyncIterator<T> {
    return this;
  }

  async next(): Promise<IteratorResult<T>> {
    if (this.queue.length > 0) {
      return { value: this.queue.shift() as T, done: false };
    }
    if (this.closed) {
      return { value: undefined as unknown as T, done: true };
    }
    return new Promise((resolve) => {
      this.resolvers.push(resolve);
    });
  }
}

class AgentSession {
  readonly id: string;
  private input = new AsyncQueue<SDKUserMessage>();
  private sessionId: string | null = null;
  private currentResolve: ((value: string) => void) | null = null;
  private currentReject: ((err: Error) => void) | null = null;
  private currentStream: StreamCallback | null = null;
  private currentToolProgress: ToolProgressCallback | null = null;
  private currentText = '';
  private pending: Promise<void> = Promise.resolve();
  private closed = false;
  private query: ReturnType<typeof query>;

  // Memory tracking
  private turnCount = 0;
  private totalCost = 0;
  private querySnippets: string[] = [];
  private resultSnippets: string[] = [];
  private startedAt = Date.now();

  assignedKey: string | null = null;
  lastUsed = Date.now();
  busy = false;

  constructor(
    private options: AgentSessionOptions,
    private onClosed: (session: AgentSession) => void,
    id: string,
  ) {
    this.id = id;
    this.query = query({
      prompt: this.input,
      options: {
        model: this.options.model,
        maxTurns: this.options.maxTurns,
        ...(this.options.maxBudgetUsd > 0 ? { maxBudgetUsd: this.options.maxBudgetUsd } : {}),
        canUseTool: async () => ({ behavior: 'allow' as const }),
        cwd: this.options.cwd,
        allowedTools: this.options.allowedTools,
        settingSources: this.options.settingSources,
        env: this.options.env,
        includePartialMessages: true,
        stderr: (data: string) => {
          if (data.trim()) console.error(`[agent:stderr] ${data.trim()}`);
        },
      },
    });
    this.readLoop().catch((err) => {
      console.error(`[agent:session] Read loop failed (${this.id}):`, err);
      this.failCurrent(err instanceof Error ? err : new Error(String(err)));
      this.close();
    });
  }

  async run(promptText: string, onStream?: StreamCallback, onToolProgress?: ToolProgressCallback): Promise<string> {
    const task = async () => {
      if (this.closed) {
        throw new Error('Session is closed');
      }
      this.busy = true;
      this.lastUsed = Date.now();
      this.currentText = '';
      this.currentStream = onStream || null;
      this.currentToolProgress = onToolProgress || null;

      const resultPromise = new Promise<string>((resolve, reject) => {
        this.currentResolve = resolve;
        this.currentReject = reject;
      });

      // Track query for memory capture
      this.querySnippets.push(promptText.slice(0, 120));

      const userMessage: SDKUserMessage = {
        type: 'user',
        message: {
          role: 'user',
          content: [{ type: 'text', text: promptText }],
        },
        parent_tool_use_id: null,
        session_id: this.sessionId ?? '',
      };

      this.input.push(userMessage);

      try {
        const result = await resultPromise;
        return result;
      } finally {
        this.busy = false;
        this.lastUsed = Date.now();
      }
    };

    const chained = this.pending.then(task, task);
    this.pending = chained.then(() => undefined, () => undefined);
    return chained;
  }

  close(): void {
    if (this.closed) return;
    this.closed = true;
    // Capture memory before destroying the session
    if (this.turnCount > 0 && this.assignedKey) {
      this.captureSessionMemory();
    }
    try {
      this.input.close();
      this.query.close();
    } catch {
      // ignore
    }
    this.onClosed(this);
  }

  private captureSessionMemory(): void {
    try {
      const duration = Math.round((Date.now() - this.startedAt) / 1000);
      const mins = Math.floor(duration / 60);
      const secs = duration % 60;
      const entry = [
        '',
        `### Session ${this.id} (${this.assignedKey})`,
        `- Time: ${new Date().toISOString()} (duration: ${mins}m${secs}s)`,
        `- Turns: ${this.turnCount}, Cost: $${this.totalCost.toFixed(4)}`,
        `- Queries: ${this.querySnippets.join(' → ')}`,
        `- Last result: ${this.resultSnippets[this.resultSnippets.length - 1] || 'none'}`,
        '',
      ].join('\n');

      const today = new Date().toISOString().split('T')[0];
      const dailyFile = join(this.options.cwd, 'memory', `${today}.md`);
      mkdirSync(dirname(dailyFile), { recursive: true });
      appendFileSync(dailyFile, entry);
      console.log(`[memory] Captured session ${this.id} → memory/${today}.md`);
    } catch (e) {
      console.error(`[memory] Failed to capture session ${this.id}:`, e);
    }
  }

  private failCurrent(err: Error): void {
    if (this.currentReject) {
      this.currentReject(err);
    }
    this.currentResolve = null;
    this.currentReject = null;
    this.currentStream = null;
  }

  private resolveCurrent(text: string): void {
    if (this.currentResolve) {
      this.currentResolve(text);
    }
    this.currentResolve = null;
    this.currentReject = null;
    this.currentStream = null;
    this.currentToolProgress = null;
  }

  private handleStreamEvent(message: any): void {
    if (message.parent_tool_use_id !== null) return;
    const event = message.event;
    if (!event || typeof event.type !== 'string') return;

    if (event.type === 'message_start') {
      this.currentText = '';
      return;
    }
    if (event.type === 'content_block_delta' && event.delta?.type === 'text_delta') {
      const delta = event.delta.text || '';
      if (!delta) return;
      this.currentText += delta;
      if (this.currentStream) {
        this.currentStream(this.currentText);
      }
    }
  }

  private handleResult(message: SDKResultMessage): void {
    const cost = (message as any).total_cost_usd;
    const turns = (message as any).num_turns;
    this.turnCount += turns || 0;
    this.totalCost += cost || 0;

    if (message.subtype === 'success') {
      this.resultSnippets.push((message.result || '').slice(0, 200));
      this.resolveCurrent(message.result || '');
      return;
    }
    if (message.subtype === 'error_max_turns') {
      console.log(`[agent:session] Hit max turns limit in session ${this.id}`);
      const text = (message as any).result || 'I ran out of steps (hit the turn limit). Could you try a simpler ask, or break it into smaller parts?';
      this.resolveCurrent(text);
      return;
    }
    if (message.subtype === 'error_max_budget_usd') {
      console.log(`[agent:session] Hit budget limit in session ${this.id}`);
      this.resolveCurrent('I hit the spending limit for this session. Let me know if you want me to continue.');
      return;
    }
    // Log other error types
    console.log(`[agent:session] Result with subtype: ${message.subtype}`);
    this.resolveCurrent('Something went wrong — try again?');
  }

  private async readLoop(): Promise<void> {
    for await (const message of this.query as AsyncIterable<SDKMessage>) {
      if (message.type === 'system' && (message as any).subtype === 'init') {
        const sid = (message as any).session_id;
        if (sid) this.sessionId = sid;
        continue;
      }
      // Detect compaction events
      if (message.type === 'system' && (message as any).subtype === 'compact_boundary') {
        const meta = (message as any).compact_metadata;
        console.log(`[agent:session] Context compaction triggered (trigger: ${meta?.trigger}, pre_tokens: ${meta?.pre_tokens})`);
        // Save compaction notice to SESSION-STATE.md so context loss is detectable
        try {
          const stateFile = join(this.options.cwd, 'memory', 'SESSION-STATE.md');
          mkdirSync(dirname(stateFile), { recursive: true });
          const timestamp = new Date().toISOString();
          const notice = `\n---\n[COMPACTION - ${timestamp}]\nContext auto-compacted in session ${this.id} (key: ${this.assignedKey ?? 'unassigned'})\nPre-compaction tokens: ${meta?.pre_tokens ?? 'unknown'}. Trigger: ${meta?.trigger ?? 'unknown'}.\nRe-read memory/MEMORY.md and today's daily notes if context is unclear.\n`;
          appendFileSync(stateFile, notice);
        } catch (e) {
          console.error('[agent:session] Failed to write SESSION-STATE.md compaction notice:', e);
        }
        continue;
      }
      // Detect status changes (compacting, etc.)
      if (message.type === 'system' && (message as any).subtype === 'status') {
        const status = (message as any).status;
        if (status === 'compacting') {
          console.log(`[agent:session] Session ${this.id} is compacting context...`);
        }
        continue;
      }
      if (message.type === 'stream_event') {
        this.handleStreamEvent(message);
        continue;
      }
      if (message.type === 'tool_progress' && this.currentToolProgress) {
        const tp = message as any;
        if (tp.parent_tool_use_id === null && tp.tool_name) {
          this.currentToolProgress(tp.tool_name, tp.elapsed_time_seconds || 0);
        }
        continue;
      }
      if (message.type === 'result') {
        this.handleResult(message as SDKResultMessage);
        continue;
      }
    }
  }
}

type SessionPoolOptions = {
  sessionOptions: AgentSessionOptions;
  maxSessions: number;
  sessionTtlMs: number;
  warmPool: number;
};

export class AgentSessionPool {
  private sessions = new Set<AgentSession>();
  private sessionsByKey = new Map<string, AgentSession>();
  private warmPool: AgentSession[] = [];
  private cleanupTimer: ReturnType<typeof setInterval> | null = null;
  private nextId = 1;

  constructor(private options: SessionPoolOptions) {
    this.ensureWarmPool();
  }

  startCleanup(intervalMs: number): void {
    if (this.cleanupTimer) return;
    this.cleanupTimer = setInterval(() => this.cleanup(), intervalMs);
  }

  stopCleanup(): void {
    if (!this.cleanupTimer) return;
    clearInterval(this.cleanupTimer);
    this.cleanupTimer = null;
  }

  async run(key: string, promptText: string, onStream?: StreamCallback, onToolProgress?: ToolProgressCallback): Promise<string> {
    const session = await this.getSession(key);
    return session.run(promptText, onStream, onToolProgress);
  }

  forceCloseSession(key: string): void {
    const session = this.sessionsByKey.get(key);
    if (session) {
      console.log(`[agent:pool] Force-closing stuck session for key: ${key}`);
      this.sessionsByKey.delete(key);
      session.close();
    }
  }

  closeAll(): void {
    for (const session of this.sessions) {
      session.close();
    }
    this.sessions.clear();
    this.sessionsByKey.clear();
    this.warmPool = [];
  }

  private ensureWarmPool(): void {
    while (this.warmPool.length < this.options.warmPool && this.sessions.size < this.options.maxSessions) {
      const session = this.createSession();
      this.warmPool.push(session);
    }
  }

  private createSession(): AgentSession {
    const id = `session-${this.nextId++}`;
    const session = new AgentSession(this.options.sessionOptions, (closed) => {
      this.sessions.delete(closed);
      if (closed.assignedKey) {
        this.sessionsByKey.delete(closed.assignedKey);
      } else {
        this.warmPool = this.warmPool.filter((s) => s !== closed);
      }
      this.ensureWarmPool();
    }, id);
    this.sessions.add(session);
    return session;
  }

  private async getSession(key: string): Promise<AgentSession> {
    const existing = this.sessionsByKey.get(key);
    if (existing) return existing;

    let session = this.warmPool.pop() || null;
    if (!session && this.sessions.size < this.options.maxSessions) {
      session = this.createSession();
    }

    if (!session) {
      // At capacity: try to evict an idle session
      const idle = Array.from(this.sessions)
        .filter((s) => !s.busy && s.assignedKey)
        .sort((a, b) => a.lastUsed - b.lastUsed)[0];
      if (idle) {
        if (idle.assignedKey) this.sessionsByKey.delete(idle.assignedKey);
        idle.close();
        session = this.createSession();
      }
    }

    if (!session) {
      throw new Error('Agent is at capacity. Try again in a minute.');
    }

    session.assignedKey = key;
    this.sessionsByKey.set(key, session);
    return session;
  }

  private cleanup(): void {
    const now = Date.now();
    for (const session of Array.from(this.sessions)) {
      if (session.busy) continue;
      if (session.assignedKey && now - session.lastUsed > this.options.sessionTtlMs) {
        this.sessionsByKey.delete(session.assignedKey);
        session.close();
      }
    }
    this.ensureWarmPool();
  }
}
