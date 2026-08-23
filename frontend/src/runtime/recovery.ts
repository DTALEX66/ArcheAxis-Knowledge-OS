export type RecoveryState =
  | "booting"
  | "checking"
  | "ready"
  | "reconnecting"
  | "incompatible"
  | "failed"
  | "stopped";

export interface RecoveryStatusDto {
  state: RecoveryState;
  safe_mode: boolean;
  backend_available: boolean;
  message: string;
  backups: string[];
  external_dev: boolean;
}

export interface RecoveryLogTailDto {
  lines: string[];
}

export interface RestoreReceiptDto {
  status: "restored";
}

const RECOVERY_STATES = new Set<RecoveryState>([
  "booting",
  "checking",
  "ready",
  "reconnecting",
  "incompatible",
  "failed",
  "stopped",
]);
const BACKUP_NAME = /^cognitive_os_\d{8}T\d{6}_\d{6}Z\.sqlite$/;
const ANSI_SEQUENCE = /\u001b\[[0-?]*[ -/]*[@-~]/g;
const CONTROL_CHARACTER = /[\u0000-\u001f\u007f-\u009f]/;
const SENSITIVE_DIAGNOSTIC = [
  /\b(?:authorization|token|password|api[_-]?key|secret|credential)\s*[:=]/i,
  /\b(?:https?|file):\/\//i,
  /[\\/]/,
  /\b(?:127\.0\.0\.1|localhost|\[?::1\]?)\s*:\s*\d{1,5}\b/i,
  /[A-Za-z0-9_-][A-Za-z0-9._~+/-]{38,}[A-Za-z0-9_-](?:={1,2})?/,
];
const WITHHELD_DIAGNOSTIC = "Recovery diagnostic withheld";

function record(value: unknown): Record<string, unknown> {
  return value !== null && typeof value === "object" ? value as Record<string, unknown> : {};
}

export function sanitizeRecoveryDisplayText(value: unknown, fallback = ""): string {
  if (typeof value !== "string") return fallback;
  const normalized = value.replace(ANSI_SEQUENCE, "");
  if (CONTROL_CHARACTER.test(normalized)) return WITHHELD_DIAGNOSTIC;
  if (SENSITIVE_DIAGNOSTIC.some((pattern) => pattern.test(normalized))) {
    return WITHHELD_DIAGNOSTIC;
  }
  return normalized.slice(0, 240);
}

export function isOpaqueBackupName(value: string): boolean {
  return BACKUP_NAME.test(value) && !value.includes("/") && !value.includes("\\") && !value.includes(":");
}

export function normalizeRecoveryStatus(value: unknown): RecoveryStatusDto {
  const source = record(value);
  const rawState = typeof source.state === "string" ? source.state : "failed";
  const state = RECOVERY_STATES.has(rawState as RecoveryState)
    ? rawState as RecoveryState
    : "failed";
  const backups = Array.isArray(source.backups)
    ? source.backups
        .filter((name): name is string => typeof name === "string" && isOpaqueBackupName(name))
        .slice(0, 200)
    : [];
  return {
    state,
    safe_mode: source.safe_mode === true,
    backend_available: source.backend_available === true,
    message: sanitizeRecoveryDisplayText(source.message, "Recovery status unavailable"),
    backups,
    external_dev: source.external_dev === true,
  };
}

export function normalizeRecoveryLogTail(value: unknown): RecoveryLogTailDto {
  const source = record(value);
  const lines = Array.isArray(source.lines)
    ? source.lines
        .filter((line): line is string => typeof line === "string")
        .slice(-200)
        .map((line) => sanitizeRecoveryDisplayText(line))
    : [];
  return { lines };
}

export function checkingRecoveryStatus(): RecoveryStatusDto {
  return {
    state: "checking",
    safe_mode: false,
    backend_available: false,
    message: "Checking the local Core…",
    backups: [],
    external_dev: false,
  };
}

export function failedRecoveryStatus(message: string, previous?: RecoveryStatusDto): RecoveryStatusDto {
  return {
    state: "incompatible",
    safe_mode: false,
    backend_available: false,
    message,
    backups: previous?.backups ?? [],
    external_dev: previous?.external_dev ?? false,
  };
}

export function isRecoveryReady(status: RecoveryStatusDto): boolean {
  return status.state === "ready" && status.backend_available && !status.safe_mode;
}
