# 任务总账（Master Task Summary）· 2026-09-04

> 会话主线：08-19 → 09-04。HEAD `6eab165`（本地=云端）。本文件是任务汇总索引；每项给状态、证据位置与关键 SHA，细节见指向的既有文档/回执。

## 一、vNext 同仓结构性重启（goal：complete，7 轮，提交 990c1b0..6eab165）

| # | 任务 | 状态 | 证据 |
| --- | --- | --- | --- |
| ① | 治理与契约落仓 | ✅ | PROJECT_CONTRACT / DIRECTORY_AUTHORITY / DECISION_SUPERSESSION_LEDGER / LEGACY_MANIFEST / .project/** / taskpacks/ / docs/authority(vNext 5 决策) / ADR-0001（990c1b0/50d8e75） |
| ② | Rust Core 8 crates | ✅ 全绿 | contracts / store-sqlite(唯一 writer) / domain / api / application / sidecar-protocol / migration / archive；cargo test 15 集成测试 |
| ③ | python worker 隔离 + Avalonia 桌面 | ✅ | services/python-workers/worker_extract.py + api jobs 端点；apps/ArcheAxis.Desktop（.NET 10.0.400 共用库）+ CoreSupervisor spawn/握手/清理（6eab165） |
| ④ | legacy 冻结 + 迁移工具 | ✅ 工具 / ⏳ 真实数据 | LEGACY_MAINTENANCE_ONLY_2026-09-04.md；migration crate（只读导出/JSONL/manifest/零改动测试）；真实 v0.6.14 库 dry-run 待 Owner 数据 |
| ⑤ | v0.1 十二步闭环 | ✅ | journey 全 PASS → reports/vnext/v01-closed-loop-receipt.json；进程级握手（supervisor_launch）；**云端 vnext-ci 绿**（54f23ba/最新 success；含 dotnet build） |

验收判据达成：cargo test 绿 + CI 绿 + exact 收据。状态：reports/vnext/VNEXT_STATUS.md。

## 二、本机管线/验证链（08-19 → 08-20 完成并已归档）

| 任务 | 状态 | 证据 |
| --- | --- | --- |
| 联邦知识 API（TP-20260819） | ✅ | 8 V1 契约+记录端点；E2E-003；迁移试点；reports/current/CONTRACT_CONFORMANCE 等 |
| ceshi 全库测试（22,422 文件） | ✅ 知识类 100% | 文本/PDF66/Office/svg30-31/图片1273/mp4画面64/mp3 14(56,309 字)；AUDIO_FULL_RECEIPT / CESHI_COMPLETENESS_AUDIT |
| 引擎修复与增强 | ✅ | TESSDATA 根因、faster-whisper 内存分块、SenseVoice 34x、fw-CUDA、onnxruntime-gpu、RapidOCR、Web 截图+E2E 3/3 |
| 配置最优审计 / 闭环审计 | ✅ | PIPELINE_CONFIG_AUDIT / CLOSED_LOOP_AUDIT（本地模型全链路可承担） |
| DeepSeek 交叉验证 | ✅ 8/8 | DEEPSEEK_CROSSCHECK_REPORT |
| 桌面发布 R5/R6（legacy 线） | ✅ 至 v0.6.14 | Tauri+安装包（legacy v0.6.14 冻结为迁移基线，勿动） |
| 会话交接 | ✅ | HANDOFF_2026-08-20_session.md |

## 三、当前状态
- HEAD `6eab165` == origin/main（双端一致，工作树干净）；云端 vnext-ci 绿（最新 push 后新 run 自动触发）
- Goal（vNext 全量执行）phase=complete

## 四、未完成 / 门禁（如实，不虚报完成）
| 项 | 门禁 | 触发后动作 |
| --- | --- | --- |
| 真实 v0.6.14 数据迁移 dry-run | Owner 提供 legacy 数据文件 | migration export → reports/vnext/legacy-dryrun-*.json + 人工确认 |
| Avalonia Green 打包 + GUI 桌面验收 | 桌面会话（无头不可验 GUI） | dotnet publish / 打包；人工走查 |
| Supervisor 全生命周期强化（健康轮询/崩溃重启/日志） | 下一产品 slice | 扩 CoreSupervisor |
| worker job 队列 HTTP 化 + 取消语义 | 下一产品 slice | api 扩展 |
| CI 纳入 legacy 回归 / Tauri 构建 | 可选 | workflows |

## 五、关键复现命令
```powershell
# vNext Rust 全套测试（共用库工具链）
cmd /c "call \"D:/All projects/OS External Configuration/10-toolchains/msvc/VC/Auxiliary/Build/vcvars64.bat\" && cd /d D:/All projects/ArcheAxis-Knowledge-OS && cargo test"
# Avalonia 构建
$env:DOTNET_ROOT='D:/All projects/OS External Configuration/10-toolchains/dotnet'; & "$env:DOTNET_ROOT/dotnet.exe" build apps/ArcheAxis.Desktop
# v0.1 收据再生成
$env:VNEXT_RECEIPT_OUT="D:/All projects/ArcheAxis-Knowledge-OS/reports/vnext/v01-closed-loop-receipt.json"; cargo test -p archeaxis-api --test v01_journey
```
