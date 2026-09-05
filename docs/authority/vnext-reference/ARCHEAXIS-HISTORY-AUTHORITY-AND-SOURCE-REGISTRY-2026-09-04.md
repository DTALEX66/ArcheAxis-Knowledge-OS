# ArcheAxis Knowledge 历史、权威与来源总账

> 版本：v1.2（项目用途与许可边界纠正）  
> 基准日期：2026-09-04 UTC  
> 云端仓库：`DTALEX66/ArcheAxis-Knowledge-OS`  
> 已重新确认的默认分支基线：`main@ce3c2de551bcaac52c8a26d012e6482c1a73a540`（2026-09-03T17:51:49Z）  
> 用途：以后任何审计、交接、重构、语言迁移和 UI 迁移必须先读取本总账；不得再由单一 handoff 代替全部历史。

---

## 1. “历史完整”的可验证口径

本总账不使用无法证明的“世界上所有记录都已找到”表述。这里的“完整”严格指：

1. 对当前可访问的持久资料，以 `ArcheAxis`、`Cognitive-Loop-OS`、`Cognitive OS`、`AXOS`、`星环知识` 五组标题别名执行全量标题检索；结果 `next_cursor=null`；
2. 直接项目资料去重后 **85 项**；另以 `三项目`、`THREE-PROJECT`、`TRI_PROJECT`、`DTALEX66` 检索跨项目资料 **13 项**，与直接资料重叠 1 项；合计 **97 项唯一来源资产**；
3. 直接资料中有 55 项 Markdown/DOCX/JSON/XLSX 决策承载物；加入跨项目资料并去重后，共 **64 项决策承载物**；
4. 同时纳入当前云端代码、权威索引、current/truth/history/taskpack、Git 提交与 Release 证据；
5. 纳入本轮对话中 Owner 的最新明确裁决：**桌面 UI 为 C#/Avalonia；权威核心/BFF/唯一领域写者目标为 Rust；Python 仅为可替换 AI/解析/评测侧车**；
   同轮 Owner 澄清：**ArcheAxis 是个人研究项目，当前按非商业目的开发和使用；这是项目用途说明，不是许可限制；仓库现行第一方许可继续为 MIT，第三方组件保持原许可**；
6. 20MB《ArcheAxis完整项目对话与时间线汇报》覆盖至 2026-08-25。2026-08-26 至 2026-09-04 由 8 月 26/31 专项任务包、9 月 1 日语言与目录任务包、9 月 3 日交接、仓库权威索引和本轮 Owner 裁决连续补齐；这是一条显式覆盖接缝，不得隐藏；
7. 未上传、已永久删除、未在当前账号/连接范围内的资料无法被证明存在或不存在。若未来发现，必须追加为新来源并重跑冲突裁决，不能声称此前“其实早已读取”。

### 1.1 本次检索统计

| 范围 | 唯一项 | 决策承载物 | 其他证据资产 | 分页状态 |
|---|---:|---:|---:|---|
| ArcheAxis 与历史别名直接资料 | 85 | 55 | 30 | `next_cursor=null` |
| 三项目/仓库联动资料 | 13 | 10 | 3 | `next_cursor=null` |
| 去重总计 | 97 | 64 | 33 | 已结束 |

直接资料 MIME 分布：Markdown 48、ZIP 18、PNG 10、DOCX 4、JSON 2、HTML 1、XLSX 1、未知/校验文件 1。

---

## 2. 权威等级

| 等级 | 来源 | 用法 |
|---|---|---|
| A0 | Owner 当前明确决策 | 冲突时最高；必须形成 ADR/Decision Ledger 后进入仓库 |
| A1 | 当前云端源码、锁文件、测试、精确 SHA CI、Release/安装态回读 | 判断“现在实际是什么”；代码存在不等于运行/发布通过 |
| A2 | 当前仓库 `docs/*_AUTHORITY_INDEX.md`、`docs/current/`、`docs/truth/` | 判断当前责任边界、事实状态和门禁 |
| A3 | 专项架构/迁移任务包与最新完整交接 | 确定目标和执行 DAG；若与 A0-A2 冲突必须标出 |
| A4 | 历史蓝图、总任务包、对话归档、旧交接 | 保留需求来源和演进原因，不直接覆盖当前事实 |
| A5 | 外部研究、UI 图、演示、基准和开源清单 | 作为候选与设计证据，不自动成为产品决策 |
| A6 | 重复副本、ZIP 配套包、图片、HTML、校验文件 | 保留资产和哈希价值，不重复计票 |

