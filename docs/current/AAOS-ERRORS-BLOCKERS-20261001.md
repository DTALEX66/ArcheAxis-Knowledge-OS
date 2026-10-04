# AAOS 错误与阻塞集合（2026-10-01）

状态：`PARTIAL`；这是本轮审计观察，不代替实时 CI、运行日志或 Owner 决策。

| 项 | 已观察证据 | 下一步 / 验收边界 |
| --- | --- | --- |
| 权威入口 | 根 `AUTHORITY.md` 缺失：`AUTHORITY_REFERENCE_MISSING`；项目实际 Authority 索引和 R6/M0 文件存在。 | 遵循已有索引，不从历史任务包重建权威。 |
| 正式 UI | 阶段 Native 64 张截图覆盖 16 route、两主题、720/1280；未完成逐页母版像素/交互/DPI/IME/UIA 验收。 | 用 12 张产品母版与品牌图逐页核对；补空/加载/错误/离线，并重建最新源码安装候选。 |
| 图标/配图/动效 | 现有 Lucide 矢量有局部部署；其余 UI01–UI14 为候选库，不能把 React 库直接当 Avalonia 控件。 | 核具体版本、许可证与引用路径；按母版做本地资产和低频光效，验证 reduced motion。 |
| 真实后端 | iv32 原生握手和阶段 Home/Evidence 空态 Core 回读已见证据；原创持久化、全路由对象导航、多格式质量、真实模型纠错、重启回读未闭合。 | 按 `AAOS-UI-BACKEND-MAP-20261001.md` 与 R6/M0 用真实输入逐跳验收，未知保持 UNKNOWN。 |
| Desktop 崩溃 | 历史启动崩溃不能仅凭 `0xe0434352` 判根因；阶段候选可启动不证明后续源码稳定。 | 新候选采集实际 Desktop/Core stdout、stderr、Windows 事件与启动参数，复现后定位堆栈，再修复和回归。 |
| 当前 CI | `0345d2d862f026cc10fa3c74e1b57f8ba5474e66` 的一轮 `test (3.12)` 失败；本地定向测试与构建通过。 | 提交本轮过期导航/输出断言修复，等待同一精确 SHA 的 CI readback；失败不能算 PASS。 |
| 本地全量测试 | 上轮 3550 passed、35 skipped、13 failed；其中 5 项受非规范 `--basetemp`、6 项受 Green 父目录被忽略的 `release-identity.json` 影响，2 项旧 UI 文案/宽度断言已修改。 | 使用项目规范入口复核；本地环境型失败与干净 CI 失败分开报告，不删父目录资产。 |
| R6 资格/发布 | `R6-STATE.json` 为部分测试；A02/A16 及 G01–G14 有 Owner/真实运行关卡，release `FROZEN`。 | 不以编译、PR、push 或网页预览宣称 Local Green/发布。 |
| 两棵本地树 | 正式根 `codex/Audit` 存在未知修改及大量未跟踪历史文件；Green 中隔离 UI 分支独立。 | 保护正式根；只提交任务所属 UI 分支文件。双端一致须分清同远端提交与两处工作树一致，后者当前未证实。 |
| Green 目录边界 | Green 根同时含旧运行时、阶段候选、用户数据、验收输出和 `.ui-task-tree` 开发目录；其中有一套独立 Git 克隆及三棵主仓库工作树，均非已安装产品。两个旧 UI 树 dirty。 | 按 `AAOS-GREEN-REPOSITORY-BOUNDARY-AUDIT-20261001.md` 的 GC-01..05 审计；先定未来隔离树路径、保护成果和更新引用，再逐项处置。当前 `NOT_EXECUTED`。 |
| 清理/迁移 | 用户允许新增分支/仓库目录规范任务，但须先完成逐项审计、引用更新和可回退归档；E/F 盘禁止访问。 | 数据库、缓存、历史、恢复包的清理与迁移继续暂停。分支/目录处置按 GC-01..05 单列，不触碰真实数据。 |

每条关闭需要精确源码 SHA、环境、输入、命令或原生操作、输出日志与真实/合成证据级别。若证据缺失保持 `UNVERIFIED` 或 `BLOCKED`。

---

## 后端分支补记（2026-10-01，分支 `codex/dsh-aaos-real-multiformat-loop-20261001`）

