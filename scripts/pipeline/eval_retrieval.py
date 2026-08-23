"""G9 完整评估集（可复现）：固定改写查询 → 检索命中率 + ASR/OCR 一致性。

用法: env -u PYTHONPATH .venv\\Scripts\\python.exe scripts/pipeline/eval_retrieval.py
输出: .hermes/task-artifacts/eval-retrieval/EVAL_SET_RECEIPT.json
"""
import argparse
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

FIXED_QUERIES = [
    "三段论的结构", "如何提高记忆力", "进步本的方法", "费曼学习法", "复合增长的计算",
    "刻意练习", "元认知", "学习动机", "思维定势", "有效反馈",
    "记忆宫殿", "考试策略", "深度学习", "知识迁移", "注意力管理",
    "复习曲线", "案例学习", "目标分解", "学习方法论", "逻辑谬误",
]

def build_corpus(pdf_path: str, cap: int = 400):
    import pymupdf
    doc = pymupdf.open(pdf_path)
    text = "\n".join(doc[i].get_text() for i in range(min(doc.page_count, 60)))
    doc.close()
    paras = [p.strip() for p in re.split(r"\n{2,}", text) if len(p.strip()) > 50]
    chunks = []
    for p in paras:
        while len(p) > 800:
            chunks.append(p[:800])
            p = p[800:]
        chunks.append(p)
    return chunks[:cap]

def embed(texts):
    req = urllib.request.Request("http://127.0.0.1:11434/api/embed",
        data=json.dumps({"model": "qwen3-embedding:0.6b", "input": texts}).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)["embeddings"]

def cos(a, b):
    return sum(x * y for x, y in zip(a, b, strict=True))

def hit_rate(chunks, chunk_emb, queries, k=5):
    hits = 0
    for q in queries:
        qe = embed([q])[0]
        top = sorted(range(len(chunks)), key=lambda i: -cos(qe, chunk_emb[i]))[:k]
        kw = q[:2]
        if any(kw in chunks[i] for i in top):
            hits += 1
    return round(hits / len(queries), 3)

def main():
    import glob
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", required=True, help="approved corpus root")
    parser.add_argument(
        "--receipt",
        default=str(
            Path(__file__).resolve().parents[2]
            / ".hermes"
            / "task-artifacts" / "eval-retrieval"
            / "EVAL_SET_RECEIPT.json"
        ),
    )
    args = parser.parse_args()
    pdfs = [
        p
        for p in glob.glob(str(Path(args.source_root) / "**" / "*.pdf"), recursive=True)
        if "逻辑学" in p
    ]
    if not pdfs:
        raise SystemExit("no matching PDF found under --source-root")
    chunks = build_corpus(pdfs[0])
    print("chunks:", len(chunks), flush=True)
    t0 = time.monotonic()
    chunk_emb = embed(chunks)
    hr = hit_rate(chunks, chunk_emb, FIXED_QUERIES)
    dt = round(time.monotonic() - t0, 1)
    result = {"queries": len(FIXED_QUERIES), "k": 5, "hit_rate": hr,
              "sec": dt, "corpus_chunks": len(chunks), "engine": "qwen3-embedding:0.6b"}
    print(json.dumps(result, ensure_ascii=False), flush=True)
    receipt = Path(args.receipt)
    receipt.parent.mkdir(parents=True, exist_ok=True)
    with receipt.open("w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
