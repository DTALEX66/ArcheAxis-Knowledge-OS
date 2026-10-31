# 并行维护：目录生产者、F05探针与外溢恢复线索

Owner要求加速、按难度分模型并行所有未完工作并静默执行。根任务保留共享沙盒与落库；目录分支使用gpt-6.1-sol/medium，恢复追踪使用gpt-6.1-sol/high，后端证据修复使用gpt-6-astra/high，各自独占写集。此为本轮任务分工，不修改产品模型、服务商或全局配置。当前授权和实际进度仍沿[活动指针](../../../current/AAOS-ACTIVE-EXECUTION.json)及[唯一执行记录](../../../current/AAOS-UI-FIRST-EXECUTION-20261009.md)，全目标PARTIAL。

## 目录生产者修复

50项精确规范化核实中，23项直接WinError5，14项为空、13项非空；没有将未知归属/占用/恢复的非空目录批量搬迁。发现 `crates/archeaxis-api/tests/declared_routes.rs` 仍持续生成浅层 `.project-local/runs/declared-routes`，历史曾清空后又出现；仅清目录不能解决增长来源。

该测试现在复用 `dev.py::pytest_environment` 的canonical run校验与独立调用fallback，在本轮 `run/tmp` 内创建独立TempDir，各次launch隔离、正常释放自有临时目录。`nrm-route-test` 真实编译并执行原2项路由测试，2/2通过，child/launcher退出0、source_consistent=true；`nrm-fmt1` workspace格式检查通过。旧浅层目录测试前后为空且mtime不变，没有继续生成。

随后普通令牌独立核当前所有者、祖先无reparse和空目录，`nrm-empty2` 以非递归rmdir移除这一个精确目录；遇非空/系统锁会拒绝，不终止其他进程。事后确认缺失。删除文件0、文件逻辑字节0，仅空目录1，不把它计入此前51,068,863,617逻辑字节的副本回收。早期 `nrm-empty1` 的owner子进程返回1且诊断解码失败，发生在删除意图前；原失败保留，改为原生参数、显式模块及UTF-8后才执行成功。其他49项仍按各自证据处理，未放宽layout规则。

## F05有限探针修复

旧真实回答已正确指出Rust Core/FROZEN，原探针仍给它写入人为失败标签；初始8项合同测试通过也没有挡住错误/空答、假回链、空body或重复阶段。此次只改既有 `colearning_real_model_smoke.py` 与合同测试，不重复Core已有的persisted answer/question/knowledge/text绑定，不改变同题retest合同。

固定结构化量规在推理前记录，错误、空答、否定与未知文本分开；正确原答/合理拒答不再人为纠正。纠正绑定具体answer/client request、完整request、context SHA、授权快照和持久化prior；同题复测保持原问题，独立应用题走新的 `/machine/answers`，模型/预算/问题/上下文变化不能混作效果。legacy知识未行使资产grant，资产或scoped上下文不在本轮资格内。

根任务另发现反例：正确原答但独立任务答错，初版仍exit0/NO_FAILURE_OBSERVED；纯合成Receipt还标REAL_MODEL。`bkr-rootx1` 留证后再修：独立题错误→TRANSFER_FAILURE_REVIEW/exit1，无法评分基线→TRANSFER_BASELINE_REVIEW_REQUIRED；不纠正正确原答。schema v3默认SYNTHETIC_OR_UNEXECUTED；显式本地运行尝试在未见模型响应时为LIVE_ATTEMPT_NO_MODEL_EVIDENCE，只列具名成功响应阶段，不宣称链路完成。原反例不改输入经 `bkr-rootx2` 独立复核，现exit1且合成证据层正确。

最终 `bkr-f05v3` 52项合成合同/反例通过，`bkr-f05l3` Ruff通过，均LOCAL_PASS/source_consistent=true。`v1` 的正控fixture前缀错误、`v2` 的44通过但未覆盖根反例均保留，不扩大其资格。**F05总体仍PARTIAL**：未运行真实模型、完整main入口、资产/scoped效果链或安装态复测；learning_improvement始终NOT_ESTABLISHED，asset_effect为NOT_QUALIFIED。有限JSON量规不能证明一般学习或完整AI闭环。

