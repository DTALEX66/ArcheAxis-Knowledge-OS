# Architecture Guard

## 目标

在不搬迁目录、不重写业务实现的前提下，为 Phase 1 建立可执行的依赖方向门禁。Guard 使用 Python AST，不依赖文本 grep，避免把注释和文档示例误报为运行时代码。

## 规则

`scripts/check_architecture.py` 扫描生产 Python 树并阻止：

1. 新增 `sys.path.insert()` 或 `sys.path.append()`；
2. `shared-contracts` 或未来 `platform` 模块反向导入业务模块；
3. `app/core`、`app/agent`、`shared`、`knowledge_base` 反向依赖 `app.facades` 或 `app.main`；
4. 运行时代码硬编码 Windows 盘符、`/Users/...` 或 `/home/...` 绝对路径。

## Grandfather 策略

历史 `sys.path` 兼容点和两个 crawler adapter 反向导入按“文件路径 + 行号 + AST 表达式/导入模块”精确登记。新增文件、移动调用点、不同表达式或额外重复都会失败；不会使用目录级或规则级宽泛豁免。

Grandfather 只允许当前代码继续运行，不代表这些兼容点是目标架构。后续 Facade 切换可逐项删除；删除旧点不需要修改 Guard 基线。

## CI

`.github/workflows/ci.yml` 的 lint job 在 Ruff 前执行：

```bash
python scripts/check_architecture.py
```

合同测试使用故意违规的临时 fixture，证明每类边界会被拒绝；另有当前树回归测试证明精确 grandfather 可用。

## 回滚

删除 CI step、Guard 脚本和对应测试即可回滚。Guard 不修改运行时数据、数据库 Schema 或业务入口。
