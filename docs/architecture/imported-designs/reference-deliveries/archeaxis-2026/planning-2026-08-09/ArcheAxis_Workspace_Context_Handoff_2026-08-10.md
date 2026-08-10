# ArcheAxis Workspace / 元枢工作台

## 新对话交接摘要

更新时间：2026-08-10
当前执行者：Codex  互联网/云端事实必须重新核验；本摘要是决策交接，不替代最新仓库事实。

## 1. 唯一产品定位

**元枢工作台 / ArcheAxis Workspace** 是面向个人与 AI 的本地优先、证据驱动、开放兼容的人机双向学习与知识工作台。

固定短句：**同一份可信知识，人学得更深，AI 用得更准。**

它把真实文件、现有知识库和经核验的开放资料，在保留原件、来源、版本和转换损失的前提下，转化为：

- 人类学习资产：理解、练习、记忆、复习、迁移、教学和项目输出；
- AI 学习资产：Memory、Rule、Skill、Standard、Context、Eval。

人和 AI 都只能提出 Candidate/Proposal；经过来源校验、评估、人工授权后，才能成为正式知识或正式 AI 资产。

“人类深度学习”指理解、迁移、练习、记忆和元认知，不是模型训练意义上的 Deep Learning。项目不是 Cognitive OS、Agent OS、通用 Agent 平台或 Runtime 控制台。

## 2. 名称与身份

- 对外品牌：`ArcheAxis` / `元枢`
- 唯一产品名：`ArcheAxis Workspace` / `元枢工作台`
- 当前仓库技术 ID：`DTALEX66/Cognitive-Loop-OS`，仅作历史/兼容身份
- 未来目标仓库名：`DTALEX66/ArcheAxis-Workspace`，需独立迁移任务，不能盲改
- 旧名称 `Cognitive-Loop-OS`、`Cognitive OS`、`认知闭环系统`、`ArcheAxis OS` 等只能出现在历史、别名、迁移文档
- 不得把 WORK-LAB、HERMES、OpenHuman、Obsidian 变成产品名或内部一级模块名

## 3. 最小闭环与路线

### 生存闭环（立即）

修复 v0.5 安装版真实 PDF 流程：安装 → 上传 PDF → 转换/解析 → 页面/块/来源锚点 → 阅读/展示 → 重启回读。不得用“测试通过、Pillow 元数据或 FFprobe 元数据”冒充 PDF/OCR/ASR 能力。

### 产品最小闭环（C4 目标）

选择真实来源 → 保存 RawAsset → 可解释转换 → DerivedDocument/Block + LossReport + EvidenceAnchor → 中央阅读/编辑 → 搜索/链接/反链/引用 → 重启回读 → 开放导出/往返/冲突恢复。

第一高保真互操作纵切：Obsidian Markdown、Properties、链接/反链、附件、JSON Canvas、增量变更、expected-hash、原子写、备份、冲突、回滚；不是逐像素复制，也不是私有插件全部兼容。

### Horizon

- H0：Truth reset、PDF真实资格、Windows构建底座、门禁提速
- H1：RawAsset/ConversionRun/DerivedBlock/LossReport/EvidenceAnchor、PDF阅读/批注/重启
- H2：DOCX/PPTX/XLSX/CSV、图片 OCR、HTML、批量导入
- H3：Vault/Markdown/Properties/Links/Backlinks/Attachments/JSON Canvas，增量与安全往返
- H4：引用 AI、多文档比较、笔记/批注→卡片、FSRS/Anki 最小交换、人类学习证明切片
- H5：稳定性、大库、无障碍、低配降级、升级/迁移/卸载、开放导出
- H6：Research/Knowledge Production、适配器、课程/项目、Visual Teaching、课件
- H7：完整学习方法、动画、交互模拟、2.5D 空间记忆与学习效果评估
- H8：受控 3D/VR/AR 原型、加密同步/多设备、一个低风险执行适配器研究
- H9：SDK、签名扩展、发布/社区能力
- H10：通用 Agent/自治演化仅探索，不回流产品中心

学习体验与知识表征层（LER）是永久正式产品层：表格、卡片、对比、时间线、学习地图、Canvas、Graph、课件、动画、交互演示、模拟实验、2D/2.5D/3D/VR/AR 都保留在蓝图中。高级形态按 Horizon 和学习效果证据分期；没有证据时只能声明 prototype/experimental，不得宣称提升学习效果。

## 4. UI/IA

苹果风格、浅色/深色、中央宽主工作区、多标签、左右按需上下文、底部仅在任务运行/失败时出现活动条。参考 OpenHuman 的布局思想，不复制 GPL 源码；中央承载 PDF、Markdown、Office、Canvas、表格、课程和 AI 资产编辑，不以聊天或 Agent 为中心。

固定一级空间：

1. Workspace：继续工作、最近内容、当前课程/项目、待处理
2. Library：Files/Vaults/Sources/Collections/Import Center/Reader/Editor
3. Evidence：Claim、来源并排、Anchor、引用、冲突、Review/Diff
4. Learning：目标、路径、练习、复习、掌握、错因、Teach Back、Transfer、Project
5. AI Assets：Memory/Rule/Skill/Standard/Context/Eval 候选、审阅、评估、撤销
6. Settings：Provider、Adapter、权限、存储/备份/同步、无障碍、诊断

不恢复 Agents、Runtime、Machine、Evolution、WORK-LAB、HERMES 作为一级导航。

## 5. 架构与技术职责

