import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'fs';
import { join } from 'path';
import type { IncomingMessage } from './adapters/types.js';

const SESSIONS_DIR = join(process.env.BOT_WORKSPACE || '/root/clawd', 'memory', 'sessions');

export interface Session {
  id: string;
  platform: string;
  channelId: string;
  threadId: string;
  type: string;
  status: string;
  metadata: Record<string, unknown>;
  events: SessionEvent[];
  createdAt: string;
  updatedAt: string;
}

export interface SessionEvent {
  id: string;
  type: string;
  data: Record<string, unknown>;
  createdAt: string;
}

// Ensure sessions directory exists
function ensureDir(): void {
  if (!existsSync(SESSIONS_DIR)) {
    mkdirSync(SESSIONS_DIR, { recursive: true });
  }
}

function sessionKey(platform: string, channelId: string, threadId: string): string {
  // Sanitize for filesystem — replace colons and slashes
  return `${platform}_${channelId}_${threadId}`.replace(/[/:]/g, '_');
}

function sessionPath(key: string): string {
  return join(SESSIONS_DIR, `${key}.json`);
}

function readSession(key: string): Session | null {
  const path = sessionPath(key);
  if (!existsSync(path)) return null;
  try {
    return JSON.parse(readFileSync(path, 'utf-8'));
  } catch {
    return null;
  }
}

function writeSession(session: Session): void {
  ensureDir();
  const key = sessionKey(session.platform, session.channelId, session.threadId);
  writeFileSync(sessionPath(key), JSON.stringify(session, null, 2));
}

export async function lookupSession(msg: IncomingMessage): Promise<Session | null> {
  const key = sessionKey(msg.platform, msg.channelId, msg.threadId);
  return readSession(key);
}

export async function createSession(msg: IncomingMessage, type: string): Promise<Session> {
  const now = new Date().toISOString();
  const id = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

  const session: Session = {
    id,
    platform: msg.platform,
    channelId: msg.channelId,
    threadId: msg.threadId,
    type,
    status: 'active',
    metadata: {
      channelName: msg.channelName,
      userName: msg.userName,
      userId: msg.userId,
    },
    events: [],
    createdAt: now,
    updatedAt: now,
  };

  writeSession(session);
  return session;
}

export async function logSessionEvent(
  sessionId: string,
  type: string,
  data: Record<string, unknown>,
): Promise<void> {
  try {
    ensureDir();
    const { readdirSync } = await import('fs');
    const files = readdirSync(SESSIONS_DIR).filter((f) => f.endsWith('.json'));

    for (const file of files) {
      const path = join(SESSIONS_DIR, file);
      try {
        const session: Session = JSON.parse(readFileSync(path, 'utf-8'));
        if (session.id === sessionId) {
          const event: SessionEvent = {
            id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
            type,
            data,
            createdAt: new Date().toISOString(),
          };
          // Keep last 50 events to prevent unbounded growth
          session.events = [...session.events.slice(-49), event];
          session.updatedAt = new Date().toISOString();
          writeFileSync(path, JSON.stringify(session, null, 2));
          return;
        }
      } catch {
        // Skip corrupted files
      }
    }
  } catch {
    // Non-critical — don't fail the message flow
  }
}
