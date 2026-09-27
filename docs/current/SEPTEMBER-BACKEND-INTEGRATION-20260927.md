# 9 月权威规划下的后端分支整合

依据：Configuration Authority Index → R6 → M0/SUP-020 → SUP-021。
本轮 Owner 已授权修复、提交、推送、合并与分支清理；正式前端任务不变。
本文件是执行记录，不是新 Authority，不签发真实 M0 或 Local Green 资格。

## 分支处置依据

整合起点：`origin/main = 43c2cafa1bfe57a862e90c5a77dc16832264babd`。

| 分支 | 处置与证据 |
| --- | --- |
| dsh/backend-r5 | 纳入 15 个后端提交；包含 backend-20260927 的 13 个提交；修复审计问题后统一验收 |
| dsh/governance-drift-alignment-20260927 | 纳入 3 个文档提交；补充 vNext receipt v3 与 root fmt 已落地的时点校正 |
| dsh/backend-audit-20260927 | 与起点 main 相同，无独有改动 |
| codex/dp-f01-20260925 | 2 个提交均 patch-equivalent；merge-tree 与 main 一致，已吸收 |
| codex/worker-quality-0906 | main 的祖先，已吸收 |
| codex/execution-reliability-standards | 2 个提交、8 路径；exact-SHA、证据层级和清理归属已在当前规则；旧 .hermes 输出根已由 .project-local 取代。原内容完整保留于 bundle |
| codex/frozen-roadmap-deepseek-v1 | 149 个独有提交，tip diff 137 路径：4 同 blob、15 当前不同、118 独有历史资料。不能声称全部吸收。3 个代码路径仅维护旧文档 hash/行号/测试，旧 Authority 已 superseded；历史原件保留于 bundle，不恢复旧执行路线 |
| docs/verification-summary-2026-08-09 | 单个 289 行历史核验文档；不是当前运行证据，保留于 bundle |
| feat/naming-step3 | 后端 ARCHEAXIS/COGNITIVE 兼容及 API alias 已在主线；旧 Tauri 身份由 NAMING_V2/SUP-021 取代，不迁回 UI |
| release/v0.4.0-contract | 4 提交含 merge；5f66f710 patch-equivalent；当前已有 payload allowlist/checksum/readback，旧 release 路线已冻结，旧 inspector 动画 selector 已不存在。保留历史，不触发发布 |
| codex/Audit、codex/aaos-p3-ui-convergence-20260922 | 活跃任务保护，不移动、不删除、不覆盖前端修改 |

## 可恢复性与清理边界

清理前 bundle：主检出 `.project-local/runs/4260083704/refs/artifacts/pre-cleanup.bundle`。
包含 24 个本地/远端 refs 的完整历史，`git bundle verify` 成功。
SHA-256：`8cd7cc526e0d4d15a33a94458e532a1ef72efe7e80bf68a19144c592fa89619e`。
恢复某分支可从该 bundle fetch 对应 `refs/heads/...` 或 `refs/remotes/origin/...`
到新 `refs/heads/recovery/...`。不依赖已删除远端 ref 来找回历史。

现有前端 checkout、未跟踪 `docs/history/**`、旧 worktree 内未分类输出和
外部 Green 数据均保留。分支 ref 退休不等于删除 checkout、用户数据或原始资料。

`worker-quality-0906` 有 6 个 tracked 修改、11 个 untracked 源码/测试文件。
逐文件核对发现相关功能均已在主线吸收或扩展，没有必须倒迁的后端遗漏。
17 个原件另存 `.project-local/runs/4260083704/worker-preserve/artifacts/worker-quality-dirty/`，
包含 tracked.patch 与逐文件 SHA-256 manifest，并逐个对比副本 hash。
manifest SHA-256：`c71d7f07fac8bcb39928d648068622451c986d7eb00461f03d3e11806e780965`。
原 dirty worktree 及其本地分支继续保留，不把备份当作删除授权。

## 修复范围

- M0 探针校验完整阶段、搜索归属、correction/retest 身份、重启状态与备份恢复；
  显式标记 SYNTHETIC，不能冒充真实模型/真人闭环。
- 启动器不在公开收据输出身份令牌；就绪等待有截止时间并消费双流、回收自有子进程。
- Python/Rust worker profile 按既有四字段契约拒绝畸形字段和受保护/链接路径；
  打包预检拒绝祖先与嵌套 reparse，避免复制越界。
- linked worktree 使用 canonical common-dir `.project-local` 开发根；
  Windows browser profile 清理处理自有进程退出后的短暂锁。
- 后端打包路径纳入 vNext 风险 gate，校正文档中的过期源码/收据描述。

## 验收状态

TESTED_LOCAL：整合 Python 主集 `tests integration-tests knowledge_base/tests`：
3513 passed、35 skipped、137 subtests passed；skip 不计通过。
补充启动器/探针/Windows runner/开发路径回归：122 passed、1 skipped、9 subtests。
Rust `cargo test --workspace --offline`、根 workspace fmt、vNext current-run
journey receipt、真实 workers、contracts、architecture、language boundaries、
R6 authority、repository/path conventions 与 CI Ruff 均通过。
词汇生成检查在逐文件 hash 一致的公共输入副本上通过（native worktree 的
`.codex` 祖先被生成器正确拒绝）；没有放开 private-path 规则。

独立审查发现并复核关闭：untracked identity 跟随链接读取、packager identity
遗漏 launcher 两项；初次全套失败的 worktree fixtures 与 browser cleanup
已修复并完成上述最终全套。现有主检出前端文件 SHA-256 仍为
`c2a8dcdc4fc508691db5dca6ea5e45c70a81a3451451cdb5aaaec8e59da748c2d`；
整合相对 main 的 apps/ArcheAxis.Desktop、frontend、desktop、src-tauri diff 为空。

exact-SHA CI、合并与 ref 退休尚待远端执行 readback；本提交不提前声称成功。
没有发布新版本、替换 Green 或将真实 M0 缺口改成 PASS。
