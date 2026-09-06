# ArcheAxis 2026-09-06 执行摘要与接续交接

本文件是执行记录，不覆盖 `AGENTS.md`、`PROJECT_CONTRACT.yaml` 和
`DECISION_SUPERSESSION_LEDGER.yaml` 的权威。**全量目标未完成。**
不要因为有本地测试或已上传分支而声称新版界面、全格式管线已经交付。

## 范围与停止条件

- 当前项目：`D:\All projects\ArcheAxis-Knowledge-OS`；不是 WORK-LAB。
- 已批准任务包：`D:\All projects\ARCHEAXIS-UPDATED-FULL-LOOP-TASKPACK-2026-09-06.zip`，
  r1；25 个成员的哈希已在初始接收时核验。冻结 `TASKS.json` 的 SHA-256：
  `1aa5c17c94f8c279987b5f4c70777e25d3614b6419fda65fd351abf71ff6bc94`。
- 正式路线：C#/Avalonia 桌面、Rust 独立 vNext 数据库、隔离 Python worker。
  React/Tauri/旧 Python 系统是能力复用和恢复参考，不是同时开发的第二正式界面。
- 保留现有 `D:\All projects\ArcheAxis.Knowledge.Green-x64` v0.6.14 及数据；不发布
  新产品版本、标签或 Release，不替换绿色版，不访问 E 盘。
- 用户要求：账户剩余额度到 20% 时停止开发，只做总结、交接、上传与读回。
  观察到的是账户用量窗口，不是精确上下文 token；没有兑换 usage reset。
  收尾时工具实测 usedPercent=80（剩余 20%），已停止功能开发；下一次开发需用户明确恢复。

## 重载入口与工具边界

依次读根 `AGENTS.md`、`docs/CONFIGURATION_AUTHORITY_INDEX.md`、
`docs/LANGUAGE_BOUNDARY_AUTHORITY_INDEX.md`、`docs/DIRECTORY_AUTHORITY_INDEX.md`、
本目录 `EXECUTION.md` 和冻结 `TASKS.json`。旧摘要不覆盖 0906 决策。

- 单 writer 分支：`codex/full-loop-0906`。先 `git status --short`，保留未知修改。
- PowerShell 7：`C:\Program Files\PowerShell\7\pwsh.exe`。
- 工具共用库：`D:\All projects\OS External Configuration\10-toolchains`；Cargo/Rustup、
  MSVC、.NET 从这里复用。.NET 10.0.400；Rust/Cargo 1.97.1。
- Python：项目 `.venv\Scripts\python.exe`，3.13.14；不要让 `dev.py -- python`
  意外选到缺依赖的全局解释器。通过 `dev.py --pytest` 或显式解释器运行。
- 模型库：`D:\All projects\Model library`；测试资料副本：`D:\All projects\ceshi`。
  本地模型优先，GPT 仅辅助审计；不能把配置名称当作实际可用能力。
- 开发产物统一经 `scripts/runtime/dev.py` 写入 ignored `.project-local/`，按 worktree/run
  隔离。`.hermes` 是保留的旧混合材料；不新增写入，不扫描私密状态，不整体删除。
- 外置库不是项目；不改 WORK-LAB、全局 Codex/Hermes 配置、凭据或模型库文件。

## 已验证的实际进展

1. 原件 CAS 保留、单连接 writer actor/跨进程锁、数据库版本保护、输出事务与导出恢复。
2. 完整 LossReceipt、跨语言词汇单源生成、真实文本字节/Unicode/截断损失与 CER/WER 工具测试。
3. 真实 Python NDJSON 文本 worker；Rust 校验 hello、请求/attempt、状态、输出 SHA、结构、
   损失回执后写入。三个完整输出落库，重启和 archive 恢复后可读、可幂等重放。
4. Core 启动凭据通过私有 stdin 管道传入，所有生产 HTTP 路由鉴权；绑定实际 Store 路径、
   session、版本。拒绝错误工作区、重定向、旧 token；C# Stop 与成功发布的竞态已修复。
5. HTTP 真实文本执行：持久 claim 后 202、状态/结果读回、按 attempt 取消、重复请求保护、
   两个活跃 worker 上限。C# 静默客户端到 Rust、Python、数据库读回的真实链路已通过。
6. writer 队列满载不再丢弃已接受回调；不可恢复终态写入保留故障状态/503，不把失去执行者的
   running 当成正常重放。准入等待不锁住取消注册表。详细 RED/GREEN 和局部限制见 EXECUTION。

关键本地证据（`.project-local/runs/be268a2d33/` 下，原始运行日志不上传）：

| 证据 | 结果 |
|---|---|
| `1947625d8f22` | API/application/Store/archive Rust 聚合 PASS；包含真实 worker 与导出恢复 |
| `7664b552a9fc` | 最终 HTTP runtime 5 项测试 PASS，包括取消、过载、故障重放和断开客户端 |
| `03d6b700515a` | 最终候选 C# 无 GUI 真实链路 PASS；停止竞态和 8.3 情况均未跳过 |
| `d9024ec5cfa9` | 合同测试 17 PASS，4 个既有 jsonschema 弃用警告 |
| `93cc316ebf75` | 架构门禁 PASS |
| `d5c9d363e5aa` | 改动 Python 文件定向 Ruff PASS |

