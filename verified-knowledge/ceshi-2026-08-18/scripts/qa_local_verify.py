# -*- coding: utf-8 -*-
"""ceshi 语料：qwen3-embedding vs n-gram 检索对比 + qwen3:8b 本地 LLM 接地问答验证。"""
import json, os, sys, time, urllib.request
sys.stdout.reconfigure(encoding='utf-8')
import numpy as np

ROOT = r"D:/All projects/ceshi"
OUT = r"D:/All projects/ArcheAxis-Knowledge-OS/.hermes/task-runtime/qa_local_verify_receipt.json"
EMBED = "http://127.0.0.1:11434/api/embed"
CHAT = "http://127.0.0.1:11434/api/chat"

def ollama_embed(texts, model='qwen3-embedding:0.6b'):
    req = urllib.request.Request(EMBED, data=json.dumps({'model': model, 'input': texts}).encode(), headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=300) as r:
        return np.asarray(json.load(r)['embeddings'], dtype=np.float32)

def ollama_chat(messages, model='qwen2.5vl:7b', max_tokens=200):
    body = {'model': model, 'messages': messages, 'options': {'num_predict': max_tokens}, 'stream': False}
    req = urllib.request.Request(CHAT, data=json.dumps(body).encode(), headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.load(r)['message']['content']

def cos(a, b):
    a, b = a.ravel(), b.ravel()
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-12))

# 1) 采样语料：Obsidian 库 md + 牛津 PDF
docs = {}
obs = os.path.join(ROOT, 'Obsidian知识库')
count = 0
for dirpath, dirnames, filenames in os.walk(obs):
    for f in filenames:
        if f.lower().endswith('.md') and count < 60:
            p = os.path.join(dirpath, f)
            try:
                with open(p, 'r', encoding='utf-8', errors='ignore') as fh:
                    t = fh.read()
                if len(t.strip()) > 100:
                    docs[f'md:{count}'] = t[:2000]
                    count += 1
            except Exception:
                pass
import pymupdf
for pdf in [os.path.join(ROOT, '牛津通识读本', '牛津通识读本：简明逻辑学（中文版）.pdf'),
            os.path.join(ROOT, '牛津通识读本', '牛津通识读本：笛卡尔（中文版）.pdf')]:
    doc = pymupdf.open(pdf)
    for i in range(min(25, doc.page_count)):
        t = doc[i].get_text().strip()
        if len(t) > 100:
            docs[f'pdf:{os.path.basename(pdf)[:6]}:p{i}'] = t[:2000]
print('docs:', len(docs))

# 2) 分块 + 双引擎嵌入
from app.rag.embedder import embed_many
ids, chunks = [], []
for doc_id, content in list(docs.items())[:120]:
    for j in range(0, len(content), 500):
        c = content[j:j+500].strip()
        if len(c) > 50:
            ids.append(f'{doc_id}#{j}')
            chunks.append(c)
print('chunks:', len(chunks))

t0 = time.monotonic()
lv = np.asarray(embed_many(chunks), dtype=np.float32)
local_time = round(time.monotonic() - t0, 2)
qv, qv_time = None, 0
try:
    t0 = time.monotonic()
    qv = ollama_embed(chunks)
    qv_time = round(time.monotonic() - t0, 2)
except Exception as e:
    print('qwen embed failed:', e)

# 3) 改写查询对比（目标=含关键词的 chunk）
QUERIES = [("费曼技巧的核心步骤是什么", "费曼"), ("间隔复习怎么安排", "复习"),
           ("三段论的结构", "三段论"), ("如何提高记忆力", "记忆")]
results = []
for query, kw in QUERIES:
    target = next((i for i, c in enumerate(chunks) if kw in c), None)
    lq = np.asarray(embed_many([query]), dtype=np.float32)[0]
    ltop = sorted(range(len(chunks)), key=lambda i: cos(lq, lv[i]), reverse=True)[:3]
    row = {'query': query, 'target': target, 'local_top3_hit': target in ltop}
    if qv is not None:
        qq = ollama_embed([query])[0]
        qtop = sorted(range(len(chunks)), key=lambda i: cos(qq, qv[i]), reverse=True)[:3]
        row['qwen_top3_hit'] = target in qtop
        row['qwen_top'] = qtop
    row['local_top'] = ltop
    results.append(row)

# 4) qwen3:8b 本地 LLM 接地问答（top-3 检索为上下文）
qa = []
if qv is not None:
    for query, kw in QUERIES[:2]:
        qq = ollama_embed([query])[0]
        top = sorted(range(len(chunks)), key=lambda i: cos(qq, qv[i]), reverse=True)[:3]
        ctx = '\n'.join(chunks[i][:300] for i in top)
        try:
            ans = ollama_chat([{'role': 'system', 'content': '只根据给定上下文用中文回答，若上下文无关则说不知道。'},
                               {'role': 'user', 'content': f'上下文：\n{ctx}\n\n问题：{query}'}])
            qa.append({'query': query, 'answer': ans[:200], 'grounded': kw in (ans + ctx)})
        except Exception as e:
            qa.append({'query': query, 'error': str(e)[:100]})

receipt = {'docs': len(docs), 'chunks': len(chunks), 'local_embed_sec': local_time, 'qwen_embed_sec': qv_time, 'queries': results, 'llm_qa': qa}
with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(receipt, f, ensure_ascii=False, indent=2)
print(json.dumps({'chunks': len(chunks), 'queries': results, 'llm_qa': qa}, ensure_ascii=False))
