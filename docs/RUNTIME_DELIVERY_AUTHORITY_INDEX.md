# Runtime and Delivery Authority Index

> **2026-10-09 当前执行覆盖**：用户已选择新 UI 优先任务及 G01；规范活动指针为 [AAOS-ACTIVE-EXECUTION](current/AAOS-ACTIVE-EXECUTION.json)，当前任务来源为 [UI 优先 TaskPack](taskpacks/aaos-ui-first-20261009/TASKPACK.md)，实际进度只读 [UI 执行记录](current/AAOS-UI-FIRST-EXECUTION-20261009.md)。规划原文的 PLANNING_READY / NOT_EXECUTED 是规划时状态，激活与实际结果由当前覆盖记录，不改写不可变原包。AAOS-01 Q00–Q15 台账仅记录该继承工作流，不代表新 UI 全队列；旧 R6/M0 整包顺序冻结，有效合同、单一 Rust Core writer、内容先保存及历史证据保留。V01 继续暂停。
> 当前新布局、架构和其余产品界面按新任务执行；默认 `blueprint`，配套 `blueprint-light`，旧 `black` / `white` / `cosmic` 仅为额外配色主题。五主题共用新布局、组件状态及统一语义颜色；一个主题内部的按钮、菜单、侧栏与正文保持一致。主题不更改 Core 配置或知识数据。
> 平台指令优先；平台范围内用户当前明确决定优先于项目旧描述。此文档同步不授予 commit、push、merge、发布、私人账户/会话访问或恢复暂停的云端任务权限；本机资源索引不是云端权限。


> Canonical map for tracing a Windows product window back to its source,
> build output and deployment target. It prevents a recovery-shell resource,
> a stale executable and a Green deployment from being treated as one thing.
> This is an authority map, not proof that a particular Green installation is
> running or that an artifact has passed CI.
>
> Machine-local tool/model/Green/material roots follow the
> [shared resource path index](SHARED_RESOURCE_PATH_INDEX.md).

## Formal vNext Windows product chain

SUP-022 sets `frontend/` (React/TypeScript/Vite) and `src-tauri/` (Rust/Tauri 2)
as the formal desktop, the Rust service in `crates/archeaxis-api/` as the vNext Core
and canonical writer, and isolated Python workers in
`services/python-workers/`. Qualification follows the selected UI slice and inherited AAOS-01 contracts under
SUP-022, retaining R6/M0 evidence and no-release boundaries. Actual
installed/Green evidence retains its inherited Q-ledger scope, while new UI progress is resolved by the active-execution pointer; this
map itself does not establish a qualified package.
Build/test commands use `scripts/runtime/dev.py` with `.project-local` outputs.
For the main checkout, Cargo uses `.project-local/build/cargo`, matching
the checked-in `.cargo/config.toml`; the launcher no longer creates a second
main-checkout Cargo cache. Linked worktrees launched through `dev.py` use
`.project-local/build/<worktree-id>/cargo` under the owning repository.
Other build outputs retain their worktree-specific paths. Historical outputs
are preserved; this routing change does not migrate or delete them.
See [active execution pointer](current/AAOS-ACTIVE-EXECUTION.json), [inherited AAOS-01 Q ledger](current/AAOS01-Q00-Q15-LEDGER-FINAL-20261005.md),
[inherited R6 execution](current/R6-EXECUTION.md),
[inherited M0 direction](current/M0-DIRECTION-OVERRIDE-20260920.md), and
[language authority](LANGUAGE_BOUNDARY_AUTHORITY_INDEX.md).

| Layer | Formal vNext source | Boundary |
| --- | --- | --- |
| Formal desktop UI source | [`frontend/`](../frontend/) | React/TypeScript/Vite content UI uses generated contracts and finite HostAdapter commands. |
| Formal desktop host | [`src-tauri/tauri.conf.json`](../src-tauri/tauri.conf.json) and [`src-tauri/src/main.rs`](../src-tauri/src/main.rs) | Tauri 2 owns the Core lifecycle and finite authenticated bridge; credentials stay in Rust memory. |
| Formal UI build | Owner `.project-local/runs/<worktree-id>/<run-id>/artifacts/frontend-dist/` | `npm --prefix frontend run build` and `npm --prefix frontend run tauri -- build` use `scripts/runtime/frontend.mjs` and the canonical `dev.py` router. Each invocation allocates its own run; the Tauri beforeBuild hook shares that invocation's run. The final CLI overlay, Rust watcher, and CI archive use the same path. Bare Tauri builds are refused by the hook; they cannot route their parent configuration. Historical `.project-local/build/frontend-dist/` is preserved. |
| Formal candidate preparation | [`scripts/release/stage_backend_runtime.py`](../scripts/release/stage_backend_runtime.py) | One authoritative runtime/worker/Core candidate preparation for desktop-fast and desktop-build; actual hashes and locked-runtime imports must be verified. `desktop/scripts/prepare_bundle.py` uses the owning repository's canonical `.project-local/cache/uv` and its allocated run's temporary wheel-build environment, including from linked worktrees. Historical per-checkout uv-desktop caches are preserved. |
| Formal portable candidate | [`scripts/release/tauri_portable_candidate.py`](../scripts/release/tauri_portable_candidate.py) | Current release host and exactly the declared backend resources, bound to the frozen source/build/member hashes. Fresh project-local candidate only; `portable.flag` selects sibling data. Static member verification and an isolated native journey are separate from NSIS installation and Owner qualification. Never replaces the daily Green installation. |
| Preserved Avalonia reference | [`apps/ArcheAxis.Desktop/`](../apps/ArcheAxis.Desktop/) | Behavior/recovery donor, not a second default product shell. |
| Canonical Core | [`crates/archeaxis-api/`](../crates/archeaxis-api/) | Rust API/Core owns the vNext database; no dual write to legacy data. |
| Isolated capability workers | [`services/python-workers/`](../services/python-workers/) | Python workers receive bounded requests and do not own the vNext database. |

