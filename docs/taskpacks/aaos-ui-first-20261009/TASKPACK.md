# UI 优先后续任务包（派生规划）

状态：PLANNING_READY；产品实施 NOT_EXECUTED。由用户 2026-10-09 当前请求生成，属于后续执行拆解，不自动替换仓库 Authority。原包是来源；原文保全且哈希登记。所有工作切片 ID 都是规划内部 ID。

顺序按补交依赖及用户 UI 优先安排：S0最小接手→S1真实 UI/可靠性/可发现性→S1b学习课程→S2教学反馈与基础表达→S3知识/AI/资源/扩展互通→统一验收。不能先把整个历史治理/池/仓库清理全做完才开始 UI。

首批执行：UF00→UF01→UF02→UF03；CB01从UF00后按唯一writer安排，再UF04；UF06在UF02之后完成。首批可独立交付，后续 UF13 是全包收口而非首批开始前置。S01是首批UI之后已明确纳入交接的独立清理线（S01.A/B/C），V01仍是暂停队列，FT01–04冻结自动执行但保留能力意图。团队若获准并行，共享源码写入仍须串行或隔离后统一验证。

依赖表示完成切片所需最小基础，不意味着后端大重构。一个切片先有实用界面和真实最小路径，再扩展；没有后端时明示 unavailable，不用 demo 数据假绿色。下表所列 write_set 是候选改动范围，接手先核实际文件，再确定有限实际修改集。

| ID | 阶段 | 内容 | 前置 | 页面 |
| --- | --- | --- | --- | --- |
| UF00 | S0 | 最小基线接手与页面承接核对 | 无 | 20 |
| UF01 | S1 | 正式 UI 视觉、资产与公共 Shell | UF00 | 01、02、03、17、18、19、20 |
| UF02 | S1 | 同一套页面与有限运行适配器 | UF01 | 支撑/跨页 |
| UF03 | S1 | 工作台、知识库、阅读编辑真实闭环 | UF02 | 01、02、03 |
| UF04 | S1 | 系统可靠性、版本与工作区恢复入口 | UF03、CB01 | 19、20 |
| UF05 | S1b | 学习路径与课程主旅程 | UF03 | 06、07 |
| UF06 | S1 | 全部能力及细项可发现性 | UF02 | 17、18 |
| UF07 | S2 | 教学需求到反馈修订与人工交换 | UF05、CB02 | 08、09、10、11、12、16 |
| UF08 | S3 | 双链图谱与研究工作面 | UF03、CB03 | 04、05 |
| UF09 | S3 | AI 记忆、纠正评测复测与受限回执 | UF07 | 13、14、22 |
| UF10 | S3 | 资源、开源吸收与模板入口 | UF06、O01 | 15 |
| UF11 | S3 | 导入导出、多格式与平台互通 | UF07、CB04 | 16 |
| UF12 | S2 | 基础画布与视觉表达 | UF07 | 21 |
| UF13 | FINAL | 当前 UI 切片统一验证与交接 | UF04、UF06、UF08、UF09、UF10、UF11、UF12 | 支撑/跨页 |
| CB01 | S1 | 工作区恢复有限契约及隔离恢复后端 | UF00 | 支撑/跨页 |
| CB02 | S2 | 教学交换和修订合同最小补齐 | UF05 | 支撑/跨页 |
| CB03 | S3 | 集合、属性、关系、视图与公式增量 | UF03 | 支撑/跨页 |
| CB04 | S3 | 格式、worker 资格与旧库迁移缺口 | UF03 | 支撑/跨页 |
| O01 | S3 | 开源池、模板供体及依赖维护核对 | UF00 | 支撑/跨页 |
| G01 | SUPPORT | 冻结旧执行路由与更新消费者投影 | UF00 | 支撑/跨页 |
| S01 | INDEPENDENT | 整仓体积、历史跟踪及外溢剩余审计 | UF00 | 支撑/跨页 |
| V01 | INDEPENDENT | 已暂停的本地验证与 CI 节流承接 | UF00 | 支撑/跨页 |
| H01 | SUPPORT | 独立细项基线与历史覆盖差距 | UF00 | 支撑/跨页 |
| M01 | ACCEPTANCE | 原生、安装、人工试学与长期效果资格 | UF04、UF05、UF06 | 支撑/跨页 |
| FT01 | FROZEN_FUTURE | 动态表达与参数仿真分轨 | UF12 | 支撑/跨页 |
| FT02 | FROZEN_FUTURE | 空间记忆及 3D/VR/AR/XR | UF12 | 支撑/跨页 |
| FT03 | FROZEN_FUTURE | 同步、多端、可选训练与维护扩展 | UF06 | 支撑/跨页 |
| FT04 | FROZEN_FUTURE | 可选科研接口与高级 Agent/Marketplace | UF09 | 支撑/跨页 |

## UF00 · 最小基线接手与页面承接核对

状态 `NOT_EXECUTED / NO_EVIDENCE`；激活 `FUTURE_SLICE_SELECTION`。

实施：

