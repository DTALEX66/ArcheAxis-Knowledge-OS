# Verification Policy

> 适用范围：仅限 `Cognitive-Loop-OS`。本文件是本仓库验证频率、审计触发和证据保留的唯一流程记录。

## 目标

用最少但足够的验证保持本地与 GitHub 健康。验证必须回答一个具体风险，禁止为了“更放心”重复运行相同门禁。

## 验证分层

| 变更类型 | 开发中 | 冻结 diff 后 | 远端 |
| --- | --- | --- | --- |
| 纯文档/机械格式 | convention scanner + `git diff --check` | 不跑全量 pytest | GitHub CI |
| 业务或治理代码 | 受影响的定向测试 + changed-file Ruff | 完整本地门禁一次 | GitHub CI |
| 打包/依赖 | 定向导入或 wheel smoke | 完整本地门禁 + wheel 一次 | GitHub CI |
| 安全、权限、数据库、迁移、架构边界 | 定向测试 | 完整本地门禁 + 独立审查一次 | GitHub CI |

## 必要门禁

1. **开发中**：每个新行为只执行一次 RED → GREEN；小修后只重跑受影响测试。
2. **提交前**：diff 冻结后运行一次对应完整本地门禁；若之后只改文档，不重复业务测试。
3. **推送后**：只验收新提交对应的一次 GitHub Actions run；Python 版本矩阵交给 CI，不在本地重复模拟。
4. **失败后**：先修根因，再重跑失败门禁；只有代码、依赖或 workflow 在完整门禁后发生变化，才重新执行完整门禁。
5. **Wheel**：从 clean checkout 构建，或先精确清理 ignored `build/` 与 `*.egg-info/`；对删除/重命名的 package-data 必须检查 wheel 成员表，防止陈旧构建目录把已退役文件重新打包。

## 审计触发

完整仓库审计只在以下情况执行：

- 新 Phase 建立基线；
- 架构、依赖方向、数据库 Schema 或安全边界改变；
- 现有门禁发现一种尚未建模的新违规类别。

普通修复不重新做全仓审计。已建立 scanner 的问题由增量门禁阻断，不再反复生成同类报告。

## 审查触发

独立 reviewer 仅用于安全、权限、数据库迁移、架构移动和高风险外部写入。低风险文档、格式归一化、纯合同 Adapter 和已有规则的小修依靠定向测试、diff 检查与 CI，不反复派发 reviewer。

## 无人值守执行性能

1. 一个 TaskPack 使用一个持续 writer 会话，直到形成提交、明确阻塞或用户中止；不得按固定时间片反复启动全新 agent 并重读相同上下文。
2. 一次性 `hermes chat -q` 不得启动异步 reviewer 后立即退出；需要独立审查时，使用能等待结果的持续父会话或同步只读 reviewer。
3. reviewer 只在本策略列出的高风险触发点执行一次。普通版本化合同与 Adapter 不因“更放心”逐轮重审。
4. 开发循环只运行受影响测试；完整门禁、冻结 tree 和远端 CI 各执行一次。没有生产 diff 的循环不得重复这些步骤。
5. 每个后续周期先读取 Git 状态和上一周期最终结果；若 HEAD、tree 与失败证据未变化，必须继续原任务或停止，不能重新发现、重新冻结、重新派审。

### 正式 TaskPack runner

无人值守开发使用仓库内 [`scripts/run_taskpack_agent.py`](../scripts/run_taskpack_agent.py)，不再使用按固定分钟数杀进程并启动新 agent 的循环：

```bash
python scripts/run_taskpack_agent.py \
  --mission-file migrations/reports/phase-2/PHASE_2_TASKPACK.md \
  --risk low
```

- `--risk low`：一个 Hermes writer 会话完成 RED/GREEN、一次冻结后完整门禁、commit、push 与 exact-SHA CI。
- `--risk high`：writer 先冻结全部 staged 改动且禁止 commit；runner 同步等待只读 reviewer。`NO-GO` 使用 stderr 中的 `session_id` 续接同一 writer lineage 修复，`GO` 后才续接发布。
- runner 在送审前拒绝 unstaged、untracked 和冲突文件；审查前后比较 `git write-tree` 与 porcelain status，reviewer 只要产生任何写入就立即失败。
- 发布验收由 runner 独立执行：工作区 clean、HEAD 前进、fetch/prune、`HEAD == origin/main`、该 HEAD 的 GitHub Actions 全部成功。
- agent 调用不设置固定周期 timeout；仅远端 CI 等待有 20 分钟故障上限。旧的 `cognitive_7h_runner.py` 固定时间片模式已废弃。

## 证据与记录

每个 TaskPack 只保留：

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
