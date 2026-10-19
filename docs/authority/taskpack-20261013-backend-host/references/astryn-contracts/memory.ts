import type { AstrynProtocolVersion } from './protocol';

/**
 * 记忆边界契约。星栖不拥有长期记忆主库：这里只定义"可治理的候选数据"
 * 如何通过授权宿主接口流动，以及星栖侧必须拒绝的越权组合。
 */

export const ASTRYN_MEMORY_SCOPES = [
  'user_preference',
  'companion_private',
  'character_fiction',
  'verified_fact'
] as const;
export type AstrynMemoryScope = (typeof ASTRYN_MEMORY_SCOPES)[number];

export const ASTRYN_MEMORY_ORIGINS = ['user-stated', 'model-generated', 'system-observed'] as const;
export type AstrynMemoryOrigin = (typeof ASTRYN_MEMORY_ORIGINS)[number];

export const ASTRYN_MEMORY_LIFECYCLE = ['candidate', 'confirmed', 'revoked', 'deleted'] as const;
export type AstrynMemoryLifecycle = (typeof ASTRYN_MEMORY_LIFECYCLE)[number];

/** 请求记忆的消费方模块。跨模块读取由作用域规则约束。 */
export const ASTRYN_MEMORY_CONSUMERS = ['companion', 'task', 'knowledge', 'ui'] as const;
export type AstrynMemoryConsumer = (typeof ASTRYN_MEMORY_CONSUMERS)[number];

export interface AstrynMemoryScopeGrant {
  readonly scope: AstrynMemoryScope;
  readonly read: boolean;
  readonly write: boolean;
  readonly grantedBy: 'user' | 'host-policy';
  readonly grantedAt: string;
  readonly expiresAt: string | null;
}

export interface AstrynMemoryCandidate {
  readonly schemaVersion: 1;
  readonly id: string;
  readonly scope: AstrynMemoryScope;
  readonly origin: AstrynMemoryOrigin;
  readonly lifecycle: AstrynMemoryLifecycle;
  readonly summary: string;
  readonly sessionId: string;
  readonly requestId: string | null;
  readonly createdAt: string;
  readonly confidence: number | null;
  /** 模型自述内容不得成为权威记录：确认必须由宿主回执触发。 */
  readonly confirmedByReceiptId: string | null;
  readonly consentRecordId: string | null;
}

export interface AstrynMemoryQuery {
  readonly consumer: AstrynMemoryConsumer;
  readonly scopes: readonly AstrynMemoryScope[];
  readonly includeLifecycle?: readonly AstrynMemoryLifecycle[];
}

export type AstrynMemoryDenialReason =
  | 'SCOPE_NOT_GRANTED'
  | 'PRIVATE_CONTENT_NOT_SHAREABLE'
  | 'FICTION_NOT_PROMOTABLE_TO_FACT'
  | 'CONSUMER_FORBIDDEN_FOR_SCOPE'
  | 'HOST_CONTRACT_MISSING';

export type AstrynMemoryReadResult =
  | { readonly ok: true; readonly records: readonly AstrynMemoryCandidate[]; readonly evidenceLevel: 'REAL' | 'SYNTHETIC' }
  | { readonly ok: false; readonly reason: AstrynMemoryDenialReason; readonly consumer: AstrynMemoryConsumer; readonly scope: AstrynMemoryScope };

export type AstrynMemoryWriteResult =
  | { readonly ok: true; readonly candidate: AstrynMemoryCandidate }
  | { readonly ok: false; readonly reason: AstrynMemoryDenialReason | 'ORIGIN_NOT_PROPOSABLE' };

export interface AstrynCandidateInput {
  readonly scope: AstrynMemoryScope;
  readonly origin: AstrynMemoryOrigin;
  readonly summary: string;
  readonly sessionId: string;
  readonly requestId?: string | null;
  readonly confidence?: number | null;
}

export interface AstrynMemoryMutationReceipt {
  readonly receiptId: string;
  readonly candidateId: string;
  readonly to: 'confirmed' | 'revoked' | 'deleted';
  readonly issuedBy: string;
  readonly issuedAt: string;
}

/**
 * 消费方禁止读取的作用域。私密陪伴内容不外溢到业务模块，
 * 虚构剧情不得进入"事实"通道。星栖侧在查询前强制执行，宿主可用更严格策略覆盖。
 */
export const ASTRYN_MEMORY_CONSUMER_FORBIDDEN: Readonly<
  Record<AstrynMemoryConsumer, readonly AstrynMemoryScope[]>
> = {
  companion: [],
  task: ['companion_private', 'character_fiction'],
  knowledge: ['companion_private', 'character_fiction'],
  ui: []
};

export interface AstrynMemoryPort {
  readonly protocol: AstrynProtocolVersion;
  readonly hostId: string;
  readonly evidenceLevel: 'REAL' | 'SYNTHETIC';
  probe(): Promise<{ readonly available: boolean; readonly reason: string | null }>;
  grantsFor(consumer: AstrynMemoryConsumer): Promise<readonly AstrynMemoryScopeGrant[]>;
  propose(input: AstrynCandidateInput): Promise<AstrynMemoryWriteResult>;
  query(query: AstrynMemoryQuery): Promise<AstrynMemoryReadResult>;
  confirm(receipt: AstrynMemoryMutationReceipt): Promise<AstrynMemoryWriteResult>;
  revoke(receipt: AstrynMemoryMutationReceipt): Promise<AstrynMemoryWriteResult>;
  delete(receipt: AstrynMemoryMutationReceipt): Promise<{ readonly ok: boolean; readonly reason?: AstrynMemoryDenialReason }>;
  listForReview(sessionId: string): Promise<readonly AstrynMemoryCandidate[]>;
}
