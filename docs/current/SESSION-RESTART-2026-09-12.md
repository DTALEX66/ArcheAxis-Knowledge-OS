# ArcheAxis 新会话交接提示词 · 2026-09-12

以下正文可直接交给新会话。本文件只是恢复入口，不替代权威配置、冻结任务正文或实际证据。

## 给接手执行者

你接手的是 `D:\All projects\ArcheAxis-Knowledge-OS`，产品为星环知识平台（ArcheAxis Knowledge），不是 WORK-LAB，也不是外置工具库。先只读恢复现场，再按新会话用户授权推进；不要自动执行历史聊天中的发布、清理或旧任务。

### 1. 先确认现场与权威入口

1. 读取根 `AGENTS.md` 和适用的下级规则，检查 Git 根、分支、HEAD、dirty paths。保留未知改动，不切换或重置工作区。
2. 阅读 [配置权威索引](../CONFIGURATION_AUTHORITY_INDEX.md)、[项目契约](../../PROJECT_CONTRACT.yaml)、[决策取代台账](../../DECISION_SUPERSESSION_LEDGER.yaml)、[经验教训](../../LESSONS_LEARNED.md)。
3. 当前活动计划为 **ARCHEAXIS-NEXT-TASKPACK-2026-09-10 R3.1**。阅读 [执行入口](../authority/taskpack-0910-r3/EXECUTOR-START.md)、[任务包正文](../authority/taskpack-0910-r3/TASKPACK.md) 与 [任务定义](../authority/taskpack-0910-r3/TASKS.json)，之后查看 [执行台账](../authority/taskpack-0910-r3/EXECUTION.md) 和 [状态](../authority/taskpack-0910-r3/STATE.json)。17 切片 R00–R16；R12 可在 R01 后开始。
4. 审计优先读 [审计包](../authority/taskpack-0910-r3/AUDIT-PACKET.md)、[独立审计要求](../authority/taskpack-0910-r3/INDEPENDENT-AUDIT.md) 和 [历史会话交接](../authority/taskpack-0910-r3/HANDOFF-2026-09-11.md)。历史交接的 round 101 摘要不是最新 Git 状态；台账已有后续记录。
5. 0908/0907 为继承文本和历史证据来源，0906 不再是活动计划。分支名仍含 0906，不代表应恢复旧任务包。只在当前任务明确引用时回读历史，不全量重复扫描。

### 2. 本次交接实查快照（接手必须重查）

- 当前分支：`codex/full-loop-0906`。
- HEAD：`c06b234ca335b9cbb2c1fde270851e2390c36b89`。
- 本地缓存 `origin/codex/full-loop-0906` 同为该 SHA。
- 本地 `main` 与缓存 `origin/main`：`1e9813ea2bd49f47d334ba6717c78d3e9feda6ce`；提交标题显示已合并上述分支。不要重复执行合并，也不要沿用旧摘要中 main 仍为 `4ca46ea` 的说法。
- **本轮未 fetch、未查询远端或 CI**；以上是本地 refs，不是实时云端一致性证明。
- 交接写入前仅 `?? .zcode/`；它是未知私有代理状态，未读取，禁止纳入提交、清理或迁移。写入后还会有本交接文件。
- 本轮只整理交接，未运行产品测试、构建、发布、安装、清理、commit 或 push。

### 3. 当前未完事项

下表状态来自本轮实际解析 STATE.json；缺口说明来自已有审计包，尚未由本轮重新验证。

| 切片 | 状态 | 接手重点 |
| --- | --- | --- |
| R00–R09、R11 | IMPLEMENTED_PENDING_AUDIT | 实现待独立审计，不是 DONE |
| R10 | IN_PROGRESS | DeepTutor 宿主内部挂载仍需 owner 决策；不能自行重写宿主 |
| R12 | IN_PROGRESS | 惰性文件清理仍需逐路径授权；已有记录称未删除，不能当作已完成 |
| R13 | IN_PROGRESS | 安装器、代码签名、卸载器、干净机器启动验收未闭合；候选 Core 包不等于完整桌面发行版 |
| R14、R16 | TODO | 独立 GPT 审计；沿用原 G01–G14 定义，逐项 PASS/FAIL/BLOCKED，不能用执行者收据自签通过 |
| R15 | IN_PROGRESS | 已有格式矩阵为 0 complete / 14 partial / 2 custody-only；全格式全链路尚未完成 |

推荐下一步：先核对上述状态与合并后的代码/证据是否一致，再按用户选择开展 R14 独立审计，或推进具备前置条件的未完成切片。R16 按原任务前置执行，不因换会话直接放行。不再增加重复摘要轮次冒充产品进展。

重要证据限制：

