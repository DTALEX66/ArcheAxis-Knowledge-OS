# Verification Policy

> **2026-10-09 当前执行覆盖**：用户已选择新 UI 优先任务及 G01；规范活动指针为 [AAOS-ACTIVE-EXECUTION](current/AAOS-ACTIVE-EXECUTION.json)，当前任务来源为 [UI 优先 TaskPack](taskpacks/aaos-ui-first-20261009/TASKPACK.md)，实际进度只读 [UI 执行记录](current/AAOS-UI-FIRST-EXECUTION-20261009.md)。规划原文的 PLANNING_READY / NOT_EXECUTED 是规划时状态，激活与实际结果由当前覆盖记录，不改写不可变原包。AAOS-01 Q00–Q15 台账仅记录该继承工作流，不代表新 UI 全队列；旧 R6/M0 整包顺序冻结，有效合同、单一 Rust Core writer、内容先保存及历史证据保留。V01 继续暂停。
> 当前新布局、架构和其余产品界面按新任务执行；默认 `blueprint`，配套 `blueprint-light`，旧 `black` / `white` / `cosmic` 仅为额外配色主题。五主题共用新布局、组件状态及统一语义颜色；一个主题内部的按钮、菜单、侧栏与正文保持一致。主题不更改 Core 配置或知识数据。
> 平台指令优先；平台范围内用户当前明确决定优先于项目旧描述。此文档同步不授予 commit、push、merge、发布、私人账户/会话访问或恢复暂停的云端任务权限；本机资源索引不是云端权限。


> 适用范围：仅限 `archeaxis-workspace`。本文件是本仓库验证频率、审计触发和证据保留的唯一流程记录。

当前执行入口：[活动指针](current/AAOS-ACTIVE-EXECUTION.json) → UI 优先任务来源与当前 UI 执行进度。AAOS-01/R6/M0的有效合同和原日期收据继承；旧整包顺序冻结。V01继续暂停，G01只执行受影响文档、引用、权威和路径检查，不恢复历史 CI 改造或云端运行。

下述既有阶段/RC/Release验证方法是对应阶段获授权时的参考，不是本次任务自动执行清单。commit、push、merge、安装与发布分别需要当前授权；文档里的阶段节奏不授予远程操作权限。云额度阻塞不当代码FAIL，本地PASS不当exact-SHA cloud PASS。

## 目标

用最少但足够的验证保持本地与 GitHub 健康。验证必须回答一个具体风险，禁止为了“更放心”重复运行相同门禁。

## 三大阶段与验证节奏（AXC-050）

以下是继承的三大验证阶段；仅在当前任务明确选择相应阶段并允许其门禁时执行：

1. **Intake/RawAsset/Conversion 底座**（导入、转换、OCR/ASR 引擎链）；
2. **常规多格式/OCR/ASR/Evidence**（格式矩阵、证据、质量门）；
3. **Knowledge/Human Learning/AI Asset/重启导出**（知识、学习、评估、机器知识、导出回读）。

节奏定义：

| 时机 | 验证 |
| --- | --- |
| 开发中 | 定向测试（30～90 秒）+ changed-file Ruff |
| TaskPack checkpoint | 保存定向证据；commit 仅在获授权时执行，不自动 push 或跑全量 |
| 获授权大阶段 | 必要 full project CI（聚合 diff 冻结后）；V01 暂停不由此解除 |
| nightly | 兼容矩阵（py 3.11/3.13）与长期 corpus |
| RC | Windows 安装态全格式（wheel/Tauri/NSIS/E2E） |
| Release | exact-SHA、SBOM、checksum、签名、下载回读 |

## 必要门禁

1. **开发中**：每个新行为仍必须执行一次定向 RED → GREEN；集中测试不等于测试后补，也不允许多个未验证行为堆积。
2. **TaskPack checkpoint**：低风险垂直切片只运行受影响测试、changed-file Ruff、diff/convention，形成可审阅的 diff 与定向证据，获授权时才形成可回滚的本地 commit；不重复全量套件，也不逐个 push/CI。
3. **阶段 Release Train**：相应阶段和完整门禁另获当前 Owner 授权后，冻结同一大阶段的聚合 diff，运行一次完整门禁（pytest 主集 + ruff + architecture/convention/secrets），只有远程写入和云端运行另获授权时，才 push 并验收最新 SHA 的一次 GitHub Actions run；V01继续暂停。
4. **高风险旁路**：安全、权限、数据库、迁移、架构、打包/依赖变更**立即定向验证对应风险**，但只有触及 stage/RC/Release 才执行 full CI 与制品 exact-SHA；普通小修（迁移修复、依赖补丁）走定向 + stage 聚合，不扩大到发布级流程。
5. **失败后**：定向失败只重跑受影响门禁；阶段完整门禁失败先定位到具体 checkpoint，修根因后只重跑失败门禁，最终聚合 tree 变化后再执行一次完整门禁。
6. **Wheel**：从 clean checkout 构建，或先精确清理 ignored `build/` 与 `*.egg-info/`；对删除/重命名的 package-data 必须检查 wheel 成员表，防止陈旧构建目录把已退役文件重新打包。

## 审计触发

完整仓库审计只在以下情况执行：

- 新 Phase 建立基线；
- 架构、依赖方向、数据库 Schema 或安全边界改变；
- 现有门禁发现一种尚未建模的新违规类别。

普通修复不重新做全仓审计。已建立 scanner 的问题由增量门禁阻断，不再反复生成同类报告。

## 无人值守执行性能

