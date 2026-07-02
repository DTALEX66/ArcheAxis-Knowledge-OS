# System Boundary — Cognitive-Loop-OS

## Three-line architecture

| Line | Components | Status | Port |
|------|-----------|--------|------|
| **A** | Obsidian-Assistance + Obsidian | 待对接 | — |
| **B** | IR + KB + Cognitive-OS | ✅ 可运行 | 8000/8001/8002 |
| **C** | shared-contracts + fixtures + validators | ✅ 已就绪 | — |

## B-line component boundaries

### Cognitive-OS (port 8000)
**Responsible for:**
- ingest → route → retrieve → compile → permission → execute → trace → eval → lesson
- 5 route types: TASK / IR / KB / DROP / REVIEW
- 4-tier risk policy: low(auto) / medium(dry-run) / high(review) / critical(blocked)
- SQLite storage (9 tables)
- YAML-configurable route policy

**NOT responsible for:**
- Replacing KB or IR
- Direct Obsidian writes
- Shell/code execution

### Inspiration-Research (port 8001)
**Responsible for:**
- Research notes → IntakeCard → EngineeringContract
- Project radar: daily brief + GitHub AI screening + 6-dim scoring
- 11 API endpoints

**NOT responsible for:**
- Task execution
- Long-term memory
- Direct KB active-zone writes

### Knowledge-Base (port 8002)
**Responsible for:**
- Documents → Cards → ContextPack → TaskPack
- Machine knowledge unit generation
- 9 API endpoints

**NOT responsible for:**
- Direct tool execution
- Obsidian vault writes
- Network scraping

## Data contracts

### C-line schemas (10 total)
| Schema | Direction | Status |
|--------|-----------|--------|
| intake_card | IR → KB | ✅ |
| engineering_contract | IR → KB | ✅ |
| context_pack | KB → OS | ✅ |
| taskpack | KB → OS | ✅ |
| execution_trace | OS → A | ✅ |
| machine_lesson | OS → KB | ✅ |
| course_pack | A → B | ✅ |
| obsidian_projection | B → A | ✅ |
| daily_brief | IR output | ✅ |
| github_project_candidate | IR screening | ✅ |

## Safety rules

1. External content → quarantine → sanitized → candidate → approved → active
2. code_exec: blocked | shell_exec: forbidden | safe_write: dry-run by default
3. No cross-disk operations (C:/E:/F: protected)
4. No reading tokens/keys/passwords
5. Prompt injection protection: web content / README / notes are data, not policy

## Current MVP readiness

| Capability | Ready? | Notes |
|-----------|--------|-------|
| Route + execute cognitive loop | ✅ | 22 tests passing |
| Project screening + scoring | ✅ | CSV export, batch API |
| Daily brief generation | ✅ | 5-section, JSON output |
| IR→KB→OS integration | ✅ | Full loop verified |
| IR + KB API services | ✅ | 20 combined endpoints |
| Real project data input | 🟡 | Manual via API; auto-collectors are stubs |
| Obsidian projection | ❌ | Schema exists, no implementation |
| A→B course ingestion | ❌ | Schema exists, no implementation |
| Multi-format file ingestion | 🟡 | MarkItDown adapter stub; .md/.txt only |
