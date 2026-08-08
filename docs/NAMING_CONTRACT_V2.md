# ArcheAxis Workspace Naming Contract v2

> 状态：`active / pre-release`
> 生效范围：ArcheAxis OS 本仓库的产品、UI、文档、OpenAPI 和发布显示层。
> 不改变：GitHub 仓库名、Python 分发兼容名、Tauri bundle identifier、既有数据目录和历史 Release。

## 1. 唯一产品身份

| 层级 | canonical value | 规则 |
| --- | --- | --- |
| 品牌 | `ArcheAxis` / `元枢` | 品牌层，可用于图标和品牌说明 |
| 对外产品 | `ArcheAxis Workspace` / `元枢工作台` | 唯一用户主名称 |
| 当前频道 | `ArcheAxis Workspace Alpha` | 仅在真实 Alpha 资格完成后使用；当前仍是 development |
| 对外描述 | `本地优先、证据驱动的 Human–AI 学习与知识工作台` | 描述，不是第二品牌 |
| 当前兼容阶段 | `Obsidian-compatible Workspace` | 阶段名，不是独立产品名 |

`元枢·观心` 不再作为产品显示名；如未来需要，只能作为用户自定义 workspace/profile 模板名，当前不进入默认 UI。

## 2. 技术兼容身份

以下名称保留为技术和历史兼容身份，不得出现在普通用户主导航、首页标题或产品定位首句：

- `Cognitive-Loop-OS`：Git 仓库、远端 URL、历史文档和内部 project root。
- `cognitive-loop-os`：Python/package 与现有发布兼容 ID。
- `cognitive-os`：既有 CLI/API/配置兼容别名；不得新建同名产品表面。
- `ArcheAxis OS`：既有 desktop protocol、installer migration 和历史 Release 的兼容身份；新用户显示层使用 `ArcheAxis Workspace`。
- `com.archeaxis.cognitive-workspace`：Tauri identifier，未经迁移、升级、卸载和回读证据不得修改。

## 3. 词汇分类

机器可读 registry `config/product-naming-registry.yaml` 将词分为：

- `display`：可以进入普通用户界面；
- `legacy`：只能出现在兼容说明、迁移文档、历史证据或技术边界；
- `alias`：可被旧入口读取，但不得作为新字段/新页面的 canonical value；
- `forbidden_default`：不得作为产品主标题、默认导航或当前阶段首句。

新 API、数据库字段、事件和配置继续使用 `config/naming-registry.yaml` 的 service ID；产品显示名只在 presentation boundary 解析。

## 4. 迁移和回滚规则

1. 先更新 display 文案、OpenAPI title/description、README、release manifest 和 UI；不做全仓字符串替换。
2. 旧技术 ID 必须继续可读；新增入口如需新品牌名，必须提供旧名兼容读取和明确迁移说明。
3. GitHub 仓库改名、Python distribution 改名、Tauri identifier 改名和数据目录改名分别处理，不在本合同中隐式执行。
4. 任何 persisted value、安装路径或协议字段的改名，都必须先有 source→target 映射、迁移、回滚、升级/卸载回读和 exact-SHA CI 证据。
5. 在 `0.5.0` 发布前，必须完成一次命名扫描，确认普通用户默认入口只显示 `ArcheAxis Workspace / 元枢工作台`，并附带兼容 ID 清单。

## 5. 当前阶段真相

本合同不宣称产品已完成。当前阶段仍是 `foundation / not user-closed`：Obsidian Vault、Markdown 和 JSON Canvas 是首个兼容纵切；打开、编辑、附件、增量冲突、Canvas 回读和 Windows/Tauri 全闭环完成前，不得使用“全面兼容”“双向兼容”或公开 Alpha 完成等表述。
