# Teaching 计划修订：有限后端 RED → GREEN

本记录封存 R6 E01/E03/E07/E08 与 R5 C1-01/C1-04 的一个后端切片：没有外部工具、尚无 Delivery/Feedback 或成果时，现有 Teaching Proposal 可以追加 Revision，再追加 Revision。复用原 Core、API、SQLite 写入者及枚举；不创建第二任务队列。

## 实际变更与边界

`parent_shape` 将 Revision 的父类型从仅 Feedback 扩为 Proposal / Revision / Feedback。已有明确 Revision 的 knowledge/course 变更规则保持，普通保存无需联网。记录仍 append-only、not_scored；这不是专门外部实践状态机的完整实现。新增 API 合同覆盖连续修订、幂等、冲突、重启、撤回和保留历史。

完整 R6 UI、IME/原生宿主、教程打开/替换/跳过交互、真实 Course 旅程、start/self-report 的产品状态和独立 mastery 评估均未验。教程文字只是惰性合成内容，不等于执行教程流程。模型调用 0，外部实践工具调用 0；未造 Delivery/Feedback，也不把保存或自述计为掌握。F05 真实模型失败和整体 PARTIAL 不因此改变。

## 同身份反例与后继

- 固定 knowledge：`k_7cfbd0a645948ed7d0087cfd`。
- 固定 proposal content SHA-256：`5c4bdac5d00efcd81055ae3f3dd269c7e3fbba64bcb5665d30c9a73bb72f20ae`。
- RED `bkr-r6plan1`：Proposal 后直接 Revision HTTP 422，错误 `parent kind does not follow teaching lineage`。原计划保存、幂等及重启保全正常。其 probe/wrapper 0 表示成功证实缺口，不是产品通过。
- GREEN `bkr-r6green1`：相同首次 Revision HTTP 201，后续 Revision HTTP 201；同 ID 改文 409，精确重试 200；重启后逐项保全。撤回影响原计划及两次修订，晚到子项 409，原正文和 SHA 保持。没有虚构已完成的实践。

## 源码与实际执行

HEAD `f5d8b570409ba6b0a1915fa7ab336c4be1879485`。RED 源为 clean；GREEN、两套测试和构建为稳定 dirty=true，patch SHA-256 `2ce0aa81962609e0f867975c18db68f68b134b47d17d8b9005dbd351fe97e55c`。该 patch 同时含独立 backup probe 修复；Teaching 资格不代替 backup 验证。文件 SHA、命令、全部本地收据 SHA 见 MANIFEST.json。五个 run 均 source_consistent=true、actual/wrapper 0。

- `bkr-r6api1`：`cargo test --locked --offline -p archeaxis-api --test teaching_state_api`，8/8。
- `bkr-r6dom1`：`cargo test --locked --offline -p archeaxis-domain --test teaching_records`，19/19。
- `bkr-r6build1`：`cargo build --locked --offline -p archeaxis-api --bin archeaxis-api`，实际构建退出 0，复用共享 target。
- `bkr-r6green1`：构建所得 Core 的真实 HTTP、真实 Store 和合成知识/Teaching 请求，实际 probe 0；没有模型请求。

GREEN Core：`6b503641cb971ddc0135f79237e036c138cae0db8986cd3510ccefa06b75de6d`，27,844,096 B。唯一 run 内保全副本为 `.project-local/runs/be268a2d33/bkr-r6green1/artifacts/practice-runtime/core/archeaxis-api.exe`；不再覆写该副本。共享 Cargo `debug/archeaxis-api.exe` 可随后继构建变化，不能代替这个同 SHA 保全来源。RED 使用既有 bfea 当前源构建的旧二进制 SHA `d8352b9de954cb32a70a26b234c01de45be7b58424b6fcaaa1d48d145cf350be`；当时至 f5d8 的相关产品源无变更，不能将旧二进制描述为本次重新构建。

构建阶段共享 target logical bytes 7,605,359,513 → 7,605,359,513；仅 `debug/archeaxis-api.d` mtime 变化，长度仍 9,799 B。此基线在两套测试之后，不能据此声称测试编译无缓存增长；物理分配/去重未测。

RED 自有 PID 38048/40380，端口 52262/52285；GREEN 自有 PID 32552/32876，端口 51072/51092。均已 terminate/reap，进程 exit 1、端口关闭；不声称优雅退出。仅清理本次拥有的进程。

这是历史有限资格记录，当前状态仅导航 [唯一执行记录](../../current/AAOS-UI-FIRST-EXECUTION-20261009.md)；不替代活动指针或扩大授权。