冲突裁决固定顺序：`A0 → A1 → A2 → A3 → A4 → A5 → A6`。同级冲突按“更具体的专项决定优于综合摘要；更新且证据完整者优先；任何完成声明必须有可回读收据”处理。

---

## 3. 已确认的决策演进与 supersession ledger

| 主题 | 历史状态 | 后续变化 | 2026-09-04 生效裁决 |
|---|---|---|---|
| 产品身份 | Cognitive Loop OS / 知行环 OS / Cognitive-Knowledge-System / AXOS 等历史名 | 锁定 ArcheAxis Knowledge / 星环知识平台 | 产品为人类与 AI 双主体的重型学习、可信知识和证据 OS；不是通用 Agent OS 或普通知识库 |
| 仓库 | 历史出现 `archeaxis-workspace` 等表述 | 云端唯一仓库成为 `DTALEX66/ArcheAxis-Knowledge-OS` | 仓库名不因 UI/语言迁移而改名 |
| 三项目边界 | 部分旧文档混合工作流、设计和知识能力 | 2026-08-18 三项目分层决策 | ArcheAxis=Knowledge Authority；WORK-LAB=Action Authority；DESIGN-LAB=Design Authority；各自独立数据库、CI、Release、回滚 |
| 当前实现语言 | Python 领域/API/SQLite + React/Tauri UI | 2026-09-01 决定迁向 Rust Core、Python sidecar；2026-09-03 决定 Avalonia UI | **C#/Avalonia UI + Rust authoritative Core/BFF/sole writer + Python replaceable sidecars** |
| 项目定位与第一方许可 | 当前 `LICENSE`、`pyproject.toml`、`THIRD_PARTY_NOTICES.md` 为 MIT；历史资料称 Personal Research Project | 2026-09-04 Owner 明确“个人研究、非商业使用”描述项目用途，并非要求更改许可证 | 仓库继续使用 MIT；README 并列说明个人研究/非商业目的与 MIT 许可，不增加 `Non-Commercial Use Only`、商业授权或 source-available 限制；第三方原许可不变 |
| 9 月 3 日冲突 | 交接将“不以 Rust/Tauri 为 UI 主线”扩写为 Python 继续拥有领域/数据服务 | 与 9 月 1 日专项语言任务包、云端 Language Authority 及 Owner 裁决冲突 | 保留 Avalonia UI 决定；废止 Python 长期领域权威结论；进入 sunset 的是 React/Tauri 产品面，不是 Rust Core |
| 写者迁移 | 当前 legacy Python 命令路径仍为旧库事实写者；历史方案要求在同一权威链上先收敛、只读差分、逐聚合切换 | 本轮 clean-sheet 决定不让 Rust 接管或共享旧库，而是建立隔离 vNext 库 | 历史“Rust 逐聚合接管旧库”的前向步骤由 D-003 废止；保留其中的快照、差分、零未分类损失和禁双写原则。旧库始终由 legacy Python 独占，vNext 新库从 Day 1 由 Rust 独占；迁移只走一致快照→只读导出→Rust staging import→人工激活 |
| UI 信息架构 | 历史出现多套 7/8/9 模块与命名 | 近期收敛六空间 | Library、Evidence、Learning、AI Assets、Workspace、Settings；二级能力不伪装顶层产品 |
| 开发生成目录 | 当前仓库以 `.hermes/` 承载项目生成证据 | 目标仓库规范提出 `.project-local/` | `.hermes/` 是当前事实；`.project-local/` 是经清单、兼容、回滚后迁移的目标，不能直接改名/删除 |
| 解析/AI | Python 同时承担领域与成熟生态能力 | 核心与 sidecar 分离 | Docling/MarkItDown/OCR/ASR/模型继续由 Python adapter/worker 承担；只产候选和 loss/receipt，不写真值 |
| 插件 | “一切皆插件”研究曾被视为近期架构方向 | 当前产品闭环优先 | WASI/Component Model 作为 Core 稳定后的受控扩展；不得先建 Marketplace 或让插件写库 |
| 平台 | Windows 为当前真实交付面；曾出现 Apple/Desktop 任务包 | Avalonia 允许跨平台 | Windows-first；macOS/Linux 仅在 Core 与 Windows 发布权威稳定后资格化，不以编译成功宣称支持 |

---

## 4. 当前云端权威链

当前默认分支最新提交已在 2026-09-04 重新读取，而不是复用旧 handoff：

