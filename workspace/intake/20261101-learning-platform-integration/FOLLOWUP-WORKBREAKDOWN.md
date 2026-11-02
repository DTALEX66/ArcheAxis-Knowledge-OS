# 两个平台接入与全部后续工作拆分

2026-11-01（Asia/Shanghai）。本页是有源码依据的交接拆分；**实际进度仍只写活动指针选定的唯一执行记录**，不建立第二队列。局部 INT-* 仅本次实现单元，不替代既有CAP/REQ、CL-01—07/J1—6/X1—8及S01/G01/UF/CB等身份。

Owner本次选定：尽快并入DeepTutor1.7.1、OpenMAIC1.3.0的适用能力，兼顾全部既有未完项。实现要实际落地，不能只做文档/注册/演示。先交付完整可用小切片，然后继续适用能力覆盖；不能以首片完成取消其余目标，也不盲目搬入两个完整站点及第二数据库。

## 并行写集与依赖

| Lane | 工作 | 写集/冲突控制 | 难度及并行方式 |
| --- | --- | --- | --- |
| L0 整合者 | 保护dirty基线、架构合同、许可证闭包、任务/证据回写、最终候选与交付 | 根入口/活动指针/唯一执行记录/共享合同和生成文件只由整合者写 | 架构复杂可用gpt-6-astra/high；只在可用且已授权时指定，其他沿继承模型 |
| L1 DeepTutor | 新版本隔离SDK/sidecar、正式Core事件桥、实际消费与恢复 | 独立DeepTutor适配器及其测试；与L2共同合同先冻结，不写旧Python canonical DB | gpt-6.1-sol/high；先独立读源，合同稳定后实现 |
| L2 OpenMAIC | 课程v2、generation/DSL/renderer、旧课程兼容、Core事件 | OpenMAIC adapter、局部renderer与测试；共享课程合同由L0串行合并 | 高难合同可用gpt-6-astra/high；可与L1并行，不升级全前端框架 |
| L3 治理/存量 | producer增长约束、候选输入归一、外溢来源/恢复和包资格 | scripts/runtime及具名清理映射；与供体代码分离，产物删除只处理已确认可再生且已有保留/恢复证据范围 | 通常gpt-6.1-sol/medium或high，按实际难度；先控新增增长再大构建 |
| 独立验收 | 反例、真实Core/worker、同候选安装与跨版本、原始失败核对 | 验收期间冻结目标写集；避免边改边测、不能自签全闭环 | 复用空闲agent，任务完成后分配，不突破并发槽；不替代Owner接受 |

## 新供体接入工作（归入CL-01/05/06/07、J4/J5/J6、X1—X5/X7/X8）

