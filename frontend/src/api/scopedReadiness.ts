import { assertCoreDto, type ReadinessSnapshot } from "./generated/core-contract";

/** Schema + scope + time identity: a permission is never a model/quality verdict. */
export function readScopedReadiness(value: unknown, scope: string, operations: readonly string[], now = Date.now()) {
  const snapshot = assertCoreDto<ReadinessSnapshot>("ReadinessSnapshot", value);
  if (snapshot.scope !== scope || !Number.isSafeInteger(snapshot.observed_at_ms)
    || !Number.isSafeInteger(snapshot.expires_at_ms) || snapshot.observed_at_ms > now
    || snapshot.expires_at_ms <= snapshot.observed_at_ms || snapshot.expires_at_ms <= now)
    throw new Error("invalid readiness identity or time");
  const names = snapshot.operations.map(row => row.operation);
  if (names.length !== operations.length || new Set(names).size !== names.length
    || names.some(name => !operations.includes(name)) || snapshot.operations.some(row =>
      !Number.isSafeInteger(row.expires_at_ms) || row.expires_at_ms <= now || row.expires_at_ms > snapshot.expires_at_ms))
    throw new Error("invalid readiness rows or scope");
  const expiresAt = Math.min(snapshot.expires_at_ms, snapshot.observed_at_ms + 30_000,
    ...snapshot.operations.map(row => row.expires_at_ms));
  if (expiresAt <= now) throw new Error("readiness observation expired");
  return { snapshot, expiresAt };
}
