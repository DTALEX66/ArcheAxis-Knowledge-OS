# AXR v0.6.0 最小闭环完成度审计（2026-08-23）

整体结论：PARTIAL

RELEASE_PUBLISHED：PASS

公开 `v0.6.8` Release、精确 SHA CI、三种分发资产及下载读回已经通过；这不等于原任务包的 24 个产品任务和 12 个发布阻断项全部关闭。本文只把生产实现、当前本地执行、精确 SHA CI、公开发布和安装运行时证据分别计级。

## 证据快照

- 公开发布证据：`reports/release/v0.6.8/release-evidence.json`，绑定提交 `93e58a3b2c537dd348903dd2296933e0cfb5a503`、CI `32607097436`、Release run `32607789507` 和 9 个读回资产。
- 当前隔离 worktree 的全量 Python 门禁：1977 passed、7 skipped；覆盖 `tests/` 与 `knowledge_base/tests/`，包括四库、迁移、RawAsset、Conversion、联邦审核、双主体写入、Supervisor、安全、导出与备份。
- 当前前端门禁：Vitest 25 passed；TypeScript 与 Vite production build PASS。
- 当前 Rust/Tauri 门禁：14 passed；`cargo-fmt` check PASS。
- v0.6.8 候选 Golden Journey Receipt：PASS_LOCAL；在干净 PR head `74ca553` 上生成，overall 为 PARTIAL 仅因安装版/Tier A 长矩阵仍未纳入同一 receipt。
- 当前六空间 Chromium 点击级联调：PASS_LOCAL；以 Tauri origin、真实 launch token 和真实后端依次读回 Workspace、Library、Evidence、Learning、AI Assets、Settings，控制台 0 error / 0 warning。
- v0.6.8 发布提交 exact-SHA CI：PASS；main 合并提交 `93e58a3b2c537dd348903dd2296933e0cfb5a503` 的 run `32607097436` 全绿。

## M0–M7 任务矩阵

