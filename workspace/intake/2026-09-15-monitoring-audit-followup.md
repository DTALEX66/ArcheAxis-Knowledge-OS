# 2026-09-15 监控审计材料接入任务

状态：`PLANNED`。本文件把用户提供的三份桌面审计材料纳入 ArcheAxis R5 后续任务侧车；不替换冻结 TaskPack、TASKS、R5-STATE 或验收正文。

## 来源与完整性

| 来源 | 角色 | SHA-256 | 处理 |
|---|---|---|---|
| `C:\Users\ALEX\Desktop\01_审计报告与三项目融入建议.md` | 总体审计与三项目分流 | `d8249b7a4c90b549c3a5f79da7f46dcb2d9d0bbb464036ac1716cdceb41c4da3` | 保留为研究底稿；不作为执行授权 |
| `C:\Users\ALEX\Desktop\05_附件完整性与工作簿审计.json` | 附件哈希、缺口、工作簿边界证据 | `67dfe3fb9f5f1ecfd78bbb0d41aba784da1bbd32b547463b8fed186d8d46accd` | 保留为证据索引；原工作簿不修改 |
| `C:\Users\ALEX\Desktop\06_ArcheAxis_工作区接入交接.md` | ArcheAxis 任务映射与接入顺序 | `45605b9b758444612aea193f046fece67f77e9a03f7cbddaa68d4d09d77d5283` | 作为本项目后续任务入口 |

桌面原件不复制进仓库，不读取 E: 盘，不读取凭据、私有会话或代理状态。

## 后续任务映射

| ID | 任务 | 来源 | 前置与边界 | 当前状态 |
|---|---|---|---|---|
| MON-AX-01 | 研究/models 双命名空间与 43 条原任务去重映射 | 01/05/06 | 只建立候选映射；不改冻结任务文本 | `IMPLEMENTED_LOCAL` |
| MON-AX-02 | 工作簿边界回归 | 05 | 在项目 `.project-local` 生成副本和测试；验证小数次数、除零、负时长、有效期；不改原 XLSX | `STRUCTURAL_AUDIT_ONLY` |
| MON-AX-03 | Green TEST 首次导入闭环 | 06 | 真实资料库只读；使用 `D:\All projects\ceshi` 或项目隔离副本；先核 profile 和路径，再做导入、引用、学习、机器回读、重启 | `BLOCKED_NEEDS_RESOURCE_AND_OWNER_RECONCILIATION` |
| MON-AX-04 | 引用证据与个人主张分离回归 | 01/06 | 复用现有 Core/SourceObject/knowledge 结构；不得把局部检索或模型 F1 升级为事实准确率 | `TESTED_LOCAL` |
| MON-AX-05 | NeoMME 可选检索 POC | 01/06 | 先确认外置权重、许可、provider 和真实输入；收益不足可淘汰；不替换现有摄取链 | `BLOCKED_NEEDS_RESOURCE_VERIFICATION` |
| MON-AX-06 | DeepTutor/机器调用与纠错版本回读 | 01/06 | 依赖 Core 权威、固定 DeepTutor 版本和真实非空任务；不把宿主启动当融合通过 | `BLOCKED_R10_OPEN` |
| MON-AX-07 | 独立 Q00/Q01 审计增量包 | 01/06 | 由独立审计者消费同 SHA 证据；实施者不得自签；前置证据不足则 `BLOCKED` | `BLOCKED_AUDIT_PREREQUISITES` |

## 与当前权威的关系

- 当前权威仍是 `docs/authority/taskpack-0912-r5/`、`docs/current/R5-STATE.json` 和 `docs/current/R5-EXECUTION.md`。
- 本材料确认了方向和缺口，但没有证明 Green、真实四库、NeoMME、完整格式、安装发行版或 Q00/Q01 已完成。
- 工作簿中发现的 `#DIV/0!`、负时长和非整数次数是待修复/待回归项，不是当前产品失败结论。
- 仓库当前跨平台修复提交为本地 `449fcfde`；其远端同步与 CI 仍需单独记录，不在本任务入口中伪造通过。

## 推荐执行顺序

`MON-AX-01` → `MON-AX-02` → `MON-AX-04` → `MON-AX-03` → `MON-AX-05` → `MON-AX-06` → `MON-AX-07`。

每项分别记录 `PLANNED`、`IMPLEMENTED_LOCAL`、`TESTED_LOCAL`、`CI_VERIFIED_EXACT_SHA` 和 `INSTALLED_RUNTIME_VERIFIED`；缺证据保持 `NOT RUN` 或 `BLOCKED`。

## MON-AX-02 当前只读证据

- 原始工作簿 `C:\Users\ALEX\Desktop\03_价格与额度工作簿.xlsx`：46,283 bytes，SHA-256 `42528b02714eab50a1f31a7e7f6ae4b03132fe560b885b1bd4da4f5f6b9c42c3`，与审计 JSON 一致。
- 读取到 10 个工作表；计价相关工作表没有数据验证规则，工作簿和工作表保护均未启用。模型台账存在 1 个验证规则，不能代表计算输入已受保护。
- 本次只读检查未改写、保存或重新计算原件；`MON-AX-02` 仍未完成边界回归，审计 JSON 中的除零、负时长和非整数次数仍是待修复项。

