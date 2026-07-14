# Phase 1 TaskPack：Facade 与 Architecture Guard

> Phase 0 输入基线：`469c39dcedf187e4c99d816728a2b38524881694`。功能与治理基线：`46076da8942ee7cc0846b4f2d4c5c5af8dfa0a49`。本 TaskPack 只建立可运行边界，不重写业务实现。

## 状态

- TP1.0 已完成：命名、编码与 repository convention 治理。
- TP1.1 已完成：Runtime Facade tracer bullet，旧 `/run` 保留并复用新边界。
- TP1.2 已完成：Knowledge keyword 查询与 Research IntakeCard candidate Facade；Research 已迁为可安装的 `inspiration_research` 包。
- TP1.3 已完成：Enhancement candidate 与 Contracts identity re-export Facade。
- TP1.4 已完成：AST Architecture Guard 已接入 CI，并以精确 grandfather 保留历史兼容点。
- TP1.6 已完成：CI、架构文档和旧入口兼容证据已收口。
- Facade/Guard 工作包已完成；下一阶段进入路线图 Phase 2。TP1.5 安全项对应路线图 Phase 3，保持独立批次。
- 验证频率、完整门禁与 reviewer 触发条件只由 [`docs/VERIFICATION_POLICY.md`](../../../docs/VERIFICATION_POLICY.md) 定义；本文件不复制一套可能漂移的门禁。

## 目标

建立 Research、Knowledge、Enhancement、Runtime、Contracts 五个公共 Facade；每个入口调用
当前真实实现，并以 Architecture Guard 阻止依赖方向继续恶化。

## Ownership

- 允许：新增 Facade、合同测试、架构守卫、最小 CI 接入和对应文档。
- 禁止：数据库迁移、依赖大升级、目录树搬迁、Planner/Evaluator 重写、外部仓库扫描。
- 数据边界：不得写入用户知识、活动数据库或仓库外路径。

## 垂直任务

### TP1.0 命名与编码治理（已完成）

1. `config/naming-registry.yaml` 成为 canonical ID 的机器真相。
2. `.editorconfig` 与 `.gitattributes` 定义编码和换行合同。
3. `scripts/check_repository_conventions.py` 支持 worktree、index 与 HEAD 扫描。
4. pre-commit 扫描 staged index，CI 扫描 Git HEAD。
5. 详细合同见 [`docs/NAMING_ENCODING_CONVENTIONS.md`](../../../docs/NAMING_ENCODING_CONVENTIONS.md)。

Phase 0 的清单隔离、运行时临时目录和 API 快照属于已冻结的历史基线生成能力，由 `tests/test_phase0_baseline.py` 和 `migrations/reports/phase-0/` 保留，不再占用 TP1.0 编号，也不在 Phase 1 重复生成整套审计。

### TP1.1 Runtime Facade tracer bullet（已完成）

1. 先写失败合同测试：通过 Facade 完成 route → permission → execute → trace。
2. 最小包装现有 `app/core` 与 `app/agent`，不得复制实现。
3. 对比 Facade 与旧入口的标准对象结果。

### TP1.2 Knowledge 与 Research Facade（已完成）

1. 先写失败测试覆盖一个真实查询和一个 candidate 摄入路径。
2. Knowledge Facade 调用 `knowledge_base` 稳定入口。
3. Research 实现已迁为 canonical `inspiration_research` 包；连字符目录只保留 deprecated API launcher，调用方不再注入路径。

### TP1.3 Enhancement 与 Contracts Facade（已完成）

1. 用现有摘要/卡片/质量能力完成一个真实 artifact tracer bullet。
2. Contracts Facade 先导出现有对象；版本化对象定义留给 Phase 2。

### TP1.4 Architecture Guard（已完成）

1. 为禁止依赖方向写失败测试。
2. 禁止新代码增加 `sys.path.insert`。
3. 禁止 Contracts/Platform 反向依赖业务模块。
4. 禁止运行时代码硬编码外部项目或个人资料路径。
5. 仅对白名单中的现有兼容点 grandfather，新增即失败。

### TP1.5 Security Guards（对应路线图 Phase 3，未开始）

1. 为 write/import/execute/backup 路由建立端点级 RBAC，`readonly` 变更请求必须 403。
2. 建统一 `safe_http_fetch()`，拒绝私网/回环/链路本地和重定向逃逸，并限制响应大小。
3. 所有 API 可达文件路径必须经过 approved-root containment；输入根与输出根分权。
4. 为 SSRF、symlink/junction 逃逸和存储型 XSS 候选补失败优先回归测试。

### TP1.6 CI 与文档收口（已完成）

1. 将 Architecture Guard 加入 CI。
2. 更新当前架构图和 Facade 所有权表。
3. 保留旧入口兼容期和回滚开关，不删除遗留 API。

## 每个垂直任务门禁

执行 [`docs/VERIFICATION_POLICY.md`](../../../docs/VERIFICATION_POLICY.md)：开发中每个行为只做一次 RED → GREEN 和 changed-file Ruff；冻结 diff 后按变更类型执行一次必要完整门禁；推送后只验收该提交对应的一次 GitHub Actions run。架构边界、安全、权限、数据库迁移或高风险外部写入才触发独立 reviewer。

## 验收

- 五个 Facade 至少各有一个调用真实实现的合同测试。
- Architecture Guard 能用故意违规 fixture 证明会失败。
- 旧入口和 Facade 对同一输入的合同对象可比较。
- 无新增 `sys.path.insert`、外部绝对路径、秘密或运行时生成物。
- 每个任务独立提交并写明回滚方法；推送后核对 CI 与远端 SHA。

## 回滚

TP1.0 已作为独立治理提交交付；后续按 TP1.1–TP1.6 的独立提交逆序回滚。Facade 切换前保留旧入口，因此回滚不得要求数据库恢复。
