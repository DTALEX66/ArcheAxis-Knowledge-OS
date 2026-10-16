# ASTRYN M0 执行拆解与交接

日期：2026-10-13。用途：供用户另行选择的 AGENT 承接真实开发。本文件是执行拆解，不替代启动原文、不证明功能已完成、不自动授予远端或付费操作权限。

## 1. 当前事实与目标

项目：ASTRYN｜星栖，默认角色小栖。目标仓库 https://github.com/DTALEX66/ASTRYN ，本地根目录 `D:\All projects\ASTRYN`。

本次交接前已完成任务原文归档、目录规范、权威索引、项目合同与路径登记。归档 SHA-256 为 `866C151DB45E0D0ADFCAFA9F059A836DF859D830420B65AB95673FDD4B08450F`，已与源附件核对一致。

本轮读取时存在上述规范文件和空代码目录；没有产品实现、manifest、lockfile、测试、CI 或可运行宿主。最近检查 `.git` 不存在。之前远端读取因 SSH known_hosts 权限拒绝失败；不能推断 GitHub 仓库不存在或为空。新 AGENT 必须重新核验这些易变事实。

M0 完成定义：开发宿主可运行，能看到原创小栖；文本交互、状态和取消实际工作；存在可替换的 AAOS Host 契约；真实模型有条件验证，缺失时明确报错。AAOS 接口缺失不能阻止不依赖它的开发，也不能用合成测试代替真实集成结论。

## 2. 阅读顺序与边界

先读根目录 `AGENTS.md`、`AUTHORITY.md`、`PROJECT_CONTRACT.yaml`、`docs/current/STATUS.md`、`docs/authority/PATH-REGISTRY.md`、`docs/development/REPOSITORY-LAYOUT.md`，再完整读 `docs/tasks/archive/ASTRYN-DEVELOPMENT-START-V1.0.txt` 与本文件。

唯一默认写入范围：ASTRYN。AAOS 可按启动任务作最小必要只读核验，候选路径 `D:\All projects\ArcheAxis-Knowledge-OS`；不可修改其源码、任务队列或运行状态。其他挂载项目不自动授权读写。E:/F: 不访问。

不得修改全局配置、SSH 配置、ACL、模型/provider/auth 或绕过拒绝。不得自动 git init、覆盖规范、强制 pull、批量清理、commit、push、merge、发布、安装正式程序或调用付费模型。遇到必须新增授权的操作，说明具体对象与原因，同时继续独立可完成的部分。

ASTRYN 拥有角色领域；AAOS 拥有通用模型、记忆、上下文、任务、权限与权威存储。只通过有类型、版本和权限的 Host Adapter 接入，禁止直接写宿主数据库。Dev Host 不演化为正式独立产品。不新建长期记忆库、模型管理中心或任务引擎。

## 3. 总体依赖与工作组织

执行链：T00 → T01 → T02/T03 → T04 → T05 → T06 → T07 → T08 → T09 → T10。T02/T03 可以在概念上并行；没有用户要求时无需多 AGENT。共享 checkout 只有一个 writer。用户若安排多个 AGENT，只读研究可共享，独立写入必须隔离且由最终负责人统一集成验证。

每个任务开始时记录输入、现状和范围；结束时记录实际文件、命令、退出码、证据级别、阻塞及下一项。不要完成一份计划就停止，也不要在每项常规实现前反复询问。

## 4. 任务包

### T00｜现场与 Git 身份核验（S0）

输入：已建立的规范和路径。动作：检查 cwd、目录内容；若 `.git` 存在，读取 root/status/branch/HEAD/remotes/worktrees；若不存在，明确 NOT_A_GIT_REPOSITORY，不循环运行无意义 Git 命令。读取可用 Node、包管理器、Rust 等版本，不全局安装。

只读核验目标远端和实际 ref。确认 URL 是否受 Git 全局 rewrite 影响时，只读取相关配置，不打印认证信息；权限拒绝后不修改 SSH/凭据或绕过。无法访问远端记录 UNVERIFIED。

输出：`docs/verification/S0-BASELINE.md`，包括新增规范文件也属于需保留的数据。若需 clone/初始化，先提出保留本地所有文件的具体方案，请用户决定；不要 clone 到非空目录或重新创建远端。Git 未解决时，可继续已授权的本地源码工作，但不得声称在正式 Git 分支上完成。

验收：本地/远端事实分别有证据，已有文件未损失。阻塞只影响依赖 Git 的动作，不冻结全部开发。

### T01｜AAOS 权威及 API 发现（S0）

先验证 AAOS exact path 是否存在及仓库身份，读取启动原文指定的 AGENTS、AUTHORITY、PROJECT_CONTRACT、DECISION_SUPERSESSION_LEDGER、现行执行文件，再按需读 frontend、src-tauri 与共享契约。不存在或不可读时按授权使用 GitHub 只读源码，不扫描磁盘。

