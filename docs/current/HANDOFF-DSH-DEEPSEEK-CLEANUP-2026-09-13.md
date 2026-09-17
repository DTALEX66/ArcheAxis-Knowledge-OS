# DSH / DeepSeek 清理与瘦身交接

## 交接目标

本交接只授权 DSH/DeepSeek 继续审计和瘦身 `D:/All projects/ArcheAxis-Knowledge-OS`。
目标是降低项目自身的可再生构建、缓存和临时输出体积，保留当前可复用构建、验证证据、产品源代码
和用户资产。清理不等于产品功能闭环；X03 默认学习入口和 Core 桥接仍未完成。

## 现场身份

- 当前分支：`codex/full-loop-0906`
- 当前 HEAD：`3dee1278c170573c0d45e307635cafd8e1a68425`
- 最近两个功能/清理提交：`eef4b76`、`556f31f`
- 已上传到 `origin` 的同名分支；本地 tracking 状态可能因使用显式 HTTPS 推送而显示 ahead，不能把它解释为未上传。
- 未跟踪文件：`docs/current/SESSION-RESTART-2026-09-12.md`；保留，不要纳入清理或提交。

## 已完成且不可重复做的清理

已在用户授权后审计并删除：

1. 根目录 `target/`（约 5.73 GiB）；Cargo 已由 `.cargo/config.toml` 和 CI 改道到 `.project-local/build/cargo`。
2. `.project-local/build/be268a2d33/cargo/`（约 7.85 GiB）；属于旧 checkpoint Cargo 输出，当前验证使用新的共享 build/cargo。

两条路径均使用 PowerShell `Remove-Item -LiteralPath ... -Recurse -Force` 删除，随后逐条
`Test-Path` 复核不存在，命令退出 0。不要恢复、重复删除或从外部复制二进制。

## 当前项目自身体积（不包含受保护目录）

最近一次只读盘点：

| 路径 | 逻辑大小 | 处理意见 |
| --- | ---: | --- |
| `.project-local` | 13.22 GiB | 按子目录审计；`build` 当前产物、`runs` 证据先保留 |
| `.project-local/build` | 10.35 GiB | 当前 Cargo 与保留的 .NET 产物；不要整体删除 |
| `.project-local/build/cargo/debug/deps` | 4.93 GiB | 当前构建依赖，保留 |
| `.project-local/build/cargo/debug/incremental` | 4.23 GiB | 可再生但会拖慢后续构建；仅在确认无进程、无近期验证依赖后逐路径决定 |
| `.project-local/cache` | 1.54 GiB | 可再生缓存；先确认是否仍需离线测试/构建，再按子目录处理 |
| `.project-local/runs` | 0.78 GiB | 审计收据和回归证据，保留，不按缓存删除 |
| `.venv` | 0.88 GiB | 项目测试环境，保留；不要在共享环境重装 |
| `frontend` | 0.10 GiB | 现有前端依赖/产物，先不动 |
| `data` | 0.09 GiB | 项目数据边界，禁止当缓存清理 |

受保护目录 `.hermes`、`.zcode`、`.codex` 未读取、未计入上述盘点、未删除。历史脱敏记录曾测得
`.hermes` 约 42.85 GiB，但不能把旧数值当作当前事实，也不能据此操作目录；这些状态不属于产品资产。

## DSH 执行顺序

1. 先读根 `AGENTS.md`、`docs/current/R5-EXECUTION.md`、`docs/current/R5-STATE.json` 和本交接。
2. 用只读命令重新核对分支、HEAD、dirty paths、进程和 `.project-local` 子目录大小；不要扫描或枚举受保护目录内容。
3. 只对项目拥有且可重建的候选制定逐路径清单。优先审计 `.project-local/cache` 子目录和
   `build/cargo/debug/incremental`，保留 `build/cargo/debug/archeaxis-api.exe`、`.NET` 产物和所有 `runs` 收据。
4. 清理前确认没有 `cargo`、`rustc`、`archeaxis-api`、`dotnet` 或测试进程占用目标；每次只删一个已批准路径，删除后立即做 `Test-Path` 和大小复核。
5. 所有新盘点/日志/收据经 `scripts/runtime/dev.py` 写入 `.project-local`，不要写桌面、用户目录、系统 TEMP 或共享库。
6. 每次交付记录路径、删除前后字节数、命令、退出码、后置条件、回滚方法；不要用“瘦身完成”代替精确证据。

## 明确禁止

- 不读取、复制、合并、上传或删除 `.hermes`、`.zcode`、`.codex`；不要尝试修改 ACL 绕过边界。
- 不访问 `E:`，不读取凭据、`.env`、浏览器数据、私钥、token 或其他代理私有状态。
- 不删除 `docs/current/SESSION-RESTART-2026-09-12.md`，不执行 `git clean`、`reset`、强制覆盖或全局配置修改。
- 不清理真实资料库、Green、`D:/All projects/Model library` 或 `D:/All projects/OS External Configuration`。
- 不把旧证据目录、构建产物、`.venv`、项目 `data` 当作无主垃圾；不重复运行全量 CI 消耗额度。

## 需要回报的结果

DSH 应回报：

- 当前安全可审计总量与受保护黑箱单列；
- 每个候选路径的用途、最近写入时间、是否被当前入口引用、删除前后字节数；
- `PASS` / `PARTIAL` / `BLOCKED`，以及未删除的具体原因；
- 若删除，逐路径命令和后置条件；若保留，说明它服务的构建/验证/回滚用途；
- 不得宣称 78G 全部归因或全部清理，除非有新的、合规且不读取受保护状态的卷级证据。

额度紧张时，在剩余 20% 前停止新增大规模构建和扫描，整理本交接的增量证据。不要为了追求目录数字删除当前验证所需的缓存或证据。
