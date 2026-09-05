# T00 — 本轮决策、现场与基线（2026-09-05）

来源：`ARCHEAXIS-FAST-FULL-LOOP-TASKPACK-2026-09-05-r2`（19 任务，规划包）。
本文件只记录能力与事实，不包含任何密钥或个人原件。

## 1. 基线核验

- 任务包声明基线：`e9a7d2db854da157138111dc1c772cee95c16647`
- 本机 HEAD：`e9a7d2db854da157138111dc1c772cee95c16647` = origin/main（ls-remote 回读一致）
- 工作树干净；远端自基线以来无新提交 → 无需按实际代码勾销既有修复
- 既有修复在库：v01 闭环收据（`reports/vnext/v01-closed-loop-receipt.json`）、
  Green 在线备份运行锁修复（commit f623634/e9a7d2d）均属已完成项

## 2. 工具链与运行现场（实测，非虚报）

| 项 | 实测值 |
|---|---|
| Rust | cargo/rustc 1.97.1 (stable-x86_64-pc-windows-msvc)，外置 MSVC 14.44 + WinSDK |
| .NET | SDK 10.0.400（外置 10-toolchains/dotnet） |
| ffmpeg | 8.1.2 full build (gyan.dev) |
| tesseract | 5.5.0.20241111 |
| GPU | NVIDIA RTX 5060，8 GiB（本机 CUDA 可用） |
| Python(产品) | Green v0.6.14 捆绑运行时与仓库 `.venv`(3.13) 均在场 |
| Ollama(运行中) | qwen3:8b、qwen2.5vl:7b（视觉）、qwen3-embedding:0.6b、qwen3-reranker、qwen3-coder:30b-a3b-q4_K_M |
| 模型库目录 | faster-whisper-large-v3-turbo、sherpa-onnx sense-voice（中英日韩粤）/streaming-zh、ComfyUI 扩散资产 |
| 外置配置根 | `D:\All projects\OS External Configuration` 在场 |

## 3. 外部条件与阻塞（具体到能力，不阻塞其余任务）

- 云端模型/搜索凭据：环境变量（ANTHROPIC/DEEPSEEK/OPENAI/GEMINI/BRAVE/TAVILY/HF 等）**当前均未配置**
  → 产品内 T08 云端联网核查所需凭据属**阻塞能力**；执行 Agent 的联网研究不受影响（harness 级工具）。
- 其余任务（T01–T07、T09–T14、T17、T18 等）不依赖上述凭据，可继续。
- 真实用户旧库切换（M3/T13 真实数据部分）需用户另行授权时点，不在自动执行范围；
  本机 Green 数据副本 40.7 MB 与仓库 dev 数据 96.7 MB 供 dry-run/迁移验证使用（只读/副本）。

## 4. 决策登记（见 DECISION_SUPERSESSION_LEDGER.yaml SUP-007..010）

1. 首个正式交付 = Avalonia/C# 桌面 + Rust Core + 隔离 Python worker；旧 UI 过渡路线撤销。
2. 有界云端联网交叉核查提前至本轮完整闭环（不再后置）。
3. “全量语言迁移”= 权威业务迁 Rust；Python 保留能力 worker；吸收台账不冒充迁移完成。
4. 旧目录只允许 T17 核验后的定向维护切片；资产逐项登记去向。

## 5. 本轮执行约定

- 每个完成切片：变更与原因、实际验证、剩余风险、回滚路径、精确 SHA（见 T 收据）。
- 共享文件（Cargo 锁、csproj、路由根、迁移序列、CI、目录规则）由集成者串行合入。
- 新增临时文件一律在 `.hermes/task-runtime/` 内；秘密/本机状态不入库。

（T00 验收：决策覆盖关系唯一且链接可解析 ✓；模型/运行时可用性清单如上，无虚报 ✓）