为模型/会话、记忆、上下文、动作/审批分别登记：实际代码或合同位置、版本、权限机制、可调用入口、是否可用。不能只从类型名断言服务运行。权威文件缺失标 AUTHORITY_REFERENCE_MISSING；接口缺失标 BLOCKED_BY_HOST_CONTRACT。

输出：`docs/architecture/AAOS-HOST-CAPABILITY-MAP.md`。每项列支持事实、ASTRYN Adapter 责任和缺口。验收：实际已有能力与拟议接口分开；AAOS 没有任何写入。

### T02｜首批开源研究与采用决定（S2）

完整覆盖启动原文的九个优先仓库：airi、Open-LLM-VTuber、OpenAvatarChat、Fay、TalkingHead、LiveTalking、LivePortrait、MuseTalk、Codex-QQ-Skin。主动补充相关候选，十类方向至少注明首轮覆盖与后续待研究范围；不要声称已深度验证所有项目。

对重要候选记录官方 URL、核验日期、tag/commit、维护情况、实际源码/测试证据、代码/权重/素材/依赖许可、Windows 与 React/Tauri 成本、硬件与运行成本、最小可吸收能力、AAOS/ASTRYN 归属和 adopt/adapt/reference/defer/reject 理由。不明许可证标 UNKNOWN，不下载权重或复制素材。

优先决策建议：M0 使用原创 SVG/Canvas + React，保留 renderer seam；只研究未来 Live2D/VRM 和语音路径，不一次引入多套渲染底座。Codex-QQ-Skin 仅交互参考。建议需经事实核验收敛，不作为已确认依赖。

输出：`docs/research/OPEN-SOURCE-MATRIX.md` 和最小决策记录。验收：不只引用 README 宣传；先完成足以支持 M0 的判断，然后继续编码，研究不无限延期。

### T03｜最小工程骨架（S1）

根据实际 AAOS 约束选择最少依赖的 React/TypeScript/Vite Dev Host；先确认项目 scope、版本、官方来源、现有环境与 lockfile。此处是建议，当前尚未批准或验证具体版本。不得默认下载大型运行时或先创建七个包。

建立 manifest、唯一 lockfile、类型检查、lint、定向单测、build 命令及基础 CI 定义。逻辑模块落在现有目录，具体布局写入架构文档。先把结构跑通，不把空接口算产品完成。M0 无必要时不额外引入 Tauri/Rust/Python 后台；AAOS Host 边界保持兼容。

输出：可安装/构建的最小工程、启动说明与命令表。验收：命令实际运行、依赖与锁一致；CI 文件存在只证明配置，未远端运行不报 CI PASS。

### T04｜契约与事件状态机（S1/S3）

实现 AstrynHostPort、ConversationPort、MemoryPort、ActionPort、ContextPort、AvatarRenderer、PresentationMode、CharacterProfile 或职责等价接口。角色配置可维护，不将全部身份藏在单一巨大提示词中。

定义事件 envelope：协议版本、会话 ID、请求/关联任务 ID、事件序号或版本、来源和 payload。每次请求独立身份；旧会话、已取消请求、重复/过期序号不得写入当前状态。断线恢复明确 cursor/能力声明；宿主不支持时返回能力缺失，不伪造恢复。

状态包含 idle/listening/thinking/speaking/executing/awaiting_approval/completed/failed/interrupted。用户输入与请求生命周期驱动聊天状态；任务审批/完成/失败必须来自可信 Action 回执。模型正文含“任务已完成”不得改变任务状态。说完一句话也不等于执行任务完成。

输出：类型、状态 reducer/controller、单测。验收：正常、错误、重复、乱序、取消、晚到、切换会话、卸载测试通过；任务权威来源有负向测试。

### T05｜原创小栖与可复用 UI（M0-A/C/F）

实现原创 2D 角色，至少 idle、输入/聆听、思考、回复、失败/中断有可见差异；表情动作绑定 T04 事件，不用定时假进度模拟智能。注明 AI 身份、提供停止与隐藏角色控制，兼顾减少动画与低资源占用。

实现对话输入、消息流、错误展示、停止生成、基础角色配置和开发宿主。呈现接口声明 embedded/panel/floating/pet/voice-only，但只宣称本轮实际实现的模式；浏览器预览不等于原生浮窗或桌宠。

输出：renderer、React presentation、Dev Host。验收：浏览器能看到角色，真实 UI 输入引发状态变化，布局可用，卸载清理事件/动画/请求；不默认开启麦克风、摄像头、采屏或系统命令。

### T06｜真实对话适配（M0-B）

先尝试 T01 已确认的 AAOS 服务。不可接通时实现仅开发环境的标准兼容服务端代理，密钥留在服务端，不进入前端 bundle、日志或 Git；不改变用户全局 endpoint/provider。开发服务绑定 loopback，约束请求目标/大小/超时，避免成为开放代理。

实现真实请求、流式解析、失败、取消、上下文管理。测试流的分块边界、结束事件、损坏数据和中断；传输取消和 UI 忽略迟到事件同时成立。无配置显示 MODEL_UNAVAILABLE，不给脚本回复冒充 AI。

