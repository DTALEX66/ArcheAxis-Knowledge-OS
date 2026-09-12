# R01 — cache growth-stop and capacity baseline (2026-09-11)

Slice: R01 (C10 -> X01, X14), stage M0, dependency R00. Status:
IMPLEMENTED_PENDING_AUDIT for the parts below; remaining scope listed in §6.

## 1. Method and scope (so the numbers cannot be misread)

- Tool: `scripts/maintenance/inventory_project.py` (read-only, metadata only,
  never opens file content). It sums **logical bytes of successfully observed
  regular files**; hard-linked paths contribute their logical size independently
  (`file_identity: not_collected`); allocated/physical space is
  `not_measured` by the tool.
- Scope: the exact Git project root. Opaque private/Git directories are
  **excluded and retained**, not measured: `.git`, `.hermes`, `.codex`, `.dsh`,
  `.openhuman`, `.claude`, agent-private roots, `sessions`, `memories`,
  credentials-like names. Reparse points/symlinks are skipped. No parent/child
  double counting (one group per top-level entry).
- Volume state is a separate measurement (filesystem free/used), never conflated
  with logical bytes.

## 2. Same-tool census (2026-09-11)

| Metric | Value |
| --- | --- |
| Observed logical total | **23.423 GiB** |
| Observed regular files | 130,120 |
| Observation errors | 20 |
| Excluded opaque entries | 60 |
| Skipped reparse points | 10 |

Largest groups (logical GiB / files):

| Group | GiB | Files |
| --- | --- | --- |
| `.project-local` | 16.595 | 79,224 |
| `target` (root, legacy) | 5.729 | 19,949 |
| `.venv` | 0.858 | 22,038 |
| `frontend` | 0.099 | 5,683 |
| `data` | 0.094 | 71 |
| `tests`, `shared`, rest | < 0.02 each | — |

Separately fingerprinted (not part of the total above): `.hermes`
**42.853 GiB / 718,077 files, newest write 2026-09-06 11:29** - unchanged from
the R2-era measurement, i.e. zero growth including all of today's real builds,
tests and host activity.

**The 23.423 GiB figure is not the whole repository**: it excludes the opaque
roots above and cannot be added to the 42.853 GiB `.hermes` figure to claim a
precise total (different scopes and methods). Volume state: **D: free 231.15 GiB,
used 234.61 GiB**.

Volume trend with causes (same volume, different times): 240.7 GiB free at the
R2-era record -> 235.98 GiB at the R2 round-240 census -> 234.0 GiB at the
X14 early census (2026-09-09) -> 231.15 GiB today. The decline is build/run
output: the cargo seal redirects bare cargo output into `.project-local`, so the
repository's build cache now grows **inside the governed location** rather than
at the root (`target` is frozen, see §3), plus run evidence and inventories under
`.project-local/runs`.

## 3. Growth-stop proof (real minimal build, not a doc claim)

Bare `cargo build -p archeaxis-api --offline` through the MSVC wrapper
`.project-local/runs/cargo-build-api.bat` (the wrapper is required because the
default GNU toolchain has no gcc/dlltool):

| Check | Before | After |
| --- | --- | --- |
| Root `target/` fingerprint | 6,151,810,038 bytes / 19,949 files | **identical** |
| `.project-local/build/cargo` | baseline | +52.6 MiB |
| Build result | — | exit 0, "Finished dev profile in 1.05s" |
| Artifact | — | `.project-local/build/cargo/debug/archeaxis-api.exe` (7,492,608 bytes) |

Root `target/` therefore has not grown across the R2-era X01 seal fingerprint and
today's build: growth-stopped, with the output relocated to the agreed
`.project-local` location by `.cargo/config.toml` (`[build] target-dir`).

## 4. Entry-point write destinations (audited)

| Entry point | Writes to |
| --- | --- |
| Bare `cargo build/test` | `.project-local/build/cargo` (sealed) |
| `scripts/ci/run_tests.sh/ps1`, `dev.py` | `.project-local/runs/<run-id>/` (tmp, cache, artifacts) |
| Full-workspace wrapper | `.project-local/build/cargo` + run log under `.project-local/runs` |
| Python venv / bytecode | `.venv`, `__pycache__` (git-ignored; not relocated) |
| DeepTutor validation host | `.project-local/deeptutor-val` (data, logs, evidence) |
| Inventories / receipts | `.project-local/inventory`, `.project-local/runs` |

Git tracked tree stays clean after these operations; `.gitignore` covers every
destination used (`/target/`, `.project-local/`, `.venv/`, `.hermes/`,
`__pycache__/`, `.pytest_cache/`, `build/`, data trees).

## 5. Inclusion / exclusion / unknown summary (for R12 and Q01 reuse)

- Included and measured: tracked sources, docs, tests, `frontend`, `shared`,
  `tools`, `packaging`, `data`, `.venv`, `.project-local`, legacy root `target`.
- Excluded, retained, **unknown size by this tool**: `.git`, `.hermes` (measured
  separately as a fingerprint only), `.codex`, `.dsh`, and other opaque
  agent-private roots; non-regular files; reparse points.
- Not read at all: `E:\`, real user libraries outside the repo, `.hermes`
  private content.
- Regenerable-cache candidates for a later authorized cleanup slice (R12), with
  sizes from this census: `.project-local/build` (cargo output), legacy root
  `target` 5.729 GiB, `.venv` 0.858 GiB, `.project-local/cache`.
- Unique history to preserve: docs, taskpacks, `.project-local/runs` receipts,
  `.project-local/inventory`, `.hermes`.

## 6. Remaining R01 scope (not claimed done)

- Packaging-side path diff in CI (RELEASE-01) and the browser/short-socket-path
  exceptions carried over from R2.
- Decide and document whether `__pycache__`/`.ruff_cache` bytecode caches should
  be redirected (`PYTHONPYCACHEPREFIX`) or explicitly accepted as git-ignored
  local caches; today they are accepted and excluded from the census by ignore
  rules, not governed by a redirect.
- Physical allocation measurement (allocated bytes per directory) is still not
  measured by this tool; only logical bytes plus volume free/used are reported.

## 7. Rollback

This slice changed no product code and no configuration; it adds this evidence
document plus ledger entries. Rollback = revert this documentation commit.
