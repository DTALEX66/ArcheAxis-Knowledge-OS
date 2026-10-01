# 交给 DSH / DeepSeek 的独立任务提示词

你接手 ArcheAxis Knowledge 后端全链路工作。仓库 `D:/All projects/ArcheAxis-Knowledge-OS`，原 Green `D:/All projects/ArcheAxis.Knowledge.Green-x64`。先读取当前 Git branch/status/远端 SHA、`AGENTS.md`、`docs/CONFIGURATION_AUTHORITY_INDEX.md`、R6 `EXECUTOR-START.md`/`TASKS.json`/`TASKPACK.md`、`docs/current/R6-STATE.json`/`R6-EXECUTION.md`、M0 方向覆盖，再读 `docs/current/AAOS-EXECUTION-PACKET-20261001.md`、`AAOS-UNFINISHED-TASKS-20261001.md`、`AAOS-ALL-TASKS-DISPOSITION-20261001.csv` 中的 `BACKEND_FRONTEND_LOOP`/`OWNER_GATE` 行，按需追 `AAOS-ALL-TASKS-LEDGER-20261001.json` 的原要求，以及 `AAOS-ERRORS-BLOCKERS-20261001.md`、`AAOS-UI-BACKEND-MAP-20261001.md`。根 `AUTHORITY.md` 缺失则报告 `AUTHORITY_REFERENCE_MISSING`，不得从历史包自造新权威。9/28、9/29、9/30 和 10/1 资料是需求/候选/历史证据，依总账映射处理；不自动授予跨项目写权限。

从当前远端已验证的 `main` 新建**独立后端功能分支**，建议 `codex/dsh-aaos-real-multiformat-loop-20261001`；分支名冲突时加唯一后缀，不重置/覆盖任何已有分支或未知修改。保持 UI 分支 `codex/aaos-ui-phase2-20261001` 与其隔离；同一文件仅一个 writer。若当前软件无法创建 Git 分支，先核实真实工具能力并明确阻塞，不伪称已创建。使用软件自己的当前模型、provider、reasoning 和认证设置，不硬编码或改全局配置。省 token：依权威入口和总账 ID 定向读文件，每一轮只加载相关源码/合同/测试/日志；不要反复粘贴大包。

目标是新规划里**最完整的最短真实多格式整体闭环**，保持 R6 Rust canonical writer、Desktop/Core 边界及 M0 P0–P6 顺序。挑选合法、可审计的代表性真实文本、PDF、Office、HTML、图片、音频、视频、Canvas 输入，逐个给出摄取/转换/OCR 或 ASR（适用时）/来源与修订/证据链接/质量和失败恢复；打通 Knowledge → Search/Review → Human Learning/FSRS/Mastery → 一次真实模型错误、人审纠正、复用与重测 → 进程重启回读。缺供应商或模型能力时明确 `BLOCKED`，保留有界降级与真实错误状态，不用 fixture/synthetic 冒充 REAL。通过版本化 API/合同向 UI 分支提供接口、空/加载/错误/离线语义及样本响应，禁止双写旧数据库。只在隔离测试资源上验证备份/回滚；用户暂停清理、迁移与整理，真实数据库、缓存、历史、恢复包均不碰。E/F 盘禁止访问；不得读取/上传凭据和私人状态。

每一闭环节点写入总账对应 ID、真实输入来源、代码 SHA、命令、日志、可复现结果和证据等级。运行项目规范入口的定向及最终门禁；Desktop 启动异常以实际日志/堆栈定位，不能以 `0xe0434352` 猜根因。推送任务所属公共修改至新分支，创建 Draft PR，回读远端精确 SHA 与同 SHA CI；不要把 push、编译、窄握手当完整产品通过，不解除 R6 release 冻结。最终交付已闭合项、接口合同、真实运行证据、剩余 Owner 决策/阻塞及回滚方式。