- 现场读回两目录 branch/HEAD/status 与全部未提交修改，确认本切片唯一 writer；本轮快照不能当下一轮当前事实
- 确认 SUP-022 与 10/04 Q 规范有效条款；将 10/09 用户优先级、产品与 UI 增量写入现有当前入口，不伪造 SUP 编号
- 把 22 页面职责映射到现有 route、对象、读写合同与缺口；逻辑页面不强制 22 个独立路由
- 保留原始档案和旧日期证据，停止旧包自动执行，仅冻结已被取代条款

验收：

- 有效基线与 dirty 保护清单可回读；未丢失未提交改动
- 页面→源码→合同→验收映射明确；缺失权威标 AUTHORITY_REFERENCE_MISSING
- 只做支撑 UI 的入口修正，不以全仓治理完结作为启动 UI 的前提

验证入口：git status --short；git diff --stat；读取现有 Authority、合同与来源 SHA；结构门禁按 changed-path 发现。

## UF01 · 正式 UI 视觉、资产与公共 Shell

状态 `NOT_EXECUTED / NO_EVIDENCE`；激活 `FUTURE_SLICE_SELECTION`。

实施：

- 以新 22 页参考、tokens.css 和资产清单更新真实 React Shell；沿用现有黑/白/cosmic 主题与业主 emblem
- 保留一级域/二级页/三级对象、搜索命令、历史路由、窄窗抽屉、可键盘操作和动效降级
- 复用已修复状态栏、Inspector、焦点与 A0；截图只作比较，业务图形用真实对象或清楚的 unavailable
- 登记逐资产哈希、许可、用途、打包与主题差异；包内字体是候选，不强制新增字体或升级依赖

验收：

- 主要布局、字体、色彩、间距与原图同尺寸对照；差异有理由和来源
- 宽窄窗、三主题、焦点/弹窗/返回与状态栏回归无已知 T1–T5 倒退
- 演示笔记、假 KPI 和占位按钮未冒充业务结果

验证入口：现有前端类型检查、受影响 Vitest；现有 A0 与状态栏故障注入回归；真实 DPI/IME 留 M01。

## UF02 · 同一套页面与有限运行适配器

状态 `NOT_EXECUTED / NO_EVIDENCE`；激活 `FUTURE_SLICE_SELECTION`。

实施：

- 移除 desktop 与 browser 业务页面分裂，React 页面只接现有统一数据接口；transport 随宿主适配
- 复用现有 Tauri production frontendDist/custom protocol 修复和 Core bridge，不重造 router 或本地 DB
- 将四个 canonical surface 向真实页面职责拆分；保留 legacy route/deep-link 兼容入口与无后端状态

验收：

- 桌面/浏览器挂同一业务页面；浏览器没有 Core 时明确不可用，不能回退假业务数据
- Rust Core 仍是 SQLite/CAS 唯一 writer；不存在 UI localStorage 第二业务库
- 原生产 custom protocol、有限命令、权限与历史路由不退化

验证入口：前端适配器/路由回归与严格合同校验；隔离 Core+Tauri 原生回读；非交互优先，真实窗口启动遵守确认边界。

## UF03 · 工作台、知识库、阅读编辑真实闭环

状态 `NOT_EXECUTED / NO_EVIDENCE`；激活 `FUTURE_SLICE_SELECTION`。

实施：

- 接续 CanonicalLibrary/CanonicalKnowledge 与成熟 Tiptap，不新造编辑器
- 普通文本/笔记/草稿不需依据、云服务、额度或网络即可保存；内容身份与核验、采用、掌握、AI 资格分别展示
- 新建→中文编辑→保存→检索→引用→版本查看→退出重启回读；原件/CAS/未知载荷保持
- 编辑上下文和草稿恢复、空态、错误、权限、冲突及取消必须实际可用

验收：

- 隔离本地数据根的 Core 实际持久化与重启回读通过，原始来源哈希不变
- 离线未配置模型照常保存；保存失败不会显示成功或吞草稿
- 一份真实 ID/版本可从列表进入正文、原件与历史；来源未绑定可区分

验证入口：现有 document/block/draft/reader 定向合同与前端测试；隔离 GUI/Core 持久化 journey；物理中文输入另列 M01。

## UF04 · 系统可靠性、版本与工作区恢复入口

状态 `NOT_EXECUTED / NO_EVIDENCE`；激活 `FUTURE_SLICE_SELECTION`。

实施：

- 将已存在备份创建/列表接到系统页，使用 Core 实际返回标识和元数据，校对旧正则/显示名差异
- 增加选择→完整性及兼容预检→明确确认→恢复→故障反馈→重启回读；版本恢复和工作区恢复分别表达
- 普通保存、草稿恢复、Document 版本恢复、AI 撤回、整个 workspace 恢复是五类动作

验收：

- 备份列表到恢复完成是一条真实用户路径；schema/ID 不匹配显示真实错误
- 独立数据根恢复后 DB/CAS/对象/引用/草稿回读一致，失败不破坏原库
- 用户确认只作用于选择的恢复目标，不以脚本 21 步历史 PASS 替代当前 UI 验收

