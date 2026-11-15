# AAOS 开源池对账与融合决策（2026-11-12）

本报告是审计提案与事实对账，不是 Owner 已批准的新架构或接入资格。基线 `157ee1db401bc4c101ad73309159eca7d09abc9a` 加本次接手已有三项修改；未运行旧测试、旧实验、模型、安装或产品旅程，未升级依赖。报告日期使用 Asia/Shanghai。

## 结论与实际变更

**继续用当前 Tauri/React、Rust Core、现有转换/检索/复习底座；把 DeepTutor 的辅导模块与 OpenMAIC 的教学内容/renderer 融入同一活动，不再引入一套完整知识库、记忆 OS 或 Agent 产品。** 当前最有价值的新候选只有：复杂版面提取的 Docling、轻量中文 OCR 的 RapidOCR，以及真正可编辑知识画布的 XYFlow。它们均先解决具名缺口，不成为默认依赖。

已经更新 `docs/truth/SUPPLY_CHAIN_LEDGER.json`：55→79 行，原 55 个 ID 全保留；新增 24 行含已有宿主组件、OpenMAIC、具体候选及行为参考，不是新增 24 个运行依赖。当前分布：CURRENT 23、ADOPT 12、EVALUATE 12、SIDECAR 5、REFERENCE 14、DEFER 3、REVIEW-BLOCK 9、REJECT-CORE 1。CURRENT 仍由 `qualification` 限定，不代表安装/发布通过。

`CAPABILITY_ABSORPTION_REGISTRY.yaml` 保持 11 个原 CAP 身份：纠正两教学供体的固定版本、真实目录、运行边界，保留原记录到 history；whole-capability status 仍为 candidate，因为完整功能融入资格尚未建立。修正 WeKnora 引用的正式宿主为 Tauri/React。没有用新日期冒充全部上游已经逐一刷新；每行增补 `audit_20261112`，未核字段明确 UNKNOWN。

历史 369 行池按规范化仓库名（大小写、`.git`、尾 `/`）计数仍为 369 个不同身份，无可直接删除的重复。跨表同名是来源重复，不是重复安装：保留每个 `record_key`，由现有 crosswalk `identity_groups` 合并检索。没有覆写历史池、历史资格与 115 项原冲突。Kreuzberg→Xberg 是显式别名提案，不能把不同版本 API 视为相同。

`config/provenance/oss-reuse-crosswalk.json` 与它指向的 ignored 派生表同步新输入；这是必要的数据重生成，不是旧测试重跑。现有前端资源投影也由原生成器刷新，不改冻结资格或启用按钮。历史表仍可显示历史 route/冲突，不能仅凭其名称选择运行入口；后续产品应清楚展示“历史记录”与“当前接线”。

## 实际代码与登记差异

| 事实 | 代码/原件依据 | 处理及影响 |
|---|---|---|
| DeepTutor 台账仍指 1.5.17、`.hermes` 与旧 Python bridge | 原 C013；`services/learning-providers/deeptutor/upstream/README.md`；`UPSTREAM.md`；`QUESTION_TURN_UPSTREAM.md`；`TEACHING_FEEDBACK_UPSTREAM.md` | 改为 1.7.1、隔离模块与 Core；原记录完整保留。不得复活旧写库链 |
| OpenMAIC 完整源码与大量 worker 已存在，但原 55 行没有 OpenMAIC | `services/learning-providers/openmaic/upstream/README.md`、`RUNTIME-CLOSURE.json`、`vendor/`；`frontend/src/adapters/openmaicCourseV2.ts` | 增 C055，source 资格；不能再写“尚未纳入”或“只有文本 slide”，也不据模块数量宣称完整课件已可用 |
| 本地冻结身份明确 | DeepTutor archive `9614f50c…` / LICENSE `cd2f54e1…`；OpenMAIC archive `7cea2a58…` / LICENSE `ba252563…`，完整值见各 upstream README | 1.7.1 Apache-2.0、1.3.0 MIT 分别成立；新上游许可不反向改写历史版本 |
| ASR 已有正式 worker | `services/python-workers/media/worker_transcribe.py:218,325,433` | A005 更新为 source CURRENT；继承已有音频转写证据，质量仍未测，不重复换 whisper 引擎 |
| FSRS 已有正式调度 worker | `services/python-workers/learning/worker_schedule.py:145,180,195` | A015 补真实消费者；调度不代表掌握；先保留参数与历史状态 |
| 主搜索真实使用 FTS5；sqlite-vec 台账仍是旧 Python 路径 | `crates/archeaxis-domain/src/search.rs:1,37,116`；C008 `app/memory/vector_db.py` | 不能说正式 Rust Core 已支持向量混合检索；保留 FTS5 首选，向量只是派生投影候选 |
| 网页正文不是只有 placeholder | `services/python-workers/web/worker_html.py:196,236`；`machine/document_check.py:244` | 保留 Trafilatura；已有 stdlib 降级与失败记录，不另造正文提取链 |
| MarkItDown 仍有旧转换消费者，但不等于正式 Core Office 引擎 | C002；`services/python-workers/document/worker_office.py` | 保持旧 fallback 身份；正式 Office/PDF 路由按现有 worker 与格式资格表，不把依赖存在当接通 |
| 宿主早已具备工作区/编辑/阅读底座 | `frontend/package.json`；`workspace/DockWorkspace.tsx`；`components/PdfReader.tsx` | 新增登记 Dockview/Tiptap/Radix，继续当前版本，无第二 Dock、第二编辑器 |

