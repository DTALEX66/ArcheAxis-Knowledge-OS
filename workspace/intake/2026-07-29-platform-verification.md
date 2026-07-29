# Platform Verification Evidence — 2026-07-29

## Scope

This note records the two platform axes separately. Windows native Tauri is the desktop product path; WSL2 is only a local reproduction environment for the Linux application lane.

## Windows native desktop axis

Local evidence from `config/platform/windows-linux-verification`:

- Rust `1.88.0`, Cargo `1.88.0`.
- Tauri CLI `2.11.4` after `npm ci --ignore-scripts --no-audit --no-fund` in `desktop/`.
- `cargo check --locked`: passed.
- `cargo build --locked`: passed; `desktop/src-tauri/target/debug/archeaxis-desktop-shell.exe`, 12,837,888 bytes.
- `cargo test --lib`: 11 passed.
- Ignored Windows lifecycle suite (`cargo test --test backend_lifecycle -- --ignored --nocapture`): 2 passed; both development and installed bundled-runtime launch/shutdown paths passed.
- Tauri frontend distribution is intentionally minimal: `desktop/bootstrap/index.html`, 157 bytes, is the configured `frontendDist`.
- The exact-SHA GitHub Windows lane supplied hosted evidence for native Windows runtime smoke, Rust library tests, locked Rust audit, release build, NSIS artifact presence, and installed NSIS lifecycle: run `30410127211`, all jobs successful.

## Linux / WSL axis

- `wsl.exe --status` and `wsl.exe --list --verbose` confirmed registered `Ubuntu-24.04` WSL2 distro, currently stopped.
- Inside the distro: Python `3.12.3` and repository `uv.lock` were readable.
- Local WSL pytest reproduction was not claimed: the distro does not currently have `pytest` installed. No distro installation or package mutation was performed.
- Hosted Ubuntu exact-SHA CI is the authoritative Linux evidence. Run `30410127211` passed Python 3.11/3.12/3.13 OS, KB, integration, lint, wheel, and browser lanes.

## Boundary and conclusion

- Windows native and Linux application evidence are not conflated.
- WSL2 is optional for local Linux reproduction and is not used as a substitute for native Windows desktop verification.
- No SQLite database or runtime artifact was shared between Windows and WSL during this verification.
- Result: GREEN for the repository's hosted two-axis platform gates; PARTIAL for local WSL reproduction because its optional pytest environment is not installed.