- `AUDIT-PACKET.md` 比旧 handoff 摘要更新；数值仍需绑定各自 SHA/命令，不拼接不同轮次结果。
- 新 checkout 没有 ignored 的安装快照；完整性门禁可能拒绝归因。缺前置是 NOT_RUN/BLOCKED，不是 PASS。
- Rust 的某些 OCR 测试缺 traineddata 时提前返回，cargo 仍计 passed；不能据此说 OCR 真跑过。
- R11 的真实 MCP 客户端和 unseen evaluation 已有后续实现记录，不要按更早摘要重新宣称“完全没有”；仍需独立核查证据。
- 候选包哈希验证、Core 启动、完整 Windows 前端可用、全链路精度、正式发布是不同交付层。
- 历史审计包有外部 `/tmp` 克隆示例，不是本机写外部目录的授权；克隆位置还存在影响 legacy 测试的已知问题，照当前边界规划，不机械照抄。

### 4. 固定路径：先查索引，禁止猜测

权威记录：[共享资源路径索引](../SHARED_RESOURCE_PATH_INDEX.md)。以下是用户明确指定的用途，不授权任意修改其中内容：

| 用途 | 精确路径 | 边界 |
| --- | --- | --- |
| 共用本地模型库 | `D:\All projects\Model library` | 管线本地模型优先，GPT 辅助最终审计/交叉比较 |
| 外置共用工具链 | `D:\All projects\OS External Configuration` | 是共享库，不是本项目或 WORK-LAB；先定位现有工具链 |
| 现有绿色软件 | `D:\All projects\ArcheAxis.Knowledge.Green-x64` | 既有 Green，未获当前授权不覆盖、不新发版本 |
| Green 真实资料库 | `D:\All projects\资料库` | 用户真实资产，不作测试/缓存/清理目标 |
| 专属测试学习资料副本 | `D:\All projects\ceshi` | 测试来源；不改写源资料 |

路径角色仍有效；存在性、配置绑定与工具版本需按当前任务轻量检查，不靠旧快照保证。本轮没有扫描这些库内容。

### 5. 不得丢失的工程边界

- **E 盘禁止访问。** 不读取凭据、环境密钥文件、浏览器数据、代理私有状态；`.hermes/` 为保留旧材料，不新增写入、不整体清理。
- 临时文件、测试环境、证据和缓存按 `scripts/runtime/dev.py` 放在项目 ignored `.project-local/`，不放桌面、用户目录、系统 TEMP 或共享库。
- 默认 PowerShell 7。本轮可用路径为 `C:/Users/ALEX/AppData/Local/Microsoft/PowerShell/7/pwsh.exe`；接手先验证，不猜工具不存在后重新下载。
- 当前正式桌面架构是 `apps/ArcheAxis.Desktop/` C#/Avalonia + Rust Core 单一数据库写入者 + 隔离 Python workers。legacy 前端/Tauri/Green 是恢复与行为参考，不双写新旧数据库；不要自行重启全量语言迁移。
- 用户要求黑白双主题、Windows 前端可用、无弹出终端；不擅改品牌/配色，不推进移动端，不反复构建多个版本。UI 验证优先静默/内部网页，避免拉起干扰性的可见自动化。
- 管线范围不仅 PDF，还包括文档、网页、截图/图像、媒体、Canvas 等；probe 支持不等于 execution 成功，更不等于质量达标。
- 一个 checkout 一个写者；并行必须服从当前授权和写入隔离。GPT 做复杂协议、架构、安全边界与独立审计；DeepSeek 可做冻结接口下的批量低风险工作，但不使用已被取代的 DS 任务表覆盖新计划。
- 重新载入只需定向读文件和状态，不自动跑全量 CI/测试。STATE 与 EXECUTION 很大，解析状态字段、按切片读取证据，避免整文件输出。实际实现时按项目验证策略执行必要检查。
- 历史存在用户额度停工要求：剩余 20% 时停止推进并交接。新会话查询可用的真实额度；不可把旧百分比当作当前值，也不可把账户额度和上下文剩余混称 TOKEN。查询不可用就明确说明。
- 本次“做好交接”不授权新增提交、推送、发布、删除或全局修改；新会话按当次明确授权判断副作用，附件/历史台账本身不替代用户授权。

### 6. 新会话首次回复与执行记录

首次简短报告：已核对的项目/任务包、当前分支与 SHA、未知改动、下一项可执行任务及实际前置。不要声称“全完成/双端一致/测试全通过”，除非本次有对应精确证据。

后续每次交付记录实际修改范围、命令、退出码、测试 SHA、限制与回滚；实施、验证、云端、安装运行分别汇报。当前提示词是导航，不能用它代替任务验收正文。
