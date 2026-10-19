# 项目资料收敛与完整闭环实施 · 2026-10-18

当前 **RUNNING_BY_OWNER / PARTIAL**。Owner 本轮要求所有关键历史、权威、规划收敛到本仓库，并开始完整架构、多格式、最短闭环和开源能力吸收实施。此文是本轮进度与查找入口；当前队列仍由 [活动指针](AAOS-ACTIVE-EXECUTION.json) 路由到 [UI 执行记录](AAOS-UI-FIRST-EXECUTION-20261009.md)，没有另立 TaskPack。

## 资料与来源

| 范围 | 仓库内入口与事实 | 边界 |
| --- | --- | --- |
| 权威与当前执行 | `AUTHORITY.md`、`PROJECT_CONTRACT.yaml`、`docs/current/AAOS-AUTHORITY-ROUTES.json`；51 条登记路由现场全部存在 | 路径存在只证明可查，不证明任务完成 |
| Record 历史资料 | `docs/history/record-archive-20261009/MANIFEST.json` 登记的 121 份原件恢复到登记路径，逐份哈希核对；蓝图派生文本也与原登记哈希一致 | 不扫描或导入清单外 59 份其他项目材料；历史指令不自动激活 |
| 历史大型恢复 ZIP | `.project-local/archives/record-20261009/compact-recovery-v1/`；13 个 ZIP 原始 15,042,293,812 字节，经现有共享压缩段方案保存为 1,911,212,397 字节并逐字节重建验证 | 保留原 SHA；不运行旧安装包、覆盖 Green 或恢复真实数据 |
| 前后端正式任务包 | `docs/authority/taskpack-20261013-backend-host/` 34 文件；`docs/authority/taskpack-20261013-frontend-ui/01-Frontend-UI/` 105 文件；全部按包内 CHECKSUMS 检查，原 ZIP 另存项目 `.project-local/archives/taskpacks-20261013/` | 只恢复当前指针已引用的包，未执行包内脚本；PLANNED 保留为规划快照 |
| Codex / Claude Code / Cowork | [跨客户端对账](AAOS-SESSION-RECONCILIATION-20261018.md)、[Codex 索引](AAOS-CODEX-SESSION-INDEX-20261018.md) 与项目内脱敏派生物 | 原始 native session 保持原软件私有；完整 Cowork 逐字正文仍 UNVERIFIED，任务化交接 ZIP 不冒充原会话 |
| 统一待办 | [88 个跟踪 ID 的来源与执行边界](AAOS-EXECUTION-BACKLOG-20261018.json) | 来源映射层，不是第二进度权威；历史 NOT_EXECUTED 不能覆盖当前已实现代码，也不能直接算当前通过 |
| 开源研究与吸收 | 原始 369 候选 CSV、现有 11 项能力吸收 registry、51 项供应链 ledger、现有交叉表生成器均在仓库 | 完整生成表放 `.project-local/runs/be268a2d33/oss-pool-rebuild-20261018/artifacts/`，701 条记录保留跨表身份与重复来源 |

原件保全、缓存、运行日志和会话脱敏材料在**项目目录内部的忽略区**；公开路径、哈希、结论、源码与规划进入可审查文档。仓库内收敛不表示将私有 session、模型、凭据或运行数据库提交 Git，也不复制共享工具和模型库。

## 吸收决策与“降级”含义

维持既定顺序：已有正式实现 → 合法且合适的锁定依赖 → 有限适配或隔离 worker/sidecar → 有具体行为或格式契约的算法/交互吸收 → 有依据的延期或拒绝。产品目标仍覆盖完整闭环；调整的是 donor 并入方式、依赖范围与资格声明。

| 对象 | 本轮采用方式 | 实际判据与后续 |
| --- | --- | --- |
| Rust Core、SQLite/CAS、Python workers | 保持唯一业务写者与有限协议 | 不引入第二正式知识数据库；普通保存不增加模型或人工审批前置条件 |
| Dockview 8.5.1、Radix dialog 1.2.0、Tiptap 3.31.4、PDF.js 6.4.299 | 复用当前 manifest、lockfile、已存在 node_modules 与调用方 | 10/13 包的“已下载未安装”是历史状态；当前安装存在与原生运行分别验证，不重复安装第二套 |
| DeepTutor / OpenTutor / LearningMap 等完整应用 | 按既有能力 registry 保留有限算法、交互、契约或可替换 worker 的吸收边界 | 不把完整上游应用、其数据库和 Agent 平台整体塞入正式宿主；六项冻结对话增量及其他既有冻结保持 |
| Trafilatura、Office/PDF/表格解析、OCR、媒体工具 | 沿现有 worker/adapter 路由验证每种操作 | 原件保管、预览、提取、编辑、导出、往返、位置与损失分开，不把提取成功升级为高保真原生编辑 |
| MarkItDown / Docling / sherpa-onnx / AIRI / TalkingHead | 沿包内复用矩阵及当前代码逐项核对；增强路线保持按需启用 | 未资格项不升级为可用，不下载新模型、不激活第二默认推理栈；代码和资产许可分别处理 |
| Kuzu 等第二正式库 | 保留现有拒绝 canonical store 的决定 | Rust SQLite 与可重建投影承担当前真值；研究参考仍保留 |
| XYFlow 等只有候选或测试引用的来源 | 纠正证据误判；测试字符串/fixture 不能认定产品已经吸收 | 本轮发现资源页测试中的正则引用被扫描器算作 imported_in_source；修复生产证据范围并重建现有交叉表 |
| 其他研究池候选 | 保留原记录、理由与需求触发，不批量安装 | 369 行的历史资格分布 A2/B13/C2/D351/E1 只绑定原验证环境；本轮重建不构成 369 项当前运行验收 |