验证入口：BackupPanel/SettingsSpace 定向前端与 bridge 合同；隔离备份/损坏包/不兼容/取消/重启回读；禁用正式库作为测试材料。

## UF05 · 学习路径与课程主旅程

状态 `NOT_EXECUTED / NO_EVIDENCE`；激活 `FUTURE_SLICE_SELECTION`。

实施：

- 复用已有课程生成/查看/render 与学习对象，不新建教学平台或数据库
- 按已有 Profile/Recipe/Event 模型承接诊断、先修缺口、负荷、编码、复习提取、训练实战、Teach-back、元认知与反馈画像巩固；尚无模型的子项进入详情并挂可验收后续缺口
- 课程绑定知识不可变版本，目标/场景/练习/rubric/进度/events 与 renderer 能力分开
- 保留旧知识/课程绑定；stale binding 提示，不偷偷升级老课或旧事件 rubric

验收：

- 知识→学习路径→课程→真实练习入口可回读，缺项不靠假进度补齐
- 课程离线保存及重启有效；源版本更新时旧绑定仍能解析
- 8 renderer 名称不被宣称为 8 个真实引擎

验证入口：现有 course/learning 合同、前端及版本绑定测试；隔离 course 生成、保存、阅读、学习事件重启回读。

## UF06 · 全部能力及细项可发现性

状态 `NOT_EXECUTED / NO_EVIDENCE`；激活 `FUTURE_SLICE_SELECTION`。

实施：

- 能力目录从现有 CAP/registry/证据投影生成；16 父项全部可搜索和进入详情
- 对照原蓝图、97 资产来源、新任务书与 186 设计细项，建立子项/别名/依赖/供体/承接任务映射
- 当前可用、实现程度、资格、冻结执行及未来意图独立显示；缺证据 UNKNOWN
- 旧 REQUIREMENT_TRACE 的依据前置条款按新普通保存决定纠正适用范围；不创建第二进度数据库

验收：

- 没有能力被只因延期而删除；父项/细项和名称别名可发现
- 独立核对来源与实际投影，186 设计文本不自证明需求已全覆盖
- 每个缺口可回到任务与来源；历史 PASS 未显示成当前可用

验证入口：registry 合同、搜索/别名/状态投影测试；96 跟踪项和 16 CAP 完整核对；缺失细项来源明确标记。

## UF07 · 教学需求到反馈修订与人工交换

状态 `NOT_EXECUTED / NO_EVIDENCE`；激活 `FUTURE_SLICE_SELECTION`。

实施：

- 串联需求→表达方案审阅→交付登记/版本→练习 Teach-back→反馈修订→再交付，优先手工导入导出
- A 知识读取、B 观察候选、C 需求方案、D 交付登记、E 反馈修订复用现有对象；不造五个微服务
- 采纳动作只能由真实 actor 权限触发；专业依据/识别质量/表达适配/操作故障/掌握/AI 资格六类反馈分别负责
- 外部内容为非特权材料，带目的/授权/撤回/哈希/幂等/重试/版本关系，表达修订不改知识正文

验收：

- 用隔离真实 Core ID 实跑整条路径并重启；重复导入/交付不重复创建
- 新知识版本、旧课程绑定、旧评分事件和修订 lineage 都可读
- 人工试学结果单列，合成 actor 或演示答案不算真人效果
- AAOS 可独立完成；未写其他项目或共享库

验证入口：现有教学/course/delivery/actor 幂等负例与 UI tests；本地两次手工交换、校验/损坏/重复/权限拒绝/撤回回读；真实试学 M01。

## UF08 · 双链图谱与研究工作面

状态 `NOT_EXECUTED / NO_EVIDENCE`；激活 `FUTURE_SLICE_SELECTION`。

实施：

- 复用知识关系、别名、锚点、搜索和投影；图谱不是新的主存储
- 节点/边/反链能跳回真实文档和来源；图形不可用有列表降级
- 研究问题、材料、假设、方法、反证与结论通过既有空间文档承接；学术接口/GraphRAG 作为可选合格供体

验收：

- 图与列表查询同一对象/版本，增删关系可重启回读
- 研究结论的来源与依据独立呈现，离线不制造学术检索结果

验证入口：关系/反链/索引与组件定向回归；Core 数据变更→投影→来源跳转回读。

## UF09 · AI 记忆、纠正评测复测与受限回执

状态 `NOT_EXECUTED / NO_EVIDENCE`；激活 `FUTURE_SLICE_SELECTION`。

实施：

- 复用已有 machine correction/retest 和有限任务接口，补 memory→候选→回答→评测→采纳→复测→撤回旅程
- 记忆/知识包/规则技能/用途/范围/时效/版本/客户端消费只在产品授权范围内；不读取私人 Agent native session
- 模型存在、可发现、可加载、调用成功、端到端有效五层分别报告；预算、超时与资源串行按真实状态
- AI 生成身份不能伪装 human，原答案与 rubric 版本不改写；通用 Agent Runtime 与参数训练独立延期