- `ce3c2de551bcaac52c8a26d012e6482c1a73a540` — `docs: record exact CI repair evidence`，2026-09-03T17:51:49Z；
- `af216e349b283f7c3a7ffbadc5f980b35bed8b87` — `fix: classify historical CI baseline`；
- `24e817789bde2efacea7d37a7bd1c861847a468c` — `fix: align CI OCR smoke and operational records`；
- `9217c510b3b150fe9da72a437ad31df45db616c4` — `feat: harden multi-format runtime qualification`。

### 4.1 每次审计必须读取的仓库文件

| 责任面 | 当前入口 | 已核对的核心结论 |
|---|---|---|
| 语言边界 | `docs/LANGUAGE_BOUNDARY_AUTHORITY_INDEX.md` | 当前 Python writer；目标 Rust；G0→只读差分→两份零差异→单聚合切换；禁双写 |
| 语言任务采纳 | `docs/current/AXM_LANGUAGE_AUDIT_TASK_ADOPTION_2026-09-02.md` | Rust 长期权威核心、React 当时仍为产品表面、Python sidecar；G1-G9 DAG |
| G0 冻结 | `docs/current/AXM_G0_MIGRATION_FREEZE_RULES_2026-09-02.md` | 无备份/指纹/回滚/拒绝路径不得换 writer |
| G0 缺口 | `docs/current/AXM_G0_EVIDENCE_GAP_REGISTER_2026-09-03.md` | exact-SHA 全资格化、多格式旅程、writer/consumer/rejection 证据仍有缺口 |
| G0 owner | `docs/current/AXM_G0_OWNER_MAP_2026-09-02.md` | 当前 writer/consumer 是静态证据，不能冒充 runtime reachability |
| 运行交付 | `docs/RUNTIME_DELIVERY_AUTHORITY_INDEX.md` | 当前主链为 `frontend/`→root Tauri→Green；recovery shell 非主产品 |
| 目录 | `docs/DIRECTORY_AUTHORITY_INDEX.md` | 路径分类不授权移动/删除；Green `data/` 永不因仓库修复被触碰 |
| 规范化 | `docs/current/REPOSITORY_NORMALIZATION_STATE_2026-09-03.md` | 当前仍是 G0-only；目录移动和编译不能代替语言迁移 |
| 活跃问题 | `docs/current/OPERATIONAL_ISSUE_ARCHIVE_2026-09-04.md` | OP-001~010；选择性 CI 已修，full qualification 仍 open |
| 当前事实 | `docs/current/CURRENT_REALITY_2026-09-01.md` | 必须与最新提交/CI 回读比对；文件日期不是事实新鲜度证明 |
| 文档权威 | `docs/DOCUMENTATION_AUTHORITY_INDEX.md` | current/truth/history/plan 分层读取 |
| 配置权威 | `docs/CONFIGURATION_AUTHORITY_INDEX.md` | 默认值、profile、工具、门禁配置不得多源漂移 |
| 产品真值 | `docs/truth/NAMING_CONTRACT_V2.md`、`docs/truth/CAPABILITY_ATLAS_V2.yaml` | 名称、能力与 deferred 范围 |
| 历史执行 | `docs/truth/EXECUTION_STATUS_LOG.md` | 追加式保留失败与修复，不重写历史 |

### 4.2 当前事实与目标必须分栏

| 层 | 当前事实 | 目标 |
|---|---|---|
| UI | React/Vite + Rust/Tauri 主 host，另有 recovery host | C#/Avalonia 单一桌面 UI 与 Supervisor |
| Rust | Tauri host/恢复边界；没有已落地的 authoritative core/Axum workspace | Domain/Core/Store/API/local-service，在隔离的 vNext 新库中成为唯一 writer，不接管或共享 legacy DB |
| Python | 当前领域/API/SQLite writer，并承担解析/AI | 只保留版本化、可替换、无 DB 句柄的 sidecars |
| 数据 | 分散 SQLite 写入与 legacy/V2 并存风险 | Rust command path 单一写入，append-only 事件/receipt，projection 可重建 |
| 发布 | `v0.6.14` 是不可变历史稳定发布；`main@ce3c2de` 未发布 | 通过 exact-SHA、签名、SBOM、安装态和回滚后再建立新发布权威 |

---

## 5. 直接项目资料全量清单（85 项）

下表中的稳定 ID 用于以后精确读取；`(1)`、同大小同日期附近副本与 ZIP/MD 配套不视为独立裁决。

