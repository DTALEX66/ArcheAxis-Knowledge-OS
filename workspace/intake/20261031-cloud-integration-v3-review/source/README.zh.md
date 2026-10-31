# AAOS 云端整合验证 — 隔离副本，不是正式发布

**结论：真实 Core / 生产前端组件接线已跑通代表路径，但不是全项目验收通过。**

- 基线：`8d367bac4a85bebfbb523503678ade0838faa73e`，正式仓库未推送、未发布、未修改其他项目或真实资料。
- 真实双解析提供方（PyMuPDF、pypdf）及 pypdf 6.10.0 → 6.10.2 → 6.10.0 已经经过同一 Core 任务/原件/产物接口运行，旧结果仍可读。25 项新增 HTTP 断言通过；双页样本补验也通过。
- 生产 `JobContent` 不改源码，实际读取以上四份持久化结果；生产课程文件适配组件实际保存、重启读回、冲突拒绝、恢复。8 项新增前端 jsdom → 真 Core 集成测试通过。**jsdom DOM 不是浏览器截图，更不是 Tauri 原生宿主。**
- 现成 FSRS 6.3.2 调度器实际运行并由 Core 保存与恢复；没有自研学习算法。OpenMAIC 仅现有导出文件适配，不是其模型生成/课堂播放器运行。
- 五入口已作最小分组修复；未知课程版本/renderer 新增局部安全回退，可保全原件而不是空白或偷偷降级为成功。
- **仍受阻/未验证**：Chromium 被当前执行环境拒绝 Unix socket；CUA 云浏览器不能访问独立执行命名空间的 localhost。无真实截图/多视口结论。H5P 播放与 xAPI 真实事件未运行；无产品 LLM 端点的实际调用；X8已做同次知识修订综合读回，但研究/AI统一来源当前性投影存在代码合同缺口；Windows/WebView2/本地设备未验证。

## 追加全量验证

已在云端跑完整适用Python（5780通过、105当次skip、4浏览器deselect；379subtests）、Rust/Core1025通过、前端1983通过/4opt-in跳过。105原skip另有42项定向补过，剩63项逐条说明，不重复累计。已修检测worker定位、非UTC租约、安全锁6包和CI剥离runtime依赖问题；保留全部旧失败。详见`deliverable/FULL-VALIDATION.zh.md`。

**本地无需对相同源码/锁重做通用全量审计**；继承条件和仅需补做的真实环境/新变更见`deliverable/HANDOFF-NO-REDUNDANT-AUDIT.zh.md`。

## 阅读顺序
1. `deliverable/REPORT.zh.md`：结论、X1—X8、失败根因、前后端复用/修复/删减、下一步。
2. `deliverable/X-results.csv`：逐组具体证据和限制。
3. `deliverable/mappings/`：186 能力、22 历史职责、22 格式、37 平台、最新决定/任务/旅程的保留去向；**不是逐项运行通过**。
4. `deliverable/review/` 与 `deliverable/research/`：独立审查、学习平台复用与界面架构建议。
5. `logs/`、`deliverable/evidence/`、`patches/`、`harness/`：原始输出、真实 Core 数据与 HTTP 请求/回执、代码差异。

## 复现
在新目录解压，检查 `reproduce.sh` 后执行。脚本会下载固定 Git 基线、仅在新副本应用补丁、安装项目局部依赖、编译并执行代表验证。需要 Git、Node/npm、Python、C 编译工具、可访问 GitHub/PyPI/npm/Rust 下载源。不会推送、发布或配置模型。
所有结果只写实验目录；脚本拒绝覆盖已有 `repo/`。不要在正式工作目录运行。`core_matrix.py` 与 Vitest 测试退出时终止自己启动的 Core 进程。若手动中断，只终止本实验 PID，不扫描/终止其他服务。

依赖下载、构建和浏览器能力与云环境有关。提供的真实证据保留，复现使用单独数据根。当前实验成本没有可核对的计费记录，不报告虚构费用。小样本不外推为全格式/全学科准确率。
