# OSS 复用与模板交接 · 2026-10-08

状态 **PARTIAL**：范围内已交付可运行代码、全池去向和结果验证；native 桌面、在线服务、音频模型、全平台兼容仍未取得结果证据。不要将这张交接卡当作 Local Green 或发布证书。

## 基线、权威与隔离

实际已提交基线 `4b9828c4058901c0b1fd2c75c528238c55e0ec89`，独立分支 `codex/oss-reuse-templates-20261008`。选的是本地当前 `origin/main` 已提交状态；SHA 与历史对照相同，不是为了回退版本。工作目录 `D:\All projects\ArcheAxis-Knowledge-OS\.project-local\worktrees\oss-reuse-20261008`；任务环境和缓存 `D:\All projects\ArcheAxis-Knowledge-OS\.project-local\artifacts\oss-reuse-20261008`，运行回执在 `.project-local/runs/c3b20e76da/<run-id>/artifacts/execution.json`。

原目录开始处于 `codex/Audit` / `1a981a4482b01f31989074e79c82a63400aa07a7`，有未跟踪历史目录和其他测试，未进行修改、切换、清理、stash 或合并。当前有效权威读取自隔离基线：AUTHORITY.md、PROJECT_CONTRACT.yaml、DECISION_SUPERSESSION_LEDGER.yaml SUP-022，以及 `docs/authority/taskpack-1004-aaos01/01_完整执行任务书.md`。旧 AGENTS 中 Avalonia 正式桌面叙述与当前权威冲突，按 SUP-022 保留为历史供体，不恢复为主线。

在 docs/current 和任务 intake 等项目记录中未找到可核对的 Qoder 正在修改文件清单，所有权 **UNKNOWN**。这是独立候选提交，不自动整合。用户已明确允许本任务 worktree 的正常平台审批；仅用于隔离 Git/测试，不改 ACL、全局 Agent 配置、全局 Python/Node 或共享运行状态。未安装 WSL，也未访问 E/F 或真实用户知识库。

## 全池与证据

`OSS-REUSE-CROSSWALK-20261008.json` / 同名 CSV 保留 **691 条来源行**：369 历史池、101 registry、101 absorption ledger、51 当前供应链、11 当前 capability registry、58 处置文档存档行。每行保留原始 ID/name/record/path/行号，来源文件 SHA256，显式别名依据、去向、价值、延后理由、重启条件。重复 MinerU 等未静默覆盖；池外 API/格式/运行时原记录也保留。无 v0.2 规格包可用，因此从仓库重建，不把旧初筛当通过证书。

369 池当前为 **A=2、B=13、C=2、D=351、E=1**。A 是 Trafilatura 和 Tesseract，仅表示本任务环境中经过 Core 产品 API 得到正确结果。PyMuPDF、py-fsrs 等在池外相关记录中另有结果证据，不能拿重复来源行当新增供体数量。旧 13/62/294 初筛数字不再强行保留；没有具体提炼结果的旧 reference 保守退到 D。D 每行写明能补的能力、当前未有需求/资格证据的原因和重新评估触发，不代表安装或已吸收。

具体参考成果见 `OSS-REFERENCE-EXTRACTIONS-20261008.md`：JSON Canvas 的节点/边/文件引用、JSON Schema 的明确版本与有限字段验证、OpenAPI 的有限业务动作及运行结果区分，均有本项目映射和样例。大图服务、完整 RAG 产品、多 Agent、训练、多推理栈、复杂仿真/协作仍是未来条件，不阻塞三模板。

短复用卡见 `OSS-REUSE-CARDS-20261008.md`，固定版本、入口、输入输出、样例、失败替代及代码/权重许可分开记录。不能确认的分发许可/权重来源链明确标缺口。此任务不升级生产依赖或 lockfile；任务 venv 为固定直接版本的隔离测试环境，不能冒充完整 uv sync。

## 修改和调用入口

1. `services/python-workers/web/worker_html.py`：现有 `html.structure` route 加入已锁定 Trafilatura 2.1.0，仅处理显式 article/main；缺依赖、空输出、异常或普通 fragment 使用现有 stdlib fallback。保留 title/links 和来源 SHA；损失收据记录 engine/version/attempt/fallback。没有下载、脚本执行或正式数据库写入。
2. `frontend/src/templates/{disciplines.ts,bindings.ts,TemplateWorkspace.tsx}`：28 个独立学科配置记录共用 T1/T2/T3；只增加字段、关系、活动、评价及代表样例。模板在既有 Document 根 attrs 下保存，调用 `documents_list`、`document_create/get/version/draft`、`learning_state` 等有限 Core 命令。引用绑定真实 ID、不可变版本与可选块。反向引用含源对象上下文，图谱关系按钮打开真实对象，画布卡片保存引用/坐标，集合统计从当前对象派生；最多读取 100 文档并明确显示范围，不增加图服务/正式存储。
3. `frontend/src/components/DocumentEditor.tsx`：Tiptap 根属性往返保留模板 attrs，正文编辑不丢模板元数据。
4. `frontend/src/spaces/CanonicalLibrarySpace.tsx`：资料库接入折叠模板工作区，沿用真实文档打开与 app dirty 关闭保护；另有属性保存、版本冲突与关闭放弃确认。
5. `frontend/src/spaces/CanonicalLearningSpace.tsx`：增加可选 initialItemKey；T3 保存绑定后沿用现有作答/反馈/复习 UI 和 Core 保存，不复制学习引擎或状态库。course.general worker 仅源级有限合同测试，缺模板 native bridge 的部分仍 B，28 标签不宣称专属课程完成。
6. `docs/truth/SUPPLY_CHAIN_LEDGER.json`：C001 PDF.js 仍在当前前端；C002 MarkItDown 真实 legacy 函数与 txt/md 占位区分；C003 Trafilatura 精确锁版和许可哈希；A015 fsrs 独立调用路径和真实学习结果。旧记录在各行 history.original_record 保留，任务资格与安装/release 分开。
7. `docs/current/AAOS-OSS-DONOR-DISPOSITION-V2-20261002.json`：只追加当前证据 overlay；原 frame、47+11 存档及原未完成声明均保留为历史。
8. `scripts/audit/build_oss_reuse_inventory.py`：生成证据表，不是调度系统；无显式实测证据不能升 A，无具体提炼成果不能升 C，别名冲突拒绝。
9. 新测试：`crates/archeaxis-api/tests/oss_template_reuse.rs`、`tests/workers/test_html_donor_absorption.py`、`tests/workflow/test_oss_reuse_crosswalk.py`、`frontend/src/__tests__/TemplateBindings.test.tsx`。

