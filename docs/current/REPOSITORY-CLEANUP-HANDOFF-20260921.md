# ArcheAxis 仓库整理、瘦身与交接报告（2026-09-21）

> **HISTORICAL HANDOFF / NOT CURRENT GIT OR RUNTIME TRUTH.** This document is
> preserved for the 2026-09-21 cleanup evidence. Its branch, HEAD, remote and
> working-tree values are dated snapshots. Use
> `REPOSITORY-DRIFT-CURRENT-RECEIPT-20260923.md` for current readback. The
> exact cleanup receipt and deleted-path evidence remain valid within their
> recorded scope.

## 当前结论

本轮完成了一次只读边界审计、项目内输出溢出追踪，以及一组有明确归属且可再生的构建/候选产物清理。未读取、修改或删除 `E:\`、`F:\`、`.codex`、`.zcode`、`.hermes`、凭据、外置共享库、真实资料库、测试资料库或现有 Green 运行目录。

清理收据为 `.project-local/audits/cleanup-receipt-20260921.json`。收据记录 28 个精确路径、全部删除成功、删除前 8,361,939,708 bytes、删除后剩余 0 bytes、错误 0、残留路径 0。删除对象只属于项目内的旧 Green 候选重复包和不再被当前证据引用的中间构建输出。

## Git 与上传状态

| 项目 | 当前值 |
| --- | --- |
| 分支 | `main` |
| `HEAD` | `42d5660c1b5f36b6f13445ea5fe631662cd75047` |
| 本地 `origin/main` | `42d5660c1b5f36b6f13445ea5fe631662cd75047` |
| `HEAD...origin/main` | `0 0` |
| 跟踪文件修改 | 本轮报告提交前为 0 |
| 未跟踪项 | `docs/history/` 迁移资产及 `SESSION-RESTART-2026-09-12.md`，全部保留、未纳入本轮提交 |

本轮先遇到 SSH `known_hosts` 读取权限问题，随后在授权的推送环境中完成上传。最终 `git ls-remote origin refs/heads/main` 返回 `42d5660c1b5f36b6f13445ea5fe631662cd75047`，与本地 `HEAD` 和 `origin/main` 完全一致；`HEAD...origin/main` 为 `0 0`。远端仍提示 required status check `a0-gates` expected，这是分支保护提示，不是本次提交内容的测试通过证明。

## 瘦身范围

### 已删除的旧 Green 候选重复包

以下路径均位于 `.project-local/build/green-candidates/`：

- `ArcheAxis.Knowledge.Green-vclean-archive70226a42-x64` 及 `.zip`
- `ArcheAxis.Knowledge.Green-vclean-core59f6419b-x64` 及 `.zip`
- `ArcheAxis.Knowledge.Green-vlocal-dirty-20260918-x64` 及 `.zip`
- `ArcheAxis.Knowledge.Green-vclean-52fb1d41-x64` 及 `.zip`
- `ArcheAxis.Knowledge.Green-vclean-59f6419b-x64` 及 `.zip`
- `ArcheAxis.Knowledge.Green-vclean-8e2c59be-x64` 及 `.zip`
- `ArcheAxis.Knowledge.Green-vclean-d88c06b4-x64` 及 `.zip`
- `ArcheAxis.Knowledge.Green-vlocal-20260918-x64` 及 `.zip`
- `ArcheAxis.Knowledge.Green-vheadb8bbd16b-x64` 及 `.zip`
- `ArcheAxis.Knowledge.Green-vhead736d20a7-x64.zip`

这是与既有候选存储审计中“保留 `vheadd1bb2b99` 与 `vclean-fc05b0ad`、删除九组旧副本”一致的精确执行。保留项为：

- `.project-local/build/green-candidates/ArcheAxis.Knowledge.Green-vheadd1bb2b99-x64` 及 `.zip`
- `.project-local/build/green-candidates/ArcheAxis.Knowledge.Green-vclean-fc05b0ad-x64` 及 `.zip`
- `.project-local/build/green-candidates-r6/` 下的三组 R6 候选及其 ZIP

### 已删除的中间构建输出

- `.project-local/build/cargo-a04-20260921`
- `.project-local/build/cargo-r6-p5-audit`
- `.project-local/build/cargo-r6-domain-fix`
- `.project-local/build/cargo-r6-domain`
- `.project-local/build/cargo-r6-api-direct2`
- `.project-local/build/cargo-r6-api-direct`
- `.project-local/build/cargo-r6-api-check-direct`
- `.project-local/build/cargo-check-dsh`
- `.project-local/build/asr-sherpa-venv`

这些目录没有被当前受跟踪代码或当前 R6 证据索引作为继续运行所需的唯一输入引用，均可由项目入口重新生成。保留 `.project-local/build/cargo` 主目标、`cargo-r6-p4`、`cargo-r6-api-sdk2`、`cargo-r6-api-fix`、`rust-msvc`、`cargo-r6-a12`、`cargo-current-452b5d0c`、`desktop-publish` 和 R6 候选，因为它们仍出现在当前运行收据或历史证据路径中。

## 体积与外溢审计

只读盘点 `inventory_project.py` 的结果是 `status=partial`：全项目观测 47,725,293,678 bytes、295,772 文件、229 个读取错误、26 个 reparse 跳过、883 个排除项；`.project-local` 观测 44,251,819,839 bytes、261,525 文件。该工具明确把私有/opaque 目录作为不可归因项，不能把它们计入“已清理”。

本轮清理后的 PowerShell 快照显示 `.project-local` 约 31,705,314,672 bytes；这与前一工具的排除规则和时间点不同，不能直接相减归因。唯一可归因的回收量以精确清理收据为准：8,361,939,708 bytes。

`trace_output_producers.py` 产出 1,178 条静态输出路径/变量候选，报告模式为 `read_only_structural_candidates`。它只证明源码和脚本中存在输出意图，不证明运行时已经写入外部目录；进程命令行、日志和私有运行态没有读取。`check_resource_boundaries.py` 退出 0，并确认索引中的五个固定资源路径：Model library、OS External Configuration、ArcheAxis.Knowledge.Green-x64、资料库、ceshi。该检查只读取路径元数据，没有扫描这些库内容。

## 已完成验证与已知限制

- A04 当前提交的 Rust 定向测试：8 passed，退出码 0；包含 `knowledge_v3_projection`、`v01_journey`、`api_closed_loop`。
- `git diff --check` 在生成本报告前无输出。
- 权威 SHA 与 R6 authority 检查在 `9ca805b6` 提交时已通过；本轮尝试重跑时，项目 `.venv\Scripts\python.exe` 是 uv trampoline，进程被权限策略拒绝（`permission denied (os error 5)`），因此本轮重跑状态为 `NOT_EXECUTED`，没有把旧 PASS 冒充成新 PASS。
- 当前 PowerShell 会话的 `python` 不在 PATH；没有安装新解释器，也没有改全局环境。后续应使用已登记的项目解释器或修复执行权限后再跑门禁。
- 推送已完成，远端精确 SHA 回读通过；远端返回的 `a0-gates` expected 规则提示仍需按云端流程补齐检查，不能把推送当成 CI PASS。

## 未完成任务与阻塞

- R6/M0 的 owner-gated 协议与宿主决策仍未闭合；A02/A16 不能由执行者自签。
- A05–A15 仍是部分完成，M0 P3 的真实 Core/桌面 journey 仍受当前二进制与源码契约不一致阻塞。
- R13 的安装器、代码签名、卸载器和干净机器验收仍未完成；候选包不等于正式 Green 发布。
- R14/R16 独立审计仍必须由独立 GPT 按证据逐项裁决，不能使用执行者收据自签通过。
- 未跟踪的 `docs/history/` 迁移资产和私有会话提示未获得逐项入库授权，故本轮保留且不上传。

## 交接与精确提交范围

本报告是唯一计划提交的跟踪文件：

`docs/current/REPOSITORY-CLEANUP-HANDOFF-20260921.md`

`.project-local/audits/` 下的原始盘点、外溢候选、资源边界、低额度监控和清理收据是项目内忽略的运行证据，不随提交上传；报告已记录其精确文件名、统计和限制，供本机复核。

下一位执行者应按以下顺序继续：

1. 先修复项目 Python 入口的权限/解释器发现，再重跑 authority SHA、R6 authority 和必要的定向门禁。
2. 重新尝试 `git ls-remote` 或使用已批准的 HTTPS 远端完成精确 SHA 回读；成功后才报告双端一致。
3. 处理 R6/M0 owner-gated 决策和独立审计，不扩大清理范围。
4. 若再次瘦身，只能引用新的精确路径清单和对应回读收据；不得删除 `.project-local/runs`、未知历史、私有状态、外置库或现有 Green。

状态语义：本报告记录的是 `IMPLEMENTED_LOCAL` 的清理动作、`TESTED_LOCAL` 的既有 A04 收据、`REMOTE_READBACK_BLOCKED` 的当前 SSH 限制，以及仍为 `BLOCKED/UNVERIFIED` 的未完任务；没有把本地删除、提交或候选包宣称成发布、安装或独立审计通过。
