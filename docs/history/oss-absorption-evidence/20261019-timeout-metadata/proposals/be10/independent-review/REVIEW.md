# BE10 冻结提案独立审阅

状态：**PARTIAL / ONE_CONTRACT_GAP**。补丁保持 **NOT_APPLIED**。未发现 Observer 准入、角色隔离、业务只读或私有资料投影的阻断缺陷；HTTP 总截止存在一项应在声称合同通过前修正的实现缺口。

绑定补丁 SHA-256：`1642aa55797fa212d559690174aefc265348077935da5d23d8c3bb501c72cc8d`（15文件）。独立读回15份 proposal 源码与 manifest/mirror 字节全部一致，14份历史验证回执 SHA 全部一致。详见 `READBACK.json`。

审阅模式：当前冻结源码、合同、测试、交付说明静态阅读与证据哈希读回。本审阅者没有应用补丁、改产品、重新执行测试、启动模型/服务或读取用户业务资料。既有测试运行属于作者的 SYNTHETIC / 工程集成证据，不提升为当前产品、外部原生宿主或 Owner 验收。

## 需要修正：统一 HTTP 单次请求的总截止（P2）

位置：proposal `crates/archeaxis-api/src/project_observer/client.rs:86-188`，尤其91-94、104-105、116-120、188。合同 `docs/contracts/project-observer-v1.md` 的“3秒总截止”。

实际：`started` 在连接前建立，但 `connect_timeout(3s)` 后 `set_write_timeout(3s)` 重新授予完整写预算；`write_all` 也没有逐次写重算总剩余。read 循环进入时检查剩余，却在 `read` 返回EOF后直接 break；HTTP/JSON/身份/时间校验后直接返回 Ok，没有确认总预算。由源码可以确定“3秒总截止”没有覆盖所有阶段；完成I/O后线程暂停或校验消耗时间，存在过期后接受有效metadata的成功路径。

这是合同实现缺口，不能只称测试覆盖不足。本轮没有构造实际 late-success 复现，不能把源码路径分析写成运行已复现；具体Windows调度延迟/最大超时量仍 UNVERIFIED。它不授予额外执行权限，也没有发现凭据/正文泄漏。

最小修改：建立一个 monotonic deadline，connect / write / read 均通过同一剩余预算函数获取超时。write 使用有限循环逐次重算剩余；每次read完成（包括EOF）后以及成功返回前检查总预算。预算耗尽返回既有 `OBSERVER_UNAVAILABLE`，不携带metadata，不引入新的重试或缓存成功。

必须补的定向回归（owned loopback，自建合成数据）：

1. 及时完整合法响应正控，仍可成功。
2. accept后保持连接不回包超过总预算，返回Unavailable并有界退出。
3. 每次read间隔短于socket timeout的分块慢流，但累计超过总预算，仍失败，不能靠单次read不断续命。
4. 合法完整body在截止附近到达、EOF延后，不能在截止后返回成功。
5. 对连接/写入已消耗预算和EOF/解析后预算耗尽，用内部有限budget/clock测试接缝确定性验证；不要用塞满OS backlog、修改系统网络或依赖毫秒级调度碰运气。

计时断言需明确Windows调度容差，不能以容差把deadline后成功放行为PASS。建议同时断言结果为失败和不会输出metadata。CLI先握手再所选操作产生两个请求；这里的3秒定义按单请求执行，若打算承诺整个CLI总3秒，须明确另一个总预算，不能从现有合同推导已满足。

## 已核对的主要边界

- **独立准入/角色隔离**：v3显式grant；token与human/machine及其他Observer不冲突；有限consumer、producer/restore、expiry及对象allowlist。Observer认证后直接返回受限serve，不进入通用router或自报actor逻辑。
- **新增admission正负控有效**：human POST确实到达可变下游并递增计数；合法Observer读与禁止的普通路径/写请求都没有继续下游。不是单纯测试不存在的mutation route得到404。
- **空库只读**：使用existing_workspace_id与authorization_epoch读取；没有调用首次读取写身份的UI helper。未初始化身份503；producer/restore不匹配409。bootstrap无凭据/正文投影。
- **业务只读**：metadata查询为固定SELECT，仅显式grant IDs；DEFERRED读事务与commit。源码未发现INSERT/UPDATE/DELETE；现有process测试对所有业务表逻辑快照作前后比较。此结论不等于SQLite完全不产生任何底层锁/WAL系统行为。
- **有限响应**：严格DTO与unknown-field拒绝；身份、namespace/instance、workspace/restore、版本/hash、时间窗口与所选operation核对。status回显冻结reference精确相等，不静默以新revision代替。client只连127.0.0.1、无任意URL、不跟随重定向；有frame/JSON大小界限。
- **资料边界**：输出不查询正文/title/memory；测试使用独立合成私密正文/标题/另一个未授权ID负例及原始输出检查。error只输出有限code。授权方显式提供的document_id本身属于许可metadata。
- **合同负例**：Rust实际serde+语义valid与Python实际JSON Schema分别遍历同27case，schema_valid与runtime_valid有意区分动态时间及重复ID语义；没有把schema结构PASS当运行语义PASS。
- **历史证据没有洗绿**：validation保留FAIL与INVALIDATED；v2-final外层INVALIDATED，child exit0不计正式产品PASS。DELIVERY明确完整launch_auth待根writer在稳定正式源码下运行。

## 应用与资格边界

根writer若将来接入：先修总deadline并补定向回归，再检查3个既有文件preimage / git apply --check，统一运行完整launch_auth、新API/进程/client合同目标及Python合同验证。当前冻结产品不应因本审阅被修改。

BE10仍是工程首切片；真实WORK-LAB/DESIGN-LAB原生互通、可见关联UI、deep link、投递/幂等、安装打包、已注册真实worker端到端取消、用户资料及Owner验收均未由本补丁交付。不得称完整BE10或整个产品PASS。

本审阅写入仅本目录的REVIEW.md及READBACK.json；没有产品写入。源目录历史报告/冻结归档均未改动。
