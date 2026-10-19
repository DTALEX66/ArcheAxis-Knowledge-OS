# 当前闭环缺口审计 · 2026-10-03

## 结论与边界

**NOT_READY。** 当前代码已实现正式语义搜索、General 课程生成/持久化/render/显式开始学习、真人学习及机器纠正入口。它们不是全链路真人、真实资料、安装态闭环证据。Release 保持 FROZEN，MINIMAX 视觉＋DSH 功能是用户选定的界面依据。

当前执行入口仍是 R6 immutable TaskPack、M0 overlay 和用户最新指令。R7 等标签或历史完成报告不能覆盖这些 Authority。本文是独立审计增量，不改写历史收据。

## 前端未完成

| 项目 | 当前真实状态 | 关闭条件 |
| --- | --- | --- |
| 默认页面后台术语 | PARTIAL：原始 IDs/JSON/回执已默认收起，但实际首页仍显示 Core/evidence anchors，学习侧栏仍显示 Assessment/Review/FSRS 协议说明 | 普通页面改为自然用户文案；必要诊断进入明确展开区；保持真实失败和不可用原因 |
| 课程正常操作 | IMPLEMENTED_LOCAL：知识选择→生成候选→读回/render核验→真人显式开始学习已接入 | 在同一真实资料的正式 Desktop 完成真人点击、作答、退出重启及状态读回 |
| 搜索正常操作 | IMPLEMENTED_LOCAL：FTS 与语义按钮均有，真实 PARTIAL/UNAVAILABLE 语义保留 | 真人执行真实查询并核对正文、来源和结果；包含失败/恢复，不用静态 fixture 代替 |
| 机器纠正操作 | IMPLEMENTED_LOCAL：多轮纠正/显式接受/重答入口已补 | 真人实际发现错误、提供纠正、明确接受、模型 Retest 和重启读回；先前用户接受的回答不能重标为错误 |
| 视觉、交互、无障碍 | PARTIAL：MINIMAX cosmic/theme/glass与DSH功能融合，三种实际 Avalonia空状态图已生成 | 真实填充状态、键鼠焦点/IME、忙碌/禁用/错误/成功、减弱动效、主题对比度和必要DPI/窄窗验收；没有完整矩阵证据 |

## 后端及 M0 未完成

| 包 | 已有证据 | 剩余必需动作 |
| --- | --- | --- |
| P0 插件/模型运行 | health、启停边界、人工 profile 替换/重启/恢复及真实失败已有分段证据 | 新集成候选统一记录成功→失败→禁用→人工替换→重启→恢复；资源根语义需 Owner 决定。不擅自增加自动 provider 切换 |
| P1 真实来源/知识 | 真实多格式运行、canonical Source/Anchor/Knowledge写入已有 | 同一用户选择的真实资料链串联 Source/Transform/Anchor/Loss/Quality 与知识审核；三类知识范围对照Authority验收，fixture不得算真实资料 |
| P2 搜索/课程 | 真实 embedding、Responses yes/no reranker、schema9课程、生成/渲染API已实现 | 同批真实知识搜索→候选课件→正文和来源核验→显式学习。缺exact yes/no仍PARTIAL；无持久向量索引，不能称完整索引/研究/图谱已完成 |
| P3 真人学习 | 真实用户事件5、FSRS和隔离恢复已读回，但来源是fixture | 真资料真人学习及整条Desktop冷重启读回。`learning.rs` 当前固定 `mastery_projection.closed=false`；需Owner明确掌握规则，不能自行把Good或连对次数变成闭环 |
| P4 机器学习 | 后端/界面task→correction→accept→retest已有局部及合成测试 | 同一真实Accepted/Personal Knowledge上的真实模型任务与真人错误判断/纠正；用户原先接受的答案保持接受 |
| P5 持久化/迁移 | 真实旧库只读副本迁移、新课程维护CLI backup/restore及事件5保留已验证 | 整条新增真实旅程的workspace身份、schema、FK、对象摘要、课程、Assessment、事件、FSRS、机器纠正及Retest全状态恢复 |
| P6 候选/安装 | 清洁b421ddee候选和最新未提交融合版各有局部证据 | 冻结最新集成源码→重新构建候选→manifest逐项校验→候选P0–P5。实际Green备份/替换/冷启动/回滚须Owner精确授权；发布不自动开启 |

`courses/from-knowledge` 当前仅支持有anchor的active accepted知识。无anchor个人知识的课程支持没有完成；若真实旅程必须包含它，需要补实现或Owner明确范围，不能默认为已支持。

