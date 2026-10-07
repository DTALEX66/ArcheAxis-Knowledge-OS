# AAOS 覆盖矩阵（CAP / Q / F / I）2026-10-06

用途：把输入蓝图的每一个编号、以及本仓已存在的稳定编号，映射到"来源 → 有效决定 → 规范锚点 → 证据 → 下一步"。
本表**不新造状态枚举**，只用各来源已记录的措辞，并注明它写在哪个文件的哪一行。**没有找到实现证据的行留空并写明**，不用 Markdown 链接冒充实测。

方法与边界：

- 输入：蓝图《AAOS 完整项目描述与未来蓝图》2026-10-06（字节 SHA-256 `2c99e7ae…1ed9`，已核）。
- 状态来源必须可定位：`AAOS-CAPABILITY-MASTER-ATLAS-V3-20261002.json`（V3，2026-10-02）、`CAPABILITY_ATLAS_V2.yaml`（V2，2026-08-12）、
  唯一实时进度记录 `AAOS01-Q00-Q15-LEDGER-FINAL-20261005.md`、审计更正 `AAOS01-AUDIT-CORRECTIONS-20261005.md`（2026-10-05）。
- **ID 冲突警告**：本仓 `docs/authority/taskpack-0910-r3/R15-FORMAT-STATUS.json` 里的 `F01—F16` 是**格式覆盖切片**，与蓝图 §17.2 的
  `F00—F14`（未来工作）**不是同一族**，前缀相同、含义不同。本表分别标注，禁止把它们相互对应。

## A. 长期能力 CAP-0010—CAP-0160（16 项）

`authority_status` 与 `technical_state` 在 V3/V2 两份记录中一致；下表"记录值"栏格式为 `authority_status / technical_state`，括号内为 V3 行号。

