# 剩余工作台账（ASTRYN Companion 第一期交接）

- 配套文档：`docs/companion/GF11-DELIVERY-GUIDE.md`（交付指南）；本台账是其 §9 声明分级的逐项展开。
- 状态词表：OPEN（内部可推行）/ BLOCKED_BY_HOST_CONTRACT / PENDING_EXTERNAL / UNVERIFIED / NOT_EXECUTED / RESERVED（入口保留，接通条件未到）。
- 封存基线：源码树 sha256 `367b15793cfb7a2b88c3d486674916b869e89b37699dc9a6d05373a57b0d037f`（100 文件，GF11 当轮历史封印），收据 `docs/verification/gates.json`；门禁 36 文件 / 319 测试全绿（GF11 当轮）。

> **N1–N4 更新（2026-10-14）**：B 表 MINIMAX v2 已交付落库（`PENDING_EXTERNAL` 解除）；现行封存以 `docs/verification/gates.json` 为准（八阶段全绿）。下文相关行已就地更新。

## A 宿主合同依赖（阻塞集成；宿主仓 = DTALEX66/ArcheAxis-Knowledge-OS，本仓库从不写宿主仓）

| 事项 | 状态 | 需要宿主提供的面 | ASTRYN 侧已就绪 | 证据 |
|---|---|---|---|---|
| 语音运行时（ASR/TTS/音频主时钟） | BLOCKED（BE01） | speech_optional 提案正式登记：schemas/DTOs、原生路由、契约+负例测试、版本与校验和四项齐备 | 前端字段、设置面板、回放外壳与降级（禁用运行、无占位语音） | docs/companion/GF09-SPEECH-SHELL.md；contracts/speech.ts 提案逐字冻结 |
| AAOS 侧集成面 | BLOCKED（BE12） | 宿主合同版本、能力注册表键名回填、权限面 | 八端口 fail-closed 握手 + 联合验收剧本 | docs/companion/GF04-HOST-ADAPTER.md；GF10-JOINT-ACCEPTANCE.md |
| 正式槽位接管 | BLOCKED（FE18） | 宿主前端把 home/reading/sidebar 三槽的入场退场接到正式页面 | AstrynCompanionEntry 三槽 + 共享会话 + 令牌化尺寸（宿主容器覆盖令牌即可） | docs/companion/GF08-SLOTS-AND-HANDOFF.md |
| 会话流通道 | BLOCKED（BE05） | 流式会话事件通道（或一次性问答的正式语义） | SSE 解码、乱序/迟到守卫、取消与查询-再重发 | docs/companion/GF07-STREAM-AND-RETRY.md |
| 档案/记忆持久化 | BLOCKED（BE06） | 人物档案与记忆的宿主持久化接口；记忆 grant 变更接口 | 档案 v3（含 v1/v2 迁移）、记忆治理双读回、本机停用拦截 | docs/companion/GF01-PROFILE-AND-SETTINGS.md；GF06-MEMORY-GOVERNANCE.md |
| 其余宿主合同项 | BLOCKED | 见 PROJECT_CONTRACT.yaml host_dependencies（BE03/BE05/BE06/BE07/BE12 清单） | 对应端口契约已冻结 | docs/companion/source-ports-readback.json |

## B 外部产出

| 事项 | 状态 | 规程 | 不得宣称 |
|---|---|---|---|
| MINIMAX v2 写实/位图资产 | DELIVERED（2026-10-14 落库） | 已按规程执行：22 直用 + 3 派生（`derived-alpha`）落 `assets/character/upgraded/v1/`，清单 schema v2 逐张 bytes/sha256 登记；`pose_listening` 去背如实中止（`ABORTED_BG_NONUNIFORM`）、种子未暴露（`seedExposure=NONE`）、MINIMAX 侧 429 重试需显式授权 | 「音素口型」「未登记件被运行时引用」「Live2D / 3D 已交付」；当前默认画面为 v2 位图（2D 升级），v1 SVG 为回退下限 |

## C 保留状态入口（入口已在，条件未到；禁止宣称已接通）

| 入口 | 状态 | 现状（实测） | 接通条件 |
|---|---|---|---|
| 待接声音 | RESERVED | 设置-声音节四能力芯片全「未接」+ BLOCKED_BY_HOST_CONTRACT 文案 + 试听/停止/按住说话禁用 + 无 audio 元素 | BE01 登记 + 真实回放源接入（外壳按 AbortSignal 结清） |
| 精确口型 | RESERVED | 口型模式=文本帧口型（无音频）；resolveMouthMode 三态契约已备 | 音素时间戳来源（未来口型驱动器） |
| 写实 / Live2D / 3D 人物 | RESERVED | v2 = 2D 升级位图已 DELIVERED 并默认（见 B）；写实照片级 / Live2D / VRM 仍 `deferred_scope` | Live2D / 3D 立项 + 生产（二期） |
| 桌宠入口 | RESERVED | deferred_scope（任务包明列）：原生桌宠、多显示器跨窗音频、渲染所有权均不在一期 | 二期立项 |

## D 未执行 / 未验证

| 事项 | 状态 | 说明 |
|---|---|---|
| 安装与发布 | NOT_EXECUTED | 未发布包、未安装到宿主；融入方式=源码级引入 + `@astryn/core` / `@astryn/contracts` 别名（或复制子集） |
| 真实模型联调 | UNVERIFIED（A05） | 仅合成传输与 loopback 代理两条路径的测试证据；无上游凭据、未联调 |
| 真人验收主观项 | NOT_EXECUTED | GF10 现场项（真实用户试用判断）不在本仓库可执行范围 |
| 3D / Live2D / VRM 渲染器 | deferred_scope | 任务包明列 |

## E 技术残余（GF10 已如实记录，此处汇总为交接项）

| 残余 | 说明 | 交接提示 |
|---|---|---|
| 亚秒状态不可截屏 | listen/think/speak 在零时延合成夹具下不稳定可观察；九态语义由单元测试钉住 | 接真实模型/宿主后重拍状态帧 |
| devhost-new-session 不重置进程内存储 | 该按钮只换会话种子；学习/记忆存储需整页刷新才重置；属开发演示接线 | 正式宿主不需要此语义；勿据此设计产品行为 |
| 字幕/停止语义待真实播放器 | 投影与停止由合成时钟单元测试钉住 | 真实播放器必须遵守端口 AbortSignal 与结清语义 |
| 连接形态无截图 | 合成端口按钮流有单元测试、无浏览器截图（GF10 limitations） | 真实模型接通后补采集 |
| 功能分支无 CI | ci.yml 只在 main/PR 触发；分支权威闸门=本地门禁链 | 合入 main 即触发双 node 矩阵 CI |

## F 推进建议（顺序）

1. BE12/FE18 宿主合同登记 → 八端口逐个转正（先 conversation/memory，后 action/context）。
2. BE01 语音登记 → 接真实 ASR/TTS，替换禁用态外壳（保留降级路径）。
3. ~~MINIMAX v2 回传 → 登记 + 激活（v1 保留为回退下限）~~ **已完成**（N1，2026-10-14：落库 + 默认渲染器切换 D018/D019）；残余 = `pose_listening` 去背重试（MINIMAX 侧 429，需显式授权）与 `derived-alpha` 三张过渡件的后续精修。
4. 真实模型凭据经宿主侧注入 → A05 联调，补连接形态与真实引用采集。
5. 桌宠 / 3D / 音素口型按 deferred_scope 立二期卡。
