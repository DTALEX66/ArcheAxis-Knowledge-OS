# ArcheAxis Knowledge Developer Kit（AXW-PKG-605）

> 内部开发产物，不作为普通用户正式版。用于"前端常驻、后端热重载"开发测试。

## 内容

- `runtime-profile.external-dev.yaml` — 外接后端 Runtime Profile 模板
- `README.md` — 使用说明（本文件）

## 使用流程（任务包 §8.3）

1. 在桌面应用 **设置 → 开发者 → 启用外接后端**
2. 选择源码根目录与 Python runtime（要求 `pyproject.toml` + package identity + API contract 检查通过）
3. 创建或选择**隔离测试工作区**（禁止直接打开正式生产数据库）
4. 启动迁移 dry-run → 启动 uvicorn reload 后端
5. 前端 handshake 成功后即可热修改 Python 文件（自动重启 + 自动重连）

## 安全约束

- external-dev 默认只使用隔离测试数据；Owner 明确选择正式数据时必须先一致性备份 + 显示绝对路径 + 风险确认
- reload 前不重复执行非幂等迁移
- 前端显示醒目的 `DEV BACKEND / TEST DATA` 状态条
- 开发后端不得继承用户全局 `PYTHONPATH`、代理或未授权密钥
- 本 Kit 不含任何密钥或个人绝对路径（路径仅作本机示例，不写入公共默认配置）

## 外部热重载工作流（AXW-DEV-301~304）

前置：`config/profiles/external-dev.yaml`（`backend: external-source`、
`data_policy: isolated-test-workspace`、`reload: true`、`source_root` 指向外接源码 checkout）。

1. **启动 external-dev profile**：设置 `ARCHEAXIS_RUNTIME_PROFILE=external-dev` 后启动后端，
   handshake 返回 `runtime_mode=external-dev`；Recovery Shell 显示 `DEV BACKEND / TEST DATA`
   徽标与 reload 状态面板（10s 轮询 `/api/v1/system/status` 的 `reload` 字段）。
2. **修改代码**：编辑 `source_root` 下任意 `*.py`（`.git/.venv/.hermes/__pycache__/node_modules`
   被监听器忽略）。`app/workspace/hotreload.py` 以默认 1.0s 间隔做 mtime 轮询，检测到变更后
   调用 supervisor 的 `request_reload()`。
3. **自动 reload**：supervisor 执行 `ready → reconnecting → ready` 生命周期并记录
   `reload_count` / `last_reload_at`（仅 external-dev 且 `reload: true` 时允许，否则 fail-closed）。
4. **验证**：`GET /api/v1/system/status` 检查 `reload` 字段——
   `{"enabled": true, "interval_ms": 1000, "reload_count": <递增>, "last_reload_at": ...}`。
   手动重载：Recovery Shell 面板「重载」按钮或 `POST /api/v1/system/restart`。
5. **测试数据隔离**：external-dev 数据策略为 `isolated-test-workspace`；用
   `app/workspace/test_workspace.py::clone_test_workspace(src_workspace, dst)` 从现有工作区
   克隆出隔离测试工作区（复制四资产域真实文件 + manifest，重新生成 `workspace_id`（uuid4），
   保留 `data_ownership`；`dst` 已存在时报错，不覆盖正式数据）。

## 验收（任务包 §14.2 Developer Kit）

- [ ] external backend 修改后自动重启
- [ ] 前端保持打开并恢复
- [ ] 不兼容 API 拒绝连接
- [ ] 后端崩溃日志可读
- [ ] 测试数据库与正式数据库严格隔离
- [ ] 从 bundled 切回 external、再切回 bundled
