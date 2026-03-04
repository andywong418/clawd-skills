import { query, type SDKUserMessage, type SDKMessage, type SDKResultMessage, type SettingSource } from '@anthropic-ai/claude-agent-sdk';
import type { StreamCallback, ToolProgressCallback } from './adapters/types.js';

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
        maxBudgetUsd: this.options.maxBudgetUsd,
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
    try {
      this.input.close();
      this.query.close();
    } catch {
      // ignore
    }
    this.onClosed(this);
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
    if (message.subtype === 'success') {
      this.resolveCurrent(message.result || '');
      return;
    }
    if (message.subtype === 'error_max_turns') {
      const text = (message as any).result || 'I ran out of steps processing that. Could you try a simpler ask, or break it into smaller parts?';
      this.resolveCurrent(text);
      return;
    }
    this.resolveCurrent('Something went wrong — try again?');
  }

  private async readLoop(): Promise<void> {
    for await (const message of this.query as AsyncIterable<SDKMessage>) {
      if (message.type === 'system' && (message as any).subtype === 'init') {
        const sid = (message as any).session_id;
        if (sid) this.sessionId = sid;
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
