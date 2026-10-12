# 当前 Agent 接手入口 · 2026-10-12

先读 [根权威入口](../../AUTHORITY.md)、[AGENTS](../../AGENTS.md)、[项目合同](../../PROJECT_CONTRACT.yaml)、[文档权威索引](../DOCUMENTATION_AUTHORITY_INDEX.md) 和 [路径身份路由](AAOS-AUTHORITY-ROUTES.json)。这些是仓库公开入口，适用于遵循项目规则的本地/云端软件与模型；不依赖私人配置。

## 当前任务与停止边界

[活动指针](AAOS-ACTIVE-EXECUTION.json) 是任务路由；来源仍为 `docs/taskpacks/aaos-ui-first-20261009/`，实际进度读 [UI执行记录](AAOS-UI-FIRST-EXECUTION-20261009.md)。Owner 2026-10-11 已明确恢复“完整框架 / 多格式（常见常用格式）/ 最短闭环”，当前 **RUNNING_BY_OWNER / PARTIAL**；[恢复范围](AAOS-CLOSED-LOOP-OWNER-RESUME-20261011.json) 只承接这次用户决定，不替换原任务包或赋予 PASS。V01暂停、FT01–04冻结；发布、Green替换与真实用户数据覆盖未授权。

六项核心能力对话增量已 [归档冻结](../history/conversation-summary-20261010/INDEX.md)：**FROZEN_BY_OWNER / NOT_EXECUTED**，不加入当前队列。其旧AAOS-01活动队列措辞、旧源码基线、48项测试提案和包内执行提示词均不是当前授权。

## 不变的产品规则

正式 `frontend/` + `src-tauri/`，Tauri 2 + React/TypeScript/Vite；Rust Core唯一SQLite/CAS业务写者，Python worker隔离。Avalonia是冻结供体，旧FastAPI不成为正式后端。普通内容先保存，权限/结构/完整性仍检查；识别忠实度与专业依据独立，人工认可属专门流程。

新布局/架构按UI优先包，blueprint默认，blueprint-light与black/white/cosmic可切换；所有主题共用新布局，同主题全局语义颜色一致。治理更新不改产品配色和代码。

## 当前检出、云端与证据

公开源码已在 PR #184 合并至 main；合并 SHA `1a322045490075e68e4d8b5f26bdd706d3e4089a`，候选 SHA `fca7e7150c0e356b832730531f942af3f49b1b95` 的必需 CI 运行 `38268676998` 通过，包括 CI Windows 实际安装旅程。候选树与合并树一致。这是记录时点，最新 HEAD/ref/CI 必须现场读回。

`codex/Audit` 已删除；不再作为接手目标。Owner 随后明确要求删除的 cosmic 远程分支亦已删除；2026-10-13 回读远程仅有 main。9 个含未提交修改的历史工作区与 cosmic 本地供体工作区仍保留，不能认定与 main 一致，也不能机械并入。完整状态、保留理由和换软件接续步骤见[仓库接续记录](AAOS-REPOSITORY-CONTINUITY-20261012.md)。

本地测试、候选 exact-SHA CI、合并 SHA CI、CI 安装旅程、本机安装/Green 和 Owner 验收分别记账。合并及 CI PASS 不完成整个产品，也不授予新会话任意发布、模型切换或私有数据外发权限。

## 2026-10-12 实测增量与仍缺证据

当前范围仍 RUNNING_BY_OWNER / PARTIAL。以下是绑定 dirty patch 的隔离 Windows
Tauri/Core 工程证据，不是当前 HEAD 全量资格、安装版或 Owner 验收：

