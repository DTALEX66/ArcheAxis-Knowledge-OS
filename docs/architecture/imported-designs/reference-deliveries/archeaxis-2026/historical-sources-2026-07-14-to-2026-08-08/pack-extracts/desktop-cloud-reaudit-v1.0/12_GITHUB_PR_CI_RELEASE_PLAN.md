# GitHub 分支、PR、CI 与发布计划

## A1

分支：

`feat/archeaxis-desktop-a1-violet-core`

PR 标题：

`feat(workspace): establish ArcheAxis Desktop Violet Core shell`

PR 内容必须包含：

- 基线 SHA；
- 不变的后端边界；
- 页面映射；
- 浏览器真实闭环；
- 无内部 ID；
- 无假 Agent；
- 截图；
- 运行过的门禁；
- 已知限制；
- A2/A3 明确未完成。

## Commit 建议

1. `test(workspace): define desktop shell truth regressions`
2. `refactor(workspace): organize current UI contracts`
3. `feat(workspace): add Violet Core desktop shell`
4. `test(workspace): prove responsive inspector and activity dock`
5. `docs(workspace): record desktop A1 boundaries`

只有测试需要时才拆分；避免大量无意义小提交。

## CI

现有 A0 聚合门禁必须全部通过：

- test
- lint
- wheel-smoke
- browser-smoke
- windows-runtime-smoke
- desktop-shell
- a0-gates

## 发布

A1 合并不等于公开 Alpha。

禁止：

- 把 Release Manifest 改成 released；
- 把 public_installer 改成 available；
- 宣称完整 Agent Desktop；
- 宣称多 Agent；
- 宣称通用 Planner。

只有正式冻结 Release Train，才注入 exact commit/tree/CI。