| ID | 能力范围（蓝图 §4） | 输入章节 | 记录值（V3 行） | 本轮找到的实现/测试证据 | 下一步 / 阻塞 |
| --- | --- | --- | --- | --- | --- |
| CAP-0010 | 原件资产与来源接入 | 5、6、16 | `binding_core / supported`（96/98） | 轮内复跑 `tests/test_vault_restore_api.py` + `test_vault_search_api.py` + `test_vault_write_api.py` → **16 passed，exit 0** | 其余来源接入/原件保全用例待登记；本行只登记已实测部分 |
| CAP-0020 | 多格式转换 | 6 | `binding_core / in_progress`（104/107） | 轮内复跑 `tests/test_format_execution_v1.py` + `test_format_matrix.py` + `test_multiformat_extraction.py` + `test_format_intake_probe.py` → **34 passed，exit 0**（另加 `tests/workers` 146 项 unittest 全通过） | 音视频仅头信息探测（审计更正 §3）；ASR 分段执行为真实引擎但未安装态验收 |
| CAP-0030 | 证据锚定与交叉核验 | 3、7、11 | `binding_core / supported`（114/116） | 轮内复跑 `tests/test_evidence_anchor.py` + `test_evidence_bundle.py` + `test_evidence_bundle_ledger.py` + `test_evidence_commands.py` + `test_anchor_and_loss_probe.py` → **47 passed，exit 0** | 识别忠实度与专业依据须继续分别登记，不得合并为单一可信度 |
| CAP-0040 | 人类深度学习系统 | 8 | `binding_core / in_progress`（123/125） | 轮内复跑 `tests/test_learning_api_security.py` + `test_learning_artifact_card_projection.py` + `test_learning_artifact_contract.py` + `test_learning_event_store.py` → **21 passed，exit 0** | 诊断/路线/迁移/元认知仍未逐项取证；FSRS 不等于掌握或真值 |
| CAP-0050 | AI 学习资产与受控调用 | 9 | `binding_long_term / planned`（132/134） | 轮内复跑 `tests/test_machine_actor_refusal_probe.py` + `test_machine_growth_v1.py` + `test_machine_knowledge_candidates.py` + `test_machine_knowledge_contract.py` → **21 passed，exit 0** | AI 资产/评测/认可/回流/撤回中仅候选与合同有实测，评测与回流未取证 |
| CAP-0060 | LER 视觉教学与课件 | 10 | `binding_long_term / planned`（141/143） | 轮内复跑 `tests/test_courseware_v1.py` + `test_general_courseware_renderer.py` + `test_lesson_contract.py` → **24 passed，exit 0** | 可离线课程包与真实学习事件仍未端到端取证（F05 属未来包） |
| CAP-0070 | 动态解释与仿真 | 10 | `binding_long_term / planned`（150/152） | 本轮未找到**仿真**独立套件：`仿真/动画` 只在课程与 UI 动效用例中出现（`test_courseware_v1.py`、`test_desktop_motion_contract.py`），后者是界面动效合同，不是参数化模型/实验结果 | 待登记：动态解释与仿真属 F08 未来包；不得因课程用例提到动画就记为已实现 |
| CAP-0080 | 空间记忆与沉浸学习 | 12 | `binding_long_term / planned`（159/161） | 轮内复跑 `tests/test_aaos_memory_graph_master.py` + `test_b03_memory_map_mother_contract.py` + `test_memory_graph_hover_filter_contract.py` + `test_memory_graph_keyboard_focus_contract.py` + `test_memory_layers.py` + `test_memory_files.py` + `test_reasoning_memory.py` → **26 passed，exit 0** | 记忆地图与图层有合同与交互实测；知识宫殿/3D/XR 仍为长期目标（F09/F13） |
| CAP-0090 | 研究、课程与项目空间 | 11 | `binding_long_term / planned`（168/170） | 轮内复跑 `tests/test_inspiration_research.py` + `test_knowledge_research_facades.py` + `test_phase4_research_github.py` + `test_research_artifact_runtime_loop.py` + `test_research_boundary.py` + `test_research_knowledge_approval_contract.py` + `test_research_knowledge_governance_lifecycle.py` + `test_research_package_contract.py` + `test_research_to_knowledge_promotion.py` + `test_workspace_research_consumer.py` → **86 passed，exit 0** | 研究→知识的提升与边界有实测；科研可复现结果与反证流程属 F06 未来包 |
| CAP-0100 | 开放互操作与生态适配 | 13 | `binding_core / in_progress`（177/179） | 无（首互通 profile 属 Q10，见 B 组） | 仅目标 |
| CAP-0110 | 搜索、图谱与索引 | 7 | `binding_core / in_progress`（186/188） | 轮内复跑 `tests/test_search_b05_contract.py` + `tests/test_graph_community.py` + `test_graph_index.py` + `test_graph_pipeline.py` + `test_graph_rag.py` → **22 passed，exit 0** | 图谱/双链增量按 U02 属研究方向；多跳 GraphRAG/探索未取证 |
| CAP-0120 | 桌面、平台与可选协作 | 14、16 | `binding_core / in_progress`（195/197） | 轮内复跑 `scripts/a0_browser_smoke.py`（真实 Chromium 六档视口）**PASS**，`tests/workflow/test_workspace_layout_contract.py` 4 passed；见本轮快照 | 正式宿主见 `AUTHORITY.md` §6（SUP-022）；安装态与具体设备未取证 |
| CAP-0130 | 受限受控执行探索 | 16 | `exploration / planned`（204/206） | 轮内复跑 `tests/test_workspace_plugin_dispatch.py` + `test_axw_cap502_plugin_manifest.py` + `test_agent_feedback.py` → **21 passed，exit 0** | 插件清单与派发、Agent 反馈有实测；知识领域任务协调仍受限，不得扩为通用 Agent OS |
| CAP-0140 | 备份、同步与发布 | 16、17 | `binding_long_term / in_progress`（213/215） | 轮内复跑 `tests/test_backup.py` + `test_backup_leaves_library_untouched.py` + `test_backup_restore_probe.py` → **18 passed，exit 0**（另 Q11 见 B 组） | 真实副本恢复与身份核对有实现；跨设备同步未取证 |
| CAP-0150 | 模型、Provider 与数据出境治理 | 9、15、16 | `binding_long_term / planned`（222/224） | 轮内复跑 `tests/test_provider_contract.py` + `test_provider_routing.py` + `test_rag_embedding_provider.py` → **33 passed，exit 0** | Provider 合同与路由有实测；额度/预算与真实云端调用未取证（本地无默认模型） |
| CAP-0160 | 可视化与空间学习表征 | 7、10、12 | `binding_long_term / planned`（231/233） | 轮内复跑 `tests/test_canvas_projection.py` → **1 passed，exit 0** | 画布投影有实测；学习地图与空间投影未取证 |

