# DSH 后端执行任务提示词 — 2026-09-27

> 归档（2026-10-08 文档收敛，批次 d-docs-20261008）：本文件自 `docs/current/` 原样移入 `docs/history/dsh-backend-20260927/`，正文、日期与原始证据未改写；该主题的当前入口是 `docs/current/DSH-BACKEND-GAP-MAP-20260927.md`。

## 目标

在当前 ArcheAxis-Knowledge-OS 主线和 R6 权威边界内，独立核验 DSH 历史 DP-NF/DP-F01 交付是否已被当前 HEAD 吸收，并把可复现的后端验证补齐。最终提供一份带源代码定位、精确 SHA、命令与原始结果的任务报告。该工作与正在进行的 Green UI 母版复刻并行，但写入范围必须隔离。

## 当前基线与输入

- 仓库：`D:\All projects\ArcheAxis-Knowledge-OS`
- 当前交接/审计报告：`docs/current/DSH-BACKEND-HANDOFF-20260927.md`
- 当前权威：仓库根 `AGENTS.md`，R6 `docs/authority/taskpack-0919-r6/EXECUTOR-START.md`、`TASKS.json`、`TASKPACK.md`，以及 `docs/current/R6-EXECUTION.md`、`docs/current/R6-STATE.json` 和适用的 M0 overlay。
- 目标族：DP-NF-01…07、DP-A11、DP-F01、DP-UI-01 的后端交接边界。历史报告均为待核材料，不代表当前完成状态。
- 报告列出的 current HEAD `666d01b3bd1e14b9193e125593f44d282dfef524` 是本交接记录时读到的快照。执行时必须重新读取，不得假定它仍是当前 HEAD。

## 硬约束

1. 开始与结束读取 `git status --short`、HEAD/tree；不覆盖、不清理、不归属既存 dirty/untracked 文件。若 status 无法完整读取，记录原始权限错误和受影响范围。
2. 遵守根 AGENTS、R6 冻结 TaskPack 与 M0 优先级；不修改 TaskPack、R6 状态台账或由整合者维护的执行收据，不自行升级任务状态。
3. 本任务只写 DSH 后端报告/明确授权的后端代码路径，不接触 UI write-set、Green 安装目录、Candidate/发布或其他任务的未提交变更。需要代码修复时，先在报告中给出缺陷证据和最小建议，等待既定任务授权/Owner 冻结合同后实施。
4. 不运行 hard reset/clean/批量 restore，不执行 commit/push/merge/release；不读取或回显 secrets、session、memory、凭据。不访问 E:。不为通过测试安装全局依赖或修改系统配置。
5. 所有证据绑定当前 exact HEAD/tree 和 dirty state。旧分支测试只记“历史报告所载”；缺原始回执记 `REQUEST-ARTIFACT`。严禁把叙述、fixture、静态路由、编译通过或历史测试冒充 `REAL`、GUI、CI 或运行时验收。
6. 报告只使用项目批准的状态词：`TESTED_LOCAL`、`TESTED_LOCAL_PARTIAL`、`BLOCKED_BY_OWNER_DECISION`、`STRUCTURAL`、`NOT_EXECUTED`、`NOT_VERIFIED`。不得把 `PROPOSAL`、`BLOCKED`、`PASS`、`DONE` 当作项目状态；审计意见另用 `CONFIRMED`、`REFUTED`、`PARTIAL`、`UNVERIFIED` 并附证据。
7. 真实资料/模型/外部 CI/GUI 的缺证分别标为 `REQUEST-ARTIFACT`，并写清所需 artifact；未知不等于 0 或成功。保留 stdout、stderr、exit code、warning、skip 和失败摘要。

## 执行步骤

### A. 重建当前真值

- 读取根 AGENTS、R6 Executor Start/TASKS/TASKPACK、M0 overlay、当前 R6 execution/state；确认是否有更新的 Authority。
- 记录分支（若可读）、HEAD、tree、status、提交时间；检查报告所引用的当前源码路径确实存在，并给出行号。
- 只读实际 Git refs 与当前可访问的本地历史；建立 DSH 纳入 SHAs → parent/tree/path → 当前 HEAD ancestry/path 状态表。区分“已吸收”“被后续主线取代”“未吸收”“无法判定”。不能根据 worktree 名称或旧 handoff 推断 merge。
- 不联网查询、不改变远端状态；若远端/CI readback 是必要项，列成 `REQUEST-ARTIFACT`，不要声称已核实。

### B. 历史交付与代码逐项审计

对 DP-NF-01…07、DP-A11、DP-F01、DP-UI-01，各写一行：原始主张、审计判定 (`CONFIRMED/REFUTED/PARTIAL/UNVERIFIED`)、current-source 文件/行号或 SHA 证据、历史证据等级、未决项和接续动作。

