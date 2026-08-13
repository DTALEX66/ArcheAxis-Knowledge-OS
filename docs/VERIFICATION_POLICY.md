# Verification Policy

> 适用范围：仅限 `archeaxis-workspace`。本文件是本仓库验证频率、审计触发和证据保留的唯一流程记录。

## 目标

用最少但足够的验证保持本地与 GitHub 健康。验证必须回答一个具体风险，禁止为了“更放心”重复运行相同门禁。

## 三大阶段与验证节奏（AXC-050）

固定三大阶段，每阶段结束执行一次完整项目 CI：

1. **Intake/RawAsset/Conversion 底座**（导入、转换、OCR/ASR 引擎链）；
2. **常规多格式/OCR/ASR/Evidence**（格式矩阵、证据、质量门）；
3. **Knowledge/Human Learning/AI Asset/重启导出**（知识、学习、评估、机器知识、导出回读）。

节奏定义：

| 时机 | 验证 |
| --- | --- |
| 开发中 | 定向测试（30～90 秒）+ changed-file Ruff |
| TaskPack checkpoint | 本地 commit，不 push、不跑全量 |
| 每大阶段 | 一次 full project CI（聚合 diff 冻结后） |
| nightly | 兼容矩阵（py 3.11/3.13）与长期 corpus |
| RC | Windows 安装态全格式（wheel/Tauri/NSIS/E2E） |
| Release | exact-SHA、SBOM、checksum、签名、下载回读 |

## 必要门禁

1. **开发中**：每个新行为仍必须执行一次定向 RED → GREEN；集中测试不等于测试后补，也不允许多个未验证行为堆积。
2. **TaskPack checkpoint**：低风险垂直切片只运行受影响测试、changed-file Ruff、diff/convention，形成可回滚的本地 commit；不重复全量套件，也不逐个 push/CI。
3. **阶段 Release Train**：同一大阶段的一组低风险 checkpoint 完成后，冻结聚合 diff，运行一次完整门禁（pytest 主集 + ruff + architecture/convention/secrets），再统一 push 并验收最新 SHA 的一次 GitHub Actions run。
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
4. 开发循环只运行受影响测试；普通低风险 TaskPack 形成本地 checkpoint，完整门禁、聚合 frozen tree 和远端 CI 每个阶段 Release Train 各执行一次。没有生产 diff 的循环不得重复这些步骤。
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

每个低风险 TaskPack checkpoint 只保留本地 commit 与定向 RED/GREEN 结果；每个阶段 Release Train 只保留：

- 最终提交 SHA；
- 最后一次必要本地门禁结果；
- 对应 GitHub Actions run URL；
- 已知但不阻断的警告。

不在路线图、技能和多个报告中复制易过期的测试数量、文件数量和中间失败日志。Git 历史与 CI 日志是执行证据，文档只记录稳定规则和当前决策。

## 本地与云端健康

- 临时数据只能写入本仓库 `.tmp/`、测试专用目录或已忽略的构建目录；结束前删除。
- 禁止验证命令读写其他项目或数据目录。
- 提交前要求无未暂存变更、无凭据、无运行时数据库或缓存泄漏。
- 推送后必须确认远端 SHA 与本地提交一致且 CI 通过。
- 使用一次性本地克隆的交付流程，在远端验证完成后删除该克隆；远端仓库作为唯一长期代码真相。
