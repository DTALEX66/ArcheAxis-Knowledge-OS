# 04｜B线模块与 API

## Inspiration-Research API

```text
POST /ir/research-note
POST /ir/intake-card
POST /ir/engineering-contract
GET  /ir/research-notes
GET  /ir/contracts/{contract_id}
```

## Knowledge-Base API

```text
POST /kb/documents
POST /kb/sources
POST /kb/cards
POST /kb/context-pack
POST /kb/taskpack
GET  /kb/search
GET  /kb/context-pack/{context_id}
GET  /kb/taskpack/{task_id}
```

## Cognitive-OS API

```text
GET  /health
POST /ingest
POST /route
POST /memory/search
POST /run
GET  /traces
GET  /memory/lessons
GET  /tools
```

## 内部模块建议

```text
inspiration_research/
  ingest/
  sources/
  analysis/
  intake/
  contracts/

knowledge_base/
  documents/
  sources/
  chunks/
  search/
  cards/
  context_pack/
  taskpack/
  machine_knowledge/

cognitive_os/
  ingestion/
  router/
  memory/
  retriever/
  compiler/
  permissions/
  tools/
  trace/
  evaluation/
  lessons/
```

## 第一阶段优先模块

```text
1. shared schemas
2. mock fixtures
3. context_pack builder
4. taskpack builder
5. cognitive_os /run mock execution
6. trace writer
7. lesson compiler
```
