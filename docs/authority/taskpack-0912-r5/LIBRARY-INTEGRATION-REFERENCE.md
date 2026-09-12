# ArcheAxis｜开源能力与知识资源承接规划

日期：2026-09-08。性质：基于当日审计的实施规划补充，尚未实施。

唯一项目主体：ArcheAxis Knowledge／星环知识平台（仓库 DTALEX66/ArcheAxis-Knowledge-OS）。DSH、CODEX、HERMES 是执行工具或类比，不是本规划的产品主体。

本文件承接 `AAK-REUSE-FIRST-20260907-R2` 的 23 项冻结任务，不替换 TASKS.json、不重编号、不另建活动任务图。文中的步骤、资源包名称都是原任务内的实施切片或候选，不是新的独立项目。未修改产品源码、未推送仓库、未在用户 Windows 上部署或清理。

## 1. 决策与审计基线

本轮重新读取远端分支列表，`codex/full-loop-0906` 仍为 `cbe253b107da0e8b6d55505bd9c3c2d8de59b7ed`；`main` 仍为 `4ca46eaf94c486dadcf200aac6b41cd968b1ce6e`。当日审计结论继续作为规划前提：Q00 不通过，Q01 尚未具备通过条件。本轮做针对性读取和方案核对，没有重复执行完整审计或本地测试。

读取依据：

- [现行 AGENTS.md](https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/blob/cbe253b107da0e8b6d55505bd9c3c2d8de59b7ed/AGENTS.md)
- [冻结 TASKS.json](https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/blob/cbe253b107da0e8b6d55505bd9c3c2d8de59b7ed/docs/authority/taskpack-0907/TASKS.json)
- [夜间执行摘要](https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/blob/cbe253b107da0e8b6d55505bd9c3c2d8de59b7ed/docs/authority/taskpack-0907/OVERNIGHT-RESULTS-2026-09-08.md)
- [16 个能力域蓝图](https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/blob/cbe253b107da0e8b6d55505bd9c3c2d8de59b7ed/docs/truth/CAPABILITY_ATLAS_V2.yaml)
- [开源登记契约 V2](https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/blob/cbe253b107da0e8b6d55505bd9c3c2d8de59b7ed/docs/contracts/OPEN_SOURCE_REGISTRY_V2.md)

能力蓝图里的历史 horizon、Tauri 等旧实现标记不应覆盖 R2 已决定的人机双侧首版和 C#/Avalonia 方向。X00/X13 应对齐当前索引，保留历史事实，不篡改旧证据 SHA。

### 1.1 必须先处理的审计问题

| 原审计项 | 回归原任务 | 对资源接入的直接影响 | 接入前验收 |
|---|---|---|---|
| C03：审校 new_body 可覆盖原知识正文 | X04、X05、X07 | 外部题目、记忆、引用会失去稳定含义 | 接受/拒绝/撤销不能改正文；修改生成新修订，保留旧内容和 supersedes 关系 |
| C03/C04：v3 归档表集合变化导致旧包不兼容 | X05、X10 | 升级插件或资料包后可能无法恢复旧数据 | 用上一版本生成的非空备份在新版恢复；明确归档版本迁移，不仅测试新版自往返 |
| C05：学习事件同 key 异内容被当成重复成功 | X04、X08 | DeepTutor、Anki、H5P 事件回流可能丢失或重复 | 相同身份与内容重试幂等；key 冲突拒绝；无 key 的行为有明确契约 |
| C07：网络/模型运行成功被当作事实支持 | X07 | 多接几个 API 会扩大错误核查结论 | 运行状态与支持/反证/无法判断分离；对象、单位、时间与原文证据对应 |
| C02：未知启动 actor 默认落 human 等边界 | X04、X09 | 新客户端可能继承过宽权限 | 无效身份拒绝；实际会话授权决定角色，凭据与进程边界验证 |
| C07：统一多格式 executor 未闭合 | X05、X06 | 每加格式都可能另起一条孤立管线 | 所有已启用引擎经同一作业状态、收据、取消、恢复和 Rust 入库 |
| C08/C05/C06：界面、人学、机用未接通 | X03、X08、X09、X11 | 工具安装成功仍不能形成可用产品 | 同一资料完成真实学习与机器任务，结果进入 Core 并可重启读回 |
| C10：容量统计口径不完整、target 再增长 | X01、X14 | 新模型、索引、容器使仓库继续膨胀 | 分清代码、构建缓存、唯一数据、模型和依赖；统一计量并验证止增 |

不能把 19.146 GiB 当成全仓大小：报告明确排除了 `.hermes` 等，另列 `.hermes` 约 42.853 GiB。不得据算术相加或历史摘要宣称精确总占用、实际释放空间或清理已完成。

### 1.2 总体选择

1. 保留 ArcheAxis Rust Core、Python workers、C#/Avalonia 壳及可复用 Web/TypeScript 交互层，不启动全量语言迁移。
2. 默认继续验证和接通已运行的 DeepTutor；不因发现 AnythingLLM、PrivateGPT、Dify 而更换学习主入口。
3. 保留共同知识管线、人类学习、机器学习和双向反馈四个产品部分。
4. 复用顺序：现有可用实现 → 现有供体的必要适配 → 官方 API/SDK/CLI/可部署服务 → 有证据的替代 → 必要独立实现。
5. 免费本地能力构成核心；免费在线资源做按需补充。无外网、无付费 Key 不应阻止本地保存、学习、检索与机器任务。
6. 原 X07 关于真实联网核查的验收仍保留。离线样例可测试解析和状态逻辑，但不能替代联网资格；不暗中删除任何明确要求的云端验证门。
7. 3D、动画、仿真、大型知识宫殿、VR/AR 全部保留；冻结的是重型自研和首版默认启动，不是需求。

## 2. 先承接仓库已有资产

以下结论来自本轮读取的路径与内容；“有文件”不等于对应能力已经完成生产接入。

