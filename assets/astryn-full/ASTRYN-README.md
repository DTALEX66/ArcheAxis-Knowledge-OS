# ASTRYN｜星栖

AAOS 原生的角色化交互与陪伴子系统，默认角色为小栖。

当前阶段：**M0 已实现并可运行**（开发宿主、原创角色、文本交互、事件驱动状态机、宿主契约、测试），已推送到 `DTALEX66/ASTRYN` 的 `main`（HEAD 与远端逐字符一致，见 `PROJECT_CONTRACT.yaml` 的 `git_head`），远端 CI 双矩阵 success。真实模型 `NOT_TESTED`，AAOS 集成 `UNVERIFIED`，整体判定 **PARTIAL** —— 逐项证据见 [M0 验收台账](docs/tasks/M0-ACCEPTANCE-TRACKER.md)。

## 快速开始

```bash
# PATH 里没有 node/npm，需显式绑定（见 docs/development/DEVELOPMENT.md）
# $HOME 在 Git Bash 下即用户目录；不要把含用户名的绝对路径写进仓库文档。
export N26="$HOME/AppData/Local/hermes/tools/node-26.7.0-win32-x64"
export PATH="$N26:$PATH"
"$N26/node.exe" "$N26/node_modules/npm/bin/npm-cli.js" ci
cp .env.example .env            # 按需开启合成夹具/宿主模拟器
npm run dev                     # http://127.0.0.1:5183/
```

门禁：`npm run lint` / `typecheck` / `test` / `build`，或一次跑完 `npm run verify`。
真实模型：另起 `npm run dev:proxy`，凭据只进代理进程环境，不进浏览器包、不进 Git。

## 现在能看到什么

打开开发宿主即可看到原创小栖（SVG，`assets/third-party/` 为空 ⇒ 无任何第三方素材）。她会随真实事件改变表情：聚焦输入框 → 聆听；流式回复到达 → 口型帧逐帧推进（帧号只由真实数据递增，无定时器假播放）；宿主回执 → 审批/执行/完成/失败各有可辨视觉。未配置获准模型时明确显示 `MODEL_UNAVAILABLE`，**不会用脚本回复冒充 AI**；合成数据一律带 `SYNTHETIC` 徽标。

## 入口

- [执行规则](AGENTS.md) · [权威索引](AUTHORITY.md) · [项目合同](PROJECT_CONTRACT.yaml) · [决策记录](docs/authority/DECISIONS.md)
- [当前状态与接续队列](docs/current/STATUS.md) · [路径登记](docs/authority/PATH-REGISTRY.md) · [目录规范](docs/development/REPOSITORY-LAYOUT.md)
- [开发与启动](docs/development/DEVELOPMENT.md) · [依赖与许可证](docs/development/DEPENDENCIES.md)
- [能力归属与边界](docs/architecture/ASTRYN-CAPABILITY-OWNERSHIP.md) · [AAOS 能力图谱（只读核验）](docs/architecture/AAOS-HOST-CAPABILITY-MAP.md) · [C4 架构模型](docs/architecture/astryn-m0.structurizr.dsl)（配套[阅读说明](docs/architecture/astryn-m0.architecture-understanding.md)与[证据索引](docs/architecture/astryn-m0.evidence.md)） · [架构风险登记册](docs/architecture/astryn-m0.risk-quality.md)
- [设计系统契约 DESIGN.md](DESIGN.md) · [设计与无障碍复审](docs/verification/design-a11y.md) · [门禁回执 gates.json](docs/verification/gates.json)
- [开源吸收矩阵](docs/research/OPEN-SOURCE-MATRIX.md)（含方向 2/3/5/7/9 补研 43 个候选）
- [S0 现场基线](docs/verification/S0-BASELINE.md) · [M0 验证报告](docs/verification/M0-VALIDATION.md)
- [M0 验收台账](docs/tasks/M0-ACCEPTANCE-TRACKER.md) · [任务拆解与交接](docs/tasks/M0-EXECUTION-HANDOFF.md) · [启动任务原文（归档）](docs/tasks/archive/ASTRYN-DEVELOPMENT-START-V1.0.txt)

## 代码结构

| 位置 | 内容 |
| --- | --- |
| `contracts/` | 八类 Port 契约：Host / Conversation / Memory / Action / Context / AvatarRenderer / PresentationMode / CharacterProfile，加事件信封与协议版本。纯类型 + 运行时校验，不依赖 React |
| `src/companion/` | 状态 reducer、会话/请求/序号守卫、角色档案与版本化提示组装 |
| `src/interaction/` | `AstrynCompanionController`：编排 ports + guard + reducer，可脱离 React 测试 |
| `src/adapters/` | AAOS Host Adapter、仅开发环境的标准兼容适配器、SSE 解析、合成夹具、模型来源收敛 |
| `src/memory/`、`src/context/` | 记忆治理规则与进程内可销毁夹具、授权选区夹具 |
| `src/avatar/`、`src/presentation/` | 原创小栖 SVG 与状态视觉映射、可复用 React 呈现层（embedded / panel） |
| `dev-host/` | 隔离开发宿主与服务端模型代理。**不是第二个正式前端** |
| `tests/` | 118 项定向测试（14 文件）；夹具一律显式标注 SYNTHETIC |
| `scripts/` | 仓库级开发工具（`record-gates.mjs` 生成门禁回执），不属于产品运行时 |

## 边界（不可协商）

星栖只拥有人格、陪伴互动、角色表达与呈现；通用模型、记忆、上下文、任务与权限归 AAOS。二者之间只经有类型、有版本、有权限的 Host Adapter。不建第二套长期记忆主库、模型管理中心或正式前端；不直接写 AAOS 的 SQLite/CAS；任务状态只来自可校验的宿主回执，模型自称完成无效；默认不启用麦克风、摄像头、屏幕采集与系统命令。
