/** Neutral imported learning content. References are external candidates, never accepted knowledge. */
export type ImportedQuestion = {
  id: string; type: "single" | "multiple" | "short_answer"; question: string;
  options?: { label: string; value: string }[]; answer?: string[]; analysis?: string;
  commentPrompt?: string; hasAnswer?: boolean; points?: number;
};
export type CourseImportDraft = {
  title: string; scenes: { title: string; order: number; questions: ImportedQuestion[] }[];
  report: string[];
};
export type ImportedCourse = CourseImportDraft & {
  schema: "archeaxis.imported-course/v1"; status: "candidate"; grounding: "external_unverified";
  human_review_required: true;
  provenance: { adapter: "openmaic-manifest/v1"; upstream_commit: string; file_name: string;
    source_id: string; sha256: string; byte_length: number };
};
export function referenceFeedback(question: ImportedQuestion, selected: string[]):
  "invalid_response" | "no_reference" | "review_required" | "matches_reference" | "differs_from_reference" {
  if (question.hasAnswer === false || !question.answer?.length) return "no_reference";
  if (question.type === "short_answer") return "review_required";
  if (!selected.length || new Set(selected).size !== selected.length || (question.type === "single" && selected.length !== 1)
    || selected.some(v => !question.options?.some(o => o.value === v))) return "invalid_response";
  return selected.length === question.answer.length && selected.every(v => question.answer!.includes(v))
    ? "matches_reference" : "differs_from_reference";
}
