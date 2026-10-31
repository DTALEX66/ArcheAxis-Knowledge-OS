# R5 独立审计：设计可采纳，工程承接有待核实

审计基线：本地 `codex/local-backend-closure-20261029`，HEAD `3fd0cf7835d2271abb65099a1c65f809e89127ab`；审计期间维护写集为 storage_report 的长路径修正及其测试、本文和任务导航。未改变产品源码，未将历史测试移绑为当前安装态资格。

## 判断

原件完整性及覆盖计数 PASS；作为可直接实施/验收的工程合同仍 PARTIAL。没有发现 R5 将所有能力谎报已运行：包中明确写了 `NOT_EXECUTED` 和“未审计当前仓库”。下面的实现缺口不等于原件造假，也不因本次归档而自动通过。

方向可保留：人类学习与 AI 资产分开评价；普通保存无联网/审批前置；同一来源/知识/版本复用；Core 唯一写入；预览不产生真实事件；状态查询不启动引擎；关闭不取消、恢复不重放；依赖、任务资格和一次执行分开；required 不因难度被后移。R2 与现行合同没有被 R5 替代。

## 问题与吸收修正

### R5-F01 · P1 · 映射完整，但实际操作与消费者仍全为空缺

证据：`共享/03-186项前后端承接映射.csv` 的 186 行 `R5_真实操作绑定` 都是“待本地记录真实模块/符号/操作/消费者”；25 条验收的本轮执行均为 NOT_EXECUTED。`PedagogicProfile/LearningRecipe/LearningEvent` 被包内列为历史查找线索，本次检查的正式 Core 实际入口是 Course、Teaching、Learning、UI working state 等，不能依名字另建三套对象。

影响：按表头或父族 `core_native` 直接标可用，会把设计覆盖变成虚假的实现覆盖。

吸收：表格保持冻结来源身份，后继沿既有 R2/CL/J 逐项绑定真实类型、操作、第二消费者与证据；已有实现只补核验，不重复开发。验收必须区分源码存在、定向合同、真实 Core、真实引擎、Host 与安装态。

### R5-F02 · P1 · WORK-LAB 主责表述超出了本项目的独立运行边界

证据：后端说明 §4 写“复杂跨工具编排由 WORK-LAB 主责”，逐页 R1 提示词也写由其承担，CAP-0130 的分期说明沿用了这一归属。根 AGENTS.md §9 明确 WORK-LAB 为独立、可选协调方，不是本项目运行前提；跨仓库变更各自授权、检查、回退。

吸收修正：复杂编排仍在本期之外，AAOS 只保留有限知识 Job、研究产物/引用和收据；未来可对接获准的外部编排器，WORK-LAB 是候选之一，不固化依赖或跨项目写入授权。修改本地吸收解释，原始包不改字节。

### R5-F03 · P1 · “方法”标签没有对应当前 AI 资产 Kind

证据：A0 图的类型标签含“方法”，A1 示例名为“版式阅读顺序检查方法”；当前 `crates/archeaxis-domain/src/ai_asset.rs` 的 `Kind` 仅为 Memory、KnowledgePackage、Rule、Skill、Experience。图片中的中文名称不是合法枚举 `method` 的证明。

影响：直接按标签发送新 Kind 会被现有反序列化合同拒绝；另建方法库会制造第二资产真值。

吸收：先为“方法”建立到现有类型及 purpose/content 的明确业务映射，核消费者；确需新增枚举时再评估兼容、导出、历史只读与迁移，不能仅由位图新增后端类型。C4 还须接续原 F05：绑定具体失败 answer/request、旧资产及新版本、固定输入/量规、负向控制与独立复测，不能把候选保存算成效果改善。

### R5-F04 · P2 · A0 与 A1 的示例资产版本不能直接连成同一旅程

证据：A0 的“版式阅读顺序检查方法”为 v0.3／待评测；A1 同名示例显示旧已采用 v1.2 → 候选 v1.3。未标明它们是不同时间点或不同资产。

吸收：后继原型用稳定示例 ID 和明确时间/版本衔接；从概览打开资产时不能悄悄跳到另一版。此为静态设计一致性问题，不是已复现的产品运行缺陷。

### R5-F05 · P2 · 教学与参数图仍是非受控示意

