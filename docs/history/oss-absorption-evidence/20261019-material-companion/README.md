# 材料与陪伴原生验证、接续快照 · 2026-10-19

这是限定证据快照，不是新权威或第二份进度台账。先读[活动指针](../../../current/AAOS-ACTIVE-EXECUTION.json)的 `continuation_context`，最新决定见[统一决定第九节](../../../current/AAOS-OSS-INTEGRATION-DECISION-20261019.md)，实际进度仍写入其 `active_progress`。总回执为[原生验证回执](../../../current/receipts/AAOS-MATERIAL-COMPANION-NATIVE-20261019.json)。

本轮源 patch `430bc832dfd1cc304458b0abc0f2ecee986b7f16eca9147b6a45c3483cad37ab` 的探针检查58项及145 subtests、TypeScript/Vite/Tauri/Core构建 PASS。候选已包含上一轮小栖恢复修复；候选 host/Core 哈希和旧组件保全见 `candidate-build.json`。检查数量不证明全仓、安装版或学习质量通过。

原生候选在隔离合成工作区，通过真实 UI→Rust Core→LM Studio，完成 material 与 companion 的预览、冻结确认、实际27B调用和原请求只读回执。两次 requested/observed 均为 `aaos-deep-27b-mtp`、stop、未截断，分别71.98秒/241输出token、46.86秒/145输出token。合成材料及人为审核不构成真实用户知识或教学质量验收。

**整条原生旅程 FAIL**：同一进程离开材料页再返回后，组件内回执已清空；探针没有先点击已有“恢复最近同版本材料请求”，直接等待旧回答。堆栈在 `native-result.json`。这是缺少恢复动作的探针路径；自动恢复是否应成为产品行为仍未验收。不能据此宣称模型失败，也不能把局部调用成功写成旅程通过。冷重开、备份恢复未到达，NOT_EXECUTED；启动阶段调用次数 UNVERIFIED。后续最小步骤是在返回后显式恢复并核对原请求，再重走冷重开与备份恢复；保留本轮失败，不覆盖其回执。

三张 PNG 均实际查看，路径、大小及完整 SHA 见 `native-result.json`。截图另见复习按钮把内部 `course:…:artifact:…` 长键当作标题，首页也存在同类源码：下一切片应由 Core 的 learning_items 投影提供业务标题（课程 manifest.title 优先，普通学习项取绑定 assessment.content 摘要），原 ID 保留查询身份，集中诊断。不要依赖第一页课程清单或逐项前端 N+1 请求拼标题；同名标题不得合并身份。这是待修复项，不计为已完成。当前截图部分内容位于滚动区域外，不把截图名称当作回答已在画面内的视觉证据。

自己创建的宿主与驱动已退出，端口释放，原创建身份的剩余宿主/监听为空；共享 LM Studio 服务、权重、真实 workspace、Green 与用户配置均未改写。LM Studio 本轮按现有 deep-mtp profile 加载，无其他模型卸载或默认 provider 改动；本机加载回执保留于 `.project-local/runs/lm-studio-profile/1792345466308-load.json`，不是永久加载状态。

本目录保存实际命令、时间、退出码、限定结果及探针源码字节快照。完整原生回执和PNG留在项目 `.project-local/`，不复制数据库、认证、私人会话或原始业务资料；哈希清单记录成员。复现从当前源码入口执行 `native-execution.json` 中的命令，经 `scripts/runtime/dev.py` 使用新 run ID；先核对当前候选构建绑定、模型 profile 与驱动身份，不能直接用历史 patch 资格替代当前源码。整体 PARTIAL；未 commit/push，归档不等于云端备份。