## Preserved Green v0.6.14 maintenance chain

The following chain diagnoses the existing installed Green product only.
It is not the formal vNext delivery route under SUP-022. Source paths below refer
to the frozen v0.6.14 revision, not the current branch's formal Tauri/Core product.

| Layer | Canonical location | Authority and verification boundary |
| --- | --- | --- |
| Legacy Green UI source | `frontend/src/` at the frozen v0.6.14 revision | Historical React product surface for v0.6.14 maintenance/recovery; not the formal vNext desktop at that revision. Current branch files serve the SUP-022 formal UI. |
| Legacy Green UI build | `.project-local/build/frontend-dist/` | Generated input to the legacy Tauri maintenance build; it is embedded, not loaded from a Green `bootstrap/` directory. The directory is intentionally absent from a clean source checkout. |
| Legacy Green desktop host | `src-tauri/tauri.conf.json` and `src-tauri/src/main.rs` at the frozen v0.6.14 revision | `com.archeaxis.workspace`, title `星环知识平台（ArcheAxis Knowledge）`, and `WebviewUrl::App` are historical identifiers; shared path/title alone does not identify the current executable or backend contract. |
| Legacy Green maintenance candidate | `.project-local/build/tauri/release/ArcheAxis.exe` | Local build output only. Its SHA-256 must be read back before an authorized Green maintenance operation. |
| Green deployment target | `D:/All projects/ArcheAxis.Knowledge.Green-x64/ArcheAxis.exe` | Existing `v0.6.14` maintenance target. Replace only while no `ArcheAxis.exe` process is running; save a hash-addressed backup and require candidate/target SHA-256 equality. |
| Green GUI launcher | `D:/All projects/ArcheAxis.Knowledge.Green-x64/启动星环知识.vbs` | Silent GUI-only launch path. It starts the exact sibling `ArcheAxis.exe`; it must not invoke a console host. |

**Diagnostic rule:** the title alone is insufficient; verify the executable
path before assigning a window to the Green chain above. Do not inspect or replace
`bootstrap/` to repair that window unless the primary executable's own
evidence establishes a separate dependency.

## Recovery-shell boundary

| Layer | Canonical location | Non-equivalence rule |
| --- | --- | --- |
| Recovery desktop host | [`desktop/src-tauri/tauri.conf.json`](../desktop/src-tauri/tauri.conf.json) and [`desktop/src-tauri/src/lib.rs`](../desktop/src-tauri/src/lib.rs) | Distinct recovery identity, not the primary product host. |
| Recovery static fallback | [`desktop/bootstrap/`](../desktop/bootstrap/) | Used only by the recovery shell's filesystem fallback. It is not the embedded `frontend/dist` of the main application. |

## Required evidence for an authorized legacy Green maintenance repair

These steps apply only to a requested legacy Green maintenance operation after
the exact-path R6/A16 Owner Gate authorizes it. They are not the formal Tauri
Candidate workflow.

1. Identify the window title and executable path; reject an update if the
   target process is still running.
2. Confirm the exact Green target and Owner Gate receipt, then identify the
   owning legacy chain above before copying any file.
3. Build only the legacy Green maintenance surface and hash the candidate.
4. Back up and replace only the authorized exact target; read back candidate
   and target SHA-256 values and require equality.
5. Launch through `启动星环知识.vbs` without a terminal; record only the
   process path, version/status endpoint and visible UI result. Do not inspect,
   copy or clear Green `data/`.

For the formal Tauri desktop, use the selected UI slice gates and inherited AAOS-01 Candidate requirements under SUP-022,
R6/M0 preservation boundaries and project-local isolated runtime evidence. A local build or UI run does not
authorize Green replacement.

## Relationship to other authority records

- [`CONFIGURATION_AUTHORITY_INDEX.md`](CONFIGURATION_AUTHORITY_INDEX.md)
  governs configuration precedence.
- [`DOCUMENTATION_AUTHORITY_INDEX.md`](DOCUMENTATION_AUTHORITY_INDEX.md)
  governs documentation lookup and migration classification.
- [`LANGUAGE_BOUNDARY_AUTHORITY_INDEX.md`](LANGUAGE_BOUNDARY_AUTHORITY_INDEX.md)
  governs the current vNext shell and writer. The frozen
  [`current/AXM_G0_MIGRATION_FREEZE_RULES_2026-09-02.md`](current/AXM_G0_MIGRATION_FREEZE_RULES_2026-09-02.md)
  records legacy-database no-dual-write boundaries only; its old React/Tauri
  target and G0 shadow-cutover route are superseded.
- [`../.github/workflows/ci.yml`](../.github/workflows/ci.yml) is CI
  implementation; an artifact build is not a claim of exact-SHA CI success.
- [`../.github/workflows/nightly.yml`](../.github/workflows/nightly.yml)
  owns scheduled/manual full qualification. Its browser and Windows runtime
  jobs must use lock-bound frontend tooling and native PowerShell semantics;
  their local contract is
  [`../tests/test_nightly_runtime_gates.py`](../tests/test_nightly_runtime_gates.py).
  Neither workflow text nor its local contract proves a cloud run for a SHA.
