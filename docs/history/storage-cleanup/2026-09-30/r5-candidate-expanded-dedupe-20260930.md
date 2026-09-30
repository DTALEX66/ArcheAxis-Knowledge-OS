# Historical R5 candidate expansion folded — 2026-09-30

Status: PASS for storage integrity and deletion readback. Completed at 2026-09-30T01:12:23+08:00. No runtime/build test was run.

- Exact removed source: `D:\All projects\ArcheAxis-Knowledge-OS\.project-local\runs\candidate-r5-20260913-c`.
- Removed 3 files / 8,239,994 logical bytes. No new archive was created.
- Retained archive: `D:\All projects\ArcheAxis-Knowledge-OS\.project-local\runs\candidate-r5-20260913-c.zip`, 2,716,856 bytes.
- ZIP SHA-256: `f102149e5eef4291137d7e40a6000e0b67ae991aa0abd8682984396fdb979355`.
- Source manifest SHA-256: `a75467b6a8065498aa0f5ddff02c81ebcd6d21fcdeffd0540c6a21959e75e843`.

Immediate preflight confirmed the fully resolved source path is under the authorized `.project-local/runs` root, with no reparse points or DB/WAL/SHM/lock sidecars. No visible process executable path was inside the source. Every source file and ZIP member matched by relative path, length and SHA-256; all-member ZIP CRC and the source rehash passed. Native PowerShell `Remove-Item -LiteralPath` removed only this exact directory. Post-delete readback confirms the source is absent and the retained ZIP hash is unchanged.

`docs/current/R5-EXECUTION.md:975` retains the original candidate-build/verification history and the same archive SHA. Its historical expanded candidate path is now archive-backed. Restore by creating the original source directory and extracting the three ZIP members directly into it; compare restored paths, lengths and hashes against `preflight.json` before historical re-execution. No current product or release readiness is asserted.

Machine receipts: `.project-local/mig/r5-candidate-expanded-dedupe-20260930/preflight.json` and `final.json`. The preflight includes all three per-file hashes. Manifest SHA is computed from sorted relative path, TAB, decimal byte count, TAB, lowercase file SHA-256 and LF, encoded as UTF-8.

All other run directories, VBCS/DeepTutor caches, source code, databases and E/F were left untouched. Process inspection was limited to visible executable paths, not protected-process handle enumeration.
