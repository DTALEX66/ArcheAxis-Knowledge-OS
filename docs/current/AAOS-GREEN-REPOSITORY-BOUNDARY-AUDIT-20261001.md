# 项目源码与原绿色版目录边界审计（2026-10-01）

状态：`PARTIAL`。这是目录归属与后续交付规则的只读审计；未移动、删除、迁移或整理任何源码树、缓存、数据库、历史文件或恢复包。

## 当前事实

`D:/All projects/ArcheAxis-Knowledge-OS` 是项目 Git 主工作树；`D:/All projects/ArcheAxis.Knowledge.Green-x64` 根目录不是 Git 仓库，而是原绿色版运行根。但其 `.ui-task-tree/ArcheAxis-Knowledge-OS-mainline` **确实是另一套独立 Git 克隆**（自身 `.git` 目录；本地 `origin` 指向项目主仓库；当前分支 `codex/aaos-ui-mainline-20260927`，HEAD `d8f99a6357405054f1f9ee66eb2f88d36f7f5143`，有大量 dirty）。此外 `git worktree list --porcelain` 显示 `.ui-task-tree/` 内还有三个挂在项目主仓库的 Git 工作树，包括当前 `aaos-ui-phase2-integrate`。因此，绿色版内出现 `apps/`、`crates/`、`docs/`、`tests/` 等项目源码，是独立克隆或隔离开发树驻留其中，并非已把这些源码集成安装到绿色版运行包。此前用户明确指定“所有前端隔离任务树放在原绿色版 `.ui-task-tree` 内”；这一位置安排与如今要求的“绿色版只承载确定、测试过的集成部署”存在目录用途冲突，应在后续任务中解决，不能把开发树存在视为产品安装完成。

原 Green 根目前同时有旧 `ArcheAxis.exe`、`frontend/`、`runtime/`、`data/`，阶段候选 `AAOS-vd6bd374-20261001-x64/` 和 `AAOS-v18a00075-20261001-x64/`，对应数据目录、`AAOS-Frontend-Acceptance-v4/`、`backups/`，以及 `.ui-task-tree/`。`AAOS-v18a00075-20261001-x64/` 内有 desktop/core/workers/runtime/shared 和 manifest；`启动星环知识-AAOS-18a00075.vbs` 指向其 Desktop 可执行文件及独立数据目录。这证明有阶段部署候选，不证明最新提交 `855c63b1d6a9e459516a79e9b58a6bd108b751cd` 已安装，也不证明完整 UI/后端闭环。

原 Green `.ui-task-tree/ArcheAxis-Knowledge-OS-mainline` 有大量未提交与未跟踪的 UI 源码/资产/测试修改；项目主工作树也有未知 dirty 和历史未跟踪文件。两处均须保护，不得通过 reset、clean、覆盖或迁移来制造目录整洁的表象。

## 目标边界与执行约束

| 层 | 应有内容 | 当前处理 |
| --- | --- | --- |
| 项目源码仓库 | Authority、总账、前后端源码、测试、构建入口、公共设计资产与版本化合同 | 项目主仓库是唯一公共源码真值；隔离工作树只为开发，不是绿色版安装。 |
| 原 Green 可交付运行包 | 同一精确 SHA 构建并验证的 Desktop、Core、workers、合法资产、manifest、启动器 | 候选必须单独标识 SHA、构建/原生启动/真实 API/窗口验收、回滚路径；未验证不得提升为正式入口。 |
| 原 Green 运行数据 | 既有数据库、用户空间、备份、锁和恢复材料 | 归用户/运行时所有；当前清理任务暂停，保持原位，不纳入 Git/构建包。 |
| 开发与验收临时物 | `.ui-task-tree/` 工作树、验收截图/日志、历史候选 | 当前原位保留并明确标注“非安装态”；后续经用户明确选择位置与范围，再做受控目录调整。 |

