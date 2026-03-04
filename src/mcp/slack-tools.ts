import { tool, createSdkMcpServer } from '@anthropic-ai/claude-agent-sdk';
import { z } from 'zod';

// Slack Web API base — uses bot token from env
const SLACK_TOKEN = () => process.env.SLACK_BOT_TOKEN!;

async function slackApi(method: string, body: Record<string, unknown>): Promise<unknown> {
  const res = await fetch(`https://slack.com/api/${method}`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${SLACK_TOKEN()}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (!data.ok) {
    throw new Error(`Slack API ${method} failed: ${data.error}`);
  }
  return data;
}

const sendMessage = tool(
  'slack_send_message',
  'Send a message to a Slack channel or thread',
  {
    channel: z.string().describe('Channel ID (e.g., C0AHBK5E9V3)'),
    text: z.string().describe('Message text (supports Slack mrkdwn formatting)'),
    thread_ts: z.string().optional().describe('Thread timestamp to reply in-thread'),
  },
  async ({ channel, text, thread_ts }) => {
    const body: Record<string, unknown> = { channel, text };
    if (thread_ts) body.thread_ts = thread_ts;
    const data = await slackApi('chat.postMessage', body) as { ts: string };
    return { content: [{ type: 'text' as const, text: `Message sent (ts: ${data.ts})` }] };
  },
);

const addReaction = tool(
  'slack_react',
  'Add an emoji reaction to a message',
  {
    channel: z.string().describe('Channel ID'),
    timestamp: z.string().describe('Message timestamp to react to'),
    emoji: z.string().describe('Emoji name without colons (e.g., "fire", "eyes", "thumbsup")'),
  },
  async ({ channel, timestamp, emoji }) => {
    await slackApi('reactions.add', { channel, timestamp, name: emoji });
    return { content: [{ type: 'text' as const, text: `Reacted with :${emoji}:` }] };
  },
);

const uploadFile = tool(
  'slack_upload_file',
  'Upload a file to a Slack channel',
  {
    channel: z.string().describe('Channel ID'),
    filepath: z.string().describe('Local file path to upload'),
    filename: z.string().optional().describe('Display filename'),
    title: z.string().optional().describe('File title'),
    thread_ts: z.string().optional().describe('Thread timestamp'),
    initial_comment: z.string().optional().describe('Message to post with the file'),
  },
  async ({ channel, filepath, filename, title, thread_ts, initial_comment }) => {
    // Step 1: Get upload URL
    const file = Bun.file(filepath);
    const bytes = await file.arrayBuffer();
    const name = filename || filepath.split('/').pop() || 'file';

    const uploadRes = await slackApi('files.getUploadURLExternal', {
      filename: name,
      length: bytes.byteLength,
    }) as { upload_url: string; file_id: string };

    // Step 2: Upload file content
    await fetch(uploadRes.upload_url, {
      method: 'POST',
      body: bytes,
    });

    // Step 3: Complete upload
    const completeBody: Record<string, unknown> = {
      files: [{ id: uploadRes.file_id, title: title || name }],
      channel_id: channel,
    };
    if (thread_ts) completeBody.thread_ts = thread_ts;
    if (initial_comment) completeBody.initial_comment = initial_comment;

    await slackApi('files.completeUploadExternal', completeBody);
    return { content: [{ type: 'text' as const, text: `File "${name}" uploaded to channel` }] };
  },
);

const readThread = tool(
  'slack_read_thread',
  'Read all messages in a Slack thread',
  {
    channel: z.string().describe('Channel ID'),
    thread_ts: z.string().describe('Thread timestamp'),
    limit: z.number().optional().describe('Max messages to return (default 50)'),
  },
  async ({ channel, thread_ts, limit }) => {
    const data = await slackApi('conversations.replies', {
      channel,
      ts: thread_ts,
      limit: limit || 50,
    }) as { messages: Array<{ user?: string; text: string; ts: string }> };

    const formatted = data.messages
      .map((m) => `[${m.ts}] ${m.user || 'bot'}: ${m.text}`)
      .join('\n');

    return { content: [{ type: 'text' as const, text: formatted || 'No messages in thread' }] };
  },
);

const readChannel = tool(
  'slack_read_channel',
  'Read recent messages from a Slack channel',
  {
    channel: z.string().describe('Channel ID'),
    limit: z.number().optional().describe('Max messages to return (default 20)'),
  },
  async ({ channel, limit }) => {
    const data = await slackApi('conversations.history', {
      channel,
      limit: limit || 20,
    }) as { messages: Array<{ user?: string; text: string; ts: string; thread_ts?: string }> };

    const formatted = data.messages
      .reverse()
      .map((m) => {
        const thread = m.thread_ts ? ` [thread: ${m.thread_ts}]` : '';
        return `[${m.ts}] ${m.user || 'bot'}: ${m.text}${thread}`;
      })
      .join('\n');

    return { content: [{ type: 'text' as const, text: formatted || 'No recent messages' }] };
  },
);

export function createSlackMcpServer() {
  return createSdkMcpServer({
    name: 'slack-tools',
    tools: [sendMessage, addReaction, uploadFile, readThread, readChannel],
  });
}