| # | 标题 | 稳定 ID |
|---:|---|---|
| 1 | `02-ARCHEAXIS-DEEPENED-TASKPACK(1).md` | `libfile_de39e76bb2388191a8afdcbe5b768de5` |
| 2 | `02-ARCHEAXIS-DEEPENED-TASKPACK.md` | `libfile_0de7e34be43c819181905b1daadccb32` |
| 3 | `AI Agent 时代基础设施地图：WORK-LAB 与 ArcheAxis Workspace 可执行深度研究报告` | `libfile_0b39eadf07d4819183b06e1f4ea0fe5d` |
| 4 | `ArcheAxis Knowledge “一切皆插件”架构改造深度研究报告` | `libfile_eb360ba680ec8191856a63ec58547c1d` |
| 5 | `ArcheAxis OS Overview.docx` | `libfile_029a669e68948191808035cac3ddb596` |
| 6 | `ArcheAxis OS V3.0 Blueprint.docx` | `libfile_1b9ef0421ad881919cfc8ae3d800a6ac` |
| 7 | `ArcheAxis OS V3.1 Documentation.docx` | `libfile_871a17e6aed88191810cec30da5226a7` |
| 8 | `ArcheAxis 智能知识工作台.png` | `libfile_a0cd6836d54c81919e75d644cb4b83ee` |
| 9 | `ArcheAxis 知识工作区首页.png` | `libfile_58ccfb010e2c81918517e10cfcfdaf9d` |
| 10 | `ARCHEAXIS-CLEAN-SHEET-LANGUAGE-AUDIT-MIGRATION-TASKPACK-2026-09-01(1).md` | `libfile_802c6ebabd888191a0b1703151300fd4` |
| 11 | `ARCHEAXIS-CLEAN-SHEET-LANGUAGE-AUDIT-MIGRATION-TASKPACK-2026-09-01.md` | `libfile_346de37fed90819190956431e82348fc` |
| 12 | `ARCHEAXIS-COMPLETE-REPAIR-AND-LANGUAGE-MIGRATION-PLAN-2026-09-04.md` | `libfile_2b146f9f03708191a3fdad77e1dbf5dd` |
| 13 | `ARCHEAXIS-DIRECTORY-MIGRATION-CLEANUP-TASKPACK-2026-09-01.md` | `libfile_7c96d8f71b248191900af1607a51f131` |
| 14 | `ARCHEAXIS-FINAL-TASKPACK-2026-08-25.md` | `libfile_73920db5f14c8191996a9cdc521fbfec` |
| 15 | `ArcheAxis-Knowledge-Full-UI-Effect-Screens-v1-2026-08-13.zip` | `libfile_a7b639b48f888191ac39ffcce8da0443` |
| 16 | `ArcheAxis-Knowledge-Historical-Visual-Frontend-Assets-v1-2026-08-13.zip` | `libfile_727fb3724e58819193875650fea31ef5` |
| 17 | `ArcheAxis-Knowledge-OPEN-DESIGN-UI-TaskPack-v1-2026-08-12.zip` | `libfile_bcce3d7803b481918331c8dec661149b` |
| 18 | `ArcheAxis-Knowledge-OS-SUMMARY.md` | `libfile_9ff8707c6a6c819192c13fe0772474ab` |
| 19 | `ArcheAxis-Knowledge-OS_Project_Config_CI_DeDup_TaskPack_2026-08-13.md` | `libfile_a72e3d1f81408191ae3c0760e5706c9e` |
| 20 | `ARCHEAXIS-NEW-CHAT-HANDOFF-2026-09-03(1).md` | `libfile_a24acadc959881919a4fd203befa1042` |
| 21 | `ARCHEAXIS-NEW-CHAT-HANDOFF-2026-09-03.md` | `libfile_5b16aeece6388191923545f00b0b6ecf` |
| 22 | `ArcheAxis_2026-07-31_完整对话整理与决策归档.docx` | `libfile_7b3ae6462a708191b844a3d6175be3d5` |
| 23 | `ArcheAxis_2026-07-31_完整对话整理与决策归档.md` | `libfile_4062a1fe3f548191a3f2798e8b7e971a` |
| 24 | `ArcheAxis_Apple_Desktop_Full_UI_TaskPack_v1.0.zip` | `libfile_e394bbd862308191b869969c4d4cbb7c` |
| 25 | `ArcheAxis_Apple_Desktop_HERMES_MasterPrompt_v1.0.md` | `libfile_eac0d3a20da88191942f6ba1b085b68f` |
| 26 | `archeaxis_desktop_a1.html` | `libfile_e84401d278cc819196edca648d241517` |
| 27 | `ArcheAxis_Desktop_Cloud_Reaudit_Modification_Pack_v1.0.zip` | `libfile_f61701ea5794819195ec2321701e6c7e` |
| 28 | `ArcheAxis_Desktop_HERMES_Master_TaskPack_v1.0.md` | `libfile_a27f52a4e2948191a39ad9e4cffa3045` |
| 29 | `ArcheAxis_Frontend_Reconstruction_and_Generation_Prompts_2026-08-21.md` | `libfile_ec8db1421e9481918040d4b5956b88ea` |
| 30 | `ArcheAxis_HERMES_Full_TaskPack_2026-08-01_v1.0.zip` | `libfile_fb086b8ea34c8191b69b255241f1953e` |
| 31 | `ArcheAxis_HERMES_Master_Command_2026-08-01_v1.0.md` | `libfile_b11379097f1c8191ac0616c90451124b` |
| 32 | `ArcheAxis_HERMES_Master_TaskPack_2026-07-28_v1.0.md` | `libfile_e3d20e3c5db481918e114a9accc0187e` |
| 33 | `ArcheAxis_Knowledge_Benchmark_TaskPack_v1.0.md` | `libfile_a36e3e6ff8708191b1839b0bddf89c0d` |
| 34 | `ArcheAxis_Knowledge_Benchmark_TaskPack_v1.0.zip` | `libfile_fa44a66d01548191bb7e8343ad90ffd7` |
| 35 | `ArcheAxis_Knowledge_Cloud_Audit_Plugin_Core_UI_HERMES_TaskPack_2026-08-14.md` | `libfile_be388f3c2c8c8191814a8550d2c32853` |
| 36 | `ArcheAxis_Knowledge_Final_Architecture_ExternalStore_Release_HERMES_TaskPack_2026-08-14.md` | `libfile_96abd89a8ed88191adcbfb0df5c94b9c` |
| 37 | `ArcheAxis_Knowledge_MultiFormat_ClosedLoop_HERMES_TaskPack_2026-08-13.md` | `libfile_4c8970c1c0808191849d580a94d98012` |
| 38 | `ArcheAxis_Knowledge_MultiFormat_ClosedLoop_HERMES_TaskPack_2026-08-13.zip` | `libfile_2c91babe213081918050c7cc5e41aca1` |
| 39 | `ArcheAxis_Knowledge_Naming_Audit_TaskPack_v1_2026-08-12.zip` | `libfile_dd70eb27b6d48191b3b237137489865a` |
| 40 | `ArcheAxis_Learning_Workspace_System_Blueprint_and_HERMES_Update_TaskPack_v1_2026-08-11.md` | `libfile_143c4ff08dd88191a88b5b6160fb23dd` |
| 41 | `ArcheAxis_Learning_Workspace_System_Blueprint_and_HERMES_Update_TaskPack_v1_2026-08-11.zip` | `libfile_de733805caec8191a48910daef7804d7` |
| 42 | `ArcheAxis_Open_Source_Research_Master_2026-07-30_v1.0.zip` | `libfile_87cafaf4b9e08191b14313ac50789b4a` |
| 43 | `ArcheAxis_Open_Source_Research_Master_List_2026-07-30.md` | `libfile_96abf84c781c8191bb4afa5b6959426c` |
| 44 | `ArcheAxis_OS_CI_Acceleration_WORKLAB_Compatible_HERMES_TaskPack_2026-08-07.md` | `libfile_c84167dd3a808191ab76d1d45f6e3c97` |
| 45 | `ArcheAxis_OS_Cloud_Full_Audit_Integrated_TaskPack_2026-08-07.md` | `libfile_01b1e47c1e1c8191aba5135e6930f0bc` |
| 46 | `ArcheAxis_OS_Full_Context_Handoff_2026-08-19(1).md` | `libfile_73ab97017af08191bc1dd3a276c15c38` |
| 47 | `ArcheAxis_OS_Full_Context_Handoff_2026-08-19.md` | `libfile_2ca78f5d6d248191a4d23bdab499fe37` |
| 48 | `ArcheAxis_OS_MCS_Phase5_v0.1.0.sha256` | `libfile_30125db279948191a83f04892a403906` |
| 49 | `ArcheAxis_OS_MCS_Phase5_v0.1.0.zip` | `libfile_34b107b552f4819199b8c26c7d5eb316` |
| 50 | `ArcheAxis_OS_Minimum_Surface_Master_TaskPack_2026-08-06.md` | `libfile_4b3d5c1a73488191acf28c4f4bac1584` |
| 51 | `ArcheAxis_OS_New_Conversation_Handoff_2026-08-19.zip` | `libfile_56f6ecd184dc819182b3e5893fb06bc5` |
| 52 | `ArcheAxis_OS_Only_Product_UI_Naming_Compatibility_Audit_2026-08-08.md` | `libfile_e2b9cc3b33508191b9e9099fb864f016` |
| 53 | `ArcheAxis_OS_Project_Library_Architecture_2026-08-18.md` | `libfile_48b2c145ecac8191baf554c47631f6b9` |
| 54 | `ArcheAxis_Project_Context_Handoff_2026-08-17.md` | `libfile_4d6017b3022081918c47834ec7f4299a` |
| 55 | `ArcheAxis_Project_Context_Handoff_2026-08-18.md` | `libfile_e95b7e77e6e08191bb85c4fbe08c1a1a` |
| 56 | `ArcheAxis_Today_Conversation_Archive_HERMES_TaskPack_2026-07-28_v1.0.zip` | `libfile_2896703a0c908191aaddf76651485369` |
| 57 | `ArcheAxis_UI_Concept_v0.4.1.zip` | `libfile_10ff585ae7e481919443418a401de096` |
| 58 | `ArcheAxis_v0.6.0_Minimum_Closed_Loop_Release_TaskPack_2026-08-20.md` | `libfile_19c9c44b3b008191a78ac71d99b9a94b` |
| 59 | `ArcheAxis_Workspace_CODEX_Final_Master_TaskPack_v3_2026-08-09.md` | `libfile_a2414a0eae508191aa80d6df4c79c4ac` |
| 60 | `ArcheAxis_Workspace_Complete_Project_Introduction_and_Integrated_Blueprint_v1_2026-08-11.md` | `libfile_85e9a4dc24c481918f63256bde1fdabf` |
| 61 | `ArcheAxis_Workspace_Complete_Project_Introduction_and_Integrated_Blueprint_v1_2026-08-11.zip` | `libfile_eef510b103908191adbbb2ff01dbb963` |
| 62 | `ArcheAxis_Workspace_Context_Handoff_2026-08-10(1).md` | `libfile_58aa35888c8c81919cd9afc39aa89049` |
| 63 | `ArcheAxis_Workspace_Context_Handoff_2026-08-10.md` | `libfile_070a840afbf881919a3618598ae4c28f` |
| 64 | `ArcheAxis_Workspace_Final_Master_TaskPack_v4_2026-08-09.md` | `libfile_1f76b12718d08191966ceb66e3bccaca` |
| 65 | `ArcheAxis_Workspace_Future_Master_Blueprint_v1_2026-08-09.md` | `libfile_170cd96502048191a0ab2ebb3ade5183` |
| 66 | `ArcheAxis_Workspace_Incremental_TaskPack_OSS_Windows_LER_v1_2026-08-09.md` | `libfile_e456529807248191bf10c5a3671b9bf0` |
| 67 | `ArcheAxis_Workspace_Multiformat_Recognition_Web_Verification_Enhancement_TaskPack_v1_2026-08-11.md` | `libfile_573eac3ffbd88191ab70e4b1aa268412` |
| 68 | `ArcheAxis_Workspace_Project_History_and_OSS_Absorption_Master_Atlas_v1_2026-08-11.md` | `libfile_2b9114805b688191b702dde32f322a0e` |
| 69 | `ArcheAxis_Workspace_v0.5_Multiformat_Full_Audit_and_Recovery_TaskPack_2026-08-09.md` | `libfile_420f7c20183081918ae4e37886fac362` |
| 70 | `ArcheAxis完整项目对话与时间线汇报.md` | `libfile_33ae3cd6ebc88191980d4edff8e4de56` |
| 71 | `OPEN-DESIGN-ARCHEAXIS-WORKSPACE-UI-MASTER-PROMPT-2026-08-11.md` | `libfile_62e2f4becdcc8191903087fa8533ec74` |
| 72 | `WORK-LAB_and_ArcheAxis-Knowledge-OS_Config_Governance_TaskPacks_2026-08-13.zip` | `libfile_fb11c63f55648191ab071af042315be0` |
| 73 | `三项目联动分层架构决策文档：ArcheAxis _ WORK-LAB _ DESIGN-LAB.md` | `libfile_1d1876e534788191a19d2a74743836aa` |
| 74 | `Cognitive-Loop-OS-Frontend-System-UI-Audit-and-TaskPack-2026-08-11.md` | `libfile_e7c4d0ea68088191828adfb0513de7c7` |
| 75 | `Cognitive-Loop-OS_INTEGRATION.md` | `libfile_b9b58bf37c948191b9bec395e72193b1` |
| 76 | `03_AXOS_开源能力总表.xlsx` | `libfile_3148895b1ea88191a096107afd6a08fd` |
| 77 | `AXOS_OpenSource_Absorption_Pack_2026-07-25.zip` | `libfile_5385fee7f6208191b6006e846c5c4d57` |
| 78 | `星环知识平台·学习主页(1).png` | `libfile_a7f0cbf3dec88191938d4631ab218074` |
| 79 | `星环知识平台·学习主页.png` | `libfile_308e7ec841b48191a5e1d7a3acf2396d` |
| 80 | `星环知识平台工作台总览(1).png` | `libfile_a66b340bd1a481918630633454fbe421` |
| 81 | `星环知识平台工作台总览.png` | `libfile_d6575a8613dc8191bb6e67560c641254` |
| 82 | `星环知识平台并排差异阅读器(1).png` | `libfile_eea778676964819180562321fc674a11` |
| 83 | `星环知识平台并排差异阅读器.png` | `libfile_3faa112d93fc8191976714310a80ae84` |
| 84 | `星环知识平台资料库(1).png` | `libfile_3789566d6c1c81918d876682a86f6440` |
| 85 | `星环知识平台资料库.png` | `libfile_081d9a3092008191954ce2e5e5b64034` |

