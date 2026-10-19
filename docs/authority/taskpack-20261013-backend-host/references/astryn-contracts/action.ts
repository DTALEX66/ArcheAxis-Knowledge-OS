import type { AstrynProtocolVersion } from './protocol';
import type { AstrynFailureCode } from './events';

/**
 * 动作、审批与执行回执契约。
 * 任务状态权威只来自 verifyReceipt 通过的 AstrynActionReceipt；
 * 模型正文里的"我做完了"在本契约中没有任何对应类型。
 */

export type AstrynRiskTier = 'low' | 'medium' | 'high';

export interface AstrynActionRequest {
  readonly protocol: AstrynProtocolVersion;
  readonly requestId: string;
  readonly sessionId: string;
  readonly actionKind: string;
  readonly summary: string;
  readonly riskTier: AstrynRiskTier;
  readonly argumentsDigest: string;
}

export const ASTRYN_RECEIPT_OUTCOMES = ['approval-requested', 'approval-granted', 'approval-denied', 'started', 'completed', 'failed'] as const;
export type AstrynReceiptOutcome = (typeof ASTRYN_RECEIPT_OUTCOMES)[number];

/** 宿主签发、星栖只能校验不能伪造的回执。 */
export interface AstrynActionReceipt {
  readonly receiptId: string;
  readonly taskId: string;
  readonly actionRequestId: string;
  readonly outcome: AstrynReceiptOutcome;
  readonly issuedBy: string;
  readonly issuedAt: string;
  readonly summary: string | null;
  readonly failureCode: AstrynFailureCode | null;
  readonly riskTier: AstrynRiskTier | null;
  readonly authority: 'aaos-core' | 'synthetic-fixture';
  readonly signature: string;
}

export interface AstrynVerificationResult {
  readonly ok: boolean;
  readonly reason: 'SIGNED_BY_TRUSTED_HOST' | 'UNKNOWN_ISSUER' | 'BAD_SIGNATURE' | 'REPLAYED' | 'NO_VERIFIER' | string;
  readonly issuer: string;
}

/** 校验器由宿主适配器持有。没有校验器时，任何回执都不产生权威状态。 */
export interface AstrynReceiptVerifier {
  verify(receipt: AstrynActionReceipt): Promise<AstrynVerificationResult>;
}

export type AstrynActionSubmitResult =
  | { readonly ok: true; readonly taskId: string }
  | { readonly ok: false; readonly reason: 'HOST_CONTRACT_MISSING' | 'PERMISSION_DENIED' | AstrynFailureCode };

export interface AstrynActionPort {
  readonly protocol: AstrynProtocolVersion;
  readonly hostId: string;
  readonly evidenceLevel: 'REAL' | 'SYNTHETIC';
  probe(): Promise<{ readonly available: boolean; readonly reason: string | null }>;
  submit(request: AstrynActionRequest, signal?: AbortSignal): Promise<AstrynActionSubmitResult>;
  cancel(taskId: string): Promise<{ readonly ok: boolean; readonly reason?: string }>;
  subscribe(handler: (receipt: AstrynActionReceipt) => void): () => void;
}
