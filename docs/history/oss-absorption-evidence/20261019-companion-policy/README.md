# 陪伴策略与导航标题：2026-10-19 限定增量快照

状态 **PARTIAL**。本目录保存项目派生证据，不是新 Authority 或另一份任务队列。现行范围经[活动指针](../../../current/AAOS-ACTIVE-EXECUTION.json)解析，实际进度仍归[唯一执行记录](../../../current/AAOS-UI-FIRST-EXECUTION-20261009.md)。Owner 可见对话原话、提问与决定见[39项来源归档](../../owner-dialogue-20261019/README.md)；完整私人 Cowork 正文仍 UNVERIFIED。

## 已应用的产品变更

普通陪伴与材料问答共用严格 grounding 模板曾导致普通复习建议拒答。本轮将两种策略版本化：Core 从 purpose 决定有限策略，策略/提示版本绑定新 plan SHA，Executor 与 worker 显式传递并回报；元数据缺失或不匹配则不给答案及知识接纳。旧 grounded 模板、历史 journal 回放与既有权限保持其原语义，不迁移历史计划或重新推理。Schema/生成类型兼容旧计划。

另修正自有取消探针离开材料草稿时的受信确认。Dockview 页签和关闭按钮名称随已获准页面变化，覆盖首次、同族切换、关闭重开、布局恢复及对象文档；继续保留原业务宿主和草稿，拒绝导航不改已接受页面。

14个文件的任务前置/当前 SHA 在 [SOURCE-MANIFEST.json](SOURCE-MANIFEST.json)，任务增量在 [task-delta.diff](task-delta.diff)。前置为当时的 dirty 工作树，不能把这个 diff 直接当作从 HEAD 生成的干净补丁。旧 handoff 与文档索引按原字节保全，避免删除旧说明时丢失历史。

## 验证与失败边界

实际命令、UTC起止、退出码、源码 patch 和日志定位在 [EXECUTIONS.json](EXECUTIONS.json)：137项Python、15项应用层Rust、8+6项Core API、55项前端定向检查通过；最后样式修正后18项探针/合同复核通过，计数重叠，不相加冒充全仓覆盖。Core/TypeScript/Vite/Tauri构建通过。导航提案原始产品负对照9项失败；应用后26项实际Dockview/App的jsdom行为测试与TypeScript/Vite通过。每组保留各自源码标识，不拼为同一patch全仓通过。

[真实worker单例](real-companion-worker.json)使用当前 LM Studio 的 `aaos-deep-27b-mtp`，对自拟复习问题返回实用中文建议，耗时60.71秒，报告152 output tokens、stop、无截断。该项是实际模型＋合成问题的直接worker验证，没有经过Core或原生UI，不等于完整质量、学习效果或性能达标。

[最新原生诊断](native-material-failure-diagnostics.json)为 `TimeoutError`：材料问答118.03秒超过118秒worker预算，终态 failed / `material_model_call_failed`、answer为空、candidate、无接纳权。原生旅程整体 **FAIL**，本轮普通陪伴、取消与后续恢复阶段尚未到达。模型内部为何超时仍UNVERIFIED；未提高合同超时、改模型或全局配置。

[两轮原生读回](NATIVE-READBACK.json)分开保存：先前源码的材料取消已发出并得到严格身份ACK和取消终态；随后切陪伴被自有草稿确认阻断。那一轮不是当前源码的陪伴取消通过。两轮共10张截图均已实际查看，PNG留在项目内忽略目录并记录SHA；两轮拥有进程与端口退出为空，共享LM Studio未停止。当前候选包含策略修复，但早于最后的导航标题补丁；最后补丁原生视觉 **NOT_EXECUTED**。

[Ruff比较](ruff-before-after.json)保留34项既有诊断，整体lint为FAIL；相对本轮前置新增诊断为0。失败、无效中间测试fixture及原红色回归未删除，原日志保留在相应run目录，不以最终局部PASS覆盖。

## 接续与未完成

限定总回执：[AAOS-COMPANION-POLICY-20261019.json](../../../current/receipts/AAOS-COMPANION-POLICY-20261019.json)。后续先解决材料推理时延/超时复现，再完成当前策略的Core→原生陪伴与取消/恢复闭环；导航原生视觉、工程字段密度/手工对比度、BE10、HUB003/004、统一模型合同、全格式、安装及Owner验收尚未关闭。

[BE10只读提案](BE10-READONLY-PROPOSAL.md)保留独立Observer准入、有限只读端口、真实adapter及只读身份陷阱；它是工程建议且 **NOT_EXECUTED**，不能按合同占位声明互通。原规划、冻结与权限仍读原规范源。

`MANIFEST.json`冻结本目录成员SHA；后继应新增回执，不改写本次失败和时间。未提交、推送、云端备份、发布或替换Green。结构归档PASS不等于产品通过。
