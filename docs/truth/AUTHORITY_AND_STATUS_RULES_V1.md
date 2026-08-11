# Authority & Status Rules — 权威与状态规则 V1（AXW-1200/1202）

> 状态：**binding（定死）**。权威优先级与禁止裁决不可漂移。

## 1. 权威优先级

1. Owner 最新明确决策与本任务包
2. 当前已验证的 main、安装器、Release、CI、分支和真实 fixture 证据
3. 本任务包创建的 Product Truth / Capability Atlas / Requirement Trace / Scope Ledger / Task Graph
4. 既有 Future Blueprint、Final Master TaskPack v4、历史审计、开源研究池
5. 旧名称、旧版本 README、Issue/PR、模型总结和界面文字

历史资料只能解释来源，不能覆盖本任务包的命名、边界、能力保留和状态规则。

## 2. 禁止的错误裁决

- 用当前未实现的事实删除/降级已确认的长期能力
- 用未来能力冒充当前安装版已支持
- 用"系统级"恢复 `OS`/`Runtime`/`Agent Platform`/`Machine`/`Evolution` 为产品名或一级导航
- 用"兼容 Obsidian"把项目写成 Obsidian 克隆，或把第三方品牌写进日常 UI
- 用 HERMES、WORK-LAB、OpenHuman、Codex 等外部工具替代 ArcheAxis 产品主体
- 用模型输出、OCR/ASR 置信度、内部可信度分数或单一网页替代事实核验
- 以整理为名删除历史任务、能力、候选、需求或名称映射

## 3. 状态定义（roadmap_state）

| 状态 | 含义 |
|---|---|
| `critical_now` | 当前 Release 必须优先完成 |
| `core_next` | 当前 Release 的后续核心 |
| `formal_later` | 长期正式能力，稍后激活 |
| `experimental_later` | 长期实验能力，稍后激活 |
| `deferred_retained` | 延期但永久保留 |
| `retired_positioning` | 仅历史定位记录 |
| `rejected_with_record` | 有记录地拒绝 |

## 4. authority_status

| 状态 | 含义 |
|---|---|
| `binding_core` | 绑定核心能力，不可删除 |
| `binding_long_term` | 绑定长期能力，不可静默删除 |
| `exploration` | 探索能力，非承诺 |
| `retired` | 已退休，仅记录 |

## 5. 冲突处理

若当前仓库事实与任务包冲突：仓库只能否定"当前已实现"，不能删除 Owner 已确认的长期能力。记录冲突并要求 Owner 裁决。

## 6. 修订记录

| 版本 | 日期 | 变更 | 授权 |
|---|---|---|---|
| V1 | 2026-08-12 | 权威规则冻结（AXW-1200/1202） | Owner 任务包 |
