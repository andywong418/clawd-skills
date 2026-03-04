import { App, type SlackEventMiddlewareArgs, type AllMiddlewareArgs } from '@slack/bolt';
import type { IncomingMessage, OutgoingMessage, PlatformAdapter, MessageHandler } from './types.js';

const MAX_CONCURRENT = 3;
const STREAM_DEBOUNCE_MS = 3000;
const SLACK_MAX_TEXT = 3900;

export class SlackAdapter implements PlatformAdapter {
  platform = 'slack' as const;
  private app: App;
  private handler: MessageHandler;
  private botUserId: string | null = null;

  // Concurrency control
  private seenEvents = new Set<string>();
  private activeQueries = 0;
  private requestQueue: Array<{ event: any; client: any; resolve: () => void }> = [];

  constructor(handler: MessageHandler) {
    this.handler = handler;

    this.app = new App({
      token: process.env.SLACK_BOT_TOKEN,
      appToken: process.env.SLACK_APP_TOKEN,
      socketMode: true,
      logLevel: (process.env.SLACK_LOG_LEVEL as any) || 'warn',
    });

    this.setupListeners();
  }

  private setupListeners(): void {
    this.app.use(async ({ body, next }) => {
      console.log(`[slack:event] type=${(body as any).event?.type || body.type} subtype=${(body as any).event?.subtype || ''} channel=${(body as any).event?.channel || ''}`);
      await next();
    });

    this.app.event('app_mention', async ({ event, say, client }) => {
      console.log(`[slack:mention] from=${event.user} channel=${event.channel} text=${(event as any).text?.slice(0, 80)}`);
      this.enqueueEvent(event, client).catch((err) =>
        console.error('[slack] Unhandled error in enqueueEvent:', err),
      );
    });

    this.app.event('message', async ({ event, say, client }) => {
      const msg = event as any;
      if (msg.subtype) return;
      if (msg.bot_id || msg.user === this.botUserId) return;

      const isDM = msg.channel_type === 'im';
      const mentionsBot = this.botUserId && msg.text?.includes(`<@${this.botUserId}>`);

      if (!isDM && !mentionsBot) return;

      this.enqueueEvent(msg, client).catch((err) =>
        console.error('[slack] Unhandled error in enqueueEvent:', err),
      );
    });
  }

  private async enqueueEvent(event: any, client: any): Promise<void> {
    const eventKey = `${event.channel}:${event.event_ts || event.ts}`;
    if (this.seenEvents.has(eventKey)) {
      console.log(`[slack] Skipping duplicate event: ${eventKey}`);
      return;
    }
    this.seenEvents.add(eventKey);
    setTimeout(() => this.seenEvents.delete(eventKey), 5 * 60 * 1000);

    if (this.activeQueries >= MAX_CONCURRENT) {
      console.log(`[slack] Queuing request (${this.activeQueries}/${MAX_CONCURRENT} active): ${eventKey}`);
      await new Promise<void>((resolve) => {
        this.requestQueue.push({ event, client, resolve });
      });
    }

    this.activeQueries++;
    console.log(`[slack] Processing (${this.activeQueries}/${MAX_CONCURRENT} active): ${eventKey}`);

    try {
      await this.processEvent(event, client);
    } finally {
      this.activeQueries--;
      this.processNextInQueue();
    }
  }

  private processNextInQueue(): void {
    if (this.requestQueue.length > 0 && this.activeQueries < MAX_CONCURRENT) {
      const next = this.requestQueue.shift()!;
      next.resolve();
    }
  }

