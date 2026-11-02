# OpenMAIC 有限 HTML 改写候选

这是未注册的内部原型：调用 OpenMAIC 1.3.0 / generation 0.3.28 保全原件的
`rewriteInteractiveLibraries`，不连接 Core、HTTP、数据库、模型或前端，不渲染 HTML，
也没有把输入脚本交给 JavaScript 运行器执行。输入和输出都必须当作未净化的私有材料；
本原型不证明一般输入代码绝不执行，也不是系统沙箱。

调用方须先自行保留原始字节及授权依据。`interactive_html_rewrite_runner.py` 的
`run_candidate(html: bytes, *, node_executable, cancelled=None, timeout_seconds=30)`
返回一次候选；`node_executable` 只能由可信宿主配置，不能从请求、HTML 或 HTTP 参数选择。
这里没有并发调度器：每个 Python 模块实例只允许一个运行中的调用，忙时直接拒绝而不排队；
如果直接子进程或管道线程清理未确认，该实例保留占用状态，之后的调用继续拒绝。此约束不跨进程
或重复导入的模块实例，可信宿主仍须设置整体并发上限。取消只是一枚进程内事件，不是 Core
授权或撤权边界，返回前后仍存在竞态。

worker 请求为单个 UTF-8 JSON 对象，仅允许 `schema`、`request_id`、
`html_utf8_base64` 三个字符串字段；schema 是 `archeaxis.openmaic-interactive-html-rewrite/v1`。
拒绝重复及未知字段、非规范 base64、无效 UTF-8、UTF-8 BOM、NUL、超限输入，以及含大小写
不敏感 `sourceMappingURL` 字样的 HTML。最后一项会误拒部分普通文字，是有意缩小首版范围；
它不是通用 source map 识别、动态代码拦截或 HTML 安全检查。HTML 声明的编码未做浏览器语义
验证。runner 自己生成请求 ID，不把任何路径、模型、网络选项或原文写到命令行。

成功状态仅为 `OBSERVED_CANDIDATE`。回执包含输入/输出字节长度与 SHA-256、输出的 UTF-8
base64、原上游的 `unmatchedExternalHosts` 和一个以**字节**为单位的可重放 patch；patch 使用
最长公共前缀与后缀，可能把多个分散编辑合成一个范围，也可能在 UTF-8 字符的字节中间分界。
runner 独立验证原文摘要、结果摘要、patch 重放及已知字段；原文仍由调用方保留，本模块不会
写入或恢复它。错误不回显原文、结果、异常文字、stderr 或调用方路径。摘要没有密钥，低熵材料
可能被枚举；它们不是脱敏、认证、材料授权或来源验证。

上游函数有有意保留的范围与损失：

- 改写 script `src` 或 link `href` 时可能删除 `integrity`、将已有 `crossorigin` 改为
  `anonymous`；改写 style、module 或 importmap 文本时可能改变 CRLF。精确 patch 记录实际差异，
  `possible_effects` 只是全局提示，不表示每项都发生。
- 只扫描上游支持的部分引用；例如 img、iframe、普通 CSS `url()`、运行时构造的 URL 和重复
  属性可能没有计入。坏 CSS、importmap 或模块内容可能被上游捕获异常并保留。因而空
  `unmatchedExternalHosts` 不证明没有外链、完整离线、资源存在或内容可安全播放。
- 保留或输出的 URL、路径与脚本均不可信。上游对既有 `/vendor/interactive/` 前缀有快速路径，
  可留下 `..`；HTML 改写没有调用 URL 原型的 `safeOutput`。任何未来加载动作仍需独立做授权、
  路径检查、资产成员及完整性验证；词法路径匹配不证明对应资源已安装。

worker 退出码 0 只表示协议处理结束；调用方必须检查 `status`。失败不会返回候选。输入和输出
上限依次为 8,192 / 16,384 字节，stdin 16,384 字节，stdout 65,536 字节、stderr 8,192 字节。
超限拒绝，不把截断视作完整内容；runner 使用有界读取线程并丢弃 stderr。回执、输出和未匹配主机
可能包含私有内容，必须只经私有 IPC 交给授权调用方，不应写入普通日志或合成测试收据。Python
和 Node 的内存及垃圾回收不保证擦除这些字节；管道清理未知时尤其不能声称已清除所有副本。

runner 仅从可信配置的绝对路径启动指定 SHA-256 的 Node 24.21.0，并在启动前检查固定 worker
SHA；非 shell 启动并清理环境，在 Windows 使用 `CREATE_NO_WINDOW`。worker 再检查运行中 Node
版本及字节、供体原件和锁定依赖。身份校验后按路径启动/加载仍有替换竞态，祖先目录和 Python
runner 自身的可信身份须由未来宿主绑定；这些检查不建立文件系统或网络隔离。固定资产不可用或
身份不符即拒绝。此处的解析器和身份守卫是已有 URL/HTML 探针逻辑的**独立副本**，不是统一生产
加载器；未来合并或接线前须消除漂移，并同时回归 URL 和 HTML 两条路径。

默认 30 秒 deadline 覆盖可检查的启动前校验、子进程及结果阶段，支持 0.25–60 秒；同步文件 I/O
和进程创建本身不可由此保证准时中断。超时、取消或输出超限时仅尝试终止并等待本次直接子进程，
回执的 `direct_child`、`pipe_threads` 记录实际确认状态，清理阶段仅作有限等待、可能再花数秒；
未确认即 `UNKNOWN`。
没有验证 Job、后代进程回收、总内存上限或网络隔离，`descendants` 永远为 `UNKNOWN`。运行中的
stdout 不是日志；Node 或 runner 运行时被外部强制终止时，回收也可能无法确认。

现有测试仅使用固定合成材料与固定身份 Node，不能据此声称真实资料、安装包、Core 授权、撤权、
持久任务或正式环境通过。未来任何持久化都必须由 Core 在同一事务或串行边界重新检查材料版本、
授权、取消/世代并写入；本原型的哈希、事件和候选回执不能替代该步骤。
