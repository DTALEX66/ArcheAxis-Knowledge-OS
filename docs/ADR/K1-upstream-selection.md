# K1 — P0 上游选型 Decision Record

> 审计基线：`main@2698736251bf50364e5ab304090b0f4d787cb1bc`
> 日期：2026-08-07
> 性质：K1 P0 上游选型 + 复用决策记录。**不把 demo/候选标成产品完成**；本项目只选型并登记，真正的 Compatibility Kernel（K2）与 Obsidian C3（K3）在后续 TaskPack 实现。
>
> 技术栈基线：Python 后端（FastAPI/SQLite）+ Tauri (Rust) 桌面壳。复用阶梯：直接依赖 → 官方 SDK/API/CLI → fork/vendor → Adapter/sidecar → 自研。

## 0. 决策摘要

| 组件 | 首选 | 许可证 | 活跃度 | 复用模式 |
|---|---|---|---|---|
| Markdown AST / 解析 | `markdown-it-py` + `mdit-py-plugins` | MIT | 2026-08 | 直接依赖 |
| YAML frontmatter roundtrip | `ruamel.yaml`（round-trip 模式） | MIT | 活跃 | 直接依赖 |
| JSON Canvas | `obsidianmd/jsoncanvas`（规范 + 样例） | MIT | 2026-07 | 规范参照 + 自研实现 |
| FSRS 调度 | `py-fsrs` | MIT | 2026-07 | 直接依赖 |
| 虚拟文件树 / 文件系统抽象 | 自研轻量层（Adapter） | — | — | 自研（内部模型） |
| Reader/Editor 渲染 | `markdown-it-py` 渲染管线（Tauri WebView 呈现） | MIT | — | 直接依赖 |
| Attachment 预览 | 系统 + WebView2（复用已装 `desktop-runtime-v1`） | — | — | Adapter |

**原则**：先复用成熟、许可兼容、活跃维护的上游；YAML 与 Markdown 用 roundtrip/保真能力；JSON Canvas 用官方规范自研（无必要不引入重依赖）；文件树与编辑内核自研为 Adapter（因需贴合 OS 的 governed 数据模型）。

---

## 1. Markdown AST / 解析器

### 候选核验（GitHub API，只读）

| 候选 | 许可证 | 最后推送 | Stars | 判定 |
|---|---|---|---|---|
| `remarkjs/remark` + `syntax-tree/mdast` | MIT | 2026-07 / 2026-02 | 8974 / 1463 | 强大但 JS 生态；Tauri 前端可用，后端 Python 复用度低 |
| `micromark/micromark` | MIT | 2025-05 | 2199 | fast 但纯 JS |
| `executablebooks/markdown-it-py` | MIT | 2026-08-03 | 1350 | **Python 首选**，CommonMark + 扩展 |
| `executablebooks/mdit-py-plugins` | MIT | 2026-08-03 | 44 | **Python**，Obsidian 风格扩展（frontmatter/attrs） |
| `lezer-parser/markdown` | MIT | archived | 149 | 已归档，不采用 |

**决策**：Python 后端用 `markdown-it-py` + `mdit-py-plugins`（MIT、活跃、CommonMark 兼容、支持 frontmatter/属性扩展）。Tauri 前端渲染可选 `markdown-it`（JS 版）但需在 K3 时评估是否共享 AST；后端是主 truth source。

### Obsidian extensions 覆盖

`mdit-py-plugins` 提供：front_matter、attrs、deflist、footnote、tasklist、table。Obsidian 的 wikilink/embed/alias 需在 K3 通过自定义插件扩展（登记为 Adapter 计划，非本轮实现）。

---

## 2. YAML frontmatter roundtrip

| 候选 | 许可证 | 判定 |
|---|---|---|
| `yaml/pyyaml` | MIT | 不保留注释/顺序/类型保真，**不满足 roundtrip** |
| `ruamel.yaml`（round_trip） | MIT | **首选**：保留注释、键序、多行、类型 |

**决策**：YAML frontmatter 用 `ruamel.yaml` 的 round-trip loader（保留注释与键序）。若 vendoring 成本高，退而评估 `strictyaml`，但 roundtrip 保真是硬需求。

---

## 3. JSON Canvas

| 候选 | 许可证 | 判定 |
|---|---|---|
| `obsidianmd/jsoncanvas` | MIT | **官方规范 + 样例**：v1.0 结构（nodes/edges/connections），2026-07 活跃 |
| 第三方 JS canvas 库 | 视具体 | 引入重依赖风险；Tauri 前端已有渲染基础 |

**决策**：以官方 `jsoncanvas` 规范为**数据契约**，K3 自研 import/export/semantic-diff 实现（JSON 结构简单，无需引入第三方渲染库）。此为上阶梯 4（自研）但**有官方规范锚定**，非重复造轮子。

