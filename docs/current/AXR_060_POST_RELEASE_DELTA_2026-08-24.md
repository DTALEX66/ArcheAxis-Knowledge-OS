# AXR-060 发布后 exact-SHA 差异审计（2026-08-24）

## 结论

`v0.6.10` 的发布闭环为 `PASS_RELEASE`；原始最小可信闭环任务包整体仍为
`PARTIAL`。本文件取代把 2026-08-23 分支交接中的“未合并 / 未执行 CI”直接
当作当前事实的做法：所有下列提交已是当前 main 的祖先，并已由发布 SHA 的全量
CI 覆盖。

| 证据层 | 当前事实 |
| --- | --- |
| 发布源码 | `v0.6.10` → `3428a65cf6445918365f76b114cc11630d9640bb` |
| 源码树 | `828ffe3039b65d1b2fccf9c9348233342818cea1` |
| Full Qualification | CI `32665051446`，success（含 `a0-gates`、Windows build 与 installer lifecycle） |
| 公开发布 | Release `32665840172`，success；9 项资产、三种分发生命周期和全资产工作流读回通过 |
| 发布后文档 | `main@675029cfda4271e651d19cb546a110569173022c`；CI `32666694617`，success |

发布收据见 [`../../reports/release/v0.6.10/release-evidence.json`](../../reports/release/v0.6.10/release-evidence.json)。

## 已进入发布线、但不应过度升级的切片

| 任务 | main 中的实现提交 | 当前层级 | 仍未关闭 |
| --- | --- | --- | --- |
| AXR-060-103 首次启动 | `6f5ef88` | `IMPLEMENTED_LOCAL` + `CI_VERIFIED_EXACT_SHA` | 干净安装机的向导点击 Golden Journey。 |
| AXR-060-302 append-only | `b528d90` | `IMPLEMENTED_LOCAL` + `CI_VERIFIED_EXACT_SHA` | 四类账本的全路径 SQL 白名单与迁移回滚矩阵。 |
| AXR-060-303 Bundle/Version | `64f72e0` | `IMPLEMENTED_LOCAL` + `CI_VERIFIED_EXACT_SHA` | 跨库 RawAsset→Bundle→KnowledgeVersion 的真实 UI/E2E。 |
| AXR-060-401 统一写客户端 | `55c2899` | `IMPLEMENTED_LOCAL` + `CI_VERIFIED_EXACT_SHA` | 所有未来 React 写路由的 scope/幂等覆盖与离线投影。 |
| AXR-060-203 raw-first Web | `9cd8608` | `TESTED_LOCAL` + `CI_VERIFIED_EXACT_SHA` | 隔离网络的真实 HTTP 证据与页面级损失评估。 |
| AXR-060-403 Dock | `cab4095` | `IMPLEMENTED_LOCAL` + `CI_VERIFIED_EXACT_SHA` | Inspector conflict/rights/full history，真实取消与错误详情合同。 |

“已进入 main”仅证明源码与该 SHA 的 CI；不证明干净安装机、真实旧数据迁移或无障碍人工矩阵。

## 仍未关闭的最短执行顺序

1. **P0 / 可代码关闭**：为 Evidence、Learning、Provenance、Rights 四类追加表建立路径级 SQL 白名单，补向前迁移、回滚与重启读回矩阵（AXR-060-302 / B04）。
2. **P0 / 可代码关闭**：补 Bundle/Inspector 的 conflict、rights、version-history 读模型；只在后端存在明确取消状态机后启用 Dock 取消按钮（AXR-060-303/403）。
3. **P1 / 可代码关闭**：Tier A 固定 fixture 结构矩阵、键盘/焦点/reduced-motion 与长列表行为；高 DPI/读屏保留独立人工运行证据（AXR-060-202/404）。
4. **外部证据门**：干净 Windows 的四库→Golden Journey→导出/导入→升级→卸载保留→重装回读（B10 / AXR-060-604）。不能用 CI 安装生命周期替代。
5. **外部数据门**：真实用户旧数据迁移只在 Owner 单独授权样本后执行；不读取或迁移私人用户目录。

## 发布与版本纪律

- 后续功能先在 `main` 汇集，采用风险选择 CI；不为每个修复创建新 tag 或安装包。
- 只有以上 P0/P1 批次形成可交付候选时，再创建一个新的语义版本并执行一次 Full Qualification/Release。
- `v0.6.10` tag 和公开资产不可改写；发布后文档提交与 tag 指向不同 SHA 是正常的证据分层。
