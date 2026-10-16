# GF04 八类宿主端口适配（交付说明）

任务包：ASTRYN-COMPANION-20261013｜分支 `feat/astryn-learning-companion-v1`
验收条款（逐字）："未接端口返回明确原因，未知不当可用。不能以非空回执或 digest 充当数字签名；没有校验器不冒充验证。"；并要求逐项接 Host、Conversation、Memory、Action、Context、AvatarRenderer、PresentationMode、CharacterProfile 八端口，使用有限宿主桥与正式 Consumer，不要求 React 获取 launch-token 的授权路径。

## 1. 交付物

| 交付物 | 位置 | 说明 |
| --- | --- | --- |
| 宿主握手与八端口清单 | `src/adapters/host-handshake.ts`（新） | 纯函数：版本面解析、能力注册表解析、兼容性判定、逐端口可用性推导（fail-closed） |
| 正式宿主适配器 | `src/adapters/aaos-bridge.ts`（改） | `x-archeaxis-launch-token` 头（无 Origin）；协议未确认与注册表未命中一律不可用；回执校验恒 `NO_VERIFIER`；轮询回执签名恒空串 |
| 契约扩展 | `contracts/host.ts`（改，附加式） | `AstrynHostCapabilityReading/AstrynHostCapabilityState`；`AstrynHostCapabilities` 增加 `observedProtocol/protocolConfirmed/hostRuntime/capabilityRegistry/capabilityRegistryNote` |
| 渲染 seam 精确化 | `src/avatar/xiaoqi-svg-renderer.ts`（改） | `resolveAvatarRenderer`：未注册 rendererId 回退并显式 `exact:false + reason` |
| UI 透出 | `src/presentation/companion-view.tsx`、`dev-host/app.tsx`（改） | AvatarView 对回退挂 `data-renderer-exact="false"`；Dev Host 新增"宿主八端口核对（GF04 握手读数）"节 |
| 测试 | `tests/adapters/host-handshake.test.ts`、`aaos-bridge.test.ts`、`port-compatibility.test.ts`（新） | 52 项：解析边界、fail-closed 矩阵、回执诚实性、边界源码扫描 |

## 2. 验收对照

| 条款 | 落点 | 证据 |
| --- | --- | --- |
| 未接端口返回明确原因 | `describePortAvailability`：不可用必带非空 `reason`（invariant 测试逐项断言）；`probeCapabilities` 五级失败（HOST_CONTRACT_MISSING / AUTHORITY_REFERENCE_MISSING / PROTOCOL_MISMATCH / WORKER_MISSING / UNKNOWN） | `host-handshake.test.ts` 9 组场景 + Dev Host 实测：5 个宿主端口全部显示 `未接｜AAOS Core 地址未配置：HOST_CONTRACT_MISSING` |
| 未知不当可用 | 协议未确认 → 五个宿主端口全 false（即使注册表 enabled）；注册表 DISABLED/WORKER_MISSING/UNKNOWN/未命中 → false；注册表整体不可读 → registryNote 透传 | `host-handshake.test.ts` "协议未确认 fail-closed"；`aaos-bridge.test.ts` "注册表 404 全部 false" |
| 不以非空回执充当数字签名 | `AaosHostBridge.verify` 对 `aaos-core` 恒 `NO_VERIFIER`（含带 64 位伪造签名字符串）；轮询回执 `signature: ''`（注释：不拿 jobId/status 拼串冒充签名） | `aaos-bridge.test.ts` 三组校验器测试；Dev Host 页内 NO_VERIFIER 披露行 |
| 没有校验器不冒充验证 | `authoritativeReceipts: false` 恒值；synthetic 回执在真实桥 `UNKNOWN_ISSUER` | 同上 |
| 有限宿主桥 + 正式 Consumer | `requestGrant` 全拒（Consumer 闭集不含星栖）；Memory/Context 端口显式拒绝并给宿主侧原因 | `aaos-bridge.test.ts` 授权与记忆/上下文组 |
| 不要求 React 获取 launch-token | 头名字面量仅存在于 `src/adapters/aaos-bridge.ts`；`presentation` 与 `dev-host` 组件层零 `launchToken` 处理（源码扫描测试） | `port-compatibility.test.ts` "边界守卫" 2 项 |
| 八端口逐项接 | `ASTRYN_PORT_MANIFEST` 八项；5 宿主边 fail-closed + 3 自有 seam 本地可用且 detail 诚实（`data-renderer-exact=false` / 未实现形态 `blockedBy` / 档案持久化 `BLOCKED_BY_HOST_CONTRACT BE06`） | `port-compatibility.test.ts` 八端口一致性组 |

## 3. 门禁与封存（GF04 终局）

- 门禁链：`bash .project-local/runs/gate-chain.sh` → lint=0 typecheck=0 test=0 build=0 record=0 anchors=0，日志 `.project-local/runs/gate-20261013-225347.log`。
- 首跑 `gate-20261013-225258` 暴露 4 处真实测试夹具类型错误（typecheck=2 build=2）：`exactOptionalPropertyTypes` 下 `body?: string` 冲突、`AstrynActionRequest` 夹具缺 `protocol/sessionId/argumentsDigest`、`grantsFor/requestAuthorization/readSelection` 少参。已逐项修复后重跑全绿，未做任何豁免。
- 树哈希：`05661b857379dc2ab384c317abb9550520d77d8bf0ae33fba6011ce6f36f7acc`（82 文件：contracts/src/dev-host/tests + 根文件含 PROJECT_CONTRACT.yaml），收据 `docs/verification/gates.json`；锚点 `trackedFiles 130 problems []`。
- 测试：26 文件 / 223 通过（新增 3 文件 52 项）。
- 构建：`index-DijUeU0d.js` 229.30 kB（gzip 75.73 kB，sha256 前缀 `129f8107fcd5d420`）、`index-h1SbPDct.css` 8.58 kB（未变）。

## 4. 浏览器实测（Dev Host，DOM 读数）

`127.0.0.1:5183`，`[data-testid=devhost-ports]` 节：

- 身份/协议/runtime 三枚 chip：`未探测 / 未探测 / 未报告`（未配置 baseUrl，符合 fail-closed）。
- 8 行端口：5 个宿主端口 `未接｜AAOS Core 地址未配置：HOST_CONTRACT_MISSING（星栖不猜测宿主现场）`；3 个 ASTRYN seam `可用`。
- NO_VERIFIER 披露行在场；控制台 3 条（2 vite debug + 1 React DevTools info）、0 错误。
- 另：AvatarView 对未注册 rendererId 的回退已带 `data-renderer-exact="false"`（GF03 三档呈现回归由既有测试覆盖）。
- 局限：本轮截图面不可用（in-app Browser 无可见表面），证据为结构化 DOM 读数而非像素；vite PID 23964 已终止，端口已释放。

## 5. 诚实边界（未接即明示）

- 真实 AAOS 调用在 GF04 未发生：宿主真值仍为 `UNVERIFIED`，全部 fail-closed 分支用回放宿主形状的夹具传输验证。
- 注册表能力键为文档化候选别名（conversation/machine_answers…、memory/knowledge_items…、actions/jobs、context/contexts…），真实键名待 GF10 握手回填；未确认期间一律按未命中处理。
- Memory 生产读写、Context 选区广播、宿主档案持久化仍 `BLOCKED_BY_HOST_CONTRACT`（BE06/BE01/BE12），本任务只交付星栖侧适配语义与拒绝原因。

## 6. 回滚

GF04 提交为线性历史上的单次提交；`git revert` 即可回滚。契约变更附加式（新增可选字段与只读读数），GF00–GF03 行为不受影响。
