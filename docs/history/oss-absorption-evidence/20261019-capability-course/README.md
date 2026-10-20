# 能力中心与严格测验 UI 验证快照（2026-10-19）

这是固定执行证据，关联[Owner 决定](../../../current/AAOS-OSS-INTEGRATION-DECISION-20261019.md)、[限定回执](../../../current/receipts/AAOS-CAPABILITY-COURSE-UI-20261019.json)及唯一[当前进度](../../../current/AAOS-UI-FIRST-EXECUTION-20261009.md)。不要将此历史脚本当作当前产品权威或工具默认路径。

`MANIFEST.json` 固定每个快照成员的 SHA-256。`prepare.py`、`run.py`、`launch.cjs`、`playwright.config.cjs`、`audit.spec.cjs`、`fixture.js` 是最终实际执行的脚本；`expanded-fixture.js` 是注入本次浏览器的完整合成桥接脚本。其余 JSON 保存六项逐项检查、五组 axe、浏览器版本/视口/字体/主题、自己创建的进程、退出读回及11张已实际查看截图的哈希。完整 PNG、trace 和运行日志保留于项目 `.project-local/runs/be268a2d33/capability-course-style-browser-1019/`；没有上传私人资料。

本次使用现有 `visual-project-audit` 技能和 Playwright/axe 工具环境，没有重新安装、升级或修改用户级配置。先从[共享资源索引](../../../SHARED_RESOURCE_PATH_INDEX.md)解析现行工具，再校验 manifest。快照内绝对路径和版本只代表本次执行现场，不应硬编码为后续机器的默认配置。

实际调用由项目 `scripts/runtime/dev.py` 分配独立运行目录，再运行 `run.py <frontend-build.json>`；构建入口为 `scripts/runtime/frontend.mjs build`。完整命令、开始/结束时间、退出码和源码 patch 均在限定回执。脚本只启动 127.0.0.1 静态生产 bundle 服务，确认41730–41739内空闲端口，独立浏览器 profile、一个浏览器/worker；禁止真实 API、数据库、模型与业务写入。重新执行应采用新的运行 ID，先检查现行授权及脚本副作用，不复用旧 profile 或其他会话服务。

六项检查覆盖目录筛选与未来条目、范围化状态与现有配置页、测验预览与键盘参考核对、未知保存同请求重试及重开、拒绝/列表失败、窄窗口与 reduced-motion。额外记录选项44px行/控件13px/中心偏差0，以及卡片纵向排列和无横向溢出。五组 axe 无违规，仍有7条 incomplete，不能称完整无障碍合规；首轮失败、旧标题断言失败、两处导航缺陷和两处视觉修复见限定回执。

证据为真实 Chrome＋生产前端＋SYNTHETIC Core。未验真实 UI→Core、原生 WebView2、安装、真实上游完整课件、屏幕阅读器、所有主题/DPI、性能或模型学习质量。目录本身不证明插件安装/执行已实现；完整市场生命周期仍待后续任务。