## 外溢恢复追踪

对121条登记中的36个顶层ZIP入口核查，35个有效容器共30,620成员；另1个同登记SHA重现已知SOURCE_CONTAINER_INVALID/BadZipFile。11个嵌套ZIP和2个后继ZIP均在内存做成员元数据核对，分别191/29成员，无更深容器；累计30,840次成员元数据枚举，无目标名称匹配。嵌套ZIP本体SHA与已知wheel ZIP不符，仅说明这些ZIP本体；未读内部DB/文件载荷SHA，不据名称排除载荷存在。

历史文件明确三组是AAOS任务产物，DSH是执行方；不能按名字迁往其他项目。Green mainline线索实际是外部linked开发worktree。Owner回应旧版基本不用后，沿提出的三处精确只读边界核查：`candidate-run-20260928`、`dsh-backend-runtime-20260928`、`dsh-wheel-qual-20260928` 均未解析到，共同mig祖先winerror2、目标winerror3；已有祖先无reparse。没有枚举共同父目录或整Green，没有读取DB正文/私有状态、搬迁或删除。

这不是SOURCE_MISSING/永久丢失结论，也没有恢复或外部清理候选。旧迁移收据、原manifest和4个SHM差异继续保留，后继精确路径须沿迁移/替代账本核实。不能由旧程序基本不用推定恢复资料也无价值。剩余533根ACL截至封存未见apply终态；初始review两行不等于权限已恢复。

## 证据与接续

[MANIFEST](MANIFEST.json)绑定三份代码、每个独立检查和只读追踪证据；`pm-seal1` 独立复核测试退出、原反例拒绝、精确空目录缺失和raw身份，source_consistent=true。无远端写、云CI、前端实施、模型/鉴权/全局设置变更、Green替换或真实数据覆盖。可分别回退测试路径与probe修复，保留运行证据；需要旧空目录时只重建空目录，当前生产者不回退到浅层落点。

## 后继恢复路由与权限观察

[补充证据清单](ADDENDUM.json)保留原pm-seal1，不覆盖旧检查。后继仅选择Git跟踪的docs/workspace/config/scripts：3,113路径中2,894公开UTF-8文本读完、219项排除、0读取错误，33文件134匹配；三组目标的直接名字/哈希只在3份历史文档。六个新精确本仓候选只有原10/07只读审计仍在，6,307字节/SHA `6c798b7d90e3b6537e40862632abb5a75f1c3e9b7591aa98514f8f6031a68dbe`，没有后继载荷绑定。

据该原件，Formal三组在10/07仍有36/3,117/4文件，candidate的4个SHM差异、3,112个CAS及wheel资格限制分别保留；Green在10/07已缺且无删除收据。本轮明确缺口为Formal在10/07之后、Green在9/29复制声明至10/07缺失之间的迁移/替代账，未据缺口推断永久丢失。三组仍无可迁移或清理候选，同一范围搜索不重复循环。

截至 `acl-observe2` 冻结观察，原ACL备份156,988,637字节的SHA与identity一致；完整日志前缀有95,558次INTENT_DURABLE和95,558次VERIFIED，读取期间日志继续增长，未见apply终态收据。此数是已观察前缀事件数，不能代替533根全量完成或普通令牌复核。既有管理员命令继续运行，不重复启动；reader ACL写入0、无进程终态判断，监控暂停不变。

ACL范围判断的纯合成基准发现533根逐项pipeline成本较高；候选短路判断在2,135路径及7个边界fixture结果相同，基准仅约束成员判断，不证明实际ACL应用/回退等价。冻结修复模块未替换；待旧run终态和普通读取复核后，任何新版本需独立新run、hash、catalog/plan及应用/回退资格，旧备份仍用原模块。
