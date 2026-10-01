# Current-source Green candidate expansion review — 2026-09-30

> 后续执行更新：本轮已复核并删除 801,672,850 B 展开副本；原 sibling ZIP 保留且 SHA-256 不变。下文 `PRESERVED_THIS_TURN` 是此前只读阶段的历史状态。恢复旧展开路径后才能重跑历史验收。见 `storage-cleanup-current-goal-20260930.md` 及本地 `candidate-prune-readback.json`。

## Decision

`VERIFIED_DUPLICATE_EXPANSION; PRESERVED_THIS_TURN`. The 801.7 MB current-source expansion and its 285.1 MB sibling ZIP are byte-identical by all 18,247 member paths, lengths and SHA-256 hashes; ZIP CRC readback passed. The candidate is still cited by `docs/current/R6-EXECUTION.md` as current dirty-source evidence. The expansion and ZIP remain at their original paths; no deletion was attempted. A future compaction must retain the ZIP and restore the expansion to the exact path below before a historical GUI/qualification rerun.

## Exact paths and evidence

- Expansion: `.project-local/staging/aaos-current-candidate-final-20260926/ArcheAxis.Knowledge.Green-vcurrent-2994efa-final-20260926-x64/`
- Archive: same parent, `ArcheAxis.Knowledge.Green-vcurrent-2994efa-final-20260926-x64.zip`
- Expansion: 18,247 files / 801,672,850 logical bytes
- ZIP: 18,247 members / 285,115,521 bytes
- ZIP SHA-256: `49AD275391B6B78DCB611F196A0DAF2FD3DCB1431D1CD6648ABD7025AD3BC471`
- Recheck: `.project-local/mig/current-candidate-dedupe-20260930/verification.json`; path/length/SHA all exact, `testzip()` returned no failing member, 0 extras, 0 reparse points.
- Candidate source identity, verification requirements, and runtime smoke remain as recorded in `docs/current/R6-EXECUTION.md` around the 2026-09-26 current candidate section. Storage equality does not extend that historical product qualification or prove current installed runtime health.

## Restore

Extract the ZIP into `.project-local/staging/aaos-current-candidate-final-20260926/`; the member paths already include the `ArcheAxis.Knowledge.Green-vcurrent-2994efa-final-20260926-x64/` top directory. Then rerun the candidate provenance/runtime check required by the dated R6 entry. This is a local recovery map, not a new candidate PASS.

No source data or application runtime was changed; no branch, commit, or push was created.
