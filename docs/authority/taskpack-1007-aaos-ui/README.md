# AAOS UI 任务包（2026-10-07）归档

Owner 提供的输入包，是当前 UI 车道执行与验收的权威任务文本。原始包只在被 Git 忽略的
`.project-local/inputs/` 下存在，干净检出读不到自己的计划，因此把任务文本原样入库。

- 入库范围：`CODEX_START_HERE.md` 与 `docs/01…12`，字节未改写，哈希见 `ARCHIVE-MANIFEST.json`。
- 不入库范围：包内 `evidence/` 是**本仓库自身权威文档的副本**，重复入库会造成同一文件两个权威；
  `assets/donors/` 属冻结供体材料，按本项目规则不再吸收。两者只登记哈希。
- 进度与证据不在本目录：一律记在 `docs/current/AAOS01-Q00-Q15-LEDGER-FINAL-20261005.md`。
- 命名提醒：包内 `U01…U12` 是 UI 任务编号，与 `docs/history/.../requirements_trace.json` 里另一族
  `U01…U12` 不是同一套；`F10/F11` 在本包指说话人分离与视频覆盖，与
  `docs/current/AAOS-COVERAGE-MATRIX-20261006.md` 的未来能力 `F00—F14` 也**不是同一族**。
