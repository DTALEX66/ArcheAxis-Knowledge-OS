# 历史资料关键信息与合并归档登记

这些材料记录 2026-09-29/30 的历史构建、安装、UI 验收与恢复，不证明当前版本完成。原始 ZIP 全字节保存为项目内共享压缩片段，所有历史 README 继续保留原字节。

| 历史容器 | 文件项数 | 展开逻辑字节 | 原 ZIP 字节 |
| --- | ---: | ---: | ---: |
| AAOS-project-archives/2026-09-29/AAOS-Frontend-Acceptance-archive.zip | 697 | 654,827,163 | 229,477,326 |
| AAOS-project-archives/2026-09-29/AAOS-UI-HISTORY-76DIRS-20260929.zip | 14713 | 14,366,893,032 | 5,434,623,954 |
| AAOS-project-archives/2026-09-29/desktop-app-local-build-20260929.zip | 303 | 1,775,289,340 | 639,514,260 |
| AAOS-project-archives/2026-09-29/green-old-checkout-acceptance.zip | 889 | 3,410,535,157 | 1,248,479,583 |
| AAOS-project-archives/2026-09-29/green-old-checkout-build-output-20260929.zip | 437 | 1,415,586,378 | 522,265,850 |
| AAOS-project-archives/2026-09-29/green-ui-unreferenced-output-20260929.zip | 6341 | 12,293,102,376 | 4,324,551,549 |
| AAOS-project-archives/2026-09-30/formal-run-builds/frontend-responsive-desktop-build-absolute.zip | 229 | 219,127,815 | 76,522,014 |
| AAOS-project-archives/2026-09-30/formal-run-builds/frontend-responsive-desktop-build-railfix.zip | 229 | 219,127,883 | 76,522,155 |
| AAOS-project-archives/2026-09-30/formal-run-builds/r6-a12-build.zip | 79 | 591,288,191 | 190,562,228 |
| AAOS-project-archives/2026-09-30/formal-run-builds/ui-finalbuild3.zip | 249 | 222,330,884 | 79,944,989 |
| AAOS-project-archives/2026-09-30/green-mainline-historical-publish-20260930.zip | 450 | 454,415,128 | 170,123,195 |
| AAOS-project-archives/2026-09-30/historical-desktop-publish-22dirs-20260930.zip | 4984 | 4,798,503,361 | 1,659,496,511 |
| AAOS-project-archives/2026-09-30/nuget-http-cache-20260930.zip | 71 | 392,421,775 | 390,210,198 |

恢复要点：

- 合并包 `objects.pack`、`catalog.json` 与 `recipes/` 必须共同保留；仅重建到项目 `.project-local/restored/`，不操作正式数据库或已安装程序。
- `AAOS-UI-HISTORY-76DIRS` 与 `green-ui-unreferenced-output`：历史 UI 证据及未引用输出；可恢复历史材料，不构成当前 UI 验收。
- `historical-desktop-publish-22dirs`、`green-mainline-historical-publish`：历史桌面发布输出；不是当前发布或安装生命周期通过。
- `formal-run-builds`、`desktop-app-local-build`、旧 checkout 输出：历史构建与验收参考；保留恢复用途，默认不重新运行。
- `nuget-http-cache`：历史依赖缓存恢复档；与业务知识库分开，未作为产品运行数据。
- WER 报告保留两份历史启动崩溃证据；未查询 Windows 私人报告目录。
- 原来源 README 的完整原文与哈希见主索引，不格式化归档原文。
- 新 UI 四分包 155 项及补齐材料 18 项均为本次校验通过的新来源，不实施其内部执行指令。

量化结果：
- 历史 ZIP 15,042,293,812 → 1,911,212,397 字节，原ZIP SHA256全部匹配。
- 59,424 次片段引用 → 31,847 个唯一片段；仅相同 SHA256 压缩字节共享。
- 额外复用 5 项本项目已有文件，原有冻结副本保持不动。
