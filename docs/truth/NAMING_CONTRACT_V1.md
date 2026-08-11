# Naming Contract — 命名契约 V1（AXW-1201）

> 权威来源：`ArcheAxis_Learning_Workspace_System_Blueprint_and_HERMES_Update_TaskPack_v1_2026-08-11`
> 状态：**binding（定死，不可漂移）**。更新需 Owner 明确决策 + 本契约修订记录。
> 关联：`PRODUCT_IDENTITY_V2.md`、`AUTHORITY_AND_STATUS_RULES_V1.md`

## 1. 固定命名表（唯一权威）

| 层级 | 固定名称 | 规则 |
|---|---|---|
| 唯一主品牌 | `ArcheAxis` | 固定拼写；禁止 `Archeaxis`/`Arche Axis`/`Arche-Axis`/`ArcheAXIS` 等变形 |
| 英文完整产品名 | `ArcheAxis Learning Workspace` | README、Release、安装器、About、英文文档、版本展示 |
| 中文完整产品名 | `星轨学习工作台` | 中文 UI、中文文档、国内展示 |
| 中文首次出现 | `星轨学习工作台（ArcheAxis Learning Workspace）` | 中文首次提及时强制使用 |
| 标准版本展示 | `ArcheAxis Learning Workspace vX.Y.Z` | 公开版本文字；版本数值单独存储 |
| 项目状态 | `Personal Research Project / 个人研究项目` | 不等同于许可证；许可证独立声明 |
| 固定短句 | `同一份可信知识，人学得更深，AI 用得更准。` | 不允许被旧宣传语替代 |

"唯一"是内部命名契约，不是全球排他性声明。不得写"全球唯一品牌"或"已注册商标"。

## 2. 中文风险控制

- 禁止"星轨"裸用为独立对外品牌/商店名/一级标题/无障碍标签
- 公开中文必须用完整词"星轨学习工作台"
- 图标可无文字；窗口标题、无障碍标签、下载名、元数据必须用完整产品名
- 原"元枢""元枢工作台"只留在历史、迁移与兼容说明中

## 3. 历史名称映射（Legacy/Migration only）

| 旧名称 | 现状 | 允许语境 |
|---|---|---|
| Cognitive-Loop-OS | 当前仓库技术身份（GitHub repo 名） | Git/CI/包名历史兼容 |
| 元枢 / 元枢工作台 | 已弃用 | 历史、迁移、兼容说明 |
| ArcheAxis OS | 旧产品名（曾用于 GitHub 描述） | 历史记录 |

## 4. 技术身份目标（planned，不盲改）

| 对象 | 目标标识 | 迁移状态 |
|---|---|---|
| GitHub 仓库 | `DTALEX66/archeaxis-workspace` | planned（需 Owner 授权） |
| Machine ID / dist | `archeaxis-workspace` | planned |
| Python 根导入 / CLI | `archeaxis` | planned |
| 环境变量 | `ARCHEAXIS_*` | planned |
| 配置/URI | `archeaxis.*` / `archeaxis://` | planned |
| API 根 | `/api/v1/` | planned |
| 事件 | `archeaxis.<domain>.<event>.v1` | planned |
| Tauri Bundle ID | `com.archeaxis.workspace` | planned |
| Windows 数据根 | `%LOCALAPPDATA%\ArcheAxis\Workspace` | planned |
| Windows 可执行文件 | `ArcheAxis.exe` | planned |
| 本地服务 | `archeaxis-local-service` | planned |

分别迁移，禁止批量搜索替换，禁止无迁移/回滚证据改名。

## 5. 修订记录

| 版本 | 日期 | 变更 | 授权 |
|---|---|---|---|
| V1 | 2026-08-12 | 首次冻结（任务包 AXW-1201） | Owner 任务包裁决 |
