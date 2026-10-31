# Canvas 编辑后文本节点导出

2026-10-29。接续唯一执行记录中的具名 Core 缺口；不新增任务队列，不恢复 UI 构建。

## 问题与结果

原 `GET /api/v1/documents/:id/export` 仅支持 `markdown` / `obsidian`；原始 `.canvas` 的字节导出不能表达已经保存的编辑内容。新增 `format=canvas`，从 Document 固定 `source_id` / `source_revision` 对应的原始 CAS Canvas 取得结构，用当前 Document 明确映射的文本替换对应 text 节点，生成 `document.canvas` 与版本绑定的 `manifest.json`。

规范依据为 [JSON Canvas 1.0](https://jsoncanvas.org/spec/1.0/)。原件、节点和边的数组顺序、坐标、未知扩展字段、file/link/background 声明保留；不访问这些声明指向的目标，不打包附件。

## 有限合同

- 当前每个顶层 paragraph/codeBlock 以 `attrs.canvas_node_id` 唯一映射原 text 节点。缺失、重复、额外、指向非 text 节点或不支持的正文结构均返回 400，不能按顺序猜测或静默恢复旧文字。
- 导出范围显式为 `TEXT_NODE_PLAIN_TEXT_ONLY`。当前可见文本及 hardBreak 更新到 Canvas；富文本 marks、链接 href 和代码语言不转成 Markdown 标记，损失清单逐项说明，完整 editor JSON 仍在 manifest 内。它不是富文本保真或原应用全部编辑往返。
- 本轮不增加、删除或移动 Canvas 节点；几何与连接来自原始结构。当前 UI 尚无自动生成此映射的消费者，不宣称界面已支持编辑后导出。
- 原 source revision 与 CAS SHA、文件大小、节点/边预算、必备字段和关系均校验。普通保存、版本冲突、markdown/obsidian 导出沿原合同；不增加外部审批、网络或模型前提。

## 实现与验证

写集仅 `crates/archeaxis-api/src/documents.rs`、`crates/archeaxis-domain/src/lib.rs`、新 `crates/archeaxis-domain/src/canvas_export.rs` 和新 `crates/archeaxis-api/tests/document_canvas_export.rs`。

canonical `canvdom1` 的 3 项 domain 测试、`canvapi1` 的 2 项新 Canvas / 11 项原文档草稿 / 2 项原可移植包 API 测试全部通过；两次 `source_consistent=true`，执行时公共源码差异为 `9f962658a2fd8ea89ae952850c61063f793d952be302c8f14bcfa88cae6cd700`。覆盖当前中文与换行、未知字段/顺序、原件未变、409 冲突、歧义拒绝、普通保存独立、link/bold/code language 的明确损失，以及重新打开 Router 和独立 Document package 恢复后再导出。

这些是本地 domain/API 集成检查。Router 重开不等于操作系统进程冷启动；独立 Document package 恢复不等于全部工作区或所有外部引用依赖恢复。修补前 Host/Core 的 `53a83f…e9708` 安装包没有包含这些新源码，不移绑其历史 c453＋6b30 编译来源或 a66 runtime 包装来源。新 Core 的正式构建、身份、安装与原生消费者仍待后继资格；本轮未编译 UI、提交、推送或发布。

回退时只撤销本增量的 Canvas 分支、模块注册及新增文件；不重置或覆盖原有 dirty 文件中的其他改动，不更改已有数据库或原始 CAS。
