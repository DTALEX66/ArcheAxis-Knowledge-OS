# Phase 1 TaskPack：Facade 与 Architecture Guard

> 输入基线：`82b9df3f719d9212111536b454654f2243150f16`。本 TaskPack 只建立可运行边界，不重写业务实现。

## 目标

建立 Research、Knowledge、Enhancement、Runtime、Contracts 五个公共 Facade；每个入口调用
当前真实实现，并以 Architecture Guard 阻止依赖方向继续恶化。

## Ownership

- 允许：新增 Facade、合同测试、架构守卫、最小 CI 接入和对应文档。
- 禁止：数据库迁移、依赖大升级、目录树搬迁、Planner/Evaluator 重写、外部仓库扫描。
- 数据边界：不得写入用户知识、活动数据库或仓库外路径。

## 垂直任务

### TP1.0 基线可信度与完整测试矩阵

1. 保持 NUL/Unicode-safe HEAD 清单、dotfile、报告自排除与 index 隔离回归测试。
2. 在任何测试导入前设置隔离数据目录，禁用 bytecode/pytest cache，保证活动数据库哈希不变。
3. 修复 `Inspiration-Research/tests` 的包导入并加入 CI；每套测试记录 cwd、Python 版本和收集数。
4. API 快照按 core、KB、IR 服务分组，区分 route 与 operation，禁止硬编码漂移数字。

### TP1.1 Runtime Facade tracer bullet

1. 先写失败合同测试：通过 Facade 完成 route → permission → execute → trace。
2. 最小包装现有 `app/core` 与 `app/agent`，不得复制实现。
3. 对比 Facade 与旧入口的标准对象结果。

### TP1.2 Knowledge 与 Research Facade

1. 先写失败测试覆盖一个真实查询和一个 candidate 摄入路径。
2. Knowledge Facade 调用 `knowledge_base` 稳定入口。
3. Research Facade 隔离连字符目录兼容逻辑，调用方不得新增 `sys.path.insert`。

### TP1.3 Enhancement 与 Contracts Facade

1. 用现有摘要/卡片/质量能力完成一个真实 artifact tracer bullet。
2. Contracts Facade 先导出现有对象；版本化对象定义留给 Phase 2。

### TP1.4 Architecture Guard

1. 为禁止依赖方向写失败测试。
2. 禁止新代码增加 `sys.path.insert`。
3. 禁止 Contracts/Platform 反向依赖业务模块。
4. 禁止运行时代码硬编码外部项目或个人资料路径。
5. 仅对白名单中的现有兼容点 grandfather，新增即失败。

### TP1.5 Security Guards

1. 为 write/import/execute/backup 路由建立端点级 RBAC，`readonly` 变更请求必须 403。
2. 建统一 `safe_http_fetch()`，拒绝私网/回环/链路本地和重定向逃逸，并限制响应大小。
3. 所有 API 可达文件路径必须经过 approved-root containment；输入根与输出根分权。
4. 为 SSRF、symlink/junction 逃逸和存储型 XSS 候选补失败优先回归测试。

### TP1.6 CI 与文档收口

1. 将 Architecture Guard 加入 CI。
2. 更新当前架构图和 Facade 所有权表。
3. 保留旧入口兼容期和回滚开关，不删除遗留 API。

## 每个垂直任务门禁

```bash
python -m pytest <targeted-test> -q --tb=short
python -m ruff check <changed-files> --no-cache
python -m pytest tests -q --tb=short
python -m pytest knowledge_base/tests -q --tb=short
python -m pytest Inspiration-Research/tests -q --tb=short
python -m pytest integration-tests -q --tb=short
python -m ruff check app shared knowledge_base Inspiration-Research \
  shared-contracts/adapters app/workflow integration-tests scripts --no-cache
git diff --check
```

## 验收

- 五个 Facade 至少各有一个调用真实实现的合同测试。
- Architecture Guard 能用故意违规 fixture 证明会失败。
- 旧入口和 Facade 对同一输入的合同对象可比较。
- 无新增 `sys.path.insert`、外部绝对路径、秘密或运行时生成物。
- 每个任务独立提交并写明回滚方法；推送后核对 CI 与远端 SHA。

## 回滚

按 TP1.0–TP1.6 的独立提交逆序回滚。Facade 切换前保留旧入口，因此回滚不得要求数据库恢复。