重点核实：

- DP-NF-01 Git 审计器验证的是哪些 SHA/path，和当前 HEAD 的关系；“无候选/KEEP”是否仅限当时批次。
- DP-NF-02 / P0-H01 是否仍只是提案；资源根、Provider 身份/生命周期不得自行定案。
- DP-NF-03 quality matrix 在当前实现和当前测试下是否成立。
- DP-NF-04 Search 与 General Course 两部分分别审计；不可将 FTS 描述成 vector/hybrid/graph 或相关性已校准。
- DP-NF-05 重启边界测试覆盖与未覆盖内容；严格区分 fixture 与真实进程/模型。
- DP-NF-06 backup/Candidate 的源快照、dirty readback、verifier 当前证据。
- DP-NF-07 lineage/文件归属只按 Git 实据，不把未知 root/Codex/Hermes 文件认领为 DSH。
- DP-A11 Research projection、source_revision、Provider/version、运行 route 的现状；合同待 Owner 决策期间不造实现。
- DP-F01 Python/Rust quality roundtrip 与 typed receipt；D1–D5 Owner 问题未冻结前不更改公共 schema/API。
- DP-UI-01 保持交由独立 UI 任务提供 exact Candidate 后验收；本任务不触碰其源码或 Green。

### C. 当前 HEAD 复跑（先发现 canonical 命令）

依照 `AGENTS.md`、测试配置与 `scripts/runtime/dev.py` 发现项目真实命令、隔离证据目录和工具链；不要假定 pytest/cargo 通用命令能直接代表项目 gate。优先目标运行，依赖缺失则如实 `NOT_EXECUTED`，不要绕过项目边界。

尝试执行并各自留回执：

1. DP-F01 Python：`tests/workers/test_f01_real_quality.py`，再运行其明确相邻的 worker quality tests。
2. DP-F01 Rust：`archeaxis-api` 的 `f01_quality_roundtrip` 集成测试和受影响邻接测试。
3. DP-NF-03：P1 quality matrix 对应的精确测试目标。
4. DP-NF-05：`crates/archeaxis-domain/tests/machine_loop_restart.rs` 与受影响 domain 目标。
5. DP-NF-04：search 与 General Course/CourseManifest 相关目标分别运行；记录每个目标是否存在，不要扩大到不相关全套。

每个目标记录命令、当前 SHA/tree/dirty state、工具版本、测试路径、隔离数据目录身份（不得包含敏感内容）、stdout/stderr、exit code、pass/fail/skip/warnings 和回执绝对路径。失败时先诊断，不降低断言，不把依赖缺失归因成产品缺陷。

### D. Owner 决策与继续工作

- 将真正互斥的产品语义整理成决策单：A02 resource-root/schema；P0-H01 Provider/host identity/lifecycle；DP-F01 typed receipt proposal D1–D5；DP-A11 Research 能力/source revision/Provider/version。
- 每项给出当前证据、最小选项、兼容影响和默认安全行为；标 `BLOCKED_BY_OWNER_DECISION` 的仅限受该决定直接阻塞的工作。
- 等待决定期间继续完成不依赖该语义的 ancestry、静态审计、当前测试和可证伪核对；不要让 Owner 决策扩张成整个 DSH 任务的总阻塞。

### E. 输出与验收

更新或新增 `docs/current/DSH-BACKEND-HANDOFF-20260927.md` 的审计部分，必要时另存当前运行回执于项目规定的 `.project-local/` 隔离目录；不要改 immutable authority/台账。最终报告必须包含：

1. 当前 baseline（HEAD/tree/status 与可读性限制）；
2. 每个 DP 项的 `CONFIRMED/REFUTED/PARTIAL/UNVERIFIED` + 源码锚点；
3. 已吸收/取代/未吸收/无法判定的 SHA/path 表；
4. 当前重跑命令、逐项退出码与结果；
5. Owner 决策单和对应 `BLOCKED_BY_OWNER_DECISION` 范围；
6. `REQUEST-ARTIFACT` 清单；
7. 未执行项、风险、最小恢复方法和证据等级；
8. 结束时重新读取 `git diff --stat` 与 `git status --short`，明确列出本任务自己改动的文件。

完成标准：没有把历史报告冒充当前实现证据；当前测试对 exact SHA 可重现；后端与 UI 写范围分离；未知项有责任人/所需 artifact/下一步；不触碰 R6 Owner 台账和发布边界。若任一标准无法满足，结论保持 `STRUCTURAL`、`TESTED_LOCAL_PARTIAL` 或 `NOT_VERIFIED`，明确说明原因。
