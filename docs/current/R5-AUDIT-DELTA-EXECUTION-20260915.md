# R5 审计差分执行收据（2026-09-15）

本收据对应用户提供的 `ARCHEAXIS-R5-AUDIT-DELTA-2026-09-14.zip`，原包隔离解压于项目 `.project-local/runs/r5-audit-delta-20260915/`。它是 R5 的复审与修复要求，不替换 `docs/authority/taskpack-0912-r5/`。

## 已实施

| 差分 | 实施 | 验证 | 交付提交 |
| --- | --- | --- | --- |
| A02 | Core 备份/恢复绑定 ArcheAxis 身份元数据与 hash；无元数据 SQLite 被拒绝 | `tests/test_core_launch.py`: 21 passed | `a3ea5f17` |
| A03 | 执行预检拒绝非 Git 根或缺失 HEAD | `tests/workflow/test_execution_preflight.py`: 3 passed | `93faebc7` |
| A04 | Avalonia 默认学习界面可载入项目、输入回答、选择结果并提交 Core review | 桌面结构回归：11 passed | `32ba061a` |
| A05 | `learning/v2/review.schema.json` 与 Rust 可选证据字段 | 契约/恢复组合：33 passed | `e50e444d` |
| A06 | 只读环境 Registry，记录资源 ID、来源、命令路径、版本和探测状态 | `tests/workflow/test_environment_registry.py`: 2 passed | `d5d8ab01` |
| A01 | 发布前检查 Avalonia → Rust Core → Python workers 正式链；Tauri/frontend 标为 recovery | 架构/CI 结构门：24 passed | `4903c4da` |

## 当前头与边界

- 当前测试/实现头：`1a0a8028c4a80c1e8cb4f715b9ba9c9465227a61`（本收据此前记录的实现头为 `4903c4da`）。
- 当前工作分支与 `origin/codex/full-loop-0906` 已逐次推送到相同 SHA。
- 2026-09-15 `git ls-remote origin refs/heads/codex/full-loop-0906 refs/heads/main` 回读：工作分支为 `1eb0f8fe96cbca7766b73822c6aa96b958d5c8ee`，`main` 为 `1e9813ea2bd49f47d334ba6717c78d3e9feda6ce`。
- GitHub Actions 的当前头精确 CI 结果未能从本机 CLI 读取（GitHub CLI 配置权限拒绝）；公开页面无法绑定该 SHA，故 A07 仍为 `NOT_VERIFIED`。
- 2026-09-15 公开 Actions API 查询 `head_sha=f6d6a3ba156fcdba7f5f5d340fb6a436a2090742` 返回 `total_count=0`；当前 CI 仅对 `main` push、PR 或手动 dispatch 触发，工作分支推送不会自动产生该记录。未使用凭据触发 dispatch。
- 随后扩展 `codex/**` 触发并运行 `34879091966`（head `eba3a097ea49e66a2d7d520ef0624d2b7671dcf4`）：总体 `failure`；`gateplan` 成功，`lint`、`desktop-fast`、`desktop-build`、`a0-gates` 失败，其余选择性 job 跳过。公开 API 仅可见退出码，日志下载接口返回 403 管理员权限要求。
- 未执行 C# 编译、Windows 可见 GUI、安装/签名/卸载/干净机、真实 Green/四库、外置模型/工具库或真实资料库。
- Q00/Q01 仍须独立审计，执行者不得自签。

## 交接增补（2026-09-15）

- 分支触发后的 Run `34880184223` 仍未形成可用的完整成功证据：`gateplan` 已通过，`lint` 与 `desktop-fast` 失败，`desktop-build` 长时间停留在 Rust 依赖审计；公开日志接口返回 403，无法取得失败堆栈。
- 本机再次读取该 Run 的公开 API 时出现认证失败；`git ls-remote` 复核也因 SSH `known_hosts` 权限错误失败。因此当前只能沿用此前已记录的远端回读，不把当前远端状态写成已确认一致。
- 当前工作树的 `docs/history/` 迁移资产与 `docs/current/SESSION-RESTART-2026-09-12.md` 均为未跟踪内容，本次交接不纳入提交。