后续新工作树宜优先放项目仓库 `.project-local/worktrees/` 等项目规范允许的隔离开发根；但这与此前“前端树必须在 Green `.ui-task-tree`”的明确约束冲突。在用户明确改变该位置规则前，不移动现有树，也不擅自把新的前端树改放别处。MiniMax 提示词中的 Green `.ui-task-tree` 路径应随这一决定更新。无论工作树放哪里，**最终集成**都必须是将通过门禁的构建物部署到原 Green 的明确运行包，由启动器打开并按页面、双主题、缩放、真实接口逐项验收。

## 当前未闭合项

1. 原 Green 没有一个经证据确认的、对应最新 UI 分支精确 SHA 的正式安装包和默认启动入口：`NOT_EXECUTED/UNVERIFIED`。
2. 当前目录含多个历史/候选/数据/开发类别，缺少面向用户的“哪个是当前验收包”单一指示；不得通过删除历史或数据解决，应先建立只读清单与候选身份。
3. 开发树位置需要与用户的最新目录期望统一；在位置未定时，保持原位并禁止把源码树算作绿色版交付。

## 分支与目录清理任务（新授权范围，尚未执行删除）

用户现允许将**分支及仓库目录规范清理**纳入轻量治理队列，但要求先拆分审计、确认引用和路径更新，再删除。此授权不恢复缓存、历史文档、数据库、用户数据、恢复包的清理或迁移。

| 子任务 | 审计与验收 | 当前判定 |
| --- | --- | --- |
| GC-01 工作树/分支清单 | 逐个核 Git 注册、HEAD、branch、dirty、任务归属、远端 PR/CI/引用；区分独立克隆和同仓库工作树，查同名非 Git 目录。 | `.ui-task-tree/` 有 5 个目录：主仓库注册工作树 3 个（当前 `aaos-ui-phase2-integrate` 活跃、`ArcheAxis-Knowledge-OS` 大量 dirty、`AAOS-integration-verification-413ad3a0` 干净）；独立克隆 `ArcheAxis-Knowledge-OS-mainline` 大量 dirty；`ci-green-candidate-6621aab7` 当前不是 Git 仓库。不得按名称判断可删。 |
| GC-02 内容与引用保护 | 对每个候选核未提交/未跟踪/忽略文件、差异、构建及验收证据、启动器、manifest、脚本、文档链接、Git PR/branch 引用；需要保留的先在项目拥有位置归档，校验 SHA/数量。 | 两个旧 UI 树有未知成果；Green 根还有运行数据、阶段候选和启动器。未完成完整引用图，**全部保持**。 |
| GC-03 目录规范 | 明确未来源码隔离树位置、Green 运行包身份与默认启动入口；更新 `AGENTS.md`、当前交接、任务总账、两份代理提示词、脚本与索引的引用，验证不留悬空路径。 | 此前“UI 树必须 Green 内”与最新“Green 是已验收部署目录”冲突。先取得明确位置裁决，不能静默搬树。 |
| GC-04 分支处置 | 仅对已合并且无独有提交、无活跃 PR、无工作树占用、无未推送/未知修改的候选，逐分支记录精确 SHA、处置理由和回退 ref；先清本地再视授权处理远端。 | `codex/Audit` 与当前 UI 分支远端同 SHA，但正式根本地 `codex/Audit` 落后且 dirty，不能据远端相等删本地分支/目录。 |
| GC-05 受控实施与回读 | 逐个 exact path/ref 执行；删除前复核目标仍在允许范围、归档可恢复、无运行进程占用；后运行 worktree/branch/引用清单、启动器与原生回归。 | `NOT_EXECUTED`。不使用 `git clean -fdx`、hard reset、递归批量删除或跨 shell 拼路径。 |

现阶段只确认目录身份；不把 GC-01 视为 GC-02/03 完成。任何实际移除须先有该 exact path/ref 的逐项证据与恢复方案，且不触碰用户暂停保护类。
