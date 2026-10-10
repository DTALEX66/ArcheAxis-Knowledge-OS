export type WorkspaceReviewItem = { item_key: string; next_review: string | null };
/** Core's legacy SQLite datetime is UTC; never interpret it as browser local time. */
export function reviewDeadline(value: string | null): number | null {
  if (value === null) return null;
  let normalized = value;
  if (/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/.test(value)) normalized = value.replace(" ", "T") + "Z";
  const parts=/^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.(\d{1,9}))?(Z|[+-]\d{2}:\d{2})$/.exec(normalized);
  if (!parts) return null;
  // Validate the calendar before applying the offset; Date.parse alone normalizes February 30.
  const calendar=Date.parse(parts[1]+"Z");
  if (!Number.isFinite(calendar) || new Date(calendar).toISOString().slice(0,19)!==parts[1]) return null;
  if(parts[3]!=="Z" && (Number(parts[3].slice(1,3))>23 || Number(parts[3].slice(4))>59)) return null;
  // Python FSRS uses microseconds and +00:00; browser deadlines have millisecond precision.
  const fraction=parts[2]?"."+parts[2].slice(0,3).padEnd(3,"0"):"";
  const timestamp = Date.parse(parts[1]+fraction+parts[3]);
  return Number.isFinite(timestamp) ? timestamp : null;
}
export function workspaceReviews(items: WorkspaceReviewItem[], now: number) {
  const due = items.filter(item => { const deadline = reviewDeadline(item.next_review); return deadline !== null && deadline <= now; });
  due.sort((a, b) => reviewDeadline(a.next_review)! - reviewDeadline(b.next_review)! || a.item_key.localeCompare(b.item_key));
  return { due, unscheduled: items.filter(item => item.next_review === null).length,
    unverified: items.filter(item => item.next_review !== null && reviewDeadline(item.next_review) === null).length };
}