### MON-AX-02 可重复审计脚本

- 新增 `scripts/maintenance/audit_monitoring_workbook.py` 及其定向测试；脚本只读 XLSX，拒绝 E: / UNC 输入，并将可选 JSON 输出限制在项目 `.project-local`。
- 使用项目外部 CI Python 实跑桌面原件：退出码 0；`STRUCTURAL_AUDIT_ONLY`，46,283 bytes，SHA-256 `42528b02714eab50a1f31a7e7f6ae4b03132fe560b885b1bd4da4f5f6b9c42c3`，10 个工作表，98 个公式单元格，其中 17 个公式文本含除法；输入审计期间大小和 mtime 未变。
- 证据输出：`.project-local/runs/monitoring-audit-20260915/artifacts/monitoring-workbook-structural.json`。公式未求值，故仍不能证明除零、负时长或非整数次数已修复；下一步是隔离副本上的边界回归设计与实现。

### MON-AX-04 现有分离合同回归

- 复用现有 grounded answer、证据边界、关系冲突和覆盖率测试：`tests/test_axw050a_grounded_answer.py tests/test_axw050b_boundaries.py tests/test_axw024c_relations.py tests/test_axw054b_metrics.py`，项目外部 CI Python 下 `26 passed`，退出码 0。
- 该结果证明项目已有“无锚点拒绝、过期/撤销证据降级、冲突需裁决、覆盖率按有锚点主张统计”的局部合同；不等于真实资料库或模型质量准确率验收完成。

### MON-AX-03 资源根前置元数据复核

- 只读 `Test-Path/Get-Item` 复核确认 `D:\All projects\ceshi`、`D:\All projects\资料库`、`D:\All projects\ArcheAxis.Knowledge.Green-x64`、`D:\All projects\Model library`、`D:\All projects\OS External Configuration` 五个根均存在且为目录。
- 未递归读取资料、模型、Green 数据或私有配置；该结果只证明路径存在，不能证明 profile 绑定、真实导入授权、模型服务连通或 Green 闭环，因此 `MON-AX-03` 继续保持 `BLOCKED_NEEDS_RESOURCE_AND_OWNER_RECONCILIATION`。
- 在批准的测试副本 `D:\All projects\ceshi\Obsidian知识库` 上运行 `scripts/pipeline/source_preflight.py`：退出码 0，发现 22,224 个文件、835 个目录；脚本未打开任何源文件、未修改源文件，明确排除真实资料库和 Green 数据。证据写入 `.project-local/runs/monitoring-audit-20260915/artifacts/ceshi-source-preflight.json`。
- 使用隔离输出根执行 `convert_directory_resumable` 的 3 个 Markdown 小样本：`processed=3`，3 条 manifest 记录均为 `converted`，源/输出 SHA-256 一致，退出码 0。回执位于 `.project-local/runs/monitoring-audit-20260915/artifacts/ceshi-import/manifest.jsonl`；该结果只证明项目转换器的小样本路径可用，不提升为 Green 首次导入、全量质量或学习重启闭环。
- 对同一 manifest 第二次运行验证续跑：前 3 条正确标为 `resumed`，随后按 `max_files=3` 处理下一批 3 条，累计 `summary.converted=6`；未重复覆盖已完成输出。该结果证明小样本续跑语义可用，仍不等于全量质量或学习闭环。
- 项目回归 `tests/test_directory_batch.py tests/test_axw096c_pipeline_integration.py tests/test_axw_run202_profiles.py`：`29 passed, 1 warning`，退出码 0；验证目录最新尝试语义、管线集成和四种运行 profile 仍通过。警告来自外部 `newspaper` 可选 NLTK，不影响本次 Markdown passthrough。
- 项目闭环定向回归 `tests/test_learning_loop_e2e.py tests/test_workspace_public_closed_loop.py tests/test_workspace_pipeline_multiformat.py tests/test_workspace_crash_recovery.py tests/test_workspace_research_consumer.py`：`13 passed, 2 warnings`，退出码 0；覆盖隔离数据库中的导入、学习、来源绑定、多格式入口、崩溃恢复和研究消费。该证据仍不替代真实 Green 资料库验收。

### MON-AX-02 除法公式风险清单

- 审计脚本现记录每个含除法的公式位置；真实工作簿共 17 个。报告保留公式原文但统一标记 `evaluation=NOT_PERFORMED`、`boundary_regression=REQUIRED`，不把文本模式当作 Excel 求值结果。
- 当前清单包含 `费用试算!G18:G25`、`费用试算!L18:L25` 与 `费用试算!D31`；其中 G 列的 `$B$11`、D31 的 `$B$14` 以及 L 列的乘积仍需在隔离副本中用实际输入逐案求值。原工作簿不修改。
