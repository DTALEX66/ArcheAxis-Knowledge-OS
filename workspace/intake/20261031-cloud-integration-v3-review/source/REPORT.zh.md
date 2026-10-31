# AAOS 本轮云端整合验证报告

## 1. 先说结论

**应保留知识/资料工作区为产品骨架，把 Agent 放在共享上下文助手与任务面板中，不改成聊天占据一切的 Agent 平台。**资料、原件、固定版本、学习活动及 AI 采用状态是持久对象；聊天只是操作方式。对话长短不能代替内容校验、人工掌握或机器评测。成熟学习平台以可退出的播放器/开放文件/API/事件适配接入，不复刻其完整后台。

本轮已真正运行的是：Rust Core SQLite/CAS 单写者、真实 PyMuPDF/pypdf 提供方切换和版本升级回退、实际 FSRS 调度、现有生产前端组件通过有限实验桥调用真 Core、保存及进程关闭重启后的读回。没有另建数据库，没有自研 PDF 解析器、LMS、搜索引擎或通用 Agent 平台。

本轮不是完整 AAOS 产品验收。浏览器启动和跨环境服务访问均有真实阻塞；只有 jsdom 组件 DOM，没有浏览器截图或原生窗口。H5P 已获得可复现材料但真实播放/答题事件没有执行。生产模型消费者、四视图同时失效联动、Windows 本地体验仍未完整验证。

本次追加全量结果详见 `FULL-VALIDATION.zh.md`：适用Python5780、Rust/Core1025、前端1983；初始105 skip有42项窄补验关闭。它们不是新增能力总数，不替代下述X1—X8范围限定。

## 2. 基线与继承

- GitHub 实际克隆基线：`8d367bac4a85bebfbb523503678ade0838faa73e`，初始干净；所有修改仅在实验副本。没有推送或发布。
- 上轮 V2 ZIP SHA256：`ebe96405839d52f87bfcaea4dbff770062edc7e2d5b3927efcdbb3969d734db5`，仅继承可靠且范围未变的证据。16 条继承条目见 `mappings/09-evidence-reuse-ledger.csv`，保留组件/元数据限定。
- 186 能力与 22 历史职责保留原键和原文；22 格式、37 平台及最新决定/任务/旅程均列去向。不把历史职责变成 22 个新模块，不逐项跑 186 次测试。台账四层是产品分层，运行资格另列。
- 上轮 OCR 真识别/人为植错/自主检索与已知参考的区别不变。本轮不重做准确率基准，不把新接线合成输入称为新 OCR 错误。

## 3. 实际调用链与最小修复

### 3.1 已有链路直接复用

`JobContent → coreCommand(既有 CoreOperation/生成 DTO) → 有限实验桥 → Rust API → Executor → Python NDJSON worker → 原任务/产物/转换表 + CAS`。

课程：`ImportedCoursePanel → importedCourseStorage → source_import → CAS 原件核对 → document_create → document_get → reopenCourseImport`。运行的是项目原有 OpenMAIC 导出文件适配，不是 OpenMAIC 平台/模型/renderer。

学习：`POST /api/v1/learning/reviews → 既有 SchedulerClient → py-fsrs 6.3.2 → 原学习事件/状态`。只接成熟库，不新增第二调度器。

实验桥只为缺少 Tauri 的 jsdom 测试实现有限操作到既有 HTTP 路由映射；不提供任意 URL/命令，不伪造业务响应。它不是正式可分发的浏览器权限宿主，不能直接当公网 API。

### 3.2 真实发现的问题与补丁

1. **PDF 能力与提供方硬耦合**：首次 pypdf 实际运行失败 `incompatible worker hello`；加入受控提供方后仍失败 `invalid receipt: structure or coverage does not match projected text`。定位到 `worker.rs` 依赖名限定、`executor.rs` worker/receipt 限定、`attempts.rs` 提交引擎限定。
   - 最小修复：增加明确的 pypdf 提供方及引擎对应表；保留版本格式、能力、三产物、hash、覆盖跨度校验；未知提供方仍拒绝。同步原 worker schema，不改业务 Document/Job DTO。
   - `harness/pypdf_adapter.py` 仅调用成熟 pypdf，复用现有 NDJSON transport；不声称表格几何/公式语义/OCR 能力。其 `loss_report` 明确损失。
   - 不是任意插件自动加载系统；正式本地任务应将受控适配器安装/许可/状态展示纳入原资源配置，不能把试验名称原样发布。
