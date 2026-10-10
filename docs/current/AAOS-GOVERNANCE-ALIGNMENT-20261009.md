# G01 权威、引用与仓库描述对齐 · 2026-10-09

> **2026-10-10 当前路由与状态**：产品执行 PAUSED_BY_OWNER，整体 PARTIAL；当前请求仅授权归档和权威/引用治理修复。旧“下一队列/未发布/两树不同”属于历史日期快照；上次源码已发布，本轮最新状态读 [修复回读](AAOS-AUTHORITY-REPAIR-20261010.md)。读取任何旧路径前先按 [路径身份路由](AAOS-AUTHORITY-ROUTES.json) 分类，不从文件名CURRENT、旧COMPLETE或旧grant推导授权。六项核心能力增量 FROZEN_BY_OWNER，不自动排队；V01暂停、FT01–04冻结。

本文件记录用户当前明确选中的 G01，范围是新任务包的活动路由、规则/索引/context 消费者、仓库说明及有限反漂移门禁。不是新的产品能力总账，不授予发布、安装、清理或 V01 权限。执行状态以本轮核验回执为准；文档对齐不代表新 UI 已获原生或云端资格。

## 单一活动路由

规范机器入口为 [AAOS-ACTIVE-EXECUTION.json](AAOS-ACTIVE-EXECUTION.json)。当前选择 `docs/taskpacks/aaos-ui-first-20261009/`（AAOS-UI-FIRST-PLAN-20261009）；UI 实施进度为 [UI 执行记录](AAOS-UI-FIRST-EXECUTION-20261009.md)。用户当前补充的新布局、默认新配色、旧配色主题化及同主题颜色统一均明确承接。

AAOS-01 的 Q00–Q15 台账只保留原 Q 合同和范围；R6/M0、旧任务书、旧审计和 dated handoff 均不能重新成为整包自动队列。原始任务包、FREEZE-REGISTER、330 行处置、96 项需求与186设计细项不改写、重编号或回填 PASS。TASKS.json 的 PLANNING_READY/NOT_EXECUTED 是包建立时状态，当前选择/授权在活动路由，实际结果在实施记录。G01 本次已明确选中；其原规划 activation 不回填。

## 两个本地检出与云端

资料/治理主检出 `D:/All projects/ArcheAxis-Knowledge-OS`：`codex/Audit`，本次起始 HEAD `1a981a4482b01f31989074e79c82a63400aa07a7`。代码 writer `.project-local/worktrees/gov-ui-20261008`：`codex/aaos-gov-ui-20261008`，起始 HEAD `fc5d4adc7acc28e38c2e6046ef06c0be2eed721d`。此前主根 R6/Avalonia 文档已过期。本次只同步经审的治理/索引/必要继承文档，保护主根未知文件和两树 dirty；不能将治理同步当作源码合并或 main 产品升级。接手始终重读 HEAD/status，不直接使用本页快照。

GitHub 仓库 `DTALEX66/ArcheAxis-Knowledge-OS` 默认分支 main，本次只读回 HEAD `4b9828c4058901c0b1fd2c75c528238c55e0ec89`，原 README/AGENTS/AUTHORITY 仍指向 AAOS-01，活动路由文件在云端尚不存在。

**已执行远程操作**：按用户“云端仓库描述更新”请求，仅更新 GitHub About。读回描述与拟定文本一致；表述新 UI 优先、Tauri/React/Rust 单写者、内容保存政策和分层验收，不使用“当前可用”暗示安装资格。回读见本项目 `.project-local/runs/f714401b40/ui-governance-20261009/artifacts/cloud-description-readback.json`。

**尚未执行**：云端文件 commit/push/PR/merge 与 CI。GitHub About 更新不使远程 README/规则自动同步，不等同 BRANCH_PUBLISHED、MERGED_MAIN 或 CI_VERIFIED_EXACT_SHA。待发布文档需精确 write-set 与单独提交/推送授权；本地大量未提交代码不能混入治理提交。云端审计当前 main 时仍须明确“未包含本地 UI/G01 增量”，不能审计不存在的代码或将本地路径当云端证据。

## 当前消费者与历史处理

根 AGENTS、AUTHORITY、README、PROJECT_CONTRACT，以及文档/配置/语言/目录/运行交付索引、docs/README、Truth/TaskPack 导航、当前架构、验证政策、UI 路线图与 UI_CONTRACT_V2 消费活动路由。产品命名、Rust/Core 单写者、独立 Python worker、普通内容保存和长期能力保留不改变。

旧 B10/Aurora/双主题视觉路线保留为历史输入；不覆盖新 UI 布局或新 token。旧云端审计和交接保持原日期、正文、PASS/FAIL、SHA及原权限范围，统一索引将其标为 dated non-authority。`docs/authority/AGENTS.vnext-governance.md` 属保留治理参考，其旧受保护 grant 程序不自动成为当前 UI 前置；全局/私人 Agent 配置和其他仓规则未修改。

原始规划 SOURCE-REGISTER 继续绑定规划时字节。它的“现场不变”校验在真实实现后存在预期差异，不能重写快照让旧校验假绿；本次记录新 before/after，而不是变更历史 SHA。源 ZIP/成员、任务包正文及交叉映射的完整性另行核对。外部/private locator 的存在与内容不由文档门禁读取，标 UNVERIFIED。

