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

Current project authority sets `apps/ArcheAxis.Desktop/` (C#/Avalonia) as the
formal desktop, the Rust service in `crates/archeaxis-api/` as the vNext Core
and canonical writer, and isolated Python workers in
`services/python-workers/`. The existing implementation still needs the R6
Windows/full-loop qualification; this map does not claim a usable vNext package.
Build/test commands use `scripts/runtime/dev.py` with `.project-local` outputs.
For the main checkout, Cargo uses `.project-local/build/cargo`, matching
the checked-in `.cargo/config.toml`; the launcher no longer creates a second
main-checkout Cargo cache. Linked worktrees launched through `dev.py` use
`.project-local/build/<worktree-id>/cargo` under the owning repository.
Other build outputs retain their worktree-specific paths. Historical outputs
are preserved; this routing change does not migrate or delete them.
See [current R6 execution](current/R6-EXECUTION.md),
[M0 direction](current/M0-DIRECTION-OVERRIDE-20260920.md), and
[language authority](LANGUAGE_BOUNDARY_AUTHORITY_INDEX.md).

| Layer | Formal vNext source | Boundary |
| --- | --- | --- |
| Formal desktop UI source | [`apps/ArcheAxis.Desktop/`](../apps/ArcheAxis.Desktop/) | C#/Avalonia product shell and Core supervisor. |
| Canonical Core | [`crates/archeaxis-api/`](../crates/archeaxis-api/) | Rust API/Core owns the vNext database; no dual write to legacy data. |
| Isolated capability workers | [`services/python-workers/`](../services/python-workers/) | Python workers receive bounded requests and do not own the vNext database. |

## Preserved Green v0.6.14 maintenance chain

The following chain diagnoses the existing installed Green product only.
It is not the formal vNext delivery route (SUP-007).

| Layer | Canonical location | Authority and verification boundary |
| --- | --- | --- |
| Legacy Green UI source | [`frontend/src/`](../frontend/src/) | Preserved React product surface for v0.6.14 maintenance/recovery; not the formal vNext desktop. Changes require its targeted legacy tests and build. |
| Legacy Green UI build | `.project-local/build/frontend-dist/` | Generated input to the legacy Tauri maintenance build; it is embedded, not loaded from a Green `bootstrap/` directory. The directory is intentionally absent from a clean source checkout. |
| Legacy Green desktop host | [`src-tauri/tauri.conf.json`](../src-tauri/tauri.conf.json) and [`src-tauri/src/main.rs`](../src-tauri/src/main.rs) | `com.archeaxis.workspace`, title `星环知识平台（ArcheAxis Knowledge）`, and `WebviewUrl::App`; this host serves the existing Green installation only. |
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
the exact-path R6/A16 Owner Gate authorizes it. They are not the vNext Avalonia
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

For the formal Avalonia desktop, use the R6 TaskPack Candidate gates and
project-local isolated runtime evidence. A local build or UI run does not
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