- Python/FastAPI：导入、格式转换、证据、知识、学习、AI 资产、API、评估
- SQLite WAL/FTS/可选向量：本地数据、索引、版本、Outbox、回滚
- Rust/Tauri：桌面壳、进程、窗口、安装器生命周期
- TypeScript/JavaScript：阅读器、编辑器、表格、Canvas、Graph、动画和 3D 渲染
- PowerShell 7：Windows 环境发现、MSVC/SDK/进程/端口/安装器编排；复杂规则留在 Python

不做不必要的语言重写。依赖版本以当前锁文件和经过验证的工具链为准，不在规划中硬编码过时版本；需有替换方案和能力探针。

Windows 必须有 doctor/bootstrap/build/clean 与 dev/test/bundle profiles，隔离源码、构建缓存、应用数据和测试临时目录；记录 commit/tree、dirty 状态、工具链/锁文件摘要、命令、产物哈希和测试结论。ambient Python、全局 npm、偶然 PATH、固定端口、个人 Vault 都不得进入 Release 证据。

## 6. 开源吸收规则

当前为个人学习研究项目，**非商业不等于许可证豁免**。符合许可证和工程规范的项目可以优先吸收，并允许以后用自研实现替换。

复用阶梯：开放格式 → 成熟依赖 → SDK/API/CLI → sidecar → 许可兼容 fork/vendor → 行为/fixture 参考 → 自研。

每项必须记录 exact revision、许可证、模型/数据/字体/图标/资产许可、集成方式、公开源码/二进制资格、NOTICE/SBOM、fixture、升级和回滚策略。闭源项目只能做公开格式/API/行为兼容。GPL/AGPL 不能因个人项目自动忽略边界。

候选方向：PDF.js、MarkItDown、Docling（许可另审）、Tesseract/PaddleOCR、Tika sidecar、Trafilatura、Markdown/YAML AST、CodeMirror 类编辑器、py-fsrs；Obsidian 公共 Markdown/JSON Canvas；Zotero/BibTeX/CSL、Anki、Joplin、Logseq、SiYuan、Readwise 等开放格式/API。OpenHuman 仅做洁净 UX 参考。

## 7. 证据与数据规则

RawAsset → SourceRecord → ExtractedClaim → EvidenceCandidate → CrossValidationRecord → CorroboratedEvidence → VerifiedKnowledge。

用户文件只能证明文件内容；AI 输出不能作为外部事实的独立佐证，只能作为 GeneratedArtifact、软件行为证据或 Candidate。医疗/法律/财务等高风险内容需要权威来源、独立佐证和人工复核。真实 Vault 默认只读；写入必须 approved root、expected-hash、原子写、backup、冲突检测和 rollback。

核心对象包括 RawAsset、ImportBatch、ConversionRun、DerivedDocument/Block、EvidenceAnchor、Annotation、LossReport、IndexRevision、KnowledgeUnit/Version、LearningAsset、AI Asset Revision、TransformationProposal、ReviewDecision、EvaluationCase/Result。

## 8. CI/Release 原则

- 普通 PR：主 Python 兼容版本 + 受影响测试 + lint
- UI：增加 browser smoke
- Windows runtime：增加 Windows smoke
- Desktop/Tauri/Installer：增加 desktop-shell
- 依赖/兼容接口/解析器：Python 兼容矩阵 + installed-format/wheel
- nightly/RC：完整矩阵
- main 合并后：同 tree、workflow/policy/lock 和可信证据一致时，允许轻量 SHA 绑定；不一致或未知自动 full
- 正式 Release：exact-SHA full qualification、安装器、资产、下载哈希回读

不能把同 SHA 的任意成功 CI 当完整 Release 证据。desktop lifecycle 已知可能 flaky，稳定性未解决前不能盲目省略关键复验。CI 不得重复执行自己的政策；测试数量和 Job/Receipt 数不等于产品进度。

## 9. 当前主任务包

当前唯一主任务包：`ArcheAxis_Workspace_Final_Master_TaskPack_v4_2026-08-09.md`。

本地文件曾绑定 SHA-256：`33b81a111204000318238001a28bc5d7cc024d153e119c8463aa109be424a241`。

旧 v3、旧 Incremental、Future Blueprint v1、旧 UI/云端审计、HERMES 任务包均为历史输入，不可作为当前执行权威；需从最新仓库重新核对是否已落地。能力状态必须分开记录：technical_state、learning_evidence_state、interop_state、release_state、license_state。

## 10. 新对话第一步

1. 读取本摘要和 v4 主任务包。
2. 重新获取云端 `main` 的 commit/tree、当前分支、PR、CI、Release 和安装版事实；旧审计仅作证据。
3. 读取仓库 `docs/truth/**`；若不存在，先建立 Product Truth、Naming、Authority、Evidence、Capability Atlas。
4. 先做 v0.5.1 PDF 安装后真实用户流，不先扩展 3D/Agent/重型蓝图。
5. 所有任务绑定 Horizon、Capability ID、用户动作和可回读证据；一包一分支一 PR，失败只重跑受影响门禁。

## 11. 明确排除与防漂移

- 不把 WORK-LAB 作为 OS 产品依赖、路线、UI、命名或权威；它只能是外部可选验证消费方。
- 不把 HERMES 写成当前唯一执行者；用户已明确 Codex 接替执行责任。
- 不把 Obsidian 兼容误写成已完成；当前目标是分期达到 C4。
- 不因当前未实现就从长期蓝图删除 Research、Knowledge Production、完整学习方法、课程/项目、Visual Teaching、动画、模拟、Spatial Memory、3D/VR/AR、同步/发布等能力。
- 不把长期能力提前塞进当前 Release；不允许“全蓝图”反向阻塞 PDF 最小闭环。
- 不扫描个人 Vault、E 盘或其他项目目录；不执行 reset、force-push 或未授权远端重命名。
