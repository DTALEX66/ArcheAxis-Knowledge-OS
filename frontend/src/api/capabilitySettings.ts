export type CapabilityHandshake = { capability: string; enabled?: boolean; health?: string; [key: string]: unknown };
export const CAPABILITY_ENABLED_BASIS = "the workspace's capability record; an absent record means enabled";
/** Reject malformed/duplicate rows instead of accepting a partial permission list. */
export function readResourceHandshake(value: unknown): CapabilityHandshake[] {
  if (!value || typeof value !== "object" || !Array.isArray((value as { capabilities?: unknown }).capabilities)) throw new Error("invalid capability list");
  const ids = new Set<string>();
  return (value as { capabilities: unknown[] }).capabilities.map(row => {
    if (!row || typeof row !== "object" || Array.isArray(row)) throw new Error("invalid capability row");
    const item = row as Record<string, unknown>;
    if (typeof item.capability !== "string" || !item.capability || ids.has(item.capability)) throw new Error("invalid/duplicate capability identity");
    if (item.enabled !== undefined && typeof item.enabled !== "boolean") throw new Error("invalid capability permission");
    if (item.health !== undefined && typeof item.health !== "string") throw new Error("invalid capability health");
    ids.add(item.capability);
    return item as CapabilityHandshake;
  });
}
export function readCapabilityDecision(value: unknown, capability: string, enabled: boolean): CapabilityHandshake {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("invalid capability decision");
  const [decision] = readResourceHandshake({ capabilities: [(value as { capability?: unknown }).capability] });
  if (decision.capability !== capability || decision.enabled !== enabled || decision.enabled_basis !== CAPABILITY_ENABLED_BASIS) throw new Error("unconfirmed capability decision");
  return decision;
}
export function readCapabilityPermission(value: unknown, capability: string): boolean {
  const row = readResourceHandshake(value).find(item => item.capability === capability);
  if (!row || typeof row.enabled !== "boolean" || row.enabled_basis !== CAPABILITY_ENABLED_BASIS) throw new Error("capability permission readback unavailable");
  return row.enabled;
}