- [复习 ACK 故障与完整本地 AI 链](receipts/AAOS-NATIVE-REVIEW-ACK-FULL-LOOP-20261012.json)：工程 PASS；真实持久化后合成丢失两次 ACK、两次完整宿主冷重启、同请求显式重试 duplicate=true、日志清除、界面确认、真实本地模型调用及最终备份恢复读回。故障和材料为 SYNTHETIC，Tauri/Core 执行为 INTEGRATED，本地模型调用为 REAL。
- [原生鼠标导航](receipts/AAOS-NATIVE-POINTER-NAVIGATION-20261012.json)：一次受信点击与路由/渲染读回 PASS，不证明历史偶发故障根因或永久消除。
- [当前模型诊断链](receipts/AAOS-NATIVE-ACTUAL-AI-DIAGNOSTICS-20261012.json)：真实本地模型工程链 PASS；本轮没有触发模型失败，失败原因分类仍由合成/集成回归支持，不能追认历史 503 原因。

最新实现与实测补充（2026-10-12，后续源码变化仍需重新绑定）：

- [最新清单与清理候选闭环](receipts/AAOS-NATIVE-INVENTORY-CLEANUP-20261012.json)：正式 UI 显式本地清单探测读到 6 项，声明模型已列出；加载 UNKNOWN、推理 NOT_EXECUTED，未增加机器任务。其后独立实际 4B 回答、复测、保存、冷重启及合成 ACK 恢复 PASS，源码与构建绑定、自有端口释放。清单存在不证明模型已加载或推理成功。
- [清单资源异常回归](receipts/AAOS-MODEL-INVENTORY-RESOURCES-20261012.json)：设置读取失败、禁用、排队期间禁用、满队列、输出超限、超时及自有后代持管道回归通过。Windows 管道取消后读线程结束并 join；故障为合成复现，不是实际用户故障发生记录。
- [计量真实读回](receipts/AAOS-NATIVE-MODEL-METERING-20261012.json)：服务返回 Token 用量已传递、显示并随任务保存；最新清理候选亦保留原答/复测计量。缺失费用保持 UNKNOWN。服务报告用量不等于独立计费测量。

`config/models.yaml` 的 stub/local-stub 是历史产品适配器占位，不能代表当前 Core 注册 worker、清单或单次模型调用的实际状态。日常基座最终选择、任务角色呈现和本地/云端调用契约统一仍须按当前源码审计实施；不得凭已有 4B PASS 宣称所有模型供应商支持。

上述回执的 raw receipt 与 SHA-256 已在 2026-10-12 逐一核对。具体每轮测试 patch
以各回执为准；后续修改不能继承其资格。旧 FAIL 保留，复习恢复此前“仅模拟”的
表述属于旧时点，不能当作本轮仍缺实测。

[27B 正式应用闭环](receipts/AAOS-NATIVE-27B-APPLICATION-20261012.json) 已在 `webdriver-473ddd0813ca` 完成工程 PASS：独占临时模型实际回答、纠正复测、保存、冷重启及备份恢复读回，合成材料；首次回答89.89秒、服务报告413 tokens。本轮实例已卸载，既有4B保留。设备总显存峰值7589 MiB包含4B，RAM峰值、实际层分配仍 UNVERIFIED；不证明日常流畅、质量或MTP加速。历史失败保留。

仍未完成：27B 峰值资源与质量资格、匹配条件下MTP加速比较、独立准确率与学习效果评估、
真实故障下模型执行恢复、云端真实调用、本机安装/Green 与 Owner 验收。[恢复后的原复习身份](receipts/AAOS-PRIOR-EPOCH-REVIEW-NATIVE-20261012.json) 已完成两次指定合成备份恢复、候选丢弃按钮禁用、显式保留旧origin、冷重启和原body首次/duplicate重试的原生工程PASS。Core直接discard拒绝仍为合成后端回归，机器日志候选的原生保留、冷重启和原任务恢复已在 `webdriver-e53abf84cbf8` PASS（[回执](receipts/AAOS-MACHINE-RESTORE-NATIVE-20261012.json)）；多条复习显式选择已在正式06页 `webdriver-7cae664a1b80` 工程PASS（[回执](receipts/AAOS-MULTI-REVIEW-NATIVE-20261012.json)），本次未调用模型，不能扩大为真实模型故障资格；不能扩大证据范围。
临时27B实测已有本轮限定授权；不擅自扩大到新模型、共享实例或全局配置。付费调用、私有材料外发、发布、Green替换及
真实数据覆盖仍不在本轮授权中。继续以活动执行记录核对其余产品任务，不以这几项
证据代替完整范围验收。

