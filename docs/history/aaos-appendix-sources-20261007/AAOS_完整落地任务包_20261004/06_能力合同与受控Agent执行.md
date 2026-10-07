# 能力合同、可发现性与受控 Agent 执行

## 1. 不是一个文件装下所有事实

单源不是把规划、执行、密钥和健康塞进同一个大文件，而是每类事实只有一个权威来源，并用稳定 ID 联接。

| 信息 | 唯一负责的事实 | UI 使用方式 |
|---|---|---|
| Product Capability Catalog | 现有/未来有效能力、业务域、场景、依赖、导航与详情 | 全部可发现，包括无实现项 |
| Runtime Implementation Manifest | 已实现 worker/adapter、入口、版本、协议、必需性、支持动作 | 判断有没有对应实现，不判断当前授权 |
| Connection/Policy Record | 配置引用、授权范围、启用、预算、允许目的地 | 配置/测试/禁用/权限管理 |
| Health/Execution Receipt | 最近探测、调用结果、产物、版本和时间 | 当前可用性与本次实际调用 |
| Compatibility Profile | 平台版本、功能、方向、字段映射、损失与往返结果 | 兼容等级按方向显示，不笼统一颗绿灯 |

各对象扩展现有合同，不另设第二 Current Truth。派生 UI 投影由 Core/现有安全只读接口提供；桌面不因连接页需要数据而直写数据库。

## 2. ID 与状态

复用现有 capability_id；本包 seed_key 仅为整理键，必须映射到仓库 ID，禁止批量覆盖 CAP 编号。保留中文别名和历史路由跳转。提供方、插件、技能、worker 分别有 ID，不能把一个平台名同时当四种对象。

规划/实现：planned、in_development、implemented、qualified、superseded。运行：not_configured、needs_auth、not_checked、available、limited、offline、failed、disabled。这些是概念值，先映射现有状态模型再落代码，不能为本包字符串改破兼容。

available 必须同时满足有效实现、允许策略、必要授权、版本兼容和近期有效探测；过期健康状态显示 stale/需检查。未来能力默认无实现、runtime 不适用，不当红色故障。

## 3. 一项能力的典型字段

Catalog：id、name、domain、parent、aliases、summary、input/output intent、planning_state、dependencies、canonical_detail、source_authority_refs。
Runtime：implementation_id、capability_ids、provider/worker、protocol、version/revision、entry/resource_root、required、input/output schemas、healthcheck、artifact_types。
Connection：connection_id、credential_ref、enabled、data_scopes、network_targets、budget、policy_revision。无明文 Key。
Receipt：run_id、step_id、capability/implementation/provider versions、input references、request fingerprint、policy/consent、status、error_kind、artifact references、cost estimate vs actual、started/finished、cancellation/commit status。

缺字段给 null+reason；null 与零区分。能力计数区分“目录条目、已实现、当前可用、待配置、规划中”，不要把全部能力数命名为“已连接”。

## 4. 产品技能与开发技能分开

产品技能是用户的资料学习、研究对比、研发资料包或迁移预检流程。开发技能是 Codex/DSH 使用的 Avalonia/测试/设计方法。安装开发 Skill 不等于产品获得该能力。

产品技能只引用已定义工具与权限，不携带能自行升权的命令。导入外部技能先审阅出处、许可、版本、依赖和副作用；默认不自动安装/启用。技能里的自然语言不能覆盖 Core 的权限。

## 5. 受控 Agent 最小路线

复用现有任务/Job/Receipt 机制，建立有界状态：created → planned → awaiting_approval（需要时）→ running → succeeded/failed/cancelled；允许暂停/恢复，但只在支持 checkpoint 的阶段承诺可恢复。

每步保存允许能力、数据范围、预算、前置条件、输入版本和结果引用。模型提出计划，宿主校验；实际工具调用由允许列表和 Core/worker 边界执行。研究正文、外部技能、模型返回字段不能直接决定审批或扩大网络权限。

