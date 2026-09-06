# HANDOFF — T04 任务执行器、模型能力与 Supervisor（CODEX）

交接人：DeepSeek（集成者）· 日期：2026-09-05 · 难度：高 · 目标代理：CODEX

## 目标
真实 worker 运行链与进程治理，验收：
- 真实启动 worker 并验证输入/输出、attempt、哈希、超时、取消和幂等；
- 能力发现/模型 profile/队列资源预算；启动目录、token、workspace 身份与日志清理；
- 只把通过能力探针的模型与格式显示为可用；
- 重复回写一份结果；错误结果不会留下 completed；占端口、无输出、worker 崩溃可恢复；
  窗口关闭无遗留子进程。

## 现状与上下文
- crates/archeaxis-application/src/jobs.rs 与 runtime/** 骨架、crates/archeaxis-api/src/runtime/** 已存在
  （v01 journey 12 步通过；cargo test 全绿于 2bae648）。
- apps/ArcheAxis.Desktop/CoreSupervisor.cs 已实现 spawn/readiness/handshake/Stop（进程树清理），
  Program.cs 有 --smoke 无头模式；CI 步骤已验：dotnet build + cargo build -p archeaxis-api + dotnet run -- --smoke。
- services/python-workers/worker_extract.py 为最小 stdio JSON envelope worker 样例；
  协议 schema：packages/contracts/v1/worker-protocol.schema.json（envelope 含 engine/version/text/loss_receipt；
  失败=非零退出+{"error":...}，禁假成功）。
- 契约：Core↔worker stdio-NDJSON（PROJECT_CONTRACT.yaml runtime）；worker 禁开主库。

## 范围与允许路径（任务包 T04）
crates/archeaxis-application/src/jobs.rs、crates/archeaxis-application/src/runtime/**、
crates/archeaxis-api/src/runtime/**、apps/ArcheAxis.Desktop/CoreSupervisor.cs、
apps/ArcheAxis.Desktop/Program.cs、services/python-workers/runtime/**。

## 验收（任务包原文）
- 重复回写一份结果；错误结果不会留下 completed；
- 占端口、无输出、worker 崩溃可恢复；窗口关闭无遗留子进程。

## 环境事实
- Windows；测试用真实 python worker（仓库 .venv python 或 Green 捆绑 python 均可，勿污染产品目录）；
- 端口/进程实验在 127.0.0.1 高位端口 + scripts/runtime/dev.py 分配的 .project-local/runs/ 下执行；结束必须无残留进程（0906 覆盖旧 .hermes/task-runtime/ 指令）；
- 本地模型探针：ollama(11434) qwen3:8b 等（HTTP），faster-whisper 目录在 D:\All projects\Model library；
- 能力 profile 只登记探针通过的项。

## 建议切片
1. jobs 执行器（stdout/JSON 解析、attempt、幂等键、超时/取消、哈希校验）+ 失败回归；
2. Supervisor 强化：port-in-use/无输出/崩溃恢复路径 + 无遗留子进程断言；
3. 能力发现与模型 profile 探针（只列可用）；worker 日志清理与身份（token/workspace 目录）约束。

## 风险与阻塞
- 与 T03 store、T02 协议共享接口：先等 T02 冻结后的 schema，串行合入共享文件；
- Windows 进程树终止语义（taskkill /T）已在 CoreSupervisor 有实现，可复用。

## 输出契约
- 切片证据：真实运行输出（启动/回写/崩溃恢复/清理后进程数=0）、命令与 SHA；
- 证据落 docs/authority/taskpack-0905/T04/；
- 完成后报告 commit SHA + 验收对照表给集成者。