> 注：第 3 项的稳定 ID 以本轮检索返回值为准；任何 ID/标题不一致都应重新以标题精确检索，不得猜测。

---

## 6. 跨项目与仓库联动资料（13 项，1 项与上表重叠）

| # | 标题 | 稳定 ID | 作用 |
|---:|---|---|---|
| 1 | `Cognitive_Knowledge_System_三项目聚合分析包.zip` | `libfile_a7e33c6e9f6c8191bc8fa958ae643230` | 历史聚合资产 |
| 2 | `三项目 AI 原生桌面工作台与运行闭环研究报告` | `libfile_4569193cd3188191a56af0e1b4eacf1a` | 外部研究 |
| 3 | `三项目定位、总体蓝图与 DSH 闭环架构研究报告` | `libfile_02c4a2d116508191980a31ad41368099` | 架构研究 |
| 4 | `三项目联动分层架构决策文档：ArcheAxis _ WORK-LAB _ DESIGN-LAB.md` | `libfile_1d1876e534788191a19d2a74743836aa` | A3 决策；与上表重复 |
| 5 | `00-THREE-PROJECT-TASKPACK-INDEX(1).md` | `libfile_826b75a80e5c81918a4d5077a2efb708` | 重复索引 |
| 6 | `00-THREE-PROJECT-TASKPACK-INDEX.md` | `libfile_00e21079b0288191aaf0915fd39ff48e` | 任务索引 |
| 7 | `DTALEX66-Three-Project-Development-Pack-v5.0.zip` | `libfile_ac614a7b5f1c819182d7539304447dd9` | 历史配套包 |
| 8 | `DTALEX66-Three-Project-Development-Pack-v5.1.zip` | `libfile_20dd151b2e2c8191b877b7ed5ac65ab2` | 历史配套包 |
| 9 | `THREE-PROJECT-CLOUD-AUDIT-FRONTEND-OSS-FIRST-2026-08-31.md` | `libfile_fbd81d08d6cc8191ad7bb668a65ab315` | 8/25 后覆盖接缝 |
| 10 | `THREE-PROJECT-OSS-REUSE-FAST-TRACK-2026-08-26.md` | `libfile_30d360aec1e08191b65ebef7ed0fd96d` | 8/25 后覆盖接缝 |
| 11 | `DSH_TRI_PROJECT_FULL_TASKPACK_2026-08-19.md` | `libfile_d9a091b63fa88191a8b441bb478781dd` | 三项目任务包 |
| 12 | `Tri_Project_Full_Audit_2026-08-24.md` | `libfile_0f8eb2ebb1d48191b2e9f705503e84a9` | 三项目全审计 |
| 13 | `DTALEX66 三仓库全面云端审计与视觉智能演进研究` | `libfile_2fab7e1ec35881919f1f45ecacd8b8f4` | 云端/视觉研究 |