确定性任务先用显式步骤，不为“像 Agent”在每一步都调用模型。只有解释、规划、比较等需要时使用模型。最大步骤/重试/Token/费用都有上限；到限停止并给已产出的部分结果。

对写操作使用幂等键和提交回执；外部副作用无法保证原子回滚时必须记录补偿策略。取消只取消未提交或可终止步骤，已保存知识不会被宣称自动撤销。

### 三个首批技能

| 技能 | 工具 | 输出与安全边界 |
|---|---|---|
| 资料学习 | 现有阅读、引用、讲解、练习、学习事件、调度 | 可追溯讲解/练习与真实学习记录；不自动认可知识 |
| 研究对比 | 选定资料+授权只读检索+引用/候选生成 | 主张、证据、冲突、局限、待核验项；不假称穷尽文献 |
| 研发资料包 | 指定版本官方资料、代码文档读取、归纳 | 技术约束、来源版本、风险与给执行层的任务输入；不任意运行仓库代码 |

知识库迁移默认使用可预测的向导/分批任务，不让模型自行改变映射或覆盖源库。AI 可建议映射，执行前必须通过格式合同和用户确认。

## 6. 三项目职责

AAOS：知识/证据/学习/受控知识任务的领域真值与长期成果。
WORK-LAB：跨软件和通用执行的既有能力治理与交接，保留外部 Agent 自身推理循环边界。
DESIGN-LAB：设计与生产资产能力，可消费经过授权的知识资料包。

只设计所需交接合同，不在本次包中修改另两仓。成果回 AAOS 时记录来源与审批，不建立双写。网页规划审计与本地执行器之间使用明确任务/回执交接，不绕过平台权限去抓取私人会话。

## 7. 网络与性能

本地已有模型/共享路径优先，执行器先检查资源再选方案。不得同时启动多个大模型或复制模型库。连接页不对所有未启用平台周期探测，列表虚拟化和缓存；展开未来菜单不下载依赖、不联网。

外部内容获取遵守授权、许可与缓存政策。任务参数和密钥从日志脱敏；截图不显示 token。外部服务改变数据目的地需要新授权。当前软件未具备这种授权机制时，把对应外部调用标阻塞，而不是 UI 提醒一下就实际上传。

<!-- source-links -->
[S01]: sources/GPT-PROMPT-OWNER-QUESTIONS-20261004.md
[S02]: https://github.com/tinyhumansai/openhuman
[S03]: https://docs.avaloniaui.net/docs/testing/
[S04]: https://www.crossref.org/documentation/retrieve-metadata/rest-api/access-and-authentication/
[S05]: https://help.openalex.org/api/authentication/
[S06]: https://sqlite.org/backup.html
[S07]: https://sqlite.org/lang_transaction.html
[S08]: https://sqlite.org/lang_returning.html
[S09]: https://doc.rust-lang.org/std/net/struct.TcpListener.html
[S10]: https://learn.microsoft.com/en-us/dotnet/api/system.diagnostics.processstartinfo.redirectstandardoutput
[S11]: https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects
[S12]: https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/takeown
[S13]: https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/icacls
[S14]: https://github.com/open-spaced-repetition/awesome-fsrs/wiki/The-Algorithm
[S15]: https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html
[S16]: https://www.apple.com/newsroom/2017/06/apple-design-awards-celebrate-the-best-in-innovation-and-creativity/
[S17]: https://www.apple.com/newsroom/2021/12/app-store-awards-honor-the-best-apps-and-games-of-2021/
[S18]: https://www.notion.com/help/export-your-content
[S19]: https://obsidian.md/help/import/markdown
[S20]: https://joplinapp.org/help/apps/import_export/
[S21]: https://docs.ankiweb.net/exporting.html
[S22]: https://www.zotero.org/support/kb/importing_standardized_formats
[S23]: 10_来源与待核验登记.md
[S24]: https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/pull/157
[S25]: https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/blob/main/docs/current/R6-EXECUTION.md
[S26]: https://docs.github.com/en/pull-requests/reference/pull-request-merges
[S27]: 10_来源与待核验登记.md
