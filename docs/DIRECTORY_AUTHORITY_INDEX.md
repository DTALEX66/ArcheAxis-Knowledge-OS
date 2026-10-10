# Directory Authority Index

> **2026-10-09 当前执行覆盖**：用户已选择新 UI 优先任务及 G01；规范活动指针为 [AAOS-ACTIVE-EXECUTION](current/AAOS-ACTIVE-EXECUTION.json)，当前任务来源为 [UI 优先 TaskPack](taskpacks/aaos-ui-first-20261009/TASKPACK.md)，实际进度只读 [UI 执行记录](current/AAOS-UI-FIRST-EXECUTION-20261009.md)。规划原文的 PLANNING_READY / NOT_EXECUTED 是规划时状态，激活与实际结果由当前覆盖记录，不改写不可变原包。AAOS-01 Q00–Q15 台账仅记录该继承工作流，不代表新 UI 全队列；旧 R6/M0 整包顺序冻结，有效合同、单一 Rust Core writer、内容先保存及历史证据保留。V01 继续暂停。
> 当前新布局、架构和其余产品界面按新任务执行；默认 `blueprint`，配套 `blueprint-light`，旧 `black` / `white` / `cosmic` 仅为额外配色主题。五主题共用新布局、组件状态及统一语义颜色；一个主题内部的按钮、菜单、侧栏与正文保持一致。主题不更改 Core 配置或知识数据。
> 平台指令优先；平台范围内用户当前明确决定优先于项目旧描述。此文档同步不授予 commit、push、merge、发布、私人账户/会话访问或恢复暂停的云端任务权限；本机资源索引不是云端权限。


> Canonical directory classification for maintenance and future normalization.
> It names what a path is; it does not authorize a move, cleanup or deletion.

本机具体资源根以 [共享资源路径索引](SHARED_RESOURCE_PATH_INDEX.md) 为准：共用模型、外置工具、绿色软件、绿色版真实资料库、项目测试资料库分属不同职责。不得把真实资料库当测试目录或把共享库当本项目清理对象。

## Authoritative topology

Current task selection is resolved by the active-execution pointer; ownership reconciliation retains the R6/M0 preservation constraints, SUP-022 and this index;
[R5-PATH-DISPOSITION.json](current/R5-PATH-DISPOSITION.json) is historical evidence.
The 0910 measurement keeps its original SHA and 69 historical gaps. R5 assigned
metadata owners and maintenance-only legacy lanes; that historical assignment is
not semantic absorption or a deletion grant. `.zcode/**` is private state and
denied for commit.

| Path / surface | Class | Canonical role | Normalization rule |
| --- | --- | --- | --- |
| `app/`, `shared/`, `knowledge_base/`, `inspiration_research/` | `LEGACY_SOURCE` / `MIGRATION_DONOR` | Preserved Python-era product/domain implementation for Green compatibility, recovery and migration. It is not the formal vNext desktop/Core or isolated Python-worker boundary. Existing legacy aggregates keep their current single writer until a validated, aggregate-specific migration. | Inventory consumers and writer ownership before changing a module boundary. |
| `apps/ArcheAxis.Desktop/` | `MIGRATION_DONOR` | Preserved Avalonia behavior and recovery reference under SUP-022 | Absorb qualified behavior into the formal host; retain old assets and do not claim installed takeover or Owner acceptance from this classification. |
| `crates/`, `services/python-workers/`, `packages/contracts/` | `SOURCE` | Rust Core, isolated capabilities, shared contracts | One vNext writer; actual protocol output must be validated. |
| `frontend/` | `SOURCE` | Formal React/TypeScript/Vite product UI under SUP-022 | Finite HostAdapter commands and generated contracts; no direct database, arbitrary file or Shell access. |
| `src-tauri/` | `SOURCE` | Formal Tauri 2 host under SUP-022 | Own Core lifecycle and finite authenticated business bridge; Rust Core remains the sole canonical writer. |
| `desktop/`, `desktop/bootstrap/` | `COMPATIBILITY_SHIM` | Separate recovery shell/fallback | Preserve until its production-use matrix and G1 gate close. |
| `docs/current/`, `docs/truth/`, `docs/taskpacks/`, `docs/history/` | `CURRENT_RECORD`, `TRUTH_RECORD`, `PLAN`, `HISTORY` | Evidence, current records, plans and historical snapshots | Classify and link before archival; history is not deletion evidence. |
| `.hermes/` | `LEGACY_MIXED_PRESERVE` | Historical mixed assets; regenerability unverified | No new development writes; no blanket deletion. |
| `.project-local/` | `IGNORED_DEVELOPMENT` | Per-worktree/run state, caches and builds | Use `scripts/runtime/dev.py`; retained evidence is not disposable cache. |
| `.playwright-cli/` | `TRANSIENT_AUTOMATION` | Ignored browser-session residue | Remove only after exact content/path verification; it must never be staged. |
| Green `data/` | `PRESERVE_USER_DATA` | Out-of-repository runtime data | Never inspect, copy, clear, rename or delete for a repository repair. |
| Shared tool/model libraries | `EXTERNAL_BOUNDARY` | Reusable machine-local dependencies | May be consumed by declared path; never absorbed or reorganized by this repository. |

## Required records before a move

Every proposed relocation or archival action must first have one row compliant
with the [AX-DIR-010 inventory schema](current/AX_DIR_010_INVENTORY_SCHEMA.md):
source and target path, owner, data class, hashes, consumer scan, rollback,
verification and an exact deletion-authorization state.

The [directory-migration adoption map](current/AX_DIRECTORY_MIGRATION_TASK_ADOPTION_2026-09-02.md)
is a historical proposal, partially superseded by R6/M0 and its dated freeze
banner. Use this index and the current project authority for present path roles.
A dirty tree, unresolved consumer, missing rollback receipt or `NOT_REQUESTED`
deletion state still stops any exact-path move or deletion.

## Relationship to other authority records

- [Documentation authority](DOCUMENTATION_AUTHORITY_INDEX.md) classifies
  document truth/current/history status.
- [Runtime and delivery authority](RUNTIME_DELIVERY_AUTHORITY_INDEX.md)
  governs the Windows executable chain.
- [Language boundary authority](LANGUAGE_BOUNDARY_AUTHORITY_INDEX.md)
  governs implementation ownership; a directory name cannot change it.
- [Repository normalization state](current/REPOSITORY_NORMALIZATION_STATE_2026-09-03.md)
  is a frozen 2026-09-03 snapshot; its React/Tauri and G0 sequencing are
  superseded by R6/M0. Its dated hygiene evidence remains historical and does
  not authorize a move or deletion.


### Frozen donor archive — 2026-09-26

`docs/history/branch-donors/execution-reliability-20260926/` is HISTORICAL_RECORD, not execution authority. ARCHIVE.json identifies three exact-tip, byte-preserved repository documents and source hashes. This bounded archive is repository documentation; it does not classify other mixed history paths. The source branch was retired on 2026-09-27 after review and a verified full-history local bundle; the six bounded imported documents and duplicate/move dispositions are recorded in [the consolidation manifest](history/DOCUMENT-CONSOLIDATION-20260927.json). Other mixed history paths retain their protected classification.
