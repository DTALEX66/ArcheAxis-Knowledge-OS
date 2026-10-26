/** Local form representation only. Persistence continues to use exact Unix seconds. */
export function localExpiryValue(seconds: number | null | undefined): string | null {
  if (seconds == null) return "";
  const date = new Date(seconds * 1000);
  if (!Number.isSafeInteger(seconds) || seconds < 0 || !Number.isFinite(date.getTime())
    || date.getFullYear() < 1 || date.getFullYear() > 9999) return null;
  const two = (value: number) => String(value).padStart(2, "0");
  return `${String(date.getFullYear()).padStart(4, "0")}-${two(date.getMonth() + 1)}-${two(date.getDate())}T${two(date.getHours())}:${two(date.getMinutes())}:${two(date.getSeconds())}`;
}

export function parseLocalExpiry(value: string, previous?: number | null): number | null {
  if (value === "") return null;
  if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.0{1,3})?)?$/.test(value)) throw new Error("请选择有效的本地日期与时间；原到期时间未改变。");
  const seconds = new Date(value).getTime() / 1000;
  const normalized = value.replace(/\.0{1,3}$/, "");
  const exact = normalized.length === 16 ? `${normalized}:00` : normalized;
  // A repeated wall time cannot identify which saved occurrence was intended.
  // Keep its exact existing instant when the displayed value is unchanged.
  if (previous != null && localExpiryValue(previous) === exact) return previous;
  // Reject normalized invalid dates and local times skipped by a DST transition.
  if (!Number.isSafeInteger(seconds) || seconds < 0 || localExpiryValue(seconds) !== exact) throw new Error("请选择有效的本地日期与时间；原到期时间未改变。");
  const offset = new Date(seconds * 1000).getTimezoneOffset();
  // Date chooses one occurrence of a fall-back time. Check the nearby timezone
  // offsets for another exact match, including transitions other than one hour.
  const offsets = new Set([-2, -1, 0, 1, 2].map(day => new Date((seconds + day * 86400) * 1000).getTimezoneOffset()));
  for (const other of offsets) {
    const alternative = seconds + (other - offset) * 60;
    if (alternative !== seconds && localExpiryValue(alternative) === exact) throw new Error("这个本地时间在时区切换时出现两次，请选择其他时间；原到期时间未改变。");
  }
  return seconds;
}

export function expiryDescription(seconds: number | null | undefined): string {
  if (seconds == null) return "不限时";
  if (localExpiryValue(seconds) === null) return "已保存的到期时间超出日期选择器范围，原值保留";
  const date = new Date(seconds * 1000);
  const offset = new Intl.DateTimeFormat(undefined, { timeZoneName: "shortOffset" }).formatToParts(date).find(part => part.type === "timeZoneName")?.value;
  return offset ? `${date.toLocaleString()}（${offset}）` : date.toLocaleString();
}
