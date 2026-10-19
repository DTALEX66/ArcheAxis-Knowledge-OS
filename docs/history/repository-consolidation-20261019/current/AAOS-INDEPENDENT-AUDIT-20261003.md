# 独立审计进展 · 2026-10-03

状态：**NOT_READY / IN_PROGRESS**。Release 保持 FROZEN。本文不替代不可变 R6 TaskPack，不把分段证据升级为完整 M0。

## 已核实证据

- 本地候选源码为 `b421ddeef2284692d2897ac679cde1e6c5df8779`，tree `6263af01c7df117c9f5332025620608fe490c4dd`。清洁源码快照、Core 构建和候选 20,083 文件校验通过；不是远端 CI 或安装替换证据。
- 该提交 Rust workspace 测试 400 passed；日志位于项目 `.project-local/runs/candidate-b421ddee/rust-workspace.log`。
- 真人确认已在隔离 Desktop 提交。Core 事件 5 保存了本人答案、Assessment 与真实 FSRS 排程；`mastery_projection.closed=false`。来源和先前诊断仍是 fixture，不能称为真实资料全旅程。
- 真人收据位于 `.project-local/runs/2611ed9ca1/5eb83531919e/artifacts/desktop-launch/136cacb6e4bd494db89b235fd84061c0/real-human-ui-review.json`。
- Green 根目录旧库的隔离副本迁移、幂等及回滚通过，原文件摘要、大小和时间未变。没有替换已安装 Green。
- 用户认为当前模型回答可以接受；不得替用户制造错误判定、纠正或真人 Retest 证据。

## 当前整改与缺口

- 用户指出默认界面暴露后台数据且交互、配色、动画细节不足。Desktop 正在将诊断默认收起、改为面向用户的文案，并完善忙碌、禁用、选中和点击反馈；发布验证前不得声称已交付。
- 正式 Desktop 机器回答→真人纠正→显式接受→重答→读回入口正在补齐。已有后端测试不等于真人完整旅程。
- 插件 health 与人工配置替换/重启/恢复正补运行证据。当前设计不授权自动 provider 切换。
- embedding 已有本机真实结果，但 LM Studio `/v1/rerank` 返回错误正文，真实 reranker **UNAVAILABLE**。不能用聊天自报分数代替。首次探针可能触发服务 JIT 载入，已记录；随后适配器要求模型已加载。
- General 契约/lesson donor 已增加隔离 worker；Core canonical 课程存储、正式 UI 接入和全链路证据仍未完成。
- 2026-10-03 对新增 search/course workers 的独立复跑为 28 passed、1 个 pytest cache 权限 warning；证据 run `2611ed9ca1/79377e797409`。第一次命令因找不到 pytest 可执行文件未执行，随后用精确 Python 路径复跑。
- 原位替换、安装后重启/读回/回滚仍受 Owner Gate 约束；资源根 Authority 和 mastery 完成语义不能由审计方擅自决定。

当前并行工作树包含未提交整改，不与上述候选源码混称。下一次候选需在集成和验证后重新生成源码快照。由 Codex 承接整改与独立验证；不能依据 DSH 的“全部完成”叙述判定闭环。

## 后续现场增量（同日）