---

## 4. FSRS 调度

| 候选 | 许可证 | 活跃度 | 判定 |
|---|---|---|---|
| `open-spaced-repetition/py-fsrs` | MIT | 2026-07-29 | **Python 首选**，官方 FSRS 算法 |
| `open-spaced-repetition/ts-fsrs` | MIT | 2026-08-05 | Tauri 前端可选 |
| `fsrs4anki` | MIT | 2026-07-28 | 参考实现，非直接依赖 |

**决策**：Python 后端用 `py-fsrs`（MIT、官方算法、活跃）。Card/Review 调度数据模型基于 FSRS 状态（due/state/stability）。

---

## 5. 虚拟文件树 / 文件系统抽象

**候选**：`virtual-file-tree` 类库少且贴合度低。**决策：自研轻量 Adapter**——封装 Vault 文件树遍历、相对路径规范化、watch/scan，映射到 OS 的 governed 数据模型（RawAsset → VaultFile）。这是 K2 的核心，不引入外部重依赖。

---

## 6. Reader / Editor

**决策**：后端用 `markdown-it-py` 渲染 Markdown → HTML，Tauri WebView 呈现。编辑器内核待 K4 评估（可选 `@codemirror/*` JS 或轻量 contenteditable），**本轮不锁定**——先保证 Reader（读）与 roundtrip（读写保真）闭环，Editor 交互 K4 决策。

---

## 7. Attachment 预览

**决策**：复用已安装的 `desktop-runtime-v1`（WebView2）与系统程序处理；图片/PDF 预览在 K4 用 WebView2 原生能力。登记为 Adapter，非本轮实现。

---

## 8. 版本固定与供应链

所有直接依赖在进入 K2 时固定 exact commit/tag + SPDX hash，遵循仓库依赖固定政策：

```text
PyPI: >=floor,<next_major
Git:  40-char commit SHA
```

选型未冻结 exact commit——在 K2 实际引入依赖时固定，并更新 `uv.lock` + release-manifest dependency digest。

---

## 9. 非目标 / 延期

- 不引入完整 Obsidian 私有 UI/源码（审计明确）
- 不做通用 Agent Runtime / 多 Agent / Marketplace
- 不做复杂 affected-test 图谱（未达触发阈值）
- Editor 交互层、Canvas 渲染 UI、Attachment 全预览 → K4

---

## 10. 验收（本 TaskPack 的闭环证据）

本 TaskPack 只产出**选型 ADR**（本文件），不宣称组件已实现。K1 的完成证据是：

- [x] 候选经 GitHub API 只读核验（license/活跃度/维护状态）
- [x] 每个 P0 组件有明确首选 + 复用模式 + 拒绝理由
- [x] 复用阶梯遵循（直接依赖 > Adapter > 自研）
- [x] 非目标明确（不把选型当产品完成）

**K1 不实现功能**；K2（Compatibility Kernel）将依据本 ADR 落地数据模型与 Adapter，届时固定 exact commit 并更新锁。

---

## 11. 最小 spike 验证（K1 完成证据）

在 Hermes venv（含候选库）执行只读 spike，验证选型可行性：

**Spike 1 — YAML frontmatter roundtrip（`ruamel.yaml`）：**
```text
注释保留: True   键序保留: True   多行块保留: True   值正确: True
```
结论：`ruamel.yaml` round_trip 满足 frontmatter 保真（注释/键序/多行/类型）。PyYAML 不满足（不保留注释）。

**Spike 2 — Markdown AST 解析（`markdown-it-py`）：**
```text
heading_open: True   list_item_open: True   inline: True
```
heading/list 顶层 token 正确；加粗/行内代码在 `inline.children`（markdown-it-py 标准行为，非缺陷）。AST 可解析。

**Spike 3 — frontmatter 结构分离：**
```text
frontmatter: {'title': 'T'}   正文: 正文
```
`---` 分隔的 frontmatter 可正确剥离并 roundtrip 解析。

**依赖决策（K2 引入时执行）：**
- 项目当前仅 `pyyaml>=6.0`（无 roundtrip）+ `markitdown`（内部带 markdown-it-py 但未直接声明）。
- K2 需新增：`ruamel.yaml`（roundtrip）、`markdown-it-py` + `mdit-py-plugins`（AST）。
- 新增须遵循依赖固定政策：`>=floor,<next_major` + `uv lock` + release-manifest digest 更新。
- 本 TaskPack 只验证可行性，**未新增依赖、未改动产品代码**。

**Spike 脚本**：`.hermes/task-runtime/k1-spike.py`（项目忽略目录，非交付产物）。
