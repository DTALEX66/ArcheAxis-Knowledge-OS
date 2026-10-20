import type { AstrynActionPort } from './action';
import type { AstrynConversationPort } from './conversation';
import type { AstrynContextPort } from './context';
import type { AstrynMemoryPort } from './memory';
import type { AstrynAnyEvent } from './events';
import type { AstrynProtocolVersion } from './protocol';

/** 宿主能力声明。不支持的能力必须显式缺失，不得用假实现填补。 */
export interface AstrynHostCapabilities {
  readonly protocol: AstrynProtocolVersion;
  readonly conversation: boolean;
  readonly memory: boolean;
  readonly context: boolean;
  readonly actions: boolean;
  readonly authoritativeReceipts: boolean;
  readonly streamResume: boolean;
  readonly hostBuildIdentity: string | null;
}

export interface AstrynHostUnavailable {
  readonly available: false;
  readonly code: 'HOST_CONTRACT_MISSING' | 'AUTHORITY_REFERENCE_MISSING' | 'PROTOCOL_MISMATCH';
  readonly detail: string;
}

/** 断线恢复游标：宿主不支持 streamResume 时适配器必须返回能力缺失。 */
export interface AstrynResumeCursor {
  readonly sessionId: string;
  readonly lastAppliedSeq: number;
  readonly supported: boolean;
}

export type AstrynHostEvent = AstrynAnyEvent;

export interface AstrynGrantRequest {
  readonly sessionId: string;
  readonly scopes: readonly string[];
  readonly purpose: string;
}

/**
 * 星栖接触 AAOS 的唯一入口。所有子端口都必须经过授权，
 * 角色身份不提升权限。
 */
export interface AstrynHostPort {
  readonly hostId: string;
  readonly protocol: AstrynProtocolVersion;
  probeCapabilities(): Promise<AstrynHostCapabilities | AstrynHostUnavailable>;
  conversation(): AstrynConversationPort | null;
  memory(): AstrynMemoryPort | null;
  context(): AstrynContextPort | null;
  actions(): AstrynActionPort | null;
  requestGrant(request: AstrynGrantRequest): Promise<{ readonly granted: readonly string[]; readonly denied: readonly string[] }>;
  onAuthoritativeEvent(handler: (event: AstrynHostEvent) => void): () => void;
}
