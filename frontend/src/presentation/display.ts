/** Display only. Never use a shortened identity or formatted time in a request. */
export function compactIdentity(value: string | null | undefined): string {
  if (!value?.trim()) return "编号未记录";
  return value.length > 20 ? `${value.slice(0, 8)}…${value.slice(-6)}` : value;
}

export function displayTitle(value: string | null | undefined, fallback = "未命名文档"): string {
  return value?.trim() || fallback;
}

/** ISO instants use the device's locale/timezone; date-only values stay calendar dates. */
export function localDateTime(value: string | null | undefined): string {
  if (!value?.trim()) return "时间未记录";
  if (/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    const date = new Date(`${value}T12:00:00Z`);
    if (!Number.isFinite(date.getTime()) || date.toISOString().slice(0, 10) !== value) return "时间待核对";
    return new Intl.DateTimeFormat("zh-CN", { dateStyle: "medium", timeZone: "UTC" }).format(date);
  }
  // Do not invent a timezone for an ambiguous saved wall-clock value.
  if (!/^\d{4}-\d{2}-\d{2}T.+(?:Z|[+-]\d{2}:\d{2})$/i.test(value)) return "时间待核对";
  const calendar = value.slice(0, 10);
  const calendarDate = new Date(`${calendar}T12:00:00Z`);
  if (!Number.isFinite(calendarDate.getTime()) || calendarDate.toISOString().slice(0, 10) !== calendar) return "时间待核对";
  const date = new Date(value);
  if (!Number.isFinite(date.getTime())) return "时间待核对";
  const formatted = new Intl.DateTimeFormat("zh-CN", { dateStyle: "medium", timeStyle: "short" }).format(date);
  const offset = new Intl.DateTimeFormat(undefined, { timeZoneName: "shortOffset" }).formatToParts(date).find(part => part.type === "timeZoneName")?.value;
  return offset ? `${formatted}（${offset}）` : formatted;
}