---

## 7. 重复件与时间接缝处理

### 7.1 已识别重复组

- `02-ARCHEAXIS-DEEPENED-TASKPACK.md` 与 `(1)`；
- 2026-09-01 clean-sheet language taskpack 两份；
- 2026-09-03 handoff 两份；
- 2026-08-19 handoff 两份及 ZIP 配套；
- 2026-08-10 handoff 两份；
- 2026-07-31 对话归档 DOCX/MD 为同主题不同载体；
- 多个 MD/ZIP 配套任务包；
- 四张 UI 页面各有原图与 `(1)` 版本；
- THREE-PROJECT-TASKPACK-INDEX 两份。

规则：内容 hash 相同则一个 canonical、其余 alias；内容不同则生成差异摘要并判断是否为修订版。不得按文件创建时间简单覆盖，也不得因 `(1)` 自动认定更新。

### 7.2 时间接缝

```mermaid
flowchart LR
    A["7 月蓝图与早期任务包"] --> B["8 月 9–24 总任务包与交接"]
    B --> C["8 月 25：20MB 对话归档"]
    C --> D["8 月 26/31：三项目与 OSS 任务包"]
    D --> E["9 月 1：Rust 语言任务包"]
    E --> F["9 月 3：Avalonia 交接 + 云端权威"]
    F --> G["9 月 4：Owner 裁决与本总账"]
```