## 实测验收与限制

**INTEGRATED**：Core import→job→真实 Python worker→text/structure/loss API→关闭/reopen SQLite/CAS；HTML 正文/噪声、PDF 标记、DOCX 原文、OCR 标记均有具体断言，Canvas 有结构和结果读回。实际 DOCX worker 报告的位置能经原 anchor API 定位。模板字段、关系、坐标通过 document_draft 保存，旧 expected_version 拒绝 409，重开对象相同。学习 11 测试验证 FSRS 真调用、作答重启读回和相同 event ID 写一次。已有 ask/vault-links 14 测试验证本地有据引用、无匹配/锚点诚实返回和不持久化派生图。全部正式写入由 Rust Core 执行，worker 只处理 staged 输入并回传派生物；没有另建知识库。

**SYNTHETIC / SIMULATED**：Python 66 项既有 worker/合同/台账测试通过；HTML/交叉表/台账定向 23 项通过，其中与前述套件有重叠，不相加成独立能力数。前端 44 项通过，模板追加关闭/损坏元数据两项后单独 8 项通过，共 46 个不同前端测试；前端是 jsdom finite-host mock，真实持久化由独立 Core 测试证明。changed-file Ruff、TypeScript 与 Vite 生产构建通过。每个运行范围和回执哈希见 `OSS-REUSE-VERIFICATION-20261008.json`。

安装过程：npm ci 在任务目录中因下载长时间无进展取消；剩余 PDF.js 6.4.299 官方归档与 lock SHA512 一致后仅补齐任务 node_modules，构建通过，不声称 npm-ci 安装回执通过。Windows launcher 首次 GBK 打印失败，用本进程 PYTHONUTF8 修复输出重跑；失败回执保留，未计 PASS。Rust 使用已有工具链和 Windows SDK 10.0.28000.0 的任务进程变量，没有更改全局环境。

**NOT_RUN**：Tauri native bridge/安装态桌面与 PDF 实际显示、Windows installer、macOS/Linux、音频/embedding 模型、在线 Crossref/DataCite/OpenAlex/Wikidata、全平台/版本/功能/导入导出方向矩阵、exact-SHA CI/release。PPTX/XLSX/XLS/DOC 非本轮代表 DOCX 的完整资格，不能因 DOCX 成功扩大声明。Tesseract eng 样例不证明中文或多语言准确率。复习间隔不等于实操掌握。模板层引用是 Document 版本/块引用；导入来源的 source anchor 操作沿用资料库现有入口，不把派生文本偏移当原文 DOM。

## 给 Qoder 的整合顺序和冲突处理

先核对 Qoder 的当前 write set 与有效 HEAD，保留其未提交内容。建议顺序：独立审计/证据与 worker 变更 → 新模板目录/测试 → 三个现有前端文件的最小接线 → 定向测试及 ledger 证据重生成。不会自动合并主线。

必须串行核对的交叉文件是 `DocumentEditor.tsx`、`CanonicalLibrarySpace.tsx`、`CanonicalLearningSpace.tsx`；若 Qoder 正在改这些文件，先吸收新增模板代码与 worker，再手工应用任务产物中的 `frontend-integration.patch`。它只包含根 attrs 保留、模板 launcher/dirty 接线、可选 learning item 初始绑定，不含重构或依赖变化。供应链台账和处置 JSON 若也有并行更新，按 ID 合并历史与 current verification 字段，再重跑交叉表生成，不覆盖新行。

提交与完整 format-patch 保存在任务独立分支/产物目录。整合后回归：新 Core reuse + structure anchor，learning state/event，ask/vault links，Python HTML/交叉表/台账，前端模板/editor/library/PDF/learning；再做该平台实际 Tauri 入口的闭环。没有资格证据的项目维持 B/D，不能将本地源级 PASS 升成安装或 release PASS。回退为独立提交的普通 revert，不触及 Qoder 原工作区或历史重写。