| 实现单元 | 具体动作与现有接缝 | 依赖/验收 |
| --- | --- | --- |
| INT-00 来源及合同 | 只读本仓MANIFEST所指两原ZIP，按hash选定必要源码。保留Apache/MIT、包级声明与修改来源；依赖/媒体/模型另核。沿现有Core对象、任务、权限及能力中心，不新建通用Runtime/调度器/第二知识库 | 两ZIP已归档与CRC通过，不重复制。先列实际采用路径、版本、输入/输出、未知/失败与回退，再直接实现 |
| INT-DT-01 1.7.1隔离接入 | C013旧1.5.17资格留历史。新包`deeptutor/__version__.py`=1.7.1，web/package.json=1.0.0不是主版本。选择SDK/sidecar最小调用，不以整站替换正式宿主；provider设置/缓存/数据仅项目隔离，`.hermes`不新增写 | 只读就绪探测与真实调用分列；不自动读取外部Agent账户/会话，显式使用产品已授权模型配置；依赖缺失可继续另一供体离线片 |
| INT-DT-02 Core事件桥 | `app/integrations/deeptutor_bridge.py.accept_event`→`app.learning.event_store.append_event(db_path)`读写旧Python表，不能复活为canonical writer。正式接缝在`src-tauri/src/core_bridge.rs`的LearningItems/State/History/Review及Rust API | 把供体事件映射现行Core合同，稳定source_version/activity/attempt/client_event_id和幂等；失败/重试/撤权不重复写，不旁路业务SQLite |
| INT-DT-03 教学实链 | 实际已选资料→供体教学/练习→人类作答→反馈/复习→重启与导出回读，材料/答案/评估分开；可复用策略进入AI资产沿既有治理 | 不把HTTP200、主程序可开、模型回答或自报完成当掌握/学习改善；F05仍需冻结独立复测 |
| INT-MAIC-01 课程v2 | 复用`frontend/src/adapters/openmaicCourse.ts`、`presentation/importedCourseStorage.ts`、`ImportedCoursePanel.tsx`、`CanonicalLearningJourneySpace.tsx`。旧v1=256KiB/quiz-only/pin6b83751a...；`packages/contracts/learning/v1/imported-course.schema.json`旧SHA const不能替换毁掉老课 | 新增清晰v2分派和能力allowlist；保留v1 reader与原件、payload SHA、provider/renderer版本、loss/unknown；坏版本/超限拒绝或保全回退 |
| INT-MAIC-02 离线完整片 | `@openmaic/dsl`0.12.0 + `@openmaic/renderer`0.2.0；首片slide+quiz，复用source_import→原字节比对→document_create/get；事件经Core落盘 | 导入→实际页面/题目→作答反馈→重启→导出恢复；重试不重复事件，旧引用不自动改指；自报完成/考试评分/独立掌握分开 |
| INT-MAIC-03 真本地生成 | `@openmaic/generation`0.3.28的AICallFn、generateSceneOutlinesFromRequirements/generateSceneContent/generateSceneActions/buildCompleteScene。固定sceneId、输入版本；隔离Node桥调用现有本地模型，Core管task/attempt/result | 缺模型、不支持、invalid-model-output/prompt-unavailable/null均明确未成功；不偷偷转云。输出可沿离线片实际消费，连接成功不替代课程成功 |
| INT-MAIC-04 样式/资源和生命周期 | renderer是SlideCanvas/渲染组件，不是完整播放器。React>=18/motion>=11可局部适配；Tailwind>=4与AAOS当前差异须局部构建隔离，不升级整框架。可选fonts.css默认指外部CDN，首片不用，系统字体回退验证中文 | 取消/超时/迟到结果/未知renderer、provider升级回退旧结果、断网/资源缺失/撤权逐项验；外部URL不会被简单资源重写全部清除 |
| INT-MAIC-05 继续覆盖 | 动作/讲解/白板/语音、interactive/PBL、PPTX/importer/editor分别映射当前目标与采用方式，逐项实现或有依据保留状态，不能首片后即称整个平台完成 | 交互HTML隔离并约束导航/联网；PBL接外部实践计划/人工回流，不建设专业生产工具；不得带入整站Next16/React19/Postgres/Agent持久化 |
| INT-QUAL 统一资格 | 两供体均作为能力提供方，经现有合同接回资料、研究、学习、AI四消费者。补worker课程合同：`archeaxis-sidecar-protocol/src/worker.rs`现TEXT_SCHEMAS仅text/document-structure/loss-receipt，不是任意课程已支持 | 静态/单测/mock、真实Core、真实provider/worker、本地模型、同候选原生安装/升级恢复、Owner接受分别记录；X1—X8逐项不得用总测试数代替 |

静态审包证据在`.project-local/runs/be268a2d33/donor-deeptutor-review/`和`donor-openmaic-review/`，未运行附带代码/安装/整包展开/模型。上表是工程接缝，不是两软件整体功能已经具备。优先现有成熟能力和局部供体复用，功能接线不授权全局布局重做。

## 既有15组未完事项：来源核对快照

