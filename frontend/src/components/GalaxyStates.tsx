/** Adapted from Uiverse/Galaxy AHMED-MIT spinner and 1osm skeleton.
 * MIT source commit and notices are recorded in THIRD_PARTY_NOTICES.md.
 * Cosmetic state only; actual loading/error data comes from the feature.
 */
import "./galaxy-states.css";

export function AaosSpinner({ label = "加载中" }: { label?: string }) {
  return <span role="status" className="aaos-loading"><span className="aaos-spinner" aria-hidden="true" /><span>{label}</span></span>;
}

export function AaosSkeleton({ label = "正在读取资料" }: { label?: string }) {
  return <div role="status"><span className="aaos-sr-only">{label}</span><div className="aaos-skeleton" aria-hidden="true"><span /><div><i /><i /></div></div></div>;
}
