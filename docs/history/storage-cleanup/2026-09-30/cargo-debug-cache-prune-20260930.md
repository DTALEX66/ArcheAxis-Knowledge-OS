# Cargo debug cache cleanup — 2026-09-30

## Result

Removed only four regenerable Cargo debug subdirectories under
`.project-local/build/cargo/debug/`: `deps`, `build`, `examples`, and
`.fingerprint`. This reclaimed 14,307,581,655 logical bytes across 5,786 files.
All targets were inside the project-owned `.project-local` build tree, had no
reparse points, and contained no database/WAL/SHM/lock-named files. No active
Cargo/Rust/Core process was found before removal.

## Preserved

The debug root Core EXE/PDB/RLIB and lock files were SHA-256 checked before and
after and were unchanged. The entire release tree was preserved. The retained
Cargo cache remains available for offline regeneration.

## Recovery

Regenerate the removed debug intermediates from the tracked lockfile and local
Cargo cache with:

```powershell
scripts\ci\cargo_test.bat build --workspace --locked --offline
```

This recovery command was not run as part of cleanup.

## Evidence

- Preflight: `.project-local/mig/cargo-debug-cache-prune-20260930/preflight.json`
- Readback: `.project-local/mig/cargo-debug-cache-prune-20260930/final.json`
- Drive D free space changed from 153,503,076,352 B to 167,529,525,248 B
  (+14,026,448,896 B system-wide). The volume-wide delta can include concurrent
  activity, so it is not treated as an exact attribution of reclaimed bytes.
- C/D volumes were previously reported NTFS Healthy/OK; machine-wide SFC/DISM
  health remains unverified because the commands require an elevated admin
  context not available to this run.

Status: **PASS** for the bounded cache cleanup and readback; **NOT_EXECUTED** for
the recovery build and administrator-only system integrity checks.