验收：

- 来源授权与最小权限合同、human 假冒拒绝和撤回后的消费行为可验
- 有现有可用模型时真实 isolated 调用并记录；缺模型 NOT_RUN，不下载大模型或伪造 REAL
- 机器资格不等于人类掌握或专业知识可信

验证入口：现有 correction/retest/permission/receipt 负例回归；可用模型条件下同 Core 持久化、重启、撤回；否则保留明确环境缺项。

## UF10 · 资源、开源吸收与模板入口

状态 `NOT_EXECUTED / NO_EVIDENCE`；激活 `FUTURE_SLICE_SELECTION`。

实施：

- 复用已有模板与 28 学科登记、真实对象版本/坐标/引用和成熟编辑器属性；不再实现已存在 cursor 分页
- 资源入口分别显示可用插件、吸收算法、SDK/API/CLI、内容参考、候选和冻结供体
- 只接当页所需供体，复核 68 surface 记录及 115 冲突的适用项；不安装整个 369/691 池
- 模板共用 capability 与 versioned binding，超页数量/空页/循环 cursor/重启均可验

验收：

- 模板创建→编辑→保存→再载入→重启的内容/位置/引用不丢失
- 供体模式、版本、许可证与可用资格不混淆；索引数量不是集成数量
- 分页当前实现被复用并经新切片测试，未默认为仍有旧 100 条限制

验证入口：现有模板 binding/editor attrs/cursor 回归；隔离真实 Core 模板规模与重启验证；外部 API 缺环境单列。

## UF11 · 导入导出、多格式与平台互通

状态 `NOT_EXECUTED / NO_EVIDENCE`；激活 `FUTURE_SLICE_SELECTION`。

实施：

- 人工教学交换已在 UF07 完成；这里扩展真实 worker/adapter 与现有 profiles
- 每种格式独立记录正文/结构/定位/损失/启动/安装态，不以文件扩展名支持冒充保真
- 功能等价、数据兼容、双向往返、增量同步四类独立验收；完整平台范围保留，按实际 profile 分批
- 未知原始字段、媒体与 CAS 保留；原始字节不格式化，失败仍保留原件

验收：

- 选定格式/平台对象往返、损失报告及引用定位可回读
- 没有默默吞未知 payload；不把 fixture 通过等同正式旧库全迁移

验证入口：现有格式矩阵、worker/Core 合同和 profile 验证；isolated 导入/导出/第二次导入幂等/损坏材料回读。

## UF12 · 基础画布与视觉表达

状态 `NOT_EXECUTED / NO_EVIDENCE`；激活 `FUTURE_SLICE_SELECTION`。

实施：

- 先完成课程/表达方案关联的图文、节点关系、布局与媒体引用，SVG/Canvas 是可编辑表达
- 复用对象版本、坐标和 CAS，不把参考截图当地业务画布
- 动画产物、参数仿真、空间场景/XR 的基础元数据与能力详情保留，高级引擎留 FT01/FT02

验收：

- 编辑表达→保存→退出→重启后图文、布局、媒体引用完整
- 导出的表达 revision 不改知识正文；不宣称基础图文已实现物理模拟或 XR

验证入口：已有 canvas/layout/template 合同与组件回归；隔离 Core 保存、再载入、引用缺失和表达修订回读。

## UF13 · 当前 UI 切片统一验证与交接

状态 `NOT_EXECUTED / NO_EVIDENCE`；激活 `AFTER_IMPLEMENTED_SLICES`。

实施：

- 按已实施范围逐页留同尺寸参考/真实界面、后端 ID/版本、差异与未接通项；运行现有门禁
- 记录源码快照、工具版本、命令、退出码、前后哈希和日志；源变化 INVALIDATED
- 更新现有 Q/F/开放台账有效承接与六类验收，不把计划/LOCAL_PASS 当完成产品
- 先交付小切片并持续收口，不要求等 22 页全做完才展示首批 UI

验收：

- 已实施页面无演示数据冒充，原生与 browser 运行界线明确
- 本地行为、安装生命周期、人工交换、真人试学、长期效果、治理分别记账
- 所有未运行/失败/缺环境/云端额度问题仍可见，required skip 不算 PASS

验证入口：现有受影响门禁与 canonical quick/full（先核对当前脚本及暂停任务授权）；当前工作区快照本地结果；物理/native/install/manual 交 M01。

## CB01 · 工作区恢复有限契约及隔离恢复后端

状态 `NOT_EXECUTED / NO_EVIDENCE`；激活 `FUTURE_SLICE_SELECTION`。

实施：

- 核对既有 backup/create/list、离线恢复脚本、真正 Core backup_id/filename/schema 与 document_restore
- 在现有恢复底座上补受限的 preview/validate/restore/restart 语义与权限，尽量复用而非另写恢复引擎
- 需要新字段/命令时按合同版本化，不将任意路径开放给 WebView，不偷改 strict v1
- 恢复操作处理一致快照、CAS 引用、兼容性、取消、失败与原库保全

