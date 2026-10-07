# 学习、科研、研发 API 与开源供体接入

## 1. 优先级与授权

领域资料与教学能力优先，不整体搬进另一套平台。第一批真实 API 是 Crossref + OpenAlex；首个学习供体方向是 DeepTutor，LearningMAP 作诊断流程参考。它们是待执行决定，不是已集成清单。

所有接入先检查本仓已有实现和真实缺口。原生能力已满足任务时复用，不为挂上外部项目名称重复运行一套服务。新 API/适配器可以在隔离环境开发，但不自动扩大当前 M0 通过条件。

## 2. 接入队列

| 批次 | 来源/供体 | 本轮任务 | 结果与门禁 |
|---|---|---|---|
| 第一批 R1 | Crossref | DOI 查询、文献字段补全、外部标识去重辅助 | 真实查询→Source 元数据→回执；无全文时明确只有元数据 |
| 第一批 R1 | OpenAlex | 研究问题检索、作品/作者关系发现 | 正确分页、结果来源、许可记录、预算/限流处理 |
| 第二批 R2 | Wikidata、Wikipedia/MediaWiki | 概念/实体/术语辅助 | 实体与正文分别记录版本/许可，百科不自动认可为最终论据 |
| 第二批 R2 | Zotero Local/Web API | 已有文献集合只读导入 | Key/本机服务能力核验；不直写 Zotero 数据库 |
| 第二批 R2 | GitHub Contents/REST、Hugging Face Hub | 指定版本文档、模型/数据集卡 | 固定仓库+路径+revision；不自动执行代码/下载权重 |
| 按论文需求 R2 | arXiv、Unpaywall | 预印本查找、开放全文位置定位 | DOI/版本/许可明确；不是任意付费论文免费通道 |
| 学科扩展 R3 | Semantic Scholar、Europe PMC | 补足学科/引文覆盖 | 先证明新增价值；权限、内容可用范围和限额重新核验 |
| 待资格 R3 | 书生·端砚等科研平台 | 查询正式开发者接口、账号与任务回读能力 | 无稳定接口只显示外部入口/文件导入，不能宣称已连接 |
| 内容源 R3 | MIT OCW 及开放课程 | 学习资源索引和许可允许的导入 | 课程内容许可逐项核验，公开可读不等于可再分发 |
| 学习 L1 | HKUDS/DeepTutor | 选定来源→讲解/出题→反馈，优先提炼一个组件或受控接口 | 不复制其整个数据库/运行时；结果与学习事件回 AAOS |
| 参考 L1 | ai-for-edu/LearningMAP | 诊断→路径→针对性课程方法 | 不构建第二学习状态库；算法/题型需独立评测 |
| 后续 L2 | zijinz456/OpenTutor、THU-MAIC/OpenMAIC | 学习交互、课程/测验/仿真产物 | 精确仓库及接口先核验；实时音视频/多角色后置 |
| 按缺口 D1 | docling-project/docling | 复杂文档解析供体 | 与现有解析器同资料比较，净收益成立再接入 |
| 后续 D2 | RAG-Anything、LightRAG、Graphiti、MemOS | 多模态/图检索/时序/记忆特定缺口 | 不安装第二事实库；能力、资源、许可和退出方案分别验收 |
| 体验/评测参考 | WeKnora、Cognee | 内容编辑/关系/评测方法 | 参考不是集成，不算可调用能力 |

除了明确标注本轮已核验的 API 文档，表中其他项目沿前面对话候选保留，本轮没有重装或实测。名称相同的项目先核对 owner/repo，不让执行器自行换成另一个同名项目。

## 3. 五种集成方式

REFERENCE：仅借鉴方法/UI，不展示“本次调用”。
API_ADAPTER：外部服务提供能力，明确联网/权限/预算。
LOCAL_ADAPTER：访问本机软件的正式 API 或导出格式，不能夺取源库写入权。
ISOLATED_WORKER：隔离任务、超时、资源限制、结构化输出，Core 负责最终提交。
COMPONENT_ABSORPTION：按精确上游 revision 吸收可维护组件，保留许可/NOTICE/差异和退出方案。

