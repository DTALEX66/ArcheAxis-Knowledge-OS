# Project boundary repair — 2026-07-28

## Scope

Repair the current `archeaxis-workspace` boundary without modifying the separate `C:\Users\ALEX\Cognitive-OS` repository. Project code and project-owned runtime data remain under `D:\All projects\Cognitive-Loop-OS`; external software, shared environments, portable tools, and related configuration remain under `D:\All projects\OS configuration`.

## Repairs completed

- Pytest now forces `TMP`, `TEMP`, and `TMPDIR` to `.hermes/task-runtime/pytest-tmp`.
- Python bytecode cache for pytest is forced to `.hermes/task-runtime/pycache`.
- `tempfile.tempdir` is explicitly reset because pytest can cache the Windows user Temp root before test fixtures run.
- Added `tests/test_pytest_boundary.py` to fail if pytest temp or bytecode roots escape the project runtime.
- Removed the verified project-owned test spill from `C:\Users\ALEX\AppData\Local\Temp\pytest-of-ALEX` after all pytest processes exited.
- Removed the stale, inactive `C:\Users\ALEX\AppData\Local\com.archeaxis.cognitive-workspace` WebView2 profile. The authoritative development and installed profiles already exist under `.hermes/task-runtime/desktop-dev` and `.hermes/task-runtime/desktop-installed`.

## Preserved external state

`C:\Users\ALEX\Cognitive-OS` remains untouched. It is a separate Git worktree pointing to the `Cognitive-OS` remote and has a dirty `.gitignore`; ownership and disposal require a separate exact-path decision.

Hermes, Gateway, authentication, browser, WebView2 processes, and other shared workflow infrastructure were not migrated or deleted.

## Verification requirements

After this change, run the boundary regression, full pytest suite, Ruff, architecture/convention checks, Rust tests, and the Chromium/runtime HTTP smoke tests. Re-scan `%TEMP%` for project markers and verify the project worktree is clean before publication.
