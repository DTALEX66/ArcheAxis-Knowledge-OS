/// <reference types="vite/client" />
import { useEffect, useRef, useState } from "react";
import { getDocument, GlobalWorkerOptions, type PDFDocumentProxy, type RenderTask } from "pdfjs-dist";
import workerUrl from "pdfjs-dist/build/pdf.worker.min.mjs?url";

// The worker is bundled by Vite; source documents never fetch a remote viewer.
GlobalWorkerOptions.workerSrc = workerUrl;

export function PdfReader({ bytes, page, onPageChange, focusRequest = 0 }: {
  bytes: Uint8Array;
  page: number;
  onPageChange: (page: number) => void;
  focusRequest?: number;
}) {
  const [document, setDocument] = useState<PDFDocumentProxy | null>(null);
  const [scale, setScale] = useState(1);
  const [error, setError] = useState(false);
  const canvas = useRef<HTMLCanvasElement>(null);
  const region = useRef<HTMLElement>(null);
  useEffect(() => {
    let alive = true;
    setDocument(null);
    setError(false);
    const task = getDocument({ data: bytes.slice() });
    task.promise.then((loaded) => { if (alive) setDocument(loaded); }).catch(() => { if (alive) setError(true); });
    return () => { alive = false; void task.destroy(); };
  }, [bytes]);
  useEffect(() => {
    if (!document) return;
    let alive = true;
    let rendering: RenderTask | undefined;
    const requested = Math.max(1, Math.min(document.numPages, page));
    document.getPage(requested).then((loaded) => {
      if (!alive || !canvas.current) return;
      const viewport = loaded.getViewport({ scale });
      canvas.current.width = viewport.width;
      canvas.current.height = viewport.height;
      const context = canvas.current.getContext("2d");
      if (!context) throw new Error("canvas unavailable");
      rendering = loaded.render({ canvasContext: context, canvas: canvas.current, viewport });
      return rendering.promise;
    }).then(() => { if (alive) region.current?.focus(); }).catch((cause: Error) => {
      if (alive && cause.name !== "RenderingCancelledException") setError(true);
    });
    return () => { alive = false; rendering?.cancel(); };
  }, [document, page, scale, focusRequest]);
  return <section className="pdf-reader" aria-label="PDF 原件阅读器" tabIndex={-1} ref={region}>
    <nav aria-label="PDF 阅读控制">
      <button type="button" disabled={!document || page <= 1} onClick={() => onPageChange(page - 1)}>上一页</button>
      <span>第 {page} 页 / {document?.numPages ?? "…"}</span>
      <button type="button" disabled={!document || page >= document.numPages} onClick={() => onPageChange(page + 1)}>下一页</button>
      <button type="button" aria-label="缩小" disabled={scale <= 0.5} onClick={() => setScale((value) => Math.max(0.5, value - 0.25))}>−</button>
      <span aria-label="缩放比例">{Math.round(scale * 100)}%</span>
      <button type="button" aria-label="放大" disabled={scale >= 2} onClick={() => setScale((value) => Math.min(2, value + 0.25))}>+</button>
    </nav>
    {error ? <p role="alert">无法读取此 PDF，请保留原件并检查转换回执。</p> : <canvas ref={canvas} aria-label={`PDF 第 ${page} 页`} />}
  </section>;
}
