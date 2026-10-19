import type { AstrynProtocolVersion } from './protocol';

/**
 * 授权上下文契约：小栖只能拿到"获准之后"的选中内容与真实来源标识。
 * M0 用合成文档夹具验证契约形状，来源必须显式标注，不得假装访问真实知识库。
 */

export const ASTRYN_CONTEXT_SCOPES = [
  'active-document-selection',
  'active-document-summary',
  'task-context',
  'knowledge-citation'
] as const;
export type AstrynContextScope = (typeof ASTRYN_CONTEXT_SCOPES)[number];

export type AstrynContextProvenance = 'aaos-knowledge' | 'aaos-workspace' | 'synthetic-fixture';

export interface AstrynContextAuthorization {
  readonly authorizationId: string;
  readonly scope: AstrynContextScope;
  readonly grantedBy: 'user' | 'host-policy';
  readonly grantedAt: string;
  readonly expiresAt: string | null;
}

export interface AstrynContextFragment {
  readonly scope: AstrynContextScope;
  readonly sourceId: string;
  readonly sourceTitle: string;
  readonly sourceVersion: string;
  readonly excerpt: string;
  readonly provenance: AstrynContextProvenance;
  readonly authorizationId: string;
  readonly evidenceLevel: 'REAL' | 'SYNTHETIC';
}

export type AstrynContextDenialReason =
  | 'NO_SELECTION'
  | 'PERMISSION_DENIED'
  | 'AUTHORIZATION_EXPIRED'
  | 'SCOPE_NOT_SUPPORTED'
  | 'HOST_CONTRACT_MISSING';

export type AstrynContextReadResult =
  | { readonly ok: true; readonly fragment: AstrynContextFragment }
  | { readonly ok: false; readonly reason: AstrynContextDenialReason };

export interface AstrynContextPort {
  readonly protocol: AstrynProtocolVersion;
  readonly hostId: string;
  readonly evidenceLevel: 'REAL' | 'SYNTHETIC';
  probe(): Promise<{ readonly available: boolean; readonly supportedScopes: readonly AstrynContextScope[]; readonly reason: string | null }>;
  requestAuthorization(scope: AstrynContextScope, sessionId: string): Promise<AstrynContextAuthorization | null>;
  readSelection(authorization: AstrynContextAuthorization, requestId: string): Promise<AstrynContextReadResult>;
}
