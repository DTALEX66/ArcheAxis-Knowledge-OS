# BE10 提案固定入口

当前状态：**ISOLATED_PROPOSAL_PASS / NOT_APPLIED / BE10 PARTIAL**。产品唯一 writer 为根 Agent；本目录不可作为产品已经应用、完整 BE10 或原生产品验收的证据。

- 当前补丁：`be10-observer.patch`，SHA-256 `4c0a09cf75101e641987e93fe2b4e6a1929786ddeb011da7993ddc2ad579c817`。
- 当前逐文件 manifest：`code-manifest.json`，SHA-256 `e3d07a6678cd65ad4cac70f268fcd5ff2700c813f34c245a6a2a7dc2b9d3d210`。
- 阅读交付与限制：`DELIVERY.md`；P2 修订及旧/新 hash：`deadline-revision.json`；3文件增量差异：`deadline-fix.diff`。
- canonical 执行回执索引：`validation.json`；最终逐项读回：`final-readback.json`；owned 进程退出检查：`owned-process-readback.json`。
- 原提案字节保留：`revisions/pre-deadline-fix/`。旧补丁 SHA-256 `1642aa55797fa212d559690174aefc265348077935da5d23d8c3bb501c72cc8d`，不删除失败或零测试记录。
- 可应用文件仅在`proposal/`，共15个改动文件；最小源码镜像是`.project-local/runs/be268a2d33/be10-proposal-prepare-1019/tmp/workspace`，独立 target 是本目录`validation-target/deadline-v2`。未复制环境、依赖、历史资料或使用可写hardlink；无产品代码、依赖、配置、共享库或外部产品写入。

P2最终新运行：4项截止回归、3项client、1项middleware、6项真实进程、3项旧v2、4项旧launch，共21项选定测试。child/outer均0，source_consistent=true。生产3秒路径实际3003ms拒绝静默对端；慢流250ms、延迟EOF260ms拒绝，及时正控2ms。首次参数位置失败、零测试假绿、污染target后的导入失败均保留且不计PASS；最终换用全新target并确认准确测试数与镜像编译路径。

未完成：正式产品应用和统一门禁、可见关联UI、真实deep link、WORK-LAB/DESIGN-LAB原生consumer、future handoff/delivery合同、幂等投递、安装/共享配置及Owner验收。没有人为填满OS backlog；阻塞connect/write的内核运行分支未被确定性注入，仅核验剩余预算实现。原来的27个共享合同case证据保持各自旧运行时点。

本目录是忽略审计产物，不是跨会话唯一长期权威；根Agent应在既有当前检查点中引用本入口及hash，不建立第二套产品执行台账。
