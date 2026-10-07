import type { ReactNode } from "react";

export type AaosStatusTone = "success" | "warning" | "danger" | "info";

function StatusIcon({ tone }: { tone: AaosStatusTone }) {
  const paths: Record<AaosStatusTone, ReactNode> = {
    success: <><circle cx="12" cy="12" r="9" /><path d="m8 12 2.5 2.5L16.5 9" /></>,
    warning: <><path d="M12 3 22 21H2L12 3Z" /><path d="M12 9v5" /><path d="M12 17.5v.1" /></>,
    danger: <><circle cx="12" cy="12" r="9" /><path d="m9 9 6 6m0-6-6 6" /></>,
    info: <><circle cx="12" cy="12" r="9" /><path d="M12 11v5" /><path d="M12 8v.1" /></>,
  };
  return <svg className="aaos-status-badge-icon" data-icon={tone} viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[tone]}</svg>;
}

/** Status always carries readable text; color and icon are redundant cues. */
export function AaosStatusBadge({ tone, children }: { tone: AaosStatusTone; children: ReactNode }) {
  return <span className={`badge badge-${tone} aaos-status-badge`} data-status-tone={tone}>
    <StatusIcon tone={tone} />
    <span>{children}</span>
  </span>;
}