## 旧路径与接手行为

搜索命中旧handoff、docs/current中的dated文件、authority/taskpack、蓝图或模型总结时，先按路径身份路由分类，再回到活动指针和相应Concern索引。文件名CURRENT、旧COMPLETE与旧grant不能提升成当前规则、状态或操作授权。外部/私人路径不自动进入；本地共享资源读 [资源路径索引](../SHARED_RESOURCE_PATH_INDEX.md)，云端不照搬本机绝对路径。

原本页历史各阶段叙述按 [完整原字节](../history/authority-repair-20261010/AAOS-AGENT-HANDOFF-before-repair.md) 保留，不再与当前接手指令混排。所有历史FAIL、PARTIAL、证据SHA与原权限保持其原时点。


## 2026-10-12 整体缺口复核

图像/视频帧本机传输边界已修复，38项回归含实际 loopback 验证；当前 native 宿主尚未包含该增量。机器 max3 retry、原子失败审计、专用只读 status/clear 和正式 UI 明确失败冷恢复已实施，UNKNOWN 不重复推理；同 owner 新身份不能绕过冻结请求，复测预算缓存与未知历史预算拒绝已修复。[本轮回执](receipts/AAOS-MACHINE-FAILURE-COLD-RECOVERY-20261012.json)：同 dirty patch Rust 766 项、前端 127 文件/1230 项、TypeScript 与合同检查 PASS。实际 Core 使用合成 worker，UI 是模拟，尚无本增量 native 或真实模型失败资格。旧回执保留其历史时点。下一步机器取消与 owned task 收尾，再统一当前 native 资格；随后文档便携包回导及媒体 CAS 往返、正式模型/工具职责呈现和有界视频视觉资格、外发最后授权复核到首次发送竞态。整体仍 PARTIAL，不能以历史闭环代替这些缺口。

## 2026-10-13 当前收尾证据（覆盖此前待实施措辞）

PR #186 已合并 `c7c631a6afa86660679d8ab5439170503f89ea29`，其候选与主线 CI 均通过。PR #187 已合并 `e8e28efba00aee464f10ba4ba44fb2d950641543`；候选 `5cfeb17622b77598c9ba7e08c5b49369ebf52759` 的 CI `38289331035` 通过，合并后的主线 CI 仍需读回。

同一候选已完成现有 4B 和 27B 的真实隔离 Tauri/Core 合成材料闭环：问答、复测、本地 worker 取消、职责界面、便携媒体 CAS 字节/哈希、未知节点保留、重启读回及重复导入均 PASS。Core 自动补充的新节点 block_id 纳入严格比对；入库未自动执行。4B 首答约 33 秒，27B 约 85 秒；这不是模型准确性、流畅性保证或 Owner 验收。两轮自有模型实例已卸载、端口释放、既有实例保留。匹配条件 MTP 短程比较已完成，持续性能与独立质量仍未验证。

具体脱敏证据和原失败历史保留在 [本轮收尾回执](receipts/AAOS-CONVERSATION-CLOSURE-20261013.json)。4B/27B 登记 vision=false；7B 视觉候选未加载，真实视频视觉资格仍 NOT_EXECUTED。云端真实供应商、浏览器下载文件落盘读回、安装版 Green 替换和真实用户数据覆盖未执行。此前日期段落中的“尚须实施/集成中/匹配比较未完成”保留为历史观察，不再代表当前状态。另一会话的独立 UI 分支未修改。
