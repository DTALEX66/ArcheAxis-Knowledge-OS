# 材料／陪伴恢复原生尝试（历史证据，2026-10-19）

此目录绑定 patch `9eba6d3558edd54c0adf2f18c8f258faaed6ffa692c8d90ebb43ecb4ce8b7751`，整体 **PARTIAL / 原生整旅程 FAIL**。它是历史快照，不是当前源码或另一份进度台账。接续读[活动指针](../../../current/AAOS-ACTIVE-EXECUTION.json)和[当前执行记录](../../../current/AAOS-UI-FIRST-EXECUTION-20261009.md)。

本轮修正探针遗漏既有“恢复最近同版本材料请求”的问题，并用受信任滚动把实际回答带入截图。59项＋145 subtests 与 TypeScript/Vite/Tauri/Core 构建 PASS；具体命令、时间、退出码及源码绑定见 `probe-tests.json`、`host-build.json`、`core-build.json`、`native-execution.json` 和 `candidate-build.json`。

实际候选 UI→Core→LM Studio 的材料与陪伴调用成功；requested/observed 为 `aaos-deep-27b-mtp`、stop、未截断。同进程恢复与冷重开读回原回执不变，观察窗口内额外 UI 执行调用为0；启动前调用数仍 UNVERIFIED。这些是合成材料工程证据，不是答案质量或学习效果资格。

备份恢复、宿主重启及配置读回已经发生；之后探针在恢复布局瞬间无法触达文档导航按钮而失败。`native-result.json` 中 `backup_restore: NOT_EXECUTED` **仅指材料／陪伴恢复后的读回阶段未完成**，不表示整项备份操作未发生。后续有界布局重观察修复及新失败见[后继快照](../20261019-material-companion-final/README.md)，不能用后继回归 PASS 改写本次 FAIL。

截图路径、长度与 SHA-256 在 `native-result.json`。其中材料完成、材料冷重开、陪伴冷重开、组合完成及失败截图已实际查看；本目录没有声称该轮所有截图均被查看。PNG 与原始回执保留在项目 `.project-local/runs/be268a2d33/webdriver-402c847cf11e/tmp/journey/`，不复制业务数据库或认证资料进 Git。受控进程及端口退出读回为空。

`MANIFEST.json` 核验本目录成员字节。全产品、已安装、真实用户数据、取消、独立质量与 Owner 验收均未因此通过；未提交、推送或云端备份。
