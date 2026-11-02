# OpenMAIC 文本场景归一化候选

此未注册原型直接调用保全的 OpenMAIC 1.3.0 中 `@openmaic/dsl` 0.12.0 原版
`normalizeScene`，并由它调用 `normalizeSlide`。它只返回调用方提供的场景及其归一化结果，
不调用模型、不生成完整场景、不播放或执行内容，不连接 Core、数据库或网络服务，也不保存课程。
不导入 `scene-generator.ts`、KaTeX 或 `interactive-post-processor`。源许可证是同目录保全的
THU-MAIC MIT；原始 ZIP 与逐成员身份记录见 `vendor/scene-content-0.3.28-original/dsl/ORIGINALS.json`。

`slide_normalize_runner.py` 的 `run_candidate(scene_json: bytes, *, node_executable, cancelled=None,
timeout_seconds=30)` 是可信宿主内部的单次调用。Node 路径只能来自可信启动配置，不能由
场景或 HTTP 指定。输入为一段完整 UTF-8 JSON 场景，最大 16,384 字节；拒绝 BOM、无效 UTF-8、
重复键、未知字段、非有限数值和与 ECMAScript 数字序列化不一致的数字文本（例如 `1.0`、
`-0`、过度精确的十进制）。数字限制是有意缩小首版，避免悄悄舍入；被拒绝的原文仍由调用方持有。

有限输入包含 `id`、`stageId`、`type: slide`、`title`、`order`、`content` 和空 `actions`；
可选的 `outlineId`、`createdAt`、`updatedAt` 不被改写。canvas 接受有界 id、视口、已知主题字段、
纯色背景和最多 200 个 text 元素。每个元素须已有唯一 id、有限坐标/尺寸/旋转及非空 content；
只对缺失或空的 `defaultFontName`、`defaultColor` 调用上游默认值。图片、形状、公式、视频、
白板、动画、动作、渐变背景与未知字段均拒绝，不删除、不降级。保守筛除部分活动/媒体标签不等于
HTML 净化：文本仍可能包含不可信标记、链接或其他危险内容。非空判断按 ECMAScript `trim`，
例如 U+FEFF 会被视为空白，而 U+0085 不会；runner 与 worker 使用同一集合。

候选回执在私有通道保留原始输入字节、输出 JSON 字节、各自 SHA-256、精确字节 patch 和语义变化
路径。补默认值会明确标示字段原先缺失还是空串；其他语义变化拒绝。输出是 ECMAScript JSON
重新序列化，空格、换行及键序可能改变，字节 patch 允许跨 UTF-8 字符边界并可重放，还原和长期
保全仍是调用方责任。摘要是无密钥的，不证明来源、权限或真实性，低熵内容可能被猜测。
回执可能包含完整私有材料，禁止写普通日志、调试输出或公共测试收据；异常仅返回固定错误码，
不回显输入或 stderr。语言运行时的内存和垃圾回收不保证擦除材料。

限定为原版结构默认值，不等于原版 `generateSceneContent`：上游完整生成还包括提示、模型调用、
形状几何修复、媒体/公式处理及新元素 ID。`normalizeScene` 本身不验证 id、几何、重复标识、
完整 JSON Schema 或渲染安全；这些窄范围约束由本包装另外检查。此结果是
`CALLER_SUPPLIED_UNVERIFIED`；未证明 Core 材料身份或外发授权。DSL 包版本 0.12.0 与其序列化
版本 0.3.0、OpenMAIC 1.3.0、AAOS 导入适配器 v2 是不同版本。

现有 `scene-build-worker.mjs` 的 Core 校验要求响应元素与该次请求原样一致；不能悄悄在该 worker
内插入本处理。可以先把归一化视作独立候选，保留转换前后信息，再另行设计 Core 协议。现有外部
导入课程按原件重新解析核对，生成内容不能冒充外部 manifest 来源；需要后续明确生成候选与材料
版本绑定、授权/取消与写事务边界、首次结果幂等和重启读回。既有 builder 的 canvas id 和时间戳
不因固定 scene id 而字节稳定。

runner 限定 stdin 32,768 字节、stdout 196,608 字节、stderr 8,192 字节和单模块实例一槽，
忙时立即拒绝；直接子进程或管道线程清理未确认则该实例不再准入。多进程或多次导入不共享槽，
可信宿主仍须设整体并发上限。默认 deadline 30 秒、范围 0.25–60 秒，发生超时或取消只尝试回收
本次直接持有的子进程；管道、后代和网络隔离分别报告已知状态或 `UNKNOWN` / `NOT_ESTABLISHED`。
启动调用可能在创建进程后抛错，所以从调用开始即将子进程状态视为未知；若未取得句柄则保留槽。
`pipe_threads: JOINED` 仅说明线程结束，不证明管道句柄已关闭。线程均结束时，close 抛出
`BaseException` 会返回 `PIPE_IO_FAILED` 并保留槽；线程未全部结束时保留未知状态和槽。
线程构造或启动中途失败时，只关闭尚未交给线程的管道，并对已有线程标识的线程限时等待；
尝试启动但状态不明的管道不会跨线程强制关闭。
同步文件读取、进程创建及非标准管道包装器的同步 close 本身不保证可及时中断。
未建立 Windows Job、进程树或内存硬限制。

外层在启动前校验 Node 24.21.0 和 worker 固定字节、清除环境并非 shell 启动，Windows 隐藏窗口；
worker 校验 DSL manifest、许可证与实际使用的两个原始 TS 源，并以固定规则把上游 `./stage.js`
解析到保全的 `stage.ts`；本次调用不会重新打开或校验 Owner 原 ZIP。没有新增 npm 依赖或安装脚本。
身份检查与路径加载之间仍有竞态，
祖先目录和 runner 自身身份必须由未来宿主绑定；这些检查不是系统沙箱。与 HTML 候选一样，
runner 是独立副本，不是统一生产加载器，后续整合须回归各自原有行为。退出码 0 不代表候选成功，
必须检查 `status`。合成测试通过也不等于真实资料、已安装产品、Core 持久化或 Owner 验收。