既有 `CAP-00NN` 能力族与 `CAP-…` donor registry 属于不同命名空间，不强行合并。生成表中的冲突保留，不能以字符串命中、依赖声明或手工改状态清零。

本轮同时修复非 Python 源码扫描把字符串标签、注释和模板文本当标识符的误判；Tiptap 则按明确的 `@tiptap/*` 包名映射认定依赖，避免删去错误字符串证据后反而漏报真正安装的依赖。当前68来源仍保留115项原冲突，分类为基础依赖20、算法吸收15、未来候选10、可启用插件7、未采用11、格式规范3、交互供体2。Tiptap 表面类别按原声明 UX_DONOR 呈现，实际锁定依赖证据另行保留，类别不代替运行资格。

资源资格层原先引用的交叉表、LICENSE 和前端 lockfile 已发生历史漂移。本轮按其登记 SHA 从 Git 找回全部原始字节到 `docs/history/oss-absorption-evidence/20261018/`，只迁移证据路径；受旧许可证/锁文件影响的证据标为 `HISTORICAL_SOURCE_NOT_CURRENT`，没有将旧声明改绑新内容。重建现有资源目录，17项目录/包身份回归通过。归档及来源收敛的公开回执见[来源收据](receipts/AAOS-SOURCE-CLOSURE-20261018.json)。

## 实施与验证

1. 先完成上述资料与缺失权威路径恢复，再复用已有主线实现，核对后端 BE00–12、前端 FE00–25 及现有 UF/CB/S/G 队列的剩余验收。Owner 10/18 新决定将小栖/ASTRYN直接适配进本项目，更新原FE18独立开发边界；见[整合决定](../../workspace/intake/20261018-xiaoqi-in-project.md)，当前集成仍在执行。
2. 本轮已经补上 CW-AAOS-01：单文件及文件夹导入在上传前计算内容 SHA-256，回执必须有非空来源、合法摘要、duplicate 布尔值且摘要与原字节一致；不符不显示保管成功、不入队、不启动转换。回执确认后的列表刷新失败独立显示，仍保留成功事实。两个入口 74 项定向回归通过，模型/Core 为受控模拟；6/26 MiB 真字节编码及 64 MiB 上限有覆盖。
3. 真实 Core/worker 的多格式、重开、位置与失败恢复按现有 canonical probes 继续；候选构建与源码摘要必须一致。历史 72 格式登记、旧 CI、旧安装收据均保留原资格，不能冒充本轮执行。
4. FE21/23 继续沿已接入的生产性能与键盘/焦点实现；FE24/25 仍需当前候选、原生/安装旅程及真实产品资产资格。七图全部视觉、真实模型质量和 Owner 最终认可仍 PARTIAL。

本轮没有 commit/push/merge/release、Green 替换或共享配置变更。最终本地门禁、具体证据和未闭合事项追加到本页及主执行记录；失败、缺失和中断保留，不用历史 PASS 抵消。

## 2026-10-18 本轮验证、运行时迁移与归档收尾

[最终验证收据](receipts/AAOS-PROJECT-CLOSURE-VALIDATION-20261018.json)汇总各阶段独立 source patch、日志和证据层级。
最新产品源码门禁及两次编译、runtime stage 绑定 dirty patch
`e13f8b2bfa99dffac13aeb87c426624171fc0685cac5ee94066ec4bfa864af6f`；其后仅补目录权属路径与结果文档，另行检查。
先前来源收据保留生成时内容哈希，后续路由迁移不追改旧快照。

| 范围 | 当前本轮结果 | 实际资格 |
| --- | --- | --- |
| 前端 | 159 文件、1527 用例 PASS | SYNTHETIC 组件/契约；TypeScript/Vite 和 Tauri 原生宿主构建 PASS，保留 bundle/既有 Rust 警告 |
| Python | 173 项、18 subtests PASS；资源索引/文档 29 项 PASS | 本地定向回归，含无自动 Ollama 回退、冻结旧 profile、防索引 manifest 漂移 |
| Rust | 材料/会话路由 7 项集成 PASS；Core release 构建 PASS | 失败/取消/重开/身份绑定；不等于完整真实模型质量验收 |
| Ruff | 新增问题 0，继承问题 89 | 仅本轮变更差额 PASS；不宣称仓库全量 Ruff 干净 |
| 多格式 | DOCX/XLSX/PPTX/PDF 实际 Core/worker 4 格式，以及轻格式两波 25 案例 | INTEGRATED，自编材料；不是全格式高保真往返或原应用编辑资格 |
| 原生 | 无模型闭环、模型配置、记忆工程旅程有各自本地通过收据 | 真实模型完整原生旅程仍 FAIL/PARTIAL；4B 空最终答案/503 和 27B 重测失败原样保留 |

