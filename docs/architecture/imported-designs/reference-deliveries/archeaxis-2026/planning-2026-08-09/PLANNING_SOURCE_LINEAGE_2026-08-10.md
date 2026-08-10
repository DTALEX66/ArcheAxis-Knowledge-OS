# ArcheAxis Workspace Planning Source Lineage

> 日期：2026-08-10
> 目的：固定原始蓝图、规划、任务包与仓库执行权威之间的关系，避免再次因文件名、附件位置或历史对话丢失上下文。

## 1. 来源演变

```text
v0.5 多格式审计与恢复任务包
  + 未来总蓝图 v1
  → Codex 主任务包 v3
  → Final Master TaskPack v4
  → 冻结执行基线 v1
     + 强制 Web 知识摄取增补
     + 能力优先知识生命周期增补
     + DeepSeek 全量执行协议
     + 追加式状态日志
```

v4 声明完整吸收并取代 v3 及同日增量输入；后续仓库工作又将 v4 作为迁移决策源，重新拆分为不可改写的冻结任务定义、批准增补、执行协议和追加式证据日志。

## 2. 当前角色映射

| 来源 | 当前角色 | 可否直接定义新执行任务 |
| --- | --- | --- |
| v0.5 多格式审计任务包 | 历史问题与恢复输入 | 否 |
| Future Master Blueprint v1 | 产品能力与长期路线输入 | 否 |
| Master TaskPack v3 | 被 v4 取代的历史任务包 | 否 |
| Final Master TaskPack v4 | 冻结基线形成前的迁移决策源 | 否；先映射到当前任务 ID |
| Context Handoff | 对话续接摘要 | 否；实时事实必须重验 |
| Frozen Execution Baseline v1 | 当前冻结任务定义 | 是 |
| Web/KLC approved addenda | 当前批准增补任务定义 | 是 |
| DeepSeek Full Execution TaskPack | 执行控制协议 | 只能执行已批准任务 ID |
| Execution Status Log | 追加式证据与偏差记录 | 否；不得反向改写任务 |

## 3. 防漏与防漂移规则

1. 原始来源以 [`ORIGINAL_SOURCE_MANIFEST.sha256`](ORIGINAL_SOURCE_MANIFEST.sha256) 和原件 ZIP 固定；可读副本以 [`REPOSITORY_COPY_MANIFEST.sha256`](REPOSITORY_COPY_MANIFEST.sha256) 和 Git blob 固定，不依赖桌面、附件目录或对话列表。
2. 搜索任务时同时检查本目录、`docs/truth/`、`docs/taskpacks/`、`docs/FUTURE_EXECUTION_BLUEPRINT.md` 与 `docs/ABSORPTION_EXECUTION_MATRIX.md`。
3. 旧任务 ID、Program 名称、Horizon 或父任务不能自动当作当前原子任务；必须建立语义映射。
4. 供应商可以替换，但搜索、摄取、原件保存、多格式转换、证据/知识、课程/学习、approved-only AI 复用和评测反馈能力不可删除。
5. 文档存在只证明结构归档；实现、CI、发布和安装态资格必须使用对应证据等级独立验证。

## 4. 尚未关闭的核对项

- 本次归档证明五份原始文件完整存在并进入版本控制；不自动证明 v4 的每条自然语言要求已经被 159 项联合任务 DAG 逐条吸收。
- 后续应建立 requirement-to-task coverage ledger，把 v4 的能力、约束和验收要求映射到冻结基线或批准增补；无法映射的内容只能记录为 `CHANGE_PROPOSAL`，不得静默改写冻结文件。
- 当前分支、PR、CI、Release 和安装态事实必须从 Git/GitHub/真实运行重新读取，历史文件中的快照不作当前结论。