另：`docs/authority/taskpack-1004-aaos01/registries/capability_handoff.json` 对上述 16 项一律记 `implementation_status: UNVERIFIED`、
`runtime_status: NOT_CHECKED`（CAP-0010 起每 11 行一条）。它是**交接登记**而非进度记录，故不与上表冲突；引用时须标明出处。

## B. 第一包 Q00—Q15（16 项）

唯一实时进度记录 `docs/current/AAOS01-Q00-Q15-LEDGER-FINAL-20261005.md` §"当前状态与剩余缺口"（第 69 行起）：

| ID | 工作内容（蓝图 §17.1） | 账本记录（行） | 审计更正约束 | 下一步 / 阻塞 |
| --- | --- | --- | --- | --- |
| Q00 | 现场保护与基线对账 | `PARTIAL`（73） | — | 本轮快照补齐 observed_at/SHA |
| Q01 | 重构决定、目录与构建登记 | `TESTED_LOCAL`（74） | — | — |
| Q02 | Tauri 启动与只读桥接 | `INSTALLED_RUNTIME_VERIFIED / PARTIAL`（75） | — | — |
| Q03 | 类型合同、有限命令与权限 | `PARTIAL`（76） | — | — |
| Q04 | 原件、Document/Block 与草稿保存 | `TESTED_LOCAL / PARTIAL`（77） | **"完成"声明已撤销**（更正文件第 34 行）：候选调用不证明 Document/Block/草稿恢复一致 | 以更正为准，不得按完成口径汇报 |
| Q05 | 阅读与引用/核验样板 | `INSTALLED_RUNTIME_VERIFIED / PARTIAL`（78） | — | — |
| Q06 | 首批多格式路径 | `INSTALLED_RUNTIME_VERIFIED / PARTIAL`（79） | 音视频仅头信息探测（更正 §3），不得称内容理解 | — |
| Q07 | 候选审核与纠正 | `PARTIAL / AWAITING_OWNER`（80） | — | 待业主人工处置 |
| Q08 | 学习与 AI 资产基础闭环 | `TESTED_LOCAL / PARTIAL`（81） | — | — |
| Q09 | 搜索与完整能力目录 | `INSTALLED_RUNTIME_VERIFIED / PARTIAL`（82） | — | — |
| Q10 | 导出与首个互通 profile | `TESTED_LOCAL / PARTIAL`（83） | — | — |
| Q11 | 一致备份与副本恢复 | `INSTALLED_RUNTIME_VERIFIED / PARTIAL`（84） | — | — |
| Q12 | 轻量格式增补 | `INSTALLED_RUNTIME_VERIFIED / PARTIAL`（85） | — | — |
| Q13 | 性能与故障 | `TESTED_LOCAL / PARTIAL`（86） | — | — |
| Q14 | Windows 安装态资格 | `INSTALLED_RUNTIME_VERIFIED / PARTIAL`（87） | 更正文件（2026-10-05）记 `NOT_RUN`，那是**当时**的状态；账本第 5/87 行记的是其后的证据（固定 SHA `578d06b7…` / run `37399470467` 全 20 job SUCCESS、artifact `11385093136` 的 21 步原生收据、NSIS host SHA `00b7ba9b…`） | 二者是**同一事项的不同日期，不是冲突**。仍然成立的是：不可变 `checks/acceptance.json` 记 `NOT_RUN`，旧默认入口、物理 IME、真人 Owner 未验收——**资格化未达成、不发行** |
| Q15 | 第一包收口与未来交接 | `PARTIAL`（88） | — | — |

冲突情况：`docs/authority/taskpack-1004-aaos01/registries/tasks.json` 对 Q00—Q15 一律记 `"status": "NOT_RUN"`。
它是**规划登记**（任务尚未执行完时全为 NOT_RUN），不是进度记录，故本表以账本＋更正为准，并在此明示该差异以免被误读为第三份进度源。

## C. 未来扩展 F00—F14（15 项，逐项登记）

