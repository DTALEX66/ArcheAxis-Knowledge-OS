/** Display-only labels. Identity, persistence and navigation always use item_key.
 * Match Core's first nonempty line, Unicode whitespace and 80-scalar limit.
 * Missing titles from an older Core remain a normal, non-identifying fallback.
 */
export function learningTitle(...candidates: unknown[]): string {
  for (const candidate of candidates) {
    if (typeof candidate !== "string") continue;
    for (const line of candidate.split(/\r?\n/u)) {
      const clean = line.replace(/\p{Cc}/gu, character => /\p{White_Space}/u.test(character) ? character : "");
      const normalized = clean.split(/\p{White_Space}+/u).filter(Boolean).join(" ");
      if (normalized) return Array.from(normalized).slice(0, 80).join("");
    }
  }
  return "学习项目";
}