验收：

- 真实 backup ID 可被前端消费，preview/readback 和拒绝路径明确
- 原库/坏包/不同 schema/WAL/重启场景在独立 fixture 中可验，恢复失败原目标不损坏

验证入口：已有 backup/restore/core bridge 合同与独立恢复回归；不使用正式库或原始恢复档案，不安装/卸载宿主。

## CB02 · 教学交换和修订合同最小补齐

状态 `NOT_EXECUTED / NO_EVIDENCE`；激活 `FUTURE_SLICE_SELECTION`。

实施：

- A–E 语义映射现有 source/knowledge/course/delivery/learning-event/correction 对象，列出实缺字段
- 补 schema version、stable ID、purpose/scope/privacy/withdrawal、idempotency/hash/retry 与 lineage
- 权限从真实 actor 产生，producer 不能自报 human；外部教材不提升执行权限

验收：

- 旧 v1 包继续验证、新字段按版本扩展；重复/冲突/伪冒/撤回负例 fail closed
- 版本 lineage 和知识/课程/表达独立，历史 event rubric 不被替换

验证入口：现有跨语言严格合同/权限回归；隔离 import/export→Core→重启→withdraw/readback。

## CB03 · 集合、属性、关系、视图与公式增量

状态 `NOT_EXECUTED / NO_EVIDENCE`；激活 `FUTURE_SLICE_SELECTION`。

实施：

- 复核 F02 的既有实现与缺口，按集合/属性/关系/过滤视图/公式拆可交付子项；只补实际缺口
- 复用 Document/Block/source/CAS、版本与 unknown payload；不重建知识主库
- 公式执行限制、版本变更和索引投影归 Core 合同

验收：

- 每个子项都有源条款、真实写读和离线重启证据，未实现细项在 UF06 可见
- 关系/视图不会变成第二 writer，错误公式不会静默成功

验证入口：现有对象/关系/视图/公式测试，缺口补针对性回归。

## CB04 · 格式、worker 资格与旧库迁移缺口

状态 `NOT_EXECUTED / NO_EVIDENCE`；激活 `FUTURE_SLICE_SELECTION`。

实施：

- 复用已存在 workers 和格式矩阵，逐项辨别 Linux/Windows/外部工具/模型依赖
- 普通导入保留原件；OCR/ASR/图像/Office/PDF/HTML/media/canvas 不共用虚假 PASS
- 旧非空库迁移按明确批准来源做只读快照→隔离目标→差分/哈希/引用/重启/回滚；未获来源许可先 NOT_RUN
- 无需为 UI 首批等待全格式或全旧库迁移收口

验收：

- 格式证据足以说明内容/结构/定位/损失边界，缺引擎报告真实原因
- fixture、isolated REAL Core 与正式用户旧库资格分开；源哈希/未知载荷未丢失

验证入口：现有 worker/Core/迁移/备份入口；按合同发现，禁用正式恢复材料。

## O01 · 开源池、模板供体及依赖维护核对

状态 `NOT_EXECUTED / NO_EVIDENCE`；激活 `FUTURE_SLICE_SELECTION`。

实施：

- 读取 OSS/Qoder 交接与现有 68 surface，按供体身份/吸收方式/许可/版本/权限/实测资格解释冲突
- 当前 115 冲突涉及 59 记录，仅处理当前页面所需项；其余记录冻结及激活条件
- 28 学科模板与供体目录复用同 capability，不独立维护第二状态库；不用来源行数考核集成率
- 承接 F14 当前所用依赖版本矩阵、既有 SBOM/NOTICE 入口和可迁出；升级需独立数据副本演练、锁文件与回退，不擅自 major/global upgrade，退出演练由 UF11/M01 承接

验收：

- 每个所选供体有采用/候选/延期/拒绝与证据原因；完整池意图未删除
- 共享文件从已存在分支/dirty 实现人工审阅集成，不盲目 cherry-pick 不同祖先分支

验证入口：JSON 唯一 ID、引用与 selected scope 事实核对；官方许可/版本仅在具体选型执行时核实。

## G01 · 冻结旧执行路由与更新消费者投影

状态 `NOT_EXECUTED / NO_EVIDENCE`；激活 `FUTURE_SLICE_SELECTION`。

实施：

- 按 FREEZE-REGISTER 逻辑冻结过时栈/重复任务/已替代门槛，保留原件与日期绑定证据
- 活动任务、能力投影、引用入口、context 消费者和有限 gate 同步；不构建新治理平台
- 本规划 ID UF/CB 等只是工作切片，不是 CAP/Q/F/SUP 编号；执行再按当前权限写现有 live ledger

验收：

- 旧冻结任务不再被自动重复执行，仍可检索且可恢复；当前入口无旧 formal-Avalonia 误导
- 历史 PASS/FAIL 不改写，不以挪目录假装闭环完成

验证入口：现有 document-authority/path-conventions/引用门禁；changed paths 定向检查。

## S01 · 三项存储清理与长期归档闭环

