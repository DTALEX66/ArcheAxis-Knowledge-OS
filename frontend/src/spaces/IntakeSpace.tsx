import { useCallback, useEffect, useRef, useState } from "react";
import { DataError, Section } from "../components/RealData";
import {
  getBatchStatus,
  intakeUpload,
  intakeUrl,
  pauseBatch,
  resumeBatch,
  shutdownBatch,
  startBatchImport,
  type BatchStatusDto,
  type IntakeResultDto,
} from "../api/workspace";
import { userErrorMessage } from "../presentation/labels";

const FORMAT_LABELS: Record<string, string> = {
  pdf: "PDF",
  docx: "Word",
  pptx: "PPT",
  xlsx: "Excel",
  html: "HTML 网页",
  md: "Markdown",
  txt: "文本",
  image: "图片",
  media_video: "视频",
  media_audio: "音频",
  canvas: "画布",
  rtf: "RTF",
  odt: "ODT",
  csv: "表格",
  unknown: "未知格式",
};

export function formatLabel(format: string | undefined | null): string {
  if (!format) return "未识别";
  return FORMAT_LABELS[format] ?? format;
}

function sourceTypeLabel(sourceType: string): string {
  if (sourceType === "file") return "文件";
  if (sourceType === "web") return "网页";
  if (sourceType === "github_repository") return "GitHub 仓库";
  return sourceType;
}

function IntakeReceipt({ result }: { result: IntakeResultDto }) {
  return (
    <dl className="receipt-grid" aria-label="导入回执">
      <div><dt>来源</dt><dd>{sourceTypeLabel(result.source_type)}{result.file_name ? ` · ${result.file_name}` : ""}</dd></div>
      <div><dt>格式</dt><dd>{formatLabel(result.format)}</dd></div>
      <div><dt>转换引擎</dt><dd>{result.engine ?? "未转换"}</dd></div>
      <div><dt>转换文本</dt><dd>{result.char_count != null ? `${result.char_count} 字符` : "—"}</dd></div>
      <div><dt>状态</dt><dd>{result.requires_human_review ? "需人工复核" : "已保留"}</dd></div>
      {result.content_preview ? <div className="receipt-preview"><dt>预览</dt><dd><pre>{result.content_preview}</pre></dd></div> : null}
    </dl>
  );
}

