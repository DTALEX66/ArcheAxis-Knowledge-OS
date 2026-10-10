# H01 独立来源追溯投影 · 2026-10-09

本文件及配套 JSON 是**派生来源追溯，不是 Authority，也不是第二进度数据库**。候选本地实源结构核验 PASS；H01 独立语义审查仍 **UNVERIFIED / PARTIAL**，产品实现资格 **UNKNOWN**。原包、历史原文与原状态不改写。

当前权威路由固定为 [活动指针](AAOS-ACTIVE-EXECUTION.json) → [新 UI 优先任务包](../taskpacks/aaos-ui-first-20261009/TASKPACK.md)。实际实施结果仍读取 [现有 UI 执行记录](AAOS-UI-FIRST-EXECUTION-20261009.md)；[G01 对齐记录](AAOS-GOVERNANCE-ALIGNMENT-20261009.md) 负责当前路由和消费者。旧 Q00–Q15 记录只承接对应继承流程，不成为整个新 UI 队列。这里不写完成百分比、运行状态或新的执行顺序。

[机器投影](AAOS-H01-SOURCE-TRACE-20261009.json) 包含426个唯一来源定位键：330条既有旧任务处置记录，及96条新原始矩阵要求。来源 namespace 保留，避免 Q00、T1 等重名。每条均保留已有承接任务、处置去向与理由；同时记录原来源文件 SHA-256 与原来源行规范 JSON SHA-256。旧270条原历史行逐字段与原台账对比；其原文件 SHA 单独保留。426不是新增产品任务数。

输入绑定来自不可变包的 OLD-TASK-DISPOSITION、REQUIREMENT-CROSSWALK、PAGE-PLAN、DESIGN-DETAIL-CROSSWALK 与 SOURCE-REGISTER。新96行还直接与登记的原始 CSV 对比，22页与实际 PAGE-PLAN 行及承接任务对比，186细项与原设计 JSON 文本、顺序及父 CAP 对比。原 crosswalk 中未绑定的能力细项/实施证据继续保留待核；目标任务存在不证明已经实现。

独立补齐六来源的实际读取 SHA 与登记值全部一致。原 DOCX 是629段的长期描述与蓝图整理稿，不替代仓库 Authority；P0028–P0031 声明来源解释顺序与完整性限制，P0039–P0042 说明普通内容先保存。97资产表含97个唯一 stable_id（85直接、12跨项目身份）。本轮只核实表格身份与来源导航，没有读完97份原件正文；不声称全账号、全历史或所有私有会话零遗漏。

六来源完整 SHA：

| 来源 | SHA-256 |
|---|---|
| 01_AAOS_完整项目描述与未来蓝图_20261006.docx | `2c99e7ae7dd52298ee425c8360c90b63a40d02f41af4c1b151cad6efd55d1ed9` |
| AAOS_SOURCE_BASELINE_97_2026-09-04.csv | `b278a5950e59bfc47bf924061f350c1bc061c56aeec8e94465cf3c423ba92e7f` |
| AAOS_完整历史规划蓝图吸收池与当前状态总报告_2026-09-29.md | `3839646bb60b811c5cc1ab3417625a69e71b70f5983b6b24ec796a664fa28ffb` |
| AAOS_完整执行任务包_20261004.md | `d6bb6432a6850dcf39c451b0a88e97ace668be040bbddf915e09f2b33b7ba1d9` |
| AAOS_快速重构与多格式闭环_完整方案_20261004.md | `7ecda3e3f9d22834d65df663ba4f42a3ac62e31d215ab5e7c59c08bfaf08441e` |
| AAOS_未来延展与可持续架构_完整方案_20261004.md | `771b189740e94dfeaf65e363b919745c2a69bb795d461e2b2fbcc9c95b15e1e1` |

186条设计原文全部保留为来源定位键，而不是擅自批准新的子能力 ID。对独立来源的词面匹配仅作为审阅信号：40条有精确文本匹配，146条没有精确文本匹配；前者不证明语义覆盖或实施，后者不证明来源遗漏。每条独立语义覆盖均 UNVERIFIED、实现资格均 UNKNOWN。UI 健康握手、父实现声明和历史 PASS 不能提升细项资格。

本地结构验收与待完成工作分开：

- 本地结构验收检查真实来源字节、行哈希、唯一性、96/22/270覆盖、186文本与顺序、承接任务及处置理由保全、97身份和六来源读取范围。缺失、越界、私人或 reparse 来源均不能写 PASS。
- 待完成语义审查需逐条核对独立有效来源的条款、适用范围、父/子能力及实际实现证据；未找到依据保留 UNVERIFIED，不能按相似名称或词面匹配猜测。
- 产品资格、原生桌面、真人学习、安装及云端发布均不由本投影验收。

本地核验入口：`python -B scripts/ci/check_h01_source_trace.py`。隔离评审可显式传入 `--repo <gov-ui checkout> --source-root <project owning root> --trace <scratch candidate JSON>`。回归 `tests/workflow/test_h01_source_trace.py` 使用实际登记 CSV/JSON/历史台账，不生成镜像 fixture 当独立来源；覆盖删源键、重复 namespace、伪哈希、错任务、漏页、漏细项、伪 PASS 和私人/越界路径。在缺少项目本地原来源字节的环境中，本地门禁应报告不可核实/FAIL，不把 required skip 当 PASS，也不自动恢复 V01 云 CI。

H01 独立读回证据保存在项目 owning root 下 `.project-local/runs/f714401b40/ui-learning-stage-20261009/governance-assessment/` 的 H01-ASSESSMENT.md、assessment.json 与 file-evidence.json，机器投影绑定其 SHA。这些是**本地 ignored 产物，未核实云端公开可用**；仓库文档中的路径只是本地证据定位，不是云端链接或已公开证明。当前 UI/G01 文档也只按本地读取记录，远端文件可用性未由此核验。

## 当前可见用户决定与未闭环事项

以下仅依据本聊天中用户明确发出的文字，不读取私人 native sessions，不声称更早未知对话完整。来源不是归档原件；这些稳定决定由活动指针与当前交接承接，不产生新的任务 ID。

| 可见决定 | 承接与边界 |
|---|---|
| 按照交接并行执行任务；目前没有其他 writer | 根 Agent 唯一 checkout writer；并行候选/只读验证隔离 |
| 新布局、架构及其他内容按新任务；原配色可转为主题 | 当前正式技术栈与新布局；blueprint/blueprint-light 配色值保留，black/white/cosmic 继续可选 |
| 统一配色主题下颜色要统一 | 全部页面使用选中主题的语义 token，验证主题内一致性 |
| 权威文档、索引、漂移引用和本地/云端描述先更新 | G01 本地对齐与云端文件同步分别记录；About 描述读回不代表代码已发布 |
| 优先 G01；任务以今天任务包为主并融合部分旧任务 | 新任务包为活动路由，旧来源保留去向与理由；原包不改写为当前进度 |
| 仍优先治理层和 UI 层面任务 | H01、UF05 及后续 UI 优先；V01 暂停、FT01–04 冻结 |

未闭环：云端文件同步/commit/push/PR 未获本轮明确授权；原生安装、物理 IME、人工试学和长期效果尚未验证；S01 物理处置未执行；186细项独立语义覆盖和97原件正文完整性继续 UNVERIFIED。以上缺口不提升历史 PASS，也不阻塞已知 UI 实现。