2026-11-01。本报告是交接辅助证据，不是第二目标、队列或进度源，原核对本身未执行产品/UI/监控、清理、模型、构建或远端操作；后续新供体接入按本页上方Owner选定范围执行。所有相对路径以 `D:/All projects/ArcheAxis-Knowledge-OS/` 为根。下表保留新供体接入不能替代的已有剩余任务；未核的远端状态必须现场读回。

## 基线与控制

- 实读 PROJECT_CURRENT.md、AUTHORITY.md、近两日13组对照、CLOSED_LOOP_DEFINITION.md、活动指针及唯一执行记录末段。最新基准为 AUTHORITY / 13组 / 产品身份V2.3 / 唯一闭环V3；SUP-030/031/032分别处理新包目标、任意领域AI知识及归档治理。
- 现场分支 `codex/candidate-input-normalization-20261101`；HEAD `08d96fc64c6856ad03e51dfff298183eafadfbfa`；`git status --short` 55项公开dirty（此为本次新来源入仓前快照；含intent-to-add，未暂存文件内容），HEAD不能代表这批治理/原件索引代码的完整身份。禁止reset/clean/整树覆盖；接手先留完整patch和untracked身份，按文件反向合并。
- 活动指针 `selected_tasks`：UF00/01/02/03、CB01、UF04/06、S01.A/B/C、G01、H01、UF05、CB02、UF07/12、CB03、UF08/09、O01、UF10、CB04、UF11/13。priority_tasks为UF03/CB04/UF11/UF09/UF10/UF13；治理overlay当前优先S01/G01，不另生任务ID。V01暂停，FT01—04冻结。UI实施与监控暂停；新接入授权应精确表述覆盖范围，不能连带恢复全部UI/监控。
- 老 `RUNNING_BY_OWNER` 字段与后继暂停/文档限定并存：后继知识澄清、归档整理由明确范围限定，不从旧字段推断整体已恢复。历史恢复权限与产品完成无关。
- 本地公开源码交付授权曾覆盖旧本地阶段远端禁令，但本子任务未联网。PR205、CI、main/远端分支现况全部 CURRENT_UNVERIFIED；不能把旧收据的pending/fail或后来口述当今日远端结论。

## 未完成矩阵