证据：L1 两张海报除了对齐还改变图像裁切和文字布局；L2 位图不能证明 6 列、24px、48px 的实际生成关系。原包 `验证/图稿审阅与实施修正.md` 已承认这些限制，本次看图确认限制仍存在。

吸收：教学比较固定同一内容/图像，只变化教学变量；参数由实际布局或合格引擎驱动，保留算法/单位/初值/结果来源。当前图只能作设计示意，不用于学习效果或仿真验收。无需为本审计重画原件。

### R5-F06 · P2 · 单尺寸静态图未覆盖恢复与可访问性验收

证据：8 图均为 1672×941；三栏页面在较小窗口的收起/滚动/焦点关系没有交互证据。图片虽注明草稿、预览、未评测，但没有真实保存未确认、版本冲突、撤回、IME、键盘及减少动态状态。

吸收：继续沿现行一套流式布局，待 UI 恢复后验证普通小窗与 1920×1080、辅助区收起、草稿与焦点、返回位置及未知结果查原请求。不能把缩放位图当作响应式/键盘/屏幕阅读器通过；本轮不启动 UI 实施。

## 五场景与正式 Core 的有限源码核对

| 场景 | 现有真实承接点 | 本次能下的结论与剩余要求 |
| --- | --- | --- |
| C1 学习 | `course.rs`、`teaching.rs`、`learning.rs`、`ui_state.rs`；`/api/v1/courses`、`/api/v2/teaching/records`、`/api/v1/learning/events` | 已有课程引用、版本化教学、学习事件和可恢复草稿；不新建平行 Profile/Recipe/Event 库。跨活动选区/焦点/返回及整条重启旅程本次未运行。 |
| C2 仿真 | `expression.rs` 的有界 Text/Media 和惰性 capability metadata；现有 readiness/Job | 有限元数据承接不等于仿真引擎。缺引擎、预览隔离、参数/单位/取消/结果身份须分别验；真实引擎未执行。 |
| C3 空间 | 现有 Expression 的坐标/布局/Context、Learning 引用与事件 | 2D 节点坐标不等于完整 World/Room/Locus/Route。地点/路线/布局版本/回忆绑定及文本降级仍需逐项实际绑定；不把 3D 图当运行证据。 |
| C4 AI 纠正 | `ai_asset.rs`、`asset_context_grant.rs`、`machine_evaluation.rs`、`runtime/colearning.rs`；corrections/retests | 已有固定资产快照、采用/撤回、评测与 answer_id/retest_of 绑定，不重建资产库。中文“方法”类型映射与原 F05 的独立负向控制待补。 |
| C5 科研 | `research.rs` 的 methods/experiments/conclusions/unresolved，既有 Document 保存；`public_research.rs` | 实验计划不必等外部工具才能保存。计划记录不是可执行实验定义，真实科研 Agent、计算及科学结论资格均未验证。 |

以上是源码与路由检查；列出的既有测试文件只作定位，本轮没有重跑或签发产品 PASS。对外工具的许可、维护、原生 MCP、费用和版本仍逐工具核验。R5 的 SDK v2 文档只是参考，当前 `pyproject.toml` 的 Python MCP 可选依赖约束为 `mcp>=1.2,<2`，不是同语言或同版本兼容声明。

公开官方依据仅核一般边界：[MCP 生命周期](https://modelcontextprotocol.io/specification/2025-06-18/basic/lifecycle)分别协商版本与能力；[SDK 调用说明](https://ts.sdk.modelcontextprotocol.io/v2/clients/calling)不能证明本项目使用该 SDK；[Tauri capabilities](https://v2.tauri.app/security/capabilities/)限定宿主窗口/命令权限，不能替代 Core 业务授权。本次未升级依赖或调用任何科研工具。

## 证据范围与后继

全成员身份见 MANIFEST；原始 `archive-check.json`、PNG CRC、9 个示例引用、源码快照身份与读取范围在项目 ignored 审计 run 中保全。R5 新要求并入现有优先级：体积/规范化/外溢 → F01—F05 → R2+R5 真实后端绑定 → 同候选可靠性；未来扩展和 UI 实施仍按原授权。

本轮没有产品 API/真实引擎/模型/迁移/安装测试，没有浏览器 HTML 渲染、axe、性能或可点击原型。未发现或未测试不等于已不存在/已通过。结论保持 `DESIGN_INPUT_CONDITIONALLY_ACCEPTABLE / ENGINEERING_PARTIAL`。