状态 `NOT_EXECUTED / NO_EVIDENCE`；已纳入后续交接，当前仅更新文档。UI优先，首批后推进；可用 HANDOFF-STORAGE-CLEANUP.md 单独交给Agent。不可逆批量处置仍按精确路径授权判断。

## S01.A–S01.C · 三项清理闭环（明确纳入后续交接）

这三项都是未完成的后续任务，不能因资料归档、精确 exclude 或 UI 首批完成而写成 COMPLETE。UI 保持优先，首批交付后继续本节；也可由用户把 HANDOFF-STORAGE-CLEANUP.md 单独交给一个 Agent。三个子项先共享一份当前计量与归属清单，再串行处置，避免同一 checkout 多 writer。当前整理会话仅补交接，不实施清理。

### S01.A：整仓“50多GB”的全面保全清理

- 主对象是 `D:\All projects\ArcheAxis-Knowledge-OS`，含项目内 `.project-local/`、活跃 worktree、Git 对象、归档、开发输出与历史遗留。重新实测；“50多GB”是用户历史观察，不能写成今天已测值。Record 归档约2.206GB只是子项，不能代表整仓。
- 先读 Git/worktree 状态与本项目目录边界，不跟随 junction/symlink 逃出授权根。不读 `.env`、凭据、私人 Agent memory/session；对私有目录只作不进入的未知归属登记。`.hermes/` 原位保留，不新增输出、不 blanket 删除。
- 按 Git对象、活跃/退役候选工作树、可重建缓存/构建输出、安装器、恢复材料、业务数据、来源原件、历史证据分组；记录绝对路径、归属依据、文件数、逻辑字节、可获得的物理占用及重复/共享计数口径。无法计量 UNKNOWN；不能把硬链接或共享载荷重复计算成实际可回收空间。
- 有用材料都留本项目，复用现有 Record 索引、分段压缩恢复工具与档案，不再复制15GB、不迁外库。允许无损压缩/合并、提取关键信息；摘要不能替代原始字节、来源和恢复配方。可重建副本只有确认归属、生成方式、引用、当前使用与授权后才处置。
- 先形成逐路径 `KEEP / COMPRESS / DEDUP / REGENERABLE_DELETE_CANDIDATE / UNRESOLVED` 清单。大量删除、活跃工作树退役、跨盘迁移或终止共享进程不在默认许可内：先把精确路径、影响、备份/恢复与预期节省做成可审结果，再按实际用户授权判断；不 reset/clean/批量restore，不绕过ACL或文件锁，不运行激进 Git prune/gc 清掉未交付历史。
- 验收：同口径清理前/后全仓计量、实际释放字节、保留字节和未处理字节可核对；每项处置有日志及 readback；压缩去重后从项目内材料恢复并验证原始 SHA-256。安装器、原始素材、恢复材料和历史失败证据不通过删除来省空间；未知仍开放。

### S01.B：外溢数据的归属、迁移合并与清理

- 已明确的来源候选：`D:\tmp`、`D:\All projects\dsh-acl-reports-20261003`、`D:\All projects\.aaos-stray-archive-20261001`、`D:\All projects\.aaos-root-backup-20261001`。另有截图中的 D 根12个临时文件，只按既有迁移清单列出的 exact path 回查，不扫描整个 D盘或 Home。检查来源是否仍存在、已迁走、被其他 Agent 使用或重新生成；历史目录名和旧65文件迁移回执都不是当前归属证据。
- 回查项目内已有外溢迁移清单、哈希、日志和引用；核对创建命令、Git worktree与实际用途，避免把工作流基础设施、他项目文件或未知材料当 AAOS垃圾。既有65项有历史迁移记录，`D:\tmp`仍有未决对象；不要以“目录名像 AAOS”直接决定删除。
- 有用且归属已证实的材料迁到项目规定的档案位置，并与已归档副本比哈希去重、合并索引；先目的端落地及完整恢复验证，再判断来源删除授权。原件不用格式化、改编码或截断。没用且明确可重建的材料列精确处置依据；未知标 UNRESOLVED 保留。
- 只处理上述明示来源和清单中的 exact 文件。不进入其他项目、软件私有目录或 E/F；绿色安装目录/其他外部工作树不因为与 AAOS有关而自动获得清理授权。
- 验收：来源→目的地→SHA/字节数→引用更新→保留/删除授权→现场readback逐项登记；已迁项目内容可检索和恢复。剩余项列绝对路径、归属缺口与下一动作，不能无证据把残留数量记0或整条标 COMPLETE。

### S01.C：`docs/history/` 长期保留与 Git 跟踪裁决

