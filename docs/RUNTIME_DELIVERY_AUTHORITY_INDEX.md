# Runtime and Delivery Authority Index

> Canonical map for tracing a Windows product window back to its source,
> build output and deployment target. It prevents a recovery-shell resource,
> a stale executable and a Green deployment from being treated as one thing.
> This is an authority map, not proof that a particular Green installation is
> running or that an artifact has passed CI.

## Primary Windows product chain

| Layer | Canonical location | Authority and verification boundary |
| --- | --- | --- |
| Product UI source | [`frontend/src/`](../frontend/src/) | React product surface; changes require its targeted tests and build. |
| Product UI build | [`frontend/dist/`](../frontend/dist/) | Generated input to the primary Tauri build; it is embedded, not loaded from a Green `bootstrap/` directory. |
| Primary desktop host | [`src-tauri/tauri.conf.json`](../src-tauri/tauri.conf.json) and [`src-tauri/src/main.rs`](../src-tauri/src/main.rs) | `com.archeaxis.workspace`, title `星环知识平台（ArcheAxis Knowledge）`, and `WebviewUrl::App`. This is the user-facing desktop host. |
| Candidate executable | `src-tauri/target/release/ArcheAxis.exe` | Local build output only. Its SHA-256 must be read back before any Green replacement. |
| Green deployment target | `D:/All projects/ArcheAxis.Knowledge.Green-x64/ArcheAxis.exe` | Existing `v0.6.14` maintenance target. Replace only while no `ArcheAxis.exe` process is running; save a hash-addressed backup and require candidate/target SHA-256 equality. |
| Green GUI launcher | `D:/All projects/ArcheAxis.Knowledge.Green-x64/启动星环知识.vbs` | Silent GUI-only launch path. It starts the exact sibling `ArcheAxis.exe`; it must not invoke a console host. |

**Diagnostic rule:** a window titled `星环知识平台（ArcheAxis Knowledge）`
belongs to the primary chain above. Do not inspect or replace
`bootstrap/` to repair that window unless the primary executable's own
evidence establishes a separate dependency.

## Recovery-shell boundary

| Layer | Canonical location | Non-equivalence rule |
| --- | --- | --- |
| Recovery desktop host | [`desktop/src-tauri/tauri.conf.json`](../desktop/src-tauri/tauri.conf.json) and [`desktop/src-tauri/src/lib.rs`](../desktop/src-tauri/src/lib.rs) | Distinct recovery identity, not the primary product host. |
| Recovery static fallback | [`desktop/bootstrap/`](../desktop/bootstrap/) | Used only by the recovery shell's filesystem fallback. It is not the embedded `frontend/dist` of the main application. |

## Required evidence for a UI repair

1. Identify the window title and executable path; reject an update if the
   target process is still running.
2. Identify the owning chain from the tables above before copying any file.
3. Build only the owning surface and hash the candidate output.
4. Back up the exact Green target, replace it, then read back candidate and
   target SHA-256 values for equality.
5. Launch through `启动星环知识.vbs` without a terminal; record only the
   process path, version/status endpoint and visible UI result. Do not inspect,
   copy or clear Green `data/` to make a visual problem disappear.

## Relationship to other authority records

- [`CONFIGURATION_AUTHORITY_INDEX.md`](CONFIGURATION_AUTHORITY_INDEX.md)
  governs configuration precedence.
- [`DOCUMENTATION_AUTHORITY_INDEX.md`](DOCUMENTATION_AUTHORITY_INDEX.md)
  governs documentation lookup and migration classification.
- [`current/AXM_G0_MIGRATION_FREEZE_RULES_2026-09-02.md`](current/AXM_G0_MIGRATION_FREEZE_RULES_2026-09-02.md)
  keeps Green repairs narrow and preserves the existing data writer.
- [`../.github/workflows/ci.yml`](../.github/workflows/ci.yml) is CI
  implementation; an artifact build is not a claim of exact-SHA CI success.
- [`../.github/workflows/nightly.yml`](../.github/workflows/nightly.yml)
  owns scheduled/manual full qualification. Its browser and Windows runtime
  jobs must use lock-bound frontend tooling and native PowerShell semantics;
  their local contract is
  [`../tests/test_nightly_runtime_gates.py`](../tests/test_nightly_runtime_gates.py).
  Neither workflow text nor its local contract proves a cloud run for a SHA.
