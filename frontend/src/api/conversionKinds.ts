// Which Core route an extension converts through. Kept in one place on purpose: the per-source
// conversion panel and the folder entry must not disagree about what a format can become.
// A value here is a Core job kind; `directory_batch.py`'s table is checked against the Core's own
// media-type list, and the conversion panel's tests pin the behaviour of this one.
export const EXTENSION_TO_KIND: Record<string, string> = {
  xlsx: "office", pptx: "office", docx: "office",
  xls: "office", ppt: "office", doc: "office",
  html: "html", htm: "html", xhtml: "html",
  pdf: "pdf",
  png: "image", jpg: "image", jpeg: "image", tif: "image", tiff: "image", webp: "image", bmp: "image",
  zip: "archive", tar: "archive",
  canvas: "canvas",
  srt: "subtitles", vtt: "subtitles",
  wav: "transcribe", mp3: "transcribe", m4a: "transcribe", flac: "transcribe", ogg: "transcribe", opus: "transcribe",
  mp4: "video", mov: "video", mkv: "video", webm: "video",
  txt: "text", md: "text", markdown: "text", csv: "text", tsv: "text", json: "text", jsonl: "text",
  yaml: "text", yml: "text", toml: "text", xml: "text", log: "text", text: "text",
  ini: "text", cfg: "text", sql: "text",
  rs: "text", py: "text", ts: "text", tsx: "text", js: "text", jsx: "text",
  c: "text", h: "text", cpp: "text", hpp: "text", go: "text", java: "text", cs: "text",
  rb: "text", sh: "text", ps1: "text", bat: "text",
  epub: "text", eml: "text",
  // F13: ODF/RTF reach the same text.extract reader (kind "text", proven by the Rust
  // format_location_anchor_api path). Legacy binary MS Office uses the same existing office route;
  // mapping declares a request kind, never engine/runtime/license qualification.
  odt: "text", ods: "text", odp: "text", rtf: "text",
};

export function conversionKindFor(name: string): string | null {
  const extension = name.split(".").pop()?.toLowerCase();
  return extension ? EXTENSION_TO_KIND[extension] ?? null : null;
}


/** Existing route requirement only. Office handshake does not prove a particular binary reader. */
export function legacyOfficeRequirementFor(name: string): { capability: "office.structure"; engine_requirement: string; qualification: "DECLARATION_ONLY"; requires_actual_result: true } | null {
  const ext = name.split(".").pop()?.toLowerCase();
  const engine = ext === "doc" ? "declared antiword binary + license/permission readback"
    : ext === "xls" ? "xlrd engine + BIFF/formula/style loss receipt"
      : ext === "ppt" ? "declared Tika/JVM + version and slide loss receipt" : null;
  return engine ? { capability: "office.structure", engine_requirement: engine, qualification: "DECLARATION_ONLY", requires_actual_result: true } : null;
}
