import type { AstrynAnyEvent, AstrynFailureCode } from './events';
import type { AstrynContextFragment } from './context';
import type { AstrynProtocolVersion } from './protocol';

export type AstrynChatRole = 'system' | 'user' | 'assistant';

export interface AstrynChatMessage {
  readonly role: AstrynChatRole;
  readonly content: string;
  readonly sessionId: string;
  readonly requestId: string | null;
}

export interface AstrynConversationRequest {
  readonly protocol: AstrynProtocolVersion;
  readonly sessionId: string;
  readonly requestId: string;
  readonly characterId: string;
  readonly messages: readonly AstrynChatMessage[];
  readonly contextFragments: readonly AstrynContextFragment[];
}

export type AstrynTransportKind = 'aaos-host' | 'openai-compatible' | 'scripted-synthetic';

export interface AstrynConversationAvailability {
  readonly available: boolean;
  readonly reason: string | null;
  readonly failureCode: AstrynFailureCode | null;
}

/**
 * 会话与流式对话端口。
 * 端口自己签发事件的 source/trust：传输层不得把自身事件标成 authoritative，
 * 否则模型正文就能改写任务状态。
 */
export interface AstrynConversationPort {
  readonly protocol: AstrynProtocolVersion;
  readonly providerId: string;
  readonly transport: AstrynTransportKind;
  readonly evidenceLevel: 'REAL' | 'SYNTHETIC';
  readonly modelId: string | null;
  availability(): Promise<AstrynConversationAvailability>;
  stream(request: AstrynConversationRequest, signal: AbortSignal): AsyncIterable<AstrynAnyEvent>;
}