| 原ID/归属 | 剩余动作 | 依赖与建议先后 | 具体证据入口 | 验收与状态区别 |
| --- | --- | --- | --- | --- |
| S01.A/B/C、G01：持续增长治理 | 将其余stager/build、local_pinned_packaging和linked-worktree common-owner接入等价增长/保留/恢复约束；核其他机器/CI当期输入与checkpoint | P0，新增依赖/构建前；直接复用已实现portable门禁，不复制第二预算系统 | docs/history/storage-cleanup/2026-10-31-portable-pair-qualification/GROWTH-ENFORCEMENT.md；2026-11-01-governance-followup/CONTINUATION-2…5.json；scripts/runtime/ | 保留operator固定基线、类预算、2GiB复核线、单次claim/seal/实际post；未知拒绝；真实producer执行后再登记，fixture不能当≥1GiB真实组包PASS。不是跨producer原子容量保证 |
| S01目录规范化/存量归属 | 对303旧浅层布局快照按当前消费者、归属、可再生和恢复映射治理；先对账此前49项与latest-only实删，不重清已退役集合 | P0，可与独立适配实现分写集；不全仓历史重扫 | docs/history/storage-cleanup/2026-11-01-governance-followup/CONTINUATION.json、CONTINUATION-4.json、CONTINUATION-5.json | 303=181散落叶+91目录+30旧run+根stray1，是旧快照；后继5叶归位不能自动推算当前总数。私有/未知/真实数据保留；净逻辑B、压缩差、物理释放分开 |
| S01外溢/Green mig | 继续3处mig缺失源和替代账来源核对；按原精确路径/生产者/消费者/manifest追踪，先查归档替代再判SOURCE_MISSING | P0，避免误删；与Green程序替换分开 | docs/history/storage-cleanup/2026-10-31-portable-pair-qualification/DEEP-RETIREMENT.md及.json、其evidence精确映射；CONTINUATION-5.json | 缺失路径不等于已证丢失或已全迁移。Record24源13ZIP+11文件/15,042,572,388B保全已经成立不重做；43已知缓存根/580叶实删也不重新派单。Green程序/真实库/私有状态无自动操作权 |
| S01候选输入归一：六主包 | 修改当前硬钉消费者输入、共享引用与恢复映射后逐包重新资格，再决定可退役载荷 | P0/P1，真实新候选前；不能先删旧包 | DEEP-RETIREMENT.md第36行；CONTINUATION-4/5.json；workspace/intake/20261029-local-pinned-packaging-contract.md | cnprep3 native硬钉、bpr1 ASR、cppcand1 Host donor、zc1c8 package/tools冲突消费者和sci-build1各守原身份；六主包7.319GB/sci0.439GB只是旧时点，不能当现测或永久保留理由 |
| Host角色输入归一后继 | 继续完整旧候选消费者归一及同候选资格；使用已准备副本前重新核三hash/映射/无INCOMPLETE/FAILURE | P1，依赖上一行，切勿重做已完成53MB准备 | docs/history/storage-cleanup/2026-11-01-governance-followup/CONTINUATION-5.json；.project-local/runs/be268a2d33/cpphost-input1/artifacts/cpphost-input/SOURCE-MAP.json；scripts/runtime/candidate_inputs.py | Host49,999,360B+manifest3,669,060B+pin553B共53,668,973B已保全且87P/14subtests；只HOST_INPUT_PREPARED，WHOLE_PACKAGE_HOLD。--donor-manifest应指553B pin副本，不是大manifest；未运行旧Host/assembler，不计空间释放 |
| 交付PR205/本地远端一致 | 核35f696自身CI41267526637终态、PR205合并与main；再独立交付08d96fc后继dirty公开改动，按精确SHA门禁和对应ref读回 | P1，必须冻结/检查当前写集；本子任务不联网，当前状态未核 | CONTINUATION-5.json.remote；唯一执行记录2026-11-01公开治理交付及后继段；execution_control.owner_delivery_20261101 | PR205父链pending是记录时点；不能互借PASS，不强推/绕过a0。只上传公开源码/索引，不上传ignored原件/日志/DB/缓存；真实CI/合并/双端SHA分别完成 |
| 本地独立审计F01/F02/F04 | 保留历史云编码外发豁免UNVERIFIED；限定外部/未知/私有引用及硬链接归属；旧清场终态继续UNVERIFIED，新Popen模拟修复不能追认历史 | P1，沿实际现用路径定向补证 | docs/current/AAOS-UI-FIRST-EXECUTION-20261009.md未完表；workspace/intake/20261030-zcode-backend-closure/及evidence-index.json | F03冻结摘要后继已补；后继zc1c8安装态冲突子集已经执行，不能沿旧Owner清单“guest冲突待设计”重新派。当前证据/历史终态/授权三者分开 |
| F05 / CL-06 / J4：真实学习改善 | 在冻结输入、量规、权限、正确答案隔离及负控下研究真实V2第二题失败，继续迁移/package干预、真实采用消费、纠正及独立复测 | P1核心验收；复用原LM Studio路线，不通过提预算/去围栏/调参重试掩盖旧FAIL | docs/history/backend-response-format-20261031/REAL-V2.md；FOLLOWUP.md；docs/history/asset-scoped-real-model-20261031/README.md | 首题CORRECT/VALID；第二HTTP503 INVALID_OUTPUT/content/length、2048token上限，根因未确认。packet=null/members=[]，迁移/干预/纠正复测未执行，学习改善NOT_ESTABLISHED；旧NO_FINAL_ANSWER/ar2围栏等FAIL保留 |
| R2/R5/R6 / CL-05 / J5 / X7 | 专门start、自报完成、独立掌握、教程替换/跳过、计划版本、第二产品消费者、同候选恢复；按R6 E01—E10逐项补真实旅程 | P1；DeepTutor/OpenMAIC只吸收适配能力，不另建LMS/调度器/第二DB | workspace/intake/20261030-r6-external-practice-boundary-review/README.md、AUDIT.md、BACKEND-BINDING-6d556c48.md；docs/history/teaching-plan-observation-20261031/README.md、FEEDBACK.md、DRAFT-RECOVERY.md | 后端文字实践/Feedback/typed草稿冷恢复只有限子集；原E01—E10不可全PASS。186静态65有界/84部分/18缺口/19未来外部不是运行资格，51共享操作缺第二消费者；无工具/无成果也能记录，恢复不重放外部动作 |
| V3-F01—04 / X1—X6相关 | 选择性本地重基；移植真正适用detector/worker安装定位/full-suite候选；修旧reproduce.sh system-site/固定输出问题 | P1，先查现源码/合同；禁止6中间patch叠加或整包覆盖 | workspace/intake/20261031-cloud-integration-v3-review/README.md；20261101-cloud-integration-v3-1-review/README.md | 历史4690same/437diff/2new及13patch失败为旧70dfc397比较；当期重验差异。42tests/47subtests及8控制流只原环境证据，未移植不当当前Core/Windows已修 |
| V3-F05 / S31-E01 | 两历史stdout缺失/历史生成状态保留；若有新证据核执行时generator/test/source绑定 | P2历史证据局限，不造日志、不强制重跑所有历史 | workspace/intake/20261101-log-binding-addendum-review/README.md；20261101-cloud-integration-v3-1-review/README.md | MISSING/UNVERIFIED；时区误读已撤回，不再派“修时区”或称造假；事后hash不能补签历史。V3-F06两原22/37模板缺件已关闭 |
| CL-01—07 / J1—6 / X1—8完整总验收 | 同一合格候选贯通知识/资料、三类真实检索、个人知识库特色、学习、AI实际消费纠正、权限/版本/重启导出恢复与故障；逐22格式/37平台承诺保留coverage | P1总目标，新接入只是其中增量，必须继承全部CL/J/X | docs/truth/CLOSED_LOOP_DEFINITION.md第2/6/6.1节；现行TASKS与唯一执行记录 | CL01共享对象单写者；02内容可用；03百科/社区/科研真通道；04非企业特色矩阵；05provider/activity/外实践；06本地实用+专业云接口；07同候选可靠性。J1资料/J2研究/J3特色/J4模型/J5扩展/J6安装；X1替换/X2升降/X3活动/X4renderer/X5失效恢复/X6格式互通/X7学习/X8四消费者当前性。不能用总数、接口或代表样本算全链PASS |
| CL-06/J4/J6安装态AI、跨版本升级/回滚 | 先读Owner待决，核是否已有后继授权；仍未授权则保留；可研究不改变全局配置的合法隔离路径 | 关键决策依赖，不自动改监听/网络/版本 | workspace/intake/20261030-zcode-backend-closure/OWNER-决策清单.md；src-tauri/tauri.conf.json；活动指针green_update_authorization | 旧0.6.14同版本重装不等于真跨版本；宿主127.0.0.1 LM Studio不能冒充Sandbox guest真实AI。监听地址/沙盒Networking子决定须明确授权；当前安装器版本现场核实，旧报告不当最新配置 |
| UI-01…24 / V01暂停 / 术语日志 | 只在恢复UI后补UI06/18/21/23/24等PARTIAL与Owner审美接受；持久跨重启日志/未捕获异常兜底、普通术语、教学第5条声明差异；新树统一候选验收 | UI暂停；可读研究/接入后端不自动授权产品布局重做 | 唯一执行记录2026-10-28 V12小节；.project-local/ui-audit-remediation-mapping-final.json；workspace/intake/20261028-plain-language-errors-and-activity-log.md | 2399P/7F是历史已后继修复：24d为2406P，V12为2418/2418P且已有真实引导/导航。不能派“七失败尚未修/原生全未验”；当前HEAD资格与Owner视觉接受仍未建立。旧V12模型未复跑，不能借V9真模型PASS；大库RSS/SQLite C、物理断电窗口/多栏OCR准确性仍有限 |
| 真实云推理/原始上下文外接/远期能力 | 专业云接口必须当期验收；真实云调用另记后续未执行；原始外接NOT_CONNECTED，不把接收候选当真实外部采集。保留required及具名长期能力 | 真实云推理不是本地首版阻塞；FT01—04/V01等不自动解冻 | CLOSED_LOOP_DEFINITION.md；CAPABILITY_ATLAS_V2.yaml；活动指针owner_scope_current/model_delivery_override | 模型加载/MCP通/SDK导入均不是业务消费者或效果PASS；不自动上传资料、付费调用或改provider。原始Agent会话留来源系统，AAOS任意领域提炼知识，不限编程 |