  private async processEvent(event: any, client: any): Promise<void> {
    const threadTs = event.thread_ts || event.ts;
    let thinkingTs: string | undefined;

    let lastStreamUpdate = 0;
    let streamTimer: ReturnType<typeof setTimeout> | undefined;
    let latestStreamText = '';
    let isStreaming = true;
    let hasReceivedFirstChunk = false;

    let thinkingInterval: ReturnType<typeof setInterval> | undefined;
    let thinkingDots = 0;
    const thinkingFrames = ['_thinking._', '_thinking.._', '_thinking..._'];

    try {
      try {
        const thinkingMsg = await client.chat.postMessage({
          channel: event.channel,
          thread_ts: threadTs,
          text: '_thinking..._',
        });
        thinkingTs = thinkingMsg.ts;

        thinkingInterval = setInterval(async () => {
          if (hasReceivedFirstChunk || !thinkingTs) return;
          try {
            await client.chat.update({
              channel: event.channel,
              ts: thinkingTs,
              text: thinkingFrames[thinkingDots % thinkingFrames.length],
            });
            thinkingDots++;
          } catch { /* non-critical */ }
        }, 4000);
      } catch (err) {
        console.error('[slack] Failed to post thinking message:', err);
      }

      const toPreview = (text: string): string => {
        const trimmed = text.trim();
        if (trimmed.length < 10) return '';
        if (trimmed.length <= 100) return trimmed + '...';
        const cut = trimmed.lastIndexOf(' ', 100);
        return trimmed.slice(0, cut > 30 ? cut : 100) + '...';
      };

      const updateStreamDisplay = async (text: string) => {
        if (!thinkingTs || !isStreaming) return;
        const preview = toPreview(text);
        if (!preview) return;

        const now = Date.now();
        const timeSinceLastUpdate = now - lastStreamUpdate;

        const doUpdate = async () => {
          lastStreamUpdate = Date.now();
          try {
            await client.chat.update({
              channel: event.channel,
              ts: thinkingTs!,
              text: preview,
            });
          } catch { /* non-critical */ }
        };

        if (timeSinceLastUpdate >= STREAM_DEBOUNCE_MS) {
          await doUpdate();
        } else {
          if (streamTimer) clearTimeout(streamTimer);
          streamTimer = setTimeout(doUpdate, STREAM_DEBOUNCE_MS - timeSinceLastUpdate);
        }
      };

      const onStream = (text: string) => {
        if (!hasReceivedFirstChunk) {
          hasReceivedFirstChunk = true;
          if (thinkingInterval) clearInterval(thinkingInterval);
        }
        latestStreamText = text;
        updateStreamDisplay(text);
      };

      const TOOL_LABELS: Record<string, string> = {
        Bash: 'Running command',
        Read: 'Reading file',
        Write: 'Writing file',
        Edit: 'Editing file',
        Glob: 'Searching files',
        Grep: 'Searching code',
        WebSearch: 'Searching web',
        WebFetch: 'Fetching URL',
      };
      const onToolProgress = (toolName: string, elapsedSec: number) => {
        if (!thinkingTs || hasReceivedFirstChunk) return;
        const label = TOOL_LABELS[toolName] || `Running ${toolName}`;
        const sec = Math.round(elapsedSec);
        const text = sec > 0 ? `_${label} (${sec}s)..._` : `_${label}..._`;
        client.chat.update({
          channel: event.channel,
          ts: thinkingTs,
          text,
        }).catch(() => { /* non-critical */ });
      };

      const msg = await this.toIncomingMessage(event, client);
      console.log(`[slack] Calling handler for: ${msg.text.slice(0, 60)}`);
      const response = await this.handler(msg, onStream, onToolProgress);

      isStreaming = false;
      if (streamTimer) clearTimeout(streamTimer);
      if (thinkingInterval) clearInterval(thinkingInterval);

      if (response) {
        const chunks = splitMessage(response, 3900);

        if (thinkingTs && chunks.length === 1) {
          try {
            await client.chat.update({
              channel: event.channel,
              ts: thinkingTs,
              text: chunks[0],
            });
            thinkingTs = undefined;
          } catch (err) {
            console.error('[slack] Failed to update thinking message, posting new:', err);
            await this.sendMessage(event.channel, { text: response, threadId: threadTs });
          }
        } else {
          if (thinkingTs) {
            try {
              await client.chat.delete({ channel: event.channel, ts: thinkingTs });
            } catch { /* non-critical */ }
            thinkingTs = undefined;
          }
          await this.sendMessage(event.channel, { text: response, threadId: threadTs });
        }
      } else {
        if (thinkingTs) {
          try {
            await client.chat.update({
              channel: event.channel,
              ts: thinkingTs,
              text: 'Done (no output)',
            });
            thinkingTs = undefined;
          } catch { /* non-critical */ }
        }
      }

      if (thinkingTs) {
        try {
          await client.chat.delete({ channel: event.channel, ts: thinkingTs });
        } catch { /* non-critical */ }
      }

      try {
        await client.reactions.add({
          channel: event.channel,
          timestamp: event.ts,
          name: 'white_check_mark',
        });
      } catch { /* non-critical */ }

    } catch (err) {
      isStreaming = false;
      if (streamTimer) clearTimeout(streamTimer);
      if (thinkingInterval) clearInterval(thinkingInterval);
      console.error('[slack] Error processing message:', err);

      if (thinkingTs) {
        try {
          await client.chat.update({
            channel: event.channel,
            ts: thinkingTs,
            text: 'Hit an error processing that. Try again?',
          });
        } catch { /* non-critical */ }
      }

      try {
        await client.reactions.add({
          channel: event.channel,
          timestamp: event.ts,
          name: 'x',
        });
      } catch { /* non-critical */ }
    }
  }

