# DeepSeek 交接：真实案例全流程测试包（2026-07-23）

## 文档性质与证据边界

本文归档 DeepSeek 协作线对“真实案例全流程测试包”的交接输入，并以仓库中已验证的测试、CI 与持久化证据更新其状态。

- DeepSeek 的分析/交接意见是审阅输入，不等同于测试已执行。
- 本文只把有实际脚本、测试输出、SQLite readback 或 exact-SHA CI 的事项写为“已验证”。
- 不把旧会话中的通过数当作当前分支的新测试结果；每次后续变更仍须运行自己的 exact-SHA CI。
- 不记录模型凭据、API key、token、真实用户资料或本机运行数据库。

## 已验证的真实案例闭环

历史全流程验证已针对三个真实产品入口建立隔离 SQLite runtime，并在每次操作后读取持久层：

| 来源入口 | 已验证转换 | 持久化/重启证据 | 普通用户边界 |
| --- | --- | --- | --- |
| 普通网页 URL | URL intake → candidate Research | ResearchPackage、Workspace Job、Receipt、Outbox 均落盘；重启后可读回 | DTO 不返回内部 ID |
| GitHub 仓库 URL | GitHub metadata/README → candidate Research | 与 Job/Receipt/Outbox 同事务；严格读回 | DTO 不返回内部 ID |
| 本地文件上传 | 文件 intake → candidate Research | 与 Job/Receipt/Outbox 同事务；重启后可读回 | DTO 不返回内部 ID |

该轮真实 E2E 的计数证据为：

```text
packages=3
jobs=3
outbox=3
receipts=3
invalid_bindings=0
```

重启 readback 后仍可读取三份 `candidate` Research、成功 Job 与 pending Outbox。该事实证明三来源 Workspace intake 的持久化闭环；它不证明 candidate 来源为 verified truth，也不等于“全部知识转化”已完成。

## 当前已进入主线的相关治理能力

当前 `main` 已包含下列与全流程测试直接相关的生产边界：

1. Workspace Research 人工审核队列与不泄露内部 ID 的批准操作。
2. Workspace Outbox dispatcher、Research consumer、receipt-bound delivery 与 lease fencing。
3. Runtime evaluation、trace receipt、durable Sleep Loop lease/heartbeat/retry/review gate。
4. candidate Research、Knowledge/Learning/Machine Knowledge 的审批与 approved-only 读取边界。
5. A0 Chromium、fresh-wheel、Windows runtime、desktop shell/NSIS 生命周期与 aggregate CI 门禁。

近期本地完整 Python 回归曾在合并前执行为：

```text
662 passed, 2 skipped
```

这只是当时的本地验证记录；下一次代码变更必须重新执行定向门禁、完整测试和新 exact-SHA CI。

## 当前缺口：尚未形成“全部知识转化”的统一受管测试包

DeepSeek 交接正确指出：三来源 intake E2E 不能被命名为覆盖所有知识转化的测试包。以下能力尚未由一份受 Git 管理、可重复执行、带覆盖矩阵的统一 runner 端到端覆盖：

| 转化链路 | 已有局部合同/测试 | 统一真实案例包状态 |
| --- | --- | --- |
| URL / GitHub / 文件 → candidate Research | 已有真实三来源 E2E | 已覆盖基础闭环 |
| Research → 人工审核 → Knowledge 候选 | 有治理合同与 Research 审核 UI | 缺少统一 E2E 组合 |
| Knowledge → Learning / Practice | 有局部审批、幂等和投影测试 | 缺少统一 E2E 组合 |
| Learning → Machine Knowledge → Runtime approved-only 读取 | 有合同与持久化边界 | 缺少统一 E2E 组合 |
| 媒体 → 音轨 / 关键帧 / OCR Evidence | 有媒体基础链与定向测试 | ASR、时间戳、语义内容匹配和人工真值未闭环 |
| TaskPack → Permission → Tool Evidence → Evaluation → Lesson | 有受限真实 `read file:` 纵向切片 | 缺少与知识生命周期组合的用户案例 |
| Outbox → dispatcher/consumer → receipt/replay | 有 dispatcher、consumer、lease/receipt 合同 | 需要纳入统一重启、重复投递与损坏 fail-closed 案例 |

## 下一步：受管全流程测试包的完成条件

不要提交 `.hermes/task-runtime` 中的一次性脚本作为产品测试包。应在受 Git 管理的位置建立清晰的能力矩阵与 runner，并至少覆盖：

1. 确定性的本地 fixture，禁止依赖不稳定公网或真实用户内容。
2. 每条已实现转化链路的输入、持久化对象、投影、人工治理状态和输出证据。
3. 幂等 replay、冲突 replay、损坏记录、拒绝/审批路径与 fail-closed 断言。
4. 进程重启后的 SQLite readback、Outbox/Receipt/Job 一致性。
5. 普通用户 DTO/UI 的内部标识泄露扫描。
6. 结构化结果：覆盖的链路、请求/状态、读回计数、重放一致性、失败路径与未覆盖能力；不输出伪 KPI。
7. 跑完后依序执行相关 Root/KB/Integration/Ruff/Architecture、浏览器、fresh-wheel、Windows/Desktop 门禁，并以新 exact-SHA CI 作为最终结论。

## 当前真实结论

- 已有：真实三来源 Workspace intake → Research/Job/Receipt/Outbox → 重启读回闭环。
- 已有：桌面 Windows 壳、浏览器和运行时治理门禁的真实验证。
- 未有：覆盖所有已实现知识转化的、单一受管统一全流程测试包。
- 未有：ASR、媒体时间戳、语义内容匹配 Evidence 与人工真值准确率闭环。
- 不可宣称：candidate 自动成为 verified truth、完整公开产品发布或严格数据 portable release。

## 关联记录

- [`docs/HANDOFF_2026-07-23.md`](HANDOFF_2026-07-23.md)
- [`workspace/intake/2026-07-23-desktop-shell-portable-acceptance.md`](../workspace/intake/2026-07-23-desktop-shell-portable-acceptance.md)
- `scripts/a0_browser_smoke.py`
- `desktop/scripts/verify_nsis_install.ps1`
