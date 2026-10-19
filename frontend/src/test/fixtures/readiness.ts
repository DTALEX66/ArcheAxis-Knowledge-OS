export function scopedReadiness(body: {scope: string; operations: readonly string[]}, now = Date.now(), ttl = 30_000) {
  return { schema: "archeaxis.operation-readiness/v1", scope: body.scope, observed_at_ms: now,
    expires_at_ms: now + ttl, aggregate: "UNVERIFIED", network_performed: false, models_loaded: false, execution_authorized: false,
    operations: body.operations.map(operation => ({ operation, implementation: "IMPLEMENTED", dependencies: "AVAILABLE",
      connection: "UNKNOWN", qualification: "UNVERIFIED", permission: "ENABLED", status: "UNVERIFIED",
      reasons: ["RUNTIME_QUALIFICATION_UNVERIFIED"], expires_at_ms: now + ttl })) };
}