- 对主检出与实际 writer 分别重新盘点 `docs/history/` 的 tracked / untracked / ignored及字节、引用和原件位置；识别分支差异及私有本地 exclude。Qoder提到1114文件/475.3MiB、后续1007条精确exclude均是日期快照，重新核对后再报告当前值。
- `.git/info/exclude` 只是防误stage的本地措施，不是长期保留决定，也不会自动传递给新 checkout。禁止 `git add .`，不能用整体忽略 `docs/history/` 或删除旧失败/权威原文来关闭问题。
- 逐类明确：可公开且应版本化的权威导航/处置登记/哈希/恢复工具/关键文本回执；本项目保留、可无损压缩但不直接进入Git的大原件/历史证据；项目运行缓存和可重建生成物；未知/敏感材料。原件保存在项目目录与已Git跟踪是两种状态，登记必须分别说明。
- 每类写明 `TRACK_EXPLICIT_PATHS / ARCHIVE_PROJECT_LOCAL / IGNORE_PRECISE_GENERATED_PATHS / PENDING_OWNER_DECISION`、理由、原始和压缩哈希、恢复方法、持久入口与消费者影响。默认策略是小索引/恢复配方可审后版本化、原始重料仍完整保存在本项目；不可暗示该策略已经获准 staging/commit/push，更不能配置外部库/LFS上传。若仍有互斥长期选择，提交具体逐路径候选给用户裁决，保留开放状态。
- 原始权威/历史PASS/FAIL和来源日期不改写，摘要带原始引用；压缩合并不改变权威等级。仅在方案获准后修改必要的可共享规则/索引，精确处理tracked文件变动，保持未知文件检查与历史恢复能力。
- 验收：有可查的长期保留/跟踪决策表，每条可回到项目内原件或字节恢复路径；换到不继承本地exclude的合法隔离工作树时，规则与查找仍有效。统计本地防误stage、方案审批、规则落地和Git交付各自状态；未批准/未执行不算已关闭。

三项交付：存储基线、逐路径处置清单、外溢迁移/剩余清单、history长期决策表、压缩恢复与哈希回执、前后体积对比、实际修改范围、待裁决事项和下一份交接。文档留本项目规定的当前/历史目录，明细和原始计量日志留 `.project-local/runs/<unique>/`，统一索引登记。资料可找、字节可恢复、归属/授权可追溯、未知不冒充已清，是闭环标准。

## V01 · 已暂停的本地验证与 CI 节流承接

状态 `NOT_EXECUTED / NO_EVIDENCE`；激活 `SEPARATE_USER_SELECTION`。

实施：

- 此线曾被用户停止；新 UI 规划不视为恢复旧 CI 工作的许可，留作单独后续切片
- dirty 中 local_verify.py/workflows 已有实现，先审阅实际 quick/full、串行锁、快照 INVALIDATED 与缺环境报告，不重复建立测试体系
- 核对 push/PR 重复重型检查、concurrency、新提交取消、快检前置、显式验收候选安装与稳定 required summary
- 根 pycache/egg-info 精确允许分类仍保持未知文件检查；无 global install/模型下载/网络权限变化

验收：

- 可本地/Linux/Windows/外部依赖/人工清单与当前 CI 一致；每次命令/版本/时间/退出码/日志齐全
- 云额度停跑 CLOUD_BLOCKED 不当代码 FAIL；本地通过不冒充 exact-SHA cloud PASS
- 本轮不自动推送、合并、触发重跑或删除历史 artifact

验证入口：先查看现有入口，再按获选切片运行 quick/full；云端与安装人工独立。

## H01 · 独立细项基线与历史覆盖差距

状态 `NOT_EXECUTED / NO_EVIDENCE`；激活 `FUTURE_SLICE_SELECTION`。

实施：

- 旧 270 来源键完整承接，补 Q/F、新 96 项及 UI/OSS/对话，来源键加 namespace 避免 Q00/T1 重名
- 原蓝图、97资产表与六来源文已找回；不再开重复找文件任务；未知更细来源不能写成已读
- 从独立来源对照 186 设计文本与实际 CAP 子项，防止设计/代码自身证明需求完备
- 当前可见用户对话提炼稳定决定和未闭环问题；不扫描私人 native sessions

验收：

- 每条已知来源任务都有合并/保留/冻结/独立挂起去向与理由
- 权威缺失或无法证实的历史全文/细项完整性明确 UNVERIFIED，不阻塞已知首批 UI

验证入口：来源 ID 唯一性、96/22/270 覆盖和原文 hash 对照。

## M01 · 原生、安装、人工试学与长期效果资格

状态 `NOT_EXECUTED / NO_EVIDENCE`；激活 `OWNER_ACCEPTANCE_SELECTION`。

实施：

- 物理 100/125/150/200% DPI、中文 IME、键盘/读屏、窗口缩放、reduced-motion 与普通用户 AQ26 单列
- AQ27 Core 自动资格已有历史 isolated 证据；新快照重新验证，不再整项错标全部待人审
- 当前候选安装/卸载/升级/回滚/快捷方式/实际 WebView2/原 Green 根身份分别核；真实安装或反复窗口须先说明影响并确认
- 三项目可先人工交换；真人试学、回流修订与长期效果按真实时间/人物证据，禁止 synthetic 冒充

验收：

- 独立列治理/本地行为/安装/交换/真实试学/长期效果六类状态，不强造全通过
- 未执行/缺工具/用户未参与项保持 NOT_RUN 或人工待验收；不自动发布

