# 首版收敛、能力启动台与视觉纠偏归档 · 2026-10-22

本归档覆盖本线程从桌面化／小栖调研讨论、核心收敛、两份历史文档复核、前后端规划，到生成概念图、Owner确认菜单窗口及后继玻璃／图标纠偏的可见讨论。它是脱敏来源归档，不是私人Codex会话导出，也不覆盖本线程更早全部执行历史。

- [对话摘录与决定映射](SOURCE-EXCERPTS.md)：用户明确决定、提问、助手建议及否定反馈分开。
- [设计候选与静态核查](DESIGN.md)：玻璃根因、标准库比较、候选规格及Stitch调用边界。
- [原件及冻结成员清单](MANIFEST.json)：五份文档、两张用户参考图的项目本地保全路径、长度、SHA-256；概念图及公开派生材料的冻结哈希。
- [启动台概念图](concept-desktop-launcher.png)：仅布局参考；图标已被Owner否定，不能作为整体视觉批准或实现证据。

规范只维护在[当前决定十九／二十节](../../current/AAOS-OSS-INTEGRATION-DECISION-20261019.md#十九首个可用版本核心收敛与能力启动台2026-10-22)及[唯一闭环定义](../../truth/CLOSED_LOOP_DEFINITION.md)。接续读[活动指针](../../current/AAOS-ACTIVE-EXECUTION.json)和[交接](../../current/AAOS-AGENT-HANDOFF-CURRENT.md)，实际进度仍只有[原执行记录](../../current/AAOS-UI-FIRST-EXECUTION-20261009.md)。

## 本轮确认与尚未确认

已确认：快速形成可实际使用的常用多格式→研究比较→知识→特色展示／学习主链；核心收敛、专用能力模块化；在现有Stitch中增加能力启动台、收敛Dock与重复导航；其他开源池和复杂能力延后；修正玻璃不足，标准库图标替代生成图标。

尚未逐项核定：首版所有格式／编码／语言、软件版本／特色／方向、Dock精确排列、图标库版本、最终透明度／模糊参数和新Stitch设计稿。建议不能写成这些事项已获逐项批准。原生／模型失败和安装／Owner验收缺口没有因本次归档消失。

当前仅归档、权威更新与定向设计核查；产品 `PAUSED_BY_OWNER / PARTIAL`，监控继续暂停。没有修改产品CSS／TSX、安装依赖、调用模型或启动验收长链。历史文档提示词不是当前执行指令。生成图与来源示例数据均不是产品真实业务证据。

## 附件保全与可移植边界

五份Markdown与两张用户参考图按原字节复制到项目被忽略的 `.project-local/archives/owner-dialogue-20261022-desktop-launcher/`；源文件不修改、不删除。概念图是本线程生成的设计产物，作为公开项目设计参考归档；其图标否定状态随本README和清单一起保留。无需把私人原生会话、运行数据库、凭据或原始讨论全文上传。

Git克隆只保证公开成员；ignored原件须由持有者按manifest核验，不宣称已云端备份。公开文件中的哈希只证明归档字节一致，不证明调研报告的技术或产品完成声明正确。

可在仓库根运行 `pwsh -NoProfile -File docs/history/owner-dialogue-20261022-desktop-launcher/verify_archive.ps1`；默认核公开冻结成员及JSON结构。加 `-IncludeLocalSources` 核本机原件副本。该校验不运行产品、不访问附件原路径或私人会话。