这些是改动树本地验证，不是 exact-SHA 云端 CI，更不是安装态全格式验收。
Avalonia 仍有 starter 内容；**不要打开新 GUI 给用户当作“已可用产品”。**

## 全量后续任务链（不能缩水）

| 任务 | 状态与下一证据 |
|---|---|
| T00/T19 | PARTIAL；完成基线接收和残余旧固定路径入口收敛 |
| T01/T02 | PARTIAL；CI 去重、完整 DTO/权限/角色/anchor 与版本协商 |
| T03/T04 | PARTIAL；维护 API 封装、故障恢复、OS 进程树/内存预算、公平准入、自动重启与其他 worker |
| T17 | PARTIAL；已有 11 类旧能力差距清单，逐项复用并做非空行为验证 |
| T05/T06/T07 | PARTIAL；PDF 之外的 Office/网页/截图/图像/媒体/Canvas 等全链路，OCR/ASR/本地模型、真实语料精度与损失 |
| T08/T09 | PLANNED；研究来源、可信知识、证据绑定与撤销 |
| T10/T11 | PLANNED；人类重型学习、FSRS/掌握反馈、机器知识评估与撤销 |
| T18/T12 | PLANNED；吸收既有 UI/LOGO/设计材料，落实黑白主题、动效/交互/键盘/可访问性，接实际 Core |
| T13/T14 | PLANNED；非空旧库迁移、附件/关系/学习历史保护与目录/索引闭环 |
| T15/T16 | PLANNED；同一候选 Windows 安装态全链路资格与可逆交付；不自行发新版本 |
| T20 | PARTIAL；精确盘点、保留证明、重建证明后再处理缓存和归档；禁止按目录大小盲删 |

下一步优先把 T04 的进程树隔离/退出回收补上，再逐个启用真实多格式 worker；同时遵循
T18 既有设计证据推进实际 Avalonia 工作台。不要继续无限扩写治理文件来代替功能。
完整验收依然以原 21 项任务及其依赖为准，不以上表的简写取代任务正文。

## 已知限制与复发速查

- 文本 input CAS 当前先全量读入再做 16 MiB 上限，不能声称完整内存预算已实现。
- worker 超时不包括准入/Store 排队时间；只回收自有直接文本子进程。OCR/媒体启用前必须
  证明后代继承管道不会让 join 永久等待、父进程崩溃不会留下孤儿。
- 终态存储不可写/actor Closed：报告 503，保留证据，先修存储原因，再重启 Core 触发恢复。
  不通过改 state 或插入手工 receipt 伪造成功；生产 `/receipts` 已禁。
- UI/CSS/启动路径历史问题：先确定当前正式入口及其加载路径，不凭某份旧截图重新配色。
- Shell 错误不是产品回归；PowerShell 使用显式 Git refs 和引号，不裸写 `@{...}`。
- .NET harness 一次变量名冲突已纠正；老合同测试仍断言 bearer 已更新为实际自定义头，
  不是降低校验。原 Rust unused 与 jsonschema deprecation 警告没有隐藏。
- T20 盘点仅已获准范围：19,676,885,323 logical bytes、113646 路径、30 排除、2 reparse、
  4 WinError3。不是完整仓库总量或可释放空间；未删除项目/用户数据，也未证明全面瘦身。
- 独立 worker worktree `.project-local/worktrees/worker-quality-0906` 有旧的已集成修改，保留。
  不整树复制覆盖主库，不 reset/clean 它。子代理目前只读/已完成，没有并行写主库。

## 仓库交付状态

本地工作分支 `codex/full-loop-0906`；云端仓库已核实为
`DTALEX66/ArcheAxis-Knowledge-OS`，当前 origin 使用 SSH，文档中的 HTTPS 是公共地址，
本次没有修改 remote 或读取认证文件。收尾 fetch 读回 `origin/main`：
`4ca46eaf94c486dadcf200aac6b41cd968b1ce6e`。

实现 checkpoint：`b5a0840a926b826d249ef2a8c4e320ad6436fcca`，tree
`c6a30d98c8f4f7ba6377d7ccc08a9cd50b01697e`。已推送后重新 fetch，确认当时
本地 `codex/full-loop-0906` 与 `origin/codex/full-loop-0906` 均为该 SHA，差异 0/0。
本地 `main` 与 `origin/main` 都仍是上述 `4ca46ea...`；**没有合并 main**。

该源代码 SHA 触发了 [vnext-ci 34024333839](https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/actions/runs/34024333839)，
首次读回为 `in_progress`；最终读回为 `completed/success`，`cargo-test` 成功，
`headSha` 精确匹配上述源代码 checkpoint。完整项目 CI、安装态/全格式资格均未由此证明。
本交接的后续收尾提交仅更新文档；最终工作分支 HEAD 应再次按完整 SHA 读回。
不要把文档提交的 SHA 与源代码 checkpoint 的 CI 结果混为同一 SHA。

没有新 PR、tag、Release 或 Green 更新。源码和交接已纳入工作分支；ignored 原始日志、
模型、学习资料、私人配置和旧混合目录没有上传。仓库工作树干净不等于 T20 全面瘦身完成。
