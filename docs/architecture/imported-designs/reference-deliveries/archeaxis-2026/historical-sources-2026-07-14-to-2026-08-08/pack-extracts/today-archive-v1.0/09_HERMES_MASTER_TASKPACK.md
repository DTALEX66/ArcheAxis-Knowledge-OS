# HERMES 总任务包：2026-07-28 项目决策落地

## 元数据

- 项目：`Cognitive-Loop-OS`
- 仓库：`DTALEX66/Cognitive-Loop-OS`
- 本包最后可见远端 SHA：`a92e6730a267f4268ff64d92be5d2fc17bce59e5`
- Writer：HERMES
- Reviewer：Codex 只读
- 原则：一个阶段一个分支、一个 PR、一个完整门禁

## 总目标

将今天形成的项目定位和技术决策安全地落入仓库：

1. 项目从“认知操作系统”修正为“个人与 AI 双向重型学习知识系统”；
2. 保留已验证的 Research/Knowledge/Learning/Runtime 工程能力；
3. 将 Agent 降为 AI 使用层能力；
4. 重排前端信息架构；
5. 采用苹果明亮主题为默认目标，紫曜为深色主题；
6. 渐进升级语言和配置，不推倒重写；
7. 不制造与后端不一致的产品声明。

# 本轮只执行两个 TaskPack

## AXOS-TODAY-00：云端基线确认

只读执行：

```powershell
git fetch --all --prune
git status --short
git branch --show-current
git rev-parse HEAD
git rev-parse origin/main
git log -10 --oneline
```

确认：

- 工作树 clean；
- 当前 SHA；
- upstream；
- 是否存在未合并 PR；
- CI 状态；
- `a92e673...` 是否仍为 main HEAD。

如不一致，先报告，不得硬重置。

## AXOS-TODAY-01：定位与文档真相修正

### 风险

低到中等。原则上不改变业务行为和数据库。

### 建议分支

`docs/reposition-bidirectional-learning-knowledge-system`

### 允许修改

- `README.md`
- `pyproject.toml` 中 description / keywords / metadata
- `app/release-manifest.json` 中不改变 release 状态的产品说明字段
- `docs/README.md`
- `docs/PROJECT_STATUS.md`
- 当前架构/蓝图/吸收矩阵中的主定位说明
- Workspace 标题、说明和 Planned 文案
- 命名 Registry 中展示层名称（若不改变 canonical IDs）
- 相关测试和文档

### 禁止修改

- 数据库 Schema；
- Migration；
- Research/Knowledge/Learning 持久化；
- Planner；
- Evaluation；
- Auth；
- Safe HTTP；
- Tauri 安全；
- Release `unreleased/public=false`；
- 当前版本号；
- 其他项目；
- Workflow-assistance；
- 个人 Vault；
- E 盘资料。

### 需要完成

#### 1. README

主定位改为：

> 元枢系统是一套面向个人与 AI 协同使用的、本地优先、证据驱动的双向重型学习知识系统。

将原有主链解释为：

```text
Sources / Evidence
→ Governed Knowledge
→ Human Learning + AI Usage
→ Reviewed Bidirectional Feedback
```

不得删除现有真实工程状态和边界。

#### 2. 元数据

`pyproject.toml`：

- description 不再以 cognitive runtime 为中心；
- keywords 增加：
  - learning-system
  - knowledge-system
  - human-ai
  - evidence-driven
  - local-first
- 旧 `cognitive-os` 关键词可暂时保留用于仓库兼容，但不作为首位。

#### 3. 文档

统一说明：

- Agent 属于 AI 使用层；
- Runtime 不是产品中心；
- Research/Knowledge/Learning 是共同知识底座；
- Candidate / Approved 不变；
- 旧“认知”术语作为历史/内部术语；
- 不宣称当前已具备完整双向自动反馈。

#### 4. 前端信息架构文档

把未来一级导航调整为：

- 总览；
- 资料库；
- 研究验证；
- 知识库；
- 学习中心；
- AI 知识；
- 双向转化；
- 任务应用；
- 连接；
- 系统。

A1 现有真实页面不必立即重构，只更新路线和 Planned 文案。

#### 5. 吸收矩阵

强调：

- 101 个候选是 Registry/Ledger 状态；
- 不是集成数量；
- 所有外部能力服务于资料、知识、学习、AI 使用或系统工程；
- 不扩大能力声明。

## RED / GREEN

至少增加或更新测试以检查：

- README/Manifest/pyproject 主定位一致；
- 版本仍为 0.4.0；
- release 仍为 unreleased/public=false；
- canonical IDs 不因展示名称改变；
- 不出现新的内部 ID 泄漏；
- 当前 Workspace 页面仍可加载。

## 门禁

```bash
python scripts/check_repository_conventions.py --source worktree
python scripts/check_architecture.py
node --check app/workspace/ui/assets/app.js
python -m ruff check app shared knowledge_base inspiration_research Inspiration-Research shared-contracts/adapters app/workflow integration-tests scripts
python -m pytest tests/ -q --tb=short
cd knowledge_base && python -m pytest tests/ -q --tb=short
cd ..
python -m pytest integration-tests/ -q --tb=short
```

纯文档改变不需要重复运行所有 Windows 发布门禁；如果修改 Workspace UI 或包元数据，
按 `docs/VERIFICATION_POLICY.md` 判断是否需要 Wheel/Browser/Windows CI。

## 停止条件

遇到以下情况停止并报告：

- 远端 HEAD 与本包不一致且差异未审；
- 工作树不 clean；
- 修改需要数据库迁移；
- 定位修正导致 API/合同破坏；
- 需要修改其他项目；
- 需要删除历史文档；
- 测试要求更改 Release 状态；
- CI 不可读取或 exact-SHA 无法确认。

## 交付报告

HERMES 必须输出：

- 实际基线 SHA；
- 分支；
- 修改文件；
- 定位前后对照；
- RED/GREEN；
- 门禁结果；
- Commit SHA；
- PR；
- CI；
- 未执行的后续 TaskPack；
- 明确说明未完成前端重构、配置升级和 P0 工程债务。