| 任务 | 状态 | 已验证证据 | 未关闭范围 |
| --- | --- | --- | --- |
| AXR-060-001 | PASS_RELEASE | 当前报告生成器已分离 source/release 层、拒绝脏树伪装 exact SHA；陈旧的三份 tracked current JSON 已移除，并在干净候选 SHA 上生成报告与 Golden receipt。 | 后续每个版本继续只在干净 SHA 上生成。 |
| AXR-060-002 | PASS_SOURCE | `docs/architecture/ADR-060-001-IMPLEMENTATION-LINE.md` 和 `docs/SYSTEM_BOUNDARY.md` 固定 `frontend/ + src-tauri/` 为规范线；发布工作流从该线构建。 | 旧线仅在等价能力完成后退役。 |
| AXR-060-003 | PASS_RELEASE | 源码版本面、tag、精确 SHA CI、公开 Release 和 9 资产读回均已统一为 `v0.6.8`。 | 兼容入口继续保持只读迁移边界。 |
| AXR-060-101 | PASS_LOCAL | setup/manifest/R1 定向测试通过：quick、advanced、四域、重复/嵌套拒绝、无权限失败和重启回读。 | UI 健康信息仍归下一项。 |
| AXR-060-102 | PASS_LOCAL | dry-run、备份、迁移、哈希回读、幂等、回滚候选测试通过。 | 真实跨卷 move 与只读介质人工验证尚未单独取证。 |
| AXR-060-103 | PARTIAL | Settings 消费真实 setup status/init API。 | 当前仍是初始化按钮加键值表，不是欢迎→模式→路径卡→健康→完成的完整首次启动流程。 |
| AXR-060-201 | PASS_LOCAL | RawAsset 测试证明先持久化完整 SHA-256、不可变原件、失败 receipt 和转换失败不丢原件。 | 干净安装运行时需并入最终完整旅程。 |
| AXR-060-202 | PARTIAL | ConversionRun 合同、Golden PDF 页锚点、LossReport 和多格式单元测试通过。 | Tier A 全格式矩阵、结构金标准与 nightly 完整执行为 `NOT_EXECUTED_CURRENT_SHA`。 |
| AXR-060-203 | PARTIAL | 仓库已有 raw-first Web 摄取与回归资产。 | 本轮未在当前 worktree 实跑“单次抓取同时产出 raw snapshot 和抽取结果”的网络隔离证据。 |
| AXR-060-204 | PASS_RELEASE | 发布包从锁定依赖和 bundled runtime 启动；公开身份绑定依赖锁；源码硬编码扫描未发现活动发布依赖的开发机绝对路径。 | 开发文档中的外置工具链路径保留为开发说明，不是安装依赖。 |
| AXR-060-301 | PASS_LOCAL | 严格 ReviewDecision、token/actor/scope、乐观版本、幂等和越权拒绝的定向测试通过。 | 仍需保持所有未来写路由沿用同一 guard。 |
| AXR-060-302 | PARTIAL | 联邦审核事件、学习审批 receipt、弃用/撤销路径具备 append-only 测试。 | 尚缺覆盖 Evidence/Learning/Provenance/Rights 全部表的静态 SQL 白名单和完整迁移回滚矩阵。 |
| AXR-060-303 | PARTIAL | Bundle 支持支持/反驳关系、冲突检测和 caller-supplied 禁止自升 verified。 | 来源独立性、时效、范围、rights、not_verifiable 的统一持久合同未完整闭环。 |
| AXR-060-304 | PASS_LOCAL | 生产服务从同一已审核链生成学习卡/复习与受治理机器知识；主链、学习投影和机器知识范围测试通过。 | 安装版 UI 操作证据仍归六空间/Golden Journey。 |
| AXR-060-401 | PARTIAL | 统一 handshake client 验证 product/API/runtime，launch token 保留在闭包内；前端单测通过。 | 写操作的 scope/幂等键和完整迁移/离线统一投影尚未覆盖全部 API。 |
| AXR-060-402 | PASS_LOCAL | 六空间均接真实 API：Workspace 状态/活动、Library 原件读回、Evidence 研究审批、Learning 学习闭环、AI 资产审批/弃用、Settings 初始化/备份校验；Vitest 与真实 Chromium 联调通过。 | 正式安装包中的同一操作序列仍归分发生命周期任务。 |
| AXR-060-403 | PARTIAL | Inspector 显示来源/状态/hash/详情；Dock 读取真实 Job/Outbox/Receipt 数量。 | 缺冲突/rights/完整版本历史，以及取消、重试、错误详情操作。 |
| AXR-060-404 | PARTIAL_BROWSER | Vitest 25 passed、typecheck/build PASS；Tauri-origin Chromium 六空间真实后端联调通过且控制台无错误。 | 键盘、焦点、读屏、高 DPI、分页和 reduced-motion 的完整矩阵尚未在发布安装包中执行。 |
| AXR-060-501 | PASS_RELEASE | 根 Tauri 移植 Supervisor，随机 loopback/token、启动/重启/退出清理测试及公开分发生命周期通过。 | External Dev 的人工可见标识仍需同六空间 E2E 复核。 |
| AXR-060-502 | PARTIAL | Core 启动失败时 Shell 保活并支持 retry，Recovery 合同测试通过。 | 缺脱敏日志查看、安全模式、备份恢复和显式退出的完整恢复界面。 |
| AXR-060-503 | PARTIAL | 非 null 限制型 CSP、loopback CORS、token 内存传递和窗口关闭清理有测试。 | 日志正文/私人路径静态扫描、外链/下载策略及卸载四库保全需完整运行时证明。 |
| AXR-060-601 | PASS_LOCAL | Export/Backup 的 hash 验证、篡改拒绝、fresh four-library import readback、restore receipt 测试通过。 | 最终安装版 Golden Journey 尚未把该操作串进同一证据包。 |
| AXR-060-602 | PASS_LOCAL | 旧库备份、dry-run、迁移、记录回读、幂等和回滚候选测试通过。 | 真实用户旧数据集迁移仍需独立授权数据和人工验收。 |
| AXR-060-603 | PASS_RELEASE | Setup/Green/Portable 与 wheel、identity、manifest、SBOM、notices、checksums 来自同一 tag/SHA，9 资产下载读回通过。 | 无。 |
| AXR-060-604 | PARTIAL | 三种分发各自生命周期在 CI/Release 中通过。 | 未在同一干净 Windows 环境串行执行“四库→完整 Golden Journey→升级→卸载保留→重装回读”。 |
| AXR-060-701 | PARTIAL | Python 全量、前端单测/build、真实 Chromium、Windows runtime staging、Rust/Tauri 本地门禁及 v0.6.8 exact-SHA CI 已通过；CI GatePlan/ci-verdict 保持 fail-closed。 | nightly 全格式矩阵仍独立保留。 |
| AXR-060-702 | PASS_RELEASE | Tag=main exact SHA、先验 CI、锁绑定候选、checksum/identity/SBOM/notices、草稿读回后发布均在 v0.6.8 成功。 | ruleset 管理状态仍应周期复核。 |
| AXR-060-703 | PARTIAL | 稳定发布前实际经历多个不可改写修复标签和 exact-SHA 门禁。 | alpha/beta/RC 所对应的六空间、Supervisor、完整干净机清单没有统一 RC receipt。 |
| AXR-060-704 | PARTIAL | Release Ledger、公开 Release、checksums、exact commit 和已知边界有文档。 | 面向用户的 Tier A 明细、v0.5.0 升级步骤、卸载保留和回滚操作说明仍需汇总到正式 Release Notes。 |

