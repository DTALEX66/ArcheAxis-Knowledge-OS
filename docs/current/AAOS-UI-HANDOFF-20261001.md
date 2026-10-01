# AAOS 正式 UI 与真实后端接手交接（2026-10-01）

状态：`PARTIAL / TESTED_LOCAL`。当前 Authority 是项目配置索引、R6 不变任务包与 M0 优先级覆盖；本记录不替代它们。清理任务已由用户停止，缓存、历史文档、数据库和待核恢复包保持原样。

## 本轮完成与证据

- 母版逐页覆盖、资产、接口及验收差距见 `AAOS-UI-COVERAGE-MATRIX-20261001.md`、`AAOS-UI-MASTER-ASSET-AUDIT-20261001.md`、`AAOS-UI-ASSET-MANIFEST-20261001.json`、`AAOS-UI-BACKEND-MAP-20261001.md`。B10 母版无独立配图包，原版 HTML 内嵌 SVG/CSS；Formal 已有资产与 Green 未提交资产分别标明。
- 9 月 30 日 ZIP 只有任务文档、无可部署代码/图片；将其中规划与当前 Authority 分开记录在覆盖矩阵。
- 用户指定的四份 10 月 1 日外部文件已只读审计。`../history/external-inputs/2026-10-01/AAOS-ECOSYSTEM-AUDIT.md` 与 `AAOS-ECOSYSTEM-EXTRACT.json` 是本项目 AAOS 切片的归档副本和来源哈希索引。`R6-EXECUTION.md` 仅登记 `PROPOSED_NOT_EXECUTED` 后续输入；没有把外部文件指令升格为 Authority，也没有执行其清理/迁移提案。
- Formal Desktop 修复原生 capture 遗留 owned Core 导致下次启动 SQLite 写锁的缺陷；Review POST 后追加 GET 状态回读，只有真实匹配 event/item/assessment/answer 才显示成功。启动根因、真实 EventLog、隔离合成工作区证据见 `AAOS-DESKTOP-STARTUP-20261001.md`。
- Green `.ui-task-tree/ArcheAxis-Knowledge-OS-mainline` 保留原有未提交前端成果，定向镜像小补丁；嵌套工作树标准 launcher 资源 preflight 修复。该树 self-contained Release EXE 在合成工作区可直接启动，普通 GUI 标题为“已连接”、退出码 0，1280/720 DIP 原生截图分别见启动报告。原绿色版根目录尚未部署。
- Formal 16 模块定向测试 `262 passed`；Green 历史/新增合同范围尚有 32 项失败，分类见 `AAOS-GREEN-UI-TEST-DELTA-20261001.md`。这些测试和合成 SQLite 不代表真实用户数据全链路验收。

## 待闭合与下一步

1. 在 Green 隔离树处理 32 项合同差距，并逐页比对 B10 和其余母版的原生截图、主题、动画、DPI 与所有窗口尺寸。当前母版浏览器基准截图未产生，像素复刻状态为 `UNVERIFIED`。
2. 验证所有可用真实后端接口的页面级加载、空、错误、离线、变更及回读。Review 已有局部回读；完整真实用户工作区旅程未执行。
3. 确认有来源、版本和依赖证据的独立 Python runtime（含 FSRS），随后按 `scripts/release/assemble_green_candidate.py` 组包，运行严格 `verify_green_candidate.py --require-runtime --require-workers`，再在原 Green 根目录更新并原位启动验收。当前该环节 `BLOCKED`，不能把开发候选 EXE 称作已安装绿色版。
4. 将本轮属于公共仓的改动独立提交并上传任务分支，回读远端精确 SHA 与该 SHA 的 CI。Green 大量先存未提交修改须由对应 writer 核对，不能整树批量认领。

回退：Formal 本轮新增改动按单独提交回退；Green 隔离树仅对本轮精确文件补丁单独回退，保留既有用户修改。历史资料和数据库不参与回退或清理。
