// AXW-UI-801: runtime connection state machine mirroring the Recovery Shell
// (desktop/bootstrap). states: booting/checking/ready/reconnecting/
// incompatible/failed/stopped (task pack §9.1).
export type BackendState =
  | "booting"
  | "checking"
  | "ready"
  | "reconnecting"
  | "incompatible"
  | "failed"
  | "stopped";

export interface BackendInfo {
  port: number;
  token: string;
}

export interface RuntimeSnapshot {
  state: BackendState;
  backendInfo: BackendInfo | null;
  lastError: string | null;
}
