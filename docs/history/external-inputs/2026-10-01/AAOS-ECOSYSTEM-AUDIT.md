# 2026-10-01 外部三项目材料中的 AAOS 切片

状态：`ARCHIVED_INPUT / PROPOSED_NOT_EXECUTED`。本目录的 [结构化摘录](AAOS-ECOSYSTEM-EXTRACT.json) 从用户指定的两份 HTML、两份 JSON 中抽出与 ArcheAxis/AAOS 明确相关的段落、裁决和适用于本项目的跨项目行动。原始四文件仍在用户指定位置，未移动、删除或修改；摘录保留四份源文件的字节数和 SHA-256、原始 ID、HTML 文本节点序号。它不是 R6 TaskPack、Authority 或已完成证据。

## 对比审计

| 来源事实/建议 | 本仓当前对照 | 裁决与后续任务归属 |
| --- | --- | --- |
| `H7`、`D11`：长期可复用知识的接受/存储/回忆归 ArcheAxis；WORK-LAB 保留带 provenance 的候选，DESIGN-LAB 保留领域经验 | `PROJECT_CONTRACT.yaml` 的 Rust 单写者及 R6/M0 知识/学习链已有相同方向 | 保留为后续接口边界检查；只有经本仓人审和版本合同才接受候选，不导入原生私有 memory/session。映射 R6 A04/A08 与 M0 人工接受段。 |
| `Q8`、`F18`：AAOS `AGENTS.md` 首行指向 WORK-LAB 旧 `00-governance/global-execution-standard.md` | 本轮读取到该文字；材料称 WORK-LAB 已改用 `docs/decisions`，但未读取 WORK-LAB 当前仓核证路径 | 登记一个本仓规则引用核验任务。确认目标合同与可用性后，单独最小修正 AAOS `AGENTS.md`；不让 WORK-LAB 同步器写本仓。当前状态 `NEEDS_CURRENT_EXTERNAL_READBACK`。 |
| `I7`、`F01`：归档中 AAOS 八文件只是规则切片，三仓全树和 GPT 全历史未审完 | 当前 AAOS Authority/R6/M0 已现场读取；外部材料锚点是 WORK-LAB 固定 SHA，不是本仓今日 main | 将该材料用作线索，不据此改变当前完成状态。后续每项回到本仓源码、合同与受测 SHA 核对。 |
| `D01`、`D02`、`P00`、`P06`：保留三项目独立 owner，去重规则并明确 coverage | 本仓已有 Authority 索引和唯一 R6/M0 执行入口 | 在后续 AAOS 任务中复用现有索引；新增来源时登记实际覆盖、未读项和冲突，不建新的总账。 |
| `P05`、`P09`、`D15`：增量仓库卫生和输出归属 | 本仓已有 `DIRECTORY_AUTHORITY.yaml` 与 `.project-local` 开发运行根 | 仅作为未来生成器/CI 改动的候选，要求精确写集与可回退证据；不因本材料新建清理任务。 |
| `D08`、`D09`、`P07`：目录、重复资产和缓存迁移 | 用户本轮明确停止清理，不再删除、迁移或整理缓存、历史文档及数据库 | `PAUSED_BY_CURRENT_USER_SCOPE`。本轮只保留原文索引，禁止执行相关动作。 |
| `D12`、`P15`：新模型和软件逐版本资格化 | R6 A11 与 M0 的模型能力边界仍需真实运行证据 | 后续按项目既有模型/工具合同评估，版本/可用性未知保持 UNKNOWN；不自动下载、安装或切换模型。 |
| `P16`：各仓独立交付并按精确 SHA 验证 | 本轮用户要求 AAOS 任务公共修改上传并回读 CI；R6 release 冻结 | 对本仓任务分支执行精确 SHA 交付；这份材料不授权 merge/release，也不把旧 CI 当当前验证。 |
| `F19`：WORK-LAB 边界门禁只检查标记、seam 和 manifest | 属于外部仓自身审计；不足以证明本仓代码/数据库边界 | AAOS 后续真实接口验收仍以 Rust Core 单写者、Desktop Supervisor 和本仓测试为准，不直接改外部门禁。 |

## 纳入本项目后续任务的方式

本切片作为 R6/M0 既有执行入口的待评估输入，见 `docs/current/R6-EXECUTION.md` 的 2026-10-01 外部输入登记。后续执行者先验证当前 Authority、源码与接口，再决定是否形成具体切片。它不改变 `docs/current/R6-STATE.json`，不把 `PROPOSED_NOT_EXECUTED` 提升为 `TESTED_LOCAL`，不启动已停止的清理工作。

## 来源局限

两份 JSON 都自报 `read_only`/未修改仓库，三项目方案称其固定 WORK-LAB 锚点不足以证明三个仓库当前全树或 Windows 运行；WORK-LAB 审计也把八份 AAOS 归档文件限定为规则切片。HTML 与 JSON 对领域 owner、旧 AGENTS 引用和证据不足相互印证，但相同来源链不构成独立运行验收。HTML 节点摘录供定位，不代替原 HTML 的完整上下文。
