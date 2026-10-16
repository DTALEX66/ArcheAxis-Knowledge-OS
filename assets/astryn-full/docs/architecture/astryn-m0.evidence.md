# 星栖 M0 架构证据索引

与 `astryn-m0.structurizr.dsl` 一一对应。每条给出可复核位置；置信度规则见 `architecture-understanding.md`。
核验日期：2026-10-13。星栖侧代码为**本仓库实际文件**；AAOS 侧为**只读核验**（零写入）。

## 节点

| 节点 | 证据 | 置信度 |
| --- | --- | --- |
| `contracts` 八类 Port | `contracts/{protocol,events,state,character,host,conversation,memory,action,context,avatar,presentation}.ts` | high |
| `guard` | `src/companion/session-guard.ts`（`AstrynEventGuard.accept`、`ASTRYN_REJECTION_REASONS` 8 项） | high |
| `reducer` | `src/companion/reducer.ts`（`isTaskAuthoritative` 二次拒绝、`utterance-end-is-not-task-completion`） | high |
| `controller` | `src/interaction/companion-controller.ts`（`attach()`、`ingestReceipt()`、`rebase()` 降级） | high |
| `composer` | `src/companion/prompt-composer.ts`（`PROMPT_TEMPLATE_VERSION='xiaoqi-system-1'`、6 节） | high |
| `bridge` | `src/adapters/aaos-bridge.ts`（`AAOS_ENDPOINTS` 常量、`probeCapabilities`、`verify`） | high（星栖侧实现） |
| `openai` / `sse` / `synth` / `registry` | `src/adapters/{openai-compatible,sse,synthetic-conversation,synthetic-host,model-registry,conversation-event}.ts` | high |
| `memPolicy` / `memFixture` / `ctxFixture` | `src/memory/{policy,synthetic-fixture}.ts`、`src/context/synthetic-context.ts` | high |
| `renderers` / `shell` / `view` | `src/avatar/{renderer-registry,xiaoqi-avatar,state-visuals,xiaoqi-svg-renderer,xiaoqi-raster-renderer}.ts`、`src/presentation/*`（N4 更新：默认位图驱动 `xiaoqi-raster-v2`，v1 SVG 为注册表 index 0 回退下限） | high |
| `devhost.app` | `dev-host/app.tsx`、`dev-host/dev-config.ts`、`dev-host/index.html` | high |
| `proxy` | `dev-host/server/dev-model-proxy.mjs`（loopback 绑定、64KB 上限、503 MODEL_UNAVAILABLE） | high |
| AAOS `core` 及各端点 | `docs/architecture/AAOS-HOST-CAPABILITY-MAP.md`（引用 `crates/archeaxis-api/src/runtime/mod.rs:176-200`、`lib.rs:101,178`、`packages/contracts/v1/*.schema.json`） | medium |
| AAOS `sqlite`（CAS） | 同上（`SCHEMA_VERSION=12`、Rust 单写者） | medium |
| `upstream` 模型提供方 | 未使用；仅配置路径存在（`.env.example`） | unknown |

## 边

| 边 | 语义 | 证据 | 置信度 |
| --- | --- | --- | --- |
| `controller → guard → reducer` | OBSERVED | `companion-controller.ts` `dispatch()`；`tests/companion/guard.test.ts` 8 项 | high |
| `reducer → renderers` | OBSERVED | `toVisibleState()` + `STATE_VISUALS`；`tests/presentation/companion-shell.test.tsx`（渲染命中经 `renderer-registry`，N4 更新命名） | high |
| `openai → proxy → upstream` | OBSERVED | `vite.config.ts` 的 `/dev-model` 代理与 rewrite；`tests/adapters/openai-compatible.test.ts` 9 项 | high（星栖侧）/ unknown（真实上游） |
| `jobsEp → controller → reducer` | **AUTHORITATIVE** | `aaos-bridge.ts` `AaosActionPort.poll/emit` → `controller.ingestReceipt` → `verify` → `trust`；`tests/companion/authority.test.ts` | high（链路）/ medium（宿主端点） |
| `synth → controller` | SYNTHETIC | `src/adapters/synthetic-host.ts`（`authority:'synthetic-fixture'`）；界面 `SYNTHETIC` 徽标 | high |
| `bridge → answersEp` | **BLOCKED** | 能力图谱：`machine/answers` 一次性问答，AAOS 用双方法 404 断言无通用流式接口 | medium |
| `bridge → knowEp` | **BLOCKED** | 能力图谱：晋升 human-only（machine 403）；Consumer 枚举 `local-machine`/`manual-context-packet` | medium |
| `bridge → ctxEp` | **BLOCKED** | 能力图谱：无"当前选区"广播合同 | medium |
| `memFixture → sqlite` | **FORBIDDEN**（建模为约束，不是实现） | `PROJECT_CONTRACT.yaml` `forbidden[]`；`tests/boundary/no-sensitive-apis.test.ts` 禁 `sqlite`/`writeFileSync`/`localStorage` | high |

## 验证结果锚点

| 断言 | 实测 |
| --- | --- |
| 四道门禁 | `lint 0 / typecheck 0 / test 0 / build 0`，13 files / 108 tests（`.project-local/runs/g8-*.log`） |
| 浏览器权威链 | `awaiting_approval → executing → completed`，审计芯片 `回执校验 通过`（`m0-browser-03-awaiting-approval.png`） |
| 缺模型不冒充 | `MODEL_UNAVAILABLE：未配置获准模型接口…`，日志零脚本回复（`m0-browser-04-model-unavailable.png`） |
| 无障碍 | axe WCAG2/2.1 A+AA：0 违规且 `incomplete=[]`；焦点环缺失 0、横向裁切 0、触控 <24px 0（`.project-local/runs/a11y-final.log`） |
| 对比度 | 14 组文字/底面对全部 ≥4.5:1，九态环色 ≥3:1（`DESIGN.md` + `tests/boundary/design-tokens.test.ts`） |
| AAOS 零写入 | `docs/verification/S0-BASELINE.md` §4；AAOS 核验时 HEAD `0574c3ac` 工作树干净 |

## 本模型刻意不包含的东西

- 不画 P2/P3/P4 的组件（语音管线、桌宠窗口、多角色编排）——它们只有接口声明，画进当前状态图会被读成已存在。
- 不画 AAOS 内部模块划分（那是 AAOS 自己的权威模型，越界描绘会造成第二套架构叙事）。
- 不把 `.project-local/` 的构建产物当架构元素。
