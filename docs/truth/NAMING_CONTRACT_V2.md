# Naming Contract V2 — 命名契约 V2（AXW-1302）

> 权威来源：`ArcheAxis_Knowledge_Naming_Audit_and_HERMES_TaskPack_v1_2026-08-12`（只读审计交付）
> 状态：**binding（定死，不可漂移）**。更新需 Owner 明确决策 + 本契约修订记录。
> 关联：`NAMING_CONTRACT_V1.md`（已 SUPERSEDED，仅历史）、`AXW-NAMING-2026-08-12-v1` 任务图
> 审计基线：`DTALEX66/archeaxis-workspace` @ `2694d86`

## 0. 变更摘要（V1 → V2）

| 项 | V1（SUPERSEDED） | V2（当前 binding） |
|---|---|---|
| 对外英文产品名 | ArcheAxis Learning Workspace | **ArcheAxis Knowledge** |
| 对外中文产品名 | 星轨学习工作台 | **星环知识平台** |
| 内部工作台视图 | （未区分） | **ArcheAxis Learning Workspace**（仅内部视图） |
| 品牌词根 | ArcheAxis | ArcheAxis（不变） |
| 机器身份 | archeaxis-workspace | archeaxis-workspace（不变） |

V1 由 Owner 决策（2026-08-12）降级为历史记录；历史文档保留旧名作 Legacy 语境。

## 1. 固定命名表（唯一权威）

| 层级 | 固定名称 | 规则 |
|---|---|---|
| 品牌词根 | `ArcheAxis` | 固定拼写；禁止任何变形（Archeaxis/Arche Axis/Arche-Axis/ArcheAXIS 等） |
| 对外英文产品名 | `ArcheAxis Knowledge` | README 标题、Release、商店、About、安装器、窗口标题、公开版本——禁止被 `Learning Workspace`/`OS`/`Runtime`/`Platform`/`Star` 替代 |
| 对外中文产品名 | `星环知识平台` | 中文 UI 品牌区、中文文档、官网、商店、白皮书；禁止对外裸用"星环" |
| 中文首次出现 | `星环知识平台（ArcheAxis Knowledge）` | 中文正式文档第一次出现强制使用完整形式 |
| 内部工作台视图 | `ArcheAxis Learning Workspace` | 软件内部工作台 header、Tab、视图元数据；禁止用于 README 标题、Release、安装包、About 主产品名、商店名 |
| 标准版本展示 | `ArcheAxis Knowledge vX.Y.Z` | Release、About、更新日志、构建产物；禁止显示 `ArcheAxis OS v...` 或 `Learning Workspace v...` |
| 项目状态 | `Personal Research Project / 个人研究项目` | 不等同于许可证；许可证独立声明 |
| 固定口号 | `同一份可信知识，人学得更深，AI 用得更准。` | 不允许被旧宣传语替代 |

## 2. 技术身份（目标契约）

| 技术对象 | 标准值 | 当前事实 | 处理方式 |
|---|---|---|---|
| GitHub 仓库 | `DTALEX66/archeaxis-workspace` | ✅ 已完成 | 更新所有活跃旧链接；历史链接不改 |
| Machine / distribution ID | `archeaxis-workspace` | ✅ 已完成 | 保持 |
| Python distribution | `archeaxis-workspace` | ✅ 已完成（#131） | 保持 |
| CLI | `archeaxis` | ✅ 已完成（#131） | banner 改为对外产品名 |
| Python 根导入包 | `archeaxis` | ⏳ 未实现（app/shared/knowledge_base） | 兼容壳→逐域迁移（AXW-1313/1314）；禁止一次性移动全部模块 |
| 环境变量前缀 | `ARCHEAXIS_*` | 🚧 已迁移（#136），COGNITIVE_* 保留回退 | 新前缀 canonical；旧名至少保留两个稳定版别名 |
| 配置命名空间 | `archeaxis.*` | 仅蓝图 | 版本化迁移与旧键回读 |
| URI | `archeaxis://` | 未实现 | 先注册/解析测试，再公开 |
| API 根 | `/api/v1/` | 🚧 已加双路径（#136） | canonical 路由 + 旧 `/workspace/api/*`、`/kb/*` 兼容 |
| 事件 | `archeaxis.<domain>.<event>.v1` | 未实现 | 双发/双读迁移；数据库旧事件不可重写 |
| Bundle ID 目标 | `com.archeaxis.workspace` | 🚧 已迁移（#136，无外部安装） | 完成安装/升级/卸载/数据目录验证（AXW-1307） |
| Windows 数据目录目标 | `%LOCALAPPDATA%\ArcheAxis\Workspace` | 当前由旧 Tauri identifier / `.hermes` 路径决定 | 备份、迁移、完整性与重启回读后再切换（AXW-1311） |
| 可执行文件 | `ArcheAxis.exe` | 需从真实 bundle 回读 | 保持或在安装器阶段校准 |
| 后台服务 | `archeaxis-local-service` | 当前以 Core/runtime 语义为主 | 新显示名；旧进程/协议兼容 |
| 任务 ID | `AXW-NNN` | 已使用 | 保持 |

## 3. 术语边界

- `Library` 只作为 UI 的"资料库"；不得新建顶层 Python 包 `library`。
- `Runtime` 可作为纯技术实现词（如 `runtime_entrypoint.py`），但不得成为产品名、品牌、一级领域包或可见导航标签。
- `Agent` 可作为外部适配器或历史技术概念；不得成为首页或一级产品空间。
- `Obsidian` 只允许在适配器标识、兼容矩阵、导入导出设置和历史文档出现；主 UI 应使用 `Vault / Markdown / Canvas 兼容` 等中性能力名。
- `HERMES`、`Codex`、`WORK-LAB` 是外部开发/验证工具，不是 ArcheAxis 产品模块。隐藏的工具适配配置可过渡保留，但必须标注 owner、边界和退役策略。
- `ArcheAxis · Star`、`ArcheAxis Star`、`Star` 品牌副标题均已废止（当前 0 次，保持删除状态）。

## 4. 中文风险控制

- 禁止"星环"裸用为独立对外品牌/商店名/一级标题/无障碍标签。
- 公开中文必须用完整词"星环知识平台"。
- 图标可无文字；窗口标题、无障碍标签、下载名、元数据必须用完整产品名。
- 原"元枢""元枢工作台"只留在历史、迁移与兼容说明中。

## 5. 历史名称映射（Legacy/Migration only）

| 旧名称 | 现状 | 允许语境 |
|---|---|---|
| ArcheAxis-Knowledge-OS | 原仓库技术身份（已改名 archeaxis-workspace） | Git/CI/包名历史兼容 |
| 星轨学习工作台 / ArcheAxis Learning Workspace | V1 产品名（已降级为内部视图） | 内部视图、历史、迁移、兼容说明 |
| 元枢 / 元枢工作台 | 已弃用 | 历史、迁移、兼容说明 |
| ArcheAxis OS | 旧产品名（曾用于 GitHub 描述/安装器） | 历史记录、测试用例（拒绝场景） |

## 6. 修订记录

| 版本 | 日期 | 变更 | 授权 |
|---|---|---|---|
| V1 | 2026-08-12 | 首次冻结（任务包 AXW-1201） | Owner 任务包裁决 |
| V1.1 | 2026-08-12 | §4 迁移状态更新（#131 Step 1） | Owner 授权 |
| V2 | 2026-08-12 | 新体系：对外 ArcheAxis Knowledge/星环知识平台；Learning Workspace 降为内部视图（AXW-1302） | Owner 明确决策（2026-08-12） |
