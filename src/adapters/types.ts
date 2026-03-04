export type Platform = 'slack' | 'discord' | 'telegram' | 'whatsapp';

export interface Attachment {
  type: 'image' | 'video' | 'file';
  url: string;
  filename?: string;
  mimeType?: string;
}

export interface IncomingMessage {
  platform: Platform;
  channelId: string;
  channelName?: string;
  threadId: string;
  userId: string;
  userName: string;
  text: string;
  attachments: Attachment[];
  isDM: boolean;
  isMention: boolean;
  raw: unknown;
}

export interface OutgoingMessage {
  text: string;
  attachments?: Attachment[];
  threadId?: string;
}

export interface PlatformAdapter {
  platform: Platform;
  start(): Promise<void>;
  stop(): Promise<void>;
  sendMessage(channelId: string, message: OutgoingMessage): Promise<void>;
  addReaction(channelId: string, messageTs: string, emoji: string): Promise<void>;
  uploadFile(channelId: string, file: Buffer | string, filename: string, threadId?: string): Promise<void>;
}

export type StreamCallback = (partialText: string) => void;
export type ToolProgressCallback = (toolName: string, elapsedSec: number) => void;

export type MessageHandler = (msg: IncomingMessage, onStream?: StreamCallback, onToolProgress?: ToolProgressCallback) => Promise<string | null>;
