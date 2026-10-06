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
| CAP-0010 | 原件资产与来源接入 | 5、6、16 | `binding_core / supported`（96/98） | 未在轮内单独复跑；来源导入与原件读取有既有测试目录 | 取证待补：按 `tests/` 中来源导入用例逐项登记 |
| CAP-0020 | 多格式转换 | 6 | `binding_core / in_progress`（104/107） | 轮内复跑格式/路由套件 `tests/test_format_matrix.py`、`test_format_execution_v1.py`、`test_multiformat_extraction.py`、`tests/workers/test_text_ndjson.py` → **47 passed + 47 subtests** | 音视频仅头信息探测（见审计更正）；ASR 已实现分段执行但未在安装态验收 |
| CAP-0030 | 证据锚定与交叉核验 | 3、7、11 | `binding_core / supported`（114/116） | 未在轮内单独复跑 | 取证待补；识别忠实度与专业依据须分别登记 |
| CAP-0040 | 人类深度学习系统 | 8 | `binding_core / in_progress`（123/125） | 未在轮内单独复跑 | 诊断/路线/迁移/元认知的分项状态待登记 |
| CAP-0050 | AI 学习资产与受控调用 | 9 | `binding_long_term / planned`（132/134） | 无 | 仅目标 |
| CAP-0060 | LER 视觉教学与课件 | 10 | `binding_long_term / planned`（141/143） | 无 | 仅目标 |
| CAP-0070 | 动态解释与仿真 | 10 | `binding_long_term / planned`（150/152） | 无 | 仅目标 |
| CAP-0080 | 空间记忆与沉浸学习 | 12 | `binding_long_term / planned`（159/161） | 无 | 仅目标；3D/XR 为保留的长期能力 |
| CAP-0090 | 研究、课程与项目空间 | 11 | `binding_long_term / planned`（168/170） | 无 | 仅目标 |
| CAP-0100 | 开放互操作与生态适配 | 13 | `binding_core / in_progress`（177/179） | 无（首互通 profile 属 Q10，见 B 组） | 仅目标 |
| CAP-0110 | 搜索、图谱与索引 | 7 | `binding_core / in_progress`（186/188） | 未在轮内单独复跑 | 图谱/双链增量按 U02 属研究方向，未认定已实现 |
| CAP-0120 | 桌面、平台与可选协作 | 14、16 | `binding_core / in_progress`（195/197） | 轮内复跑布局门禁与浏览器 smoke（见快照） | 正式宿主见 `AUTHORITY.md` §6（SUP-022） |
| CAP-0130 | 受限受控执行探索 | 16 | `exploration / planned`（204/206） | 无 | 仅目标；不得扩为通用 Agent OS |
| CAP-0140 | 备份、同步与发布 | 16、17 | `binding_long_term / in_progress`（213/215） | 未在轮内单独复跑 | 备份/恢复有既有实现，Q11 见 B 组 |
| CAP-0150 | 模型、Provider 与数据出境治理 | 9、15、16 | `binding_long_term / planned`（222/224） | 无 | 仅目标 |
| CAP-0160 | 可视化与空间学习表征 | 7、10、12 | `binding_long_term / planned`（231/233） | 无 | 仅目标 |

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
| Q14 | Windows 安装态资格 | `INSTALLED_RUNTIME_VERIFIED / PARTIAL`（87） | **更正记录为 `NOT_RUN`**（更正文件第 74 行），且未做人工视觉确认 | **冲突未决**：账本与更正不一致，按更正从严；安装态资格不得声明已过 |
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
2. Q14 的账本与更正记录不一致，属**未决冲突**，已按从严口径标注。
3. 蓝图附录 8 条来源中 5 条 SOURCE_MISSING（A01、A02、A04、A06 及 U01/U02 的原始聊天），见 `AAOS-INPUT-SOURCES-20261006.json`；
   本表未据未读文件作任何判断。
4. I1—I6 与 F00—F14 无实现证据，属目标而非进度。