以下是后端任务在阅读**仓库中更新的当前权威**（`DSH-BACKEND-CONTRACT-20260927.md`、`DSH-BACKEND-GAP-MAP-20260927.md`、`docs/architecture/CURRENT_ARCHITECTURE.md`、四个 `*_AUTHORITY_INDEX.md`、交接附件）后，**实测查出并修正的自身错误**。全部已在分支上修复并有回归测试；此处记录的是"曾经写错的东西"，因为它解释了下游为什么可能读到过期说法。

| # | 曾经写错的 | 实测事实 | 状态 |
| --- | --- | --- | --- |
| 1 | `/learning/reviews` 无卡状态时 `schedule_authority = placeholder_ladder` | **`unavailable`**（`next_review: null`、`next_review_days: -2`）；带 `fsrs` 的解释器 → **`fsrs`**。`placeholder_ladder` **只属** `POST /learning/events` | 已修正；`contract_schedule_authority.rs` |
| 2 | 错误体统一为 JSON `{code,message,retryable}` | **只有认证中间件与两条 job 路由是 JSON**；`/jobs/{id}/quality`、`/sources/{id}/members`、`/knowledge-items/{id}/v3`、`/machine/tasks/{id}`、校验失败均为**纯文本** | 已修正；`contract_absent_surfaces.rs` |
| 3 | 合同缺"故意不存在的路由族"清单 | `/research*`、`/plugins*`、`/models*`、`/embeddings/search`、`/graph/search` **全部缺席**（错方法探测 404） | 已补 §8；同上 |
| 4 | M0 全链"唯一校验错误是 legacy migration not verified" | 本机实跑 **`validation_errors: []`**、27/27 阶段、`ok: true`。原引文属于另一环境 | 已修正；`test_m0_chain_claims.py` |
| 5 | 检索"过滤/分页/排序"待核对 | **分页与排序不存在**（只接受 `q`、`active_only`，上限硬编码 **20**）；`reindex` 每次查询前重建，**索引不会陈旧** | 已补；`test_request_body_fields.py` |
| 6 | 未记录评审路由的已知延迟限制 | 评审**在 writer 内同步等 FSRS**：`unavailable` **3.0 ms** vs `fsrs` **83.1 ms**（约投影读 6×）。**串行化点是评审，不是读** | 已补；`contract_review_cost.rs` |
| 7 | 合同未写消费者边界 | 桌面层**不得执行 SQL、不得复制业务规则**；Rust 是唯一权威写者。合同是**可调用的面，不是可复制的规范** | 已补 §0；`test_consumer_boundaries.py` |

**对我自己工作方法的两条修正**（同样重要）：

| # | 曾经的做法 | 为什么错 | 现在 |
| --- | --- | --- | --- |
| 8 | 用 `CARGO_TARGET_DIR=...\build\cargo-gnu`，未说明理由 | 与 `RUNTIME_DELIVERY_AUTHORITY_INDEX.md` 声明的路由不一致 | 已核实 `ARCHEAXIS_CARGO_TARGET_DIR` 是 `scripts/ci/cargo_test.bat` 的**官方覆盖**，并经官方入口实跑验证；`test_build_toolchain_routing.py` |
| 9 | 只在自己的产物内部做一致性核对 | 自我一致**无法发现**"对着错误基线写了正确文档"——第 26 轮我据此误判"后端可推进面已清空" | 改为**先读仓库中更新的权威**；第 27–33 轮每轮都查出真实修正 |

**这 9 项都不是产品代码缺陷**：产品自第 16 轮起只有 3 处真实缺陷（PDF 跨页锚点编号、OCR 语言选择、搜索 FTS 转义），均已修复并有回归测试。上表是**文档陈述与产品实际行为之间的偏差**，以及**我自己工作方式的偏差**。

**仍然需要 Owner 的项**（与上文表内条目一致，未变）：`A02`、`A16`、`P0-H01`、`DP-F01`、Research DTO 冻结、真实模型/语料授权、原库修复授权、原 Green 替换与 release 解冻、`services/python-workers` 是否纳入打包。

**环境阻塞（非决策）**：`image.caption` 需本机 Ollama vision 端点；视频解码与网页抓取需"产物+测量"合同设计；登记表两处需修（`faster-whisper-large-v3-turbo` 未登记、`sherpa-onnx` 越根路径）。

**CI 观察**：本轮内 `test (3.12)` 在 `Install and verify local OCR engine` 步骤约 20 分钟后**被取消**两次（非失败）。两次重跑后均 `success`。按上文要求，取消不算 PASS，且我报告的是**重跑后的同一精确 SHA**。