## 真实验证及未通过项

- Rust集成阶段419 passed；新增课程route及其worker正文/ID/标题篡改拒绝回归另有通过证据，不把早期419描述为覆盖后续新增代码。
- 新Core SHA256 `111486303E8EB3C4664A4F29AC3A9A61B8070DBC5472212A3E75899905487866`。正常课程route运行 `485a2c015f37`：幂等、建议身份、正文、render、冷重启、真实维护CLI备份恢复一致，事件5保留。源知识仍fixture，搜索本run NOT_EXECUTED。
- 搜索/课程同源运行 `5b636d35150b` 的语义结果AVAILABLE，是本机这一查询的结果，不是所有查询保证。
- 最新Desktop publish run `5aa014b65975` exit0；DLL SHA256 `23D9B3BB83425CC6A716017FBC05778BFCE89CC72515D4F08B2037E3221A0767`。home/search/learning attached-window图分别为 `ab7c1d888b7f`、`5fc965061a13`、`ec4264333c81`，课程为空入口。
- Desktop扩大目标检查269 passed、2 failed；修复后对应目标8 passed。不能把未复跑的整个目标组直接重标为271 passed。
- 本次canonical全量Python检查在收集阶段中断：缺onnxruntime、fsrs、jiwer、pymupdf，4 errors、3 skipped，**不是PASS**。日志 `.project-local/runs/sync-gate-e4e8eded093a4d318cebdb8437c85a12/python-full.log`。
- worktree convention检查发现60个CRLF问题，architecture guard通过。需按index/HEAD及frozen tree核对，不批量格式化immutable authority来掩盖问题。
- 所有本地日志和运行库保留在ignored `.project-local`，不上传私人数据。远端最新SHA CI需独立回读，不能用这些本地结果替代。

## 双端与清理审计

实时远端读取并fetch成功：main=`59498723a8d4e94c6314e490473ba6d60847c247`；Audit/UIphase2=`1a981a4482b01f31989074e79c82a63400aa07a7`；MINIMAX=`627e74ffcc2b16e2109ab85c0a8183f1e4a6b21a`；同步前DSH remote=`0980fc7d29c1554e01d82a6a604860028cd87cb4`，本地HEAD=`b421ddeef2284692d2897ac679cde1e6c5df8779`领先1。同步后的提交和CI以实际Git读回为准；main未合入，不称main已经一致。

主仓库有1007项未跟踪 `docs/history` 和1项测试；另外 `p-w7n3ehdf` 不可枚举。不能根据历史“已归档”叙述断定它们已逐项云端保存。Green根不是Gitrepo：runtime、数据库、backups、output和嵌套worktrees是不同归属。

清理规则：云端同HEAD只证明已提交内容；tracked源删除再同步会同时删掉云端当前树；ignored/未跟踪内容根本不随push上传。干净应由版本控制、忽略规则和可回退的精确清理达成，禁止 `git clean -fdx` 或整体清空。

- 优先可审查范围：Green `.ui-task-tree/AAOS-integration-verification-413ad3a0`，tracked/untracked均0，仅ignored `.ruff_cache`，tip已在远端main历史中。仍须确认消费者、必要证据及精确删除授权后用Git worktree规范移除。
- 其余worktree含dirty文件或ignored验证证据，保留。两个本轮早期候选目录已有精确删除计划，但尚未得到该清单的明确审批；不得代替同意。
- Green三个AAOS-v*仍被启动器引用且各含data；当前b421ddee候选Python仍是开发验证依赖；现役Desktop/Core/run保留。私人状态、DB、模型、共享工具、未知及不可读项保留，不上传。

## 分工与执行顺序

Codex完成本轮独立审计、集成差量验证和安全的项目文件同步。DSH按配套执行提示词承接剩余前后端差量、真实候选准备及清理清单；用户只负责真实资料选择、学习/错误判断、掌握规则及安装删除必要裁决。DSH执行后仍由独立审计方核实，不以执行方自报完成结案。

先同步和冻结当前工作→修复默认文案/必要后端缺口→同一真资料P0–P5真人旅程→新候选与完整门禁→独立审计→Owner安装/回滚→判定LOCAL_GREEN_READY_FOR_OWNER_REVIEW或NOT_READY。第二Provider、更多Domain/renderer、Marketplace、扩展研究/图谱等按M0 overlay延期；不能因此说整个R6长期蓝图全部完成。