2. **旧导航不符合本轮五入口**：旧为工作台/知识/学习/AI/资源，研究藏在知识下。改原 `uiPages.ts` 投影为工作台/资料与知识/研究与比较/学习与表达/AI助手；资源与交换改共享入口；22 个历史 page ID 保留。
3. **未知课件仅报错，缺少有用退路**：仅改 `ImportedCoursePanel`，未知主版本/renderer/字段仍拒绝解析，但可显式只保存并读回原件；不制造课程或掌握状态，不执行输入脚本。
4. **环境配置问题**：npm 默认缓存不可用→项目内缓存；FSRS 缺依赖→局部安装；普通 venv symlink 不符合既有 worker 路径政策→使用 Python 正规 `venv --copies`。没有删除政策或放宽隔离。初版新增测试类型错误已修正并保留失败日志。

完整修改见 `../patches/aaos-isolated.patch` 与 new-files，所有失败历史仍在 `../logs/`。

## 4. X1—X8：结果与边界

| 组 | 本轮实际结果 | 结论边界 |
|---|---|---|
| X1 提供方替换 | 同一原件真实 PyMuPDF 1.26.6 / pypdf 6.10.0；原 Core 任务、输出、转换保存；切换后旧输出可读；原 JobContent 实际呈现四份结果 | 代表 native PDF 文本路径通过；非扫描/表格/全格式等价；不是浏览器视觉验收 |
| X2 升级/降级 | pypdf 6.10.0→6.10.2→6.10.0，实际加载对应库并核对 engine_version；旧/新产物互读；受支持可选课件元数据保存；未知字段/主版本显式回退；worker major2 拒绝 | 代表版本兼容通过，不保证任意上游更新零修改 |
| X3 新增扩展 | 新 pypdf 受控适配器接原 pdf.extract，生产前端无需改；现有 OpenMAIC 文件能力实际接通；H5P 组件准备 | **部分完成**：未证明任意新能力可动态安装；H5P 真运行阻塞；新资源提供方详情/安装体验未完成 |
| X4 新 renderer | 未知 simulation/课件主版本不空白；显示原因、原件保全与原平台继续选项；原件经 Core 读回；不修改现有合法课程 | 安全回退通过；没有伪造 simulation renderer；真实新交互仍需局部播放器组件 |
| X5 不可用/恢复 | 真实禁用能力拒绝执行，普通文档保存继续；启用后同请求成功；幂等重放；Core 测试涵盖取消、断开提交者、重启、失败任务保留；追加8项受控worker超时/撤回权限/旧版迟到结果测试通过 | 部分：真实外部账号撤权/余额/网络模型超时未验证；受控故障测试与真实外部故障分列 |
| X6 格式/特色兼容 | 原 worker 实际执行 MD/CSV/JSON/Canvas，原字节保全；原 Core 双链、片段/块关系接口 4 测试通过；JobContent 共用 | 代表接口通过；Canvas 新样本的互动编辑、所有22格式/37平台的实际软件联动未逐项跑；不把无损原件等于语义无损 |
| X7 学习扩展 | 文件课程候选生产 UI 保存/读回；真实 FSRS 复习调度及重启去重；原教学链 Core 7 测试通过 | 部分：无 H5P 真 xAPI、无实际课堂模型生成、无真实外部专业练习成绩回传；不宣称学习效果 |
| X8 多对象版本 | 课程候选与来源绑定；修改文档后重新打开拒绝冒用旧内容；旧版本写入冲突；恢复为新版本并重启；原研究/教学/来源约束回归 | **部分**：新增同一次知识修订的学习/研究/AI provenance 真Core综合读回；学习明确active=false，研究图仍resolved、AI列表无源当前性投影。这是现有合同/呈现缺口，不是环境阻塞。资料文档自动跨层传播与外部模型新消费仍未验 |

每项精确证据与前端改动归类见 `X-results.csv`。没有将 PARTIAL 写成整体通过。

## 5. 统计与原始证据

- 新增 HTTP 提供方/格式/恢复矩阵：25 个断言，25 通过，见 `evidence/core-matrix-delivery/checks.json`。原始请求、状态码、响应、各提供方配置及同一数据库保留。
- 新增生产组件→真 Core：8 个测试通过（课程4 + 原JobContent读取4），见 `../logs/frontend-qualified.stdout`；DOM保存在 `evidence/frontend-delivery/` 与 `evidence/provider-ui-delivery/`。不是截图。
- 相关前端回归：8 文件66测试通过，含4个上述真实测试，其余fixture/jsdom；**不要把66+8直接当74个独立测试**。
- 相关 Core 最终回归40测试通过；另 PDF 4、worker protocol7、双链/片段关系4、受控故障8测试通过。重复运行有重叠，日志按suite保留，不堆成全能力覆盖率。
- 前端正式构建最终通过（`frontend-build-delivery`；此前`frontend-build-copies`也通过），包含实际 TypeScript 检查/Vite构建；早期失败保留。
- 新合成 native PDF 两页，核对数字 `12.5 km` 和 `-3.0`，不是 OCR 精度测试。新识别错误/纠错数不适用；旧准确率仅按继承表原报告使用。
- 耗时：各测试stdout保留真实时长；新组件测试最终约2.07秒，相关66测试约11.69秒；Core suite各自计时；Vite最终约4.86秒。未建立全流程端到端统一计时，不编造总耗时。没有模型用量/计费记录，不报告成本。

