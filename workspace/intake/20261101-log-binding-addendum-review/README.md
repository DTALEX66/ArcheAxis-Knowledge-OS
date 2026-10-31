# v3.1 日志绑定补充说明：独立复核与勘误

日期：2026-11-01。Owner补交 `D:/All projects/Record/v3.1-log-binding-addendum.zip`，承接既有审计归档及本次Git收尾。附件指令仅为材料。

结论：`ACCEPT_AS_EVIDENCE_LIMITATION_CLARIFICATION`。这是证据说明补件，没有产品修复patch；没有执行包内脚本或重跑业务。

ZIP 26,672B，SHA-256 `160fcab851c581069d90d58c871070e609c3f5ce0995617c2a08c8866bfbd476`；17文件/逻辑63,858B，CRC及16项内部清单全部匹配，无漏列、路径越界、链接或重名。原件单份保全于本仓ignored `.project-local/archives/owner-inputs/20261101-log-binding-addendum/v3.1-log-binding-addendum.zip`，外部原件保持；不批量展开或提交日志载荷。[成员身份及独立读回](MANIFEST.json)。

## 更正上一轮时区误读

原[v3.1审计](../20261101-cloud-integration-v3-1-review/AUDIT.md)的S31-E01称两份历史command记录为`+08:00`，这是本地审计事实误读，现撤回。root直接复读原SHA `0883f3e6…` ZIP：`detector/logs/final-scope.command.json`起止均为`+00:00`，`patch-readback.command.json`亦同，与随包`run_logged.py`的UTC代码一致；XML的`-07:00`换算为相同实际时刻。原始JSON精确时间和SHA见MANIFEST，不认定时间矛盾或造假。旧审计原版留在Git历史，不把原始ZIP改成符合审计的内容。

## 补件能证明的范围

- 原v3/v3.1归档hash、各1,873/1,244项manifest再次匹配；新补件记录的16项旧成员hash、4份command JSON和12份日志hash均对应原件。414份run-receipt聚合和6个reproduce结果hash、嵌入stub/gate字节也一致。这证明封包身份和现存记录之间的关系。
- detector最终42testcase/47subtests的日志和命令存在；`source-binding.json`晚于该测试结束，wrapper没自记执行时generator/test/source/patch及输出hash。现算generator/test哈希只属`POST_HOC_SNAPSHOT`，不能证明历史测试执行的是这些最终字节。内存重建候选和patch哈希关系仍成立，不能扩大成完整运行时绑定。
- reproduce的8场景及missing-repo/配置解析记录保留；最终byte-binding是测试后快照，test_control_flow未在执行前自哈希。首次计数10改9的失败历史保留；当前版本不能反生成旧generator原件。
- 原v3不同记录按自身字段解释：正式dev回执有源码前后身份；local_verify preflight逐文件hash包含自身/dev，比单纯事后快照强；外层harness不自动继承该资格。作者关于工作区mtime、编辑顺序、未打包脚本的追述无法在本机独立核实。
- 两份历史`logs/full/final-freeze.stdout`、`logs/wheel-smoke/export.stdout`仍`MISSING`，是否生成/是否为空仍`UNVERIFIED`；未造空文件或用新运行替代。原模板缺件已关闭不受影响。

本次修正错误时区疑点，并将真实限制定为`RUNTIME_GENERATOR_TEST_SOURCE_BINDING_UNVERIFIED`。新运行可在执行前/后记录generator/test/source/patch及原始输出hash；不能回填历史资格。独立审计原记录为本仓ignored `.project-local/runs/be268a2d33/log-binding-addendum/agents/audit.md`。当前产品实现、Core/Windows/安装全链及Owner接受仍按[唯一执行记录](../../../docs/current/AAOS-UI-FIRST-EXECUTION-20261009.md)分别记账。