## 已完成，不再作为欠账重复实施

- 本轮131治理检查：按主任务已存最终回执引用；本子任务未重复执行，不把该数量当产品PASS。
- 865 AAOS来源+13管理来源的仓库相对本地保全、45近期包及125恢复成员复用；沿 LOCAL-SOURCES.json 和 canonical local-closure-* 读取，不重复制/重审整个历史。
- 131、865+13、45、125口径不同，不相加；45与131准确资格取其原回执，本报告未重新计数。
- 10/23原文14,897B已补；13组对照/产品身份/闭环入口已归位；V3-F06模板缺件关闭；时区误读撤回；历史186份preOct无损归档及默认检索隔离已有证据。
- Host三对象已准备、历史七失败后继已全套通过、zc1c8安装态冲突子集已验；仍保留各自源码/候选身份，不能因此宣布当前整树闭环。
- 已做的清理不能再次计回收；operator旧28,352,993,453B/351,032文件/243私有/581布局只原时点；674旧错误与533根旧ACL清单不可继续冒充当前总阻塞。

## 新会话必须保留的边界

1. 保存dirty源码、精确HEAD+完整patch SHA+untracked身份；不hard reset/clean。本轮原始任务前32处与较晚baseline34处含2项已启动修改不同，不能一概归本轮。
2. ignored源码材料、原始归档、运行和数据库独立保全；搬迁完整项目必须带 `.project-local/archives/`。Git clone并不包含865+13原件；完整对话local-only，不能被公开索引或聊天业务库自动收走。
3. 优先读取 LOCAL-SOURCES.json、SOURCE-MAP、恢复manifest，路径失效先找ZIP/精确SHA；不扫描磁盘/home/凭据、E/F或任意外部路径。AIWORKLAB独立，不共享业务DB。
4. 生成/静态映射/单测/mock/真实Core和worker/真模型/同候选安装/精确SHA CI/Green/Owner接受分账。原FAIL/INVALIDATED/skip保留，后继PASS仅其源码与环境；未核不是暂停，暂停不是失败。
5. 全量截图包和该批MiniMax素材已取消，不恢复。Green替换、真实库覆盖、发布不随构建/CI PASS自动执行。

## 本次核对限制

仅本地只读文档/Git现场核验，未测试/构建/调用模型/访问远端，不宣称所有历史正文、附件或所有软件特色已审。ripgrep shim不可启动后使用PowerShell Select-String做精确文件定向查找。数据边界skill `C:/Users/ALEX/.agents/skills/workflow-assistance-project-data-boundary/SKILL.md` 被文件权限拒绝，未绕过；证据输出沿父任务明确指定的ignored目录，不改正式文档。
