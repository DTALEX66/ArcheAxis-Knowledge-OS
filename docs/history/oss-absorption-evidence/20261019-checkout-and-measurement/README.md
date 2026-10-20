# 2026-10-19 接续归档：Git原字节、请求测量和来源重绑定

状态 **PARTIAL / 本地未提交**。这是证据快照；当前决定、权威和任务状态沿[固定接手入口](../../../current/AAOS-AGENT-HANDOFF-CURRENT.md)解析，不另建一套权威。

- [39项原话主题](../../owner-dialogue-20261019/README.md)保持原SHA；本次新增的[明确归档要求](OWNER-ARCHIVAL-REQUIREMENT.md)另存。权威、规划、入口、外置模型/工具库按[NAVIGATION](NAVIGATION.json)查既有规范源，不猜路径。
- [18文件实际源码身份](SOURCE-IDENTITY.json)、[差异](OWNED-DELTA.patch)、[结果与边界](RESULTS.json)：已应用EOL4、失败请求测量11、来源目录3；source/保留精确后继原字节。eol/measurement/catalog内旧提案状态是形成时记录，不能覆盖根RESULTS的APPLIED。
- [11次真实执行回读](EXECUTION-READBACK.json)各有命令、时间、退出码与源码patch。它们属于不同源码时点，不合并成全量产品PASS。
- [独立原生读回](NATIVE-READBACK.json)：真实27B两次完成，同进程、冷重开和备份恢复通过，6图实看并保留身份；材料概括低效用、完整AI链旧FAIL均保留。该运行早于本次18文件，不能为新源码授予原生资格。
- be10-pending/保存12文件提案及[正式应用阻断](be10-pending/APPLICATION-BLOCKERS.md)：隔离验证通过，但CI环境依赖与Rust格式门禁未闭环，NOT_APPLIED；不冒称已实现完整外部投递。
- [.project-local证据身份](LOCAL-EVIDENCE.json)只列有限项目产物，PNG和更新前原件保持本地。未复制私人客户端正文、凭据或浏览器资料。

冻结规则：MANIFEST覆盖本目录所有成员；旧归档不回写。精确目录已登记.gitattributes -text，Git检出验证会复制本快照和16个既有冻结目录到独立fixture，清除子进程继承的GIT_*，不触碰真实index。

从仓库根执行 `.venv/Scripts/python.exe -X utf8 -B docs/history/oss-absorption-evidence/20261019-checkout-and-measurement/verify_snapshot.py --require-local-evidence --git-checkout`。结构/哈希/Git检出通过不代表产品、安装或Owner通过；实际最终读回见[限定回执](../../../current/receipts/AAOS-CHECKOUT-MEASUREMENT-20261019.json)。