| 现有资产 | 已知情况 | 承接方式 | 原任务 |
|---|---|---|---|
| `services/python-workers/document/`、`web/`、`vision/`、`media/` | 已有 Office、字幕、Canvas、网页、OCR、转录等脚本；README 明确多格式完整调用链仍有缺口 | 复用算法与行为，接统一 NDJSON/executor；不要新增平行导入库 | X02、X05、X06、X12 |
| `services/python-workers/transport/text_ndjson.py` 与 Rust executor | 已有文本通道和作业执行基础 | 扩展受控引擎选择、格式输出和进程树取消；不接受 HTTP 任意可执行路径 | X05、X06 |
| `app/integrations/deeptutor_bridge.py` | 有投影/事件概念，但代码使用 sqlite3 及旧 learning event store | 保留字段映射和测试语义；vNext 改走 Core API，不让 Python 直接读写主库 | X02、X03、X04、X08 |
| `app/adapters/deeptutor/authority.py` | 有只接收候选事件、拒绝权威状态字段的逻辑 | 作为边界供体，结合真实身份、修订和幂等契约接线 | X04、X08 |
| `app/adapters/anki_zotero.py` | 实际是 Anki CSV 导出与 Zotero JSON 解析，没有默认 live HTTP | 先复用无损导出/导入；需要自动事件回收再接 AnkiConnect 或 Zotero 本地 API | X08、X12 |
| `app/knowledge/due_queue.py` 与旧学习代码 | 有旧 kb_cards/kb_reviews 读取和排程相关资产；夜间摘要报告 FSRS 供体探测通过 | 拆出可复用计算与记录映射，不能把旧库访问照搬入 vNext | X02、X08 |
| `app/ingestion/rapid_ocr_adapter.py` | 已有 RapidOCR 包装；当前包装只返回文本，未保留全部框坐标 | 中文 OCR 先复用，但补页/区域框及置信/损失信息，符合锚点契约 | X06、X12 |
| `app/rag/retriever.py` | 有旧检索封装和启发式 score | 不能把该分数当事实准确率；按 vNext 资格过滤接真实检索出口 | X07、X09 |
| `packages/contracts/v1/` | 已有 worker、anchor、learning-feedback、machine-feedback、quality 等契约 | 在现有版本政策下扩充，不再发明另一套同义事件格式 | X04 |
| `config/tools.yaml` | 产品内部受控工具风险登记，明确不是全局 Agent 权限平台 | 使用其职责范围；组件版本/安装元数据另按已有开源登记契约承接，不把一切权限塞进该文件 | X00、X04、X09 |

路径来源：[workers 说明](https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/blob/cbe253b107da0e8b6d55505bd9c3c2d8de59b7ed/services/python-workers/README.md)、[DeepTutor 桥接](https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/blob/cbe253b107da0e8b6d55505bd9c3c2d8de59b7ed/app/integrations/deeptutor_bridge.py)、[Anki/Zotero 适配](https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/blob/cbe253b107da0e8b6d55505bd9c3c2d8de59b7ed/app/adapters/anki_zotero.py)、[运行 API](https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/blob/cbe253b107da0e8b6d55505bd9c3c2d8de59b7ed/crates/archeaxis-api/src/runtime/mod.rs)。

## 3. 模块化的边界：能力可换，权威数据不分裂

| 层 | ArcheAxis 负责 | 外部组件负责 | 明确限制 |
|---|---|---|---|
| 原件与知识 | 原件哈希、来源、修订、关系、审校、核查、资格 | 下载/解析后提交候选材料和收据 | 插件不能自行宣布 verified 或覆写旧修订 |
| 作业 | 身份、队列、attempt、预算、超时、取消、恢复 | 在限定输入输出范围内计算 | 外部流程不能另建权威完成状态 |
| 检索 | 范围、可用修订、原文定位和返回前资格检查 | 本地/远程检索候选、可重建索引 | 索引命中不自动成为现行可信知识 |
| 人类学习 | 学习事件、知识依赖、解释/练习/复习记录 | Tutor 界面、活动播放器、FSRS 计算或 Anki 调度 | 外部评分不直接等于理解/掌握；一个集合一个排程权威 |
| 机器学习 | 方法与经验版本、能力评测、纠错审查、可调用范围 | 本地模型、受控工具、记忆候选、评测执行 | 检索/记忆更新不宣称权重训练；机器不能自授接受权限 |
| 表现与空间 | 知识对象和位置的稳定 ID、学习事件 | 图谱、动画、3D 渲染、交互 | 引擎更换不应改变知识 ID 或丢失空间绑定 |
| 备份与同步 | 一致导出、归档版本、恢复资格 | 搬运和保存完成的快照包 | 不同步活动数据库冒充一致备份 |

采用四种模块即可：内容包、原生扩展、独立本地服务、命令行/库组件。首版不建 Marketplace、不做通用插件 SDK、不建第二个 Agent Runtime；这些仍承接 F04/F06 后置范围。

### 3.1 可立即采用的连接方式

- Python 能力处理：复用现有 Core 管理的 NDJSON 子进程通道，重依赖可用各自锁定环境。
- 本地独立软件：通过既有 HTTP API 或 CLI 适配；不直接打开其活动数据库修改内容。
- 机器消费者：按 X09 使用官方 MCP SDK 与已有 Core API 暴露 search/get/source/context/feedback/proposal。
- 学习/3D 界面：本地 Web UI 或浏览器先交付；Avalonia 负责生命周期和打开入口，不重写上游 UI。
- 外部知识包：按其原始格式保管。全文索引可复用则直接查询；选定条目需要作为证据时，再形成可追溯的 Core 原件/快照和锚点。

MCP 只是连接协议，不自动提供安装管理、访问隔离、统一成绩或索引迁移。已有 HTTP/CLI 足够时不为“插件化”强行套 MCP。

### 3.2 最小生命周期

登记候选 → 固定上游版本和许可 → 单组件样本探测 → 经 Core 集成 → 真实人机使用验收 → 允许启用。

每一步使用现有 Registry V2 与执行台账的状态字段。`verified` 只对指定版本、环境和能力成立；未知版本、实际安装目录、哈希、运行证据保持 null/未验证，禁止填猜测值。

最小运行功能为启用/停用、健康检查、依赖诊断、版本显示、重试/取消和回滚。插件停用保留原件、笔记、方法、学习记录；只有已确认可重建的派生缓存可以清理。

## 4. 资源登记总表

阶段说明：

- **首版承接**：属于当前 X 任务闭环，优先复用已有资产；不是本轮已部署。
- **M1 按需**：Q00 后按具体资料/学科启用，非全量安装。
- **后置保留**：映射 F01–F06 或明确候选触发条件。
- **参考/未核实**：不能放入自动部署清单。

“本地”表示相应软件/内容可以在本机使用；依赖、模型、字体、播放器库等必须预备齐全。免费指选定自托管/开放内容路径不产生强制软件或 API 费用，硬件、电力、磁盘成本仍存在。软件、模型、内容的许可分别核查。

### 4.1 内容资源与外部知识源