  private async toIncomingMessage(event: any, client: any): Promise<IncomingMessage> {
    let channelName: string | undefined;
    try {
      const info = await client.conversations.info({ channel: event.channel });
      channelName = info.channel?.name;
    } catch { }

    let userName = event.user || 'unknown';
    try {
      const userInfo = await client.users.info({ user: event.user });
      userName = userInfo.user?.real_name || userInfo.user?.name || event.user;
    } catch { }

    const attachments = await this.processAttachments(event.files, client);

    let text = event.text || '';
    if (this.botUserId) {
      text = text.replace(new RegExp(`<@${this.botUserId}>\\s*`, 'g'), '').trim();
    }

    // Auto-read thread context when message is in a thread
    const isInThread = event.thread_ts && event.thread_ts !== event.ts;
    if (isInThread) {
      try {
        const replies = await client.conversations.replies({
          channel: event.channel,
          ts: event.thread_ts,
          limit: 50,
        });
        if (replies.messages && replies.messages.length > 1) {
          const threadMsgs = replies.messages
            .filter((m: any) => m.ts !== event.ts)
            .map((m: any) => {
              const who = m.user === this.botUserId ? '(you)' : (m.user || 'bot');
              return `[${who}]: ${m.text || '(attachment)'}`;
            })
            .join('\n');
          text = `[Thread context — ${replies.messages.length - 1} prior messages]\n${threadMsgs}\n\n[Current message]\n${text}`;
        }
      } catch {
        // Non-critical — proceed without thread context
      }
    }

    return {
      platform: 'slack',
      channelId: event.channel,
      channelName,
      threadId: event.thread_ts || event.ts,
      userId: event.user,
      userName,
      text,
      attachments,
      isDM: event.channel_type === 'im',
      isMention: !!event.text?.includes(`<@${this.botUserId}>`),
      raw: event,
    };
  }

  private async processAttachments(files: any[] | undefined, client: any) {
    if (!files?.length) return [];

    return files.map((file: any) => {
      const typeMap: Record<string, 'image' | 'video' | 'file'> = {
        image: 'image',
        video: 'video',
      };
      const mainType = file.mimetype?.split('/')[0];

      return {
        type: typeMap[mainType] || 'file',
        url: file.url_private,
        filename: file.name,
        mimeType: file.mimetype,
      };
    });
  }

  async start(): Promise<void> {
    await this.app.start();

    try {
      const auth = await this.app.client.auth.test();
      this.botUserId = auth.user_id || null;
      console.log(`[slack] Connected as ${auth.user} (${this.botUserId})`);
    } catch (err) {
      console.error('[slack] Failed to get bot identity:', err);
    }
  }

  async stop(): Promise<void> {
    await this.app.stop();
  }

  async sendMessage(channelId: string, message: OutgoingMessage): Promise<void> {
    const chunks = splitMessage(message.text, 3900);

    for (const chunk of chunks) {
      await this.app.client.chat.postMessage({
        channel: channelId,
        text: chunk,
        thread_ts: message.threadId,
        unfurl_links: false,
      });
    }
  }

  async addReaction(channelId: string, messageTs: string, emoji: string): Promise<void> {
    await this.app.client.reactions.add({
      channel: channelId,
      timestamp: messageTs,
      name: emoji,
    });
  }

  async uploadFile(channelId: string, file: Buffer | string, filename: string, threadId?: string): Promise<void> {
    const content = typeof file === 'string'
      ? await Bun.file(file).arrayBuffer()
      : new Uint8Array(file).buffer;

    const uploadRes = await this.app.client.files.getUploadURLExternal({
      filename,
      length: content.byteLength,
    });

    await fetch(uploadRes.upload_url!, {
      method: 'POST',
      body: content,
    });

    await this.app.client.files.completeUploadExternal({
      files: [{ id: uploadRes.file_id!, title: filename }],
      channel_id: channelId,
      thread_ts: threadId,
    });
  }
}

function splitMessage(text: string, maxLen: number): string[] {
  if (text.length <= maxLen) return [text];

  const chunks: string[] = [];
  let remaining = text;

  while (remaining.length > 0) {
    if (remaining.length <= maxLen) {
      chunks.push(remaining);
      break;
    }

    let splitIdx = remaining.lastIndexOf('\n', maxLen);
    if (splitIdx < maxLen * 0.5) {
      splitIdx = remaining.lastIndexOf(' ', maxLen);
    }
    if (splitIdx < maxLen * 0.3) {
      splitIdx = maxLen;
    }

    chunks.push(remaining.slice(0, splitIdx));
    remaining = remaining.slice(splitIdx).trimStart();
  }

  return chunks;
}
