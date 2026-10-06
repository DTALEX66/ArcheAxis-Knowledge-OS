# Runtime and Delivery Authority Index

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
`services/python-workers/`. Qualification follows the AAOS-01 gates under
SUP-022, retaining inherited R6/M0 evidence and no-release boundaries. Actual
installed/Green status is recorded only in the current AAOS-01 ledger; this
map itself does not establish a qualified package.
Build/test commands use `scripts/runtime/dev.py` with `.project-local` outputs.
For the main checkout, Cargo uses `.project-local/build/cargo`, matching
the checked-in `.cargo/config.toml`; the launcher no longer creates a second
main-checkout Cargo cache. Linked worktrees launched through `dev.py` use
`.project-local/build/<worktree-id>/cargo` under the owning repository.
Other build outputs retain their worktree-specific paths. Historical outputs
are preserved; this routing change does not migrate or delete them.
See [current AAOS-01 ledger](current/AAOS01-Q00-Q15-LEDGER-FINAL-20261005.md),
[inherited R6 execution](current/R6-EXECUTION.md),
[inherited M0 direction](current/M0-DIRECTION-OVERRIDE-20260920.md), and
[language authority](LANGUAGE_BOUNDARY_AUTHORITY_INDEX.md).

| Layer | Formal vNext source | Boundary |
| --- | --- | --- |
| Formal desktop UI source | [`frontend/`](../frontend/) | React/TypeScript/Vite content UI uses generated contracts and finite HostAdapter commands. |
| Formal desktop host | [`src-tauri/tauri.conf.json`](../src-tauri/tauri.conf.json) and [`src-tauri/src/main.rs`](../src-tauri/src/main.rs) | Tauri 2 owns the Core lifecycle and finite authenticated bridge; credentials stay in Rust memory. |
| Formal UI build | `.project-local/build/frontend-dist/` | Embedded frontend output, not the recovery bootstrap or an installed Green identity. |
| Formal candidate preparation | [`scripts/release/stage_backend_runtime.py`](../scripts/release/stage_backend_runtime.py) | One authoritative runtime/worker/Core candidate preparation for desktop-fast and desktop-build; actual hashes and locked-runtime imports must be verified. |
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

For the formal Tauri desktop, use the AAOS-01 Candidate gates under SUP-022,
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