完整运行深度以本审计的后端与证据继承报告为准，尤其 11 月 7 日安装布局/合成 loopback 候选证据不能缩成未 staging，也不能扩大为真实模型、UI renderer 与完整教学产品通过。

## 每类首选与对比边界

表中“上游”是公开资料核对，均不代表本机安装；没有读到固定许可的项目明确保留待核。所有公开资料访问日为 2026-11-12。最新版本页面可能来自工具缓存，不承诺此后无新版本。GitHub 公共 REST 在本机返回速率限制，改读官方 release/LICENSE 页面；未使用私人凭据。无近期提交不据此判死，未取得 archived 状态就标 UNKNOWN。

### 资料与媒体

| 项目/稳定ID | 核对版本、许可与维护线索 | 决策、重叠及退出方式 |
|---|---|---|
| Tesseract C004 | 本地 system binary 身份依旧回执；Apache-2.0 为既有登记，本轮不重测引擎版本 | **保留默认 OCR**；原件→文字/定位→Transform。图像结构与准确率单独记，替换仅换 worker，旧输出永久可读 |
| Trafilatura C003 | 本地 2.1.0、Apache-2.0，既有许可证哈希继承 | **保留静态正文首选**；网页→正文和损失。动态页面只按需现有 Chromium，不默认双浏览器 |
| faster-whisper A005 | 当前 worker 确认；实际部署版本/模型精确身份继承各回执，不虚填 latest；代码 MIT，模型和 CTranslate2 分开 | **保留 ASR 首选**；音频→分段文字/时间戳；离线依赖已声明模型。MP4 音轨不能当视频视觉理解 |
| Apache Tika A010 | 既有 4.1.0 sidecar、Apache-2.0；JRE A050 身份单列 | **保留旧格式可选回退**，不扩为所有文件默认；解析输出入原 Transform，不保存第二库；退出后原转换仍可读 |
| MarkItDown C002 | uv.lock 0.1.6、MIT 既有登记 | **保留旧兼容，不新增平行正式入口**；只有实证某格式优于现有 worker 才接入 |
| Docling A009 | [v2.150.0/2026-11-10](https://github.com/docling-project/docling/releases/tag/v2.150.0)、[MIT](https://raw.githubusercontent.com/docling-project/docling/v2.150.0/LICENSE) | **复杂 PDF/表格/公式首个候选**；与现有轻量解析互补。固定页/单元格/公式 anchor 和 coverage 必须映射；模型下载体积、Win 打包与布局丢失待验，不用上游支持格式数承诺 AAOS |
| RapidOCR A004 | [v3.10.0](https://github.com/RapidAI/RapidOCR/releases/tag/v3.10.0)、[Apache-2.0](https://raw.githubusercontent.com/RapidAI/RapidOCR/v3.10.0/LICENSE) | **中文轻量 OCR 首个替代候选**，先对现有已知错误样本做后续差分。ONNX 模型及运行库另核；保留 Tesseract 回退 |
| PaddleOCR A002 | [v3.7.0](https://github.com/PaddlePaddle/PaddleOCR/releases/tag/v3.7.0)；固定 tag LICENSE 未独立读取，Apache-2.0 为上游声明 | 结构识别备选；只有 RapidOCR/Docling 仍无法满足需要时引入，避免多个重量栈默认常驻 |
| Xberg A055 | [v1.3.10](https://github.com/xberg-io/xberg/releases/tag/v1.3.10)、[MIT](https://raw.githubusercontent.com/xberg-io/xberg/v1.3.10/LICENSE)；[官方迁移说明](https://github.com/xberg-io/xberg) | **运行闭包收敛备选**；可能减少多语言解析包装，但没有本机证据。Kreuzberg 旧 v4 与 Xberg 1.x 分界保留，不直接改 Cargo 或旧 API |

输入均是已授权 Source 固定版本，输出沿现有解析/转换合同交 Core 写入；OCR/ASR/复杂文档候选是离线能力候选，必须先备齐并核准模型与依赖，不能因为代码开源就宣称开箱离线。成本以增加 Python/ONNX/Paddle/JRE 闭包、CPU/GPU需求和维护面衡量，本轮无可比较实测，未伪报毫秒、内存或准确率。

### 检索、关系与 AI 知识

| 项目/ID | 已核版本/许可来源 | 推荐 |
|---|---|---|
| SQLite FTS5 / C008 sqlite-vec | 正式 FTS5 在 Core；sqlite-vec 为旧消费者，固定新版本 UNKNOWN | **保留 Core 检索首选**。语义向量若需要，先作为可删除重建索引，与固定 Source/Document 关联，不增加服务 |
| LightRAG A057 / CAP-LIGHTRAG | [v1.5.7](https://github.com/HKUDS/LightRAG/releases/tag/v1.5.7)、[MIT](https://raw.githubusercontent.com/HKUDS/LightRAG/v1.5.7/LICENSE) | 只保留一个混合检索备选；固定材料与问题显示召回缺口后才评估。复用供体已带算法须避免再跑全套知识库 |
| RAG-Anything A058 | [v1.4.4](https://github.com/HKUDS/RAG-Anything/releases/tag/v1.4.4)、[main MIT](https://raw.githubusercontent.com/HKUDS/RAG-Anything/main/LICENSE)；tag许可获取失败 | 多模态结构/检索方法参考；解析器/模型另核，不默认与 LightRAG/Docling 三套并行 |
| Graphiti A059 | [v0.31.2](https://github.com/getzep/graphiti/releases/tag/v0.31.2)、[Apache-2.0](https://raw.githubusercontent.com/getzep/graphiti/v0.31.2/LICENSE) | 时序关系方法参考。Core 已有版本/失效语义；不为“时序”另建业务图数据库 |
| MemOS A060 | [v2.0.36](https://github.com/MemTensor/MemOS/releases/tag/v2.0.36)、[main Apache-2.0](https://raw.githubusercontent.com/MemTensor/MemOS/main/LICENSE)；tag许可获取失败 | AI经验整理参考；不能替代 AiAsset 采用、使用和独立复测。托管接口不等于本地免费组件 |
| Cognee A061 | [v1.6.7](https://github.com/topoteretes/cognee/releases/tag/v1.6.7)、[Apache-2.0](https://raw.githubusercontent.com/topoteretes/cognee/v1.6.7/LICENSE) | 保留原 benchmark/reference；不新增 ontology/graph/memory 服务作为首版前置 |
| WeKnora A062 | [v0.9.0](https://github.com/Tencent/WeKnora/releases/tag/v0.9.0)、[LICENSE正文 MIT及第三方条款](https://raw.githubusercontent.com/Tencent/WeKnora/main/LICENSE) | 借鉴处理进度、材料工作区和修订体验；不能因 NOASSERTION 拒研。整套 Go/存储栈与 AAOS 重叠，当前不采用 |
| RAGFlow A063 | [v1.0.0](https://github.com/infiniflow/ragflow/releases/tag/v1.0.0)、[Apache-2.0](https://raw.githubusercontent.com/infiniflow/ragflow/v1.0.0/LICENSE) | 较大平台替换的真实备选，适合将来重检索负载；目前部署复杂度与迁移大，尚无证据推翻本地底座 |

此组若未来启用，I/O 为固定对象块与 source anchors→可重建索引/候选关系/检索结果，不能原地覆盖知识；推断边需独立标识。AI知识提炼→实际使用→纠正→复测仍由 AAOS 业务合同负责。维护责任在各 adapter，升级采用版本化索引重建，停用后靠 FTS/关系表与原结果退回；不把原始跨项目会话整体上传给候选服务。

### 教学与复习

DeepTutor 本地 **1.7.1** 与 OpenMAIC 本地 **1.3.0** 是冻结基线。官方 [DeepTutor 1.7.2](https://github.com/HKUDS/DeepTutor/releases/tag/v1.7.2) 的上下文补答、过期回复/重复重试与引用对齐修复，适合逐个比较已抽取的 question/teaching/recovery 模块；选区朗读可以作为后续活动功能。先对照旧模块实际使用路径，不能用上游 release 文案证明本地存在同一 bug。Apache-2.0 [固定新版本 LICENSE](https://raw.githubusercontent.com/HKUDS/DeepTutor/v1.7.2/LICENSE)已读。

OpenMAIC [1.4.2](https://github.com/THU-MAIC/OpenMAIC/releases/tag/v1.4.2) 的课程撤销与交互页修复值得回移评估；其 sandbox 使用范围、资源回收生命周期等变化并不适合整站搬入 AAOS。现行 [MIT](https://raw.githubusercontent.com/THU-MAIC/OpenMAIC/v1.4.2/LICENSE)与本地1.3.0 MIT分别成立，不借此改写更早许可证。推荐“固定 DSL/scene-content/renderer 组件直接融合 + 有界生成 worker”，不运行整套 Next/PostgreSQL/Agent。学习活动统一指向 Document版本、attempt/event和 Source anchors；renderer 升级保留旧 payload reader，未知 schema 保全原件/外部继续。

py-fsrs A015 **保留 6.3.2**；[fsrs-rs 6.6.2](https://github.com/open-spaced-repetition/fsrs-rs/releases/tag/v6.6.2)为替换候选，[实际许可 BSD-3-Clause](https://raw.githubusercontent.com/open-spaced-repetition/fsrs-rs/main/LICENSE)，不是 MIT。本轮后端源码已确认 worker 计算移出关键写事务（api/lib.rs:1128–1170），不再重复派这项修复；剩余 async handler 同步等待可先局部处理，再按真实收益考虑原生替换，否则同时换语言和算法会增加不可归因风险。迁移需要比较同输入/参数/时间下的 due、stability、difficulty、历史状态，不能重置复习历史。两供体与 FSRS 都不得把“播放完成/评分正确/调度成功”当掌握。

### 编辑、阅读、工作区与画布

| 组件 | 固定身份/许可 | 决策与对象映射 |
|---|---|---|
| Dockview C056 | 8.5.1 本地锁；[core/react MIT、enterprise商业](https://raw.githubusercontent.com/dockview/dockview/master/LICENCE.md) | **继续**；只做对象标签、双栏和恢复，不默认展示复杂 Dock 配置；布局是派生用户状态 |
| Tiptap C057 | 3.31.4 本地锁；开源包 MIT，商业组件独立 | **继续**；编辑→Document/Block版本，不能另存一份富文本主库；退出时可导出结构化内容与Markdown损失说明 |
| PDF.js C001 | 6.4.299 本地锁，Apache-2.0继承 | **继续原件阅读**；页码/坐标anchor联动转换正文；不以PDF viewer替代Office/视频renderer |
| Radix C058 / shadcn A074 | dialog1.2.0/tabs1.1.22 已锁；shadcn新固定revision UNKNOWN，MIT为声明 | **Radix首选**，shadcn仅补具体缺失控件；不批量换组件底座 |
| XYFlow A017 | [@xyflow/react main 12.12.1](https://raw.githubusercontent.com/xyflow/xyflow/main/packages/react/package.json)、[MIT](https://raw.githubusercontent.com/xyflow/xyflow/main/LICENSE)；非固定tag资格 | **编辑知识画布首选候选**。节点引用概念/摘录/问题/固定版本，边为用户组织而非自动知识事实；JSON Canvas导入/导出单列损失。主仓latest指向Svelte，不能误填React版本 |
| Excalidraw A064 | [v0.18.1](https://github.com/excalidraw/excalidraw/releases/tag/v0.18.1)；固定LICENSE未重读，MIT声明 | 可选手绘，暂不与XYFlow同时默认引入；自由图形保留原scene，不伪造语义边 |
| JSON Canvas A016 | 1.0开放格式，MIT既有登记 | **交换格式继续**；字段/附件/边/链接身份映射，内容保存≠可编辑体验≠Obsidian全兼容 |
| tldraw B005 | 固定revision UNKNOWN；[生产SDK需对应许可](https://tldraw.dev/community/license) | 保留研究，当前不作为首选；自定义许可不能标MIT，功能收益不足以抵消新授权和存储适配成本 |

上述浏览器组件可在打包资源齐备时离线使用；Windows/WebView2、中文IME、键盘/焦点与未知内容回退需在实际变更后补最小差分，不重跑本轮已有测试。固定工作区和业务对象分开，便于换视图而不迁移知识。

### 外部知识库：保留全特色目标，按方向兑现

| 软件/版本线索 | 首选连接与保留内容 | 损失/未验与维护 |
|---|---|---|
| Obsidian，客户端版本UNKNOWN；[官方插件manifest](https://docs.obsidian.md/Reference/Manifest) | 文件/Markdown/附件/属性/双链/块ID/JSON Canvas → AAOS Source/Document/Relation；先单向导入 | Obsidian为专有产品，插件可需Electron/Node；Dataview/Bases查询、插件行为、模板和同步不自动移植。每个特色按版本登记；不写回真实vault |
| Logseq [2.0.2 Beta](https://github.com/logseq/logseq/releases/tag/2.0.2) | 大纲/块引用/属性按文件模式与DB模式分开适配 | AGPL声明，固定许可和DB导出保真待核；不能把旧Markdown脚本当新DB模式往返支持 |
| SiYuan [3.8.10](https://github.com/siyuan-note/siyuan/releases/tag/v3.8.10) | 官方API优先，保留块身份、属性、引用与资产 | AGPL声明，固定许可待核；查询视图、SQL/挂件与同步不因文本导入成为可用。先只读连接 |
| Joplin [3.7.22](https://github.com/laurent22/joplin/releases/tag/v3.7.22) | JEX/Data API：笔记、资源、标签、目录映射 | 默认AGPL-3.0-or-later，子包另核；插件、端到端加密与同步状态需单独协议，不克隆数据库 |
| Zotero [Web API v3](https://www.zotero.org/support/dev/web_api/v3/)；客户端版本UNKNOWN | 文献元数据、附件、批注、页/段定位→来源与引用；可先本地导出 | 元数据不保证全文可取；引用样式、附件权限/存储、客户端代码许可不同。双向写回另授权与版本冲突合同 |

AGPL不妨碍研究、外部API或合规分发；不能仅用“独立进程”断言源码义务不适用。真实采用代码及分发范围尚未确定的项目，本轮记录条件，不发明全新审批平台。上述是本期路线，不是用五款替换现有37平台矩阵；其余个人特色继续留在原矩阵，软件/版本/操作方向/损失逐项补齐。

### 后期与整套平台

Manim [0.22.1](https://github.com/ManimCommunity/manim/releases/tag/v0.22.1)作为外部动画→视频/SVG/字幕/来源版本；JupyterLite [0.8.4](https://github.com/jupyterlite/jupyterlite/releases/tag/v0.8.4)作为隔离课件→notebook/活动事件；代码MIT/BSD声明不覆盖所有字体、媒体、内核包，固定分发许可待核。2D/3D、VR/AR、仿真保留活动类型和外部成果入口，未以本轮首版不装而删除蓝图。

AFFiNE 的 [根许可按目录分开](https://raw.githubusercontent.com/toeverything/AFFiNE/canary/LICENSE)，版本UNKNOWN；适合文档/画布交互参考，不把全部源码笼统写MIT。Dify [附加条款](https://raw.githubusercontent.com/langgenius/dify/main/LICENSE)涉及多租户及前端标识；版本UNKNOWN，本期仅参考provider调试体验。替换完整外壳的收益是成熟交互，代价是重接权限、来源版本、两侧学习和恢复；目前不比保留底座更经济。未来若真实用户试用证明现壳无法承载学习舞台、且抽组件成本明显大于迁移，可以重新比较整壳路线。

## 免费检索通道：已有实现与当前条款

`services/python-workers/machine/public_research.py:30,309,404,416–444` 已有三族通道、User-Agent、backoff/quota为limited、429区分、OpenAlex→Crossref及Wikipedia→DBpedia回退。不能再把回退当完全待实现。现有证据继承原网络时间/环境；本轮只读官网，不请求实际研究API、不重新跑三通道探针。

| 通道 | 当前官方说明 | 实现影响和后续最小任务 |
|---|---|---|
| [OpenAlex认证](https://help.openalex.org/api/authentication/) | 基础查询仍可无key；免费key提高预算，游标分页需要key；免费不等于不限量 | 当前 `_research_url` 只用 search/per_page，无key、无游标，符合小量基础路径。后续需要分页时加显式可选key与配额状态；不偷偷申请、不因没key阻断普通本地保存 |
| [StackExchange限流](https://api.stackexchange.com/docs/throttle) | IP、key/token配额不同，返回backoff要求等待；并发速率约束与日额度分别存在 | worker保存retry_after，但跨用户点击/新worker调用的全局冷却不能靠一次响应证明已落实；在现有任务层按provider缓存冷却，继续保留已取hits并说明受限 |
| [Wikimedia限流](https://www.mediawiki.org/wiki/Wikimedia_APIs/Rate_limits) | 请求身份、速率、服务端错误与缓存需遵循当前文档 | 保留可识别User-Agent；网络不可达与429分开。若后续实现重试，尊重retry_after、有界退避，不重做整套抓取平台 |
| DBpedia Lookup | 本地回退保留失败的Wikipedia通道与摘要身份 | 搜索摘要不是固定修订全文，也不是独立于Wikipedia的第二证据源；不得用它宣布已完成正文对齐 |

## 首批可执行的复用任务（提案）

1. **教学内容链合并**：`CanonicalLearningSpace` 与现有 OpenMAIC adapter/renderer，配 `services/learning-providers` / Core learning 事件；直接复用固定DSL/quiz/scene模块。交付：同一资料进入讲解、课件、作答、反馈、续做。继承旧评分/场景读回，仅补新renderer与跨活动状态差分；回退旧reader、保存新payload不丢失。
2. **纠错与知识当前性统一**：现有 Source/Transform/Document/Knowledge 四消费者使用相同固定引用与失效投影。交付：比较结果可先存，修订后研究/学习/AI提示过期。复用公共检索worker和Core版本，不另装Graphiti/MemOS。补同版本转换/修订/撤销断言；旧历史不重写。
3. **资源目录去误导**：来源/吸收/资格分栏；DeepTutor当前1.7.1与旧1.5.17明确区分，OpenMAIC完整源码和具体可用行为分别展示。后端仍由原资格/冻结源决定启用；本轮只刷新生成投影，后续UI任务不改资格状态。回退显示层不回退台账事实。
4. **结构画布首个纵切片**：现有JSON Canvas合同和对象引用→XYFlow组件；源页/时间点回跳与保存重开必须一起交付。先复用正式存储，不导入Excalidraw/tldraw并行底座。新增绘制/断链/历史引用/导出损失最小验证；未知字段原样保留。
5. **复杂解析只按失败样本启用一个候选**：从已有缺口选复杂PDF/表格/公式，Docling为首选；若只是中文OCR则RapidOCR。复用相同Source/Transform/anchor，比较质量和闭包后决定；本轮没有执行此PoC。回退现有轻量worker，保留两版转换与损失，不重复导入原件。

维护责任按现有边界落位：worker负责引擎依赖与有界I/O，domain负责固定版本/状态/权限，frontend负责renderer与连续交互，packaging负责运行闭包。没有必要新增“开源管理服务”。现在应停止：平行全栈教学站、第二记忆主库、重复Dock/编辑器、为同一格式全部默认安装、把所有模块重新包装MCP，以及没有具体缺口的重复全量实验。

## 继承与本轮限制

继承的是旧回执所描述的固定输入/版本/环境，非当前整体PASS。历史池旧分类、许可证与资格保留；当前代码读到真实调用不等于执行。所有新版候选都未下载执行、未改变锁文件或模型路由。新执行仅包含公开文档读取、台账结构更新、派生表生成及本轮变更文件的格式/引用核对。默认Python缺PyYAML导致首次输出分配失败，改用仓库已有`.venv`，未安装任何包；这是审计工具环境问题，不是产品失败。

未核项目的实际影响：未固定的新候选不能立即进入打包；模型/字体/媒体许可未清意味着对应资产尚不能随包分发；平台/性能未测意味着候选收益未建立；未读固定tag许可不应据main许可直接放行该tag。其余旧55行中与本期选择无关的安全工具、观测工具、替代ASR与未来平台，保持原决定与明确UNKNOWN刷新状态，需求触发时再深入，不以本轮日期伪装全池已集成。
