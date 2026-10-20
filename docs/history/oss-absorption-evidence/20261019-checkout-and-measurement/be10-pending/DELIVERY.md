# 最小切片、验证和限制

原BE10 TASKS要求有限只读关联、协议/身份/version/freshness，以及五种handoff准备；ACCEPTANCE第5旅程要求远端只读关联并返回本地。UI-HOST旧协议已有project.handoff.preview逻辑名。现有真实CLI已满足准备消费的一部分，本切片让本仓native human桥真正消费strict context metadata，不重复CLI、不增registry/DB/壳；它是必要依赖，不能关闭原BE10旅程。

Core使用launch middleware已有human actor，machine/Observer/无效token拒绝，独立本地API与无Observer grant仍可用。存储读取已有workspace身份、authorization epoch和document当前version/hash，不初始化身份；全部业务表前后快照一致。producer身份/恢复错误409、过期/未来400、合法非context400，未知/重复字段/query/私密正文/凭据字段有限拒绝无输入回显，超64KiB为413。当前对象CURRENT、同版本错hash/旧version STALE、缺失NOT_FOUND，重复预览不创建投递或幂等持久记录。UNVERIFIED来源/选区不升级，manifest仍既有UNKNOWN，execution/knowledge acceptance false，navigation UNAVAILABLE。原提案原样保留且生产handler重算规范digest。

5项新增实际Core进程测试包含4用途×4选区正控、错身份/恢复、真正恢复fence变化、时间边界、显式三引用状态、所有业务表不变、合法task不能偷换context、严格JSON/输入大小、权限边界及不泄漏。新native测试启动owned temp Core，经现有bridge真正创建合成fixture再调用preview，校验原件/digest状态/无token正文路径；异常payload/任意URL/凭据字段与超限在transport前拒绝，owned Core退出后不得缓存成功。fixture创建与恢复fence写只针对测试自己拥有的合成DB，preview本身无写。Drop kill+wait仅自己创建Core；未启动用户/外部服务或浏览器。没有独立汇总每个子Core PID/端口回执，不宣称独立进程清理审计完成。

schema与Rust共享16case覆盖三状态正控、未知字段、错误schema/context/digest及有限权限/导航值、未来/过期等跨字段语义。JSON Schema不能表达全部时间交叉约束；case分别记录schema_valid与runtime_valid，Rust承担实际语义，不把schema通过当运行验收。Preview.valid只验digest形状，生产handler实际规范重算，客户端后续核对原件须复用同算法。

证据为SYNTHETIC工程集成（实际本仓Core/HTTP/native桥代码 + 自建合成资料），不是实际外部产品INTEGRATED/REAL，也不是完整Tauri安装UI/OS URI/模型调用/Owner接受。下一步精确接线与恢复竞态风险在正式候选合同文档中；BE10保持PARTIAL。

所有命令、cwd、开始时间、耗时、退出码、日志hash、每步12候选hash在validation.json；canonical开始/结束和source_consistent在validation-summary.json。失败过程见FAILURES.md，不隐藏失败，不累计重复绿项。
