# R5 执行台账

### X14：项目溢出数据追踪（2026-09-13）

按受保护目录排除规则重新盘点项目自身：`.project-local` 13.22GiB（其中 `build` 10.35、
`cache` 1.54、`runs` 0.78、`inventory` 0.40），`.venv` 0.88GiB，`frontend` 0.10GiB，
`data` 0.09GiB；其余项目目录均低于0.01GiB。当前 Cargo debug 的 `deps` 4.93GiB、
`incremental` 4.23GiB 是现行构建缓存，release 约0.30GiB，均保留以免破坏当前验证环境。
`.hermes`、`.zcode`、`.codex` 未读取，作为受保护黑箱单列；不能把旧测量或卷总量差额归因给
项目溢出。后续如需进一步回收，只能在停止构建进程并逐路径复核后处理增量缓存，不能整体清理。

### X14：旧构建缓存精确回收（2026-09-13）

用户授权“审计有用的留下、无用的删除”后，先核对 `.cargo/config.toml`、CI 路由、当前进程
与现有启动收据，再删除两条可重建且已被替代的路径：根 `target/` 与
`.project-local/build/be268a2d33/cargo/`。PowerShell `Remove-Item -LiteralPath ... -Recurse -Force`
退出0，逐路径 `Test-Path` 后置条件均为不存在；未触碰同目录 `.NET` 产物、当前
`.project-local/build/cargo`、runs/收据、缓存、`.hermes` 或 `.zcode`。可读目录从约28.6GiB降至
约15.0GiB，释放量约13.6GiB（D盘剩余空间需以卷级快照为准）。删除对象均可由项目构建重新生成，
不等于产品功能验收；回滚方式是重新执行受控构建，不从外部复制产物。

### X03：固定版 DeepTutor Web 项目侧启动器（2026-09-13）

新增 `scripts/launch/deeptutor_web.py`，仅接受 DeepTutor 1.5.17 的真实解释器、Node.js
与 `deeptutor_web/server.js`，启动时将 `DEEPTUTOR_HOME`、前后端端口和 Web API 地址固定到
回环地址，并从子进程环境剔除常见 provider 凭据变量。子进程由启动器持有，运行目录由调用方
放在 `.project-local`；不复制或修改外部 Web 包。`tests/test_deeptutor_web_launch.py` 4项通过，
规范检查通过；受控只读实查确认共享安装版本与三个路径均存在。该切片尚未宣称默认 Avalonia
窗口已挂载、Core API 已连通或附件/会话全量回收，真实服务启动留待 X03 的可见入口验收。
回滚限新增启动器与定向测试，不改共享工具链和用户资料。

### X01/X03：CI收口与DeepTutor笔记产物保全（2026-09-13）

`tested-source-sha:23fe970d9fbb7f43da1878cc553ddd726bb4c0a5` 的
[vnext-ci run 34730748251](https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/actions/runs/34730748251)
已实查 completed/success。此前575eb57通过调度功能后，在Windows解释器回收的瞬时观察断言失败；
按CPython 3.12 redirector的kill-on-close job行为，将真实解释器句柄退出观察限定为最多1秒，
仍早于合成worker的10秒自然退出；没有跳过回收检查或改动产品超时。定向8项通过后云端通过。
这是vnext工作流通过，不代表主Python全门禁、安装态或GUI验收通过。

固定DeepTutor 1.5.17 / Python 3.11.15笔记服务实跑发现：原Markdown导出省略user_query与metadata。
新增项目侧custody适配器，完整JSON与上游Markdown分别带SHA-256，保留未知字段，不改变Core资格。
`r5-deeptutor-notebook-custody-bound` 经dev.py运行check_deeptutor_notebook.py，seed与独立进程
restart-and-rebuild均exit0；恢复包含原问题/回答/时间/元数据，并验证合成索引损坏重建不改原笔记哈希。
收据位于该run的artifacts/deeptutor-notebook/cf7c391b912546e2b01c74849435d4df/receipt.json，
绑定实际脚本/适配器与产物哈希。上游Markdown缺字段的初次断言失败保留，不作全格式导出通过解释。
试验禁网、不转发provider变量、只写新建合成home；未改共享上游、真实资料或既有Green。
尚未接入默认GUI，附件/会话全量回收、Core桥接、模型学习活动仍待实现。回滚限新增适配器及资格脚本，保留产物。

### X03/X08：去除默认启动与调度的开发环境依赖（2026-09-13）

`tested-source-sha:824aa3fef8fc72927575f8bca652df4603166aba` 的 CI run 34730069924
已成功安装锁定 Python 环境，但同一调度测试仍失败。用干净解释器、Python -I 与非仓库 cwd
复现 `ModuleNotFoundError: No module named 'shared'`；旧本机 editable 安装与 PYTHONPATH 掩盖了它。
worker 现按自身位置加载既有 shared/learning_scheduler.py，不改调度算法、不复制供体；
CI 增加隔离 worker 的跨重启回归，供体与测试变更触发相同工作流。
`r5-fsrs-clean-isolated-green`：32 passed，exit0；`r5-fsrs-clean-core-no-pythonpath`：
显式移除 PYTHONPATH 的真实 Core 测试 8 passed，exit0。均用上述干净 Python 环境经 dev.py 执行。

同时修正 desktop_launch.py 默认 Core 路径：直接读取 dev.layout 的 cargo_build，
主仓库复用 build/cargo，独立 worktree 保留隔离路径。原回归主仓库分支失败；修正后4项通过。
`r5-desktop-default-prepare` 用现有真实构建、不传 --core 即成功准备配置，exit0；没有打开窗口。
回滚限 worker 加载、启动器路径和对应 CI/回归修改。默认 DeepTutor GUI 集成仍未完成。

### X01：修复真实 FSRS 测试的 CI 环境前置（2026-09-13）

已上传的 `tested-source-sha:3e38b59f65b88dad24e6767bfef0c2bad0bb4db3` 在 vnext-ci
run 34729363429 的 launch_auth 测试失败：调度返回 unavailable，预期 fsrs；后续桌面步骤跳过。
工作流原先只绑定 runner Python，未安装调度依赖。现沿 uv.lock/ci 组按哈希安装到
dev.py 分配的 run/worker-env，先验证 fsrs 导入，再将实际解释器传给 Core。
pyproject.toml 和 uv.lock 变更同时触发该工作流；真实 FSRS 断言未削弱。

工作树基于上述 SHA。工作流原样环境准备经项目 dev.py 实跑：离线首次因缺缓存
annotated-doc 失败；公开包源按锁文件准备后 exit0，Python 3.13.14 / fsrs 6.3.2。
用新隔离解释器执行 `cargo test --frozen --offline -p archeaxis-api --test launch_auth`，
exit0，8 passed / 0 failed，含双身份权限及真实 FSRS 跨重启状态。
运行目录为 `.project-local/runs/be268a2d33/r5-ci-worker-bootstrap-network/`
和 `r5-ci-clean-worker-launch-auth/`。这证明本地环境修复；新 SHA 的云端 CI 待上传后核验。
回滚仅撤销本次工作流修改；不改产品调度、共享工具、真实资料或既有 Green。

### checkpoint Python主集及两项门禁修正（2026-09-13）

r5-checkpoint-python-primary通过dev.py --pytest --full -- -q --maxfail=3执行到底，exit1：
2744 passed、2 failed、7 skipped、135 subtests passed，203.92秒。未启用--run-network。
失败1：新增hashlib import令规范检查器既有sys.path调用从19移到20；只更新原精确路径/行/AST记录，未增豁免。
失败2：旧AXR060只允许发布commit/tree，把R5 source head_blob等当作未声明发布SHA。
现逐项git cat-file核类型，并git rev-parse baseline:path核源blob绑定；基线tree从commit推导。
历史上游commit只沿既有DeepTutor文档声明，明确不属于本地发布；本地main快照按实际ref登记，非云端证明。
主Python CI已有fetch-depth:0；缺历史Git对象的checkout将明确失败，不自动联网补全或伪通过。

r5-primary-failures-targeted仍1失败（本地main快照未声明）；补声明后r5-primary-failures-green exit0/55 passed，
r5-primary-failures-lint exit0。修正后尚未重跑整个主集，原失败记录保持，不称主集全绿。
源绑定：`.project-local/runs/be268a2d33/r5-primary-checkpoint-binding/artifacts/primary-checkpoint/7c3424aded3947e2945edbdfe8b13e5d/binding.json`。回滚限架构行号、类型化SHA审计和main快照声明；不改变发布记录、冻结包或产品数据。

### checkpoint C#生产绑定与Avalonia构建（2026-09-13）

全部经dev.py、本机.NET10.0.400、--no-restore，复用既有build/be268a2d33/dotnet。
r5-checkpoint-desktop-supervisor exit0，9个PASS含角色隔离、恶意握手、取消、实际Core/Python与短路径。
r5-checkpoint-desktop-build exit0，Avalonia主工程0 warnings/0 errors。
r5-checkpoint-desktop-vocabulary exit0，29个共享wire cases由生产C#绑定解析。
r5-checkpoint-desktop-smoke exit0，--no-build --no-restore -- --smoke，正式主程序无界面拉起并回收自有Core。
默认烟测SQLite位于本run/tmp，未覆盖用户数据库或Green。可见GUI/默认学习工作台/安装态仍未测。
源和当前Desktop.dll/Core.exe哈希：`.project-local/runs/be268a2d33/r5-checkpoint-desktop-binding/artifacts/desktop-checkpoint/3a1b6b0f3e1d40b695e9c9705f19f9d2/binding.json`；测试基线HEAD未变，工作树有修改。
本轮无下载、发布包、删除、提交/上传，额度实查61%；60%时按授权交接上传。
回滚沿原桌面源改动，保留用户数据及本轮验证产物；不把构建通过当产品完整可用。

### checkpoint Rust工作区与OCR实际分支（2026-09-13）

r5-checkpoint-rust-workspace：经dev.py、已有rust-runner及PYTHONPATH=repo执行
cargo test --frozen --offline --workspace，exit0，工作区单元/集成/doc-test完成。
复用build/cargo，完成必要增量编译，现有unused警告保留；无依赖下载或发布构建。
不能从cargo汇总数推断所有带提前return的测试实际执行。

本机tools/tesseract/tessdata/eng.traineddata存在；对已知OCR静默返回风险，
r5-checkpoint-ocr-observed仅重跑ocr_job_end_to_end和pdf_ocr_chain并--show-output，
1+3 passed、0 failed/ignored、无skipping提示，exit0；完整输出在
.project-local/runs/be268a2d33/r5-checkpoint-ocr-observed/artifacts/ocr-observation/8f0ac485b50c4ce3ac6b401803f7a768/。
这是合成OCR/PDF测试链验证，不代表真实资料全链路精度或所有格式质量。
完整Rust源和当前Core二进制绑定：`.project-local/runs/be268a2d33/r5-checkpoint-rust-binding/artifacts/rust-checkpoint/14d940d378cd42efa1e90efacdcb846f/binding.json`。
尚未进行本轮C#汇总、py-primary、wheel或云端门禁；没有删除/提交/上传。
回滚沿各实现切片；本轮只生成验证证据，保持原学习/用户资产。

### checkpoint Python汇总与worker门禁（2026-09-13）

冻结当前代码改动后r5-checkpoint-python-aggregate exit0：12个受影响测试文件合计204 passed、11 subtests passed，25.71秒。
覆盖运行路径/盘点/规范、候选包、Core/桌面开发启动、批量导入、截图、FSRS和MCP探针路径。
r5-checkpoint-workers exit0：现有worker门禁的实际text/canvas/subtitles/html/docx正负样本通过；
其余Office引擎仅probe，不冒充全格式执行/质量达标。
239改动路径分类unknown_paths=[]，所需门禁包含static/lint/contracts-vnext/desktop-vnext/rust-vnext/workers-vnext/
py-primary/format-targeted/security-targeted/wheel-smoke/ci-verdict；无full-qualification自动扩张。
本次未执行py-primary全量、wheel或云端门禁，不宣称全部门禁通过。
分类收据：.project-local/runs/be268a2d33/r5-checkpoint-classification/artifacts/classification/8b1df90e658141f4bcc65366b7bdeb0a/plan.json。
当前受测工作树源哈希（在本次台账更新前）：`.project-local/runs/be268a2d33/r5-checkpoint-aggregate-binding/artifacts/checkpoint/b3e35a142a834982823a5cc26a214959/binding.json`。
全部复用本地环境及dev.py路由；无下载、发行包、删除、提交/上传。最近额度62%。
回滚沿各代码切片范围；本条只是汇总证据，不改历史验收状态。

### X02 新文件规范覆盖与R5原件保护（2026-09-13）

r5-checkpoint-untracked只读检查191个本次新文件，发现8个原包JSON缺末尾LF和3个sidecar的CRLF。
未知SESSION-RESTART文件不读取/修改。r5-checkpoint-r5-integrity exit0，173个active文件完整性PASS；不是产品测试。
8个JSON逐字节对照用户原ZIP的active条目一致；保留原字节，在规范检查中逐路径固定SHA256。
三个本轮sidecar仅转LF。r5-added-originals-red exit1/8失败，green exit0/30 passed，lint exit0。
不豁免整个原包目录，原件追加LF或修改内容均报错；异路径仍执行普通格式检查。
源绑定及最终tracked+191个新增文件检查见`.project-local/runs/be268a2d33/r5-added-originals-final/artifacts/normalization/7694a8c2d6f143b1823313b9801b02f9/result.json`。
回滚只撤回新增哈希条目/测试及sidecar换行，冻结原包无改动；没有删除、提交或上传。

### X01/X02 checkpoint规范冲突与冻结原件保全（2026-09-13）

r5-checkpoint-conventions exit1：本轮learning.rs的CRLF，以及0910原包两个JSON缺末尾LF。
HEAD与工作树对这两个JSON的git diff为空；r5-checkpoint-head-conventions证实HEAD同样报两项。
learning.rs只将515个CRLF转LF；不更改逻辑，旧运行收据仍绑定原源哈希。
对原包两个JSON不改字节：规范检查固定精确路径和完整SHA256，仅原始字节豁免缺末尾LF，
任何变更均frozen-original-mismatch；其他路径不豁免，无整个目录跳过。

r5-frozen-convention-red exit1复现；green exit0/22 passed，覆盖原字节、异路径、追加LF和内容变更；
lint exit0。r5-checkpoint-conventions-final exit0（tracked worktree范围）；
r5-checkpoint-architecture及r5-checkpoint-contracts exit0。未检查的untracked原包不能据此称通过。
r5-checkpoint-r31-integrity exit1于历史EXECUTION.md哈希；未改旧台账/manifest，旧包整体校验仍失败。

源绑定：`.project-local/runs/be268a2d33/r5-checkpoint-normalization-binding/artifacts/source-binding/d91460f17843404ca7bcb38b8c45a2df/binding.json`。本轮未运行全CI、未提交/上传。
回滚限规范检查/测试和源换行改动；保留冻结JSON、历史状态和收据。额度最近实查62%。

### X01/CLEAN09 容量预算未知状态不再退出成功（2026-09-13）

显式--budget遇私有/缺失/未完整测量组时，原CLI虽标UNKNOWN却exit0。
现返回exit3并列unknown_budget_groups；已知超限优先exit2，扫描错误仍exit1。
未配置预算的诊断保持原行为；没有猜测GB阈值、读取私有内容或自动清理。

r5-budget-unknown-red真实CLI复现exit0误报；green为20 passed、2 subtests passed，exit0；
r5-budget-unknown-lint两文件Ruff exit0。测试使用项目run内合成Git目录，
不是重新扫描真实仓库，也不声称完整容量预算/轮转已交付。
源绑定：`.project-local/runs/be268a2d33/r5-budget-unknown-binding/artifacts/source-binding/07f2e463814b455296873fe1be5c7723/binding.json`；基线HEAD未变，修改工作树受测。
回滚限新增未知状态返回码/报告字段及测试，不修改历史盘点或用户数据。

### X01 主checkout Cargo缓存统一（2026-09-13）

实际差异：bare Cargo已由.cargo/config.toml路由到.project-local/build/cargo，
dev.py却默认build/<worktree-id>/cargo，导致同一checkout可能重复生成大型构建。
现仅主checkout复用既有build/cargo；linked worktree仍使用独立身份目录，
其他.NET/venv构建路径不变。不移动、删除历史缓存，不声称释放空间。

- r5-cargo-target-red：exit1，新增测试复现两个入口路径不一致。
- r5-cargo-target-green：exit0，运行路径/约定40 passed、9 subtests passed。
- r5-cargo-target-live：exit0，两次真实cargo metadata --no-deps --format-version 1 --frozen --offline，包装/裸入口均为项目build/cargo；无重编译。
- r5-cargo-target-lint：exit0，两个改动Python文件Ruff通过。
- 源绑定与实际路径：.project-local/runs/be268a2d33/r5-cargo-target-live/artifacts/cargo-routing/81a1ca37bd4842e087ab11df17146712/result.json。

基线HEAD仍c06b234ca335b9cbb2c1fde270851e2390c36b89，验证对象为未提交工作树。
回滚只撤回本次cargo_build路径选择及对应测试/文档，不删除现有输出。
清理仍等待旧target精确路径授权；已验证产物不纳入旧候选。账户实查剩余63%。

### X01/X08 FSRS有界进程调用（2026-09-13）

旧SchedulerClient会卡在stdin写、read_line及wait。现共用20秒默认deadline（显式上限60秒），
三路IO独立有界读取/写入；请求与stdout各64KiB，stderr32KiB，需三路完成且子进程退出才解析结果。
超时/输出超限先kill并wait本次直接FSRS子进程，随后确认IO线程结束；超大输入在spawn前拒绝。
脚本以-B运行，Windows仍CREATE_NO_WINDOW；不改外置Python/共享环境或安装依赖。

|run|实测|
|---|---|
|r5-scheduler-deadline-red|exit1，新增超时方法未实现|
|r5-scheduler-deadline-green|exit0，7项适配测试|
|r5-scheduler-deadline-process|exit0，8项；静默、半行、不读stdin、stdout/stderr超限、关pipe后不退出均有界；持有Windows进程句柄证明目标从活跃变为退出；超大请求没有启动脚本|
|r5-scheduler-deadline-transaction|exit0，2项API内部helper/domain测试；真实Python超时保留unavailable收据，下一事务可写；并非HTTP超时故障注入|
|r5-scheduler-deadline-live|exit0，真实认证Core重启8项、旧调度3项、新状态API2项，共13项通过，无ignored|

全部通过dev.py、显式PYTHONPATH=repo、已有rust-runner及cargo --frozen --offline；
复用build/cargo，两个旧Rust未使用警告保留。只读reviewer未发现确定重要问题，未运行测试。
边界：系统kill/wait未独立计时；只管理直接FSRS子进程，任意后代未覆盖；外部持有pipe时清理
窗口1秒后明确cleanup incomplete，不能声称全部线程/后代已回收。默认GUI和安装态仍待验收。
回滚只限SchedulerClient/新增测试，保留学习事件；源与二进制绑定见`.project-local/runs/be268a2d33/r5-scheduler-deadline-binding/artifacts/source-binding/7cb254cfa84145208556b7c3bc0333b0/binding.json`。

### X05/X08 Core完整FSRS状态与真实重启（2026-09-13）

新增domain事务record_review_with_state：先核事件键/完整规范化请求摘要，再在写者事务内
读取上次FSRS状态、调用计算、追加完整状态到learning_events.outcome.schedule，写入原收据。
未新增表或修改schema；分钟级due原样保存，next_review_days=0不再丢日期。
重复请求不计算、不写，原失败/成功收据稳定重放；同键不同请求冲突。correct_streak改为
解析实际JSON字段，支持旧两种格式及compact JSON，拒绝嵌套文字、数字1冒充布尔true。

新HTTP入口`/api/v1/learning/reviews`只准human，客户端不得提供card_state，Core自动恢复。
旧/events及旧哈希协议保留，新入口不伪迁移旧阶梯事件。协议和回滚见
[R5-LEARNING-STATE.md](R5-LEARNING-STATE.md)；JSON Schema已验证，示例通过。
SchedulerClient转交六项完整状态，Windows子进程设置CREATE_NO_WINDOW。

|run|结果|
|---|---|
|r5-learning-state-red|exit1，新增domain函数未实现|
|r5-learning-state-green|exit0，domain 3新+5旧+1闭环回归|
|r5-learning-state-review-red|exit1，审查复现仅时间字符串被SQLite接受|
|r5-learning-state-reviewed-green|exit0，6+5+1通过；时间-only、无穷、非法日、缺step、due不一致均拒绝|
|r5-learning-state-api-red|exit1，新入口404|
|r5-learning-state-api-green|exit0，新API2+旧API5+旧调度3通过|
|r5-learning-malformed-red|exit1，测试误引用不存在的SCHEMA常量，非产品失败|
|r5-learning-malformed-red-fixed|exit1，改用实际init_workspace后复现损坏worker结果导致复习丢失|
|r5-learning-malformed-green|exit0，损坏结果转换明确unavailable收据，保留先前状态；注入失败单测，不冒充真实故障worker进程|
|r5-learning-state-live|exit0，真实认证Core/Python及进程重启的launch_auth8，新API2、旧API5、旧调度3|
|r5-learning-streak-type-red|exit1，JSON数字1被误认correct=true|
|r5-learning-domain-final|修复类型后exit0，6状态+5旧调度+1旧闭环/恢复=12，通过，无ignored|
|r5-learning-api-final|最终domain下exit0，1失败注入单测+8真实认证进程+2新API=11，通过，无ignored|

全部cargo经dev.py及已有rust-runner.py，PYTHONPATH显式仓库根，--frozen --offline，
复用build/cargo，无网络/安装/共享库写入；两个原有Rust未使用警告保留。
只读reviewer指出时间语法、无穷值和坏调度丢复习三个具体问题，已复现修复；不是Q00/Q01审计。
真实认证Core首次Good后重启，再Good得到2026-09-04T00:10:00+00:00；机器伪造human头仍403。
此为后端真实跨进程闭环，不是默认GUI或发行包验收。Scheduler旧同步等待仍缺deadline，下一步处理。
源/二进制绑定见r5-learning-state-binding/artifacts；旧绑定保持原SHA，不混用新Core。
回滚限新domain/API/适配/契约/测试，保留追加事件和旧接口；不清理用户数据。

### X08 FSRS重启状态丢失修复（2026-09-13）

实际复现：新卡第一次Good后序列化，启动第二个worker再Good，旧结果为9月2日00:20，
原FSRS连续计算应为9月4日00:10。worker漏step/last_review且复用展示层四舍五入值：
成熟卡稳定度98.74965869656663被截成98.75。现返回原Card精度及步骤/复习时间，
输入显式null step保留；共享FSRS算法与展示summary不改。协议仅增加可回传字段。

`r5-fsrs-restart-red` exit1/2失败；`r5-fsrs-restart-green` exit0/22 passed，
含四次独立Python进程JSON往返，对照不中断FSRS：学习→复习→重学→复习；
`r5-fsrs-restart-lint` Ruff exit0，diff检查exit0。
`r5-fsrs-api-regression`启动辅助runner因缺PYTHONPATH退出1，为环境失败，未跑Rust测试；
显式PYTHONPATH=仓库根后`r5-fsrs-api-regression-fixed`运行离线cargo test
--frozen --offline -p archeaxis-api --test learning_schedule_api，exit0/3 passed/0 ignored。
复用现有build/cargo，保留两条既有Rust未使用警告。

当前Core客户端仍丢弃详细卡状态，数据库未存这套状态；API无schedule_state仍走旧阶梯，
故这里只证明worker跨进程连续复习修复，不声称用户数据库重启学习闭环通过。
M0保留旧源hash和收据后更新当前worker；源码绑定见r5-nuget-fsrs-binding/artifacts/source-binding。
本轮均基于c06b234 + dirty，未提交/上传；账户剩余66%。回滚限worker及新回归与M0侧车。

### X03上游生命周期只读核查（2026-09-13）

读取现有共享DeepTutor1.5.17的公开安装源，未启动服务、访问旧runtime home或账号文件。
标准launcher绑定0.0.0.0并有端口冲突处理，不直接采用；API lifespan启动partner/cron/GitHub同步，
PocketBase仅在配置URL时ping。空home默认无sources/partners仍需实际运行确认。
上游另有读取本机代理账号/模型列表的接口，因此只绑定loopback不足以完成项目权限边界；
项目侧挂载必须限定启用接口、使用新home和明确环境，不把独立Welcome作为集成。
静态来源：runtime/launcher.py、api/main.py、services/base_sync.py、services/github_source/sync_service.py、
services/partners/manager.py、services/pocketbase_client.py、services/config/runtime_settings.py。
共享库未修改；默认入口挂载、Core资料投影与产物回收仍未实现。

### X01 NuGet遗漏缓存路由修复（2026-09-13）

`r5-nuget-cache-baseline`经dev.py调用实际.NET10.0.400的`nuget locals all --list`，exit0：
HTTP/plugins缓存仍指向用户LocalAppData，packages已在项目、scratch已随TMP。
只查询工具报告的路径，未读取、搬动或清理旧缓存。现新增NUGET_HTTP_CACHE_PATH、
NUGET_PLUGINS_CACHE_PATH至项目cache，NUGET_SCRATCH至独立run/tmp，全部经过safe_path。
跨run只复用缓存；临时scratch隔离，覆盖父进程传入的外来缓存位置。

`r5-nuget-routing-red` pytest新用例exit1，真实子进程继承外来缓存导致边界断言失败；
`r5-nuget-routing-green`完整test_dev_paths.py exit0，18 passed/9 subtests；
`r5-nuget-cache-live`同实际.NET命令exit0，四类路径全在.project-local；
`r5-nuget-routing-lint` changed-file Ruff exit0，git diff --check exit0。
上述runs均在.project-local/runs/be268a2d33，基线c06b234 + dirty，Python3.13.14。
未执行restore/下载或声称旧缓存已清理；未证明任意第三方插件的所有写入受控。
回滚限dev.py三项环境变量及路径验证、对应测试；不删除缓存或改全局NuGet配置。

唯一冻结计划：[R5 TASKS](../authority/taskpack-0912-r5/TASKS.json)，
`AAK-FOLLOWUP-20260908-R3 / R5`。本侧车不修改原任务/验收正文。
状态：[R5-STATE.json](R5-STATE.json)。历史证据保留在
[0910 台账](../authority/taskpack-0910-r3/EXECUTION.md)及原 STATE，绑定各自 SHA。

## 当前范围

用户2026-09-13要求本执行者连续推进，优先仓库规范化和清理；通用账户额度
剩余60%时整理交接并上传已验证、任务归属明确的改动。未知 `.zcode/`、
`SESSION-RESTART-2026-09-12.md` 保留；不读私有状态、不访问E、不修改共享库或真实资料库。
删除以精确路径清单和实际授权为准；发布、签名、安装覆盖不在本范围。

## 记录

|卡|基线/源树|实际结果|命令与证据|限制/回滚|
|---|---|---|---|---|
|X00-01|HEAD c06b234ca335b9cbb2c1fde270851e2390c36b89；tree 281255538ee3d4a4235facfddaf01d2b97d406ba|23原任务、42专项差分已列；R00-R16原状态保留；没有父任务自签通过|`.project-local/runs/be268a2d33/r5-x00-baseline-20260913/artifacts/X00-01-DELTA.json`及md；生成命令经dev.py，exit 0|只读静态/历史证据核对，产品测试NOT_RUN；文件最后提交不是测试SHA；无需产品回滚|
|X00-02|同HEAD，安装及指针为未提交diff|原ZIP active与source-active逐字节一致，安装173文件/3064455 bytes；更新当前指针，侧车置于包外|`dev.py --run-id r5-package-verify-20260913 -- .venv/Scripts/python.exe -B docs/authority/taskpack-0912-r5/verify_package.py` exit 0|包完整性PASS不是产品PASS；保留旧证据。回滚仅本轮新增包/侧车与指针diff，不能覆盖未知改动|
|X02-01 / X14预检|同HEAD，非原子元数据快照|可见范围35379878892 bytes/218586 files；54 FileNotFoundError、27 reparse跳过；不报全仓总量|`r5-capacity-before-20260913/artifacts/inventory.json`（上述同worktree run根）；inventory命令exit 1|排除私有目录；逻辑大小非物理占用；尚未删除。旧容量值不当本次值|
|X01-01 / CLEAN01边界修复|同HEAD加本轮diff|盘点器默认排除.zcode；合成私有目录扫描负例先失败，修后盘点/运行根18项通过|`r5-inventory-red-20260913` exit 1（预期RED）；`r5-inventory-green-20260913` exit 0 / 18 passed；`r5-inventory-ruff-20260913` exit 0|测试在项目.venv经dev.py运行；未运行产品全链。回滚限inventory_project.py及对应测试diff|
|X00-02入口验证|同HEAD加本轮diff|6个当前入口包含R5；相关相对链接存在；无替换字符；173原包文件均无CRLF，原包未改|`r5-pointer-check-20260913` exit 0；git diff --check exit 0|当前指针一致不等于所有历史文档被改写；历史不批量替换|
|规范化定向门|同HEAD加本轮diff|架构、语言边界、0910证据索引检查均PASS，exit codes [0,0,0]|`r5-normalization-checks-20260913` exit 0；最终git diff --check exit 0|无全量产品测试/CI/安装声称；当前证据索引实报81条tracked指针，与旧摘要80不同，保留各自时点|

### 清理候选的本轮精确范围

2026-09-13后续更正：下表为历史测量。`.project-local/build/be268a2d33`
现含本轮通过验证的.NET产物，**移出当前清理候选，保留**。只有旧`target`
继续待精确路径批准；执行前仍须重新核对大小、占用、链接和Git状态。本轮未删除。