## 验证与回退

使用现有 document-authority/path-conventions/project-contract/文档链接与 UI 声明门禁，补“旧包误称当前、新包/当前进度冲突、路径逃逸/私人 locator、缺引用”等反例。门禁只检验结构、身份和路径，不宣称产品完成。V01 继续暂停，未修改 workflow、触发 cloud CI 或运行安装。

完整命令、结果、源码指纹、精确变更及同步回执保存于本项目 `.project-local/runs/f714401b40/ui-governance-20261009/`。任何 FAIL、未执行或缺资料均保留，不合并成 PASS。before 备份与同步 manifest 支持逐文件/hunk 回退；不可 reset/clean 或覆盖未知 dirty。GitHub About 可按云端 before 回读恢复原描述；这不授予文件回写或历史改写权限。

## 本轮验证回读

- 定向治理测试：67 PASS，canonical run `ui-governance-writer-tests`，执行期间源码一致。
- 当前文档链接：代码 writer 315 条、主检出 313 条，缺失 0；主检出没有的新业务桥/打包脚本明确 NOT_AVAILABLE，未复制产品代码伪装为同一源码。
- document-authority：两检出 PASS；外部/private 原始 locator 不读取，4 项 UNVERIFIED；主检出缺失的 25 项历史 Q 测试引用保持 UNVERIFIED。
- 不可变规划校验：31 项中 29 PASS，`root_handoff_exact_mirror` 与 `protected_source_snapshot_unchanged` FAIL。根交接新增当前路由、源码进入实施导致字节不同；保留原任务包及 SOURCE-REGISTER，不回填规划 PASS。整体规划检查为 FAIL，不能当成实现或产品门禁 PASS。
- 全仓 worktree conventions 初检 FAIL 25 项：本轮 15 个文件的 CRLF 已改为 LF；其余既有 UI/浏览器文件格式与 README 历史命名另记，不扩大 G01 写集合修复。最终范围检查与全仓残留另见本轮 final-readback.json。
- 云端文件发布、exact-SHA CI、原生 UI/IME、安装与 V01 均 NOT_EXECUTED。GitHub About 单独读回 PASS。

## G01 优先收尾验收 · 2026-10-09

用户再次明确优先 G01；活动指针已登记 `priority_tasks=[G01]` 和任务包原有 `FREEZE-REGISTER.md`。不恢复 V01，也不扩大已选任务或远程权限。

| G01 原包验收 | 本地结果 | 当前证据 |
| --- | --- | --- |
| 旧冻结任务不再自动重复执行，仍可检索和恢复 | PASS | 原登记与原任务文件保持原位；活动路由仅选新 UI 包，旧 R6/M0/Q 仅按继承范围解析；优先任务必须已选中且不能处于 paused |
| 当前入口无正式 Avalonia 误导 | PASS | 根 Authority/AGENTS、架构、索引和 UI 合同均指向 Tauri/React；Avalonia 明确为冻结供体 |
| 历史 PASS/FAIL 不改写，不通过移动目录伪装完成 | PASS | 原 TaskPack/历史状态/日期 SHA 保留；旧规划现场校验差异仍保留为 FAIL；未移动或删除旧材料 |

G01 **本地实现与定向验收 PASS / 证据级别 INTEGRATED（文档消费者与实际文件门禁，不代表产品运行资格）**。canonical run `g01-priority-tests`：70 PASS、source_consistent=true；两检出的 document-authority、24 个治理变更路径 conventions、diff --check 均 PASS。新增回归证明：冻结登记缺失会失败、暂停任务进入优先队列会失败、未选中任务不能进入优先队列。README 历史命名上下文已修正；其他既有 UI 格式问题保留在原全仓结果，不列为 G01 PASS。

最新 before/after、验收与范围回执在 `.project-local/runs/f714401b40/g01-priority-closeout-20261009/`；此前 67 项结果保留其阶段，不改写为 70。云端 About 已读回 PASS；远程文件仍 NOT_PUBLISHED，commit/push/PR/merge、云端 CI 和安装均 NOT_EXECUTED。因此“云端当前 main 已包含 G01”仍不成立。

## 治理与 UI 优先的后续选择 · 2026-10-09

用户在 G01 后明确要求全面执行，继续优先治理层和 UI 层。活动指针现在 selected_tasks / priority_tasks 已选择 H01、UF05 及后续 UI/Core 承接；上节 priority_tasks=[G01] 是当时验收记录，不是当前队列。当前 Agent 入口已同步此决定。V01 暂停、FT01–04 冻结，远程文件发布与安装边界不变。

H01 已新增独立来源投影与本地核验入口，导航登记在 DOCUMENTATION_AUTHORITY_INDEX 和 truth/README。426 个来源定位键、原270历史行、新96原始行、22页与186设计原文逐项保全；六来源字节 SHA 和97资产表身份核验，不声称97原件正文全读。当前可见用户决定独立记录，未扫描私人会话。

两检出本地来源门禁 PASS；canonical run `ui-learning-governance-final1` 的 H01/文档权威/索引回归51 PASS。H01来源结构和去向核验为 INTEGRATED；细项独立语义审查仍 UNVERIFIED / PARTIAL，产品实现 UNKNOWN。云端文件仍 NOT_PUBLISHED，不能将本地派生投影描述为云端已经可用。