## 12 个发布阻断项

| 阻断 | 状态 | 结论 |
| --- | --- | --- |
| B01 | CLOSED_LOCAL | 四库由用户根或四个高级路径决定，Manifest 可重启回读。 |
| B02 | CLOSED_LOCAL | 转换前保存完整 SHA-256 原件，失败不覆盖/丢失原件。 |
| B03 | CLOSED_LOCAL | 未授权审核被 token/actor/scope/state/version 门禁拒绝。 |
| B04 | OPEN_PARTIAL | 关键审核/学习事件有 append-only 证据，但尚无四类账本全 SQL 静态白名单。 |
| B05 | CLOSED_LOCAL | Human/AI 结果由生产写入器从同一审核链生成，不是测试手写结果。 |
| B06 | CLOSED_LOCAL | Library 原件读回、Evidence 审批、AI 资产审批/弃用、Workspace/Activity、Settings 初始化与备份校验均接真实 API，并完成 Tauri-origin Chromium 联调。 |
| B07 | CLOSED_RELEASE | 根 Tauri 启动/监督后端且 CSP 非 null，测试与发布生命周期均有证据。 |
| B08 | CLOSED_RELEASE | 安装版使用 bundled runtime；外置开发工具链不是正式运行依赖。 |
| B09 | CLOSED_RELEASE | Setup/Green/Portable 由同一发布工作流、同一源码 SHA 和锁集合生成。 |
| B10 | OPEN_BLOCKER | 尚未在一台干净 Windows 环境完成完整 Golden Journey、升级/卸载保留和导出回读的串行证据。 |
| B11 | CLOSED_RELEASE | 发布事实与产品能力已分层；v0.6.8 干净 SHA 报告、公开 Release receipt 和独立资产读回均已完成。 |
| B12 | CLOSED_RELEASE | v0.6.8 main 发布 SHA `93e58a3b2c537dd348903dd2296933e0cfb5a503` 的必需 CI run `32607097436` 已绿。 |

## 下一执行序列

1. 补齐 Recovery Shell 的脱敏日志、安全模式、备份恢复与显式退出闭环。
2. 在干净 Windows 环境把四库、完整 Golden Journey、升级、卸载保留、重装与导出读回串入同一 receipt。
3. 完成键盘、读屏、高 DPI、分页、reduced-motion 与 Tier A 全格式矩阵。
4. 评估 Release 阶段重复执行约 11 分钟 NSIS 构建的身份注入约束；只有在不削弱安装包身份绑定与生命周期门禁时才复用 CI 候选。