验证入口：选定候选 exact source/artifact hash；当前端到端日志与真实人工回执。

## FT01 · 动态表达与参数仿真分轨

状态 `NOT_EXECUTED / NO_EVIDENCE`；激活 `EXPLICIT_FUTURE_ACTIVATION`。

实施：

- 保存动画产物、参数模型、算法/单位/条件/结果与 renderer 元数据意图；当前只保留发现入口
- 引擎、依赖、预算与真实案例独立评估后再选切片，不自动装全部渲染器

验收：

- 能力详情完整；激活时动态产物与参数仿真分别验收

验证入口：当前仅来源/详情覆盖；引擎验证 NOT_RUN。

## FT02 · 空间记忆及 3D/VR/AR/XR

状态 `NOT_EXECUTED / NO_EVIDENCE`；激活 `EXPLICIT_FUTURE_ACTIVATION`。

实施：

- 保存 2D/2.5D/3D/知识宫殿/VR/AR/XR 的资源、布局、定位、事件与长期意图
- 高级空间引擎与硬件需求由独立后续决定，不因基础画布完成宣称实现

验收：

- 延期不从可发现详情消失；激活需具体硬件/引擎/案例资格

验证入口：当前仅意图与依赖可追溯；硬件/引擎 NOT_RUN。

## FT03 · 同步、多端、可选训练与维护扩展

状态 `NOT_EXECUTED / NO_EVIDENCE`；激活 `EXPLICIT_FUTURE_ACTIVATION`。

实施：

- 保留多端/Web/mobile/加密/增量同步、参数训练可选实验和成本维护退出目标
- 当前核心体验不依赖外部同步、训练或付费，按具体需求选独立切片

验收：

- 未来范围及激活条件可查，不将参数训练当 AI 知识纠正的必要前置

验证入口：当前仅来源追踪；真实同步/训练 NOT_RUN。

## FT04 · 可选科研接口与高级 Agent/Marketplace

状态 `NOT_EXECUTED / NO_EVIDENCE`；激活 `EXPLICIT_FUTURE_ACTIVATION`。

实施：

- 保留科研/GraphRAG/外部学术供体、通用 Agent 编排与 Marketplace 长期意图
- 当前只复用受限任务/工具/回执；不构建新 Agent OS 或强制三项目实时互联

验收：

- 被保留的目标与当前必要接口分开，激活须许可/资源/权限/模型环境与验收

验证入口：当前仅详情/来源；在线第三方与高级 Runtime NOT_RUN。

## 通用验证与边界

默认 PowerShell 7，先动态读版本。现有入口为 scripts/runtime/dev.py、scripts/ci/run_tests.ps1、scripts/runtime/frontend.py/.mjs；writer 的 scripts/ci/local_verify.py 是已有未提交实现，未来用前要读完确认范围与环境。示例命令是未来验证模板，本轮未执行：

```powershell
# 在选定 writer 内；使用项目现有 Python/Node/Cargo，先核实际位置与脚本 --help
& 'D:\All projects\ArcheAxis-Knowledge-OS\.venv\Scripts\python.exe' -B scripts/ci/local_verify.py --profile quick --run-id ui-first-s1-<unique>
& 'D:\All projects\ArcheAxis-Knowledge-OS\.venv\Scripts\python.exe' -B scripts/ci/local_verify.py --profile full --run-id ui-first-full-<unique>
# 快检可用 --tests 指定受影响 Python targets，Node/Cargo 缺 PATH 时使用现有 --node / --cargo
```

quick/full只在对应代码切片授权范围内运行，不能自动恢复 V01 历史 CI 改造/云端工作。脚本发现不了的 Linux-only、Windows安装、外部OCR/ASR/模型、物理IME/DPI、真人试学应保留 NOT_RUN 与具体原因。新增行为测试要验证真实缺口，不为低风险文档变更重跑产品全量。已通过检查不无理由重复。

每次测试记录开始/结束时间、branch/HEAD、dirty摘要、被测文件哈希、工具版本、完整命令、退出码、日志与 skipped原因。源码中途变化 INVALIDATED。LOCAL_PASS/FAIL/NOT_RUN/CLOUD_BLOCKED/人工待验收分开；SYNTHETIC数据在REAL Core中运行仍不是真人效果。历史输入SOURCE_ONLY与当前可用资格分开。

独立临时数据根、数据库、CAS、WebView配置与端口写项目 .project-local/runs；不测试正式知识库/原始恢复材料，不下载大模型/全局软件，不改网络ACL，不推送/合并/发布。真实安装、卸载或反复启动桌面窗口按项目规则先说明影响并确认。

资料总入口 AAOS-资料索引.md；原件在本项目 .project-local/archives/record-20261009。旧压缩恢复 recipes/catalog/objects.pack 也是本项目，离开 Record 仍可恢复；禁止搬外库。来源查找复用 scripts/maintenance/archive_record_materials.py find QUERY；不要因为下个 Agent没找索引又复制整套15GB。
