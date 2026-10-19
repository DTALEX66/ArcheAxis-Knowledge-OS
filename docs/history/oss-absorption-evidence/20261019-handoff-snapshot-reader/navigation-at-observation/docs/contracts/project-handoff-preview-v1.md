# Project Handoff Preview v1：本地human有限消费

> 2026-10-19 后继：下文预览合同继续有效，“确切剩余接线”是前轮形成时的缺口。其第1—3项已由下方snapshot／page16切片实施，实际资格读[限定回执](../current/receipts/AAOS-HANDOFF-SNAPSHOT-READER-20261019.json)；第4项仍待独立授权与验证。

BE10原逻辑操作`project.handoff.preview`的真实Core与native有限命令；不是外部产品身份认证、投递、上下文正文传输、执行、知识接纳或OS深链接。

`POST /api/v1/project-handoff/preview`只接受现有launch middleware验证的human会话。machine拒绝，Observer专用token仍只到既有三个只读端口；不给外部产品human token。64KiB输入、无query、严格既有Handoff DTO且kind只能context，未识别/重复字段、私有正文/凭据/URL字段及错误时间均返回有限错误而不回显输入。过大body由现有body-limit拒绝413；API无新DB/注册器/常驻服务。

同一DEFERRED只读transaction读取已有workspace_id、恢复authorization epoch和当前文档版本/hash；缺失/损坏身份拒绝，不调用初始化身份helper。producer不匹配409；原冻结ID/version/hash与现有状态比较为CURRENT/STALE/NOT_FOUND，绝不换成最新版。STALE包括版本或hash不同，不代表真假裁定。原件元数据的source_authentication固定UNVERIFIED，选区存在性/语义仍原UNVERIFIED；consumer是原提案声明，没有声称认证了外部产品。

输出schema `archeaxis.project-handoff-preview/v1`，严格DTO/JSON Schema及共同正负案例，包含原严格context提案与规范proposal_sha256、当前观察时间/到期、reference_state、REFERENCE_METADATA_ONLY及navigation UNAVAILABLE，执行/接纳false。状态和digest不能当投递、签名、已知manifest或执行权；preview的valid不独自验证digest真实性，生产handler实际重算，客户端若比较原提案须复用规范fingerprint。到期不超过原提案，队列等待超过期限也拒绝；没有持久化去重/投递或exactly-once承诺，重复预览无写入。

原生入口复用现有Tauri `core_command`及主进程持有的人类凭据，仅增加固定`project_handoff_preview` operation，payload严格只含对象`body`。路由固定，输入与响应各64KiB、有限3秒HTTP传输；不接收URL/命令/凭据，不新增invoke或共享配置。凭据从既有主进程内存取得，不进入前端或Handoff。测试里的BE10_PREVIEW_CORE必须指向本轮构建的owned临时Core，不可使用用户服务；缺少时测试失败。

## 到只读引用旅程的确切剩余接线

1. 由后继当前FE授权在已有页面增加显式context预览入口，严格解析/限制字节；不从URL自动执行，不开第二主导航，不将它送入Library.openDocument（该路径能编辑及写working state）。显示来源认证/选区UNVERIFIED和三种引用状态；只有用户明确选择后进行本机阅读。
2. 可复用PinnedReferencePanel的document_version+expectedDocumentSha和onClose返回行为；但它目前没有workspace/restore_epoch约束，普通DocumentVersion请求也不绑定这两个身份。不能先metadata预览后直接读正文而遗漏恢复竞态。后继需要在现有human有限桥增加**同事务**身份/冻结引用绑定的本地只读snapshot读取，或者等价原生绑定；正文只在本机human阅读，不外传给Observer。CURRENT仅观察时点，不能缓存当永续读取权。
3. 保持原研究/关系/本地草稿、布局、焦点及打开上下文；关闭只读引用返回原位置。过期、恢复、版本变化、断连、切换竞态要拒绝或明确重核对，不默认为新版；无保存/执行/接受按钮。
4. OS URI handler注册/安装、外部WORK-LAB/DESIGN-LAB真实native入口与返回链需要各自明确路径/配置授权及独立仓测试；本轮不配置、不冒充对端、也不宣称已完成它们。

证据：实际Core进程API正负回归和全业务表前后快照、真实native有限桥调用owned Core、shared schema/Rust DTO。它们属于SYNTHETIC工程集成；实际外部产品UI/native、安装、完整用户旅程与Owner验收NOT_EXECUTED，BE10整体仍PARTIAL。

## 后继snapshot及现有页面消费（2026-10-19）

`POST /api/v1/project-handoff/snapshot`和原native `core_command`中的`project_handoff_snapshot`为本机human只读固定端口；与preview使用同一严格context提案（无query、未知／重复字段拒绝、输入64KiB），不接受用户指定URL／路径／命令。Observer／machine不获正文。3秒有限桥、响应24MiB；原始editor JSON超过8MiB或序列化响应超限均拒绝，不截断为成功。

同一DEFERRED事务核对已有workspace身份、restore epoch和冻结document/version，先限原始JSON字节，再核对原始UTF8 SHA＝存储SHA＝提案引用SHA；不对重新序列化的对象做替代hash。只返回核对后的`editor_json`及有限身份/时间/状态，不混入未受此hash覆盖的当前title、source、blocks或text_projection。历史版本仍可读，`STALE`保留旧版且不回退最新版；缺失404、身份/hash/过期409、过大413、不可用503。请求排队、事务后和序列化后均复核有效期，重复读取无业务写入。

`archeaxis.project-handoff-snapshot/v1`严格DTO/Schema及14共同正负case，scope固定`LOCAL_HUMAN_READ_ONLY`，来源认证／选区仍`UNVERIFIED`，执行及知识接纳均false。前端类型和运行时校验由单一合同生成器产生，核对原提案fingerprint、producer/reference/期限及snapshot身份；JSON重复键（含转义键）和不安全数值拒绝。

现有page16显式“预览跨项目引用”→预览元数据→打开固定版本全文；保留原交换页、不导航可编辑Library。关闭、过期、workspace恢复、窗口停放或输入变化丢弃正文与迟到响应，Escape返回入口焦点；原始回执的诊断不保留editor_json。全文只在本机human阅读状态内，不将引用视为执行或接纳授权。

实际Core进程/排队回归及src-tauri有限桥调用自建Core属于真实工程接线、合成业务数据；真实页面浏览器采用隔离模拟桥。它们均不等于原生UI启动、已安装运行、OS URI注册、外部WORK-LAB／DESIGN-LAB真实返回链、完整无障碍或Owner验收。BE10仍PARTIAL。