export function IntakeSpace() {
  const [url, setUrl] = useState("");
  const [urlResult, setUrlResult] = useState<IntakeResultDto | null>(null);
  const [uploadResult, setUploadResult] = useState<IntakeResultDto | null>(null);
  const [busy, setBusy] = useState<"url" | "upload" | "batch" | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [batchId, setBatchId] = useState<string | null>(null);
  const [batch, setBatch] = useState<BatchStatusDto | null>(null);
  const [dir, setDir] = useState("");
  const [pattern, setPattern] = useState("**/*");
  const [maxFiles, setMaxFiles] = useState("200");
  const fileInput = useRef<HTMLInputElement | null>(null);
  const pollTimer = useRef<number | null>(null);

  const stopPolling = useCallback(() => {
    if (pollTimer.current !== null) {
      window.clearInterval(pollTimer.current);
      pollTimer.current = null;
    }
  }, []);

  useEffect(() => () => stopPolling(), [stopPolling]);

  const refreshBatch = useCallback(async (id: string) => {
    try {
      const next = await getBatchStatus(id);
      setBatch(next);
      if (next.state === "finished" || next.state === "shutdown") {
        stopPolling();
        setBusy(null);
        setMessage(`批量导入${next.state === "shutdown" ? "已安全停止" : "已完成"}：成功 ${next.completed} · 失败 ${next.failed}`);
      }
    } catch (e) {
      stopPolling();
      setBusy(null);
      setError(userErrorMessage(e instanceof Error ? e.message : e));
    }
  }, [stopPolling]);

  async function submitUrl() {
    const target = url.trim();
    if (!target) {
      setMessage("请输入要导入的网页地址");
      return;
    }
    setBusy("url");
    setError(null);
    setMessage(null);
    try {
      const result = await intakeUrl(target);
      setUrlResult(result);
      setMessage(`网页导入完成：${result.char_count != null ? `${result.char_count} 字符` : "已记录"}`);
    } catch (e) {
      setMessage(null);
      setError(userErrorMessage(e instanceof Error ? e.message : e));
    } finally {
      setBusy(null);
    }
  }

  async function submitUpload(file: File) {
    setBusy("upload");
    setError(null);
    setMessage(null);
    try {
      const result = await intakeUpload(file);
      setUploadResult(result);
      setMessage(`文件已保留并转换，可在资料库查看。${result.requires_human_review ? "（需人工复核）" : ""}`);
    } catch (e) {
      setMessage(null);
      setError(userErrorMessage(e instanceof Error ? e.message : e));
    } finally {
      setBusy(null);
      if (fileInput.current) fileInput.current.value = "";
    }
  }

  async function submitBatch() {
    const sourceDir = dir.trim();
    if (!sourceDir) {
      setMessage("请输入要导入的本地目录路径");
      return;
    }
    setBusy("batch");
    setError(null);
    setMessage(null);
    stopPolling();
    try {
      const started = await startBatchImport({
        batch_id: `ui-${Date.now().toString(36)}`,
        source_dir: sourceDir,
        pattern: pattern.trim() || "**/*",
        max_files: Math.min(Math.max(Number(maxFiles) || 200, 1), 10_000),
      });
      setBatchId(started.batch_id);
      setBatch(started);
      setMessage(`批量导入已启动：共 ${started.total} 个文件，转换结果会进入资料库。`);
      pollTimer.current = window.setInterval(() => void refreshBatch(started.batch_id), 2000);
    } catch (e) {
      setBusy(null);
      setMessage(null);
      setError(userErrorMessage(e instanceof Error ? e.message : e));
    }
  }

  async function controlBatch(action: "pause" | "resume" | "shutdown") {
    if (!batchId) return;
    setError(null);
    try {
      if (action === "pause") await pauseBatch(batchId);
      else if (action === "resume") await resumeBatch(batchId);
      else await shutdownBatch(batchId);
      await refreshBatch(batchId);
    } catch (e) {
      setError(userErrorMessage(e instanceof Error ? e.message : e));
    }
  }

  const running = batch !== null && (batch.state === "running" || batch.state === "paused");
  const progress = batch && batch.total > 0
    ? Math.round(((batch.completed + batch.failed) / batch.total) * 100)
    : 0;
  const finished = batch !== null && (batch.state === "finished" || batch.state === "shutdown");
  const failedResults = batch?.results
    ? Object.entries(batch.results).filter(([, value]) => value.status === "failed")
    : [];

  return (
    <Section title="导入">
      <p className="muted">多格式摄取管线：原始文件先保留，再转换为可读文本并记录转换运行与证据锚点；失败的文件仍保留原件并说明原因。</p>

      <h4>网页导入</h4>
      <div className="intake-row">
        <label className="visually-hidden" htmlFor="intake-url">网页地址</label>
        <input id="intake-url" type="url" value={url} onChange={(event) => setUrl(event.target.value)} placeholder="https://example.com/article" aria-label="网页地址" />
        <button type="button" onClick={() => void submitUrl()} disabled={busy !== null}>{busy === "url" ? "正在导入…" : "导入网页"}</button>
      </div>
      {urlResult ? <IntakeReceipt result={urlResult} /> : null}

      <h4>文件上传</h4>
      <div className="intake-row">
        <input ref={fileInput} type="file" aria-label="选择要导入的文件" onChange={(event) => {
          const file = event.target.files?.[0];
          if (file) void submitUpload(file);
        }} disabled={busy !== null} />
      </div>
      {uploadResult ? <IntakeReceipt result={uploadResult} /> : null}

      <h4>批量目录导入</h4>
      <p className="muted">导入一个本地目录中的多格式文件；可暂停、恢复或安全停止，进度会持续记录。</p>
      <div className="intake-grid">
        <label>目录路径<input value={dir} onChange={(event) => setDir(event.target.value)} placeholder="D:/资料/课程资料" aria-label="目录路径" /></label>
        <label>文件匹配<input value={pattern} onChange={(event) => setPattern(event.target.value)} aria-label="文件匹配模式" /></label>
        <label>文件上限<input type="number" min={1} max={10000} value={maxFiles} onChange={(event) => setMaxFiles(event.target.value)} aria-label="文件数量上限" /></label>
      </div>
      <div className="intake-row">
        <button type="button" onClick={() => void submitBatch()} disabled={busy !== null && busy !== "batch"}>{busy === "batch" ? "正在启动…" : "开始批量导入"}</button>
        {running ? <>
          <button type="button" onClick={() => void controlBatch(batch.state === "paused" ? "resume" : "pause")}>{batch.state === "paused" ? "继续" : "暂停"}</button>
          <button type="button" onClick={() => void controlBatch("shutdown")}>安全停止</button>
        </> : null}
      </div>
      {batch ? <section className="batch-progress" aria-label="批量导入进度">
        <div className="batch-meta">
          <span>状态：{batch.state === "running" ? "运行中" : batch.state === "paused" ? "已暂停" : batch.state === "finished" ? "已完成" : batch.state === "shutdown" ? "已停止" : "等待中"}</span>
          <span>{batch.completed + batch.failed}/{batch.total} · 成功 {batch.completed} · 失败 {batch.failed}</span>
        </div>
        <div className="progress-track" role="progressbar" aria-valuenow={progress} aria-valuemin={0} aria-valuemax={100} aria-label="批量导入进度">
          <div className="progress-fill" style={{ width: `${progress}%` }} />
        </div>
        {failedResults.length > 0 ? <ul className="batch-failures">
          {failedResults.map(([task, value]) => <li key={task}>{task}：{value.error ?? "转换失败"}</li>)}
        </ul> : null}
        {finished && batch.completed > 0 ? <p className="muted">转换完成的文件已进入资料库，可查看转换文本与证据锚点。</p> : null}
      </section> : null}

      {error ? <DataError label="导入" message={error} /> : null}
      {message ? <p role="status" className="muted">{message}</p> : null}
    </Section>
  );
}