---

## 8. 以后不得再次丢历史的执行协议

每次新会话、审计或任务包必须：

1. 先读取本总账、最新 Owner 决策和云端 authority indexes；
2. 重新查询五组直接别名与四组跨项目别名，记录计数、`next_cursor`、时间；
3. 按稳定 ID 读取真正影响当前任务的来源，不用标题或记忆猜内容；
4. 对新资料计算 `source_id/title/hash/created_at/observed_at/authority/class/supersedes/superseded_by`；
5. 将“当前事实、目标、已验证完成、计划、历史”分开；
6. 任何语言/UI/数据库/发布变更都追加 supersession row；旧决定保留但标为 superseded；
7. handoff 只做导航，不能复制一份不带来源的“最终结论”；
8. 每个完成声明绑定 exact SHA、命令、退出码、测试清单、平台、artifact hash 和可回读结果；
9. 当前资料与云端代码冲突时，报告冲突，不把计划写成实现；
10. 新来源发现后更新本总账版本并保留旧版本，禁止静默覆盖。
11. “个人研究、非商业目的”等项目定位不得被自动解释为许可限制；任何未来许可变化必须来自 Owner 独立、明确的决定，并记录生效 SHA、权利人同意、第一方/第三方边界和对旧 Release 的处理。

建议在仓库增加机器可读 `docs/truth/SOURCE_AUTHORITY_REGISTRY.yaml`，并由 CI 验证：

