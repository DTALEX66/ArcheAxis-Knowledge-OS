# Historical desktop-publish archive — 2026-09-30

Status: PASS for archive integrity, exact deletion and preserved Desktop binary readback.
Completed: 2026-09-30T01:38:31.911265+08:00

## Result

Archived and removed 22 historical child directories under `D:\All projects\ArcheAxis-Knowledge-OS\.project-local\build\desktop-publish`: **4,984 files / 4,798,503,361 logical bytes**. The parent directory remains. New ZIP: **1,659,496,511 bytes**. Logical net reduction: **3,139,006,850 bytes**; this is not a measured drive-wide free-space delta.

Archive: `D:\All projects\Record\AAOS-project-archives\2026-09-30\historical-desktop-publish-22dirs-20260930.zip`

Archive SHA-256: `98bb8ffbdabe2cbdb3d4fcf4c0ae7324a2e0b7a3dd985fd912e6a6c718b9c22c`

Complete ZIP payload manifest SHA-256: `e8c831ab9d7f379a4b094c925ca83cb8cab1c77b470a73bd3be6d46b832444b4`

## Exact removed directories and restoration

ZIP members use `<historical-child-name>/<original-relative-file-path>`. To restore all children, extract the ZIP into the original `desktop-publish` parent after checking that the intended destination children are absent. To restore one history item, extract only that child prefix. Recheck the restored per-file paths, lengths and SHA-256 against `preflight.json` before using a historical executable. Restore does not assert current-source compatibility.

| Child directory | Files | Original logical bytes | Per-child manifest SHA-256 |
|---|---:|---:|---|
| `current-p3` | 230 | 222779676 | `c3232eae7b7e471a7fcc918afdd994543f37d0091e3abb8a134cfd34af9bd0b7` |
| `current-p3-v2` | 229 | 216936764 | `74c84a61be39746c02c28190c81b45abd5ceb7eb007376d29248e8cb033482af` |
| `current-p3-v3` | 230 | 222786404 | `a44d493a0c4e585adfe76ba5ce82910f3dd640abc0cd4b67d19fa9a45d2a6663` |
| `current-p3-v4` | 230 | 222789432 | `2b45c750feeb9921684032a7c12123d9fc3b9353475fb8c8612c3752e67105e7` |
| `current-p3-v5` | 230 | 222792968 | `dae864801f7a0ed454172bd7da4983f95387472ccb5a6bce88f5db0a05866bcd` |
| `current-p3-v6` | 230 | 222794012 | `e0d8802667857b32d6183272668a0363d5089338483b3ad9eeeb0cea11c18b17` |
| `current-p3-v7` | 230 | 222796476 | `86130a63fc163defb82f27cba32b59f61ecf25fefbdd3908773502c983d9ff77` |
| `ui-commercial-pass` | 225 | 216450779 | `8f7b5cef04fd96e459d4bb27867e59bf7684f18e970080dd141021c0219a3af7` |
| `ui-commercial-pass-2` | 225 | 216452039 | `9d9f1cc552dbe4d8f5b42e129f893982c6a30a7a9bab0f9e40ec6cf2566aac84` |
| `ui-current` | 225 | 215546067 | `3fde404ab036ee76e54b86ad6a993140a6f7951ac0e8f0298f2b8beee14467cd` |
| `ui-final-pass` | 225 | 216459599 | `a0a7f2dc5cab95d524215b82cf359bc6f3b7b1d64781fe776b618d5507f44355` |
| `ui-final-pass-1534a881` | 225 | 216464527 | `b1fa327dcd6d939de05702d96eaf844fdeb6f95d0171267755f5d7292069edf7` |
| `ui-final-pass-16f0935e` | 225 | 216463935 | `6c028a389b1f84611f67f383818cffa0ec9ecfdd690f8da56cbc40b344567d70` |
| `ui-final-pass-2a9b31f4` | 225 | 216460211 | `c9c47fa22b02a229cd2a1f16d0ecd9911bc358af1ce45d0648215df02483695f` |
| `ui-final-pass-2d9fbb75` | 225 | 216463915 | `d12601373dff350a92892a8026e3e6f2c5a221f92f256fb4d0a4cf7321951e6f` |
| `ui-final-pass-38f44985` | 225 | 216460803 | `c163f07aeb8e7a4d5bc3205498fdd7394d4c4f7a1a7b6a0f7dab91ff845b713e` |
| `ui-final-pass-74f658d7` | 225 | 216462099 | `6facb3b37c3894b2d81cf95c6c4cdcea3c64fc4566c4126f7b4467ee7569dd37` |
| `ui-final-pass-80a12126` | 225 | 216463975 | `1b6c90ed4ad37824f4f38d6b4a8cb9ac035aef8110c95a9da34c38e201985b56` |
| `ui-final-pass-8156be8c` | 225 | 216465215 | `2dd385057dc87261bea4b3b48d5f7278601b7a1f3fa7350b87258f1c86167c37` |
| `ui-final-pass-9185186a` | 225 | 216465151 | `beb73aa2bd8890a32955a6129d6aa18a0a4b50e86540e7b55051ad274a9fc54c` |
| `ui-final-pass-9468a08e` | 225 | 216460247 | `6d3e39e6b7e6a11c387a93732d2f7f6e069899a45948559b4be85be6078fccc8` |
| `win-x64` | 225 | 215289067 | `3cbdeaca52b9a6399794ba64a76991d258106e1bd75aa21a3b166a7822ae463f` |

