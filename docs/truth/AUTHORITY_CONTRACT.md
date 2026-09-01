# Authority Contract — ArcheAxis OS Execution

> 合同 ID：`AXW-AUTHORITY-v1-2026-08-09`
>
> 范围：`DTALEX66/ArcheAxis-Knowledge-OS` 的执行规则权威顺序。本文件固定“当来源冲突时谁优先”，防止历史蓝图或旧 handoff 覆盖当前用户指令与仓库规范。

## 1. 权威顺序（降序）

当不同来源对同一事实给出冲突指示时，按以下顺序裁决：

1. **当前用户指令**（本会话最新、明确的直接指示）最高优先。
2. **冻结执行基线** `docs/truth/FROZEN_EXECUTION_BASELINE_v1_2026-08-09.md`（`FROZEN`）与其批准增补包（Web v1、Capability-first v1）。这些是当前任务的唯一定义源，不可改写。
3. **追加式状态日志** `docs/truth/EXECUTION_STATUS_LOG.md`：只记录已发生的证据与决策；不得反向定义未来任务。
4. **仓库 AGENTS.md 与 `docs/VERIFICATION_POLICY.md`**：可复用的操作与验证规则。
5. **公开 README、PROJECT_STATUS、architecture/contract 文档**：描述性现状；若与冻结基线冲突，以冻结基线为准，并把差异记入状态日志。
6. **历史蓝图 / handoff / imported-design**（`docs/architecture/imported-designs/`、旧 `docs/bc-lines/`、旧 `docs/HANDOFF_*`）：仅作为**迁移输入与背景**，永不能覆盖第 1–4 项。它们的“已实现/已完成”声明若无当前 exact-SHA 证据，一律视为陈旧或候选。

## 2. 不可覆盖项

以下状态不因本任务列表存在而可被改写：

- 冻结基线、其 SHA 文件与所有已批准增补包原文（只读）。
- 状态日志中的历史 PASS/FAIL/BLOCKED/DEVIATION 记录（只追加）。
- 用户 WIP、未归属脏路径与真实资料源。
- 公开 immutable release/tag 与历史资产（不原地改写）。
- Hermes/Codex/CC Switch/Workflow-assistance 等外部工具运行状态（不属于本项目交付）。

## 3. 单一事实入口

当前能力、限制与证据等级的现场入口保持为：

```text
docs/current/CURRENT_REALITY_2026-09-01.md
```

`docs/PROJECT_STATUS.md` 是该入口的面向项目导航页。两者描述“已实现且已验证”的事实，并区分 `candidate` 与 `verified truth`。执行状态与任务进度由状态日志承载；二者互不覆盖。本合同与 `docs/truth/README.md` 的导航指向同一组文件。

## 4. 冲突处理

- 任何来源声称已完成某项 AXW 任务，若状态日志无对应 exact-SHA/LOCAL_RUNTIME/EXACT_SHA_CI/PUBLICATION/LIVE_INSTALLED 证据，一律视为 `UNASSESSED` 或 `PARTIAL`。
- 蓝图“已完成”不能作为当前验收；验收只能来自实际执行与回读。
- 发现矛盾时，在状态日志追加 `DEVIATION` / `CHANGE_PROPOSAL`，不静默选择更省事的一侧。

## 5. 不可变与回滚

- 本文件属于权威层文档，修改需由项目所有者批准并生成新版本。
- 回滚仅针对实现分支的提交；本合同一旦批准即作为权威记录保留。