| ID | 未来工作（蓝图 §17.2） | 状态 | 证据 |
| --- | --- | --- | --- |
| F00 | 真实基线接管 | `NO_IMPLEMENTATION_RECORD` | 轮内检索 `docs/` 与 `tests/` 未找到为该项记状态或声称实现的文件 |
| F01 | 编辑节点深化 | `NO_IMPLEMENTATION_RECORD` | 同左 |
| F02 | 集合、关系、公式、多视图 | `NO_IMPLEMENTATION_RECORD` | 同左 |
| F03 | 全知识库互通 | `NO_IMPLEMENTATION_RECORD` | 同左；互通范围见 D 组 |
| F04 | 学习诊断与辅导 | `NO_IMPLEMENTATION_RECORD` | 同左 |
| F05 | 课程与视觉教学 | `NO_IMPLEMENTATION_RECORD` | 同左 |
| F06 | 科研与研发空间 | `NO_IMPLEMENTATION_RECORD` | 同左 |
| F07 | AI 资产与评测 | `NO_IMPLEMENTATION_RECORD` | 同左 |
| F08 | 动态解释与仿真 | `NO_IMPLEMENTATION_RECORD` | 同左 |
| F09 | 空间记忆与 3D | `NO_IMPLEMENTATION_RECORD` | 同左 |
| F10 | 同步与协同 | `NO_IMPLEMENTATION_RECORD` | 同左 |
| F11 | 插件、技能与知识 Agent | `NO_IMPLEMENTATION_RECORD` | 同左 |
| F12 | 移动、Web 与加密 | `NO_IMPLEMENTATION_RECORD` | 同左 |
| F13 | XR 与 AR | `NO_IMPLEMENTATION_RECORD` | 同左 |
| F14 | 依赖维护与可迁出 | `NO_IMPLEMENTATION_RECORD` | 同左 |

蓝图自身定义它们为"未来工作"，前置条件写在 §17.2；任何一项都不得在 README 或 About 里写成已支持。

**不要**把 `docs/authority/taskpack-0910-r3/R15-FORMAT-STATUS.json` 的 `F01—F16` 读成这张表：那是格式覆盖切片
（该文件 `coverage_summary` 记 `complete: 0, partial: 14, custody_only: 2`，含 F15/F16），前缀相同、族不同。

## D. 全知识库互通 I1—I6（四个独立目标）

四个独立目标——功能等价、数据兼容、双向往返、持续增量互操作——**分别验收**。六组平台范围内本轮均为**目标**：
未找到任何一条已完成的互通实现证据，故不声称任一 profile 已就绪。清单原文见蓝图 §13；完整平台名单保留在规范蓝图，
不整段进 README 的"已支持"列表。首个互通 profile 属 Q10（见 B 组，`TESTED_LOCAL / PARTIAL`）。

| ID | 平台范围（蓝图 §13） | 状态 | 证据 |
| --- | --- | --- | --- |
| I1 | Markdown、Obsidian、JSON Canvas | `NO_IMPLEMENTATION_RECORD` | 轮内未找到双向往返实测；互通候选登记不等于已实现 |
| I2 | Notion、思源、Joplin、Logseq | `NO_IMPLEMENTATION_RECORD` | 同左 |
| I3 | Zotero、Anki | `NO_IMPLEMENTATION_RECORD` | 同左 |
| I4 | AFFiNE、AppFlowy、Outline、Docmost、Wiki.js、BookStack、Anytype、Trilium | `NO_IMPLEMENTATION_RECORD` | 同左；只做限定 profile |
| I5 | Evernote、OneNote、语雀、飞书、Confluence 等 | `NO_IMPLEMENTATION_RECORD` | 同左；取决于实际导出/API 授权 |
| I6 | RAGFlow、FastGPT、MaxKB、Dify、WeKnora、Git/研发资料 | `NO_IMPLEMENTATION_RECORD` | 同左；不导入第二运行时 |

## E. 本轮登记的缺口（不掩盖）

1. A 组多数 CAP 只有记录状态、没有轮内复跑证据；已逐行写明"取证待补"，未用链接冒充。
2. Q14 初稿被我标为「未决冲突」，**经核实不是冲突**：更正文件是 2026-10-05 的状态，账本记录的是其后的证据；此处保留该更正，以免把日期序列误读成两条互相否定的记录。资格化仍未达成（`checks/acceptance.json` 仍 `NOT_RUN`）。
3. 蓝图附录 9 条来源中 5 条 SOURCE_MISSING（U01、U02 的原始聊天未导出，A01、A02、A06 按内容哈希检索仍未找到），另 4 条 VERIFIED_MATCH（A03、A04、A05、A07），见 `AAOS-INPUT-SOURCES-20261006.json`；
   本表未据未读文件作任何判断。
4. I1—I6 与 F00—F14 无实现证据，属目标而非进度。