- 用户询问 MINIMAX / DSH 分支关系。当前源码分支为 `codex/dsh-aaos-real-multiformat-loop-20261001`，HEAD `b421ddee`；`codex/aaos-ui-phase2-20261001` 是其祖先，但 MINIMAX tip `627e74ff` 不是。独有 UI 提交 `fec7a18f` 的 cosmic layer 尚未合入。运行中的 PID 21772 为 `.project-local/build/ui-detail-20261003/desktop-selfcontained/ArcheAxis.Desktop.exe`，不是完整 MINIMAX＋DSH 合并版。
- UI v2 已构建，通过 259 项定向回归，修复重答后下一轮纠正、减弱动效静态等待与知识页身份外露。首页、资料库、任务及来源阅读的进一步整改正在 v3 写集中。构建不等于所有界面已完成真人视觉验收。
- General schema 9 与三张课程表已实现；旧 schema 8 四种 archive 布局保持可恢复。定向课程/备份 14、archive 9、store 5 通过。正式课程 API 已实现并有实际 Python worker/Store 重启证据；完整课程真人旅程未完成。
- 重排阻塞的旧表述已纠正。按已批准 R6 A11 的本机现有模型 benchmark，Root 通过 loopback `/api/v1/models/load` 将现有 `qwen3-reranker-0.6b` Q8_0 载入，context 2048；未下载、复制或修改权重。
- `/v1/completions` 返回 `logprobs=null`；`/v1/responses` 能返回真实同一首位置的 exact `yes/no` 概率。相关文档与实际收据已保存，不能再说“没有真实重排接口”。Paris 样例的比率为 0.9996038644823193；banana 样例缺 exact yes 的 top-k 值，生产适配器仍明确 PARTIAL，不补概率。
- 另有引擎特定的强制采样实验，不进入生产评分路径：已登记 GGUF metadata 的 yes/no token IDs 为 9693/2152，只读 132,651 字节元数据，未读 tensor；两种 bias 下 chosen raw logprob 不变。该实证不能冒充普遍 API 语义或标准协议保证。
- 最新实测收据 `.project-local/runs/2611ed9ca1/fc693f33c14e/artifacts/reranker-responses-preflight.json`；先前缺 token 断言失败保留为失败 run，不计 PASS。语义 Core API 正在定向验证，其容量、partial 和 source/version 边界不得默认为全量索引完成。

## 用户选定融合版后的增量

- 用户明确选择 MINIMAX 视觉＋DSH 功能。已选择性移植 cosmic backdrop、glass shell、三主题和配色资源，保留 DSH 功能及诊断默认收起、点击反馈、减弱动效整改；没有整体覆盖另一分支。Desktop 定向 286 passed，self-contained publish 成功；尚无完整真人视觉验收。
- 新融合版进程 PID 21824，路径 `.project-local/build/minimax-dsh-integrated-20261003/desktop-selfcontained/ArcheAxis.Desktop.exe`，现场读回 Responding=true，但 MainWindowTitle 为空；进程运行不能单独证明窗口可见。
- 集成未提交源码 Rust workspace 419 passed、0 failures。日志 `.project-local/runs/integration-b3431500ec2d4b6a8a2899b943e61054/rust-workspace.log`。不与清洁 b421ddee 候选或远端 CI 混称。
- 同源隔离运行收据 `.project-local/runs/2611ed9ca1/5b636d35150b/artifacts/same-source-course-search/receipt.json`：课程创建、渲染、冷重启及真实维护 CLI 备份恢复通过，真人事件 5 保留，语义搜索 AVAILABLE。此前模型未加载的 PARTIAL run 保留；本次仅加载已有本机 embedding/reranker，未下载权重。
- 该运行仍采用既有 fixture 来源和已接受知识，课程是待真人复核的 candidate；不能宣称真实资料到学习、模型纠错、重答、mastery 的完整闭环。正常课程生成和语义搜索 UI 正在集成，Owner Gate 仍未完成，状态保持 NOT_READY。

## 正常课程入口与窗口回读

- 正常用户权限读回 PID 21824 的 MainWindowHandle=2820122，标题“星环知识平台 — 已连接”，响应正常。此前 sandbox 的窗口句柄 0 是观察权限差异；现在可证明窗口存在，仍不替代视觉及交互验收。
- 新 `POST /api/v1/courses/from-knowledge` 只允许真人 actor，从当前锚定 accepted Knowledge 生成稳定身份的候选课件，独立 review 发现并修复 worker 改写正文/ID/标题仍入库的问题。Core 对规范化后 manifest 做完整结构等价检查，差异返回 502；负例均未写入课程。
- 本轮修正 RED run `aa62013701a5` 复现旧正文篡改返回 201；GREEN run `dac159f441d9` 的 course 4 + unavailable 1 passed；build run `97d634a303d1` 成功。Core SHA256 `111486303E8EB3C4664A4F29AC3A9A61B8070DBC5472212A3E75899905487866`。
- 正常入口隔离运行收据 `.project-local/runs/2611ed9ca1/485a2c015f37/artifacts/same-source-course-search/receipt.json` 验证生成幂等、建议学习项身份对应、课件正文等于 canonical Knowledge、真实渲染、Core 冷重启及维护 CLI 备份恢复一致、真人事件 5 保留。此次搜索 NOT_EXECUTED，复用前次独立搜索证据，不声称再次验证。
