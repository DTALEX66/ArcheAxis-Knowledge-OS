# ArcheAxis OS Frozen Execution Baseline v1

> 基线 ID：`AXW-FROZEN-v1-2026-08-09`
>
> 状态：`FROZEN`
>
> 建立基点：`DTALEX66/Cognitive-Loop-OS`，`origin/main` = `492fac5982c693eb668d31cc51a6a59bac83b7a1`
>
> 性质：固定的后续任务定义与对照基线，不是当前能力、完成度或发布日期声明。

## 1. 冻结合同

本文件固定任务 ID、目标、依赖、边界和验收标准。后续执行只可在 [`EXECUTION_STATUS_LOG.md`](EXECUTION_STATUS_LOG.md) 追加状态和证据，不得修改本文件以使结果看起来符合计划。

如果现实证明某项任务需要调整，保留原任务并在状态日志中追加：

- `DEVIATION`：实现路径变化，但原目标仍有效；
- `BLOCKED`：存在可复现阻塞；
- `SUPERSEDED_PROPOSAL`：建议由新版本基线取代，但未获批准；
- `CHANGE_PROPOSAL`：建议新增任务，不自动进入本基线。

只有项目所有者明确批准时，才能新增 `v2` 文件。v1 永久保留。

## 2. 产品目标与边界

ArcheAxis OS 是本地优先、证据驱动、开放互操作的人类—AI 学习与知识工作区。目标闭环是：

```text
开放格式原件 → 可追溯派生内容 → Claim / Evidence → 人类学习
→ 审批后的 AI Assets → 引用式 AI 使用 → Evaluation / Lesson
→ 经审核的知识更新
```

固定边界：