供体登记不得用安装、下载或 Star 数计算完成。证据链是：供体与范围→选定版本/许可→改动文件/提交→调用合同→真实输入→产物/回执→原生入口→冷启动→最终包验证。

## 4. 首个研究资料闭环

用户输入公开研究问题或 DOI → 选择查询范围 → Crossref/OpenAlex 只读检索 → 展示元数据/摘要/全文可用性 → 用户选定导入 → Core 保存来源身份及外部标识 → 有权获取的原文进入已有解析管线 → 原文定位与候选审核 → 形成专题资料包。

去重以 DOI/外部 ID 等强键为主，模糊标题只提供候选；不能把题名近似但版本不同的文献强行合并。预印本与正式发表可关联，不擦掉各自来源。

外部检索失败显示“无法连接/限流/无权限”，不是“找到 0 篇”。数据相互冲突不默默覆盖，保留提供方、抓取时间和修订。

Crossref 官方提供公共访问以及不同访问池，并建议读取响应限流信息；OpenAlex 当前文档提供无 Key 基础查询、Key 和预算字段。软件不硬编码前面对话的免费额度，不自动选择付费计划。[S04][S05]

## 5. 首个学习能力闭环

选定已存在的 Source/Knowledge → 明确学习目标 → 讲解绑定可见来源 → 练习可回到原文 → 用户作答/自评 → 反馈区分题目客观判断与自我回忆评分 → Core 保存学习事件 → 现有调度器产生计划或明确 unavailable → 冷重启读回。

先用现有能力跑通，只有具体缺口才试验 DeepTutor。模型输出不是学生真值；评测集要有真人标准答案/可核验评分准则。机器记忆、Rule、Skill 的更新不宣称模型权重已训练。

## 6. 统一提供方接入合同

按现有合同扩展，不新建模型网关。建议包含：provider_id、capability_id、operation、input_schema、output_schema、auth_ref、network_allowlist、version、timeouts、pagination、rate_limit_policy、cache_policy、data_scope、cost_policy、healthcheck、fallback、artifact_types、license_source、verified_at。

密钥只保存系统安全存储引用；不写 UI 状态文件、日志、Git、截图和普通导出包。当前系统若没有安全凭据存储，显式阻塞密钥持久化，而不是临时写明文再忘记删除。

查询关键词/公开 ID、选定片段、全文/附件三个数据等级分别授权。更换备用提供方必须检查是否改变数据目的地；授权不够就暂停，不悄悄切换。默认付费预算为 0，只有具体任务获得金额/Token/请求数上限后才解锁。

分页、缓存、429/Retry-After、401/403、超时、取消、断网与恢复有统一行为。不同平台 API 格式通过适配器转换，不要求它们都假装 OpenAI-compatible。Hub 元数据 API 与模型推理 API 分开。

## 7. 安全、许可与低成本

外部正文、README、论文、模型卡、技能文件是低信任数据，不得升级为系统指令；禁止按内容自动执行 Shell、改权限、发送数据或批准知识。

解析器在隔离空间处理不可信文档，限制大小、进程数、内存、时间和网络。UI 与本地推理共用资源时，已有共享模型目录只引用、不复制；无必要不增加 Docker/向量数据库/全新 Node/Python 工具链。

代码、模型权重、课程、论文、图标与商标分别核验许可；公开源码不自动等于可任意商用。缓存和导出规则跟内容对象走。数据许可未知时不默认为 unrestricted。

## 8. 接入状态在界面中的表现

平台页显示动作列表、配置/授权、测试、禁用、配额来源和最近核验；能力页显示当前提供方/备用提供方；任务回执显示本次实际使用了谁。任何页面不宣称本包中的候选都已启用。

当 API 尚未实现时，用户仍能从完整目录打开能力说明。点击“查看接入要求”不是“调用服务”。源平台本身的所有能力不自动继承给 AAOS，仅逐动作验收。

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