- 每个 current/decision 文档都有稳定 ID、authority、effective date；
- 每个 superseded 文档都有后继链接；
- 同一责任面只能有一个 `CURRENT`；
- handoff 不得成为无来源的 authority；
- README 的版本、能力和发布状态只能由 current truth 投影；
- source registry 变更必须经过 CODEOWNERS/Owner review。

---

## 9. 本总账的明确结论

1. 用户没有记错：**核心目标就是 Rust**；此前把 9 月 3 日交接中的 Python 领域服务当成最终架构，是冲突整理错误。
2. 当前代码仍不是 Rust Core 成品：Python 仍是 writer，Rust 只是 Tauri/恢复边界；这正是迁移起点，不是方向否定。
3. 正确的长期语言边界是：**Avalonia/C# 管桌面体验；Rust 管领域真值、BFF、存储、迁移和恢复；Python 管可替换 AI/解析生态。**
4. Rust 不得直接抢写旧库：仓库原 G0 中的备份、指纹、差分、拒绝路径和回滚要求继续作为迁移安全门；“Rust 在旧库上只读影子后逐聚合接管 writer”已被隔离新库方案废止。Rust 只写 vNext 新库，legacy Python 只写旧库，二者永不双写。
5. 本总账覆盖了当前可访问历史、已知旧代号、跨项目资料和最新云端权威链；未来若出现新增/未上传资料，将以追加方式纳入，而不是事后否认此前的覆盖边界。
6. Owner 已澄清：ArcheAxis 是个人研究、非商业目的项目，但这不是重许可决定；第一方仓库继续使用 MIT。项目用途、软件许可、第三方许可证和客户/用户内容必须分开治理。
