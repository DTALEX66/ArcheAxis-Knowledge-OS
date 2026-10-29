# Owner 决策清单（ZCODE 通宵后端闭环 2026-10-30）

通宵执行完成度与全部证据见[同目录完成报告](ZCODE-完成报告.md)。以下两项决策**只有 Owner 能做**，每项给出精确背景、解锁范围、可选项与不做时的如实状态。决策后按已有工单机械执行，无需新的探索。

## 决策一：安装器版本号提升 → 解锁真跨版本升级/回滚

- **现状**：安装器版本标签 `0.6.14` 来自冻结的 `src-tauri/tauri.conf.json`；backend staging manifest 已声明 `0.6.15`（两处身份分别记录）。生命周期回执如实登记 `cross_version_upgrade='NOT_TESTED'`、`rollback='NOT_TESTED'`。
- **解锁**：旧包（`53a83f20…`，v7 链）→ 新版本包安装 → 数据保全断言 → 回滚断言，复用 zc1i2 同一沙盒链与 mixed-core 资格链。
- **选项**：
  - **A（推荐）**：`tauri.conf.json` version 提升到 `0.6.15` 并提交（一行配置变更，走一次评审），随后：重跑打包链（`bundle-mixed-v6.py`，request 输出新安装器身份）→ 沙盒升级/回滚旅程（zc1i2 驱动变体 + 升级断言）。
  - **B**：维持 0.6.14 → 跨版本继续 NOT_TESTED 如实登记；同版本重装数据保全路径保持已验证状态（`SAME_INSTALLER_SAME_VERSION_REINSTALL_DATA_PRESERVATION`）。
- **不做 A 的后果**：CL-07/J6 的跨版本维度保持 NOT_TESTED，不阻塞其余已完成后端切片。

## 决策二：LM Studio 监听地址 → 解锁安装态 AI 旅程

- **现状**：宿主 LM Studio 只监听 `127.0.0.1:1234`；Windows Sandbox guest 不可达。v7 与本轮的安装态 AI 旅程均因此如实 `NOT_EXECUTED`。宿主级 REAL_MODEL 证据已成立（colearning 冒烟 PASS、v3 dual-loop PASS）。
- **解锁**：guest 内对已安装产品跑真实本地模型 AI 旅程（answer→超界失败→纠正→retest→重启读回）。
- **选项**：
  - **A**：LM Studio 改绑 `0.0.0.0`（或宿主 vEthernet 地址）——属宿主模型服务配置变更，由 Owner 自行操作或明确授权；同时需要**子决策 A2**：允许沙盒 wsb 模板开启 Networking（当前 `Disable` 是本轮离线边界）或改用 Host-only 网络适配。此后 guest 用宿主地址调 `/v1`，按 zc1i2 链新增 AI 旅程变体。
  - **B**：不改 → 安装态 AI 保持 NOT_EXECUTED；AI 链证据层继续由宿主级 REAL_MODEL 收据承载，不冒充安装态。
- **不做 A 的后果**：CL-06/J4 的安装态维度保持 NOT_EXECUTED；本地真实模型链的宿主级证据不受影响。

## 无需决策即可继续（工单已就绪）

1. **安装态冲突旅程（guest 内）**：候选层已 PASS（`conflict_journey_20261030`，REAL_TAURI_WEBDRIVER_CANDIDATE）；guest 内变体被 harness 的 dev.py/git 证据要求阻断——可按 v7 cpppdfexec1 模式设计"guest 内第二旅程 run"（staging 一个允许写入的 run 工作目录变体），设计要点已入 `evidence-index.json` 的 `conflict_journey_next_session_workplan`。
2. **剩余 142 条非门禁 clippy 债务**：有评审的清理轮（含 too_many_arguments 等设计级项），不阻塞任何旅程。
3. **刷新实测外置索引**：`scripts/environment/build_external_resources_index.py`（可选）。

## Codex 独立审计入口

- 主文档：[ZCODE-完成报告.md](ZCODE-完成报告.md)（§1 身份、§3 修复与诊断、§4.0a-d 四轮增量、§5 延期清单、§6 审计入口、§8 后继最短路径）。
- 机器可读证据索引：[evidence-index.json](evidence-index.json)（全部 run 的 execution.json SHA、安装器/生命周期/冲突旅程回执 SHA、具名诊断与工单）。
- 唯一执行记录：`docs/current/AAOS-UI-FIRST-EXECUTION-20261009.md` 末段五个 dated 小节（续轮一至五）。
- 已知失败与保留：zc1i 首跑前端就绪超时（冷启动方差判定）、zc1r 六次 review 尝试、bundle 长路径首败、INVALIDATED 机制 run——全部原样保留。
- 审计边界提醒：证据层（源码级/候选层 REAL_CORE/REAL_MODEL/安装态）不得互相晋升；CI 记 `NOT_EXECUTED_BY_OWNER_LOCAL_ONLY_BOUNDARY`；Mimosa hook 报告 commit 前 `scanner_no_output`，未做项目安全宣称。
