# X14 cleanup manifest — PREPARATION (no deletion executed)

Plan: AAK-REUSE-FIRST-20260907-R2 / X14. Date: 2026-09-07. Purpose: exact
candidate list ready for an authorized deletion wave. **No file was deleted or
moved.** The 2026-09-07 census (run `be268a2d33/a1351353bc6f`) measured
66.625 GiB logical / 857,017 files; numbers below are that census or
directory file-count probes, to be re-measured immediately before any delete.

Category meanings (from audit tool): rebuildable candidate = regenerable with
the recorded rebuild command; project runtime = dev-managed caches under
`.project-local`; hermes = preserved (never auto-delete).

| Candidate (repo-relative) | Census/top-level ref | Probe | Ownership/use | Rebuild/lock | Rollback | State |
| --- | --- | --- | --- | --- | --- | --- |
| `src-tauri/target` | 5.181 GiB (top 2-level) | 47,923 files | legacy Tauri build tree (donor only, not vNext chain) | `cd src-tauri && cargo build` (needs tauri toolchain) | rebuild only; not source | NEEDS_AUTHORIZATION |
| `desktop/src-tauri/target` | inside desktop/src-tauri 4.896 GiB | 9,345 files | legacy desktop build tree (donor) | rebuild via its cargo project | rebuild only | NEEDS_AUTHORIZATION |
| `desktop/node_modules` | inside desktop/src-tauri | 19 files | legacy frontend node deps (tiny) | `npm install` per package-lock | rebuild only | NEEDS_AUTHORIZATION |
| `target/` | target/debug 1.802 GiB | 20,714 files | active Rust dev builds used by this session's `cargo test` | `cargo test/build` offline (deps cached in CARGO_HOME) | rebuild only | HOLD (in use) |
| `apps/ArcheAxis.Desktop/bin` + `obj` | apps total 0.677 GiB | 115+46 files | C# build outputs | `dotnet build apps/ArcheAxis.Desktop` | rebuild only | NEEDS_AUTHORIZATION (small) |
| repo `.pytest_cache`, `.ruff_cache` | negligible | 5+49 files | tool caches, regenerable | pytest/ruff recreate | recreate | APPROVED-READY (trivial, non-destructive to env) |
| `.project-local/build` | 8.398 GiB (top 2-level) | dev-root build cache (cargo/dotnet targets under dev.py) | dev-managed; delete forces full rebuild of dev caches | dev.py re-runs recreate | rebuild only | HOLD |
| `.hermes/**` | 42.855 GiB category | — | preserved legacy mixed material | — | — | NEVER AUTO-DELETE |
| model weights / 五库 / 资料库 | — | — | outside repo; shared | — | — | NOT IN SCOPE |

Verification before any deletion wave:
1. Pause repo writers; rerun the same census for before-numbers.
2. Delete only rows above whose State is APPROVED-READY or individually
   authorized; record a deletion manifest (path, bytes, rebuild command,
   rollback) in `.project-local/inventory/` (ignored).
3. Rerun census for after-numbers; run the affected startup/parsing/build
   checks and the smallest affected regression (per LOCAL-CLEANUP.md step 5).
4. `.hermes`, real user data, E-drive and shared libraries remain untouched.
