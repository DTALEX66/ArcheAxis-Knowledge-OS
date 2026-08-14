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

## 验收（任务包 §14.2 Developer Kit）

- [ ] external backend 修改后自动重启
- [ ] 前端保持打开并恢复
- [ ] 不兼容 API 拒绝连接
- [ ] 后端崩溃日志可读
- [ ] 测试数据库与正式数据库严格隔离
- [ ] 从 bundled 切回 external、再切回 bundled