1. 一个 TaskPack 使用一个持续 writer 会话，直到形成提交、明确阻塞或用户中止；不得按固定时间片反复启动全新 agent 并重读相同上下文。
2. 一次性 `hermes chat -q` 不得启动异步 reviewer 后立即退出；需要独立审查时，使用能等待结果的持续父会话或同步只读 reviewer。
3. reviewer 只在本策略列出的高风险触发点执行一次。普通版本化合同与 Adapter 不因“更放心”逐轮重审。
4. 开发循环只运行受影响测试；普通低风险 TaskPack 形成本地 checkpoint，完整门禁、聚合 frozen tree 和远端 CI 仅在对应阶段及各操作另获当前 Owner 授权后执行；V01 暂停期间不启动云端 CI。没有生产 diff 的循环不得重复这些步骤。
5. 每个后续周期先读取 Git 状态和上一周期最终结果；若 HEAD、tree 与失败证据未变化，必须继续原任务或停止，不能重新发现、重新冻结、重新派审。

### 外部协调工具（可选，AXC-030）

WORK-LAB 是一个独立仓库，仅作为可选外部工作流协调工具通过稳定 CLI/协议
与本项目协作；本项目不依赖其存在即可独立完成本地运行、CI、RC 与 Release。
调用外部协调工具（如 TaskPack runner）时通过 WORK-LAB 稳定 CLI/registry
入口，不硬编码绝对路径；必须传入与实际候选分支一致的 `--remote-ref`，
不得默认假定 `origin/main`，并携带本项目批准的 TaskPack 与风险等级。

高风险路径仍遵循本政策的完整门禁、frozen tree review 与 exact-SHA CI；
外部协调工具只提供单 writer、会话续接与 exact-tree 编排，不替代本项目的
架构、SQLite、权限和发布判断。

## Hash 与幂等边界（AXC-090）

- **产品实时**：RawAsset SHA-256、conversion revision、Evidence anchor/source digest、dedup identity。
- **项目阶段**：frozen tree SHA、corpus manifest、stage qualification。
- **Release-only**：wheel/installer checksum、exact-SHA release attestation、SBOM/signature/download readback。

幂等只用于 intake、RawAsset 写入、Job/Outbox、migration、网络核验、批准/撤销、导出写入；纯转换计算、查询、UI 不做重复"认证"（不把每次转换/查询包装成幂等认证步骤）。

## 审查触发（AXC-100）

立即定向 reviewer（仅以下场景）：

- 权限/安全；
- migration/数据恢复；
- 外部高风险写入；
- release/签名；
- 新的许可证硬风险。

不需要 reviewer：文档、格式化、既有 Adapter 小修、测试补充、UI 文案、已有规则覆盖的普通缺陷。全仓审计只在新 Phase、架构/数据/安全边界改变或新违规类别时运行。

## 证据与记录

每个低风险 TaskPack checkpoint 保留定向结果及获授权后产生的提交身份；获授权执行的每个阶段 Release Train 只保留：

- 最终提交 SHA；
- 最后一次必要本地门禁结果；
- 对应 GitHub Actions run URL；
- 已知但不阻断的警告。

不在路线图、技能和多个报告中复制易过期的测试数量、文件数量和中间失败日志。Git 历史与 CI 日志是执行证据，文档只记录稳定规则和当前决策。

### 任务运行不得膨胀（2026-10-08 落实）

规则由现有 launcher 与目录约定执行，不新建平行体系；`scripts/runtime/dev.py::layout()` 已经强制：精确 worktree 根、`.project-local/` 必须被 Git 忽略、按 worktree 身份哈希分目录、每个 run 独立 `runs/<identity>/<run_id>/{tmp,logs,artifacts}`，并导出 `ARCHEAXIS_RUN_ID`。在此之上补充以下必须项：

- 一次运行只新增必要增量证据；不得把整棵源码树、整个依赖环境或完整任务包复制进新的报告目录。同一来源完整内容只保留一份，当前视图通过稳定 ID、路径、哈希与生成器复用。
- 可共用的只读依赖缓存按项目机制复用：`frontend/node_modules` 用 Windows junction 指向已有安装（`New-Item -ItemType Junction`，移除只能用 `cmd /c rmdir`，`rm -rf` 会跟随链接删源），新 worktree 不复制大型共用资源；外置工具链与模型权重只经声明根解析，禁止为"统一归档"复制进项目。
- 任务写入必须隔离在 run 目录内；共享文件（如 `config/environment/external-resources-index.json`、供应链台账）由生成器重建或按 hunk 整合，不得被两个 writer 同时改写。
- 任务收尾必须列出产物归属：路径、归属依据、用途、可否重建、仍被谁引用、回收条件。被当前版本、未合并变更、验收记录或恢复路径引用的证据不得自动清除。
- 可重建缓存与必须保留的原始证据分别治理；worktree 归档先保存必要修改与恢复身份，再按授权操作。归属不清的目录保留并标记未解决，不用定时删除器代替归属判定，也不按目录名批量删除。

## 本地与云端健康

- 新开发临时数据统一由 `scripts/runtime/dev.py` 分配到被忽略的
  `.project-local/runs/<worktree-id>/<run-id>/`；缓存与构建位于该开发根的
  `cache/`、`build/`。测试使用 `scripts/ci/run_tests.ps1` 或 `.sh`。
  `.hermes` 是待分类保留的历史材料，不视为可直接重建的缓存。
  清理必须先核实归属、链接、进程锁和保留价值，不因任务结束自动删除。
- 禁止验证命令读写其他项目或数据目录。
- 提交前要求无未暂存变更、无凭据、无运行时数据库或缓存泄漏。
- 推送后必须确认远端 SHA 与本地提交一致且 CI 通过。
- 本地分支与远端分支分别记录 SHA；未发布 checkpoint 不声称双端一致。
  工作树与历史资料的清理独立于代码推送，不自动删除本地副本。
