# -*- coding: utf-8 -*-
"""ceshi 全库转化扫描 — 本地模型跑通全部文件并出验证回执。"""
import collections, json, os, sys, time
sys.stdout.reconfigure(encoding='utf-8')

ROOT = r"D:/All projects/ceshi"
OUT = r"D:/All projects/ArcheAxis-Knowledge-OS/.hermes/task-runtime/ceshi_sweep_receipt.json"
CAP_IMAGES = 20
CAP_AUDIO = 0
PER_FILE_BUDGET = 10

from app.ingestion.ocr_gate import assess as ocr_gate

def read_text(p):
    with open(p, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()

def convert_pdf(p):
    import pymupdf
    doc = pymupdf.open(p)
    parts = []
    for i in range(min(doc.page_count, 40)):
        parts.append(doc[i].get_text())
    text = "\n".join(parts)
    if len(text.strip()) < 100 and doc.page_count > 0:
        import pytesseract, io
        from PIL import Image
        ocr = []
        for i in range(min(doc.page_count, 6)):
            pix = doc[i].get_pixmap(dpi=150)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            ocr.append(pytesseract.image_to_string(img, lang="eng+chi_sim"))
        text = "\n".join(ocr) if "".join(ocr).strip() else text
        return text, "pymupdf+ocr"
    return text, "pymupdf"

def convert_docx(p):
    try:
        from app.ingestion.docx_adapter import convert_docx
        r = convert_docx(p)
        return (r.content if getattr(r, "success", False) else ""), "docx_adapter"
    except Exception:
        import markitdown
        md = markitdown.MarkItDown()
        return (md.convert(str(p)).text_content or ""), "markitdown"

def convert_pptx(p):
    from app.ingestion.pptx_adapter import convert_pptx
    r = convert_pptx(p)
    return (r.content if getattr(r, "success", False) else ""), "pptx_adapter"

def convert_image(p):
    import pytesseract
    from PIL import Image
    return pytesseract.image_to_string(Image.open(p), lang="eng+chi_sim"), "tesseract"

def convert_audio(p):
    from app.ingestion.asr_adapter import transcribe
    r = transcribe(p)
    return r["text"], r["engine"]

TEXT_EXTS = {".md", ".txt", ".csv", ".json", ".canvas", ".ajson", ".html"}
SKIP_EXTS = {".css", ".js", ".cfg", ".ps1", ".sample", ".svg", ".gif", ".webp", ".mp4", ".mp3", ".doc", ".pptx", ".xlsx", "(none)"}

receipts = []
stats = collections.Counter()
gates = collections.Counter()
failures = collections.Counter()
total_chars = 0
img_done = 0
aud_done = 0

for dirpath, dirnames, filenames in os.walk(ROOT):
    for f in filenames:
        p = os.path.join(dirpath, f)
        ext = os.path.splitext(f)[1].lower()
        rel = p.replace(ROOT + "/", "")
        stats["total"] += 1
        engine = None
        text = ""
        t0 = time.monotonic()
        try:
            if ext in TEXT_EXTS:
                text = read_text(p)
                engine = "passthrough"
            elif ext == ".pdf":
                text, engine = convert_pdf(p)
            elif ext == ".docx":
                text, engine = convert_docx(p)
            elif ext in {".png", ".jpg", ".jpeg"}:
                if img_done >= CAP_IMAGES:
                    stats["image_capped"] += 1
                    continue
                text, engine = convert_image(p)
                img_done += 1
            elif ext in {".mp3", ".m4a", ".wav", ".flac"}:
                if aud_done >= CAP_AUDIO:
                    stats["audio_capped"] += 1
                    continue
                if os.path.getsize(p) > 5 * 1024 * 1024:
                    stats["audio_skipped_large"] += 1
                    continue
                text, engine = convert_audio(p)
                aud_done += 1
            else:
                stats["skipped"] += 1
                continue
        except Exception:
            failures[ext or "other"] += 1
            continue
        if time.monotonic() - t0 > PER_FILE_BUDGET:
            stats["over_budget"] += 1
        gate = ocr_gate(text).verdict if text.strip() else "fail"
        gates[gate] += 1
        total_chars += len(text)
        stats[ext or "(none)"] += 1
        receipts.append({"file": rel, "engine": engine or "?", "chars": len(text), "gate": gate, "size_kb": round(os.path.getsize(p) / 1024, 1)})

converted = sum(v for k, v in stats.items() if k.startswith("."))
summary = {"total": stats["total"], "converted": converted, "by_ext": dict(stats), "gates": dict(gates), "failures": dict(failures), "total_chars": total_chars, "image_capped": stats.get("image_capped", 0), "audio_capped": stats.get("audio_capped", 0), "skipped": stats.get("skipped", 0)}
payload = {"summary": summary, "receipts": receipts}
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(payload, f, ensure_ascii=False)
print(json.dumps(summary, ensure_ascii=False))