# R5 当前验证矩阵（2026-09-14）

本矩阵只汇总当前工作树可复核的本地证据。它不替代 R5 冻结任务包、独立 Q00/Q01 审计或 Windows 安装验收。

| 领域 | 当前结果 | 证据 |
| --- | --- | --- |
| 执行前置 | PASS；Python 3.13.14，yaml/fastapi/pytest/ruff 可用，破链 0 | `.project-local/runs/execution-preflight-modules-20260914b.json` |
| 架构/语言边界 | PASS；架构违规 0，跨语言/单一写入者边界 0 | `.project-local/runs/architecture-20260914c.json`；`R5-EXECUTION.md` |
| 路径规范 | PASS；1,994 个跟踪路径全部归属明确 | `.project-local/runs/path-conventions-20260914.json` |
| Core 依赖 | PASS；9 项依赖检查通过 | `.project-local/runs/core-dependency-check-20260914b.txt` |
| 入口/配置/桌面 | PASS；36 tests | `R5-EXECUTION.md`（2026-09-14 Entrypoint/config binding regression） |
| 安全/数据边界 | PASS；80 tests | `R5-EXECUTION.md`（2026-09-14 Authority/security boundary regression） |
| Workspace/交换/备份 | PASS；短 run-root 下 75 tests，2 skipped | `R5-EXECUTION.md`（short-run-root regressions） |
| 高覆盖 Python 回归 | 2,767 passed，7 skipped，126 subtests；3 个候选包回收用例因 taskkill 权限失败 | `R5-EXECUTION.md`（High-coverage regression） |
| 容量盘点 | PARTIAL；110,284 文件、约 10.73 GiB 可读逻辑大小；186 权限错误、11 重解析点 | `.project-local/runs/inventory-20260914.json` |
| 生产者追踪 | STRUCTURAL_ONLY；1,051 条静态候选，不等同运行时写入证明 | `.project-local/runs/output-producers-20260914.json` |
| R5 包完整性 | PASS；23 任务、38 场景、18 新切片 | `.project-local/runs/r5-package-verify-20260914b.json` |
| 收据文件完整性 | PASS；8 份当前收据均可解析 | `R5-EXECUTION.md`（2026-09-14 Receipt JSON integrity repair） |
| 独立审计 Q00/Q01 | NOT_RUN / NOT_READY | `docs/current/R5-STATE.json` |
| 安装、签名、卸载、干净机 | NOT_EXECUTED | `docs/current/R5-STATE.json` |

## 当前限制

- `.hermes`、`.zcode`、`.codex`、E 盘、外置模型/工具库、Green 和真实资料库未读取或修改。
- ACL-deny 目录未通过改 ACL 删除；`taskkill.exe` 权限问题未通过强杀进程绕过。
- Rust/C# 编译工具链在当前环境不可用；候选 Core 包不等同于完整桌面发行版。
- 当前工作树修改尚未提交或推送；未跟踪私有会话文件不属于本矩阵。
