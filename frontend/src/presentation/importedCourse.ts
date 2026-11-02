/** Neutral imported learning content. References are external candidates, never accepted knowledge. */
export type ImportedQuestion = {
  id: string; type: "single" | "multiple" | "short_answer"; question: string;
  options?: { label: string; value: string }[]; answer?: string[]; analysis?: string;
  commentPrompt?: string; hasAnswer?: boolean; points?: number;
};
/** A constrained view of an OpenMAIC 1.3.0 text canvas. The full canvas is retained. */
export type ImportedTextElement = Record<string, unknown> & {
  type: "text"; id: string; left: number; top: number; width: number; height: number;
  rotate: number; content: string; defaultFontName: string; defaultColor: string;
};
export type ImportedTextSlide = Record<string, unknown> & {
  id: string; viewportSize: number; viewportRatio: number;
  theme: Record<string, unknown>; elements: ImportedTextElement[];
};
export type CourseImportDraft = {
  title: string; scenes: { title: string; order: number; questions: ImportedQuestion[];
    kind?: "slide" | "quiz"; slide?: ImportedTextSlide }[];
  report: string[];
};
export type ImportedCourse = CourseImportDraft & {
  schema: "archeaxis.imported-course/v1"; status: "candidate"; grounding: "external_unverified";
  human_review_required: true;
  provenance: { adapter: "openmaic-manifest/v1"; upstream_commit: string; file_name: string;
    source_id: string; sha256: string; byte_length: number };
};
export type ImportedCourseV2 = CourseImportDraft & {
  schema: "archeaxis.imported-course/v2"; status: "candidate"; grounding: "external_unverified";
  human_review_required: true;
  provenance: { adapter: "openmaic-1.3.0-manifest/v2"; adapter_upstream_version: "1.3.0";
    file_name: string; source_id: string; sha256: string; byte_length: number };
};
export type AnyImportedCourse = ImportedCourse | ImportedCourseV2;

/** Render as text only; no HTML parser, event handlers, URLs, or external fetches are involved. */
export function slideText(content: string): string {
  const entities: Record<string, string> = { amp: "&", lt: "<", gt: ">", quot: '"', apos: "'", nbsp: " " };
  return content.replace(/<br\s*\/?>/gi, "\n").replace(/<\/(?:p|div|li|h[1-6])\s*>/gi, "\n")
    .replace(/<[^>]*>/g, "").replace(/&(#x[0-9a-f]+|#\d+|amp|lt|gt|quot|apos|nbsp);/gi, (entity, name: string) => {
      if (name[0] !== "#") return entities[name.toLowerCase()] ?? entity;
      const code = name[1].toLowerCase() === "x" ? Number.parseInt(name.slice(2), 16) : Number.parseInt(name.slice(1), 10);
      return Number.isInteger(code) && code > 0 && code <= 0x10ffff && !(code >= 0xd800 && code <= 0xdfff)
        ? String.fromCodePoint(code) : entity;
    }).replace(/\n{3,}/g, "\n\n").trim();
}
export function referenceFeedback(question: ImportedQuestion, selected: string[]):
  "invalid_response" | "no_reference" | "review_required" | "matches_reference" | "differs_from_reference" {
  if (question.hasAnswer === false || !question.answer?.length) return "no_reference";
  if (question.type === "short_answer") return "review_required";
  if (!selected.length || new Set(selected).size !== selected.length || (question.type === "single" && selected.length !== 1)
    || selected.some(v => !question.options?.some(o => o.value === v))) return "invalid_response";
  return selected.length === question.answer.length && selected.every(v => question.answer!.includes(v))
    ? "matches_reference" : "differs_from_reference";
}