合成传输可用于自动测试，但必须明确 SYNTHETIC。没有现有获准模型凭据/服务时，不读取其他项目秘密、不付费调用；实现配置路径并把真实调用验收标 NOT_TESTED，继续其余任务。

输出：Adapter、开发代理（若必要）、无密钥配置示例。验收：合成传输回归与真实模型验证分开；实际真实模型测试需记录授权服务、非敏感参数和结果，不保存私人正文。

### T07｜记忆与授权上下文（M0-D/E）

实现 MemoryPort 最小可治理候选结构：作用域、来源、类型、同意/权限及生命周期。区分偏好、私人陪伴内容、虚构剧情和经验证事实。提供查看/编辑/撤销/删除契约，未经宿主支持不声称生产功能已接通。

测试使用可销毁进程内夹具；测试越权 scope 拒绝、私密内容不跨模块、虚构内容不进入真实知识、模型候选不自动成为权威记录、撤销/删除契约。UI 不直接持久化正式记忆。

实现 ContextPort 选中文本场景，包含授权、来源标识和版本；合成文档明确标注。接通真实 AAOS 需另有集成任务许可，不能通过读取数据库替代接口。

输出：契约、Adapter/fixture、场景测试。验收：无第二主库、无直接 AAOS DB 写入；缺失真实接口标 BLOCKED_BY_HOST_CONTRACT，fixture 标 SYNTHETIC。

### T08｜本地门禁与浏览器验证（S4）

从 manifest 发现实际 lint/typecheck/unit/build 命令并运行，记录退出码。浏览器验证：角色显示、输入、缺模型、流式、失败、取消、快速切换会话、卸载及布局。需要时用可控测试传输验证 UI，但测试页面必须标 SYNTHETIC。

原始日志/截图存 `.project-local/runs`、`.project-local/artifacts`；脱敏结论存 `docs/verification/M0-VALIDATION.md`。失败/取消/required skip 不算 PASS。结构检查、本地执行、真实模型、AAOS 集成、exact-SHA CI、安装运行、用户验收分别给状态。

验收：原始问题有回归，不只有镜像实现的断言；测试完成后不无意义扩大全量测试；新变更需重跑受影响门禁。

### T09｜交付文档与验收逐项回填（S5）

更新 README 启动方法、架构能力归属、接口/配置说明、候选矩阵、STATUS 和验收台账。为每项写实际文件和证据，列未完成与最短下一步。标清开发宿主，不宣称正式产品、原生 AAOS 接入、语音或桌宠已完成。

若存在 Git，审阅 final diff/status/意外文件，显式列出待提交文件；若仍无 Git，列文件清单与原因。没有远端授权不 commit/push/PR/merge/release。

验收：用户按 README 可复现；状态来源可信；没有私人数据、密钥、无许可素材、模型权重或运行数据库；AAOS 未改动。

### T10｜接续与集成任务界定

按真实缺口排序：Git 关联、真实模型验证、宿主契约确认、AAOS 原生挂载、统一会话/记忆/上下文接入。P1 修改 AAOS 必须单独授权；P2 语音/渲染/浮窗、P3 系统 Agent、P4 多角色只保留接口，不纳入本轮完成范围。

输出：最多数项可执行队列，每项有输入、范围、完成定义和所需授权。不得另建与 AAOS 队列竞争的唯一主计划。

## 5. 防漂移规则

1. 开始每项先对照原文目标；新增需求记为后续，不偷偷替换 M0。
2. 每次决定说明为哪个验收服务；无关重构、依赖升级、生态建设不做。
3. 不将漂亮 UI、TaskPack、接口类型、fixture、build 或 CI 配置当作真实 AI/集成完成。
4. 无模型仍可交付工程和错误路径，但真实模型验收保持 NOT_TESTED；不得用 mock 填补成功指标。
5. 不丢陪伴定位；也不以角色性格绕过授权或伪造系统任务状态。
6. 需要改变本轮范围时记录来源与取舍；互斥业务选择或新增高风险权限才问用户。
7. 阻塞按任务隔离，继续不依赖该阻塞的代码；权限拒绝不绕过。
8. 每次交接更新当前文件，不让下一 AGENT 从旧 COMPLETE 或历史 SHA 推断事实。

## 6. 证据与最终报告格式

每项记录：任务 ID、状态、修改路径、验证命令及退出码、证据级别、缺口、下一步。结论可用 PASS/PARTIAL/BLOCKED/NOT_TESTED/NOT_EXECUTED/FAIL/UNVERIFIED，级别用 NO_EVIDENCE/SYNTHETIC/INTEGRATED/REAL。

最终报告必须给出：实际实现、启动步骤、验证结果、逐项验收、真实模型与 AAOS 集成状态、候选技术取舍、能力归属、Git 工作树/远端状态、未执行事项和最短接续队列。仅有文档与占位不算 M0。
