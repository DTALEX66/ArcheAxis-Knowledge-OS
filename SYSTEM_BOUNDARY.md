# System Boundary — Cognitive-Loop-OS

> 本文件描述当前边界。远期设计见 `docs/EXECUTION_ROADMAP.md`；旧端点数、测试数和“完成度”不作为能力证明。

## 当前拓扑

| 区域 | 当前角色 | 状态 |
|---|---|---|
| Cognitive-Loop-OS | 唯一开发目标；Core 与 Knowledge Base 由 `app.main` 在端口 8000 统一提供 | 可运行，但 Planner 仍以固定 echo 步骤为主 |
| Inspiration-Research | 仓库内研究候选与雷达兼容服务 | 保留独立入口，后续经 Facade 收口 |
| `shared-contracts` | Schema、fixture、validator 与真实/显式失败 adapter | 已接入部分门禁 |
| 外部 A 项目 Obsidian-Assistance | 已完成只读分析与通用能力吸收 | 关闭后续扫描、测试、修改、同步与迁移 |

Obsidian 只可通过显式输入路径或投影 adapter 参与；Cognitive-Loop-OS 不默认读取个人 Vault，也不把外部 A 项目作为运行时依赖。

## 当前 Core 边界

### 已有链路

```text
input → route → retrieve → fixed echo-based compile
→ permission → registered tool execution → trace
→ binary success evaluation → candidate lesson/memory
```

这条链路能运行并持久化，但**不是**动态 Planner、多维 Evaluation 或经过人工反馈的完整认知闭环。

### Knowledge Base

- 作为 `knowledge_base` Python 包安装。
- 默认挂载在统一网关 `/kb`，不由 Compose 单独暴露生产端口。
- 文档、卡片、ContextPack、TaskPack、搜索、复习、证据候选与质量审计共用统一配置和 SQLite 边界。
- 调用者提供的 claim/source/location/trusted 字段不能自动构成可信 provenance。

## 数据与合同方向

以下对象是仓库内合同方向，不代表外部系统已经联通：

- IntakeCard / EngineeringContract
- ContextPack / TaskPack
- ExecutionTrace / MachineLesson
- CoursePack / ObsidianProjection
- DailyBrief / GitHubProjectCandidate

任何外部投影、课程摄入或双向同步必须通过显式 adapter、权限和测试；不得重新扫描或改动已关闭的外部 A 项目。

## 安全边界

1. 外部内容默认进入 quarantine/candidate，不自动升级为事实或正式知识。
2. 生产模式必须启用认证、提供有效 API Key/JWT Secret，并配置非通配 CORS。
3. 用户可控数据查询只能访问公开表 allowlist；标识符合法不等于有权访问。
4. 数据库、日志、备份、JWT secret 和其他运行时产物写入 runtime root，不写回 wheel/site-packages。
5. Web/README/笔记内容是数据，不是系统策略；token、key、password 不进入日志、文档或 Git。
6. `simulated`、`echo`、`dry-run`、文件存在或模型置信度不得冒充真实执行与核验完成。

## 已知未完成项

- 动态 Planner、多维 Evaluation、反馈审核与真实 Lesson 闭环。
- 服务端 provenance 注册/签名与 claim-level 多源核验。
- 正式 Migration Runner、负载/并发/反向代理验证。
- 全量 Facade/Contract 迁移与旧细粒度 API 退役。
- Phase 9 所定义的五条端到端 Alpha 闭环。