| 资源 | 本地化与真实内容 | ArcheAxis 接入方式 | 阶段/原任务 | 取舍与限制 |
|---|---|---|---|---|
| [Kiwix／ZIM](https://get.kiwix.org/en/solutions/catalog/) | 离线百科、教育等打包内容 | 先一个中文包；kiwix-serve 搜索/浏览适配 | M1 按需；X07、X12 | 不全量解包重嵌入；全文搜索要求包内有索引 |
| [OpenStax](https://openstax.org/subjects) | 可下载教材 PDF | 通用导入器，章节/页码锚点 | 首版样本；X06、X08 | 先选一册匹配学科的教材，不下载全部 |
| [MIT OCW](https://ocw.mit.edu/pages/get-started/) | 课程讲义、作业、考试等 | Course/材料关联；下载文件进入同一管线 | M1；X12、F05 | 视频与外链单独确认；有材料不等于自动课程成绩 |
| [OpenLearn](https://www.open.edu/openlearn/free-courses) | 开放课程与文章 | 先链接/允许下载的材料 | M1；X12、F05 | 不假设整个课程所有互动均可离线复用 |
| [Gutenberg](https://www.gutenberg.org/)／[GITenberg](https://github.com/GITenberg) | 公版图书、部分文本仓库 | EPUB/TXT/HTML 通用导入 | M1；X12 | 各地公版范围、图片与版本分别记录 |
| [Standard Ebooks](https://standardebooks.org/ebooks) | 精排经典电子书 | 按单本下载导入 | M1；X12 | 单本免费；官方批量下载支持者条件不作为默认依赖 |
| [OAPEN](https://library.oapen.org/) | 开放学术专著与章节 | PDF/书目信息 | M1；X12、F05 | 按书确认许可证 |
| [Kanripo](https://github.com/kanripo) | 古籍原文 | 选定书籍快照，卷章段定位 | M1；X12 | 不为每本书创建插件；同一文本导入器复用 |
| [chinese-poetry](https://github.com/chinese-poetry/chinese-poetry) | 社区汇集诗词 JSON | 篇/作者/题名映射及原记录保留 | M1；X12 | 可检索不代表校勘准确；不同版本不静默合并 |
| [CBETA XML-P5](https://github.com/cbeta-org/xml-p5) | TEI XML 佛典 | XML 结构保留、卷行定位 | M1；X12 | 尊重具体版权声明和缺字信息 |
| [CText](https://ctext.org/tools/api) | 古籍在线服务 | 可用免费范围内查询，或用户合法材料导入 | 后置可选；F05 | 增强 API 涉及订阅；不得作为免费核心依赖 |
| [Wikidata](https://www.wikidata.org/wiki/Wikidata%3ADatabase_download) | JSON/RDF 实体关系数据，不是全文百科 | 在线选题查询/本地专题子集 | X07 小范围；全量 F05 | 不先部署全量图数据库；事实仍回原来源验证 |
| [OpenAlex](https://openalex.org/pricing) | 学术目录、引用关系等；有下载数据 | 查询缓存、DOI 和来源合并 | X07/F05 按需 | 使用免费额度，禁止自动付费升级；不是全篇论文库 |
| [Crossref](https://www.crossref.org/documentation/retrieve-metadata/rest-api/) | DOI、出版元数据等 | 书目解析与同源去重 | X07 首批在线源 | 只拿到书目不能判定论文支持某主张 |
| [DataCite](https://support.datacite.org/docs/rest-api) | 数据集/软件等 DOI 元数据 | 补研究数据与方法来源 | X07、F05 | Public API 无认证；元数据不是数据集本身 |
| [arXiv](https://info.arxiv.org/help/api/index.html) | 预印本目录及论文链接 | 搜索后按需下载论文 | M1；X07、X12 | 预印本状态保留；API 与全文获取分开 |
| [Europe PMC](https://europepmc.org/RestfulWebService) | 生物医学目录、摘要及允许提供的全文 | 专题查询＋开放全文 | M1；X07、X12 | 非所有记录均提供全文 |
| [PMC Article Datasets](https://pmc.ncbi.nlm.nih.gov/tools/textmining/) | 允许下载复用的论文数据集 | 精选全文或专题包 | M1；X12 | 旧 OA Web Service 已停止，使用当前入口；记录撤稿/更正 |
| [Semantic Scholar](https://www.semanticscholar.org/product/api) | 学术检索与关系 | 可选免费查询源 | F05/按需 | 与 OpenAlex 多为重叠目录，不重复当独立证据 |
| [Unpaywall](https://unpaywall.org/products/api) | DOI 对应开放全文位置 | 文献定位辅助 | X07/按需 | 不是全文存储本身，不保证每篇有开放版本 |
| [CORE](https://core.ac.uk/services/api) | 开放学术聚合与部分全文 | 免费限流路径内查询 | F05/按需 | 配额、认证及全文范围按执行时版本核对 |
| [World Bank](https://datahelpdesk.worldbank.org/knowledgebase/articles/889392-about-the-indicators-api-documentation) | 社会经济时间序列 | API 缓存→结构化表格→计算/图表 | M1；X12、F05 | 单位、国家编码、年份、缺失值必须保留 |
| [美国国会图书馆](https://www.loc.gov/apis/json-and-yaml/) | 文献、照片、地图等元数据与资产链接 | 主题包＋逐资产下载 | F05/学科包 | 馆藏记录与附件权利分开 |
| [The Met](https://metmuseum.github.io/) | 艺术藏品信息及开放图片 | 艺术史知识对象和图像原件 | F01/F05 | 仅下载符合开放条件的具体图片 |
| [Smithsonian](https://www.si.edu/openaccess/devtools) | 馆藏信息、部分图片/3D 等 | 内容包＋模型渲染器 | F01、F02 | 逐资产核查许可、格式、依赖和大小 |
| [Geofabrik](https://download.geofabrik.de/) | OSM 地区数据 | 需要真实地图时选择地区包 | F01/F02 | 不用地理地图替代知识宫殿语义 |
| **新增：[Open Library](https://openlibrary.org/developers/dumps)** | 图书/作者/版本目录 dump | 书目补全与作品版本关系 | F05 | 下载目录不等于获得所有图书全文 |
| **新增：[PubChem](https://pubchem.ncbi.nlm.nih.gov/docs/downloads)** | 化学实体与相关结构化数据 | 选定实体 JSON/结构数据→学科对象 | X12/F05 按需 | 保留来源和单位；不要先镜像全站 |
| **新增：[RCSB PDB](https://www.rcsb.org/docs/programmatic-access/file-download-services)** | 可下载生物大分子结构 | 结构文件＋说明→Mol* 活动 | F01/学科包 | 很适合真实 3D 学习；不是通用宫殿引擎 |
| **新增：[GBIF](https://techdocs.gbif.org/en/openapi/)** | 物种与分布等数据 | 专题查询或有限下载 | X12/F05 按需 | 部分批量下载需注册认证；记录数据集许可 |
| **新增：[Natural Earth](https://www.naturalearthdata.com/downloads/)** | 公共领域地图数据 | 地理/历史教学底图 | F01/学科包 | 按尺度选择；不作为导航或实时地图 |

首版额外内容只需一份有许可的教材样本；Kiwix 大包和专题资源可在 M1 扩展。联网核查从明确主张选择合适的原始出处，不能为了接 API 而制造不相关资料任务。

### 4.2 软件宿主、知识管理与记忆组件

| 项目 | 模块角色 | 承接决定 | 原任务/触发条件 |
|---|---|---|---|
| [DeepTutor](https://github.com/HKUDS/DeepTutor) | 人类学习工作台 | 默认继续，固定已验证上游版本，补 Core 适配和事件回收 | X03、X08、X11；不把夜间生成成功当完整集成 |
| [Anki/AnkiConnect](https://ankiweb.net/shared/info/2055492159) | 成熟复习工具 | 复用现有桥接；每个复习集合只选一个排程权威 | X08；CSV 是导出能力，不是自动事件回收 |
| [思源](https://github.com/siyuan-note/siyuan) | 本地笔记软件 | 保留为用户选择的互操作目标，不替换当前 Obsidian 优先路线 | X12 后续切片；核心本地与付费同步分开 |
| [TiddlyWiki](https://github.com/Jermolene/TiddlyWiki5) | 单文件便携笔记 | 内容导入导出或只读发布候选 | F04/F05；不为其重建核心数据库 |
| [LeafWiki](https://github.com/perber/leafwiki) | Go 文档 Wiki | 简单文档站候选，正确仓库为 perber | F04；当前无缺口不安装 |
| [AFFiNE](https://github.com/toeverything/AFFiNE) | 文档和白板 | 白板需求的候选，先复用 JSON Canvas | X12/F01；本地自托管不等于所有 AI 功能免费 |
| [Outline](https://github.com/outline/outline) | 团队 Wiki | 当前后置 | F04；团队协作/认证依赖不适合首版负担 |
| [AnythingLLM](https://github.com/Mintplex-Labs/anything-llm) | 本地问答成品 | 体验对照或局部备用，不替代 DeepTutor/ArcheAxis | 仅 X03 有具体失败证据时试一个备选；不是完整教学替代品 |
| [PrivateGPT](https://github.com/zylon-ai/private-gpt) | 本地 AI 应用 API 后端 | 暂不默认部署，避免第二套摄取、存储和工具权威 | X09/F06 的具体缺口才实测；必要时只用限定服务能力 |
| [Open WebUI](https://docs.openwebui.com/features/extensibility/plugin/) | 聊天与工具扩展界面 | 机器调用调试/对照候选 | X09 有需要再用；不能据此换项目主体 |
| [Dify](https://docs.dify.ai/en/develop-plugin/getting-started/getting-started-dify-plugin) | 可视化 AI 编排平台 | 后置参考；不接管 Core jobs | F04/F06；免费社区版与商业功能区分 |
| [Node-RED](https://github.com/node-red/node-red) | 外部自动化节点流程 | 仅未来补外围采集/定时触发 | F04；当前队列、重试、取消在 Core，不添第二调度权威 |
| [Langflow](https://github.com/langflow-ai/langflow) | AI 可视化组件编排 | 研究/流程试验候选 | F03/F05；不作为运行前置 |
| [Haystack](https://docs.haystack.deepset.ai/docs/integrations) | 检索与 Agent 管线框架 | 有复杂检索缺口时复用限定组件 | F05/F06；现有检索可用则不再造管线 |
| [RAGFlow](https://ragflow.io/docs/) | 文档解析/RAG 一体服务 | 重型备选，不默认安装 | X12 复杂文档质量/吞吐证据证明需要才评估 |
| [Mem0](https://docs.mem0.ai/cookbooks/companions/local-companion-ollama) | 记忆提取/检索 | 后置限定试验；输出候选、索引可重建 | F03；LLM 与 embedding 均本地，禁止写权威事实 |
| [Cognee](https://docs.cognee.ai/guides/local-setup) | 图谱记忆 | 后置限定试验 | F03/F05；缺少跨文档关联能力时启用，不先搭完整图谱 |
| [Qdrant](https://qdrant.tech/documentation/quickstart/) | 向量引擎 | 先复用现有索引；多消费者/规模需求证据出现再切换 | X07/F05；不宣称 RAG 必须 Qdrant |
| [Chroma](https://github.com/chroma-core/chroma) | 向量引擎 | 同 Qdrant，作为可替换备选 | X07/F05；不同时建多套相同向量索引 |
| [Kolibri](https://github.com/learningequality/kolibri) | 离线课程与学习平台 | 特定课程包候选，可独立打开 | X12/F05；课程内容单独下载和审许可，不假设自动回流 |
| [IIAB](https://github.com/iiab/iiab)、[RACHEL](https://rachel.worldpossible.org/) | 离线内容门户 | 内容组织和离线打包参考 | F04/F05；已有 ArcheAxis 不再套一整层门户 |
| [OFFLINED](https://github.com/Aruvaro-Chulvi/OFFLINED)、[Alexandria](https://github.com/rquezada-tech/alexandria) | 离线整机候选 | 仅确认仓库存在，能力/许可/维护仍需具体审查 | 参考，不列自动部署 |
| Project-NOMAD | 离线整机对标 | 本轮未独立核实确切来源和能力 | 参考，不继承其内置组件宣传作为证据 |

### 4.3 采集、解析、计算、表现与运维组件

| 组件 | 用途/接法 | 承接与部署决定 | 原任务 |
|---|---|---|---|
| [MarkItDown](https://github.com/microsoft/markitdown) | 文件转 Markdown，CLI/库 | 已有蓝图依赖；普通转换先复用，收费增强不开启 | X06、X12 |
| [Docling](https://github.com/docling-project/docling) | PDF 版面/表格等结构提取 | 现有复杂样本失败时新增一个专用 worker，预置模型 | X06、X12 |
| [RapidOCR](https://github.com/RapidAI/RapidOCR) | 中文等 OCR | 已有供体，先接坐标/逐页路由；不当新发现从头写 | X06、X12 |
| [Tesseract](https://github.com/tesseract-ocr/tesseract) | OCR | 已有 worker，保留回退和基准样例 | X06 |
| [faster-whisper](https://github.com/SYSTRAN/faster-whisper) | 音频转录 | 已有 worker，补时间戳、语种和失败回执 | X12；非首版必需大模型下载 |
| [FFmpeg](https://ffmpeg.org/) | 音轨/视频帧/媒体转换 | 已有 worker；按需求启用，版本与构建许可固定 | X12 |
| [Magika](https://github.com/google/magika) | 内容型文件格式识别 | 蓝图已列；可补路由，不将格式识别当安全判定 | X06、X12 |
| [PyMuPDF](https://github.com/pymupdf/PyMuPDF) | PDF 读取等 | 现有 Office worker 依赖先核验锁定版；不引入 Pro 试用作为免费能力 | X06、X12 |
| [Marker](https://github.com/datalab-to/marker) | 复杂文档转换 | 仅 Docling/现有引擎失败时比较；软件与模型许可分别记录 | X12/F06 后置 |
| [Playwright MCP](https://github.com/microsoft/playwright-mcp)／Playwright | 动态网页和真实浏览器操作 | 采集优先已有 Playwright 路由；MCP 只在真实机器调用确有需要时用 | X06、X09 |
| [ArchiveBox](https://github.com/ArchiveBox/ArchiveBox) | 网页长期归档 | 先已有原件快照；大量归档需求出现再独立服务 | X12/F05；抓取联网，已保存可本地读取 |
| [warcio](https://github.com/webrecorder/warcio) | WARC 读写 | 需要标准归档交换时作为 Python 库 | X12/F04 |
| [CyberChef](https://github.com/gchq/CyberChef) | 编码和数据配方 | 可作为离线辅助工具或固定配方供体 | X12/按需；不是核心知识库 |
| [Paperless-ngx](https://docs.paperless-ngx.com/api/) | 扫描件管理、OCR、全文搜索 | 用户已有或扫描归档工作量明确时接 API；不默认复制原件 | X12/按需 |
| [DevDocs](https://devdocs.io/offline) | 离线开发文档 | 文档包/独立阅读入口，机器接入仍需检索适配 | X12/F05 |
| **新增/明确：[Zotero 本地 API](https://www.zotero.org/support/dev/web_api/v3/local_api)** | 书目、附件与笔记关联 | 先当前 JSON 导入；只读 API 后接，写能力按安装版探测 | X12/F05；不直写 Zotero SQLite |
| **新增：[DuckDB](https://duckdb.org/why_duckdb.html)** | CSV/Parquet 等结构数据计算 | Python worker 内查询受控材料；不是第二权威主库 | X12/F05 |
| **新增：[SymPy](https://github.com/sympy/sympy)** | 确定性符号计算 | 数学活动/机器方法检验的可选 worker | X08、X09、X12；按学科启用 |
| **新增：[Promptfoo](https://github.com/promptfoo/promptfoo)** | 模型、RAG、工具输出比较 | 仅既有评测工具不足时用本地 CLI；固定断言/金标优先 | X09、X11；不用模型自评替代独立验收 |
| [PhET](https://phet.colorado.edu/en/help-center/offline) | 现成互动实验 | 首版选一个可下载活动；无法回收成绩时标记外部活动 | X08；广泛学科库 X12/F01 |
| [H5P](https://h5p.org/documentation/x-api) | 交互题目/视频，xAPI 事件 | 现成内容先；事件需映射到 Core，不自动成立 | X12、F01 |
| **新增：[h5p-standalone](https://github.com/tunapanda/h5p-standalone)** | 本地播放已有 H5P 包 | 作为播放器候选，不等于完整 H5P 编辑器；JS 依赖和事件实测 | X12、F01 |
| [GeoGebra](https://www.geogebra.org/license) | 数学交互 | 个人非商业使用的具体版本/资源可选；与开源许可分别标记 | X12、F01 |
| **新增：[Cytoscape.js](https://js.cytoscape.org/)** | 图谱可视化 | 将 Core 图投影到 Web，先邻域展开；不作为权威数据库 | F01、F05；现有图谱组件可用则不换 |
| [model-viewer](https://modelviewer.dev/) | 展示本地 glTF/GLB 等模型 | 3D 对象和热点的优先小组件；加载器/解码器本地打包 | F01/F02；浏览器 3D 与设备 AR 资格分开 |
| [Manim](https://www.manim.community/) | 可复现数学动画视频 | Python 渲染 worker，输入参数和版本留存 | F01；渲染视频不等于交互仿真 |
| **新增：[Mol*](https://github.com/molstar/molstar)** | 分子结构 3D 查看 | 配 RCSB PDB 本地结构文件，学科活动包 | F01；无相关学习需求不部署 |
| [Babylon.js](https://github.com/BabylonJS/Babylon.js) | 更完整 3D 场景 | 宫殿场景候选，待小场景试验后选；不固定永久引擎 | F02 |
| [Rclone](https://github.com/rclone/rclone) | 数据传输 | 同步导出包/选定内容，命令行方式 | X14/F04；不能替代一致导出 |
| [Syncthing](https://github.com/syncthing/syncthing) | 多设备文件同步 | 稳定内容与封闭快照；活动 DB 不直接同步 | F04；多端冲突治理后置 |
| **新增：[Restic](https://github.com/restic/restic)** | 去重加密备份 | 备份已完成的 Core 导出与唯一用户产物 | X05/F04；不能解决有缺陷的旧归档兼容 |
| [LOCKSS](https://github.com/lockss/lockss-daemon) | 图书馆级保存 | 仅参考，个人首版不用 | F04/F05 |
| [Protomaps](https://github.com/protomaps/protomaps)、[Organic Maps](https://github.com/organicmaps/organicmaps) | 地图显示/离线客户端 | 地理学科的独立模块候选 | F01/F02；不是学习 OS 或通用插件宿主 |

Awesome 收藏表作为发现来源保留，不是运行依赖：[awesome-selfhosted](https://github.com/awesome-selfhosted/awesome-selfhosted)、[awesome-digital-preservation](https://github.com/ruarxive/awesome-digital-preservation)、[awesome-knowledge-management](https://github.com/brettkromkamp/awesome-knowledge-management)。本轮未逐条核查合集内容，合集内条目不能自动升级为可信候选。

豆包给出的 `gxchu/guoxuedashi`、`chinese-corpus/sikuquanshu` 前轮未能确认；“殆知阁”未提供确定可下载来源和许可。保留未核实记录，不用近似仓库静默替代；优先已核实的 Kanripo 等。

## 5. 首版具体承接：六个切片组成同一产品闭环

### 5.1 资料输入与转换切片：X05/X06

继续使用现有导入入口，原件先交 Core 建立版本与哈希。Core 选择受控引擎，生成 attempt 输入；worker 只处理被分配材料并产出收据。先连 MD、普通 PDF、图片、静态/动态网页、扫描/混合 PDF 代表样本，覆盖原 M0 格式要求；Office/媒体/EPUB/Canvas 在 X12 扩展而不删除。

普通 PDF 原生文本优先；扫描页/混合页按页或区域 OCR。中文使用现有 RapidOCR 供体验证，Tesseract 保留；复杂阅读序和表格确有失败时，才开启 Docling 专用 lane。不得一份 PDF 默认跑四种 OCR 再存四份全文。

验收：原件可读回、缺失页显式、锚点能回跳、格式输出进入同一知识流程；超时/取消/重启不会显示假成功。worker stdout 协议和日志分离，Core 独立校验输出路径及哈希。

### 5.2 知识检索与核查切片：X07

首批把现有 FTS/检索资格链接实。增加精确词、中文短词、同义改写、DOI、页码等查询样本；默认 tokenizer 不能直接视为中文效果达标。FTS5 的 trigram 适合部分子串查询，但一/二字短词要另外处理；应以实测决定分词或回退，不能简单把空格分词套到中文。[SQLite FTS5 文档](https://www.sqlite.org/fts5.html)

知识内容分三层：本地权威记录、外部已下载参考库、在线检索结果。外部结果先作为参考/候选；被引用时绑定可保留的源版本、抓取时间与位置。外部百科整包无需全部变成“已审核知识”。

在线核查按主张选择原始来源，可用 Crossref/DataCite 做来源元数据，OpenAlex 做发现，Unpaywall 定位开放全文。检索结果可能同源；按原文/DOI/出版源分组，不能将三个聚合站当三个独立证据。

核查结构分开记录运行状态和结论：请求成功可以对应支持、反证、无法判断或证据不足。没有检索到不能直接判假，人工接受不改外部核查状态，个人定义无需伪造外部支持。

### 5.3 人类学习切片：X03/X08

DeepTutor 使用 Core 提供的材料投影。题目、讲解、学习路径引用知识修订和原件锚点；学习动作回流 Core。上游笔记、会话、批注等唯一用户产物必须纳入保全，不能统称可重建缓存。

复习集合建立时明确排程权威：

- Core 管理集合：调用已有成熟 FSRS 计算供体，Python 只返回计算结果，Rust 保存事件/状态。
- Anki 管理集合：通过 AnkiConnect 或正式导出读取所需状态，Anki 负责排程，Core 记录映射与事件；不同时运行另一套 FSRS 到期时间。

首版按当前最少接线成本选择一个默认模式。CSV 导出仍保留，但单靠 CSV 不能满足自动回流验收。FSRS 评估复习安排，不证明理解和迁移。

互动活动先使用一个已许可、可离线打开的 PhET 示例，或已有活动。不能自动获取成绩时，记录“已打开/用户反馈/未采集成绩”，不能伪造完成成绩。H5P 的 xAPI 事件后续按活动真实支持范围映射，不把点击事件当掌握。

### 5.4 机器侧切片：X09

Core 以受限 MCP/API 暴露 search/get/source/context/feedback/proposal。真实客户端在本地模型或已有已授权模型上完成：获取方法与原文→执行一项具体任务→提交结果与引用→接受独立用例检验→错误反馈→候选修订→复核后再次使用。

机器资产保留 Memory/Rule/Skill/Standard/Context/Evaluation，不压缩成一个向量集合。首轮方法例可为“按用户定义规则对提供的材料分类并生成可追溯结果”，用留出的材料和反例检验。实现者不能提前把测试答案写入检索语料；结构化断言与用户/独立评价优先。

Mem0/Cognee 仅在既有机器资产难以覆盖具体长期记忆需求时补充。它们形成的记忆是候选或派生检索记录，不能直接成为权威知识。参数微调仍 F03 后置；知识更新/方法更新/权重训练分开显示。

### 5.5 双向纠错切片：X07/X08/X09

用同一知识修订生成一道题并完成一次机器调用，再撤销或修订该知识：

1. 旧原件、知识正文和历史任务保持可读。
2. 下一次人类学习显示旧题待复核，不继续以旧答案作为现行正确答案。
3. 下一次机器获取上下文按 Core 当前资格过滤，即使索引更新尚未完成也不能返回旧有效资格。
4. 正在运行的机器任务提交结果时再次检查其所依赖修订；过期依赖不能作为有效现行结果入库。
5. 修复后新题、新上下文指向新修订，旧历史标识已过时。

导出的离线知识包只能保证导出时快照状态，不能远程即时撤回。记录导出时间、依赖版本及重新核验状态；脱网时明确“未重新核验”，不假装永远有效。

### 5.6 Windows 交付切片：X11/Q00

交付一个能启动的 ArcheAxis 入口，连接已验证 Core、workers、本地模型和学习界面。允许本地浏览器先展示 DeepTutor。界面至少能看到资料、搜索、学习、机器任务与反馈、备份/恢复、能力缺失状态；不要求首版重做全部设计稿。

打包固定源码 SHA、依赖锁和候选文件哈希；真实安装态验证，无开发环境隐藏依赖。模型或内容未安装时显示下载需求/离线不可用原因，不能返回空成功。Q00 仍由独立审计决定。

## 6. M1 和后续内容包怎样扩展

内容包是资源集合及调用配置，不是再起一个产品仓库。内容包 manifest 可以复用现有包/来源契约；只有现有字段确实不够时才按版本政策扩展。

| 包 | 最小内容 | 使用路径 | 阶段 |
|---|---|---|---|
| 通识与中文参考包 | 一个中文 ZIM＋少量已选教材/古籍 | 直接搜索→选定原文→学习/机用 | X12；不增加 Q00 首版阻塞项 |
| 文献研究包 | Zotero JSON/本地读取＋Crossref/DataCite＋一个发现源 | 书目→合法全文→证据/方法→研究记录 | X12/F05 |
| 理科互动包 | 一个 PhET 活动＋相关教材；需要时 SymPy | 阅读→实验/计算→练习→结果 | X12/F01 |
| 艺术与空间素材包 | 少量 Met/Smithsonian 开放资产＋model-viewer | 原文说明→3D/图像查看→标注/学习 | F01/F02 |
| 分子科学包 | 小批 RCSB PDB 文件＋Mol*＋相关解释 | 旋转/观察结构→问题/记录→原数据回跳 | F01；按学科需求解冻 |
| 结构数据包 | World Bank/PubChem/GBIF 子集＋DuckDB（需要时） | 数据版本→确定性计算→图表→可复核输出 | X12/F05 |
| 媒体包 | 已有 FFmpeg/faster-whisper、字幕与关键帧 | 原视频→时间戳片段→学习/机器方法 | X12 |

每种包先一个真实使用场景，验收通过再扩内容。只下载标题/书目目录的包标为“目录”，不能计入全文容量或知识吸收完成率。

## 7. 3D、动画和大型知识宫殿的保留路线

### F01：先复用表现与活动

- JSON Canvas 继续作为开放互操作基础，先保留已有节点/边/位置。
- 图谱需求：优先已有效果；缺口时试 Cytoscape.js。展示的数据来自 Core 投影，可重建。
- 精确动画：Manim 生成参数化动画，保留公式、脚本版本和输入；视频本身不当作交互实验。
- 真实互动：PhET/H5P/GeoGebra 的具体活动，界面和内容依赖本地准备；事件回收逐种活动实测。
- 单个 3D 对象：model-viewer，所有模型、纹理、字体和解码依赖本地化。AR 功能按设备另验，不影响桌面 3D 查看。

### F02：知识宫殿保持引擎无关

保留 World/Palace/Room/Locus/Object/Route/MoveMap/ReviewEvent，以及稳定位置、线索、知识绑定、修改映射。先用少量房间/对象证明绑定与学习事件闭环，再扩大规模。

渲染器只持有表现投影；场景坐标/对象 ID 与知识 ID 有明确映射。更换渲染引擎后语义 ID、路线和复习事件仍可读。Babylon.js 等只作候选，待性能、交互和维护成本试验后选一个；不永久锁死，也不同时实现多引擎。

大型场景按分区加载、LOD、实例化等成熟方式扩展；先记录目标设备、对象规模、帧率和内存预算再评测。2D 地图/文本路线作为降级。3D 展示质量、场景性能和学习效果分开验收；不声称建成宫殿就提高记忆。

F03 的完整机器学习、长期学习评估保留；F04 跨端/同步/SDK/协作保留；F05 研究课程空间保留；F06 仅处理有具体复用失败证据的必要独立实现。

## 8. 检索、内容和成本的具体约束

### 8.1 检索不重复建设

原有本地检索优先；Kiwix/Paperless 等已有可靠搜索时调用其索引。需要统一入口，最小返回为 source/provider、文档 ID、修订/快照、标题、片段、位置锚点、原文路径/URL、检索时间和当前资格。

各引擎分数不直接相加。先按来源分组展示；实际影响查找时才补融合排序。向量能力只为语义查询缺口启用，embedding 版本、维度、切片方案、语种与内容哈希进入索引身份；改变模型后索引明确失效/重建，不能混用向量。

### 8.2 零强制付费路径

核心 LLM、embedding、OCR、ASR、reranker（如启用）都指向实际本地后端；缺模型显式 unavailable。免费 API 额度用完则停止该连接器或回退本地，不自动切收费服务。OpenAlex 等服务的执行时额度、Key 和速率按官方说明复核，不承诺永久免费无限用。

不以 API 可访问推导可全文下载、可再分发或可训练模型。取得原文后保存具体许可；用户自有定义、笔记与公开素材分别标记。API 网络返回原始 JSON/元数据按需缓存，避免重复收费/重复请求。

### 8.3 模型复用

夜间报告提到本地 Ollama 与 qwen3:8b 已运行，但本轮未访问目标机。执行时从现有共享资源路径索引和配置读取实际模型，不按历史路径猜测、不因为 README 示例推荐新大模型就重新下载。LLM、OCR、嵌入等模型各自记录用途；不能用一个聊天模型覆盖所有专业识别能力。

## 9. 目录与容量治理

遵循当前目录权威、用户明确授权路径和 `docs/SHARED_RESOURCE_PATH_INDEX.md`。本规划不指定新的 D/E 盘目录，不自行把资料移动到仓库外；当前 Core 限定项目根范围的导入能力，外部资料根支持必须先实现并验证相应契约，不能靠符号链接绕过边界。

| 内容 | 存储规则 |
|---|---|
| 源码、锁文件、轻量许可说明、连接器配置模板 | 现有版本控制目录；不携带凭据/用户私密路径 |
| 开发构建、测试、临时作业与脱敏证据 | 使用 `scripts/runtime/dev.py` 管理的 `.project-local/`；每轮有清楚归属 |
| 模型、浏览器、第三方运行环境 | 复用已确认资源位置；必要的项目开发依赖按现行规则存放，避免每次试验复制 |
| 原件、知识包、学习会话、笔记、方法和反馈 | 产品数据，不是可随意删除缓存；路径由实际工作区授权决定 |
| 向量/全文索引、缩略图等派生数据 | 明确生成器/版本/源哈希和重建方式；只对真实可重建部分清理 |
| `.hermes` 历史资料 | 保全唯一会话/补丁/产物；禁止新增项目开发写入；不做整目录删除 |

清理与新资源接入同做容量台账：记录逻辑字节、计量范围、排除项、链接/硬链接处理；磁盘实际空闲变化独立记录。不得重复相加父子目录。新增组件须测“安装依赖＋模型＋内容＋索引＋临时峰值”，不能只报 pip 包大小。

默认冷启动只拉起必要 Core/界面/已选本地服务；媒体/重型解析/3D 资源按需加载。内容包先算下载、解压和索引额外空间；不因达到缓存阈值自动删唯一数据。

备份先由 Core 完成一致导出并校验，再由 Rclone/Restic 等搬运。Syncthing 只同步适合的稳定文件/快照；不让同步软件直接传播活动 DB 的部分状态。恢复必须覆盖 Core 与外部软件中唯一用户产物，不能只恢复可重建投影。

## 10. 沿原任务执行的顺序与交付物

下面是原任务内的切片顺序，不更改被冻结的任务依赖。选择一个获授权执行器连续执行；需要独立审计时才交 Q00/Q01。4 小时等限时只是试验止损建议，不能当完成承诺。

| 顺序 | 原任务/原审计项 | 工作与可见交付 | 进入下一步的条件 |
|---|---|---|---|
| 1 | X00、X02、X13 / C01 | 把本补充映射现有入口、更新过时语言/执行索引；列当前供体与候选 | 无平行任务权威、无现有需求删除；不以登记当完成 |
| 2 | X01、X14 / C10 | 先止增、只读盘点、确认可重建缓存和唯一资料 | 已有路径/授权；容量口径明确，可与后续代码工作交错 |
| 3 | X04、X05、X07、X10 / C02–C04 | 修角色、知识修订、事务、归档向后兼容；非空迁移差分 | 相关数据完整性/失败用例通过；不覆盖用户活动库 |
| 4 | X04、X08 / C05 | 修学习事件身份、冲突与幂等；选择唯一复习排程 | 重试、冲突、重启正确，无静默丢事件 |
| 5 | X05、X06 / C07 | 接统一多格式 executor，优先已有 workers | 首版代表格式走同一作业/收据/锚点/恢复 |
| 6 | X07 / C03、C07 | 接中文搜索、原文定位与真实公开核查 | 状态与证据分离；同源去重；网络失败不冒充核查 |
| 7 | X03、X08 / C05、C08 | Core–DeepTutor 适配，阅读/练习/讲回/复习和一项活动 | 真实人类轨迹和记录回收，撤销后题目待复核 |
| 8 | X09 / C06 | 真实 MCP/API 客户端完成方法应用、评测和纠错 | 有实际输入输出、引用和反例，不止工具列表 |
| 9 | X10、X11 / C04、C09 | 非空迁移/恢复、Windows 候选包和同源集成场景 | 源码 SHA/包哈希一致、同一资料人机闭环 |
| 10 | Q00 | 独立 M0 审计 | 按 G01–G14 判 PASS/FAIL/NOT_VERIFIED，失败回原 X |
| 11 | X12、X13、X14 | 加精选内容包、16组格式、Vault/Canvas往返、规范和容量收口 | M0 不回归；扩展逐包启用，不全量安装 |
| 12 | Q01 | 独立 M1 和清理资格审计 | 不混淆发布资格与全部长期蓝图完成率 |
| 后续 | F01–F06 | 按具体需求解冻图谱/动画/宫殿/长期学习/跨端/必要自研 | 先已有开源能力实测；有边界、维护成本、验收和回滚 |

候选止损：DeepTutor 继续沿 X03 原有限时验证规则。某库失败时，先记录失败样本、错误和缺失能力；只有当前用户路径被阻断且无可用回退，才评一个替代候选。避免同时试多个宿主。

## 11. 统一验收样本与发布门

### 11.1 最小样本集

- 用户自定义规则/假说一份：允许无外部证据保存与学习。
- 非空中文 Markdown 两篇：双向链接、标题/块定位和外部编辑冲突。
- 正常 PDF、扫描 PDF、混合 PDF、图像、静态网页、动态网页：按 M0 原有格式要求。
- 一个能找到公开出处的事实及一条相反/不相关证据：测试支持、反证、无法判断和运行失败。
- 一份有权使用的教材：用于人类讲解、练习和真实机器方法任务。
- 一个现成互动活动：记录能够实际取得的事件，无法取得的字段不造值。
- 旧版非空备份包和迁移 fixture：由旧版格式真正生成，不用新版模拟自己证明兼容。

评测标识精确绑定知识/原件/模型/插件版本；留出用例不得混入训练或检索答案库。真实私密库未提供时用合法合成/公开材料证明软件路径，明确用户真实库资格未完成。

### 11.2 必测行为

1. 断网后重启：本地资料可搜、已装模型可用、未装资源明确不可用；不隐式下载依赖。
2. 中文短词、原句和语义改写：记录 hit@k/召回样例、未命中原因；不以模型自信度作准确率。
3. 真正的原文回跳：页码/卷章/时间戳/框坐标与原件一致，失效锚点显式。
4. 重复任务、事件 key 冲突、取消、进程异常、重启恢复：无假成功、无重复计分。
5. 真实人类学习和机器任务：同一资料产生不同侧状态，不能“人学会=机器会用”。
6. 知识修订/撤销：旧题、旧上下文和运行中结果资格联动，历史保留。
7. 备份恢复与迁移：旧包兼容、篡改拒绝、完整计数、唯一用户产物保全。
8. 组件停用/回滚：其他已发布能力仍可用，不删除原件和用户产物。
9. Windows 安装态启动：相关依赖实际可定位，路径含中文/空格的情况实测。
10. 容量：安装前后、索引前后、清理前后和重建后的实际占用；`.hermes` 无新增项目开发写入。

性能不填虚假承诺。首轮记录目标机 CPU/GPU/RAM、资料数量/字节、冷/热状态、查询与生成分别耗时、索引耗时、峰值内存/磁盘；用真实基线决定优化。选择数据库/模型不以 README 峰值指标替代本项目测试。

## 12. 16 个能力域与后续需求的覆盖

| 能力域 | 本规划承接 | 任务 |
|---|---|---|
| CAP-0010 原件与来源 | 原件/CAS/内容包/元数据/可追溯下载 | X05、X06、X10 |
| CAP-0020 多格式转换 | 现有 workers，必要时 Docling；所有16组格式保留 | X06、X12 |
| CAP-0030 证据与核验 | 原文锚点、公开来源、状态分离、反证与撤销 | X04、X07 |
| CAP-0040 人类深度学习 | DeepTutor、成熟FSRS/Anki、讲回、练习、迁移 | X03、X08、X12 |
| CAP-0050 AI资产与调用 | 真实MCP/API任务、方法、评测、反馈；完整纵深保留 | X09、F03 |
| CAP-0060 视觉教学 | 现成活动/课件、来源绑定、静态降级 | X08、F01 |
| CAP-0070 动态解释与仿真 | PhET/H5P/Manim/SymPy按需 | X12、F01 |
| CAP-0080 空间记忆 | 宫殿稳定ID、路线与复习绑定、引擎无关 | F02 |
| CAP-0090 研究课程项目 | 文献包、数据集、课程/输出证据 | F05 |
| CAP-0100 开放互操作 | Markdown/Vault/Canvas、Zotero/Anki | X12、F04 |
| CAP-0110 搜索图谱索引 | 本地全文、按需向量/外部搜索、可重建投影 | X07、F05 |
| CAP-0120 桌面平台 | C#/Avalonia生命周期＋复用Web、Windows候选 | X03、X11、X13 |
| CAP-0130 受控执行探索 | 首版限定方法任务；通用执行探索保留后置 | X09、F04/F06 |
| CAP-0140 备份同步发布 | 一致归档、旧版兼容、恢复；同步工具后置 | X05、X10、X11、F04 |
| CAP-0150 模型与Provider | 复用本地服务、预算和数据范围、模型身份 | X04、X09、F03 |
| CAP-0160 可视化表征 | Canvas/概念图/数据图/3D投影 | X12、F01/F02 |

16 组原格式矩阵不因只选首批样本而缩减；专业格式不能解析时保留原件/预览和明确损失，不伪称完整转换。旧界面设计、否决意见、个人方法、九锚等已有保留需求继续留在原任务，不因本文件未为每项选择新库而删除。

## 13. 交给执行器的承接要求

在实际仓库和现有授权下执行，先确认工作区状态与最新远端。把本文件作为 `docs/authority/taskpack-0907/` 下的规划补充候选，按 X00 记录采用决定并链接既有任务；不重写冻结任务原文、不自行把候选资源批量标 DONE。

1. 先重读当日审计与原 TASKS/EXECUTION，确认 cbe253b 之后是否新增提交；有更新先做相关差分，不机械复修已解决问题。
2. 先完成第1节数据完整性与权限问题，再沿第10节接线；路径/容量止增按已有授权提前处理。
3. 复用第2节现有资产；涉及 legacy DB 的桥接必须迁移为 vNext Core API/受控计算接口。
4. 默认继续 DeepTutor，不新增完整宿主/数据库/Agent平台；任何替代必须说明实际失败样本、为什么已有供体不能解决、具体复用范围与回滚。
5. 将本表资源归入现有开源 Registry V2；上游 SHA、许可快照、运行证据未知时留空，不编造。软件库存与知识资源目录可有不同记录类型，但不能变成两套任务权威。
6. 当前只启用完成真实样本验证所需的最少组件；更多内容按 M1/Future 需求进入，不把调研候选变成强制安装清单。
7. 每个切片记录真实源码SHA、环境/版本、输入输出哈希、失败路径和回滚；本机原始证据留原有受控位置，仓库仅留脱敏摘要和可复跑命令。
8. 第一版交付必须含人类学习、机器方法调用和双向纠错；不能以安装截图、API工具列表、CI局部通过或聊天生成成功替代。
9. Q00/Q01由独立审计判定，不自行提高资格；本规划不改变先前G01–G14门禁。

本规划建议的最短路径是：修复可信数据与恢复底座，接通已有转换和检索，继续复用 DeepTutor 与成熟复习能力，再让真实机器客户端应用方法并回流纠错；在该闭环可用后，逐包加入百科、教材、古籍、文献、互动与空间资源。

所有第三方来源为截至本轮可读取的官方仓库/文档或本对话已核查来源。除明确列出的仓库代码观察外，外部项目兼容性为待实测候选判断；没有宣称已在 ArcheAxis 中安装、部署、完成融合或释放本地空间。
