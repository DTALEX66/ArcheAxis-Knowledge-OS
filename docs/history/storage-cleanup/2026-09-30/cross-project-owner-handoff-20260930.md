# Cross-project owner migration and handoff — 2026-09-30

## User direction

The user authorizes confirmed material belonging to another project to be moved to that project's canonical owner location, with a written handoff or a branch in that owner repository. This authorizes the scoped migration work; it does not make an unrelated repository an owner destination. Do not delete the only verified copy before the owner-side receipt is read back.

## Ownership and current disposition

| Material | Owner | Current verified location | Evidence / state | Owner-side action |
|---|---|---|---|---|
| DSH-executed backend runtime snapshot | ArcheAxis Knowledge OS | `D:\All projects\ArcheAxis-Knowledge-OS\.project-local\mig\dsh-backend-runtime-20260928\objects` plus `archive-manifest.json` | Corrected ownership: R6 names `DTALEX66/ArcheAxis-Knowledge-OS` as the target repository and lists DSH as an execution actor. The archive schema is `aaos.content-addressed-runtime-archive.v1`; all 7 packages were reconstructed and file sizes/SHA-256 matched. | Keep under AAOS `.project-local/mig`; it is an AAOS task artifact. No transfer to DSH Desktop or a separate DSH repository. |
| DSH-executed wheel qualification snapshot | ArcheAxis Knowledge OS | `D:\All projects\ArcheAxis-Knowledge-OS\.project-local\mig\dsh-wheel-qual-20260928\AAOS-DSH-WHEEL-QUAL-ee015075.zip` | Corrected ownership: its manifest/schema is `aaos.spillover-archive.v1`; ZIP SHA-256 is `031304DE1477297E5BDD182258DE438FB46892BB867488A046889D3B1370E597` and prior receipt validates CRC, paths, sizes and SHA-256. | Keep under the AAOS migration area. It is not a DSH-owned repository payload. |
| Candidate run SQLite groups | ArcheAxis Knowledge OS | `D:\All projects\ArcheAxis-Knowledge-OS\.project-local\mig\candidate-run-20260928\` | The 16-file manifest records the original root `D:\All projects\AAOS candidate run`; payloads are SQLite main DB plus `-wal`, `-shm`, and writer-lock files across `data`, `data2`, `data3`, and `final`. It is AAOS candidate evidence and must stay grouped. | Keep in AAOS `.project-local` under its existing migration evidence. Do not move this set into DSH. Any later merge must use the existing recovery report and preserve each group’s sidecars. |
| DSH desktop distribution and user data | DSH Desktop owner | `D:\All projects\DSH` | Read-only audit found desktop installation, `.dsh` user data/backups, migrations, and package store. It is not the DSH backend repository. | Leave with DSH Desktop. Do not use as a destination for backend source snapshots. |
| DSH-executed AAOS task worktrees | ArcheAxis Knowledge OS | Formal `.project-local\worktrees\dp-f01-20260925`, `dsh-backend-20260927`, `dsh-backend-r5`, `dsh-governance-20260927` | All four git-common-dir values point to the AAOS `.git`; their origin is the AAOS GitHub repository. R6 and task assignments identify DSH as an execution actor. Commits `7503195b`, `75f2dd1f`, and `ca26bcf5` are reachable from local `main` and matching origin refs. `793e06ee` was not referenced by a branch; local branch `codex/dp-f01-20260925` now points to that exact commit. The four paths contain AAOS source/docs; three larger worktrees also retain ignored runtime/build data. | This is AAOS work, not a transfer to DSH. Do not remove worktrees with ignored data merely because Git tracked status is clean. Reclaim only after preserving or explicitly disposing each ignored payload. |
| Historical DSH task Git bundle | ArcheAxis Knowledge OS | Removed from `.project-local\mig` after ref verification | Formerly 46,095,363 B; SHA-256 `A0D70082D9E6B38D7FC3A34FF7FAB04E51BD93BA6CCD00CD8AB144B85BA2C1B9`. Pre-removal `git bundle list-heads` matched all four commits. At that readback, `793e06ee` was protected by AAOS branch `codex/dp-f01-20260925` and the other three commits were reachable from AAOS refs. Commit preservation does not require the subsequently removed task worktrees to remain present. Post-removal readback confirmed file absent and refs intact. | Duplicate bundle removed; no commit object was lost. |
| Obsidian-Assistance / LibreOffice registration | Ownership unresolved | Existing Windows MSI/uninstall registration and the referenced Obsidian-Assistance path | `soffice.exe` was not found at the registered path; no installation source was proven. | No file migration yet. Once actual installation files and owner repo are identified, document and route them there; do not copy the Obsidian repository into AAOS. |

## Corrected ownership decision

The prior interpretation was wrong: DSH is an execution actor inside the AAOS R6 plan, not the owner of these backend/wheel artifacts. The three old source roots are absent, but their content-addressed archives and task outputs are AAOS-owned by schema and task assignment. The extant `D:\All projects\DSH` is a separate DSH Desktop application/user-data location and must remain separate. No DSH Desktop data is migrated into AAOS.

The AAOS task commit set is preserved as follows:

1. `793e06ee` is now referenced by AAOS branch `codex/dp-f01-20260925`.
2. `7503195b`, `75f2dd1f`, and `ca26bcf5` are reachable from AAOS `main` and matching origin refs.
3. This does not claim all four commits are integrated into the current dirty `codex/Audit` worktree; check exact branch/tree before integration.
4. Preserve ignored user/runtime/build data in task worktrees until separately inventoried. Any future cleanup must use the supported Git worktree lifecycle and exact restoration state.

## Boundary

This handoff does not authorize E:/F: access. It does not authorize moving AAOS candidate-run databases into DSH, placing AAOS task/runtime data in product source, or changing DSH Desktop user data. Current evidence level: `VERIFIED_AAOS_TASK_ARTIFACTS`; DSH Desktop user data remains separate.