1. 首个高保真纵向切片是 Obsidian Vault / Markdown / JSON Canvas。
2. 先复用合法依赖、SDK/API/CLI、fork/vendor、Adapter 或 sidecar；确无可复用方案时才自研。
3. Python 负责领域模型、转换、证据、学习和 AI；Rust/Tauri 负责桌面外壳和 Windows 生命周期；TypeScript/JavaScript 负责 UI；PowerShell 7 只做薄型 doctor/build/test/installer wrapper。
4. 不进行 Python 到 Rust 的整体重写。
5. Windows 发布资格必须在原生 Windows 安装态验证；WSL 不能替代。
6. 不访问 `E:\`。不读取、复制或输出凭据、`.env`、认证存储、私钥、浏览器数据或 token。
7. `Obsidian-Assistance` 已审计吸收，永久排除后续扫描、测试、修改和迁移。
8. 临时数据、下载、缓存、证据和执行状态留在仓库忽略的 `.hermes/`。
9. 一个 checkout 只有一个 writer；并行写入必须使用不同 branch/worktree。
10. H6–H10 在所有者显式激活前只是 Parking Lot。

## 3. 统一完成定义

任何任务只有满足其风险等级对应的全部条件才可标记 `PASS`：

1. 已读取适用规则、现有实现、调用点、manifest 和相邻测试。
2. 未覆盖未知脏改动；改动保持最小且可回滚。
3. 新行为或缺陷修复完成唯一可解释的 RED → GREEN。
4. 运行受影响测试、diff check、convention 和必要 Ruff/架构门禁。
5. 依赖、打包、安全、迁移、数据库和 Windows 生命周期变更完成独立 frozen-tree 审查与完整门禁。
6. 需要云端证明时，CI 必须对应交付的精确 SHA；失败、取消、缺失或 required-but-skipped 均不是通过。
7. 需要发布态证明时，必须验证实际 wheel/bundle/installer，而不是源码、fixture 或版本字符串。
8. 记录失败语义、回滚方法、许可证和数据边界。
9. 状态日志追加 exact SHA、命令、CI URL 或实际运行证据；不得回写本任务定义。

证据等级固定为：`STRUCTURAL`、`LOCAL_RUNTIME`、`EXACT_SHA_CI`、`PUBLICATION`、`LIVE_INSTALLED`。低等级证据不得替代高等级证据。

## 4. H0 — v0.5.1 可信恢复

| ID | 固定任务 | 依赖 | 冻结验收标准 |
| --- | --- | --- | --- |
| `AXW-BASE-0` | 冻结仓库基线与工作归属 | 无 | 记录 Git root、branch、HEAD、origin/main、分叉、脏路径与 owner；从最新云端 main 建隔离工作树；未知改动零覆盖 |
| `AXW-001A` | Current State Truth | `AXW-BASE-0` | 建立当前能力、限制和证据等级的单一入口；规划与实现事实明确分开 |
| `AXW-001B` | Authority Contract | `AXW-BASE-0` | 固定规则权威顺序；历史蓝图仅作迁移输入，不能覆盖 AGENTS 或当前用户指令 |
| `AXW-003A` | CI gate identity 修复 | `AXW-BASE-0` | GatePlan ID 与实际 job/aggregator 一致；任一 required job 失败时总门禁失败；有反向回归测试 |
| `AXW-003B` | Exact-SHA qualification attestation | `AXW-003A` | CI 保存 GatePlan、风险分类、运行矩阵与结果 artifact；Release 只接受同 SHA 的完整资格证明 |
| `AXW-003C` | 依赖与格式影响分类 | `AXW-003A` | `pyproject.toml`、requirements、lock、parser、bundle 配置变化触发相应格式、wheel 和安装态门禁；以路径变异测试证明 |
| `AXW-004A` | Evidence Index | `AXW-001A`, `AXW-003B` | 稳定记录任务、提交、测试、CI、bundle、installer 和 live readback 的证据关系，不复制易过期日志 |
| `AXW-004B` | Version/Release truth projection | `AXW-009B`, `AXW-010B` | UI、manifest、文档与发布元数据只显示经验证的同一版本和能力 |
| `AXW-004C` | Append-only status protocol | `AXW-004A` | 状态更新只追加；历史 PASS、FAIL、BLOCKED、DEVIATION 不被静默改写 |
| `AXW-006A` | Upstream ledger 最小合同 | `AXW-BASE-0` | 每个实际候选具有 source URL、revision、license、integration mode、owner 和状态；registry 不等于已集成 |
| `AXW-006B` | 实际 bundle SBOM/RDR | `AXW-006A`, `AXW-009C` | 对真实 payload 生成依赖、版本、来源 revision、许可证和 SPDX/CycloneDX SBOM；不以候选总数阻塞 |
| `AXW-006C` | NOTICE 与 payload 审计 | `AXW-006B` | `THIRD_PARTY_NOTICES` 与实际打包内容一致；禁止缺失许可证、不可追溯二进制和未声明 vendor 代码 |
| `AXW-007A` | Windows/PowerShell 7 doctor | `AXW-BASE-0` | 检测 Python、Node、Rust、PowerShell、中文/空格路径、端口、编码和可写目录；输出不含秘密或私人正文 |
| `AXW-007B` | Windows 生命周期诊断 | `AXW-007A` | 可复现启动、loopback/token、Job Object、关闭、残留进程和端口冲突；仅在证据出现时修 Rust 窄缺陷 |
| `AXW-009B` | 统一版本身份 | `AXW-BASE-0` | 源码、wheel、Tauri、安装器、release manifest 和 UI 版本一致；仓库身份保持 `DTALEX66/Cognitive-Loop-OS` |
| `AXW-011A` | 真实 PDF corpus 与 Oracle | `AXW-BASE-0` | 覆盖文本、中英文、多页、加密、扫描和损坏 PDF；样本有许可、来源、SHA 和语义预期；禁止文本伪装 PDF |
| `AXW-012A` | RawAsset-first 最小实现 | `AXW-BASE-0` | 原件先不可变保存并哈希，再转换；转换失败仍保留原件和失败记录；故障注入证明无原件丢失 |
| `AXW-012B` | PDF 提取修复 | `AXW-011A`, `AXW-012A`, `AXW-003C` | 从新 main 重建最小 PDF 修复；H0 默认只引入 PDF 所需 extra；requirements/lock/tests 同步；真实语义 Oracle 通过 |
| `AXW-010A` | Runtime capability probe | `AXW-003B`, `AXW-003C`, `AXW-007A`, `AXW-012B` | 分别报告 availability、extraction quality、evidence fidelity；在实际目标环境运行，不能只检查 import/spec |
| `AXW-009C` | Exact-tree clean bundle | `AXW-009B`, `AXW-010A` | 从干净 exact SHA 构建；包内引擎、资源、版本和哈希可复现；构建状态只写项目本地忽略目录 |
| `AXW-012C` | Windows 安装态真实 PDF 流程 | `AXW-009C`, `AXW-011A`, `AXW-012A` | 安装后完成导入、原件保存、派生文本、页级证据、重启和重开；验证失败路径与恢复 |
| `AXW-009D` | Installer 生命周期 | `AXW-009C`, `AXW-007B` | 验证全新安装、启动、正常关闭、升级、重启、卸载、用户数据保留和必要回滚；不以单次 PE 启动代替 |
| `AXW-010B` | Capability truth projection | `AXW-010A`, `AXW-012C` | 仅把已验证能力投影到 Truth、UI 和 release；不支持/降级/失败均明确显示 |
| `AXW-H0-EXIT` | v0.5.1 发布裁决 | `AXW-003B`, `AXW-003C`, `AXW-004B`, `AXW-004C`, `AXW-006C`, `AXW-009D`, `AXW-010B`, `AXW-012C` | 同一精确 SHA 的 CI、干净 bundle、安装态 PDF、Windows 生命周期和供应链证据全部 PASS；否则 NO-GO |

## 5. H1 — RawAsset、Evidence 与早期学习闭环

| ID | 固定任务 | 依赖 | 冻结验收标准 |
| --- | --- | --- | --- |
| `GOV-001` | Machine Knowledge fail-close | `AXW-H0-EXIT` | 统一两套生命周期；旧写入不能直接 active；AI 检索只使用 approved、未撤销且 scope 匹配的资产 |
| `AXW-020R` | 现有对象复用与迁移矩阵 | `AXW-H0-EXIT` | 映射 SourceRecord、Claim、Evidence、LearningArtifact、MasterySignal、Job、Outbox、Receipt；禁止平行重建 |
| `AXW-020A` | 完整 RawAsset 合同 | `AXW-020R`, `AXW-012A` | 来源、哈希、MIME、大小、保存状态、保留策略和不可变语义稳定；兼容最小 H0 数据 |
| `AXW-020B` | Import/Conversion/Derived 合同 | `AXW-020A` | ImportBatch/Item、ConversionRun、DerivedDocument/Block、LossReport 建立稳定 ID、版本和关系 |
| `AXW-020C` | EvidenceAnchor/IndexRevision | `AXW-020B` | 锚点支持页、块、字符/区域和源版本；索引可重建且不能冒充事实源 |
| `AXW-021A` | 持久导入 Job/Outbox | `AXW-020B` | 复用现有 Job/Outbox/Receipt；业务状态与 outbox 同事务；长任务可观察 |
| `AXW-021B` | 幂等、重试、取消与恢复 | `AXW-021A` | command/idempotency/revision、lease、checkpoint、retry、pause/cancel 和崩溃恢复有故障测试 |
| `AXW-022A` | PDF.js 阅读器 | `AXW-020B`, `AXW-H0-EXIT` | 本地 PDF 可分页、缩放、搜索和重开；原件不经过不必要上传 |
| `AXW-022B` | 阅读器证据与批注 | `AXW-022A`, `AXW-020C` | 文本/区域选择生成稳定锚点，能从 Claim/Evidence 回跳；源修订变化有失效语义 |
| `AXW-024A` | Claim/Evidence 核心图 | `AXW-020C` | 一条 Claim 可关联多 Evidence；来源、生成方式、审核、scope 与 provenance 可追溯 |
| `AXW-024B` | CrossValidation/EvidenceBundle | `AXW-024A` | 支持 supports/refutes/qualifies、跨来源比较、冲突、置信依据和人工审核 |
| `AXW-025A` | 学习目标与检索练习 | `AXW-024A` | 支持目标、前测、练习、回答与评分依据；不把模型置信度当学习准确率 |
| `AXW-025B` | Teach-Back 与迁移证据 | `AXW-025A` | 支持延迟回忆、迁移题、Teach-Back 和人类 truth/prediction 对；结果可追溯到来源 |
| `AXW-030A` | 稳定 Workspace DTO/API | `AXW-020C`, `AXW-024B`, `AXW-025B` | 前端通过版本化 API/DTO 访问，不直接读取 SQLite；错误和降级合同明确 |
| `AXW-030B` | Canonical Shell 与 IA | `AXW-030A` | 导航围绕资料、知识、证据、学习、AI Assets 和系统状态；旧 Runtime/Evolution 入口不主导产品 IA |
| `AXW-030C` | Truth 驱动 UI 投影 | `AXW-030B`, `AXW-010B` | UI 状态由实际能力、对象和证据投影；无空壳模块、假完成度或静态成功文案 |
| `AXW-H1-EXIT` | H1 纵向闭环资格 | `GOV-001`, `AXW-021B`, `AXW-022B`, `AXW-024B`, `AXW-025B`, `AXW-030C` | 同一 PDF 形成 RawAsset、派生块、可回跳 Evidence、人类学习记录和受控 AI 候选；安装态重启后仍成立 |

## 6. H2 — 多格式适配

每个格式任务都必须独立完成 fixture/Oracle、Adapter 合同、缺依赖降级、源码测试、实际 bundle 和 Windows 安装态资格验证。不得用一个格式的成功证明另一格式。

| ID | 固定任务 | 依赖 | 冻结验收标准 |
| --- | --- | --- | --- |
| `AXW-023A` | DOCX Adapter | `AXW-H1-EXIT` | 标题、段落、列表、表格、图片引用、批注/缺失语义形成 LossReport，并通过安装态样本 |
| `AXW-023B` | PPTX Adapter | `AXW-H1-EXIT` | 幻灯片顺序、文本、备注、表格和媒体引用可追溯；视觉损失明确报告 |
| `AXW-023C` | XLSX/CSV Adapter | `AXW-H1-EXIT` | sheet/range/cell/formula/value 语义可定位；大表有边界和降级策略 |
| `AXW-023D` | OCR Adapter | `AXW-H1-EXIT` | 扫描 PDF/图片支持语言探测、页/区域锚点、质量指标和不可用 fallback；CPU-only 可运行 |
| `AXW-023E` | HTML/Web Adapter | `AXW-H1-EXIT` | 静态正文优先；URL、抓取时间、许可/robots 边界和引用锚点保留；浏览器只作隔离 fallback |
| `AXW-023F` | 音视频转写 Adapter | `AXW-H1-EXIT` | 转写块具有时间锚点、引擎和语言元数据；无引擎时安全降级，不自动下载模型 |
| `AXW-H2-EXIT` | 多格式资格 | `AXW-023A`, `AXW-023B`, `AXW-023C`, `AXW-023D`, `AXW-023E`, `AXW-023F` | 每个格式都有独立 exact-SHA 与安装态证据；bundle、SBOM 和 NOTICE 与实际能力一致 |

## 7. H3 — Obsidian / Markdown / JSON Canvas C4

| ID | 固定任务 | 依赖 | 冻结验收标准 |
| --- | --- | --- | --- |
| `AXW-040` | C0 Vault 发现与稳定身份 | `AXW-H1-EXIT` | 仅用户批准 root；路径、重命名和内容哈希形成稳定身份；增量扫描可恢复 |
| `AXW-041` | C1 Markdown/YAML/链接语义 | `AXW-040` | CommonMark/Obsidian 扩展、frontmatter、wikilink、embed、tag 和附件引用有独立 parser Oracle |
| `AXW-042` | C2 只读 Workbench | `AXW-041` | 浏览、搜索、反链、附件和引用不写 Vault；索引删除/重建不损失原件 |
| `AXW-044A` | C3 Revision-safe write | `AXW-042` | 所有写入使用 expected revision、临时文件/原子替换、备份和审计；冲突 fail-close |
| `AXW-044B` | 冲突、回滚与恢复 | `AXW-044A` | 外部编辑、并发写、进程中断、非法路径和编码错误均可检测并恢复 |
| `AXW-043A` | JSON Canvas codec | `AXW-041` | 遵循官方 JSON Canvas 规范；未知字段保留；独立 parser 与 round-trip fixture 通过 |
| `AXW-043B` | JSON Canvas 安全写入 | `AXW-043A`, `AXW-044B` | Canvas 写入复用 C3 修订/冲突机制；节点、边、布局和未知字段无静默损失 |
| `AXW-045` | C4 安装态资格 | `AXW-043B` | 真实代表性 Vault 在 Windows 安装态完成扫描、读、搜、改、冲突、回滚与 Obsidian 重开验证 |
| `AXW-H3-EXIT` | Obsidian C4 裁决 | `AXW-045` | C0–C4 证据齐全；排除项目未被访问；不以内部 fixture 单独宣称全面兼容 |

## 8. H4 — 人类学习与 AI 学习双闭环

| ID | 固定任务 | 依赖 | 冻结验收标准 |
| --- | --- | --- | --- |
| `AXW-024C` | Evidence 关系与审查 | `AXW-H1-EXIT` | 证据支持、反驳、限定、重复、冲突和人工裁决均版本化，不静默覆盖 |
| `AXW-024D` | Freshness/Scope/Revoke | `AXW-024C` | 有效时间、适用范围、supersedes、撤销和重新验证可查询，并影响 AI/学习投影 |
| `AXW-050A` | 引用式 AI 回答 | `AXW-024D` | 每个实质结论可回到 EvidenceAnchor；无证据时拒答或明确不确定；不输出伪引用 |
| `AXW-050B` | AI 失败与边界语义 | `AXW-050A` | provider 不可用、上下文不足、冲突证据、过期证据和越权请求均 fail-safe |
| `AXW-051A` | FSRS 调度 | `AXW-H1-EXIT` | 优先复用 py-fsrs；卡片状态可序列化；UTC、due、rating 和参数版本明确 |
| `AXW-051B` | 复习与掌握证据 | `AXW-051A`, `AXW-025B` | due queue、时区、延迟回忆、迁移结果和历史重算可验证；不再使用固定三次高分启发式 |
| `AXW-052A` | Approved-only AI Assets | `GOV-001`, `AXW-024D` | Candidate→Review→Approved→Deprecated/Revoked 状态唯一；检索和 Runtime 只读允许范围 |
| `AXW-052B` | 低风险 Skill/Prompt 资产 | `AXW-052A` | 版本、来源、允许/禁止任务、输入输出合同、回滚和评测齐全；禁止自动激活高风险工具 |
| `AXW-053` | 知识—学习—AI 转换 | `AXW-050B`, `AXW-051B`, `AXW-052B` | 转换产物默认 candidate；来源、模型/工具、版本、loss、审核和 supersedes 可追溯 |
| `AXW-054A` | 对照评测 corpus | `AXW-024D` | 建立带人工 truth/prediction 的多语种、多来源样本；许可、SHA 和隐私边界完整 |
| `AXW-054B` | 比较指标与回归 | `AXW-050B`, `AXW-051B`, `AXW-053`, `AXW-054A` | 报告引用覆盖、正确性、拒答、学习保持、迁移、延迟和资源消耗；指标有置信区间/样本量 |
| `AXW-055` | 单主题全闭环资格 | `AXW-H2-EXIT`, `AXW-H3-EXIT`, `AXW-054B` | 仅做资格验证：一份真实主题从原件、证据、学习、AI Assets 到 Evaluation/Lesson 全程安装态可追溯；不夹带补实现 |
| `AXW-H4-EXIT` | 双闭环裁决 | `AXW-055` | 人和 AI 两条学习链均有真实效果证据、失败语义、撤销和恢复；否则不得进入稳定版声明 |

## 9. H5 — 稳定 v1.0

| ID | 固定任务 | 依赖 | 冻结验收标准 |
| --- | --- | --- | --- |
| `AXW-094A` | 开放交换 manifest/export | `AXW-H4-EXIT` | 原件、派生、证据、学习和 AI Assets 可按开放格式导出；版本、哈希、关系和 loss 明确 |
| `AXW-094B` | 备份、校验与恢复 | `AXW-094A` | 备份可校验、可演练恢复；损坏、部分恢复和版本不兼容有明确失败语义 |
| `AXW-095` | 升级、降级与数据保留 | `AXW-094B` | 跨支持版本升级、失败回滚、卸载重装和用户数据保留在 Windows 安装态验证 |
| `AXW-096A` | 大库与 CPU-only 性能 | `AXW-H4-EXIT` | 使用代表性分层 corpus；给出数据量、硬件、冷/热启动、延迟、内存和降级阈值 |
| `AXW-096B` | 可访问性与键盘流程 | `AXW-H4-EXIT` | 核心导入、阅读、证据、学习和设置支持键盘；语义标签、焦点、对比度和错误反馈通过检查 |
| `AXW-096C` | 长任务与资源恢复 | `AXW-021B`, `AXW-096A` | 大批量导入可暂停、恢复、限流和安全退出；无无限重试、孤儿进程或静默数据损坏 |
| `AXW-097` | 诊断包与隐私 | `AXW-095`, `AXW-096C` | 诊断信息足够定位版本、能力和失败，但不包含秘密、私有正文、绝对私人路径或认证状态 |
| `AXW-060` | v1.0 exact-SHA release qualification | `AXW-006C`, `AXW-095`, `AXW-096B`, `AXW-097` | 完整本地门禁、Windows bundle/installer、升级恢复、SBOM、签名决策和 exact-SHA CI 齐全；发布仍需所有者批准 |
| `AXW-H5-EXIT` | 稳定版裁决 | `AXW-060` | 只有同一制品通过 CI、安装态、升级、恢复、隐私与现场 readback 才可标记 v1.0 可发布 |

## 10. H6–H10 Parking Lot

以下任务定义保持固定，但默认 `DEFERRED`。每个 Horizon 都需要所有者显式激活、独立 TaskPack、风险审查和新的资源预算。

| ID | Horizon | 固定目标 | 依赖 | 额外启动授权 |
| --- | --- | --- | --- | --- |
| `AXW-070` | H6 | Adapter Foundry 合同、隔离、兼容矩阵和回滚 | `AXW-H5-EXIT` | 所有者激活 H6 |
| `AXW-071` | H6 | Zotero 单适配器 | `AXW-070` | 无新增授权 |
| `AXW-072` | H6 | Anki 单适配器 | `AXW-070` | 无新增授权 |
| `AXW-073` | H6 | Joplin/Logseq 分别评测并一次只接入一个 | `AXW-070` | 无新增授权 |
| `AXW-074` | H6 | 课程与结构化 VisualArtifact | `AXW-H5-EXIT` | 所有者激活 H6 |
| `AXW-075` | H6 | Research/Knowledge Adapter 与受控开放导入 | `AXW-070`, `AXW-074` | 无新增授权 |
| `AXW-H6-EXIT` | H6 | H6 集成资格裁决 | `AXW-071`, `AXW-072`, `AXW-073`, `AXW-074`, `AXW-075` | 无新增授权 |
| `AXW-080` | H7 | 完整自适应学习研究与对照实验 | `AXW-H6-EXIT` | 所有者激活 H7 |
| `AXW-081` | H7 | 动画与交互模拟 renderer | `AXW-074`, `AXW-080` | 无新增授权 |
| `AXW-082` | H7 | 2D/2.5D Spatial Memory | `AXW-074`, `AXW-080` | 无新增授权 |
| `AXW-H7-EXIT` | H7 | H7 学习、模拟与空间资格裁决 | `AXW-080`, `AXW-081`, `AXW-082` | 无新增授权 |
| `AXW-090` | H8 | 3D/VR renderer 研究，不建立平行事实库 | `AXW-H7-EXIT` | 所有者激活 H8 |
| `AXW-091` | H8 | Sync/device 边界、冲突、加密与恢复研究 | `AXW-H7-EXIT` | 所有者激活 H8 |
| `AXW-092` | H8 | Controlled Execution 沙箱与权限研究 | `AXW-H7-EXIT` | 所有者激活 H8 |
| `AXW-093` | H8 | 企业协作/多租户隔离研究 | `AXW-091`, `AXW-092` | 所有者批准企业范围 |
| `AXW-H8-EXIT` | H8 | H8 高风险研究资格裁决 | `AXW-090`, `AXW-091`, `AXW-092`, `AXW-093` | 无新增授权 |
| `AXW-098` | H9 | SDK、版本化 API 与开发者文档 | `AXW-H8-EXIT` | 所有者激活 H9 |
| `AXW-099` | H9 | 签名扩展、社区分发与 Marketplace 治理 | `AXW-098` | 所有者批准分发与供应链范围 |
| `AXW-H9-EXIT` | H9 | SDK/扩展生态资格裁决 | `AXW-098`, `AXW-099` | 无新增授权 |
| `AXW-180` | H10 | 通用 Agent、多智能体与自治探索 | `AXW-H9-EXIT` | 新的所有者决策；默认不启动 |

## 11. 开源复用固定优先级

1. 已在项目中合法存在且满足合同的实现。
2. 官方稳定 API/SDK/CLI。
3. 可锁定 revision 和许可证的直接依赖。
4. Adapter/sidecar。
5. 合法 fork/vendor，必须保留来源和修改记录。
6. 经过质量、体积、Windows、CPU、隐私和许可证对比后，才允许自研。

初始候选方向：MarkItDown/pdfplumber/pypdf 用于 PDF 提取，PDF.js 用于阅读，python-docx/python-pptx/openpyxl 用于 Office，Tesseract 为 OCR 基线，Trafilatura 用于静态网页，markdown-it-py/ruamel.yaml/官方 JSON Canvas 规范用于 Vault，py-fsrs 用于复习调度，SQLite FTS5 用于首阶段搜索。候选名称不代表已批准、已安装或已进入发布包。

## 12. 测试语料固定策略

1. 用户提供资料只能在当次授权路径和操作范围内使用，不把私人绝对路径、正文或元数据提交到公开仓库。
2. 用户资料不完整且不具代表性，因此必须补充合法公开 corpus。
3. 公开语料覆盖中文/英文、正常/边界/损坏、不同规模和不同生成器；每个样本记录来源、许可、获取时间、revision/SHA 和预期。
4. 开源仓库本身可以作为学习知识 corpus，但“可读取测试”不等于“可复制进产品”。
5. 下载和生成资料只进入 `.hermes/`；进入长期测试 fixture 前必须最小化并完成许可审查。

## 13. 所有者专属操作

以下操作不因本任务列表存在而获得授权：合并或关闭 PR、直接推送 main、修改 branch protection、仓库改名、顶层许可证/重新许可、签名证书、发布 release、上传安装器、删除远端分支、修改全局 Codex/Hermes/系统配置。执行时必须再次获得对应明确授权。
