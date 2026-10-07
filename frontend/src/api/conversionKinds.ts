// Which Core route an extension converts through. Kept in one place on purpose: the per-source
// conversion panel and the folder entry must not disagree about what a format can become.
// A value here is a Core job kind; `directory_batch.py`'s table is checked against the Core's own
// media-type list, and the conversion panel's tests pin the behaviour of this one.
export const EXTENSION_TO_KIND: Record<string, string> = {
  xlsx: "office", pptx: "office", docx: "office",
  html: "html", htm: "html", xhtml: "html",
  pdf: "pdf",
  png: "image", jpg: "image", jpeg: "image", tif: "image", tiff: "image", webp: "image", bmp: "image",
  zip: "archive", tar: "archive",
  canvas: "canvas",
  srt: "subtitles", vtt: "subtitles",
  wav: "transcribe", mp3: "transcribe", m4a: "transcribe", flac: "transcribe", ogg: "transcribe", opus: "transcribe",
  mp4: "video", mov: "video", mkv: "video", webm: "video",
  txt: "text", md: "text", csv: "text", tsv: "text", json: "text", jsonl: "text",
  yaml: "text", yml: "text", toml: "text", xml: "text", epub: "text", eml: "text",
};

export function conversionKindFor(name: string): string | null {
  const extension = name.split(".").pop()?.toLowerCase();
  return extension ? EXTENSION_TO_KIND[extension] ?? null : null;
}