本次补`.gitignore`的`.zcode/`规则，防止未知代理状态误入提交；未读取内容。
`git check-ignore -v -- .zcode target .project-local/build/be268a2d33` exit0，
三者均命中；`git diff --check` exit0，R5-STATE JSON解析exit0。
基线仍为c06b234 + dirty；未运行新产品测试，未提交/上传。账户实查剩余68%。
回滚仅新增忽略行和本次侧车说明；忽略不等于删除，也不等于释放磁盘空间。

|绝对路径|逻辑bytes|按文件ID去重后的逻辑bytes|当前动作|
|---|---|---|---|
|`D:\All projects\ArcheAxis-Knowledge-OS\target`|6151810038|5726392280|等待精确路径批准|
|`D:\All projects\ArcheAxis-Knowledge-OS\.project-local\build\be268a2d33`|9017545108|8484029394|历史盘点值；已移出候选，保留当前验证产物|

两个根及后代检查未见reparse/读取错误；Cargo子目录含标准CACHEDIR.TAG；不含tracked文件；
未发现cargo/rustc/archeaxis-api/dotnet进程。保留较新的 `.project-local/build/cargo`
（其中实际Core可执行名为archeaxis-api.exe）、.venv、cache、runs及所有私有/真实资产。
下一步删除前仍须复核进程与路径，不能把此快照当永久许可。

容量原始证据：`r5-candidate-sizes-fixed-20260913/artifacts/candidate-sizes.json`。
首次辅助测量误用Windows DirEntry.stat的零inode，去重数字作废；修后使用os.stat取得文件ID。
辅助收据中的allocated_bytes实际来自GetCompressedFileSizeW，**不作为NTFS簇分配或可释放值**；
本表只使用逻辑bytes和去重逻辑bytes。跨目录硬链接、并发写入会影响释放量，实际值待删除后测卷空闲。
54个原盘点错误位于历史测试的超长路径；后续长路径修复已消除同范围扫描错误，
不按旧错误把路径当作不存在或据此清理。

## 当前复用与缺口

### R5 归属收口（X02/REPO02、X13提前贡献）

新增33条精确/维护归属规则覆盖历史69项，另禁止提交.zcode私有状态；
现有1793条tracked路径100%归属，0歧义、0禁止提交路径被跟踪。
新包/侧车尚未跟踪，不包含在1793分母中；统一落在已有docs规则下。
这不证明1246旧资产已语义吸收，不改变X13的后续依赖或父任务完成状态。

检查器现在用记录提交时的DIRECTORY_AUTHORITY复算历史，而不是套用当前规则；
R5侧车用current_ownership登记当前空缺口，0910原记录保持原样。
RED：`r5-path-history-red` exit 1，因旧接口不支持历史规则读取；
GREEN：`r5-ownership-tests` exit 0 / 20 passed；
目录权威JSON Schema：`r5-ownership-validate` exit 0；
归属门：`r5-ownership-gate` exit 0。
回滚只涉及本轮DIRECTORY_AUTHORITY、路径检查器/测试、新侧车及索引diff；不触碰旧证据。

- 复用：Rust知识修订/审校事务、v3 10/11/12/13表恢复、事件键/payload冲突、真实MCP SDK接线。
- 已修：语言索引/验证策略0906指针及DeepTutor旧写入指针已定向修正；当前入口定向检查见上表。
- R5新增契约缺口：可信身份签发、曝光/原回答/评价来源/事件版本、结构寻址。不得直接向additionalProperties=false的v1协议塞新字段。
- 清理先做现有工具输出归属、旧target与构建目录预演；.venv可用且包含pytest/jsonschema，保留用于后续测试。
- R10宿主、R13完整桌面包、R15全格式和R14/R16独立审计历史缺口仍然有效；不以本台账改变其原状态。

### 长路径、增长诊断与隔离探针（2026-09-13续）

本批仍为同一HEAD加未提交diff；下列run均位于
`.project-local/runs/be268a2d33/<run>/`，命令/退出码见各自`artifacts/execution.json`。

|贡献|实际验证|边界|
|---|---|---|
|X02元数据盘点|`r5-inventory-longpath-red-clean` exit 1复现Windows长路径漏计；`r5-inventory-longpath-green` exit 0 / 10 passed；`r5-inventory-longpath-real` exit 0，15.31秒，35384193199逻辑bytes / 219038 files / 0错误|27 reparse、324排除项仍排除；非私有目录总量或磁盘物理占用。仅在根边界验证后给长路径加本机前缀，未绕过ACL|
|X01容量诊断|`r5-capacity-diagnostic-red` exit 1；`r5-capacity-cli-check` exit 0 / 15 passed；CLI支持显式预算，超限exit 2；不同根/单位/不完整观察不输出可信增减|无默认阈值、无自动删除；缺失/私有根不伪报预算内|
|X01实际容量比较|`r5-capacity-live-compare` exit 0，COMPARABLE_OBSERVED_SCOPE，0扫描错误；target前后均6151810038 bytes，delta 0|UNCONFIGURED预算；尚未清理，不声称释放空间|
|X01 CI路由|`r5-ci-routing-check` exit 0：Rust、worker、contract、Desktop分别命中对应vNext gate；dev.py命中四门|本地路由分类，未验证云端CI|
|X02复用现状|`r5-m0-reuse-tests` exit 0 / 37 passed、47 subtests passed：FSRS调度、文本NDJSON、MCP surface|FSRS 6.3.2实际可用；该测试中的MCP surface为隔离端口，不能代替真实SDK证据；逐供体注册与1246旧资产语义吸收仍未完成|
|X01 MCP输出止增|`r5-mcp-paths-red` exit 1；`r5-mcp-paths-green` exit 0 / 11 passed（含运行根回归）；`r5-mcp-paths-final-lint` exit 0|数据库由dev.py验证的当前run/artifacts分配独立UUID目录，拒绝外来run；未清理历史r11-mcp目录|
|MCP真实客户端复核|`r5-mcp-live-final` exit 0；SDK 1.30.0 stdio连接成功；搜索200、任务收据写入201并读回succeeded；人类审校工具拒绝；unmeasured仍是独立测量状态|复用现存Core二进制，不签质量/训练/GUI验收PASS；原型固定测试身份不是R5可信身份签发实现|

本批真实MCP使用`.project-local/build/cargo/debug/archeaxis-api.exe`，SHA256
`F85D72C68370C5095C3ED7054F58187D9828CBEAD48F808807D5FB58EACD3071`；
本次未重建，不能把此二进制归因为当前源代码HEAD。探针仅启动/终止自己创建的Core进程。
修正探针已有SIM117嵌套上下文样式后重新运行真实SDK探针，退出0。

补充验证：`r5-authority-doc-tests` exit 0 / 31 passed；
`r5-normalization-lint-final` exit 0（盘点器/路径检查器及其测试）。
回滚限本批inventory、probe、对应测试与侧车diff；保留历史run和原始0910收据。
当前账户通用额度实查剩余81%，60%交接阈值未触发。

### 开发产物统一分配（X01，2026-09-13续）

`dev.py`新增`artifact_directory(root, namespace)`：沿既有工作树/run校验，
仅允许单层命名空间，UUID子目录独占创建。6个历史探针改接此入口：
R10 Core journey、R10 host panel、R11 machine receipt、R11 MCP、R11 unseen、R15 directory batch。
R15不再删除固定目录中的旧manifest，也不覆盖旧合成语料。

|run|命令/退出码与结果|限制|
|---|---|---|
|r5-artifact-directory-red|dev.py --pytest tests/runtime-paths/test_dev_paths.py -q，exit 1，缺少分配接口|预期RED|
|r5-artifact-directory-green|同运行根测试加tests/test_mcp_probe_paths.py，exit 0；14 passed、5 subtests passed|覆盖不同子目录、非法命名空间、外来run拒绝；保留原中文路径/并发worktree/链接回归|
|r5-r10-journey-isolated|dev.py执行r10_core_journey_smoke.py，exit 0；导入202、搜索200、学习事件与引用201|既有合成样本，不签全格式精度|
|r5-r11-receipt-isolated|dev.py执行r11_machine_receipt_smoke.py，exit 0；写201/读200|收据中模型名是测试字段，未调用该模型|
|r5-r10-panel-isolated|dev.py执行r10_host_panel_smoke.py，exit 0；页面/健康/人机状态200，未知容器404、缺ID400、Core离线503|本地真实HTTP；未打开浏览器，也不是DeepTutor内挂载或Windows完整GUI验收|
|r5-r15-batch-isolated|dev.py执行r15_directory_batch_smoke.py，exit 0；首轮9次Core调用，次轮5 unchanged/0调用，一文件变化后2调用，manifest 15行|包含真实合成PDF；验证导入/入队/恢复，不等于PDF解析执行成功|
|r5-probe-routing-final-lint|dev.py执行changed-file Ruff，exit 0|此轮列表为dev、运行根/MCP测试及R10/R11五个probe；R15后续单独检查|

以上Core实跑继续使用上一节同哈希现存二进制。R11 unseen只改输出目录，未读取语料内容、
未重新执行评估，不能把其他探针通过代签unseen指标。运行根变化可按这6个probe及dev/test的本轮diff回滚；
旧固定目录全部保留。

剩余固定路径已定位：`scripts/ingest/directory_batch.py`的默认可恢复manifest、
`scripts/launch/core_launch.py`的启动状态，以及0910安装快照读取器。
前两者具有跨调用恢复语义，不能直接换UUID丢失续跑/停止定位；安装快照是历史证据输入，不迁移。

### 批量导入恢复隔离与遍历剪枝（X01/X02，2026-09-13续）

同HEAD加未提交diff。`scripts/runtime/dev.py::state_path`为需要跨run恢复的开发元数据
提供`.project-local/state/<worktree-id>/<namespace>/<filename>`路径；不自行创建目录或文件，
不改HOME。该目录不作临时数据自动清理目标。目录名、文件名和全部已有祖先仍走既有边界验证。

批量导入默认manifest从仅按文件夹名改为完整来源路径＋Core URL的SHA256键；
同名不同目录/不同Core地址不共用，换run不丢续跑定位。旧basename清单保留、不自动迁移，
发现时要求操作者通过已有`--manifest`显式选用。地址相同但底层数据库替换仍缺工作空间身份绑定，
本次不伪造X04身份协议；明确指定manifest的兼容行为保留。

|run|验证|结果/限制|
|---|---|---|
|r5-batch-state-red|dev.py --pytest tests/test_directory_batch.py tests/runtime-paths/test_dev_paths.py -q|exit 1：新增状态路径/清单接口缺失|
|r5-batch-state-green|相同两组测试|exit 0；30 passed、9 subtests passed；稳定路径、来源/目标区分、越界名称拒绝|
|r5-batch-state-cli|目录导入测试|exit 0；18 passed，CLI dry-run不创建默认状态目录/文件|
|r5-path-ref-red|路径归属测试-k symbolic|exit 1：记录使用HEAD时检查器抛异常|
|r5-path-ref-final|路径归属全文件测试|exit 0；21 passed；非SHA记录改为具名失败，历史测量仍用原SHA规则。中间green因已有断言依赖错误文本失败，已保留兼容文本修正|
|r5-batch-pruning-red|目录导入两个遍历负例|exit 1：真实Windows junction把外部合成文件带入来源列表；测试用联接已移除，目标合成文件未删|
|r5-batch-pruning-green|目录导入测试|exit 0；20 passed，目录层排除隐藏/构建目录并拒绝链接/reparse；不读取真实私有状态|
|r5-batch-pruning-lint|本批6个Python文件Ruff|exit 0|
|r5-batch-pruning-live|dev.py运行R15真实Core探针|exit 0；首轮9调用、次轮0调用/5 unchanged、一文件变化后2调用；排除记录改为目录层`.git`，不列出其内部私有文件|

实测项目`.venv/Scripts/python.exe`为Python 3.13.14；共享基础解释器3.12的历史检查不是此轮测试环境。
本次未安装依赖。Core探针仍使用前述固定哈希的已有二进制，未重建或发布。
回滚限定dev、directory_batch、path checker及对应测试的本轮diff；保留旧manifest、所有真实资料和历史证据。

### 启动探测、真实浏览器截图与OCR（X01，2026-09-13续）

正常启动器的RUNDIR同时承载数据库/备份，不能当开发缓存自动迁移。
本批只把`core_launch.py --probe`的默认数据库和启动记录隔离到dev.py分配目录；
显式`--db`仍按操作者选择，正常启动/停止/备份/恢复路径保留。

|run|实际命令/验证|结果与范围|
|---|---|---|
|r5-launch-probe-red|dev.py --pytest tests/test_core_launch.py -k probe_does -q|exit 1，旧探测用了持久数据库并覆盖记录；只在合成临时目录复现|
|r5-launch-probe-green|test_core_launch.py全文件|exit 0 / 20 passed，含停止、备份/恢复、清单拒绝及探测隔离|
|r5-launch-probe-live|dev.py执行core_launch.py --probe|exit 0，已有Core在新隔离数据库启动/退出；9项依赖检查true；DeepTutor端口未运行，Ollama端口可达不等于模型质量|
|r5-ocr-preflight|项目解释器导入PIL并定位Tesseract|exit 0；Pillow 12.3.0，现有共享toolchain Tesseract；未安装/修改共享库|
|r5-ocr-real-regression|test_worker_ocr_route.py、test_worker_ocr_reading_order.py、tests/workers/test_ocr_profile.py，带JUnit|exit 0 / 22 passed、18 subtests passed，无skip；真实OCR样本与部分协议/负例，非全语料精度|
|r5-screenshot-probe-red|test_x01_screenshot_ocr_probe.py|exit 1：仅ARCHEAXIS也成功、1234误命中123、默认目录回落temp；RED的temp被替换为项目合成目录，未写系统TEMP|
|r5-screenshot-probe-green|同测试|exit 0 / 4 passed：全部完整ASCII标记、默认run/artifacts；显式目录限制在项目.project-local且拒绝覆盖page.png|
|r5-browser-cleanup-red|test_web_screenshot.py|exit 1：模拟profile删除失败仍返回成功|
|r5-browser-cleanup-green|test_web_screenshot.py及截图OCR探针测试|exit 0 / 12 passed；超时/KeyboardInterrupt清理自有profile，删除失败具名报错且检查不存在后置条件|
|r5-screenshot-ocr-final|dev.py执行x01_real_screenshot_ocr.py|exit 0，msedge.exe-headless真实本地HTML截图→Tesseract；4个ASCII词全中，png 29015 bytes|
|r5-screenshot-cjk-measurement|同PNG经worker_ocr.py --profile local-2026-09-05.yaml --lang eng+chi_sim|exit 0，空白归一化后与`ARCHEAXIS OCR PROBE 123 星环 OCR 探针 2026`完全一致；仅这一合成样本，非中文全链精度|

PNG SHA256：`4bf437c8a4e50f802d915660ac340e52079a671b23ffaa93a186a880cc4fe1b7`，
已查看实际图像，中英文页面渲染正常。原探针中的中文乱码已改为正常文本；默认英文OCR测量
和额外中英混合OCR测量分别保留，不拼成同一运行结果。默认探针仍只以ASCII标记作通过条件。
浏览器产品入口实际为现有Chromium命令行，不是新建Playwright测试框架。
Chromium仍因短路径要求使用.project-local/c下的唯一临时profile；只处理本次创建的profile，
未读取用户浏览器数据。上述成功退出包含该profile不存在的后置检查；不是全机文件写入追踪。
本轮未扫描.hermes内部，不能用上述结果代签其所有历史文件无变化。

Ruff：r5-launch-probe-lint、r5-screenshot-probe-lint、r5-browser-cleanup-lint均exit 0。
回滚限core_launch、x01 probe、web_screenshot及对应测试diff；所有现有数据库/历史证据保持原位。
额度最近实查剩余78%；清理候选的精确路径批准仍未收到，未删除两个大型构建目录。

### M0复用来源登记与调度供体修复（X02，2026-09-13续）

[M0说明](R5-M0-REUSE.md)和[版本登记](R5-M0-REUSE.json)记录12组/18个源文件版本：
各自实际SHA256、HEAD blob、调用方、原行为/目标/差异、回归及退役条件。
READ/PARTIAL语义覆盖逐项写明，不把源码文件头或路由存在作为全审证明；1246历史项仍保留。

重要差分：当前Avalonia窗口仍为欢迎页，默认未传worker profile；Core只有收到该profile才启用executor。
旧DeepTutor bridge除了只读投影还通过legacy event_store追加事件；当前定位到的消费者是integration导出和测试，
不能按旧表的learning API调用假设归入新窗口链路，更不能接到vNext库形成第二写者。

|run|命令/结果|限制|
|---|---|---|
|r5-m0-pdf-ocr-reuse|dev.py --pytest test_worker_pdf_native/reading_order/structure、test_pdf_sidecar_job、test_ocr_sidecar_job，exit 0 / 28 passed|真实worker/stdio，未重建Core或验证默认Windows GUI|
|r5-fsrs-validation-red|dev.py --pytest tests/test_worker_schedule.py -q，exit 1 / 12 failed、8 passed|复现无效显式评分被correct覆盖、非对象空状态变新卡、NaN/Inf未拒绝|
|r5-fsrs-validation-green|同测试，exit 0 / 20 passed|增加输入拒绝；仍复用FSRS，未更换算法/DB接口；API无schedule_state的placeholder分支仍未消除|
|r5-fsrs-validation-lint|changed-file Ruff，exit 0|仅worker_schedule及测试|
|r5-m0-source-registry / r5-m0-registration-verify|dev.py执行登记/逐文件hash与来源键验证，均exit 0|12组、18源版本；215来源定位键唯一、全部保持候选；不作为运行时导入幂等证明|

V15的40方法/35研究/36学科/104资源均绑定冻结文件hash、命名空间和JSON pointer；
原V15包hash仅作为冻结R5声明保留，未声称本批重验原件。FSRS/MCP/PyMuPDF/Pillow版本与许可
来自已安装包元数据，不把项目MIT许可证套用于所有第三方。DeepTutor外部版本/许可仍为历史项目证据。
回滚限新M0登记/说明和调度worker/test差分；不删除/改写LEGACY_MANIFEST或原冻结来源。

### 规范化联合回归（2026-09-13）

`r5-normalization-integration-check` 经项目 `.venv/Scripts/python.exe scripts/runtime/dev.py`
执行 inventory、runtime-paths、path conventions、directory batch、core launch、MCP probe paths、
web screenshot、screenshot OCR probe、worker schedule 九个测试文件：exit 0，123 passed、9 subtests passed。
记录位于该 run 的 `artifacts/execution.json`；基于 `c06b234ca335b9cbb2c1fde270851e2390c36b89`
及当前未提交改动，不是新提交或 CI 证明。`git diff --check` exit 0。

复核现有 `.cargo/config.toml` 默认输出 `.project-local/build/cargo`，dev.py 另提供按 worktree
隔离的 `CARGO_TARGET_DIR`；Directory.Build.props 同样在项目内路由输出。本次未重复构建。
两个已列出的旧构建目录仍存在，逐路径删除授权未收到；实际删除量和实际释放空间均为 0。
`.zcode` 仍保留，未读取内容。账户通用额度实查剩余 74%，尚未触发 60% 交接上传检查点。
此联合验证不改变各父任务 PARTIAL 状态。回滚沿用上述逐项文件差分；历史证据不改写。

### X01运行器取消收尾（2026-09-13）

dev.py 原先输出循环中断只写失败收据，不清理自己启动的进程。现异常退出时终止自有活进程树、
等待退出并关闭管道；KeyboardInterrupt 返回130，收据明确 cancelled/owned_process_cleanup。
清理拒绝或超时记失败，不能伪称取消收尾成功。Windows限定本次Popen的PID树，不按进程名清理；
POSIX启动独立session后清理该进程组。未删构建文件，未触及共享服务。

- `r5-cancel-red`：exit 1，取消回归触发原KeyboardInterrupt逸出，4 passed后中断。
- `r5-cancel-final`：exit 0，16 passed、9 subtests passed；包含真实Windows父/孙进程停止，
  持有孙进程内核句柄验证退出，并验证同时启动的无关进程仍活着。测试仅清理自己创建的夹具进程。
- `r5-cancel-lint` / `r5-cancel-lint-final`：Ruff各exit 1（with与导入格式）；
  修正后 `r5-cancel-lint-pass` exit 0。最后 `git diff --check` exit 0。

基线仍为 c06b234ca335b9cbb2c1fde270851e2390c36b89 + dirty；POSIX分支未在本机运行。
这覆盖运行器捕获异常/取消，不涵盖强制杀死运行器、已脱离父进程树的进程或父进程已退出的孤儿；
不作为实际长时间构建/打包取消全验收。回滚仅dev.py取消处理及新增3项测试；不回退此前路径隔离。

### X14卷空间观测（2026-09-13）

现有inventory_project只输出分类汇总，不生成逐文件JSONL，无需再写一套简版。
本次补入根路径验证通过后的扫描前后卷空间观测；包含total/used/free字节、时间、净空闲差，
测量失败显式unavailable，不抹去已测逻辑数据。attributed_reclaimed_bytes始终null，
因为并发写入/回收站/卷上其他项目使该观测不能自行归因于本项目删除。

- `r5-volume-red`：exit 1，2 failed/16 passed，复现缺少卷观测。
- `r5-volume-green`：exit 0，18 passed；含负增长、失败未知和非法根不得查询卷。
- `r5-volume-lint`：Ruff exit 0。
- `r5-volume-live`：exit 0，可见逻辑35,387,949,026 bytes/219,941 files、0错误，
  27 reparse跳过、407排除。报告134,402 bytes；范围不包含私有排除内容，非全仓总量。
  扫描前后卷空闲均238,833,803,264 bytes，净差0；未实施删除，不宣称释放空间。

证据在各run的artifacts/execution.json，live另存inventory.json；基线SHA仍为c06b234加未提交改动。
不同轮次排除项数量变化，不能直接拼成同口径容量趋势。回滚限inventory_project的卷观测及3项测试。

### X13/X14候选打包保全与白名单（2026-09-13）

build_candidate.py 原先先rmtree已有输出并复制二进制，再拒绝dirty；ZIP写模式覆盖同名归档。
现先检查dirty，使用dev.layout/safe_path限制输出在项目.project-local/dist或runs，已有目录/ZIP/
校验sidecar拒绝且保留；新目录独占创建，ZIP与sidecar独占写入。ZIP按manifest.files加CANDIDATE.json
白名单打包，不递归收录验证后出现的缓存。没有新增覆盖开关或自动删除。

- `r5-bundle-preserve-red` exit 1：3 failed/16 passed，重现旧输出覆删、dirty残留、ZIP覆盖。
- `r5-bundle-preserve-final` exit 0：21 passed，另含越界拒绝、验证后出现未登记缓存不进入ZIP。
- `r5-bundle-preserve-lint` exit 0；检查限builder及candidate测试文件。

全部是项目run内小型fake binary夹具；未构建/发布/签名/覆盖Green，未把候选Core认作完整桌面发行版。
回滚限builder输出保全/白名单及5项新增测试；旧候选目录和归档未删除。基线为c06b234加dirty。
后续仍需候选manifest路径输入边界、实际完整桌面打包与安装/卸载验收；父任务保持PARTIAL。

### 候选manifest路径拒绝（2026-09-13）

候选校验现拒绝绝对/父目录/驱动器/ADS/非规范路径、大小写重复条目及非对象条目；不再豁免任意
未登记.sha256文件。扫描逐层剪枝链接和隐藏目录，CLI在读取CANDIDATE.json之前检查根与清单路径。
真实Windows junction夹具验证不枚举链接目标、不hash包外数据；并非操作系统沙箱或对恶意并发替换的保证。

`r5-manifest-path-red` exit 1（8 failed/21 passed）；最终`r5-manifest-junction` exit 0（31 passed）。
`r5-manifest-boundary-lint` exit 1仅导入顺序；修正后`r5-manifest-lint-pass` exit 0。
初轮RED中旧实现曾对合成E:/forbidden路径调用存在性查询，违反禁访边界；未读取内容或写入，
后续不再访问该路径，增加mock拦截，保护根测试要求任何元数据/内容调用前拒绝。

证据仍为c06b234+dirty、对应run/artifacts/execution.json；未运行真实候选二进制或发布。
回滚限candidate/verify_candidate路径验证及新增负例，不回退上段输出保全；完整安装验收仍未闭合。

### 候选运行验证止增与有界等待（2026-09-13）

verify_candidate.run_binary默认数据库改用dev.artifact_directory；启动无可见终端，随机生成临时claim。
原阻塞readline使20秒期限失效，现用独立读取线程+有界队列等待；失败/超时清理自有进程树，
读线程未结束具名失败。成功要求合法端口和本次数据库存在；这仍不是API/完整GUI功能验收。

- `r5-candidate-timeout-red` exit 1（31 passed/1 failed），原入口无有界测试参数；未启动静默夹具。
- `r5-candidate-run-final` exit 0（35 passed），真实子进程覆盖静默超时、提前退出、仅端口、正常就绪；
  验证项目run隔离、进程退出、Windows无窗口标记。`r5-candidate-run-lint` exit 0。
- `r5-candidate-core-live` exit 0，复用现有Core，创建本次隔离数据库、就绪端口59404、进程已停止。
  二进制SHA256 f85d72c68370c5095c3ed7054f58187d9828cbead48f808807d5fb58eacd3071；
  仅直接runtime探测，不等于重建、候选包验签或当前源码归因。收据在run/artifacts/core-run.json。

未构建/打包新版本、未删除旧构建目录，基线仍为c06b234+dirty。回滚限verify_candidate运行器及4场景测试。

### X04-01启动身份子契约定稿（2026-09-13）

新增[R5-DESKTOP-IDENTITY-V2.md](R5-DESKTOP-IDENTITY-V2.md)及
`packages/contracts/bootstrap/v2/launch.schema.json`，明确stdin双令牌、同Core/DB、固定角色、显式新主版本、
旧Core拒绝而不降权重试、重启失效、C#握手与adapter连接对象边界。现有launch.rs仍只支持旧格式；
没有冒充新认证已实现，也不把该子契约替代整个X04/学习字段迁移。

`r5-identity-contract-check` exit 0：Draft202012Validator.check_schema、3个正例、12个负例；
结果在run/artifacts/contract-check.json，不能证明令牌互异/重复JSON键/文件系统/真实权限隔离。
未新增Rust/C#生产逻辑，现有工具链已定位到共享10-toolchains/rustup/toolchains/stable-x86_64-pc-windows-msvc；
Cargo不在PATH，项目.project-local/cache/cargo不存在。尚未尝试构建，不能报编译失败或缺依赖已证实。
后续先准备不写共享库的构建缓存/环境，再做Core+C#及独立权限检查。回滚限本契约与Schema，不改数据库。

### X04 Core/C#双角色真实实现（2026-09-13）

上述构建前置现已解决：dev.py增加项目内CARGO_HOME；`r5-cargo-home-red` exit1，
`r5-cargo-home-green` exit0（17 passed/9 subtests）。共享registry仅只读，精确依据Cargo.lock
复制85个已核checksum的crate及公开索引，175文件/23,110,346 bytes，写入项目cache/cargo。
6个缓存缺失包未下载；实际Windows离线测试未需要它们。不是全平台依赖齐备证明。
使用现有Cargo/rustc1.97.1、MSVC14.44.35207、已安装SDK10.0.26100.0和.NET10.0.400；
Cargo `--frozen --offline`，.NET `--no-restore`，未安装、联网或修改共享工具链。

Core实现显式v2（无protocol保持旧格式）：双令牌不同、固定角色、未知/null/缺失/重复字段拒绝；
中间件按认证令牌覆盖actor，仍拒绝Origin/重复头。C#默认发送v2，在两份身份均匹配协议、角色、会话、
工作空间后发布就绪；SendMachineAsync只使用机器身份，Stop清空两份凭据。旧Core拒绝且不降级重试。

|run|命令及实际结果|
|---|---|
|r5-rust-launch-baseline|cargo test --frozen --offline -p archeaxis-api --test launch_auth，exit0，6 passed|
|r5-identity-v2-red|同命令，exit1，7 passed/1 failed，旧Core拒绝v2|
|r5-identity-v2-green|exit1，仅测试比较Windows长路径前缀未归一；改用已建DB canonicalize，未放宽身份检查|
|r5-identity-reviewed-regression|cargo test --frozen --offline -p archeaxis-api --test launch_auth --test workspace_ownership --test knowledge_actor_guard，exit0，8+3+3 passed，无ignored|
|r5-desktop-v2-red|dotnet build tests/runtime-paths/CoreSupervisor.Tests/CoreSupervisor.Tests.csproj --no-restore --nologo，exit1，缺少SendMachineAsync的3处编译错误|
|r5-desktop-v2-identity-negatives|dotnet run --project同csproj --no-restore --nologo，exit0；六种身份负例按正确失败原因拒绝|
|r5-desktop-response-header-red|同run命令，子进程exit3762504530（shell表现为1）；真实发现HttpResponse.RequestMessage残留机器认证头|
|r5-desktop-reviewed-regression|修复响应认证头清除后同run命令exit0；含C#→认证Core→实际Python→持久输出、双角色、停止/重启/并发独立库/Windows短路径|

使用 requesting-code-review 的一次只读reviewer，分别审查Rust和随后C#范围；未独立运行测试，不是Q00/Q01。
审查未发现已确认提权问题，指出缺少真实机器自审/人类事件拒绝/旧双令牌失效用例及响应诊断头残留；
均已补齐上述回归。同一Core进程中机器候选成功、accepted/自审/人类事件拒绝，同DB重启后旧双令牌401。