## Verification and preserved state

- Immediate source inventories matched the earlier complete 22-directory audit, including every file path, length and SHA. Full traversal rejected DB/SQLite/WAL/SHM/lock names, reparse points and enumeration errors; none were found.
- The ZIP was created with ZIP64 enabled, so uncompressed data over 4 GiB is supported. All 4,984 members were fully read; member path sets, lengths and SHA matched source, and CRC validation passed.
- After compression, all source files were hashed again. Immediately before deletion, source trees, full ZIP hash and formal Desktop sentinels were checked again; all agreed.
- Native PowerShell deletion was restricted to a constant allowlist of 22 fully resolved child paths. No other source path or parent was removed. Post-readback confirms all 22 children are absent, the parent exists and full ZIP SHA is unchanged.
- The separate formal output `.project-local/build/dotnet/ArcheAxis.Desktop` was explicitly outside the deletion scope. All 19 discovered Desktop EXE/DLL sentinels below it were recorded before archival and remained byte-for-byte unchanged after deletion. These include the existing Release outputs.
- No visible dotnet/ArcheAxis.Desktop/cargo/rustc process was present before archive and before deletion. This does not constitute protected-process handle enumeration.

## Historical consumers

`R6-EXECUTION.md` cites current-p3-v3/v6 and multiple ui-final-pass builds for historical smoke/contract evidence. `AAOS-UI-COMMERCIAL-AUDIT-20260923.md` references ui-commercial-pass-2, and `R5-EXECUTION.md` references win-x64. These records remain intact and receive additive location notes; the cited historical paths are now archive-backed, requiring restoration before rerunning. No test result, source identity or prior acceptance meaning was rewritten.

The currently indexed va5de4b13 candidate, all current-source candidates, formal dotnet tree, Core, user data, DB/WAL/SHM/lock material and E/F were untouched. All 22 requested objects met the deletion criteria; no directory in this batch was blocked or skipped.

## Receipts and limits

Machine receipts: `.project-local/mig/desktop-publish-history-archive-20260930/{preflight,verification,delete-ready,final}.json`. `preflight.json` includes all 4,984 per-file hashes and formal Desktop sentinels. Execution tools: `prepare_archive.py`, `delete_verified.ps1`.

Manifest digests use sorted relative path + TAB + decimal size + TAB + lowercase file SHA + LF, encoded as UTF-8. The whole archive manifest includes the child-directory prefix.

Product build, tests, UI launch, CI and release qualification were NOT_EXECUTED in this storage batch. Preserved-binary byte checks do not establish runtime PASS. Recovery is from the verified ZIP; no Git reset or source rollback is involved.
