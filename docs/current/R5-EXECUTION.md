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
使用项目 `.venv` 解释器，并经 `scripts\\runtime\\dev.py` 启动 Core。输出路由契约测试 `7 passed`，
Ruff 与 `git diff --check` 通过；未实际安装依赖或启动服务。

`run_windows.ps1` 也已收口：保留首次 `.venv` 引导和 requirements 安装，但将 TEMP/TMP/TMPDIR、
pip/uv cache 固定到 `.project-local`，Core 启动改经 `scripts\\runtime\\dev.py`。输出路由契约
测试 `6 passed`，Ruff 与 `git diff --check` 通过；本轮未实际安装依赖或拉起 Core，避免把网络/安装
副作用伪装成验证结果。
安装前复核项目 `.venv`（Python `3.13.14`）时，`uv pip check --python .venv\\Scripts\\python.exe`
报告 `rapidocr-onnxruntime` 的约束为 `Python >=3.6, <3.13`；uv 命令退出码虽为 0，但该不兼容
按环境失败处理。未强行降级 Python、替换依赖或覆盖现有环境；Windows 引导入口的真实安装仍需
在满足依赖约束的 CPython 版本上单独验收。此项标为 REPO03 环境阻塞，不影响已完成的输出路径止增。