新Core二进制SHA256：8a835d107e505c0ba4deee1d769af82a49b4e27bb9a3de0a939aadeb0b1f1b33。
此前f85d72...收据仍归属于旧二进制，不能混用。基线c06b234 + dirty，5个实现/测试/Schema源hash和二进制hash
保存于`r5-rust-runtime-binding/artifacts/source-binding.json`；同目录`rust-runner.py`保存精确离线构建环境。
重复命令须通过dev.py分配新run，再执行该runner及上述cargo参数；C#运行设置ARCHAXIS_CORE_BIN为
`.project-local/build/cargo/debug/archeaxis-api.exe`。Cargo复用该现有build目录，.NET输出到worktree build目录。
两个旧清理候选仍未删除；其中worktree build现包含本次C#测试输出，获批删除前必须重新量大小/检查占用。

M0保留旧Supervisor源hash/原收据到source_version_history后更新当前源hash，仍不宣称默认Avalonia学习窗口完成。
`r5-identity-convention` exit0（1793 tracked归属通过，不覆盖未跟踪新文件的完整交付），git diff --check exit0。
Rust已有stable_id/worker两项未使用警告仍在，未借机改无关代码。账户实查剩余70%，未触发60%上传。
回滚须成对撤回Core/C# v2改动并停用机器方法，不迁移/清理数据库；包、安装器、默认窗口与DeepTutor接线仍未完成。

### X03桌面worker配置与隔离开发入口（2026-09-13）

新增WorkerProfile.cs，MainWindow使用应用旁worker-profile.json或显式ARCHAXIS_WORKER_PROFILE。
严格四字段schema/python/script/staging，路径相对配置文件；未知/重复/缺失/超长/私有/E/UNC/链接拒绝。
缺少可选默认配置显示文本组件未配置；显式配置错误不启动Core。配置读取不创建staging，Core仍独立验证。
新增scripts/launch/desktop_launch.py，经dev.py生成项目run内配置与全新开发DB路径，默认prepare-only。
详见[R5-DESKTOP-START.md](R5-DESKTOP-START.md)；不修改legacy数据库默认值、全局环境或共享工具。

|run|实际结果|
|---|---|
|r5-worker-profile-red|dotnet build测试工程--no-restore，exit1，缺WorkerProfile.cs|
|r5-worker-profile-reviewed|dotnet run测试工程--no-restore，exit0；配置相对路径、未知/重复字段、缺失、合成私有路径、真实Windows junction拒绝，随后实际Core/Python持久输出通过|
|r5-desktop-launch-red / r5-desktop-launch-green|pytest test_desktop_launch.py，exit1缺文件→exit0/2 passed|
|r5-desktop-default-core-red / r5-desktop-default-core-green|审查回归：默认Core未跟随worktree build，exit1/1 failed→修复exit0/3 passed|
|r5-worker-private-path-red|审查回归：对项目run内不存在的合成.ssh路径未先词法拒绝，子进程非零；未读真实私有路径|
|r5-desktop-profile-build-final|正式Avalonia工程build --no-restore --nologo，exit0，0 warning/0 error|
|r5-desktop-prepare-reviewed|真实现有产物prepare，显式--core .project-local/build/cargo/debug/archeaxis-api.exe，exit0，PREPARED_NOT_LAUNCHED|

只读reviewer发现私有名单不全和默认Core路径漂移，两项均已补RED/修复。默认Core现跟随dev.layout的
worktree build；本轮既有Core在较早使用的build/cargo，所以明确传--core复用，不再构建另一份。
changed-file Ruff初次仅导入顺序失败，r5-desktop-launch-lint-pass已通过。
M0新增WorkerProfile为第19源版本并保留旧hash；当前窗口主体仍是占位，没有可见GUI交互验收。
回滚限WorkerProfile、MainWindow配置接线、desktop_launch及对应测试/配置索引；不得把开发隔离DB当真实资料库。

### X14 DSH 授权清理：四条候选、八条路径（2026-09-13，DSH/DeepSeek）

依据 `docs/current/HANDOFF-DSH-DEEPSEEK-CLEANUP-2026-09-13.md`，owner 就"批准四条候选（约 5.36 GiB，
零重建代价）"给出精确路径授权后逐条执行。前置复核：分支 `codex/full-loop-0906` @ `c643ecd`（与
origin 0/0）、`main` @ `1e9813e`；唯一未跟踪项 `docs/current/SESSION-RESTART-2026-09-12.md`（保留）；
无 cargo/rustc/archeaxis-api/dotnet/msbuild 进程；前一轮已授权删除的根 `target` 与
`.project-local/build/be268a2d33/cargo` 复核为不存在。

| # | 路径 | 归属证据 | 删除前 | 删除后 | 结果 |
|---|---|---|---|---|---|
| 1 | `%TEMP%\archeaxis-clone-99b` | 我方克隆：`.git` origin=`D:/All projects/ArcheAxis-Knowledge-OS/.`，HEAD `8f63d9f` | 4,425.9 MiB / 18,127 files | 不存在 | **PASS** |
| 2–6 | `.project-local/runs/fresh-checkout{,-98,-98b,-98c,-99}`（各含 `archeaxis` 克隆） | 同来源；HEAD `dc03f66`/`fc2372b`/`ab8570f`/`ab8570f`/`8f63d9f` | 552.4 MB / 12,481 files | 不存在 | **PASS** |
| 7 | `.project-local/inventory` | 旧全量清单体（2026-09-07），已被 R5 自身 inventory run 取代 | 433,604,988 B / 8 files | 不存在 | **PASS** |
| 8 | `.project-local/dist` | 早期候选包（2026-09-11），`build_candidate.py` 可重建 | 25,968,375 B / 12 files | 不存在 | **PASS** |

合计删除约 **5.27 GiB**（原估 5.36 GiB，实测略低），**零重建代价**。保留并在删后复核仍存在的：
`build/cargo/debug|release/archeaxis-api.exe`、`build/be268a2d33`（.NET 产物）、`runs` 收据、`.venv`、
`data`、`frontend`。

**三点方法教训（逐次修正，均留在脚本注释里）**：
1. 首版以子进程 `Remove-Item` 并**捕获输出**：PowerShell 的本地码页错误信息打死了管道读取线程，
   子进程被留在写满的管道上，删除**半途而废**（4,425.9 → 357.9 MiB）。改为**本进程内**
   `shutil.rmtree`，不再有管道死锁面。
2. `shutil.rmtree(onexc=...)` 的第三个参数是**异常实例**（旧 `onerror` 才给 exc_info 元组）；
   按元组读会在**树已被部分删除之后**抛 `TypeError`。改为直接读 `type(exc).__name__`。
