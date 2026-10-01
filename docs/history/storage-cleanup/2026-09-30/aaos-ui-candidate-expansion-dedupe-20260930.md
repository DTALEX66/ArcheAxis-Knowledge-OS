# AAOS UI candidate expansion dedupe — 2026-09-30

## Disposition

Six expanded candidate-package directories under `.project-local/runs/aaos-ui-current-candidate-20260926/` were removed after their existing sibling ZIPs were verified byte-for-byte equivalent. The sibling ZIPs remain at their original paths. This reduces the Formal repository's logical size by **4,810,102,438 bytes / 109,482 files**. The user-data-bearing `audit-final-x64` expansion was deliberately retained because it contains `workspace.sqlite`, `workspace.sqlite-shm`, `workspace.sqlite-wal`, and `workspace.sqlite.writer.lock` entries absent from its ZIP; none of those contents was read.

The six source trees each contained 18,247 files. The immediately-before-removal source tree SHA-256 values, ZIP sizes and ZIP SHA-256 values are in `.project-local/mig/aaos-current-candidate-expansion-dedupe-20260930/preflight.json`; the final readback is in `verification.json`. All six source tree hashes matched the earlier independent audit, all target paths now read absent, and all recovery ZIPs remain present. The independent audit read each archive to EOF and reported CRC PASS, exact relative member paths/lengths/SHA-256, no reparse points, and no DB/WAL/SHM/lock members in the six removed trees. A final visible-process-path check found no running process under the candidate root. It did not inspect inaccessible process handles or command lines.

## Recovery

Extract the exact same-basename sibling `.zip` back to the removed directory path before a historical rerun. The verified `vfresh-2994efa` candidate remains fully recoverable from its sibling ZIP; this action does not make the candidate a current-source build or grant release readiness. Existing R6 execution entries remain historical evidence; see the newer R6 follow-up entry for the current archive-backed state.

## Evidence and limits

- Source tree hashes were recomputed immediately before removal and matched the independent audit's six hashes.
- ZIP sizes and SHA-256 values were rechecked before removal; CRC and per-member equivalence were established by the independent audit.
- No SQLite, WAL, SHM, or writer-lock content was opened or hashed in this round.
- D drive free space is a separate drive-wide metric and is not attributed solely to this removal.
- Build, test, release, and installed-runtime gates were not run as part of this storage action.