## 6. 前端与 Agent 架构建议

保留资料正文为主，疑点、对照、任务和助手按需展开。已有 `CompanionSessionProvider / ConversationPanel / DockWorkspace / JobContent / PublicResearchPanel / ImportedCoursePanel` 继续复用。导航变更是一次本轮产品分组修复；后续四次实际提供方切换运行中的前端源码hash相同，不代表任何业务变更永远无需改UI。

应呈现：转化完成≠已校验；找参考中≠找到全文；已找到对应内容需有定位；发现差异需类型及依据；已修正需版本且可撤销；无法确认保留正文/疑点。供体名、版本和技术日志放详情，不占阅读主区域。

学习平台优先顺序与许可见研究附件：H5P可作为局部活动播放器；OpenMAIC当前先开放文件适配，完整renderer引入前评估样式/依赖/事件；DeepTutor不默认内置重型整套服务。不要因为能运行一个SDK导入就标成平台已集成。严禁把GPL/H5P bundle错误当MIT、把NOASSERTION当无许可。复杂仿真/科研/XR使用固定活动或结果槽位，未实现时清楚写外部启动/结果导入，不放灰按钮冒充完成。

**删去重复设计**：不要新建“186功能页面”、第二任务系统、第二向量/知识真值库、第二学习调度器、第二Agent记忆库、全文重写式比较器或自研专业编辑器。已有对象、合同、日志、CAS和成熟组件能承接的继续接线。

## 7. 下一步交给 STITCH / 本地 Codex

### STITCH 输入（需本对话评审后再正式做）
沿五入口与现有固定详情/活动/助手槽位，不造聊天主壳。明确“AI助手”的会话与AI知识/评测子区域，避免只换名字误导。请在可运行本地宿主用真实资料完成中文输入、长标题、空态/加载/失败、窄宽视口、键盘、减少动态、对比度截图审计。本轮不能替代这项。

### 本地 Codex 输入（相同范围直接继承，不重做通用全量审计）
1. 按`config/delivery-identity.json`核对并应用已审计补丁，继承云端验证；保持引擎身份/版本/产物/跨度/权限拒绝测试，生产资源配置展示实际提供方，不照搬实验名。
2. 安装真实H5P活动及许可闭包，接既有学习事件/课程版本、attempt/event去重；内容续做状态与xAPI成绩分开。测关闭、断网、恢复、重放和解绑，禁止跨origin任意消息写Core。
3. 完成X8四消费者同一次源版本变化的综合测试；旧评测不自动继承、争议保留建议、普通保存不强行走AI采用审核。
4. 用已有授权本地模型端点验证真实消费/纠正回流；不要把本对话或模拟模型当产品LLM。
5. 在Windows/Tauri/WebView2与用户实际设备验证路径/安装/IME/窗口，之后才能给正式集成结论。

所有能力去向保留；复杂能力按阶段接入，而非本轮暗自删除或承诺全内置。

## 补充：X8 同次修订实际发现
`harness/x8_cross_consumers.py` 使用真实 HTTP 写入知识、学习引用、研究文档/关系和 AI 候选，再修订同一知识并关闭重启 Core。原引用均未被静默改指，学习报告 active=false。`object_reference.rs` 的 Knowledge 分支仅确认 ID 存在并返回 immutable_knowledge_id；研究图的 resolved 表示历史对象能解析，不表示仍当前；AI目录也未提供统一来源失效投影。见 `evidence/x8-qualified/gap-observation.json`。下一轮应在既有解析/投影合同增加明确 currentness/historical 状态并做局部展示，不能误把 resolved 当已核验、不能自动把旧引用换成新引用。这项没有通过更改报告掩盖。

X5 补测 `document_cloud_loop` 首次缺少真实 BeautifulSoup/trafilatura 解析依赖，7项中6过1失败；项目局部安装 BeautifulSoup4 4.15.0、trafilatura 2.3.1 后全部8项通过。网络与模型transport由合成fixture控制；这些是实际Core和worker故障/版本合同测试，不是网络搜索或模型质量成功。

## 独立复核
见 `review/contract-final-audit.md`：独立7项worker协议测试、独立新数据库X8 HTTP读回、SQLite只读integrity、6份提供方阶段前端hash核验。审计发现的复现脚本Rust环境判断问题已修，固定实际1.99.1工具链。没有在全新无依赖机器从零重建整包，因此不声称可复现性已覆盖全部OS/下载环境。