3. pytest 的深路径夹具（`test_*_on_unc*`／`segment-xxxxxxxx…`）普通枚举报 `WinError 145 目录不是空的`；
   追加一次 **`\\?\` 长路径前缀**重试后清空（两个 PARTIAL 由此转为 PASS）。

**收据**：每条路径一次 `dev.py --run-id r5-dsh-cleanup-*` 调用，各自落在
`.project-local/runs/be268a2d33/<run-id>/artifacts/execution.json`；`dev.py` 拒绝复用已存在的 run-id
（首轮失败必须换新 id，这是正确行为，已如实记录多次尝试）。

**后置条件**：八条路径 `Test-Path` 全为 False，`.project-local/runs` 下无 `fresh-checkout*` 残留。
卷空闲观测 C: 211.36 GiB / D: 234.2 GiB——**观测值不等于归因**：卷上有其他项目与并发写入，
与本台账既有 `attributed_reclaimed_bytes=null` 口径一致。

**保留与未做**：`.project-local/cache`（今日 09:27 仍有写入，`dev.py` 把 NuGet HTTP/plugins 缓存路由于此）
与 `build/cargo/debug/{deps,incremental}`（今日 09:30 写入，属**当前**构建状态；删掉换来的是全量重编译，
比省下的磁盘更贵）**均未删除**；`.hermes`/`.zcode`/`.codex` 未读取、未触碰；未访问 `E:`；未改远端 URL
（实际为 SSH，与更新后 AGENTS.md 所称 HTTPS 存在漂移，留待 owner 决定）。

**回滚**：删除对象均为可再生克隆、旧清单体与早期候选包；重建方式为重新克隆或重跑构建，
不从外部复制二进制；不涉及产品源码、用户数据、共享工具链或历史收据。

### X14 DSH 第二批：runs 内临时树（2026-09-13）

owner 就"runs 内可再生的精确清单"选择**批准 2026-09-13 之前的候选**（保留今天的暂存）。清单来源：
`docs/current/R5-DSH-CLEANUP-CANDIDATES.md` 与
`.project-local/runs/be268a2d33/r5-dsh-runs-audit-2/candidates.json`。

**先分类、后删除（打开看过，不按目录名推断）**：`runs` 6.82 GiB 中，`artifacts/**` 收据仅约
**10.00 MiB / 1,315 files**（分布在 834 个 artifacts 目录），其余为临时树；最大的候选全部是
`<run>/tmp/pytest/**` 型 pytest 会话残留（2026-09-07 五条各 342.5 MB / 3,335 files；今日
`r5-checkpoint-python-primary` 238.1 MB / 3,454 files，夹具名一致）。

**执行口径与一处更正**：按"最后写入 < 2026-09-13"筛选得 **441 条路径 / 6.257 GiB**；上一条 DSH 回复里
写的"578 条"有误（那是把"今日 137 条"也加进去了），**字节口径 6.257 GiB 与批准一致**。按路径逐条执行：
每条先量、再删、再验后置条件；拒绝 `.project-local/runs` 之外的路径；**若发现某条内部含今日文件则跳过**。

| 项 | 实测 |
| --- | --- |
| 批准路径数 | 441 |
| 删除成功 | **441** |
| 删除字节 | **6,718,700,282 B（6.257 GiB）** |
| 跳过（今日有改动） | 0 |
| 部分失败 | **0** |
| 收据 | `…/r5-dsh-runs-cleanup-batch/artifacts/per_path.jsonl`（每路径一行）＋ `summary.json` |

**后置条件（删后复核）**：`runs` 由 6.82 GiB 降至 **0.56 GiB / 15,909 files**；今日写入保留
**0.522 GiB / 13,787 files**；`artifacts/**` 证据仍在 **10.00 MiB / 1,315 files / 834 目录**，抽查台账引用的
4 条（`binding.json`、`execution.json`、`candidates.json`、某 `artifacts` 目录）**全部存在**；卷空闲观测
D: **240.55 GiB**（观测值，非归因，与既有 `attributed_reclaimed_bytes=null` 口径一致）。

**为什么不是 441 次 dev.py 调用**：`dev.py` 拒绝复用 run-id，441 次独立调用纯属浪费额度；改为
**一次运行 + 每路径一条收据行**，"逐路径量／删／验"的实质未变。**未删**：今天的暂存、`artifacts/**` 收据、
以及清单里"无日期"档的空目录（约 1,302 条 / 0 字节，仍在）；如需一并清掉请单独授权。回滚：全部为
pytest/工具会话残留，重跑对应工具即重建；不涉及产品源码、用户数据、共享工具链或历史收据。

### X13/X14：跨软件构建与发布输出统一（2026-09-13）

提交 `4844010a7631bb8cde8ed275007afcda98b656b6` 将前端 Vite、Tauri shell、桌面 Green/Portable
分发、CI wheel smoke 与 Release 工作流的生成输出统一路由到项目忽略目录
`.project-local/build` 或 `.project-local/task-runtime`。桌面分发脚本不再先在仓库根目录创建临时
Green/Portable 目录或 ZIP；测试夹具同时验证根目录无泄漏。根部明确的被忽略生成目录
`build/`、`__pycache__/`、`.pytest_cache/`、`.ruff_cache/`、`archeaxis_workspace.egg-info/`
已逐路径删除并以 `Test-Path` 后置条件确认不存在；`data/`、历史资产及私有状态未触碰。

验证：`.venv\\Scripts\\python.exe -m pytest -q tests/test_ci_a0_gates.py tests/test_desktop_staging.py tests/test_release_manifest.py`
exit 0，`65 passed`；`scripts/check_path_conventions.py` exit 0，`1993/1993 tracked paths owned`；
`git diff --check` exit 0。上传后 `git fetch origin codex/full-loop-0906` 复核本地 HEAD 与远端同为上述 SHA。
该项覆盖已登记的项目内构建/发布入口；历史文档中的 legacy `dist/target` 文本、真实 `data/`
及受保护 `.hermes/.zcode/.codex` 未作为可删除对象，跨入口启动/取消和完整安装态仍由各自切片验收。

随后新增 `tests/test_project_output_routing_contract.py` 作为持续回归守卫，检查 Vite/Tauri 共用
前端输出根、CI/Release 仅使用项目内 staging 根，以及桌面分发器不在仓库根创建临时目录或 ZIP。
受影响契约与桌面门禁共 `37 passed`，Ruff 与 `git diff --check` 均 exit 0；提交
`e515ea32` 已上传到同一工作分支。该守卫覆盖当前已登记入口，不替代真实跨平台运行、安装和取消场景。
### X14：根部路径外溢空树清理（2026-09-13）

对项目根目录非标准 `c/`、`d/` 做元数据盘点：两者均未被 Git 跟踪，文件数为 0；`d/` 仅含
历史测试生成的模拟路径目录树，未发现可恢复文件或项目源码。按逐路径清单删除 `c/`、`d/`，
PowerShell `Remove-Item -LiteralPath` exit 0，随后 `Test-Path` 对两条路径均为 false。未读取或
处理真实项目外部路径、`.hermes/.zcode/.codex`、`data/` 或历史资产。该证据仅证明本次两条
空树残留已清除，不代表卷级未知占用已归因。

后续审计发现 CI wheel smoke 的构建输出已迁移，但校验脚本仍读取根 `dist/`；已改为读取
`.project-local/task-runtime/wheel-smoke/dist`，并在输出路由契约中加入根 `Path("dist")` 回退断言。
定向 CI 契约测试 `26 passed`，Ruff 与 `git diff --check` 通过；提交 `8064449d` 已上传。

同时补充 `.gitignore` 的通用 `release-assets/` 规则，覆盖误用旧发布入口时的根部或子目录 staging
残留；输出路由契约新增对应断言。该变更与 CI 路径修复联合测试 `26 passed`，提交 `dd163ee0` 已上传。

审计 `scripts/release_checksum.py` 时发现仅示例仍指向根 `dist/`，已改为 `.project-local/build/release-assets/`
输入，并加入输出路由契约测试。该测试 `4 passed`，Ruff 与 `git diff --check` 通过。

权限与环境实测发现 Windows doctor 在 PATH 没有 `python` 时会忽略仓库自有 `.venv`，将可用项目误报为
不健康。现增加仅针对 `<project>/.venv/Scripts/python.exe` 的安全回退，保持不修改 PATH、HOME 或全局
配置；自定义项目根仍不会被写入。`tests/test_doctor_windows.py` `7 passed`，Ruff 与 `git diff --check`
通过。该改动只改善项目自检，不代表缺失 Rust 工具链或完整安装态已解决。

### CLEAN01/CLEAN07：公开忽略目录 ACL 阻塞（2026-09-13）

对项目根下 37 个公开目录执行只读 ACL/可达性检查，36 个可读取且未发现显式 Deny；根部
忽略目录 `.pytest_cache/` 为空，但 `Get-Acl -LiteralPath .pytest_cache`、`icacls .pytest_cache`
及 `fsutil reparsepoint query .pytest_cache` 均返回 `Access is denied`。该目录不是受保护的
`.hermes/.zcode/.codex`，但其 ACL/重解析状态无法在当前权限下确认，因此未删除、未改 ACL、
未提权绕过。该项标为权限阻塞；需管理员在确认目录归属后按组织策略修复或删除，才能把公开
项目目录的访问门禁闭合。

后续复核确认 `.pytest_cache` ACL 已由管理员修复：只读 ACL、写入探针和递归删除均可执行。该目录
已按可重建旧缓存精确删除，`Test-Path` 后置条件为 false；doctor 实测 `healthy=true`、
`access_blockers=[]`，项目根与运行根均可写。`tests/test_doctor_windows.py` 与输出路由测试
共 `14 passed`，测试后根 `.pytest_cache` 仍不存在，缓存只出现在 `.project-local/task-runtime/pytest-cache`。
此前 CLEAN01/CLEAN07 权限阻塞解除；未触碰私有状态、真实数据或历史资产。

Windows doctor 随后增强为检查公开顶层目录 ACL，并对枚举可能隐藏的已知 `.pytest_cache` 残留做显式
探针。项目绝对路径实测输出 `access_blockers=[".pytest_cache"]`、`healthy=false`，准确暴露当前
权限阻塞；`tests/test_doctor_windows.py` `7 passed`，Ruff 与 `git diff --check` 通过。未提权、未改 ACL。

为避免该根部 ACL 残留继续被生产，`pyproject.toml` 的 pytest 配置已将 `cache_dir` 固定为
`.project-local/task-runtime/pytest-cache`。定向输出路由测试 `4 passed`，Ruff 与
`git diff --check` 通过；实测新缓存目录存在，根 `.pytest_cache` 仅保留原有条目且未作为新
写入目标。该修复止住新增外溢，但旧目录的 ACL 修复/删除仍需管理员处理。

主启动入口 `run_all.sh`、`run_all.bat` 原先直接调用 `app.runtime_entrypoint`，绕过统一环境路由；
现改为两步均经 `scripts/runtime/dev.py` 启动，使 TMP/TEMP、依赖缓存、Cargo/NuGet 与运行收据
遵守同一项目边界。输出路由与 doctor 回归 `12 passed`，Ruff、`git diff --check` 通过；显式
入口检查确认迁移与 Core 两阶段命令均保留。该改动不改变 `run_windows.ps1` 的引导安装行为，
完整跨平台安装仍需单独验收。

Windows 引导安装实测发现项目 `.venv` 为 uv 管理环境且无 `pip` 模块；两个入口原先的 `python -m pip`
会错误失败。现改为 `uv pip install --python <project .venv> -r requirements.txt`，显式绑定项目解释器，
不回退系统 Python 或用户级缓存。真实 `uv pip install --dry-run` 检查 26 个包、`Would make no changes`；
输出路由契约测试 `7 passed`，Ruff 与 `git diff --check` 通过。未执行实际安装或启动 Core。

桌面分发器的默认 staging 路径也已从 cwd 相对路径改为以 `desktop/scripts/assemble_distributions.py`
所在仓库根为锚点，避免从其它工作目录调用时生成 `desktop/.project-local` 等错误树；显式 `--out`
仍由调用方控制。桌面 staging 与输出路由回归 `18 passed`，Ruff、`git diff --check` 通过。

补齐 `run_windows.bat`：与 PowerShell 入口一致，显式设置项目内 TEMP/TMP/TMPDIR、pip/uv cache，
使用项目 `.venv` 解释器，并经 `scripts\
untime\\dev.py` 启动 Core。输出路由契约测试 `7 passed`，
Ruff 与 `git diff --check` 通过；未实际安装依赖或启动服务。

`run_windows.ps1` 也已收口：保留首次 `.venv` 引导和 requirements 安装，但将 TEMP/TMP/TMPDIR、
pip/uv cache 固定到 `.project-local`，Core 启动改经 `scripts\
untime\\dev.py`。输出路由契约
测试 `6 passed`，Ruff 与 `git diff --check` 通过；本轮未实际安装依赖或拉起 Core，避免把网络/安装
副作用伪装成验证结果。
安装前复核项目 `.venv`（Python `3.13.14`）时，`uv pip check --python .venv\\Scripts\\python.exe`
报告 `rapidocr-onnxruntime` 的约束为 `Python >=3.6, <3.13`；uv 命令退出码虽为 0，但该不兼容
按环境失败处理。未强行降级 Python、替换依赖或覆盖现有环境；Windows 引导入口的真实安装仍需
在满足依赖约束的 CPython 版本上单独验收。此项标为 REPO03 环境阻塞，不影响已完成的输出路径止增。

为使可选 `ci-adapters` 在 Python 3.13 环境下可解析，`pyproject.toml` 已将
`rapidocr-onnxruntime>=1.4` 限定为 `python_version < '3.13'`，并以联网 `uv lock` 重算
`uv.lock`；锁文件同时补齐项目已有 `mcp` extra 的解析记录。定向输出路由与 Windows doctor
测试 `14 passed`，`git diff --check` 通过。现有 `.venv` 中已安装的不兼容 RapidOCR 未被移除，
需在后续环境重建或依赖安装任务中按新锁文件处理。

当前提交 `3d0fbcd190680c3dd5299015bd98dd11e292929b` 上用项目指定 PowerShell 7.6.3 重跑
`scripts/doctor_windows.ps1`：Python 来自项目 `.venv`（3.13.14），项目根与运行缓存可写，
`access_blockers=[]`、`healthy=true`；Rust 工具链当前不可用，故不能据此宣称桌面构建或运行验收完成。

补齐 Windows 两个默认启动器的工具链解析：优先使用 PATH 中的 `uv`，否则只回退到已批准的本机
Hermes 工具链路径；缺失时明确失败，不再调用 PATH 中不确定的 `python -m venv`。环境创建统一走
`uv venv`，依赖安装继续绑定项目 `.venv`，缓存和临时目录仍固定在 `.project-local`。输出路由与
doctor 回归 `14 passed`，`git diff --check` 通过；未启动 Core，Rust 工具链仍缺失。

按精确路径清理项目根已确认可再生的 `.ruff_cache` 与 `__pycache__`，删除命令退出 0，两个路径
的 `Test-Path` 后置条件均为 False。未触碰 `.project-local/build/cargo`、`.project-local/cache`、
运行收据、产品数据或受保护私有目录。

复核 `.project-local/cache` 后，确认 `nuget` 包缓存最后写入时间为 2026-09-06，大小
`1,232,333,595` bytes，清理时无 `dotnet` 进程；按精确路径删除并验证 `Test-Path=False`。
NuGet restore 可重建该缓存。仍保留 2026-09-13 有写入的 `uv`、`cargo` 与 `nuget-http` 缓存，
避免删除当前活跃依赖状态。

Windows doctor 现支持读取调用方显式声明的 `ARCHEAXIS_RUST_TOOLCHAINS`，从其 `cargo\bin`
定位 Rust 工具链，不修改全局 PATH、不打印绝对路径。使用项目共用工具链实测 cargo metadata
exit 0；doctor 输出 `rust.source=external_toolchain`、`healthy=true`，新增回归后共 `15 passed`。

Rust workspace 经 `dev.py` 首次运行时发现 OCR 测试继承了失效的 Tesseract shim 路径；worker
现支持显式 `TESSERACT_CMD`，调用方可绑定实际可执行文件而不依赖 PATH shim。使用共用
`tesseract\current\tesseract.exe` 与 `tesseract-languages\current` 实测
`cargo test -p archeaxis-application --test ocr_job_end_to_end --offline`：`1 passed`，输出仍位于
`.project-local/build/cargo` 和对应 run 目录。旧 shim/外置路径未改写。

随后以同样的项目 `dev.py` 入口、外置 Rust/MSVC、显式 Tesseract 和 `.project-local/build/cargo`
重跑 `cargo test --workspace --offline`（run `rust-full-20260913c`）：编译完成，所有 workspace
单元测试、集成测试、文档测试均通过，未见失败；保留既有 dead-code/unused 警告，不将警告升级为失败。

最终 Python 路由复核在显式共用 Tesseract 配置下运行 `tests/test_worker_ocr_route.py`、
`tests/workers/test_bulk_ocr.py` 及规范化/doctor 套件：`24 passed`；路径归属检查为
`1994/1994`，PowerShell 7 doctor 报告 `access_blockers=[]`、`healthy=true`。本轮未读取或触碰
`.hermes`、`.zcode`、`.codex`，未改变未跟踪历史归档。

修正 `run_windows.ps1` 的 `uv` 回退解析：PATH 命令对象使用 `Source`，显式回退文件使用
`FullName`，避免 FileInfo 没有 `Source` 时传入空路径。启动器契约、doctor 测试与 PowerShell
语法解析共 `17 passed`，`git diff --check` 通过。

复核当前脚本、CI、桌面与测试入口未引用 `.project-local/build/cargo/release`，其最后写入为
2026-09-11，大小 `321,212,494` bytes，清理时无 cargo/rustc 进程；按精确路径删除并验证
`Test-Path=False`。release 构建可由 `cargo build --release` 重建，当前 debug 构建和运行证据保留。

继续复核发现 `.project-local/build/be268a2d33/dotnet`（`592,700,364` bytes，最后写入
2026-09-13 04:18）没有当前脚本/CI入口引用，清理时无 dotnet 进程；按精确路径删除并验证
`Test-Path=False`。该目录可由外置 .NET 工具链重新构建；当前 Cargo debug、运行收据和产品数据保留。

本轮 X00 入口收口：历史 R3.1 审计器不再隐式选择任务包；`check_evidence_index.py`、
`check_evidence_commands.py`、`check_worker_reachability.py`、`check_format_matrix.py`、
`check_taskpack_integrity.py` 均要求显式历史路径，未提供时以 exit 2 提示使用 R5 专用
`docs/authority/taskpack-0912-r5/verify_package.py`。新增 `tests/test_taskpack_paths.py`，
并运行相关测试共 `64 passed`（新增测试 4 项、既有相关测试 60 项）；命令使用项目内
`.project-local/runs/taskpack-paths-test-venv/Scripts/python.exe`，仅写入项目 `.project-local`。
pytest 的缓存目录因现有 ACL 返回 `WinError 5` 警告，但不影响测试结果；未读取或修改
`.hermes`、`.zcode`、`.codex`，未处理既有未跟踪历史归档。

随后使用同一项目内解释器运行 R5 `verify_package.py`：exit `0`，报告 `result: PASS`、
`tasks: 23`、`active_files: 173`；该校验明确报告 `product_tests_run: false`、
`windows_cleanup_performed: false`、`current_head_checked: false`，因此仅作为包完整性
证据。`check_path_conventions.py --json` exit `0`：`1994/1994` tracked paths owned、
`0` unowned、`0` ambiguous、`0` denied-but-tracked；记录测量提交为
`b81c789d8d6363f53ddfadf5e9da9e7735bb9338`，与当前 HEAD 的差异按工具原样保留。

X01 定向回归使用项目内 Python 3.13.15 环境：运行路径/doctor/启动器/约定相关测试共
`49 passed, 1 failed`；唯一失败为 Windows 进程树测试中 `taskkill.exe /T /F` 返回失败，
随后排除该 OS 进程树用例重跑为 `18 passed, 1 deselected`。该失败归因于当前受限解释器/进程
权限环境（`ENVIRONMENT_FAIL`），不是将其标成产品通过；入口代码未因该结果修改。项目内
解释器和 pytest 环境均位于 `.project-local`。

X01 继续核对发现 `.github/workflows/ci.yml` 与 `release.yml` 的工作树换行不符合
`.gitattributes`（CRLF）。仅将这两个 YAML 归一化为 LF；`check_repository_conventions.py
--format json` exit `0`（`issue_count: 0`），随后 `tests/test_path_conventions.py`、
`tests/test_nightly_runtime_gates.py`、`tests/test_runtime_delivery_authority.py` 共
`25 passed`。pytest 缓存仍有既存 `WinError 5` 警告。

发布门复核发现 `app/release-manifest.json` 的 `dependency_lock.digest` 与当前 `uv.lock`
不一致；已更新为当前 SHA-256 `1db913253b5d018fa4af9314939dfda5635e195f77de6bbc48fe7f3cca575859`。
补齐项目内测试环境的 `fastapi`、`python-multipart`、`numpy` 后，发布清单、身份契约、SBOM
覆盖和证据收据测试共 `44 passed`；Starlette 弃用提示与 pytest 缓存 ACL 警告保留记录，未将
警告当作失败或通过依据。

X02/X03 路径审计发现 `scripts/launch/deeptutor_web.py` 曾硬编码外置共享库绝对路径，
触发架构守卫。已改为仅接受显式参数或 `ARCHEAXIS_DEEPTUTOR_ROOT`、
`ARCHEAXIS_NODE_PATH` 环境变量，不再内嵌机器路径；`tests/test_architecture_guard.py`
与 `tests/test_deeptutor_web_launch.py` 共 `26 passed`。

本轮证据引用的提交均为已存在且可回溯的测试源：
`tested-source-sha:3d0fbcd190680c3dd5299015bd98dd11e292929b`、
`tested-source-sha:4844010a7631bb8cde8ed275007afcda98b656b6`、
`tested-source-sha:3dee1278c170573c0d45e307635cafd8e1a68425`；这些标签用于让现实性审计
区分历史收据来源，不表示发布或独立审计通过。

X02/X05 依赖环境补齐项目内 `sqlite-vec==0.1.9` 后，向量迁移、架构守卫与 AXR-060
现实性审计共 `62 passed`；此前 10 个 `ModuleNotFoundError: sqlite_vec` 均为测试环境
缺包，现已消除。现有 pytest 缓存 ACL 警告仍保留，不影响测试退出码。

- 2026-09-13 inventory CLI encoding fix: `tests/maintenance/test_inventory_project.py::InventoryProjectTests::test_cli_outputs_json_and_reports_missing_root_with_nonzero_exit` passed (1 passed). Full suite under explicit `--basetemp .project-local/runs/fulltest-final-20260913` reached 2762 passed, 7 skipped, 9 failed; five `bulk_fixture_factory` failures are invocation-root mismatches caused by overriding the pytest basetemp outside the helper's validated run root (the same 7 tests pass under the project-managed default run root), while four Windows process-tree cleanup cases fail because this managed environment returns `taskkill.exe` access denied. These are not promoted to product PASS; rerun in a normal Windows process-control environment is required.

- 2026-09-13 current path measurement: `scripts/check_path_conventions.py --json --measure` reports 1,994 tracked paths, 1,994 owned, 0 unowned, 0 ambiguous, 0 denied, 100% coverage. The historical `R5-PATH-DISPOSITION.json` remains a dated record and reports drift by design; it was not rewritten.

- 2026-09-13 runtime footprint audit: `.project-local/build` 9.54 GiB (current cargo build), `runs` 1.84 GiB (evidence/test runs), `cache` 1.19 GiB (managed dependencies), root `.venv` 0.88 GiB (legacy scripts still reference it), and `.hermes` 0.46 GiB (retained historical material). All are ignored/reproducible or protected runtime classes; no deletion was performed.

- 2026-09-13 CI route correction: after historical checker CLIs were made explicit-path-only, `.github/workflows/ci.yml` now passes `--matrix docs/authority/taskpack-0910-r3/R15-FORMAT-STATUS.json` to the format gate. `tests/test_ci_a0_gates.py tests/test_format_matrix.py` passed (35 passed); no R5 artifact was substituted for the historical matrix.

- 2026-09-13 explicit historical gates rerun: `check_format_matrix.py --matrix docs/authority/taskpack-0910-r3/R15-FORMAT-STATUS.json` PASS (16 rows, 0/14/2); `check_worker_reachability.py --record .../WORKER-REACHABILITY.json` PASS (12 workers, 10 routed, 2 exempted); `check_evidence_index.py --index .../R14-EVIDENCE-INDEX.json --state .../STATE.json` PASS (17 slices, 81 tracked pointers, 3 receipts); `check_taskpack_integrity.py --pack .../taskpack-0910-r3 --shipped .../taskpack-0910-shipped` PASS (21 frozen files intact, plan graph valid, 93 ledger rows).

- 2026-09-13 output-routing regression set: `tests/test_project_output_routing_contract.py tests/test_runtime_delivery_authority.py tests/runtime-paths` yielded 30 passed and 1 environment failure. The single failure is the known managed-Windows `taskkill.exe` access-denied process-tree case; routing and delivery contract tests passed.

- 2026-09-13 architecture/language gates rerun at current worktree: `scripts/check_architecture.py` and `scripts/check_language_boundaries.py` both exit 0 (Rust database owner, Python workers/C# shell boundary, protocol major 1).

- 2026-09-13 CLEAN02 inventory: `scripts/maintenance/inventory_project.py` produced `.project-local/runs/inventory-current-20260913.json` with status `partial`, 147,102 observed files and 15,371,011,574 logical bytes; 186 permission errors and 4 skipped reparse points were preserved as limitations. The volume measurement reported 291,391,827,968 bytes free before and after (no cleanup attribution). Private `.hermes/.zcode/.codex` and other sensitive names remained opaque.

- 2026-09-13 checker regression suite rerun: taskpack path resolver plus evidence index/commands, worker reachability, format matrix and taskpack integrity tests passed (64 passed; only existing pytest cache ACL warning).

- 2026-09-13 R13 Core preflight: `scripts/launch/core_launch.py --check` reports `dependencies_ok: true`; Core binary, project Python, text/PDF/OCR workers, PyMuPDF, Tesseract data, and Cargo wrapper resolve under the project or declared tool paths. DeepTutor ports 8001/3782 are not running; Ollama port 11434 was observed active. This is a preflight only, not GUI/install acceptance.

- 2026-09-13 Avalonia desktop build: `dotnet restore apps/ArcheAxis.Desktop/ArcheAxis.Desktop.csproj` succeeded with NU1900 vulnerability-feed warning (NuGet index unavailable); then `AVALONIA_TELEMETRY_OPTOUT=1 dotnet build ... --no-restore --nologo` succeeded with 1 warning, output routed to `.project-local/build/dotnet`. The opt-out prevented user-profile telemetry writes. This verifies compilation only, not installer/signing/GUI acceptance.

- 2026-09-13 desktop contract regression: `tests/test_desktop_staging.py tests/test_desktop_runtime.py tests/test_desktop_launch.py tests/test_axw_run204_supervisor.py` passed (32 passed; dependency deprecation warnings only).

- 2026-09-13 R13 candidate bundle: `scripts/release/build_candidate.py --out .project-local/runs/candidate-r5-20260913-c --binary .project-local/build/cargo/debug/archeaxis-api.exe --allow-debug --allow-dirty --zip` succeeded at source commit `3d560253c0d61dc0baa0728eb3fc0a74c5b67e26`; 2 files, 8,238,283 bytes, archive SHA-256 `f102149e5eef4291137d7e40a6000e0b67ae991aa0abd8682984396fdb979355`. `verify_candidate.py --candidate ... --json` returned `ok: true`, with `debug-build` and dirty-tree labels retained. This is a verified candidate, not a release or install artifact.

- 2026-09-13 managed-entry routing check: `scripts/runtime/dev.py --pytest tests/test_project_output_routing_contract.py` allocated run `be268a2d33/933eb6403438` under `.project-local/runs` and passed 9 tests; pytest cache was also inside that run root.

- 2026-09-13 managed desktop/Cargo follow-up: the Avalonia build remains successful with telemetry opt-out; direct `dev.py` invocation of the tracked `.bat` Cargo wrapper was not recorded as a product failure because Windows `cmd.exe /c` argument quoting in this shell rejected the batch path before Cargo ran. Existing managed-entry Python and prior Rust contract evidence remain authoritative.

- 2026-09-13 Windows batch launcher normalization: `dev.py` now wraps `.bat/.cmd` children with `cmd.exe /d /c` and converts slash separators, preserving project environment routing. Regression `tests/runtime-paths/test_dev_paths.py -k batch_entrypoint or normal_run` passed (2 passed). A real `dev.py scripts/ci/cargo_test.bat -p archeaxis-api --offline` reached the wrapper but exited 255 with no Cargo receipt output; direct Cargo probing confirms the declared toolchain lacks an available `link.exe`, so Rust execution remains environment-blocked.

- 2026-09-13 batch-wrapper smoke: a temporary project-local `.bat` wrote `dev-bat-proof.txt` inside run `be268a2d33/fd73854db95b/tmp` through `dev.py`; execution receipt exit 0 and postcondition file exists. The temporary batch file was removed after verification. This isolates wrapper correctness from the MSVC/Cargo toolchain blocker.

- 2026-09-13 batch wrapper follow-up: `dev.py` batch normalization regression passed (`tests/runtime-paths/test_dev_paths.py -k batch_entrypoint`, 1 passed). The declared MSVC `link.exe` files exist, but `vcvars64.bat` initialization returns 255 in this portable environment; no external toolchain files were changed.

- 2026-09-13 Rust toolchain probe: with explicit MSVC 14.44.35207 and Windows SDK 10.0.26100.0 `PATH/INCLUDE/LIB`, direct `cargo test -p archeaxis-api --offline` compiled the workspace but one scheduler test panicked because direct invocation lacked `ARCHEAXIS_PYTHON` (the project requires `dev.py`). A subsequent `dev.py` cargo attempt preserved the run root but the child still could not resolve `link.exe`; the toolchain initialization/environment handoff remains blocked and no external files were changed.

- 2026-09-13 managed batch-wrapper regression: `scripts/runtime/dev.py --pytest tests/runtime-paths/test_dev_paths.py -k batch_entrypoint` used run `be268a2d33/f4701f2ed273` and passed 1 selected test; cache stayed under that run root.

- 2026-09-13 managed desktop regression: `scripts/runtime/dev.py --pytest tests/test_desktop_staging.py tests/test_desktop_runtime.py tests/test_desktop_launch.py tests/test_axw_run204_supervisor.py` used run `be268a2d33/086092f6a056` and passed 32 tests; all pytest cache/output remained inside `.project-local/runs`.

- 2026-09-13 managed Core entry regression: `dev.py --pytest tests/test_core_launch.py tests/test_core_client.py tests/test_test_launcher_contract.py` used run `be268a2d33/4d0e877573b2` and passed 33 tests; cache/output stayed inside `.project-local/runs`.

- 2026-09-13 release/ candidate contract regression: release manifest, SBOM coverage, release identity/evidence receipt and candidate manifest tests passed (75 passed, 4 process-reap cases deselected due the known Windows taskkill restriction; warnings only from unavailable NuGet/NLP/deprecations).

- 2026-09-13 Rust linker recheck: using the declared external MSVC 14.44.35207 cl.exe/link.exe and project-local ARCHEAXIS_PYTHON, direct cargo test -p archeaxis-api --offline reached linking but exited 101 because the declared Windows SDK tree has no kernel32.lib (LNK1181). This is an external toolchain completeness blocker; no project or external files were modified.

- 2026-09-13 test-corpus path normalization: removed the pipeline documentation claim that audio input is hardwired to `D:/All projects/ceshi`; it now states that `ARCHEAXIS_PIPELINE_SOURCE_ROOT` must name an approved test source and explicitly excludes the real资料库. No external corpus or shared library was accessed or modified.

- 2026-09-13 current path-authority measurement: `scripts/check_path_conventions.py --measure` observed 1,994 tracked paths, all 1,994 owned, with 0 unowned, 0 ambiguous, and 0 denied-but-tracked; the JSON gate also passed. This classifies repository paths only and does not authorize changes to external libraries, Green, real资料库, or test corpus.

- 2026-09-13 cache-path documentation normalization: capability requirements now state that Whisper/HF cache is routed by `scripts/runtime/dev.py` into the project-local run cache, replacing the old user-home `~/.cache/huggingface` wording. No user-home cache was read or changed.

- 2026-09-13 pipeline run-root normalization: audio and video pipelines now honor `ARCHEAXIS_RUN_ROOT`, placing receipts and working files under `artifacts/pipeline/{audio,video}` for managed runs; direct fallback remains project-local `task-runtime`. Both scripts compile and repository conventions remain clean. No external corpus was accessed.

- 2026-09-13 retrieval-evaluation run-root normalization: `scripts/pipeline/eval_retrieval.py` now routes its default receipt to `ARCHEAXIS_RUN_ROOT/artifacts/pipeline/eval-retrieval/`; direct fallback is project-local `task-runtime`. The script compiles and repository conventions remain clean.

- 2026-09-13 runtime smoke normalization: `scripts/runtime_http_smoke.py` now writes logs under `ARCHEAXIS_RUN_ROOT/artifacts/runtime-http-smoke` when managed by `dev.py`; direct fallback remains project-local. Pipeline and runtime smoke modules compile, and `tests/test_ci_a0_gates.py` passed 23 tests.

- 2026-09-13 path/run-root regression: `tests/test_taskpack_paths.py tests/runtime-paths/test_dev_paths.py tests/test_ci_a0_gates.py -k "not cleanup_reaps_grandchild"` passed 46 tests with 1 known Windows process-tree case deselected; the full selection reproduced the managed-environment `taskkill.exe` access-denied failure. `check_path_conventions.py --json` still reports 1,994/1,994 owned paths, 0 unowned/ambiguous/denied.

- 2026-09-13 rebuildable-cache cleanup: after confirming no `cargo`/`rustc` process was live, removed only `.project-local/build/cargo/debug/incremental` (4.25 GiB). Postcondition `Test-Path` was false; `.project-local` measured about 9.06 GiB afterward. Cargo dependencies, current debug binary, candidate bundle and receipts were retained; candidate verification remains `ok: true`.

- 2026-09-13 additional run-root normalization: browser smoke, H2 OCR/ASR bake-off, and AXW-096A benchmark defaults now honor `ARCHEAXIS_RUN_ROOT` for runtime, reports, corpus and receipts; direct fallback remains project-local. Targeted regression `tests/test_a0_browser_smoke.py tests/test_h2_bakeoff.py tests/test_axw096a_benchmark.py` passed 19 tests.

- 2026-09-13 private-runtime boundary fix: SenseVoice default model resolution no longer points to `.hermes/task-runtime`; it now uses explicit `ARCHEAXIS_SENSE_VOICE_MODEL_DIR`, managed `ARCHEAXIS_RUN_ROOT/models/sense-voice`, or project `.project-local/task-runtime/models/sense-voice`. ASR/media regression passed 12 tests; source scan found no `.hermes` write-path references in app/scripts/config.

- 2026-09-13 DeepTutor run-root normalization: `DeepTutorBridge` now uses `ARCHEAXIS_RUN_ROOT` for its projection/custody root when managed, with the existing project-local fallback for direct calls. DeepTutor bridge, authority, launch and custody regression passed 15 tests.

- 2026-09-13 report-output normalization: current reports and Golden Journey receipts now use `ARCHEAXIS_RUN_ROOT` artifacts when managed, with project-local task-runtime fallback for direct use. Their tests passed 12 cases; repository conventions and diff checks remain clean.

- 2026-09-13 benchmark-corpus routing: `scripts/prepare_benchmark_corpus.py` now defaults to `ARCHEAXIS_RUN_ROOT/artifacts/benchmark/corpus` under managed runs, avoiding a shared per-tool corpus directory; direct fallback stays project-local. AXW-096A/096C regression passed 9 tests.

- 2026-09-13 Phase-0 isolation normalization: temporary baseline runtime now uses `ARCHEAXIS_RUN_ROOT/tmp` under managed execution, with the existing project-local fallback for direct use. Phase-0 regression passed 11 tests.

- 2026-09-13 media/lifecycle run-root normalization: media adapter temporary work directories and lifecycle browser E2E data now honor `ARCHEAXIS_RUN_ROOT`, with project-local fallback for direct calls. Media/web screenshot regression passed 11 tests; no external corpus or user data was touched.

- 2026-09-13 desktop SSOT documentation repair: capability requirements now label Node/Rust Tauri entries as legacy recovery/compatibility; UI roadmap names C#/Avalonia + Rust Core as the formal track; `apps/desktop/README.md` now reflects the verified .NET/Avalonia build and remaining GUI/installer gaps. YAML parse and CI/current-report regressions passed 28 tests.

- 2026-09-13 legacy-shell wording repair: the A0 browser smoke module now identifies React/Tauri as a compatibility/recovery shell and explicitly keeps C#/Avalonia as formal desktop authority. A0 browser/CI regressions passed 26 tests.

- 2026-09-13 UI contract SSOT repair: `config/product/UI_CONTRACT_V2.json` now names C#/Avalonia as the formal desktop shell and the `apps/ArcheAxis.Desktop/ArcheAxis.Desktop.csproj` production entrypoint; React/Tauri remains an explicitly labeled legacy recovery/behavior reference. `tests/test_ui_contract_v2.py` passed 3 tests; repository conventions passed with 0 issues; `git diff --check` passed. Historical `CURRENT_PRODUCT_PLAN_V2.md` was left unchanged and is treated as historical evidence.

- 2026-09-13 current-plan authority repair: docs/current/CURRENT_PRODUCT_PLAN_V2.md now explicitly identifies itself as the v0.6.8 historical baseline and points current desktop authority to PROJECT_CONTRACT/LANGUAGE_BOUNDARY/R5; legacy Tauri evidence remains historical. Naming/UI contract tests passed 33 cases; repository conventions returned 0 issues after LF normalization; git diff --check passed.

- 2026-09-13 current metadata inventory refresh: read-only scripts/maintenance/inventory_project.py output saved to .project-local/runs/r5-normalization-20260913/inventory.json. Scope is exact Git root; .project-local observed at 9,728,764,460 logical bytes with 186 permission errors, 4 reparse skips, and 110 opaque exclusions; exit 1/status partial. This is evidence for further CLEAN01/CLEAN02 work, not a complete size or cleanup claim; no external roots or private state were opened.

- 2026-09-13 CLEAN06/CLEAN07 exact cache cleanup: reviewed .project-local/cache/uv-probe (no source references; rebuildable probe cache, ~0.73 GiB) and removed only that exact path. Postcondition Test-Path was false. Read-only inventory after cleanup reports .project-local 8,942,454,352 logical bytes (down from 9,728,764,460; ~0.73 GiB reclaimed), still partial with 186 permission errors; report .project-local/runs/r5-normalization-20260913/inventory-after-uv-probe.json. Cargo deps, model/data roots, receipts and private boundaries were untouched.

- 2026-09-13 X01 cancellation regression recheck: targeted 	est_dev_paths.py -k interrupted_output or cleanup_failure or windows_cleanup yielded 2 passed and 1 failed. Owned cancellation and cleanup-failure semantics passed; Windows parent/grandchild cleanup remains ENVIRONMENT_FAIL because managed 	askkill.exe /T /F returned nonzero/access denied. No product success claim; no fallback kill or external process change was introduced.

- 2026-09-13 R5 package validation: docs/authority/taskpack-0912-r5/verify_package.py returned PASS (23 original tasks, 18 additional slices, 10 cleanup, 4 repository, 4 migration slices; 173 active files). The verifier explicitly reports product_tests_run=false, windows_cleanup_performed=false, and current_head_checked=false; this is package integrity only, not implementation or release qualification. Legacy evidence/worker/format checkers correctly rejected missing old-format R5 inputs and were not counted as passes.

- 2026-09-13 generated-bytecode cleanup: removed 79 source/test/script __pycache__ directories (1,314 files; 19,577,239 bytes), excluding private runtimes, .project-local, .venv, and site-packages. Repository conventions 0 issues; path ownership 1994/1994; UI plus non-Windows runtime regressions 22 passed (1 Windows cleanup case intentionally deselected due known managed taskkill blocker); diff check passed.

- 2026-09-13 output-path leak repair: desktop/scripts/verify_zip_distributions.ps1 now stages lifecycle temporary data under .project-local/task-runtime instead of legacy .hermes/task-runtime; a release-manifest regression assertion prevents reintroduction. Targeted lifecycle tests passed 3 (29 deselected).

- 2026-09-13 test-entry routing repair: scripts/ci/run_tests.ps1 now prefers ARCHEAXIS_PYTHON, then managed .project-local/build/venv/Scripts/python.exe; root .venv is compatibility fallback only. CI classifier/A0 path tests passed 7; repository conventions remained clean.

- 2026-09-13 cross-shell test routing: scripts/ci/run_tests.sh now mirrors PowerShell resolution and prefers .project-local/build/venv before legacy root .venv; R5-DESKTOP-START.md command updated accordingly. CI/nightly routing tests passed 4; repository conventions 0 issues; diff check passed.

- 2026-09-13 Avalonia current-head recheck: attempted dotnet build apps/ArcheAxis.Desktop/ArcheAxis.Desktop.csproj --no-restore --nologo with telemetry opt-out and project-local output intent; command could not start because dotnet is absent from PATH and standard local candidates were not present. Classified ENVIRONMENT_FAIL/NOT_EXECUTED; no SDK download or external toolchain mutation. Prior successful Avalonia build evidence remains bound to its recorded SHA and does not promote this recheck.

- 2026-09-13 pipeline documentation routing: pipeline README and pipeline_audio.py usage now invoke dev.py with .project-local/build/venv, matching actual managed output routing; no functional pipeline code changed. Repository conventions 0 issues; diff check passed.

- 2026-09-13 current-head binding recheck: branch codex/full-loop-0906, HEAD 3d560253c0d61dc0baa0728eb3fc0a74c5b67e26; no upstream is configured in this checkout; R5-STATE baseline remains c06b234ca335b9cbb2c1fde270851e2390c36b89. git status --short reports 60 modified/untracked entries including preserved history and current edits. No cloud-sync, commit, reset, or cleanup claim made.

- 2026-09-13 local-ref comparison: HEAD 3d560253c0d61dc0baa0728eb3fc0a74c5b67e26 equals local origin/codex/full-loop-0906; local main 1e9813ea2bd49f47d334ba6717c78d3e9feda6ce equals local origin/main. No fetch was performed; these are cached local refs, not live cloud or CI evidence.

- 2026-09-13 CLEAN01 scope refresh: metadata-only checks against the canonical shared-resource index confirm shared_models, shared_tools, green_application, green_material_library, and project_test_corpus all exist as ordinary directories with no reparse points. Report: .project-local/runs/r5-normalization-20260913/shared-resource-scope.json; all rows explicitly set write_authorized=false. No content was enumerated or modified.

- 2026-09-13 final runtime spill scan: pp/, scripts/, services/, and config/ contain no .hermes path joins, system TEMP writes, or user-profile output writes. Remaining matches are project-local lifecycle comments or explicit user-supplied workspace path normalization (xpanduser), not default output destinations. No new leak found; source scan result is structural evidence only.

- 2026-09-13 uv-cache cleanup rollback: attempted removal of `.project-local/cache/uv` and `uv-python` revealed the active test interpreter is a uv trampoline and could not spawn without managed Python. Rebuilt Python 3.13.14 and CI group into project-local cache/environment using explicit UV_PYTHON_INSTALL_DIR, UV_CACHE_DIR, and UV_PROJECT_ENVIRONMENT; no user-private uv directory or external toolchain was read/modified. Post-recovery UI/release tests passed 5 and repository conventions 0 issues. These caches are now classified retain-until-interpreter-migration.
- 2026-09-13 post-recovery gate recheck: R5 `verify_package.py` returned PASS; path ownership remained 1994/1994 with 0 ambiguous; repository conventions initially found only a missing final LF in the live ledger, fixed and rechecked to 0 issues. Package verifier still reports product_tests_run=false, windows_cleanup_performed=false, current_head_checked=false.
- 2026-09-13 normalization regression gate: targeted UI contract, release lifecycle, current-report, Golden Journey, phase0, screenshot/media, and runtime-path suites passed 88 tests (1 Windows cleanup case deselected for known managed taskkill blocker; 9 subtests passed). Two warnings were environmental/dependency deprecations; no product failure. No external data roots were used.
- 2026-09-13 evidence-checker interpreter routing: `scripts/check_evidence_commands.py` now resolves managed `.project-local/build/venv` before legacy root `.venv`, matching `run_tests` shell entrypoints. Targeted checker tests passed 2; repository conventions remained clean.
- 2026-09-13 cross-shell syntax check: `run_tests.ps1` parsed successfully and both shell entrypoints statically prefer `.project-local/build/venv`, then legacy `.venv`. `bash -n` was NOT_EXECUTED because Bash is absent from this Windows environment; no cross-shell pass claim made.
- 2026-09-13 historical mechanical gates recheck: R3.1 format matrix passed (16 rows; 0 complete, 14 partial, 2 custody_only), worker reachability passed (12 workers; 10 routed, 2 exempted), and R14 evidence index passed (17 slices; 81 tracked evidence, 3 receipt evidence). These validate inherited mechanical claims only; they do not qualify R5 current product or independent audits.
- 2026-09-13 R5 format coverage structural audit: `FORMAT-COVERAGE.json` parses as `archeaxis.format-retention/v1`, plan `AAK-FOLLOWUP-20260908-R3`, exactly F01-F16; all rows include format_id, qualification_state, preserved, and all 16 remain `NOT_REQUALIFIED` (12 core, 3 expansion, 1 explicit_boundary). No qualification claim was upgraded.
- 2026-09-13 run-root regression gate: `test_dev_paths.py` plus report, Golden Journey, Phase0, and benchmark integration suites yielded 51 passed, 1 failed (Windows owned parent/grandchild cleanup; managed `taskkill.exe` access denied), and 9 subtests passed. The failure remains environment-scoped and is not promoted to product failure or success.
- 2026-09-13 evidence command suite: full `tests/test_evidence_commands.py` passed 19 tests after managed-interpreter routing change. One pytest cache permission warning remains under the known ACL-isolated project runtime cache; no functional failure.
- 2026-09-13 controlled-volume recheck after uv environment recovery: `.project-local/build` 6,280,203,058 bytes (5.85 GiB), `cache` 731,239,189 bytes (0.68 GiB), `runs` 1,962,634,233 bytes (1.83 GiB), `task-runtime` 48,977,678 bytes (0.05 GiB). Counts are logical bytes from readable regular files; private/ACL/reparse exclusions remain outside attribution. No hidden external path was scanned.
- 2026-09-13 post-test bytecode cleanup: removed 37 newly regenerated source/test `__pycache__` directories (162 files; 2,038,289 bytes), again excluding all managed/private environments and dependency caches. Repository conventions 0 issues; diff check passed.
- 2026-09-13 normalization/ownership gate: taskpack path routing, metadata inventory, path conventions, and language boundary suites passed 61 tests with 2 subtests. One known pytest cache ACL warning remains; no external data roots were accessed.
- 2026-09-13 pytest boundary gate: `test_pytest_boundary.py` and selected workspace boundary tests passed 3. This confirms test temp resolution remains inside the project-managed runtime; Starlette deprecation and known ACL cache warnings are non-product warnings.
- 2026-09-13 format/worker route regression: text facts, PDF structure/order, media, caption, archive, worker reachability, and image media type suites passed 72 tests. Only the known pytest cache ACL warning appeared; no external corpus or model library was accessed.
- 2026-09-13 bulk-worker regression: text, PDF, Office, HTML, structured, media, and transport batch suites passed 50 tests. Output routing remained project-managed; only known pytest cache ACL warning appeared.
- 2026-09-13 core contract/migration regression: learning event store/scheduler/outcome/artifact/security, migration runner, language boundaries, and vocabulary contract suites passed 85 tests with 29 subtests. Only the known pytest cache ACL warning appeared.
- 2026-09-13 learning-loop regression: learning loop E2E, knowledge-to-learning artifacts, co-learning, distillation review, and quiz path suites passed 22 tests; only the known pytest cache ACL warning appeared.
- 2026-09-13 workspace delivery boundary regression: workspace delivery lifecycle, crash recovery, learning API security, and browser failure/retry replay suites passed 9 tests; only known pytest cache ACL warning appeared.
- 2026-09-13 final bytecode cleanup pass: removed 49 source/test `__pycache__` directories (209 files; 2,875,052 bytes), excluding all managed/private environments. Repository conventions 0 issues; `git diff --check` passed.
- 2026-09-13 R5 package gate re-read: `docs/authority/taskpack-0912-r5/verify_package.py` exited 0 (`PASS`; 23 original tasks, 18 additional slices, 10 cleanup, 4 repo, 4 migration, 173 active files). Validator explicitly reports `product_tests_run=false`, `windows_cleanup_performed=false`, `current_head_checked=false`; these remain open delivery layers.
- 2026-09-13 path conventions gate re-read: `scripts/check_path_conventions.py --json` exited 0 (`passed=true`, 1,994 tracked paths, 100% owned, 0 unowned/ambiguous/denied-but-tracked). Its ownership measurement is bound to commit `b81c789d8d6363f53ddfadf5e9da9e7735bb9338`; reported worktree drift is retained as a measurement caveat, not silently promoted.
- 2026-09-13 language boundary gate re-read: `scripts/check_language_boundaries.py --json` exited 0 (`passed=true`, protocol/contracts/schema major 1, hello/envelope checks passed).
- 2026-09-13 repository conventions gate re-read: `scripts/check_repository_conventions.py --format json` exited 0 (`issue_count=0`).

- 2026-09-13 HL01 source registration: generated docs/current/R5-HL01-SOURCE-REGISTRY.json from the four R5 research-v15 originals; counts are methods 40, research 35, disciplines 36, resources 104 (215 total). Each category records source SHA-256, namespace, candidate qualification, and not-activated status. Private history was not accessed; historical continuity and Core ID/import receipts remain open, so X00 stays PARTIAL_NEEDS_WORK.

- 2026-09-13 HL01 registry regression: tests/test_hl01_source_registry.py passed 1 test. It locks the four source counts and candidate/not-activated/private-history boundaries; pytest emitted only the known ACL cache warning.
- 2026-09-13 HL01 mapping increment: added `scripts/generate_hl01_source_registry.py` to deterministically derive 215 namespaced `hl01:` Core-ID candidates (version 1) from the four hashed R5 source files. Regeneration and `tests/test_hl01_source_registry.py` passed; IDs remain candidate/not-activated until the Core import receipt path is implemented.
- 2026-09-13 HL01 Core source import increment: added `app/evidence/hl01_import.py` and `SourceStoreV2.has_source()` to persist one append-only SourceObjectV2 per R5 candidate record (215 rows) and report idempotent retries. Targeted registry/import/source-store tests passed 5 tests; the import remains candidate-only and does not activate learning records.
- 2026-09-13 HL01 readback increment: added `SourceStoreV2.list_sources()` and verified four persisted source rows, stable IDs, version 1, and original-retained flags after a duplicate import. Targeted import/source-store tests passed 4 tests; repository conventions remained at 0 issues.
- 2026-09-13 HL01 receipt increment: `import_registry_candidates()` now optionally records a completed `workspace.sqlite` command/job/outbox receipt with registry and source-ID hashes. A replay with the same command ID is idempotent. Targeted import/source-store tests passed 4 tests; no candidate is activated.
- 2026-09-13 HL01 entrypoint increment: added `scripts/import_hl01_registry.py` with required explicit `--db`, `--registry`, and `--command-id` arguments. Help smoke passed; missing default database/user paths are refused, preserving the external and real-user data boundaries.
- 2026-09-13 HL01 CLI end-to-end smoke: in an isolated `.project-local/runs/hl01-cli-smoke` SQLite database, applied `workspace.sqlite` and `knowledge-governance.sqlite`, ran the CLI twice, and read back `sources=215`, `receipts=1`, `jobs=1`; first run imported 215, second reported 215 duplicates. No external or real-user database was accessed.
- 2026-09-13 HL01 rights-boundary hardening: `rights_status` is now required by the import API and CLI; no source is implicitly classified as owned. Targeted registry/import tests passed 2 tests and CLI help exposes the four explicit choices; repository conventions remained at 0 issues.
- 2026-09-14 HL01 integrity/path hardening: registry imports now resolve relative source paths from the repository/registry ancestry and rehash plus size-check each source before writing Core objects. The targeted test runs from a different working directory; registry/import tests passed 2 tests and conventions remained at 0 issues.
- 2026-09-14 HL01 boundary regression: absolute source paths outside the repository root are rejected before any read; the path-escape test and import smoke passed 2 tests. No external drive or protected resource root was accessed.
- 2026-09-14 HL01 compatibility regression: existing raw import, workspace job/outbox, workspace migration, and HL01 import suites passed 19 tests. Original-asset retention and command receipt semantics remain intact; only the known pytest ACL cache warning appeared.
- 2026-09-14 HL01 receipt binding hardening: command receipt payload now includes explicit `rights_status`; replaying the same command with a changed rights state is rejected as an immutable-source conflict. Targeted HL01 tests passed 3 tests; repository conventions remained at 0 issues.
- 2026-09-14 HL01 fail-closed registry validation: imports now reject missing/truncated records, category-count mismatches, unknown source paths, or duplicate Core IDs before any write. Tampered-registry and normal import tests passed 5 tests; repository conventions remained at 0 issues.
- 2026-09-14 HL01 repository-root binding: added explicit `repository_root` to the importer and CLI, keeping external source paths rejected even when a registry file is staged elsewhere. Hash-tamper and normal import tests passed 5 tests; repository conventions remained at 0 issues.
- 2026-09-14 HL01 receipt readback: added `verify_registry_receipt()` to join the durable command receipt and job with Core source rows, verifying succeeded state and source-count consistency. Targeted HL01 tests passed 5 tests; repository conventions remained at 0 issues.
- 2026-09-14 cross-module regression: HL01, source-store, raw import, workspace outbox/API, and dev-path suites yielded 68 passed, 9 subtests passed, 1 environment-scoped failure. The only failure is Windows process-tree cleanup because managed `taskkill.exe` returned access denied; path conventions, language boundaries, repository conventions, and `git diff --check` all passed. Process command-line inspection was also denied, so no cleanup claim is made.
- 2026-09-14 HL01 static gate: `py_compile` succeeded for all changed modules/tests and direct imports of the importer, receipt verifier, and source store succeeded (`imports-ok`). Repository conventions remained at 0 issues and `git diff --check` passed.
- 2026-09-14 HL01 CLI readback output: CLI now appends a read-only `readback` object after import. A new command ID replayed twice against the isolated smoke DB and returned `source_count=215`, `state=succeeded`; an older pre-rights-binding command receipt was correctly rejected as a semantic conflict and was not silently reused.
- 2026-09-14 HL01 lint gate: Ruff initially found three import issues; minimal import cleanup fixed all of them. Ruff then passed all changed HL01 modules/tests, targeted tests passed 6, repository conventions remained at 0 issues, and `git diff --check` passed.
- 2026-09-14 R5 package/boundary recheck: `verify_package.py` passed (23 original tasks, 18 additional, 10 cleanup, 4 repo, 4 migration, 173 active files); path conventions passed with 1,994/1,994 owned, language boundaries passed, repository conventions reported 0 issues, and `git diff --check` passed. Package validator still explicitly reports product tests/current-head/windows-cleanup flags as false.
- 2026-09-14 HL01 final target gate: Ruff passed all changed HL01 modules/tests; registry, importer, and source-store tests passed 9 tests; repository conventions reported 0 issues and `git diff --check` passed. The known pytest ACL cache warning remains non-functional.
- 2026-09-14 constrained bytecode cleanup: removed 26 re-creatable `__pycache__` directories (1,919,324 bytes) only under `app/`, `scripts/`, `tests/`, and `shared/`; postcondition confirmed zero remaining in those roots. Managed/private environments and user assets were excluded.
- 2026-09-14 HL01 handoff documentation: added `docs/current/R5-HL01-IMPORT.md` with explicit CLI paths, migration prerequisites, rights selection, integrity/readback behavior, and protected-root boundaries. Repository conventions and Ruff checks passed; `git diff --check` passed.
- 2026-09-14 R5 repeatable gate: the repository-local package verifier, path conventions, language boundaries, repository conventions, and `git diff --check` all passed. The package verifier still reports product tests/current-head/Windows cleanup as false; no completion promotion was made.

### 2026-09-14 CLEAN03 静态外溢生产者追踪器（本地实现）
- 新增 `scripts/maintenance/trace_output_producers.py`：只读校验精确 Git 根，跳过 `.hermes/.zcode/.codex`、`.project-local`、虚拟环境、构建和重解析点；只扫描代码/配置文本，输出逐条 `canonical_path/producer/entrypoint/config_source/owner_evidence` 候选，不读进程、日志、外置库或私有状态。
- 新增 `tests/maintenance/test_trace_output_producers.py`；项目解释器运行结果 `2 passed`，Ruff `All checks passed`。
- 运行证据：`.project-local/runs/be268a2d33/r5-spill-trace-20260914e/artifacts/spill-trace.json`，命令经 `scripts/runtime/dev.py`，HEAD `3d560253c0d61dc0baa0728eb3fc0a74c5b67e26`，输出 1,037 条候选、687,604 bytes；退出码 0。
- 限制：这是静态候选台账，不证明运行时实际写入；外部根、进程命令行和日志仍需单独授权/实测；未执行任何删除或配置改写。
- 2026-09-14 CLEAN03 boundary regression follow-up: CLI output destinations outside `.project-local` now fail closed with a clear error; tracer tests passed 3 and Ruff passed. The earlier broken-pipe run was deleted with a verified postcondition and is not evidence.
- 2026-09-14 CLEAN03/CLEAN04 routing regression: output-producer tracer, metadata inventory, and project output-routing contract suites passed 32 tests with 2 subtests. Only the known ACL pytest-cache warning appeared; no external roots or private runtime directories were read.
- 2026-09-14 CLEAN04 desktop Rust lifecycle path repair: `desktop/src-tauri/tests/backend_lifecycle.rs` no longer points lifecycle data or Python runtime at `.hermes`/root `.venv`; both use the managed `.project-local` build/runtime paths. `rustfmt` was unavailable, so formatting was structurally inspected; repository conventions and language-boundary gates passed, and `git diff --check` passed. The ignored smoke tests were not executed because Cargo/rustfmt are unavailable in this environment.
- 2026-09-14 Rust lifecycle routing contract: added a regression assertion that the ignored desktop smoke fixture uses `.project-local` runtime/data paths and contains no `.hermes` or root `.venv` target. Contract tests passed 10; repository conventions remained 0 issues.
- 2026-09-14 CLEAN04 worker-checker routing: `scripts/ci/check_vnext_workers.py` now allocates all synthetic inputs under the current `.project-local` run (or validated project-local fallback), and rejects an external `ARCHEAXIS_RUN_ROOT`. Ruff passed, CI classifier tests passed 31, and the real workers-vnext checker passed via `scripts/runtime/dev.py` (run `r5-worker-routing-20260914`, exit 0).
- 2026-09-14 desktop runtime Python path repair: `desktop/src-tauri/src/runtime.rs` development profile now resolves `.project-local/build/venv/Scripts/python.exe` instead of root `.venv`; Rust unit fixtures were updated to the same managed path and the contract suite now guards against regression. Contract tests passed 11, repository conventions 0 issues, and `git diff --check` passed. Cargo/rustfmt are unavailable, so Rust compilation remains NOT_EXECUTED.
- 2026-09-14 doctor routing repair: `scripts/doctor_windows.ps1` now checks `.project-local/build/venv` before the historical root `.venv` compatibility fallback; its test contract name and condition were updated accordingly. `tests/test_doctor_windows.py` passed 8, repository conventions 0 issues, and `git diff --check` passed.
- 2026-09-14 R15/F12 deterministic format regression: Canvas, SRT/VTT fixture matrix, archive inventory, JSON Canvas, golden Canvas, and format contract suites passed 47 tests. This is current local behavior evidence only; `FORMAT-COVERAGE.json` remains NOT_REQUALIFIED pending full-chain and independent audit.
- 2026-09-14 worker temp boundary regression: added `tests/maintenance/test_check_vnext_workers_paths.py` covering project-local allocation, cleanup, and external-root rejection. Worker path tests plus CI classifier passed 33; Ruff passed. The known ACL pytest-cache warning remains environmental only.
- 2026-09-14 output-boundary guard: added a repository contract preventing `check_vnext_workers.py` from reintroducing bare system `TemporaryDirectory()` calls; it must use the validated project-local helper. Contract and helper tests passed 14; repository conventions 0 issues and `git diff --check` passed.
- 2026-09-14 CLEAN02 inventory output contract: `inventory_project.py` now supports `--output` only inside the exact project `.project-local` tree, with reparse-point rejection; stdout behavior is preserved. Inventory tests passed 21 (2 subtests), Ruff passed. A current run via `dev.py` wrote `inventory.json` with partial status (102,661 readable files / 10,912,290,226 logical bytes / 186 permission errors); exit 1 is expected for incomplete observation and is not a full-size claim.
- 2026-09-14 source bytecode cleanup: after compile verification, removed 27 re-creatable `__pycache__` directories (1,787,876 bytes) only under `app/`, `scripts/`, `tests/`, and `shared/`; postcondition confirmed zero remaining. Managed/private environments, model caches, and user assets were untouched.
- 2026-09-14 combined normalization regression: path routing, inventory output, spill tracing, worker temp boundaries, Windows doctor, release manifest, Canvas/SRT/VTT/archive, and format contracts passed together: 125 tests, 2 subtests. Only Starlette deprecation and known ACL pytest-cache warnings appeared; no external roots or private state were accessed.

- 2026-09-14 post-regression bytecode cleanup: removed 27 regenerated source/test __pycache__ directories (1,622,935 bytes); postcondition zero under app/scripts/tests/shared. Managed/private environments and user assets retained.
- 2026-09-14 R5 entrance gate after routing changes: package verifier PASS, path conventions PASS, language boundaries PASS, repository conventions 0 issues, and `git diff --check` PASS at HEAD `3d560253c0d61dc0baa0728eb3fc0a74c5b67e26`. Package verifier still reports product tests/current-head/Windows cleanup flags false; this is an integrity gate only.
- 2026-09-14 full Python regression (managed dev run): 2,737 passed, 7 skipped, 135 subtests, 12 failures. Four Windows process-tree/candidate-reap failures are the known managed `taskkill.exe` access-denied environment condition; three optional-adapter failures are missing `newspaper4k`, `youtube-transcript-api`, and `readabilipy` dependencies; the DeepTutor failures occurred only under an overlong run path and pass under short managed run `deeptutor-short` (4 passed); two stale audit assertions were corrected for current HL01 consumers/owner count and current retrieval output routing; the current-head audit now allows only the exact checkout HEAD. No failure was promoted to product pass.
- 2026-09-14 stale-baseline regression fixes: first-wave consumer/owner tests and retrieval data-boundary test now match the current HL01/path-routed implementation; targeted suite passed 6, Ruff passed. The audit still rejects arbitrary undocumented SHAs.

- 2026-09-14 optional adapter environment closure: installed lock-compatible `newspaper4k==0.9.6`, `youtube-transcript-api==1.2.4`, and `readabilipy==0.3.0` into the project-local managed run environment using `UV_CACHE_DIR=.project-local/cache/uv-cache-r5`; no shared or external environment was modified. `tests/test_integrations.py` + `tests/test_adapter_contract.py` passed 97 tests in run `r5-optional-adapters-20260914` (exit 0). Warnings: newspaper NLP extras absent and readabilipy deprecation only.
- 2026-09-14 R5 integrity recheck: taskpack-0912-r5 verify_package PASS (23 tasks, 173 active files; product_tests_run/current_head_checked/windows_cleanup_performed remain false), path conventions PASS (1994 tracked, 0 unowned), language boundaries PASS, repository conventions PASS (0 issues). Optional adapter integration suite passed 97 after project-local dependency install. Candidate process-reap suite remains 32 passed / 3 failed because managed taskkill.exe is denied (WinError 5); no cleanup behavior was falsely promoted.
- 2026-09-14 post-adapter source cleanup: removed 14 regenerated __pycache__ directories only under app/scripts/tests/shared; postcondition Remaining=0. No private/runtime environments or external roots touched.
- 2026-09-14 CLEAN07 execution from reviewed r5-dsh-runs-audit-2/candidates.json: validated 578 non-empty candidates stayed under .project-local/runs/be268a2d33 and excluded artifacts; removed 453 paths successfully. 125 paths remain due ACL-denied pytest trees (representative failures recorded in command output); no elevation or ACL changes attempted. Artifact directories remain present (1037 observed).
- 2026-09-14 post-cleanup inventory: metadata-only scan wrote .project-local/runs/be268a2d33/r5-inventory-post-cleanup-20260914/artifacts/inventory.json; status partial (exit 1) with .project-local 9,716,222,206 logical bytes, 78,721 readable files, 186 permission errors, 6 reparse skips, and 167 excluded private/mixed entries. This is logical observed size, not allocated disk usage; inaccessible entries remain explicitly unknown.
- 2026-09-14 CLEAN07 retry: re-attempted all 125 remaining reviewed candidates; 0 removed / 125 failed with the same ACL-denied pytest-tree condition. No ACL, ownership, or process changes made; blocker remains environmental.
- 2026-09-14 post-cleanup routing regression: project output-routing contract plus inventory tests passed 33 tests and 2 subtests in run r5-post-cleanup-contract-20260914 (exit 0).
- 2026-09-14 G11 desktop shell repair: replaced the formal Avalonia MainWindow placeholder with the ArcheAxis workspace shell (workspace navigation, import/learning entry cards, status summary, and CoreStatusText updates for connection/configuration state). Added a regression contract; tests/test_project_output_routing_contract.py passed 13 tests and Ruff passed in run r5-desktop-shell-contract-20260914. Rust/.NET compilation and visible Windows runtime remain NOT_EXECUTED.
- 2026-09-14 G05/G11 desktop entry interaction: wired the formal Avalonia shell import action to StorageProvider.OpenFilePickerAsync and added a learning-path action with explicit status feedback. The routing contract suite passed 13 tests and Ruff passed in run r5-desktop-import-shell-20260914; visible Windows execution and real Core import remain NOT_EXECUTED.
- 2026-09-14 desktop-to-Core import bridge: selected files are read through Avalonia StorageProvider, encoded as base64, and submitted to the owned Core POST /api/v1/imports using the verified launch token; partial submission and interruption are surfaced in the UI. Static routing contract passed 13 tests and Ruff passed in run r5-desktop-core-import-20260914. Real Windows/Core runtime remains NOT_EXECUTED.
- 2026-09-14 desktop learning-entry follow-up: X03/X08/X11 gap review confirms backend learning APIs exist but default Avalonia UI still lacks queue rendering; current shell now exposes an explicit learning action and import-to-Core bridge. No claim of full learning closure; visible GUI and restart continuation remain pending.
- 2026-09-14 Core import/client regression: tests/test_core_client.py and tests/test_research_artifact_runtime_loop.py passed 12 tests in run r5-core-client-20260914 (exit 0), covering authenticated request construction and reviewed artifact persistence. This does not replace a compiled desktop runtime test.
- 2026-09-14 desktop validation: MainWindow.axaml XML parse passed (XAML_XML_OK); desktop output-routing contract plus Core client tests passed 24 tests in run r5-desktop-final-contract-20260914; Ruff and git diff check passed. No new learning-queue API was invented because the frozen Core contract exposes only item-key state/events.
- 2026-09-14 final full Python regression: managed run r5-full-regression-final-20260914 completed 2,739 passed, 7 skipped, 135 subtests, 11 failures. Failures: one Windows process-tree cleanup, three candidate reaping (taskkill WinError 5), and seven backup/DeepTutor cases caused by overlong run paths. Short-path confirmation passed backup 8 and DeepTutor 4 in runs bkp-short and dt-short2. No product pass was promoted; long-path and process-control limitations remain environment blockers.
- 2026-09-14 short-run full regression: run r5f completed 2,746 passed, 7 skipped, 135 subtests, 4 failures. All remaining failures are Windows process-tree/candidate reaping where taskkill.exe is denied (WinError 5); backup and DeepTutor long-path failures disappeared with the short run id. This is the strongest current Python evidence, but not a full product or Windows desktop qualification.
- 2026-09-14 learning/governance contract regression: reviews SM2, mastery signal, machine knowledge, and evaluation governance tests passed 31 tests in run r5-learning-contract-20260914 (exit 0). This verifies backend governance contracts only; default desktop queue and human long-term learning evidence remain open.
- 2026-09-14 post-full-regression cleanup: checked app/scripts/tests/shared for regenerated __pycache__; 0 found and 0 remained. Managed environments, build caches, evidence, and user assets were untouched.
- 2026-09-14 desktop entry documentation alignment: R5-DESKTOP-START now describes the implemented workspace shell and authenticated import bridge while retaining explicit NOT_EXECUTED status for visible Windows runtime, compilation, and full learning UI. Repository conventions recheck returned 0 issues.
- 2026-09-14 R5-STATE correction: X03 gap now reflects the implemented workspace shell and file-to-Core import bridge; it remains PARTIAL because learning queue rendering, DeepTutor default mount, and complete session/attachment recovery are open. STATE JSON parse, repository conventions, and diff-check passed.
- 2026-09-14 learning queue contract: added read-only Rust Core GET /api/v1/learning/items projection (one latest deadline per item), documented it in packages/contracts/v1/openapi-outline.yaml, and wired the Avalonia learning action to read its count. OpenAPI YAML and desktop contract tests passed (13); Rust compile/runtime remains NOT_EXECUTED because cargo is unavailable.
- 2026-09-14 learning queue contract readback: offline OpenAPI contract examples plus Core client tests passed 28 tests in run r5-openapi-contract-20260914 (exit 0); only existing jsonschema deprecation warnings. No duplicate route or schema-reference conflict detected.
- 2026-09-14 Rust queue endpoint static review: corrected JSON row-count ownership ordering before compilation (count captured before rows moves into serde_json). Cargo/rustfmt remain unavailable; no compile claim.
- 2026-09-14 state alignment: X03 gap now records the Core learning-items query endpoint as implemented while keeping desktop question rendering/review submission, DeepTutor default mount, and full session/attachment recovery open. STATE JSON reparse passed.

### 2026-09-14 current runtime-tree recheck

- Rechecked `.project-local/runs`: `be268a2d33` 1.829 GiB, active managed test venv 0.723 GiB, remaining named run trees each <=0.222 GiB.
- Rechecked repository top-level readable sizes: `.project-local` 9.483 GiB, `.venv` 0.876 GiB, `.hermes` 0.463 GiB, `docs` 0.461 GiB; `.git` 0.450 GiB.
- The 60+ GiB claim is not reproduced by readable regular-file totals in this checkout. ACL-denied and reparse-skipped content remains un-attributed; no ACL changes or broad deletion performed.
- `candidates.json` remains as the audit manifest at `.project-local/runs/be268a2d33/r5-dsh-runs-audit-2/candidates.json` (529,527 bytes); prior cleanup receipt remains authoritative for 453 removed / 125 ACL-denied paths.
- Classification: `PARTIAL`; generated build/cache trees remain available for reproducibility and are not deleted without a refreshed per-path manifest.

### 2026-09-14 output-producer trace

- `scripts/maintenance/trace_output_producers.py` ran against the exact Git root and wrote `.project-local/runs/path-trace-current-20260914.json`; exit 0.
- The structural scan recorded 1,049 candidates and 3 limitations. Candidates are source tokens only, not proof of runtime writes.
- The dominant tokens are governed run/output variables (`ARCHEAXIS_RUN_ROOT`, `ARCHEAXIS_DATA_DIR`, `ARCHEAXIS_PYTHON`, `CARGO_TARGET_DIR`, `UV_CACHE_DIR`) plus test temporary-directory APIs; no private runtime directories were opened.
- This does not yet constitute a full runtime path proof; live process command lines and external roots remain outside the scan boundary.

### 2026-09-14 user-provided Deep Adaptation TaskPack diff audit

- Read the user-provided 2026-09-13 attachment and compared it with current R5 authority/state and current cleanup/path evidence.
- Added `docs/current/R5-MASTER-TASKPACK-AUDIT-20260914.md`, classifying aligned direction, stale cleanup/baseline numbers, unverified external claims, and the executable gap order.
- The attachment is retained as a directional supplement; it does not replace the immutable R5 package, live state, or independent-audit gates.

### 2026-09-14 SSOT/path/format gate rerun

- Targeted governance suite (`test_architecture_guard.py`, `test_path_conventions.py`, `test_taskpack_paths.py`, `test_format_matrix.py`) passed: 59 tests.
- Pytest emitted one cache warning because the existing `.project-local/task-runtime/pytest-cache` ACL denies writes; this is an environment residue, not a product pass.

### 2026-09-14 HL01 directed verification

- `tests/test_hl01_source_registry.py` and `tests/test_hl01_import.py`: **6 passed** under the managed project interpreter.
- Evidence covers 215 candidate records, idempotent replay, immutable rights status, repository-root escape rejection, truncated registry pre-write failure, and source-hash pre-write failure.
- X00 state was updated to reflect this verified local behavior; production Core database import and visible Windows host remain unexecuted.

### 2026-09-14 desktop dependency SSOT reconciliation

- Updated `docs/environment/EXTERNAL_DEPENDENCIES.md`: C#/Avalonia `apps/ArcheAxis.Desktop/` is the formal shell; Node/Rust Tauri entries are explicitly legacy recovery/compatibility only. Added the formal .NET/Avalonia dependency entry and project-local build routing.
- Targeted language/architecture/UI governance suite passed: **41 tests**.
- External shared dependency paths and private runtime state were not opened or changed.

### 2026-09-14 R5 package integrity recheck

- `docs/authority/taskpack-0912-r5/verify_package.py` returned `PASS`: 23 tasks, 38 original scenarios, 18 additional slices, 173 active files.
- Receipt `.project-local/runs/r5-package-verify-20260914.json` binds the result to HEAD `3d560253c0d61dc0baa0728eb3fc0a74c5b67e26`.
- The verifier explicitly reports `product_tests_run=false`, `windows_cleanup_performed=false`, and `current_head_checked=false`; package integrity is therefore not a product or release pass.

### 2026-09-14 refreshed cleanup disposition

- Added `docs/current/R5-CLEANUP-MANIFEST-20260914.md` with current top-level observations and explicit KEEP / REBUILDABLE / EVIDENCE / BLOCKED / UNKNOWN dispositions.
- Current readable `.project-local` total is 9.483 GiB; build/cargo and active test venv remain retained for reproducibility.
- No deletion or ACL mutation was performed by this manifest update.

### 2026-09-14 rebuildable cache cleanup

- Removed `.project-local/cache/uv-cache` (498,671,069 bytes / 0.464 GiB) as a reviewed rebuildable download cache.
- Postcondition `Test-Path -LiteralPath .project-local/cache/uv-cache` returned false; no source, evidence, interpreter, external library, or user data was touched.

### 2026-09-14 human-learning loop regression

- Combined learning path, scheduler, outcome, event store, loop E2E, artifact projection, and learning API security suite passed: **37 tests**.
- X08 state now records this local evidence while retaining open gaps for default GUI, question correction/exposure, teach-back, interleaving, burden, and descendant-process coverage.
- One pytest cache warning remains from the pre-existing ACL-denied `.project-local/task-runtime/pytest-cache`; no ACL changes made.

### 2026-09-14 format matrix directed regression

- Format matrix, workspace multi-format pipeline, DOCX adapter, adapter quality/contract, and learning artifact contract suite passed: **46 tests**.
- X12 state records the evidence as local execution/contract coverage only; current matrix remains **0 complete / 14 partial / 2 custody-only**.
- External Vault round-trip, full source return path, three-theme acceptance, and fresh-machine regression remain unexecuted.

### 2026-09-14 repository conventions gate

- `scripts/check_repository_conventions.py . --format json` passed with `issue_count=0`; receipt `.project-local/runs/repository-conventions-20260914.json`.
- The worktree-wide naming/encoding convention gate remains clean after the current documentation and state updates.

### 2026-09-14 evidence-chain gate

- `check_evidence_index.py --index docs/authority/taskpack-0910-r3/R14-EVIDENCE-INDEX.json --state .../STATE.json --json` passed: 17 slices, 81 tracked evidence entries, 3 receipt entries, 0 failures.
- `check_evidence_commands.py` enumerated 21 recorded commands as runnable; commands were not executed in this pass because the list includes heavy Cargo/probe operations and the current environment lacks the required Rust/.NET toolchains.

### 2026-09-14 R15 matrix mechanical check

- `scripts/check_format_matrix.py --json --matrix docs/authority/taskpack-0910-r3/R15-FORMAT-STATUS.json` passed: 16 rows, 11 Core routes, 10 worker routes, 0 failures.
- Counts remain `complete=0`, `partial=14`, `custody_only=2`; this is a mechanical truth check and does not promote semantic or fresh-machine acceptance.

### 2026-09-14 R13 dependency doctor

- `scripts/launch/core_launch.py --check` passed all 9 required local dependency checks: Core binary, managed Python, text/PDF/OCR workers, PyMuPDF, Tesseract executable and language data, and Cargo wrapper.
- Receipt: `.project-local/runs/r13-core-dependency-check-20260914.json`. DeepTutor/Ollama ports were not running; this check does not prove installer, signing, uninstall, or clean-machine startup.

### 2026-09-14 data-boundary regression

- Combined project-data-boundary, approved-paths, dev-path, inventory, and output-routing suites: **59 passed, 1 failed, 1 skipped, 11 subtests passed**.
- The single failure is the known Windows process-tree cleanup case: `taskkill.exe` returned access denied in this managed environment, so `stop_owned_process` could not reap the test-owned tree.
- Process inspection via `Get-CimInstance Win32_Process` was also access denied; no unowned process was terminated and the failure remains `ENVIRONMENT_FAIL`, not a product PASS.

### 2026-09-14 machine/MCP contract regression

- MCP surface/probe, unseen evaluation, machine-knowledge contract/candidate, and candidate-versioning suites passed: **44 tests**.
- X09 state records this local evidence while keeping real-client method coverage and research-correction chain open.
- This is not an independent R11/R14 audit or a live external MCP qualification.

### 2026-09-14 DeepTutor bridge isolated rerun

- Initial combined run had 4 `unable to open database file` failures from an ACL-denied pytest temp subtree. Re-running `tests/test_deeptutor_bridge.py` with a fresh project-local basetemp passed **4/4**.
- The bridge result covers sidecar rebuild, inbound truth rejection, candidate-only idempotent learning event, and projection-root containment. This is local evidence only; default host mounting and visible desktop runtime remain open.

### 2026-09-14 backup/recovery isolated regression

- `tests/test_backup.py` and `tests/test_axw094b_backup.py` passed **19/19** with a fresh project-local basetemp.
- Coverage includes candidate creation, offline activation restore, compensation failure, validation failure, and recovery-copy preservation.
- Initial combined failures were caused by an ACL-denied reused pytest temp tree; no product code change was made.

### 2026-09-14 runtime delivery gate

- Nightly runtime gates, runtime delivery authority, desktop launch/runtime, crash recovery, and test-launcher contract suites passed: **16 tests**.
- X11 state records local contract/recovery evidence only; non-development Windows GUI, installer/signing/uninstall, and full worker/host dependency closure remain unexecuted.

### 2026-09-14 source/evidence/grounding regression

- Source store/record/discovery/anchor, workspace evidence API, retrieval practice, evidence anchor, and grounded answer suites passed: **44 tests**.
- X07 state records local source/evidence/grounding coverage; cloud claim checking and HL02/HL10 correction-impact paths remain open.

### 2026-09-14 worker reachability gate

- `check_worker_reachability.py --record docs/authority/taskpack-0910-r3/WORKER-REACHABILITY.json` passed: **12 workers**, **10 routed**, **2 explicitly exempted**, 0 failures.
- X06 state records route reachability only; dynamic web capture, structural quality, complex samples, and real model qualification remain open.

### 2026-09-14 multimodal adapter execution regression

- PDF extraction/structure/reading-order/native, OCR config/gate/routes/reading-order, media extraction/route, audio VAD, and golden fixture suites passed: **66 tests**.
- X06 state records local adapter execution evidence; dynamic web capture, complex-sample quality, structural addressing, and real model qualification remain open.

### 2026-09-14 CI/path governance regression

- CI classifier/gates, path conventions/taskpack paths, naming, long-path, approved-path, worker-path, and vNext receipt suites passed: **118 tests**, 1 Windows-specific skip.
- X01 state records broad local governance coverage; process-tree cancellation and full Windows runtime behaviors remain environment-dependent.

### 2026-09-14 donor/qualification governance regression

- Open-source absorption ledger, first-wave owner/consumer audits, research knowledge governance, quality absorption, honest capability, and governance-tamper suites passed: **30 tests**.
- X02 state records candidate/qualification boundary evidence; full M0 semantic review, M1 absorption, and default Windows invocation remain open.

### 2026-09-14 knowledge-to-learning regression

- Knowledge-to-learning artifact, distillation review, learning loop, card projection, co-learning, and knowledge-tracing suites passed: **25 tests**. Combined with the earlier learning loop run, X08 now records **62** locally passing cases across the selected coverage.
- Open gaps remain for default GUI, exposure/question correction, interleaving, teach-back, burden, and full interaction semantics.

### 2026-09-14 handoff/report receipt regression

- Current report generator, golden journey receipt, release evidence receipt, index manifest, and taskpack path suites passed: **34 tests**.
- These checks confirm receipt/index wiring and path references; they do not promote product runtime, installer, or independent audit status.

### 2026-09-14 final contract-format consistency check

- Parsed current R5 state, HL01 registry, path disposition, and OpenAPI outline successfully (`JSON_OK`/`OPENAPI_YAML_OK`).
- UI contract, release identity, taskpack paths, and output-routing contract suite passed: **26 tests**.
- No claim was promoted beyond local structural/contract evidence.

### 2026-09-14 security/authority boundary regression

- Permission, API identity/security, federation security, learning API security, machine candidate contracts, governance tamper, evaluation governance, and Tauri shell/security suites passed: **49 tests**.
- X04 state records local authority-boundary evidence; cross-process DeepTutor machine adapter and final learning/structure contract remain open.

### 2026-09-14 FSRS/review persistence regression

- Learning scheduler, review events, event store, and learning outcome suites passed: **24 tests**.
- X05 state records local persistence/scheduler evidence and confirms review-event input; R5 learning fields, source namespaces, correction append, and archive semantics remain open.

### 2026-09-14 architecture boundary guard

- AST-based `scripts/check_architecture.py . --format json` returned an empty violation list with exit 0; receipt `.project-local/runs/architecture-guard-20260914.json`.
- Formal C#/Avalonia shell, Rust Core/DB writer, and Python worker boundary remains structurally clean; this does not prove compiled/runtime behavior.

### 2026-09-14 quality/evaluation regression

- Text quality, retrieval practice, quality absorption, evaluation governance/fallback/contract, benchmark, quality-report schema, and worker quality regression suites passed: **101 tests**, **30 subtests**.
- Metrics remain separated from knowledge truth and learner mastery; this is local benchmark/contract evidence, not the final pedagogy or independent audit gate.

### 2026-09-14 execution preflight gap

- The project overlay references `scripts/workflow/execution_preflight.py`, but that file is absent in the current checkout; no false PASS was recorded.
- Fallback receipt `.project-local/runs/execution-preflight-gap-20260914.json` records current branch/HEAD/managed Python and the independent governance checks already run.
- Adding the missing helper is a future governance task; it was not invented during this verification pass.

### 2026-09-14 execution preflight implementation

- Added read-only `scripts/workflow/execution_preflight.py` and tests `tests/workflow/test_execution_preflight.py`; targeted tests passed **2/2**.
- Live scan of 536 tracked Markdown documents found 2 missing relative fixture links (`vault.canvas`, `attachments/file.png`), so the preflight correctly returned exit 1. These are documentation/fixture follow-ups, not suppressed failures.
- Report `.project-local/runs/execution-preflight-20260914.json` records interpreter, Git HEAD, link findings, and the private-state boundary.

### 2026-09-14 execution preflight fixture classification fix

- Preflight now separates intentional missing assets in synthetic fixture vaults from real broken project links.
- Re-run over 536 tracked Markdown documents: **exit 0**, `broken=0`, `expected_fixture_missing=2`; targeted preflight tests remain **2 passed**.
- The two expected fixture references remain visible in the receipt and are not silently discarded.

### 2026-09-14 preflight module environment check

- Preflight with `yaml`, `fastapi`, `pytest`, and `ruff` modules passed: all available under Python 3.13.14; Markdown broken links 0 and expected fixture missing 2.
- Receipt: `.project-local/runs/execution-preflight-modules-20260914.json`.

### 2026-09-14 configuration/entrypoint regression

- Config profiles, tool evidence, setup initialization, Core client, approved paths, and OCR configuration suites passed: **45 tests**, 1 platform-specific skip.
- Runtime configuration and entrypoint contracts remain consistent with the project-local output policy.

### 2026-09-14 · CLEAN02 metadata inventory refresh

- Command: `.project-local/runs/taskpack-paths-test-venv/Scripts/python.exe scripts/maintenance/inventory_project.py . --output .project-local/runs/inventory-20260914.json`
- Result: `status=partial`; 110,284 regular files / 11,523,900,070 logical bytes observed; 44 top-level groups; 11 reparse points skipped; 238 opaque/non-regular exclusions; 186 permission errors.
- Interpretation: this is a bounded metadata observation, not a complete volume-size claim. Permission errors are concentrated in ACL-denied pytest/runtime trees; no ACL changes or deletion were attempted. The receipt is project-local and preserves the exact limitation.

### 2026-09-14 · Repository path convention recheck

- Command: `.project-local/runs/taskpack-paths-test-venv/Scripts/python.exe scripts/check_path_conventions.py --measure --json --record .project-local/runs/path-conventions-20260914.json`
- Result: exit `0`; 1,994 tracked paths, all owned; unowned/ambiguous/denied-but-tracked all `0`; coverage `100%`.
- Scope: repository-tracked paths only. External model/tool/Green/资料库/ceshi roots were metadata-only references and were not enumerated or modified.

### 2026-09-14 · Output producer trace refresh

- Command: `.project-local/runs/taskpack-paths-test-venv/Scripts/python.exe scripts/maintenance/trace_output_producers.py . --output .project-local/runs/output-producers-20260914.json`
- Result: exit `0`; 1,051 static path candidates, 0 skipped files.
- Interpretation: candidates identify source/config references only; they do not prove runtime writes. Private agent state, process command lines, logs, and external roots remain opaque by policy.

### 2026-09-14 · Path/runtime regression rerun

- Command: `.project-local/runs/taskpack-paths-test-venv/Scripts/python.exe -m pytest tests/runtime-paths tests/maintenance/test_trace_output_producers.py tests/maintenance/test_inventory_project.py -q -p no:cacheprovider --basetemp=.project-local/runs/path-regression-20260914`
- Result: `44 passed`, `11 subtests passed`, `1 failed`; the sole failure is the existing Windows owned-process-tree cleanup test because managed `taskkill.exe` returned access denied. No product-path or file-routing assertion failed.
- Classification: `ENVIRONMENT_FAIL`; no process termination workaround or ACL change was attempted.

### 2026-09-14 · Runtime path and boundary contract regression

- Command: `.project-local/runs/taskpack-paths-test-venv/Scripts/python.exe -m pytest tests/test_project_output_routing_contract.py tests/test_axw_run205_env_fallback.py tests/test_axw_data404_paths.py tests/test_mcp_probe_paths.py tests/maintenance/test_check_vnext_workers_paths.py tests/test_evidence_commands.py -q -p no:cacheprovider --basetemp=.project-local/runs/boundary-regression-20260914`
- Result: `54 passed`, exit `0` (one existing pytest config warning about `cache_dir`).
- Coverage: project-local output routing, legacy env fallback rejection, data path boundary checks, MCP run-root paths, worker path guards, and evidence command path rules.

### 2026-09-14 · Capacity diagnostic contract regression

- Command: `.project-local/runs/taskpack-paths-test-venv/Scripts/python.exe -m pytest tests/maintenance/test_inventory_project.py -q -p no:cacheprovider --basetemp=.project-local/runs/capacity-tests-20260914`
- Result: `21 passed`, `2 subtests passed`, exit `0` (one existing pytest config warning).
- Coverage: explicit budget alarms, unknown/opaque group handling, scope mismatch rejection, no-deletion guarantee, and CLI exit precedence.

### 2026-09-14 · R5 package integrity recheck

- Command: `.project-local/runs/taskpack-paths-test-venv/Scripts/python.exe docs/authority/taskpack-0912-r5/verify_package.py --root docs/authority/taskpack-0912-r5`
- Result: `PASS`, exit `0`; 23 inherited tasks, 38 original scenarios, 18 additional slices (10 cleanup, 4 repository, 4 migration), 173 active files.
- Guard: verifier itself reports `product_tests_run=false`, `windows_cleanup_performed=false`, `current_head_checked=false`; package integrity is not product or release acceptance.

### 2026-09-14 · Modified Python lint cleanup

- Removed three unused imports introduced/retained in modified paths (`dataclass`, test `json`, unused ASR alias) without changing runtime behavior.
- Ruff F401 check: exit `0`; focused ASR and DeepTutor regression: `7 passed`, exit `0` (one existing pytest config warning).

### 2026-09-14 · Post-Ruff maintenance/runtime regression (correct run root)

- Command: `scripts/runtime/dev.py --run-id post-ruff-20260914 <managed-python> -m pytest tests/maintenance tests/runtime-paths -q -p no:cacheprovider`
- Result: `69 passed`, `11 subtests passed`, `1 failed`; all bulk fixture path tests pass once launched through the project dev runner. The sole failure remains the managed Windows `taskkill.exe` access-denied process-tree test.
- Ruff import cleanup therefore has no observed product regression in the covered suites.

### 2026-09-14 · Cross-language ownership/protocol gate

- Command: `.project-local/runs/taskpack-paths-test-venv/Scripts/python.exe scripts/check_language_boundaries.py --json`
- Result: exit `0`, `passed=true`, failures `0`.
- Scope: Rust database ownership, Python worker database isolation, desktop shell SQL isolation, and cross-language protocol literal agreement.

### 2026-09-14 · Worker reachability gate recheck

- Command: `.project-local/runs/taskpack-paths-test-venv/Scripts/python.exe scripts/check_worker_reachability.py --record docs/authority/taskpack-0910-r3/WORKER-REACHABILITY.json --json`
- Result: exit `0`, `passed=true`; 12 capability workers, 10 routed, 2 explicitly exempted with reasons (transcribe model path; video contract parameters).
- Note: the current R5 pack has no new reachability record; this check intentionally reuses the historical governed record and does not promote it to a fresh product/runtime audit.

### 2026-09-14 · Modified Python syntax gate

- Command: managed Python `-m py_compile` over 39 modified `.py` files.
- Result: exit `0`; all files compiled successfully. Exact generated `.pyc` files were removed immediately after the check; no source or runtime data was touched.

### 2026-09-14 · Authority/security boundary regression

- Command: `.project-local/runs/taskpack-paths-test-venv/Scripts/python.exe -m pytest tests/test_project_data_boundary.py tests/test_hardening.py tests/test_federation_router_security.py tests/test_axw_data404_paths.py tests/test_evidence_commands.py -q -p no:cacheprovider --basetemp=.project-local/runs/security-boundary-20260914`
- Result: `80 passed`, exit `0`; warnings only (pytest cache option, Starlette/httpx deprecation, optional newspaper NLP extra).
- Coverage: project data boundaries, runtime hardening, federation/router security, data path refusal, and evidence command safeguards.

### 2026-09-14 · Evidence index consistency recheck

- Command: `.project-local/runs/taskpack-paths-test-venv/Scripts/python.exe scripts/check_evidence_index.py --index docs/authority/taskpack-0910-r3/R14-EVIDENCE-INDEX.json --state docs/authority/taskpack-0910-r3/STATE.json --json`
- Result: exit `0`, `passed=true`; 17 slices, 81 tracked evidence entries, 3 receipt entries, 0 failures.
- Scope: governed 0910 historical evidence index; R5 has no replacement index, so this is consistency evidence only and does not close R5 independent audit.

### 2026-09-14 · Architecture guard recheck

- Command: `.project-local/runs/taskpack-paths-test-venv/Scripts/python.exe scripts/check_architecture.py --format json`
- Result: exit `0`; JSON violation list is empty.
- Scope: repository architecture guard only; no runtime, installer, or external-library claims.

### 2026-09-14 · Entrypoint/config binding regression

- Command: `.project-local/runs/taskpack-paths-test-venv/Scripts/python.exe -m pytest tests/test_doctor_windows.py tests/test_desktop_launch.py tests/test_config_profiles.py tests/test_desktop_staging.py tests/test_desktop_runtime.py -q -p no:cacheprovider --basetemp=.project-local/runs/entrypoint-regression-20260914`
- Result: `36 passed`, exit `0`; warnings only (pytest cache option, Starlette/httpx deprecation, optional newspaper NLP extra).
- Scope: Windows doctor, formal desktop launch/staging/runtime, and configuration profile bindings.

### 2026-09-14 · Core dependency preflight refresh

- Command: `.project-local/runs/taskpack-paths-test-venv/Scripts/python.exe scripts/launch/core_launch.py --check`
- Result: exit `0`, `dependencies_ok=true`; 9 required checks passed (Core binary, managed Python, text/PDF/OCR workers, PyMuPDF, Tesseract executable/data, Cargo wrapper).
- Runtime state: DeepTutor ports 8001/3782 and Ollama 11434 were not listening; this is an environment snapshot, not a failure of the dependency check.

### 2026-09-14 · Strict modified-Python lint gate

- Command: managed Python `ruff check --select E9,F` over all modified `.py` files.
- Result: exit `0`, no syntax, undefined-name, or import-failure diagnostics.

### 2026-09-14 · Evidence command inventory recheck

- Command: `.project-local/runs/taskpack-paths-test-venv/Scripts/python.exe scripts/check_evidence_commands.py --index docs/authority/taskpack-0910-r3/R14-EVIDENCE-INDEX.json --json`
- Result: exit `0`; 21 recorded commands classified as runnable; no commands executed (`--run` omitted), preserving read-only scope.
- Note: this checker emits its inventory as text in no-run mode; it does not claim command success or current R5 completion.

### 2026-09-14 · Report/receipt generation regression

- Command: `.project-local/runs/taskpack-paths-test-venv/Scripts/python.exe -m pytest tests/test_current_report_generator.py tests/test_golden_journey_receipt.py tests/runtime-paths/test_vnext_receipt.py tests/test_release_manifest.py -q -p no:cacheprovider --basetemp=.project-local/runs/report-regression-20260914`
- Result: `45 passed`, exit `0`; warnings only (known pytest cache option, Starlette/httpx deprecation, optional newspaper NLP extra).
- Scope: current report generation, Golden Journey receipts, vNext receipt semantics, and release manifest stale-claim protections.

### 2026-09-14 · Full Python regression snapshot

- Command: `scripts/runtime/dev.py --run-id full-regression-20260914 --full <managed-python> -m pytest -q -p no:cacheprovider`
- Result: `2749 passed`, `7 skipped`, `41 failed`, `135 subtests passed` in 216.94s.
- Triage: failures are environment/path-bound or pre-existing: 1 managed Windows `taskkill.exe` access-denied cleanup; multiple exchange/backup/workspace cases hit Windows MAX_PATH or ACL-denied historical pytest trees; candidate/process cases hit the same process-control restriction. The run did not produce evidence of a new import/lint regression; focused fresh-run suites pass. Full failure output is retained in the run stream, and no destructive workaround was applied.

### 2026-09-14 · Short-run-root confirmation for exchange/backup

- Command: `scripts/runtime/dev.py --run-id a <managed-python> -m pytest tests/test_axw094a_export.py tests/test_axw_data403_migrate.py tests/test_backup.py -q -p no:cacheprovider --tb=short`
- Result: `28 passed`, exit `0`.
- Interpretation: the corresponding failures in the long full run were Windows MAX_PATH/run-root length effects, not reproducible product failures. Keep run IDs short enough for Windows path limits during local regression; no product semantics were changed.

### 2026-09-14 · Short-run-root workspace regression

- Command: `scripts/runtime/dev.py --run-id b <managed-python> -m pytest tests/test_workspace_api.py tests/test_workspace_job_center.py tests/test_workspace_live_refresh_matrix.py tests/test_workspace_pdf_endpoint.py tests/test_workspace_pipeline_multiformat.py tests/test_workspace_research_consumer.py -q -p no:cacheprovider --tb=short`
- Result: `47 passed`, `2 skipped`, exit `0`.
- Interpretation: workspace import, archive, API, live refresh, PDF, multiformat pipeline, and research consumer paths pass when the project run root stays within Windows path limits.

### 2026-09-14 · Candidate verifier short-root regression

- Command: `scripts/runtime/dev.py --run-id c <managed-python> -m pytest tests/test_candidate_manifest.py -q -p no:cacheprovider --tb=short`
- Result: `32 passed`, `3 failed`; all failures are the bounded child reaping cases where `stop_owned_process` receives managed `taskkill.exe` access denied. No manifest/hash/readiness assertion failed.
- Classification: `ENVIRONMENT_FAIL`; no process-kill or privilege workaround attempted.

### 2026-09-14 · Current change binding receipt

- Receipt: `.project-local/runs/changed-files-binding-20260914.json`.
- Binds current HEAD `3d560253c0d61dc0baa0728eb3fc0a74c5b67e26` to 63 tracked modified files with working-tree SHA-256 values.
- Untracked files are explicitly excluded; no private state was read or hashed.

### 2026-09-14 · Execution preflight refresh

- Command: `.project-local/runs/taskpack-paths-test-venv/Scripts/python.exe scripts/workflow/execution_preflight.py --module yaml --module fastapi --module pytest --module ruff --json`
- Result: exit `0`, `passed=true`; Python `3.13.14` from the project-local managed interpreter; all four requested modules available; Markdown broken links `0`; expected fixture omissions `0`.
- Private-state flag remains closed; no credentials, agent state, or external roots were opened.

### 2026-09-14 · R5 baseline binding check

- Current HEAD: `3d560253c0d61dc0baa0728eb3fc0a74c5b67e26`; `R5-STATE.json` baseline SHA: `c06b234ca335b9cbb2c1fde270851e2390c36b89`; local main baseline: `1e9813ea2bd49f47d334ba6717c78d3e9feda6ce`.
- The mismatch is expected: `baseline_sha` is the frozen R5 comparison point, not a claim that the mutable worktree is unchanged. Current-change binding is provided separately by `.project-local/runs/changed-files-binding-20260914.json`; frozen task files were not rewritten.

### 2026-09-14 · High-coverage regression with path-safe run root

- Command: `scripts/runtime/dev.py --run-id d <managed-python> -m pytest -q -p no:cacheprovider --ignore=tests/runtime-paths/test_dev_paths.py`
- Result: `2767 passed`, `7 skipped`, `126 subtests passed`, `3 failed` in 219.09s.
- The only failures are candidate timeout child-reaping cases, all blocked by managed `taskkill.exe` access denial. This excludes the known process-tree test itself; all other Python tests passed under a short run root.

### 2026-09-14 · Verification matrix handoff

- Added `docs/current/R5-VERIFICATION-SUMMARY-20260914.md`, a source-bound matrix separating PASS, PARTIAL, structural-only, environment failures, and not-executed R5 layers.
- The matrix intentionally excludes private state and external libraries and does not change frozen task definitions.

### 2026-09-14 · State and taskpack JSON parse gate

- Parsed `docs/current/R5-STATE.json`, R5 `TASKS.json`, and `REMAINING-WORK.json` with the managed Python interpreter.
- Result: all 3 files parsed successfully; exit `0`. No taskpack file was modified.

### 2026-09-14 · Receipt JSON integrity repair

- Batch-parsed 8 current project-local receipts; found a trailing literal `\\n` corruption in `changed-files-binding-20260914.json` caused by shell quoting.
- Removed only the two-byte literal suffix and revalidated all 8 receipts parse successfully. No data fields or source files changed.


## 2026-09-15 首次可用断点修复 checkpoint

基线 `0dd8ff37b670ae98fac4be35720194434e82191e`。沿 X00/X01/X03/X13 完成探针误报/虚构学习事件移除、持久TEST启动准备、Linux样本路径及最终写入越界修复；修正lint历史checkout、legacy workspace归属和过期规则入口。详见 [本次修复记录](R5-FIRST-USE-REPAIR-20260915.md)。

Linux定向验证：Core客户端/启动17项、样本生成器11项、目录/CI分类/真实文本和批量worker79项及47个子测试通过。路径变更已定向只读复核。架构、语言边界、目录与命名检查通过，R5冻结包校验通过。未执行Rust/C#构建、WindowsGUI、远端CI、发布、Green或真实四库迁移，用户闭环与Q00/Q01保持未完成。回滚使用本次commit的revert，不删除TEST库。

## 2026-09-15 增量执行记录

- R13 候选层：从当前 Debug Core 生成 `archeaxis-core-42ea8237c929-debug-build` 目录/ZIP；候选清单重哈希通过，`verify_candidate.py --run` 在端口 60651 启动并停止成功。该候选明确不含安装器、卸载器、签名、Python runtime、workers 或源资料。
- R15 格式层：格式矩阵合同、文本/图像、媒体、OCR、工作区多格式及 worker 路由定向测试 `75 passed, 1 skipped, 2 warnings`。这不是 16 格式全链路或真实 Vault/Green 验收。
- 规范层：`check_repository_conventions.py --source worktree`、路径归属检查和 `execution_preflight.py . --json` 均通过；当前 HEAD 以 Git 实际读数为准。DeepTutor 桥接的 4 个 SQLite 测试失败仍归类 `ENVIRONMENT_FAIL`，源于 pytest 临时目录 ACL，未修改权限或绕过门禁。
- R13 签名审计：当前 `.github/workflows/release.yml` 未发现 `signtool`、Authenticode 或其他代码签名步骤；NSIS/资产哈希校验不能替代签名。签名状态明确为 `NOT_CONFIGURED`，不将候选包或 Release workflow 视为已签名交付。
- 2026-09-15 签名资源复核：在共享 `OS External Configuration/10-toolchains` 与其上层目录未发现 `signtool.exe`，仓库配置也未发现证书、thumbprint 或签名命令；未读取任何私钥/凭据。R13 签名状态保持 `BLOCKED_RESOURCE`。
- 发行与源根合同定向回归扩大为 `89 passed, 2 warnings`，退出码 0；仓库规范检查 PASS。warnings 为外部依赖弃用/NLP 可选包提示，不改变结果。
- R10 DeepTutor Web 实测：固定 `1.5.17` 解释器、Node 和 `server.js` 文件均存在；项目启动器在 45 秒等待内收到子进程退出码 1，未形成 READY 回执。直接调用上游 launcher 在 20 秒观察窗口内持续运行但未证明前端就绪。该运行在项目隔离 runtime home 生成约 870 个 `.next`/Web 文件，显示上游会复制 Web 产物；与启动器注释中的“不复制 Web bundle”不一致，已标为 `PARTIAL / INTEGRATION_GAP`，未提升 R10。
- R10 follow-up diagnosis: the failed launch passed a relative `runtime_home` to a child whose working directory was already that directory. DeepTutor resolved the path twice and raised Windows `WinError 206` while creating its directories. `scripts/launch/deeptutor_web.py` now resolves `runtime_home` to an absolute path before spawning; the regression covers both child `cwd` and launcher argument (`tests/test_deeptutor_web_launch.py`: 5 passed). A live restart/readiness check remains required; R10 stays `PARTIAL / INTEGRATION_GAP`.
- R10 live retry after the fix: with the pinned external Python/Node/server and project-local runtime `r10-live-retry-20260915`, `http://127.0.0.1:13822` returned HTTP 200 and `deeptutor-web-launch.json` recorded `READY`. The wrapper was then intentionally terminated with its own process tree, so its final process exit code is not a readiness failure. This proves startup/readiness for the wrapper path; desktop default mounting, session recovery, and full host acceptance remain open.
- 2026-09-15 CLEAN03 producer-trace refresh: the read-only structural tracer completed with exit 0 and wrote `.project-local/runs/r5-producer-trace-20260915/producer-trace.json` (1,076 candidate rows, 0 skipped). These are source-token candidates only; process/log/runtime confirmation and external/shared ownership remain separate evidence requirements.
- 2026-09-15 routing regression refresh: output-routing, producer-trace and inventory maintenance suites passed (`37 passed, 2 subtests`, project CI interpreter). No private state or external roots were opened.
- 2026-09-15 desktop supervisor live smoke: after building the Avalonia project with the repository `Directory.Build.props` output root, `dotnet run --no-build -- --smoke` completed with exit 0 (`SMOKE OK: owned core handshake ok: archeaxis-api 0.1.0-outline`). The real `CoreSupervisor.Tests` launcher, with explicit project-local run root, Core binary and CI Python, also completed exit 0 with all lifecycle/identity/worker/persistence checks passing. This verifies the host/Core/Python lifecycle path, not GUI interaction or installer acceptance.
- 2026-09-15 Avalonia warning cleanup: replaced the obsolete `TextBox.Watermark` property with `PlaceholderText` in `MainWindow.axaml`. Rebuild remains exit 0 with only the external NuGet vulnerability-feed warning; desktop smoke remains exit 0.
- 2026-09-15 R13 candidate recheck: release architecture verifier passed; the existing Core candidate ZIP was expanded into a project-local run and `verify_candidate.py --run --json` returned `ok: true` (2 files, no problems, database created, readiness port assigned, process stopped, token not printed). This validates the Core candidate only; it remains separate from a signed desktop installer.
- 2026-09-15 R13 release-contract regression: release architecture, manifest and completion-audit tests passed (`36 passed, 2 warnings`). Warnings are dependency deprecation/NLP notices; no installer or signing claim was promoted.
- 2026-09-15 first-use integration regression: desktop runtime/launch/staging, Core supervisor contract, import, HL01, learning loop/security, crash recovery and public closed-loop suites passed (`54 passed, 2 warnings`). This strengthens local contract evidence but does not replace visible GUI and clean-machine acceptance.
- 2026-09-15 R15 format regression: multi-format workspace pipeline, adapter, DOCX, media, ingestion and Obsidian suites passed (`132 passed, 1 skipped, 3 warnings`, 30.93s). The skipped case and fixture coverage mean the FORMAT-COVERAGE matrix remains unqualified for full end-to-end completion.
- 2026-09-15 CI classifier repair: the newly tracked `workspace/intake/**` monitoring task map was not covered by the risk profile and caused the full regression classifier failure. Added it to the authority-document class (static gate); classifier suite now passes `31` tests.
- 2026-09-15 full Python regression: managed CI interpreter run completed `2,807 passed, 9 skipped, 135 subtests, 8 failures`. One classifier failure was fixed by the preceding risk-profile change. The three backup failures are Windows long-path failures under the managed pytest run root; four DeepTutor bridge failures are the known ACL-denied SQLite temp-directory environment gate. No product-pass claim is made for those remaining failures.
- 2026-09-15 monitoring-task evidence regression: workbook structural audit, research package, governance lifecycle, approval contract and boundary suites passed (`25 passed`). Formula evaluation remains intentionally out of scope; the original workbook was not modified.
- 2026-09-15 state alignment: X03 gap text now reflects evidence for desktop question rendering/review submission and narrows the remaining gap to DeepTutor default mount, complete session/attachment recovery, visible-window interaction and restart readback. Status remains `PARTIAL_NEEDS_WORK`; taskpack path/integrity/completion-audit checks passed (`15 passed`).
- 2026-09-15 audit preflight: the frozen R5 `verify_package.py` returned `PASS` (23 tasks, 173 active files); evidence-index/check-evidence helpers correctly reported that R5 has no legacy evidence-index format and require its own validator. No Q00/Q01 self-signing performed.
- 2026-09-15 monitoring source recheck: the three user-supplied Desktop source files and the referenced workbook match the monitoring map's recorded SHA-256 values exactly (`d8249b7a…`, `67dfe3fb…`, `45605b9b…`, `42528b02…`). This validates source identity only; it does not promote the associated blocked tracks.
- 2026-09-15 desktop WinExe window probe: the compiled formal executable stayed alive for 5 seconds with a native window handle/title (`ArcheAxis.Desktop.exe`) and was then stopped as the test-owned process. The unavailable sky UI service prevented control-tree or interaction verification; this is process/window existence evidence only.
- 2026-09-15 user screenshot confirms the framework-dependent EXE shows “You must install .NET Desktop Runtime” on a machine without the desktop runtime. A self-contained publish probe was started but stopped at the restore boundary after owner clarification: no Green directory was changed, no new release version was integrated, and the failure (`NETSDK1047`, missing `net10.0/win-x64` assets) remains an R13 packaging gap. The next action is Green-compatible integration review, not a parallel distribution route.
- 2026-09-15 resource-boundary recheck after owner correction: the five indexed roots (`Model library`, `OS External Configuration`, Green application, Green material library, and `ceshi`) all exist as ordinary directories with no reparse point. No contents were enumerated or modified; Green remains the integration target and `ceshi` remains the only approved test corpus.
- 2026-09-15 resource drift guard: added `scripts/maintenance/check_resource_boundaries.py` with `integration` → `green_application` and `test` → `project_test_corpus` fail-closed purpose routing. It checks all five indexed roots for exact derived paths, directory type and reparse points without enumerating contents. Regression: `2 passed`; Ruff passed.
- 2026-09-15 resource drift guard live check: `--purpose integration` resolves only `D:\All projects\ArcheAxis.Knowledge.Green-x64`; `--purpose test` resolves only `D:\All projects\ceshi`; both return exit 0 with no reparse points. Green was not launched or modified.
- 2026-09-15 drift guard integration: `scripts/launch/desktop_launch.py` now runs the indexed `test` resource preflight before allocating default desktop test artifacts; custom fixture paths remain isolated. Desktop launcher regression passed `5` tests and Ruff passed.
- 2026-09-15 launcher routing recheck: explicit project-local Desktop/Core artifacts were prepared successfully with `--fresh-workspace` (exit 0, isolated database/profile receipt). A dev.py-scoped rebuild requires a NuGet restore that remained unresolved after 60 seconds and was stopped; no external or Green state changed. The default launcher correctly refuses when its worktree-specific build artifact is absent.
- 2026-09-15 index lock hardening: the resource preflight now also verifies that `docs/SHARED_RESOURCE_PATH_INDEX.md` contains all five registered IDs and canonical D: paths; missing or drifted index entries fail closed. Real `test` preflight, unit tests (`2 passed`) and Ruff passed.
- 2026-09-15 index-lock regression: simulated a rewritten resource index and confirmed the preflight rejects it; resource-boundary tests now pass `3`, Ruff remains `PASS`.
- 2026-09-15 E-drive boundary regression: added an explicit test that a project root on `E:` is rejected before any resource inspection; resource-boundary suite now passes `4`, Ruff remains `PASS`.
- 2026-09-15 low-quota monitoring: added `scripts/maintenance/prepare_low_quota_handoff.py` and policy `docs/current/LOW-QUOTA-HANDOFF-POLICY.md`. With live account input 11%, report state is `MONITORING`; it records branch/HEAD/upstream gap and excludes private/untracked state. Targeted tests: `4 passed`. It does not stage, commit, push, or claim double-end consistency.

- 2026-09-16 path normalization: legacy `verified-knowledge/ceshi-2026-08-18/scripts` receipts previously targeted `.hermes/task-runtime`; both scripts now derive the repository root and write only `.project-local/runs/legacy-ceshi/`. The approved `D:\All projects\ceshi` corpus remains read-only input. Python compile and repository convention checks passed.

- 2026-09-16 architecture gate repair: `check_architecture.py` flagged the resource-boundary guard for embedding an absolute D: path in runtime code. The guard now derives the canonical index path from the checkout parent and still fails closed on index drift. Resource-boundary tests `4 passed`; architecture and repository convention gates passed.

- 2026-09-16 model-library path normalization: vNext media transcription worker no longer embeds a machine-specific absolute model path. It derives the shared `Model library` root from the checkout parent and honors `ARCHEAXIS_ASR_MODEL_DIR`; worker routing/media tests `16 passed`, architecture and repository convention gates passed.

- 2026-09-16 full boundary recheck at HEAD `a5f856d9`: path convention coverage `2034/2034`, unowned `0`, ambiguous `0`; integration target resolves only Green, test target only `D:\All projects\ceshi`, all five indexed roots are ordinary non-reparse directories. Execution preflight passed (`547` Markdown links checked, `0` broken, `private_state_opened=false`).

- 2026-09-16 regression gate: CI classifier, resource-boundary, and low-quota handoff suites passed (`39 passed`).

- 2026-09-16 low-quota privacy hardening: handoff reports now capture tracked status only; untracked history/user paths are not enumerated into a report that may be uploaded. Threshold simulation at 2% returns `UPLOAD_REQUIRED` with automatic push disabled; targeted tests `4 passed`.

- 2026-09-16 model path regression: added `tests/workers/test_transcribe_model_path.py` covering checkout-parent derivation and explicit `ARCHEAXIS_ASR_MODEL_DIR` override. Worker/reachability tests `9 passed`; repository convention gate passed.

- 2026-09-16 delivery attempt: `git push origin codex/full-loop-0906` was rejected before process execution by the active automatic approval policy (`AskForApproval=Never`, approval required). No alternate push route or policy bypass was attempted; remote SHA remains unverified.

- 2026-09-16 path/worker regression: runtime-paths, resource-boundary, low-quota, transcription model-path, worker reachability and media-route suites passed `45 passed`, `9 subtests`; one existing pytest `cache_dir` option warning remains environment/config-only.

- 2026-09-16 low-quota handoff completeness: threshold report now includes tracked verification summary, R5 handoff, cleanup manifest and low-quota policy alongside execution/state/index files. At simulated 2% all available sources were listed; targeted tests `4 passed`.

- 2026-09-16 lint cleanup: removed an obsolete UTF-8 coding header from the media worker and corrected a Ruff SIM300 assertion style in its model-path regression test. Ruff, Python compile, targeted tests (`6 passed`) and `git diff --check` passed.

- 2026-09-16 R5 gate recheck: evidence index passed (17 slices, 81 tracked evidence, 3 receipts); format matrix parsed 16 rows with 0 complete / 14 partial / 2 custody-only; worker reachability passed (12 workers, 10 routed, 2 exempted); architecture check passed.

- 2026-09-16 active-source boundary gate: added `tests/maintenance/test_active_output_boundaries.py` to reject machine-specific D: roots and `.hermes/task-runtime` output strings in active code. Gate passed `1`, Ruff passed.

- 2026-09-16 low-quota threshold simulation: with supplied remaining `2%`, report correctly returned `UPLOAD_REQUIRED`, listed 9 safe tracked handoff sources and excluded `.codex/`, `.zcode/`, `.hermes/` plus untracked user/history assets. Current branch divergence is 80 commits; no upload was performed by simulation.

- 2026-09-16 fresh path measurement at current HEAD: `check_path_conventions.py --measure` recorded `.project-local/runs/path-conventions-current-20260916.json`; 2,036 tracked paths, 2,036 owned, 0 unowned/ambiguous/denied, coverage 100%.

- 2026-09-16 release-layer recheck: `verify_release_architecture.py` passed for Avalonia → Rust Core → Python workers; candidate verification returned `ok=true`, 2 files, 0 problems, retaining `debug-build` and source SHA labels. This is candidate/structure evidence only, not installed-release proof.

- 2026-09-16 fresh read-only inventory: `.project-local/runs/inventory-current-20260916.json` reports 13,123,287,548 logical bytes observed in `.project-local` (92,910 files), 229 permission errors, 7 reparse points, 348 exclusions; status `partial`. Volume free-space delta was 0 and project-attributed physical usage remains unknown. No cleanup or ACL change was performed.

- 2026-09-16 shared-resource index recheck: `docs/SHARED_RESOURCE_PATH_INDEX.md` remains the sole path authority for five resources; metadata preflight confirms all five roots are directories with no reparse points. No library contents, Green data, test corpus contents, or E: drive were accessed.

- 2026-09-16 low-quota upload scope: threshold reports now include the exact Git commit range (`origin/codex/full-loop-0906..HEAD`) and ahead count, so the future upload can be reconciled against both refs. Targeted tests `4 passed`.

- 2026-09-16 shared-model compatibility regression: ASR model resolution, legacy ASR adapter, media extraction and worker model-path suites passed `10 passed`; only existing cache-dir and optional NLTK warnings remained.

- 2026-09-16 resource-to-pipeline regression: source preflight, audio fallback, media route and worker reachability suites passed `20 passed`; the only warning was the existing pytest cache-dir option. Test entries continue to reject real Green material roots and use project-local outputs.

- 2026-09-16 Rust workspace probe: shared MSVC environment was successfully initialized and `cargo test --workspace --offline` compiled the workspace, but one API test panicked because the direct wrapper lacked the required `dev.py` run-root contract (`run through dev.py`). Exit 1 is recorded as an environment/entrypoint failure, not a product-pass claim; no source change.
- 2026-09-16 定向宿主/桌面回归：.venv\Scripts\python.exe -m pytest tests/test_deeptutor_web_launch.py tests/test_host_journey_panel.py tests/test_desktop_runtime.py tests/test_desktop_launch.py tests/test_workspace_crash_recovery.py -q，30 passed，2 warnings，exit 0。该证据覆盖启动合同、宿主面板、桌面运行时与崩溃恢复的结构/模拟回归；未证明 Green 真实目录集成、干净机安装或签名验收，R10/R13 状态不提升。
- 2026-09-16 资源边界/输出路由回归：.venv\Scripts\python.exe -m pytest tests/maintenance/test_check_resource_boundaries.py tests/maintenance/test_active_output_boundaries.py tests/maintenance/test_source_preflight.py -q，9 passed，exit 0；integration/test purpose 元数据检查均指向索引的 Green/ceshi 角色，活动源码未发现硬编码机器根或旧 .hermes/task-runtime 输出。该门禁不读取外置库内容，不证明 Green 运行时安装验收。
- 2026-09-16 R5 权威机械门禁复核：`verify_package.py` PASS（23 tasks/173 active files）；证据索引 PASS（17 slices/81 tracked/3 receipts）；格式矩阵 PASS（16 rows，0 complete/14 partial/2 custody-only）；worker reachability PASS（12 workers，10 routed/2 exempted）。这些结果仅证明包与继承证据结构完整，不提升 R5 产品完成度或独立审计状态。
- 2026-09-16 桌面烟雾路径收口：`apps/ArcheAxis.Desktop/Program.cs` 不再回退到系统 TEMP，`--smoke` 缺少显式数据库路径即返回错误，避免产生未管理的第二数据库；路径路由合同测试 14 passed。dotnet build ... --no-restore 未执行成功，当前 shell 未发现 dotnet，因此编译验证为 ENVIRONMENT_FAIL。
- 2026-09-16 桌面编译复核：调用已登记共享 SDK D:\All projects\OS External Configuration\10-toolchains\dotnet\dotnet.exe build apps/ArcheAxis.Desktop/ArcheAxis.Desktop.csproj --no-restore --configuration Debug，exit 0，产物路由至 .project-local/build/dotnet。该编译不等于 Green 真实目录安装/签名/干净机验收。
- 2026-09-16 Green 兼容方向桌面烟雾复测：设置 DOTNET_ROOT_X64/DOTNET_ROOT 指向登记共享 SDK，并显式设置当前项目 Core ARCHAXIS_CORE_BIN 后运行已编译 EXE --smoke .project-local/runs/desktop-smoke-20260916/workspace.sqlite，进程 exit 0，项目内生成 SQLite/WAL/锁文件。该次未获得标准 SMOKE OK 文本回执，因此只记为 PARTIAL_RUNTIME_SIGNAL，不提升为完整 GUI/Green 安装验收。
- 2026-09-16 R13 Green 兼容自包含候选：共享 SDK restore（`--runtime win-x64 --ignore-failed-sources`）exit 0；随后 `dotnet publish --configuration Release --runtime win-x64 --self-contained true --no-restore` 输出至 `.project-local/build/dotnet/archeaxis-green-compatible-selfcontained`，exit 0。未设置 `DOTNET_ROOT`，显式 Core 路径运行候选 smoke 返回进程 exit 0，并在项目内生成 SQLite/WAL/锁文件。候选未复制、覆盖或启动既有 Green，未包含签名/安装器，因此仍不是正式发布资格。
- 2026-09-16 R13 Release 默认配置收口：`ArcheAxis.Desktop.csproj` 的 Release 配置固定 `RuntimeIdentifier=win-x64`、`SelfContained=true`；共享 SDK restore/build 均 exit 0，输出位于 `.project-local/build/dotnet/ArcheAxis.Desktop/bin/Release/net10.0/win-x64`。未设置 `DOTNET_ROOT` 运行 Release smoke 并显式绑定项目 Core，进程 exit 0；这只证明自包含启动路径，不证明签名、安装器或 Green 真实目录验收。
- 2026-09-16 Green 候选组装器：新增 `scripts/release/assemble_green_candidate.py`，仅允许输出到项目 `.project-local`，将自包含桌面目录与 Core 放入同一候选并生成逐文件 SHA-256 清单与 ZIP；`tests/test_green_candidate_assembly.py` 通过 `2 passed`，包含深路径 Windows 兼容和越界输出拒绝。该候选组装器不触碰既有 Green、不含签名或卸载器。
- 2026-09-16 R13 候选实际组装：使用 Release 自包含桌面目录与当前 Core 生成 `.project-local/build/green-candidates/ArcheAxis.Knowledge.Green-vr5-x64.zip`，组装命令 exit 0；清单 229 个文件、ZIP 230 个成员（含清单），Core/桌面入口均存在，逐文件 SHA-256 复核 `hash_mismatches=0`。这仍是项目内审计候选，不是已发布或已覆盖的 Green 软件。
- 2026-09-16 Green 组装器扩展：支持显式传入项目内 `runtime` 目录并纳入同一候选清单；未提供时保持 Core+桌面最小包，不自动读取共享模型库、外置工具链或真实资料库。测试 `2 passed`，Ruff 通过。
- 2026-09-16 R13 runtime 前置复核：项目 `.project-local/build` 当前没有可复用的 `venv` 或 `rt/runtime`（仅有现有构建、候选和测试目录），因此未强行把开发环境伪装成 Green runtime；完整 workers/runtime 仍列为待准备资源。
- 2026-09-16 Green 候选验证器：新增 `scripts/release/verify_green_candidate.py`，只读核对候选清单、桌面自包含运行时文件、Core 入口和逐文件 SHA-256；完整候选与篡改文件测试 `4 passed`，对实际 `ArcheAxis.Knowledge.Green-vr5-x64` 候选返回 `ok=true`、229 文件、0 问题。
- 2026-09-16 Green 组装输入边界加固：组装器现在拒绝输入目录、文件及递归内容中的符号链接/Windows 重解析点，避免通过 junction 引入外置库或用户目录；回归 `4 passed, 1 skipped`（跳过项为当前环境不支持创建 symlink），Ruff 通过。
- 2026-09-16 加固后真实候选复核：重新组装 Release 桌面 + Core 为 `ArcheAxis.Knowledge.Green-vr5guarded-x64`，组装 exit 0；`verify_green_candidate.py` 返回 `ok=true`、229 文件、0 问题。输出保持项目 `.project-local`，未触碰既有 Green。
- 2026-09-16 交付复核：按用户既有上传授权执行 `git push` 尝试，但进程在启动前被当前策略拒绝：`approval required by policy, but AskForApproval is set to Never`。未绕过审批；本地与远端 SHA 仍分别报告。
- 2026-09-16 Green 验证范围标识：验证器现在返回 `scope=desktop-core-only` 或 `desktop-core-runtime` 及 `runtime_included`，避免把未含 workers/runtime 的最小候选误读为完整 Green；验证器回归 `2 passed`，Ruff 通过。
- 2026-09-16 完整 Green 审计门：`verify_green_candidate.py` 新增 `--require-runtime`/`require_runtime=True`，没有 runtime 时明确失败；验证器回归 `3 passed`，Ruff 通过。
- 2026-09-16 完整 Green 门实测：对 `ArcheAxis.Knowledge.Green-vr5guarded-x64` 执行 `verify_green_candidate.py --require-runtime` 返回 `ok=false`、`scope=desktop-core-only`、`runtime_included=false`，问题为 `runtime directory is required for a complete Green candidate`；该失败符合预期，保持 R13 未闭合状态。
- 2026-09-16 临时桌面入口误启动复核：`.project-local/runs/green-candidate-20260916/desktop/ArcheAxis.Desktop.exe` 的运行提示对应框架依赖/非完整 Green 目录，不能作为绿色版验收；Release 自包含目录 `build/dotnet/archeaxis-green-compatible-selfcontained` 在显式 `ARCHAXIS_CORE_BIN` 后执行 `--smoke` 返回 exit 0，并生成项目内 SQLite/WAL/锁文件。既有 `D:\All projects\ArcheAxis.Knowledge.Green-x64` 未修改；R13 仍未完成签名、安装器、卸载器及干净机验收。
- 2026-09-16 R13 Green runtime 候选补齐：只读使用既有 `D:\All projects\ArcheAxis.Knowledge.Green-x64\runtime\python`（21,162 文件、654,538,073 bytes）复制到项目 `.project-local` 候选；既有 Green 未修改。`ArcheAxis.Knowledge.Green-vr5full-x64` 组装含自包含桌面、Rust Core 与 Python runtime，清单 21,387 文件，`verify_green_candidate.py ... --require-runtime` 返回 `ok=true`、`scope=desktop-core-runtime`、`runtime_included=true`、`problems=[]`。该证据仍不等于安装器、签名、卸载器或干净机验收。
- 2026-09-16 Green full candidate runtime smoke：从 `ArcheAxis.Knowledge.Green-vr5full-x64\desktop\ArcheAxis.Desktop.exe` 以位置参数传入项目内数据库并绑定同候选 Core，输出 `SMOKE OK: owned core handshake ok: archeaxis-api 0.1.0-outline`，进程 exit 0；SQLite/WAL/锁文件均位于 `.project-local/runs/green-candidate-20260916`。
- 2026-09-16 R13 候选启动入口与长路径修复：`assemble_green_candidate.py` 现在在候选根生成无终端的 `启动绿色候选.vbs`，自动注入候选 Core 与项目内 data 根，避免直接双击框架依赖桌面 exe；候选重建删除使用逐文件 extended-path 清理，适配 Windows 深路径。定向测试 `tests/test_green_candidate_assembly.py` 为 `2 passed, 1 skipped`；实际 `r5full` 候选清单 `21,388` 文件、ZIP `312,085,713` bytes，`--require-runtime` 返回 `ok=true`、0 问题。
- 2026-09-16 项目内候选瘦身：盘点 `.project-local/build/green-candidates` 后仅保留可重建且已验证的 `ArcheAxis.Knowledge.Green-vr5full-x64`；删除本轮生成的旧 `vr5`/`vr5guarded` 候选目录及 ZIP，未触碰外置 Green、真实资料库、测试资料库或历史证据。删除后候选目录逻辑占用约 1,193,915,673 bytes；工作树未知历史未跟踪项仍全部保留。
- 2026-09-16 规范化门禁复核：项目 `.venv\\Scripts\\python.exe -m pytest tests/test_project_output_routing_contract.py tests/maintenance/test_check_resource_boundaries.py tests/maintenance/test_active_output_boundaries.py tests/test_desktop_launch.py -q`，`25 passed`，exit 0。覆盖活动输出路由、五个外置资源边界、旧 `.hermes` 输出拒绝及桌面启动器合同；未读取 E: 或外置库内容，未提升安装/云端验收状态。
- 2026-09-16 项目运行缓存瘦身：删除旧测试虚拟环境 `.project-local/runs/taskpack-paths-test-venv`（盘点约 778 MB、可由锁定依赖重建），删除后精确路径不存在；当前 Green 候选、构建产物和审计证据均保留。
- 2026-09-16 完整 Green 验证门收紧：`verify_green_candidate.py` 将候选根无终端启动器 `启动绿色候选.vbs` 列为必需且纳入哈希校验；回归 `5 passed, 1 skipped`。现有 `ArcheAxis.Knowledge.Green-vr5full-x64` 重新验证 `ok=true`、`desktop-core-runtime`、21,388 文件、0 问题。
- 2026-09-16 R15 格式路由定向回归：`.venv\\Scripts\\python.exe -m pytest tests/test_format_matrix.py tests/test_text_format_facts.py tests/test_worker_archive_route.py tests/test_worker_caption_route.py tests/test_worker_media_route.py tests/test_worker_pdf_native.py -q`，`56 passed`，exit 0。覆盖矩阵拒绝规则、文本/归档/字幕/媒体/PDF 路由与失败边界；格式矩阵仍按真实端到端证据保持 0 complete/14 partial/2 custody-only，未虚升状态。
- 2026-09-16 发布架构门禁复核：`verify_release_architecture.py --root . --workflow .github/workflows/release.yml` exit 0，确认工作流识别 Avalonia → Rust Core → Python workers；但静态复核仍发现实际 release candidate 构建段调用 legacy `tauri.cmd build`，该门禁只证明链路被标注，不能证明正式发行已切换到 Avalonia。R13 发布流水线迁移仍开放。
- 2026-09-16 CI desktop-vnext smoke 路径修复：`.github/workflows/ci.yml` 现在为 Avalonia supervisor smoke 显式创建 `.project-local/task-runtime/desktop-vnext/smoke.sqlite` 并以位置参数传入，符合桌面不回退 TEMP 的新合同；输出/架构/CI 门禁回归 `91 passed`，exit 0。该修复只更新 CI 路由，未宣称云端已运行。
- 2026-09-16 CI Green 候选接线：新增独立 `green-candidate-vnext` Windows job，使用 .NET 10 self-contained win-x64 publish、Rust Core build、项目组装器与验证器，并上传 `green-candidate-vnext` artifact；不替换现有 legacy Tauri release job。YAML 解析与架构/路由门禁回归 `68 passed`，exit 0；云端 job 尚未运行，不能据此宣称 CI/发布通过。
- 2026-09-16 CI Green candidate Core 路径修复：`green-candidate-vnext` job 现在读取 `CARGO_TARGET_DIR`（无值时回退 `target`），在组装前显式检查 `archeaxis-api.exe` 存在，避免 dev.py 路由后的云端路径错位；YAML 解析与 CI/输出路由回归 `46 passed`，exit 0。
- 2026-09-16 CI Green 候选完整 runtime 接线：`green-candidate-vnext` job 增加 Python 3.12/uv 锁定环境与 `desktop.scripts.prepare_bundle`，将 `.project-local/rt/runtime/python` 纳入候选，并启用 `verify_green_candidate.py --require-runtime`；YAML 解析与 CI/输出路由回归 `46 passed`，exit 0。云端执行尚未发生，仍需真实 job 收据。
- 2026-09-16 正式发布门禁接线：`.github/workflows/release.yml` 在锁定 CI 收据后下载同一 run 的 `green-candidate-vnext`，展开并执行 `verify_green_candidate.py --require-runtime`；缺少完整 Avalonia Green 候选会 fail-closed。YAML 解析与架构/路由回归 `68 passed`，exit 0；尚未运行真实 tag release，旧 Tauri 资产仍保留为历史兼容层。
- 2026-09-16 发布合同回归：`tests/test_release_architecture.py tests/test_release_identity_contract.py tests/test_release_manifest.py tests/test_product_version_truth_contract.py`，`42 passed`、2 既有依赖警告、exit 0；验证新增 exact-SHA Green 门未破坏版本/身份/清单合同，未执行真实发布。
- 2026-09-16 Green 完整候选 ZIP 交付校验：`ArcheAxis.Knowledge.Green-vr5full-x64.zip` 大小 `312,085,713` bytes，SHA-256 `c49adb90e9b979742f7314a4ee013a19b3b1f0bca087fe34a6152ec40c1e1a21`；ZIP 内启动器、Avalonia 桌面、Rust Core 均存在，runtime 条目 21,136 个。该哈希绑定项目内候选工件，未上传或安装。
- 2026-09-16 额度交接预演：以账户实测剩余约 10% 调用 `prepare_low_quota_handoff.py --remaining-percent 10`，exit 0，状态 `MONITORING`；绑定 HEAD `291a9859`、upstream `origin/codex/full-loop-0906`、ahead `126` 与精确上传范围，自动上传保持 false。输出位于 `.project-local/runs/quota-monitor-20260916`，私有目录和未知历史资产被排除。
- 2026-09-16 CI Green job 本地模拟：`prepare_bundle` 已复制项目内 Python 解释器并开始依赖 staging，但在 30 秒观察窗口内未完成，随后重入被正确拒绝为 destination 已存在；该未完成 run 根已按精确路径删除并验证不存在。未将此模拟计为通过，也未重复下载或触碰外置库。
- 2026-09-16 发布架构防漂移门：`verify_release_architecture.py` 现在要求 release workflow 同时消费 `green-candidate-vnext` 并使用 `verify_green_candidate.py --require-runtime`；测试 fixture 已同步更新。发布架构/身份/清单回归 `39 passed`、2 既有警告，实际 workflow 门禁 PASS。
- 2026-09-16 远端引用刷新：`git fetch origin` exit 0；当前 HEAD `2817983cf86aef1af424afce987a4a813bf71d97`，`origin/codex/full-loop-0906` `38d605090e88940cd2c57217ec1be6319e565901`，`origin/main` `1e9813ea2bd49f47d334ba6717c78d3e9feda6ce`，本地领先分支 `129` 个提交。未执行 push；未知未跟踪历史目录仍保留。
- 2026-09-16 Green 组装器长路径回归修复：二次组装测试首次复现递归文件超过 Windows 路径限制时 `FileNotFoundError`；现对每个递归文件/目录逐项应用 extended-length 路径。`tests/test_green_candidate_assembly.py` `2 passed, 1 skipped`；现有完整候选 `--require-runtime` 仍为 `ok=true`、21,388 文件、0 问题。
- 2026-09-16 额度交接预览刷新：以实测剩余约 10% 重新生成 `handoff-latest.json`，exit 0；绑定最新 HEAD `22eef3ae`、ahead `131`、精确上传范围，状态仍 `MONITORING`、`upload.required=false`。
- 2026-09-16 Release 桌面重建复核：调用登记共享 SDK `10-toolchains/dotnet/dotnet.exe build apps/ArcheAxis.Desktop/ArcheAxis.Desktop.csproj --configuration Release --runtime win-x64 --no-restore`，0 警告/0 错误、exit 0。随后从 `.project-local/build/dotnet/.../win-x64/ArcheAxis.Desktop.exe` 绑定项目 Core 与 `.project-local/runs/release-smoke-20260916/workspace.sqlite` 运行 smoke，生成 SQLite/WAL/锁文件；WinExe 不提供标准输出，故记录为 `PARTIAL_RUNTIME_SIGNAL`，不提升为 GUI/安装验收。
- 2026-09-16 候选语义防漂移：`scripts/release/candidate.py` 说明已明确其为 legacy Core-only manifest；新的含 runtime Green 候选由 `assemble_green_candidate.py`/`verify_green_candidate.py` 管理，并以 scope 标识。候选清单与发布架构回归 `36 passed`，exit 0。
- 2026-09-16 Green provenance binding：组装器清单新增 `provenance.source_commit/source_tree`，CI 组装与 release exact-SHA 验证均传入并校验两者；候选验证器支持 expected commit/tree，不匹配即失败。回归 `6 passed, 1 skipped`，CI/release YAML 解析通过；本地 r5full 候选绑定 commit `292c9020` 与 tree `f2fee079`，验证 `ok=true`、0 问题。
- 2026-09-16 Green 来源门负向回归：新增 expected commit/tree 不匹配测试，验证器明确返回 `candidate source commit mismatch` 与 `candidate source tree mismatch`；Green 组装/验证回归 `6 passed, 1 skipped`，exit 0。
- 2026-09-16 CI Green job 完整本地模拟：通过项目 `.venv` 完成 `prepare_bundle` runtime staging、self-contained desktop+Core 组装及 provenance/`--require-runtime` 验证；结果 `ok=true`、`desktop-core-runtime`、20,003 文件、0 问题。模拟 ZIP 180,076,968 bytes，已保存 471-byte 收据 `.project-local/runs/ci-green-sim-20260916b-receipt.json` 后删除模拟目录，避免缓存膨胀；正式 CI 仍需云端收据。
- 2026-09-16 云端只读回读：GitHub 最新可见 CI 仍对应旧远端 SHA `38d60509`（run `34974871286`），结论 failure；`test (3.12)` 的 OS-level tests 失败，`a0-gates` 的 ci-verdict 失败，其余 vNext jobs 多数 skipped。当前本地新提交尚未推送，故该 run 不能归因于本地最新改动；未触发云端操作。

- 2026-09-16 Windows deep-path repair: shared/backup.py, shared/migration.py and shared/migration_runner.py now use extended-length paths for manifests, migration backups, owner locks and SQLite connections; backup/DeepTutor bridge regression 12 passed, migration/governance/backup regression 50 passed. Commit c84414e8; this closes a real MAX_PATH failure but does not promote R10/R13 or independent audit status.

- 2026-09-16 adapter boundary repair: convert_youtube_transcript now validates empty source before importing the optional dependency, preserving the correct user error when the engine is unavailable; YouTube adapter regression 6 passed, commit 467482b2.

- 2026-09-16 full Python gate in project .venv: pytest -q completed 2834 passed, 10 skipped, 135 subtests passed in 185.17s with 13 dependency/deprecation warnings; no test failures or collection errors. This is local verification only; it does not prove remote CI, installer, signing or independent audit.

- 2026-09-16 Rust workspace gate: standard scripts/runtime/dev.py --run-id rust-full-fixed -- cargo test --workspace --offline -q with explicit registered MSVC 14.44 and system Windows SDK 10.0.26100 include/lib paths completed exit 0; all workspace test groups and doc-tests reported ok. Earlier exit 255 was toolchain environment initialization failure; this run is the first complete local Rust gate after fixing the environment handoff. Warnings are existing unused-code warnings; no external toolchain files changed.

- 2026-09-16 current-head Green candidate: reassembled from the current HEAD with self-contained Avalonia desktop, Rust Core and the existing Green Python runtime; `verify_green_candidate.py --require-runtime --expected-commit --expected-tree` returned `ok=true`, `desktop-core-runtime`, 21,392 files, 0 problems. Candidate DLL smoke returned `SMOKE OK`, exit 0, with a project-local SQLite database. This remains a project-local candidate, not installed, signed or released.
- 2026-09-16 post-integration gates: frozen R5 `verify_package.py` returned PASS (23 tasks/173 active files); `scripts/check_path_conventions.py --measure --json` returned 2,040 tracked/owned, 0 unowned/ambiguous/denied (100% coverage). These are local mechanical gates and do not alter independent audit or installation status.
- 2026-09-16 Green launcher probe: direct self-contained `ArcheAxis.Desktop.exe` remained alive with the candidate Core, but the generated `wscript.exe` entry did not expose a candidate process during an 8-second observation and was stopped as the owned launcher. The no-terminal VBS launcher remains PARTIAL.
- 2026-09-16 provenance refresh after launcher-template change: an intermediate candidate with a stale source commit was correctly rejected; the candidate was rebuilt at the then-current HEAD and verified `ok=true`, `desktop-core-runtime`, 21,392 files, 0 problems. DLL smoke returned `SMOKE OK`, exit 0, and created a project-local SQLite database.
- 2026-09-16 R5现场复核与容量审计：项目 `.venv\Scripts\python.exe` 执行 `verify_package.py` exit 0；X01/X02/X04 定向门禁 85 passed、30 subtests、exit 0。`inventory_project.py` 只读盘点 exit 1/status partial：可测逻辑量 18,779,552,061 bytes、162,002 files；`.project-local` 16,493,528,855 bytes、128,306 files；229 个 PermissionError、9 个 reparse points、437 个排除项。错误集中于项目内历史 ACL-deny 目录；未改 ACL、未提权、未删除。E/F、私有代理目录、外置库均未访问。
- 2026-09-16 清理预演：对 8 个历史项目内测试 run 生成 `.project-local/runs/r5-cleanup-plan-20260916.json`，共 203 条明确生成且可重建路径，逻辑大小合计 1,993,902,655 bytes；artifacts、logs、构建缓存、模型、Green 候选和原件均排除。递归删除被当前安全策略拒绝，实际删除 0。

- 2026-09-16 CI exact-SHA readback: run `35113104790` on commit `3a43488848e6f3dd5e8fa4887cae03b521588d24` completed `success`; `gateplan`, `lint`, and `a0-gates` passed. Path-selected specialist jobs were skipped by the workflow classifier, so this is not evidence that every R5 specialist gate executed.

- 2026-09-16 X01 browser/cancellation regression: `.venv\Scripts\python.exe -m pytest tests/test_a0_browser_smoke.py tests/runtime-paths/test_dev_paths.py tests/test_ci_a0_gates.py tests/test_ci_classifier.py -q` completed `78 passed, 9 subtests`, exit 0. Covers browser smoke receipt isolation, cancellation/owned-child cleanup, CI cancellation/verdict contracts; does not prove real browser execution on this Windows host or eliminate the taskpack's hosted taskkill permission gap.

- 2026-09-16 R5 current-head mechanical recheck: `verify_package.py` exit 0 (23 tasks, 173 active files); `check_path_conventions.py --measure --json` exit 0 (2,040 tracked/owned, 100%); `scripts/maintenance/check_resource_boundaries.py .` exit 0 and reported all five registered D: resources without reading their contents. The package verifier explicitly reports `current_head_checked=false`, `product_tests_run=false`, and `windows_cleanup_performed=false`; these remain separate open requirements.

- 2026-09-16 X13 release-contract regression: `.venv\Scripts\python.exe -m pytest tests/test_release_architecture.py tests/test_release_identity_contract.py tests/test_release_manifest.py tests/test_product_version_truth_contract.py tests/test_green_candidate_assembly.py -q` completed `44 passed, 1 skipped, 2 warnings`, exit 0. This validates self-contained Green assembly/identity/manifest contracts only; installer, signing, uninstall and clean-machine acceptance remain unproven.

- 2026-09-16 Green candidate duplication audit: `.project-local/build/green-candidates` contains six exact stale rebuildable paths (three expanded candidates plus three ZIPs), totaling 3,584,737,486 bytes as measured in `.project-local/runs/green-candidate-audit-20260916/artifacts/receipt.json`; each expanded manifest source commit predates current HEAD `8ee3a42e005e24064f11ead711df352aa224090d`. No deletion was performed because destructive filesystem operations remain policy-blocked.

- 2026-09-16 current capacity inventory: `inventory_project.py . --output .project-local/runs/r5-inventory-current-20260916.json` exit 1/status partial; `.project-local` readable logical bytes `18,880,843,834`, `171,099` files, `229` permission errors, `9` reparse points and `433` excluded entries. D: volume free space was unchanged at `281,633,751,040` bytes. The receipt retains opaque/private-name paths without opening them; E/F and external libraries were not accessed.

- 2026-09-16 CI exact-SHA readback: run `35118134675` on commit `db5858ad30b724ce09bd144b6b343f7aa64ae89a` completed `success`; `gateplan`, `desktop-fast` (canonical Windows desktop shell and recovery contracts), and `a0-gates` passed. Path-selected specialist jobs were skipped by the workflow classifier; this is not evidence that every R5 specialist gate executed.

- 2026-09-16 CI exact-SHA readback: run `35118889718` on commit `71591971e149edfc54a1e572bffba86883723042` completed `success`; `gateplan`, `lint`, `desktop-fast`, and `a0-gates` passed. Path-selected specialist jobs were skipped by the workflow classifier; this is not evidence that every R5 specialist gate executed.

- 2026-09-17 C/D 根目录外溢复核：C:\ 根未发现疑似临时目录；D:\ 根仅发现 `D:\tmp` 与 `D:\iFontsClientFileCache` 命中筛选。`D:\tmp` 的直接条目为 `oh/`、`blog.txt`、`mm-*.html`，时间集中在 2026-08-21/09-03，符合外部 OpenHuman/设计工具临时资料特征；未发现 ArcheAxis 归属证据，未删除。E/F 未访问。

- 2026-09-17 CI exact-SHA readback: run `35119288643` on commit `a1a2e3c6d15edd2fd5ef12b2f3cdedaac6c80d41` completed `success`; `gateplan`, `lint`, and `a0-gates` passed. Specialist jobs were skipped by the workflow classifier; this does not prove full R5 specialist coverage.

- 2026-09-17 CI dispatch fallback contract: `.venv\Scripts\python.exe -m pytest tests/test_ci_classifier.py tests/test_ci_a0_gates.py -q` completed `55 passed`, exit 0. This verifies the `force_full` routing contract locally; GitHub `workflow_dispatch` remains unavailable to the active token (HTTP 403), so it is not a remote full-specialist run.

- 2026-09-17 full Python qualification gate at current HEAD: `pwsh -NoLogo -NoProfile -File scripts/ci/run_tests.ps1 -- --full` completed `2840 passed, 10 skipped, 13 warnings` in 189.17s, exit 0. This is local Python evidence only; it does not prove Rust, installer, clean-machine, remote specialist CI or independent audit completion.

- 2026-09-17 Rust workspace qualification gate at current HEAD: `scripts/runtime/dev.py --run-id rust-current-20260917 -- <registered shared cargo> test --workspace --offline -q` completed with all workspace tests and doc-tests `ok`, exit 0. Existing unused-code warnings remain; no external toolchain files were modified. This is local Rust evidence only and does not prove installer, clean-machine or independent-audit completion.

## Continuation receipt — 2026-09-18

- `task_id`: R5 continuation / current-truth and qualification repair
- `source_sha`: `d3fd4dbcd154e6027755ff753023904faff34c6e`
- `tree_sha`: `main` read back at the same source commit after the API documentation updates
- `branch`: `main`
- `user_surface`: current truth, branch disposition evidence, R15/R10 targeted validation
- `backend_path`: Rust/Core and repository gates were not changed by this receipt
- `worker_path`: existing isolated worker paths retained; no new worker authority claimed
- `candidate`: no new Green candidate in this receipt
- `test_run`: CI run `35249501539` (documentation-only selective run)
- `actual_result`: PASS; `gateplan`, `lint`, and `a0-gates` succeeded. Earlier full qualification for the merged convergence head was run `35246039796`, including `desktop-build` and `installer-lifecycle`, all successful before main merge.
- `frontend_evidence`: local R10 targeted suite `30 passed`; this does not prove default Avalonia DeepTutor mounting.
- `green_evidence`: no new Green runtime evidence in this receipt; existing CI evidence remains bound to its own SHA/run.
- `restart_evidence`: not executed for the formal Avalonia owner loop.
- `limitations`: R10, R12, R13, R14/Q00, R15 and R16/Q01 remain partial or blocked per `R5-STATE.json`; current cargo executable is unavailable for the Rust Obsidian round-trip test.
- `rollback`: revert this receipt only; no product or authority behavior is changed.

## Continuation receipt — 2026-09-18 formal Avalonia counter projection

- `task_id`: R5 unified closeout / P0 product vertical slice
- `source_sha`: `cdc07cd0027de525dc909c7b0df8a7dce1cba16e`
- `tree_sha`: `cdc07cd0027de525dc909c7b0df8a7dce1cba16e`
- `branch`: `main`
- `user_surface`: Avalonia homepage now reads live Core workspace counts after startup, import, and review; static zero counters removed.
- `backend_path`: reused `GET /api/v1/workspaces/info`; no second business router added.
- `worker_path`: unchanged isolated worker authority; canonical `ARCHEAXIS_*` variables now precede `ARCHAXIS_*` compatibility aliases in the desktop launcher.
- `candidate`: formal Green/NSIS candidate built by full qualification run `35250755890`.
- `test_run`: `35250755890` workflow_dispatch with `force_full=true`
- `actual_result`: PASS; all full qualification jobs succeeded, including `desktop-build`, `green-candidate-vnext`, `desktop-fast`, `desktop-vnext`, `windows-runtime-smoke`, and `installer-lifecycle`; `a0-gates` succeeded.
- `frontend_evidence`: C# and Avalonia XAML changed at `MainWindow.axaml.cs` and `MainWindow.axaml`; counters are populated from Core readback.
- `green_evidence`: Green candidate and NSIS lifecycle were built and verified by the same exact SHA/run; this does not yet prove Owner's complete import-to-restart journey.
- `restart_evidence`: formal owner-loop restart/readback not executed in this receipt.
- `limitations`: R10 remains partial because DeepTutor sidecar/default browser lifecycle is not mounted; R12 has 229 permission errors and 10 reparse points in current inventory; R13 signing/clean-machine user loop remains incomplete; Q00 failed/blocked; R15 and R16 remain partial/blocked.
- `rollback`: revert the two Avalonia files and this receipt; Core API and database schema are unchanged.

## Continuation receipt — 2026-09-18 R12 inventory

- `task_id`: X14/R12 inventory refresh
- `source_sha`: `cdc07cd0027de525dc909c7b0df8a7dce1cba16e`
- `branch`: `main`
- `test_run`: `.project-local/runs/r12-inventory-20260918/artifacts/inventory.json`
- `actual_result`: PARTIAL; `.project-local` observed 19,147,355,586 logical bytes, 177,224 files, 229 permission errors, 10 reparse points; volume free space was measured but cleanup attribution remains unknown.
- `limitations`: opaque/private boundaries and ACL-denied paths were retained; no deletion was performed from this inventory.
- `rollback`: inventory is ignored evidence and has no product side effect.

## Continuation receipt — 2026-09-18 R10 formal sidecar entry

- `task_id`: X03/R10 DeepTutor formal Avalonia entry
- `source_sha`: `bdc239fa566d0cc3d9bf40a546fa834d24a2debb`
- `tree_sha`: `bdc239fa566d0cc3d9bf40a546fa834d24a2debb`
- `branch`: `main`
- `user_surface`: added an explicit Avalonia “打开学习工作台” action; the shell owns startup, READY receipt validation, loopback browser opening, and reverse-order process-tree cleanup.
- `backend_path`: existing `scripts/launch/deeptutor_web.py` wrapper only; Core authority and database remain Rust-owned.
- `worker_path`: no new authority; DeepTutor paths are explicit `ARCHEAXIS_DEEPTUTOR_*` configuration and never discover private state.
- `candidate`: formal Avalonia/Green/NSIS build from the same SHA.
- `test_run`: full qualification CI `35255332613` (`workflow_dispatch`, `force_full=true`)
- `actual_result`: PASS; `desktop-vnext`, `desktop-build`, `green-candidate-vnext`, `windows-runtime-smoke`, `installer-lifecycle`, and `a0-gates` all succeeded.
- `frontend_evidence`: `DeepTutorSupervisor.cs`, `MainWindow.axaml.cs`, `MainWindow.axaml`, and the copied wrapper resource in `ArcheAxis.Desktop.csproj`.
- `green_evidence`: the exact-SHA Green and NSIS jobs succeeded; external DeepTutor dependencies remain explicit optional configuration.
- `restart_evidence`: not yet executed as a full owner import→learning→restart journey; the supervisor cleanup path is implemented and tested by compilation/gates only.
- `limitations`: R10 remains `PARTIAL_NEEDS_WORK` until a configured DeepTutor runtime is exercised through the visible Windows shell and the same learning state is read back after restart.
- `rollback`: revert the sidecar supervisor, button, and project resource entry; Core schema and existing API contracts are unchanged.

## Continuation receipt — 2026-09-18 Green worker bundle normalization

- `task_id`: X13/R13 Green candidate worker and data-root closure
- `source_sha`: `f72c6101c6320fcb8f8200e13976c4e85a12b225`
- `tree_sha`: bound by the candidate manifest and the forced qualification run below
- `branch`: `main`
- `user_surface`: Green launcher now sets canonical `ARCHEAXIS_*` paths, preserves historical aliases, and uses one portable `data` root for the database, launcher state, and worker staging.
- `backend_path`: Rust Core remains the only database writer; candidate copies the self-contained Core binary.
- `worker_path`: candidate copies `services/python-workers`, stages the locked Python runtime, and emits a root `worker-profile.json` using safe portable relative paths.
- `candidate`: Green assembly and verifier now require runtime plus worker profile/transport for the full candidate gate.
- `test_run`: local targeted suite `41 passed, 1 skipped`; forced full qualification CI `35258053232` completed successfully.
- `actual_result`: PASS for static Green candidate composition and full qualification jobs; Green candidate, desktop build, installer lifecycle, Rust, workers, runtime, browser, contracts, security, migration, and A0 gates all succeeded.
- `limitations`: this closes static bundle composition and CI qualification only; clean-machine launch, real import, learning, and restart/readback remain separate R13 evidence.
- `rollback`: revert the five Green assembly/workflow/test files; no external library, Green install, or user data was modified.

## Continuation receipt — 2026-09-18 local R10/R15 probe refresh

- `task_id`: X03/R10 and X12/R15
- `source_sha`: local worktree; remote `main` currently reads `6bc26c213637c4b9423f2c02063e3cd3e692c0e6`
- `R10_core_probe`: `scripts/probes/r10_core_journey_smoke.py` exit 0; Core reachability/import/search/knowledge creation returned successfully, but `closed_loop_verified=false`.
- `R10_panel_probe`: `scripts/probes/r10_host_panel_smoke.py` exit 0; panel/health HTTP 200, unknown source 404, missing ID 400, unreachable Core 503; adapter journey failed at search-results assertion, so this is boundary evidence only.
- `R15_batch_probe`: `scripts/probes/r15_directory_batch_smoke.py` exit 0; unchanged rerun skipped five files with zero Core calls, one changed file reprocessed, unmapped `.qzx` was not routed to a refusing adapter.
- `R15_importer_increment`: local Obsidian importer now indexes body and YAML frontmatter wikilinks, preserves aliases/heading anchors, and deduplicates embeds; focused combination `110 passed`, Ruff passed.
- `actual_result`: local evidence strengthened; R10/R15 remain `PARTIAL_NEEDS_WORK`.
- `delivery_limitation`: GitHub write API continues returning HTTP 403 secondary rate limit; these local increments are not claimed as uploaded.

## Continuation receipt — 2026-09-18 repository runtime normalization and size audit

- `R12`: metadata-only inventory and post-prune inventory were run under `.project-local`; private names and reparse points remained opaque.
- Generated cleanup removed Cargo incremental data, two old Green candidates, old Debug/duplicate desktop outputs, and old supervisor test output; no source, user library, Green installation, or private state was touched.
- The observable `.project-local` logical size fell from approximately 19.15GB to 13.28GB. A remaining old candidate and repeated regression trees contain ACL-denied nested `.git` objects; no ACL change or elevation was used.
- `execution_preflight.py` passed (550 Markdown links checked, no actual broken links, private state unopened); repository convention check passed with zero issues after LF normalization.
- `delivery_limitation`: local receipts remain pending remote upload while GitHub write API returns HTTP 403 secondary rate limit.

## Continuation receipt — 2026-09-18 local Green candidate rebuild

- `task_id`: X13/R13 Green candidate composition
- `candidate`: `.project-local/build/green-candidates/ArcheAxis.Knowledge.Green-vlocal-20260918-x64`
- `assembly`: rebuilt from current Release desktop output, Core binary, self-contained runtime, and `services/python-workers`.
- `verification`: `verify_green_candidate.py --require-runtime --require-workers` returned `ok=true`, 479 files, no problems.
- `runtime_smoke`: candidate desktop `--smoke` with explicit `ARCHAXIS_CORE_BIN` returned exit 0.
- `limitations`: no signing, installer/uninstaller, clean-machine GUI acceptance, or remote upload; existing Green installation was not modified.

## Continuation receipt — 2026-09-18 dirty-worktree provenance-bound Green candidate

- `task_id`: X13/R13 candidate provenance correction
- `worktree_head`: `79d581406b8128470048f9f266ca936a684e78d5`
- `worktree_patch_sha256`: `916f42f44745c73a2f67e2c231398b45a6fcfbc979c78d1e340a1ab67e8bdad2`
- `candidate`: `.project-local/build/green-candidates/ArcheAxis.Knowledge.Green-vlocal-dirty-20260918-x64`
- `provenance`: manifest explicitly binds the HEAD plus the complete current tracked diff SHA; this is a dirty-worktree candidate and is not represented as a clean mainline build.
- `verification`: runtime/workers verifier `ok=true`, 479 files; desktop supervisor smoke exit 0 with explicit `ARCHAXIS_CORE_BIN`.
- `zip_sha256`: `5B25B61A830FD1E8A9D2FA9EC0BD5E5B3301B1909820582682E90393875CBC48`
- `limitations`: no signed installer, clean-machine GUI acceptance, or remote upload; Q00 remains blocked because the dirty candidate is not a clean-source acceptance candidate.

## Continuation receipt — 2026-09-18 clean-commit Green candidate provenance

- `task_id`: X13/R13 candidate provenance and runtime smoke
- `source_commit`: `fc05b0ad15fcff05404ad1703aee773dc4c84645`
- `source_tree`: `143f328eea834ebb6395970cd7e1a94cf14130de`
- `candidate`: `.project-local/build/green-candidates/ArcheAxis.Knowledge.Green-vclean-fc05b0ad-x64`
- `verification`: `verify_green_candidate.py --require-runtime --require-workers` returned `ok=true`, 479 files, no problems; manifest provenance matches the clean commit/tree.
- `runtime_smoke`: candidate desktop `--smoke` with explicit `ARCHAXIS_CORE_BIN` and `ARCHEAXIS_CORE_BIN` returned exit 0.
- `limitations`: this is a local clean-source candidate only; signed installer, uninstall lifecycle, clean-machine GUI acceptance, real Green install coverage, and remote upload remain open.

## Continuation receipt — 2026-09-18 live R11 MCP and unseen evidence

- `task_id`: X09/R11 real MCP client and unseen evaluation
- `source_sha`: `389766b2992c310269b3fe2dbe6971ac79764f16`
- `branch`: `main`
- `mcp_probe`: `.project-local/runs/r11-mcp-live-20260918.json`; exit `0`; MCP SDK `1.30.0`; real Core/MCP path; search, qualification, task receipt, and task readback succeeded; unsupported `archeaxis_accept` was refused as expected because no human-review tool is exposed.
- `unseen_probe`: `.project-local/runs/r11-unseen-live-20260918.json`; exit `0`; unseen evaluation completed; baseline retrieval was `3/5` with literal-token misses recorded; correction changed glacier `815` to `930`, and old/new values were read back.
- `actual_result`: PASS for probe execution and restart/readback behavior exercised by the probes; this is not an accuracy or full first-use quality claim.
- `limitations`: Q00 remains `AUDITED_FAIL_BLOCKED`; G02–G12 still require same-candidate evidence across real multi-format import, learning, MCP, migration, and Windows runtime. R11 remains partial until that independent audit closes.
- `rollback`: remove this receipt only; ignored probe artifacts remain local and were not staged.

## Continuation receipt — 2026-09-18 current-main full qualification

- `task_id`: Q00 prerequisite refresh for R5 current main
- `source_sha`: `dbafb341e619669c9b60ad69e2474f92f364908f`
- `branch`: `main`
- `test_run`: GitHub Actions workflow dispatch `35263005356` with `force_full=true`
- `actual_result`: PASS; all 20 qualification jobs succeeded, including `test (3.12)`, `rust-vnext`, `desktop-vnext`, `desktop-build`, `green-candidate-vnext`, `installer-lifecycle`, `windows-runtime-smoke`, and `a0-gates`.
- `meaning`: current-main candidate qualification is refreshed on the same SHA as the published execution receipt and Green/installer gates.
- `limitations`: this is a qualification prerequisite, not an independent Q00 decision. G02–G12 still require same-candidate real evidence and independent GPT review; Q00 remains blocked until that audit is rerun.
- `rollback`: remove this receipt only; no product or external-library data changed.

## Continuation receipt — 2026-09-18 second independent Q00 review

- `task_id`: Q00 independent GPT re-audit after current-main qualification
- `candidate_sha`: `dbafb341e619669c9b60ad69e2474f92f364908f`
- `qualification_run`: `35263005356`, 20/20 jobs success
- `review_scope`: read-only G01–G14 review using current qualification, live MCP/unseen receipts, and repository evidence; later `main` docs commits do not change product code.
- `gate_result`: G01 PASS (candidate-scoped); G06 PASS only for the exercised MCP/unseen capability; G13 PASS static scope; G14 PASS qualification scope. G02–G05 and G07–G12 remain BLOCKED.
- `actual_result`: Q00 remains `FAIL/BLOCKED`; Q01 remains blocked by Q00/X12/X13/X14 prerequisites.
- `limitations`: full real multi-format import/conversion, human learning journey, bidirectional correction, old non-empty database migration, clean Windows first-use/restart, and run-directory differential evidence are still missing on one candidate. CI green is not a substitute for those journeys.
- `rollback`: remove this receipt only; no product or external-library data changed.

## Continuation receipt — 2026-09-18 R11 rerun hashes

- `command_mcp`: `.venv\Scripts\python.exe scripts/probes/r11_mcp_client_smoke.py`
- `command_unseen`: `.venv\Scripts\python.exe scripts/probes/r11_unseen_evaluation.py`
- `mcp_exit`: `0`; `mcp_sdk`: `1.30.0`; output SHA-256 `DACFE775D19EA4276BE6834F6DC2E11301184A1989339DC062A28A6C2FADF630`
- `unseen_exit`: `0`; output SHA-256 `DAB2CA56B00527E3DF4789DD59D76B3FAACB027FBAD601B65CC85521EB564241`
- `mcp_observed`: real Core/MCP search, task receipt, readback, and refusal of machine human-review action.
- `unseen_observed`: unseen check passed; baseline 3/5; correction diagnostic changed 815 to 930 and removed the superseded value.
- `evidence_scope`: probe execution is reproducible local evidence for G06's exercised capability only; it does not close the remaining Q00 gates.

## Continuation receipt — 2026-09-18 Obsidian repeat-import identity increment

- `task_id`: X12/R15 stable Obsidian asset and relation identities
- `implementation`: Obsidian document/card/machine-knowledge IDs now derive from the vault-relative path; link IDs derive from source, target, type, alias, and embed state.
- `verification`: `pytest tests/test_obsidian_importer.py tests/workers/test_bulk_structured.py -q` — `33 passed`; Ruff passed.
- `actual_result`: repeated import of the same note now refreshes the same logical asset; relation indexing replaces the prior outgoing set before writing the current stable edges.
- `limitations`: target-to-imported-ID resolution, attachment hashing, Canvas semantic storage, and full Vault round-trip evidence remain open; R15 remains partial.

## Continuation receipt — 2026-09-18 Vault target resolution increment

- `task_id`: X12/R15 stable Obsidian target resolution
- `implementation`: unique same-Vault Markdown targets now resolve to their deterministic KB ID while preserving `#heading` anchors; unresolved or ambiguous targets remain verbatim.
- `verification`: `pytest tests/test_obsidian_importer.py tests/workers/test_bulk_structured.py -q` — `34 passed`; Ruff passed.
- `limitations`: attachment hashing, Canvas semantic storage, real Vault client round-trip, and full multi-format acceptance remain open.

## Continuation receipt — 2026-09-18 Canvas semantic projection increment

- `task_id`: X12/R15 Canvas node/edge persistence
- `implementation`: accepted `canvas.structure` worker output can now replace one canvas snapshot in the existing `canvases`, `canvas_nodes`, and `canvas_edges` tables; node geometry is stored in the existing spatial columns and edge endpoints remain explicit.
- `verification`: `pytest tests/test_canvas_projection.py tests/test_obsidian_importer.py tests/workers/test_bulk_structured.py -q` — `35 passed`; Ruff passed.
- `limitations`: this adapter is not yet wired into the full Core import journey, attachment hashing and real Vault round-trip remain open; R15 stays partial.

## Continuation receipt — 2026-09-18 Canvas projection Green rebuild

- `task_id`: X13/R13 provenance refresh after Canvas projection increment
- `source_commit`: `59f6419beca7f4ffb9b407c5940bbbd8f39f6cf2`
- `candidate`: `.project-local/build/green-candidates/ArcheAxis.Knowledge.Green-vclean-59f6419b-x64`
- `verification`: expected commit/tree verifier returned `ok=true`, 479 files, runtime/workers included; desktop supervisor smoke returned exit 0.
- `limitations`: local candidate only; full Core wiring, signing, uninstall, clean-machine GUI, real Green install, and remote upload remain open.

## Continuation receipt — 2026-09-18 Canvas projection candidate refresh

- `task_id`: X13/R13 provenance refresh after Canvas projection adapter
- `source_commit`: `59f6419beca7f4ffb9b407c5940bbbd8f39f6cf2`
- `candidate`: `.project-local/build/green-candidates/ArcheAxis.Knowledge.Green-vclean-59f6419b-x64`
- `verification`: expected commit/tree verifier returned `ok=true`, 479 files, runtime/workers included; desktop supervisor smoke returned exit 0.
- `limitations`: the Python projection adapter is not wired into the Rust Core import commit; signing, uninstall, clean-machine GUI, real Green install, and remote upload remain open.

## Continuation receipt — 2026-09-18 Rust Core Canvas projection wiring

- `task_id`: X12/R15 Canvas Core single-writer integration
- `implementation`: Rust schema version 5 now owns `canvas_projections`, `canvas_projection_nodes`, and `canvas_projection_edges`; successful `canvas.structure` completion projects validated worker geometry and edges inside the same Core transaction. Archive export/restore includes the new tables.
- `verification`: with the project MSVC toolchain plus C:\Program Files (x86)\Windows Kits\10\Lib\10.0.28000.0, `cargo check -p archeaxis-application -p archeaxis-store-sqlite -p archeaxis-archive` passed; `canvas_subtitles_job_end_to_end` passed 4/4, including Core table assertions. The cargo wrapper lacks cargo-fmt, but rustfmt parsing with edition 2021 reached the modified code.
- `actual_result`: PASS for the local Rust Core Canvas projection path and migration schema; broader R15 acceptance remains partial.
- `limitations`: clean-machine GUI, installer signing/uninstall, real Green installation, attachment hashing, and full multi-format/Vault acceptance remain open.

## Continuation receipt — 2026-09-18 Core-verified Green rebuild

- `task_id`: X13/R13 candidate refresh after Rust Core Canvas wiring
- `source_commit`: `bd0e91a57ca8150b30c9352e244b10cca85cb157`
- `candidate`: `.project-local/build/green-candidates/ArcheAxis.Knowledge.Green-vclean-core59f6419b-x64`
- `verification`: candidate expected commit/tree verifier returned `ok=true`, 479 files, runtime/workers included; rebuilt Core binary and desktop supervisor smoke returned exit 0.
- `limitations`: local candidate only; installer signing, uninstall, clean-machine GUI, real Green installation, and remote upload remain open.

## Continuation receipt — 2026-09-18 schema v5 archive compatibility

- `task_id`: X05/X12 Canvas schema migration and archive custody
- `implementation`: historical v2/v3 archive fixtures now explicitly exclude the newer Canvas tables when reconstructing their old wire shapes; current exports include the Canvas projection tables.
- `verification`: `cargo test -p archeaxis-archive --lib -- --nocapture` — `7 passed`; v2/v3 restoration and current-table rejection tests all passed.
- `limitations`: archive compatibility is verified locally; real user-library migration and full Canvas/Vault acceptance remain open.

## Continuation receipt — 2026-09-18 archive-compatible Green rebuild

- `task_id`: X13/R13 candidate provenance refresh after schema/archive fix
- `source_commit`: `70226a42b5e6422c1f52deb9519d07debfbc0c97`
- `candidate`: `.project-local/build/green-candidates/ArcheAxis.Knowledge.Green-vclean-archive70226a42-x64`
- `verification`: expected commit/tree verifier returned `ok=true`, 479 files, runtime/workers included; desktop supervisor smoke returned exit 0.
- `limitations`: local candidate only; installer signing, uninstall, clean-machine GUI, real Green installation, and remote upload remain open.

## Continuation receipt — 2026-09-18 target-resolution Green rebuild

- `task_id`: X13/R13 provenance refresh after R15 target resolution
- `source_commit`: `8e2c59be1cb3d08dbe5294e8cb93ac2a6f8f5d63`
- `candidate`: `.project-local/build/green-candidates/ArcheAxis.Knowledge.Green-vclean-8e2c59be-x64`
- `verification`: expected commit/tree verifier returned `ok=true`, 479 files, runtime/workers included; desktop supervisor smoke returned exit 0.
- `limitations`: local candidate only; signing, uninstall, clean-machine GUI, real Green install, and remote upload remain open.

## Continuation receipt — 2026-09-18 post-R15 clean Green rebuild

- `task_id`: X13/R13 provenance refresh after R15 increment
- `source_commit`: `d88c06b4d190f092ce784f5c58715f596f8ea63e`
- `source_tree`: bound by the candidate manifest for the same commit
- `candidate`: `.project-local/build/green-candidates/ArcheAxis.Knowledge.Green-vclean-d88c06b4-x64`
- `verification`: expected commit/tree verifier returned `ok=true`, 479 files, runtime/workers included; desktop supervisor smoke returned exit 0 with explicit Core paths.
- `limitations`: local candidate only; signed installer, clean-machine GUI, real Green install, and remote upload remain open.

## Continuation receipt — 2026-09-18 relation-replacement Green rebuild

- `task_id`: X13/R13 provenance refresh after R15 relation replacement
- `source_commit`: `52fb1d419d212c8ddf8f91e05f5be91fb1c21aec`
- `candidate`: `.project-local/build/green-candidates/ArcheAxis.Knowledge.Green-vclean-52fb1d41-x64`
- `verification`: expected commit/tree verifier returned `ok=true`, 479 files, runtime/workers included; desktop supervisor smoke returned exit 0.
- `limitations`: this remains a local candidate; installer signing, uninstall, clean-machine GUI, real Green install, and remote upload are not evidenced.