默认本地产品运行时收敛到 **LM Studio / `http://127.0.0.1:1234/v1`**，自动路径不再探测/回退 Ollama。
Core 默认计划、文本/视觉 worker、UI 新 profile、启动检查、检索评估与公共探针均同步；显式历史协议兼容仍保留。
资源索引绑定能力 manifest 的 SHA-256；31 项声明各保留自身资格，实际 embedding 返回 1024 维，rerank 未执行及旧 desktop 路径不可用不计 PASS。
模型库存查询看到 6 个 ID；库存、真实推理、具体 GGUF 身份和质量互不代替。
附带静态复核发现：诊断输入接受 IPv6 loopback `[::1]`，但原生 CSP 当前只许可 `127.0.0.1`；
该手动配置分支仍 UNVERIFIED，不影响本轮实际使用的 IPv4 LM Studio 默认地址，不能宣称所有自定义端点已资格。

`.project-local/rt` 和本轮 candidate 的授权组件已完成备份、替换、逐文件回读；新候选包含 **19,524** 个校验成员。
旧 88 文件/40,059,912 字节保存在 `.project-local/archives/runtime-migration-20261018/pre-promotion-components.zip`，
ZIP 12,895,781 字节、展开校验 PASS；87 个旧路径被更新，新增 1 文件，旧候选资格清单归档后删除并重建。
组件净减 273,742 字节，计入该组件归档后净增加 12,622,039 字节；不把保全操作写成磁盘释放。
data、保留 Python 依赖、共享模型、Green 与独立 QODER 检出均未迁移。p3 五个资源残片归属证据不足而保留，历史六 runtime 路径现场缺失，本轮删除数为 0。

完成替换后，本轮新建的第三套临时 stage 已逐成员与候选比对并退出：删除 19,523 文件/645,768,541 字节，
仅移除 2,284 个已空目录；保存 manifest 和删除清单占 9,131,668 字节，净逻辑回收 636,636,873 字节。
这属于本轮临时重复副本清理，不计作旧六套 runtime 回收。清单在
`.project-local/archives/runtime-migration-20261018/retired-current-stage/`，实际候选及 `.rt` 保留完整。

五份根旧交接/摘要已迁入 [历史交接归档](../history/handoff-archive-20261018/README.md)，旧 profile 和迁移前当前交接全文在
[运行时历史归档](../history/runtime-migration-20261018/README.md)。原字节、SHA-256、旧路径、替代入口均登记，路由与目录权属同步。
没有确认可无证据删除的其他历史文件；清理保留可追溯性，不把历史正文中的原路径改成现行指令。

仍未闭合：完整 Cowork 逐字正文、全应用辅助技术与全部视觉验收、FE24 当前安装五旅程、FE25 当前产品宣传资产、
全格式往返、完整真实模型学习闭环、逐 donor 许可/操作资格、exact-SHA CI 与 Owner 接受。
当前结论仍 **PARTIAL**，不据局部门禁通过宣称全项目 COMPLETE。

## 2026-10-18 后继模型与小栖接入

[本地LLM入口](AAOS-LOCAL-LLM-20261018.md)和[当前推理收据](receipts/AAOS-LOCAL-LLM-20261018.json)收敛了历史临时方案与现行配置。27B MTP有效参数与非零草稿接受统计已读回，当前正式Python worker同实例合成材料30.07秒、stop/content/未截断；这更新了“只有库存，没有推理证据”的现况。它不覆盖旧失败、完整Core/原生/已安装学习闭环或Owner接受。旧27B原生失败按详细日志定位在首答超时、尚未开始复测；旧探针汇总中的“retest unverified”不是阶段定位证据。

小栖源与云端3115378b已核一致，Owner改变独立开发决定。当前正式前端已吸收九态静帧和来源/许可索引，并在现有ConversationPanel按真实请求/终态呈现；没有第二模型代理或记忆库。取消申请保持等待终态；合法UNKNOWN和丢失响应另行保留原请求、查询原身份，不再显示尚未提交的“等待确认”。源仓库及远端保全，三槽位共享状态、人物完整设置与语音/动画仍未完成。

本段新增源代码尚未推广至旧原生候选；最新Vite产物不是已安装产品。新增资产保留32,751,479原始字节，未为减体积擅自更改原图；逐文件hash在frontend/src/companion/PROVENANCE.json。原生构建、相同源完整学习旅程和Owner验收继续为PARTIAL。

