# 首批开源技术吸收矩阵

> **读法约定**：§2 与 §3 各候选小节里出现的裸路径（如 `src/handlers/asr/`、`scripts/realtime_inference.py`、`packages/ccc/`）**指向该候选自己的仓库**，不是 ASTRYN 仓库内的路径。ASTRYN 自身文件一律带 `contracts/`、`src/`、`tests/`、`dev-host/`、`docs/` 前缀并在正文中明确说明。链接核查工具需按此排除，否则会误报死链。

核验日期：2026-10-12 至 2026-10-13。核验方式：GitHub REST API 元数据 + `git/trees` 全量文件树 + raw 源码文件 + npm registry；工作记录见 `.project-local/runs/research/group-{A,B,C}.md`（本地过程件，不作为正式证据）。全程未 clone、未安装第三方依赖、未下载权重或素材、未调用付费接口。

纪律：**README 宣传不计入能力**；代码许可与权重/素材许可分别判定；取不到的数据标 `UNVERIFIED`，不估算。

## 1. 结论先说

M0 的渲染路线是**原创 SVG + React，保留 renderer seam**（`AstrynAvatarRenderer`）。N4 更新（2026-10-14）：现行渲染路线 = **九态位图默认（`xiaoqi-raster-v2`，AI 生成，外部生产并按 `STATE-ASSET-INDEX.json` 登记）+ 原创 SVG 回退下限**（注册表 `src/avatar/renderer-registry.ts`，v1 为 index 0）。九个优先仓库中没有任何一个可以整体作为底座：三个是 GPU 服务端视频人脸（形态与"无后端 + 可交互表情"冲突），一个是 GPL 后台且自带第二套记忆库，一个是 Vue/Electron 全栈，一个是闭源素材混合的 3D 管线。真正可吸收的是**接口形状与数据结构**，不是代码本体。

| 项目 | 决定 | 一句话依据 |
| --- | --- | --- |
| moeru-ai/airi | adapt | 能力真实且有 752 个测试文件，但全栈 Vue + Electron，只吸收包级技术点 |
| Open-LLM-VTuber | reference | 后端 MIT 可读设计，**前端是自定义许可（商业嵌入需购买）**，素材另有条款 |
| HumanAIGC/OpenAvatarChat | defer | 数字人四路线真实存在，但硬依赖 torch+onnxruntime-gpu、零测试、权重许可 UNKNOWN |
| xszyou/Fay | reject | 代码 GPL-3.0 + **自带 SQLite/Chroma 记忆主库与 Python 常驻后台**，正面违反两条架构禁区；且全树无任何渲染实现 |
| met4citizen/TalkingHead | adapt | 纯前端 MIT npm 包，口型时间轴/流式打断/mood-pose-gesture 分层可直接借鉴；但**不是 VRM**、**无中文口型**、无测试无 CI、自带 avatar 含 CC BY-NC 禁商用 |
| lipku/LiveTalking | reference | 能力真实活跃，但必须 NVIDIA GPU + 权重靠网盘手download（许可 UNKNOWN）+ 开放 UDP 1-65536 |
| KlingAIResearch/LivePortrait | defer | 代码 MIT 但内置 InsightFace 权重仅限非商业研究，主权重许可未核验；写实照片驱动与原创 2D 角色路线错位 |
| TMElyralab/MuseTalk | reference | 实时口型架构有源码证据（`scripts/realtime_inference.py`），可借鉴思想；近一年提交停滞 |
| zhulin025/Codex-QQ-Skin | reference | 确为真实仓库（MIT），本质是 loopback CDP 渲染层皮肤注入器；只取"任务状态驱动视觉反馈"的交互细节，不作底座，且含 QQ/Codex 商标素材风险 |

## 2. 逐项记录

### moeru-ai/airi — adapt
- 核验：2026-10-12 | ref：tag `v0.12.0-beta.5`（2026-08-29）| 活跃度：`pushed_at` 2026-10-12（当天仍有提交）| star 50,319 | API 取回：yes
- 已实现（源码证据）：本地 ASR/TTS `packages/provider-inference/src/providers/local/sherpaw-transcription/`、`packages/stage-ui/src/libs/inference/adapters/kokoro.ts`；语音打断 `packages/core-agent/src/voice/interruption.ts`；口型 `packages/model-driver-lipsync/src/shared/wlipsync/vowel-driver.ts`；面部驱动 `packages/model-driver-mediapipe/`；渲染层 `stage-ui-live2d|three(VRM)|spine|mmd`；角色卡协议 `packages/ccc/`；桌宠形态 `apps/stage-tamagotchi/`（Electron）与 `apps/stage-pocket/`（Capacitor）。全树 6,766 文件、752 个 `*.test.*`
- 仅承诺未落地：README 的"Minecraft/Factorio 游玩、Neuro-sama 级"无对应成规模模块；桌面唤醒词仅有 ADR 草案
- 许可：代码 MIT；`packages/font-*` 各自带独立 OFL 类许可（xiaolai 的 LICENSE 路径 raw 取回 404 → `UNKNOWN`）；VRM/Live2D 演示素材许可未逐文件核验 → `UNKNOWN`
- Windows + React/Tauri 成本：中。全树 grep `tauri` 零命中；前端 Vue + UnoCSS，可复用的是与框架无关的 TS 包（lipsync / ccc / pipelines-audio / core-agent），Vue 组件层需重写
- 硬件与运行成本：低。浏览器/桌面 WebGPU/WASM 本地推理，无必须常驻 GPU 服务
- 最小可吸收能力 → 归属：lipsync vowel-driver 与 mediapipe 驱动思路 → ASTRYN（表达呈现）；`ccc` 角色卡编解码协议 → ASTRYN（角色配置可交换性）；打断/播放管线设计 → 归 AAOS（通用音频与任务能力），仅参照设计
- 覆盖方向：AI 陪伴、Live2D/VRM/3D、实时语音、AI VTuber、角色人格与记忆、桌宠/浮窗、主动式 Agent、多模态情境理解

### Open-LLM-VTuber/Open-LLM-VTuber — reference
- 核验：2026-10-12 | ref：tag `v1.2.1`（2025-08-26，附 Windows setup.exe）| 活跃度：`pushed_at` 2026-05-15，此后约 5 个月无提交 | star 14,067 | API 取回：yes
- 已实现（源码证据）：后端 299 文件，`src/open_llm_vtuber/asr/`（faster_whisper / sherpa_onnx / whisper_cpp / azure / groq / fun_asr 共 8 实现 + factory/interface）、`tts/` 22 模块、`vad/silero.py`、`agent/stateless_llm/`（ollama / llama.cpp / openai 兼容 / claude）、`agent/agents/{mem0_llm,letta_agent,basic_memory_agent}.py`、`mcpp/` 工具链、`live2d_model.py` 表情映射、`live/bilibili_live.py`、`conversations/group_conversation.py` 群聊多角色。浏览器侧 VAD 打断在 submodule `Open-LLM-VTuber-Web`（React 18 + Electron + `@ricky0123/vad-web`）
- 仅承诺未落地：主仓全树 grep `test` 零命中——**基本没有行为测试**（有 ruff/CodeQL CI）；后端仓自身无 SVG/桌宠能力
- 许可：后端 MIT（文末明示"Live2D 样例模型除外"，API spdx=NOASSERTION 因多 LICENSE 文件）；**前端仓为自定义 "Open-LLM-VTuber License 1.0"（Apache-2.0 + 附加条款：商业 SaaS/转售/嵌入商业产品需另行购买授权）**；`live2d-models/{shizuku,mao_pro}` 受 Live2D 样例数据条款约束
- Windows + React/Tauri 成本：低-中。React 前端与星栖栈最接近，但许可禁止未经许可的商业嵌入 → 只能读，不能搬
- 硬件与运行成本：低。CPU 可跑（faster-whisper/melo/pysherpa 均有 CPU 路径）
- 最小可吸收能力 → 归属：asr/tts/vad 的 factory+interface 抽象 → AAOS；`vad-web` 浏览器侧打断与口型事件流的协议形态 → ASTRYN 参考；Live2D 参数→表情映射表 → ASTRYN（表达呈现）
- 覆盖方向：AI 陪伴、Live2D、实时语音、AI VTuber、角色人格与记忆、多模态（弱）

### HumanAIGC-Engineering/OpenAvatarChat — defer
- 核验：2026-10-12 | ref：tag `0.6.0`（2026-04-17）| 活跃度：`pushed_at` 2026-07-31 | star 3,791 | API 取回：yes（逐 commit 日期因匿名配额耗尽 → UNVERIFIED）
- 已实现（源码证据）：树 494 文件。节点式会话引擎 `src/chat_engine/`；`handlers/asr/sensevoice`、`handlers/tts/{cosyvoice,edgetts,token_buffer}`、`handlers/vad/{silerovad/duplex_vad_handler.py, smart_turn_eou}`（全双工打断与轮次判定）；数字人四路线 `avatar/{liteavatar,lam/LAM_Audio2Expression,musetalk/MuseTalk,flashhead/SoulX-FlashHead}`；`service/rtc_service/` WebRTC；13 套 `config/*.yaml` 组合
- 仅承诺未落地：全树无测试文件（pyproject 有 pytest 依赖但无测试代码）；README 未明示 OS 与显存下限 → UNVERIFIED
- 许可：代码 Apache-2.0；子模块许可逐一核验为 MIT/Apache-2.0/BSD-2；**权重侧 UNKNOWN**（`scripts/download_models.py` 从 ModelScope/HF 拉取，MuseTalk 依赖的 SD-VAE 类权重常带非商用限制）；`pyproject` 钉死 `onnxruntime-gpu` + torch
- Windows + React/Tauri 成本：高。Python 服务端（FastAPI+aiortc+gradio）+ WebRTC 推流前端；数字人输出是服务端渲染的视频流，与 Tauri/React 本地可交互渲染不兼容；Docker/Linux 优先
- 硬件与运行成本：高。本地全功能需单卡 GPU
- 最小可吸收能力 → 归属：`smart_turn_eou` + `duplex_vad_handler` 的轮次判定/全双工信号 → AAOS；**LAM 的"音频 → ARKit 表情系数"输出格式**可作为星栖表情驱动的目标信号规范 → ASTRYN（自实现驱动，不搬权重）；node/handler 数据流编排 → AAOS
- 覆盖方向：实时语音、数字人驱动、AI VTuber、AI 陪伴、多模态（弱）

### xszyou/Fay — reject
- 核验：2026-10-13 | ref：无 tag/release，HEAD `d49f476`（2026-09-21）| 活跃度：约每月 1-2 次提交 | star 13,557 | API 取回：yes（releases 首次返回空，复查 403，另以 jsDelivr `versions: []` 交叉核验 → 判定确无 semver tag）
- 已实现（源码证据）：树 493 文件。`main.py`/`core/fay_core.py`/`core/interact.py`/`core/stream_manager.py` 会话编排；`llm/nlp_cognitive_stream.py`（requirements 实含 langchain/langgraph）；`asr/ali_nls.py`、`asr/funasr/`、`tts/`（edge_tts、azure speech）；**`core/memory_service.py`（386 行，get_schema/remember/search/get_reflections/get_user_profile 真实存在）**，且仓库内直接提交了 `memory/fay.db`、`memory/chroma_db/chroma.sqlite3`；`faymcp/` MCP 工具链；`ai_module/nlp_cemotion.py` 情绪；`config.json` 人设参数化（attribute + `interact.perception` 事件权重）
- 仅承诺未落地：README 头条"向上适配各种数字人模型技术"——**全树无任何渲染实现**（无 Live2D/VRM/3D/GLB/WebGL/Canvas 代码），渲染侧只有两份外部制作规范文档与 WebSocket 转发；口型靠 vendored `test/ovr_lipsync/`（Meta Oculus Lipsync 预编译 exe + 已提交的 `ffmpeg/bin/ffmpeg.exe`）离线生成，不在生产路径；无 pytest 套件、无 CI；README"完全开源，商用免责"与 GPL-3.0 义务不一致
- 许可：代码 **GPL-3.0**；权重素材 UNKNOWN（vendored exe 直接入库无许可声明、`qa.csv`/`gui/robot/*.gif` 素材许可未声明）；依赖风险高（chromadb + sentence_transformers 引入向量库这一第二套主数据面）
- Windows + React/Tauri 成本：极高。Python 常驻服务 + Flask/Element-UI 管理台 + PyInstaller；无 npm 包，Tauri/React 侧只能当 WebSocket 客户端
- 最小可吸收能力 → 归属：仅设计参照。`config.json` 的人设 + 感知事件权重表 → ASTRYN（人格参数化，本项目的 `AstrynCharacterProfile` 已用更强的结构化分节实现）；多通道打断与流式分发协议语义 → ASTRYN 事件信封参照
- **拒绝理由（架构性）**：其记忆/任务调度/DB/MCP/ASR/TTS/LLM 路由全部属于 AAOS 领地，移植即同时违反 `forbidden: [direct_aaos_database_writes, second_production_memory_store]`；GPL-3.0 又使闭源发行不可行；而 M0 最需要的渲染能力它根本没有
- 覆盖方向：AI 陪伴、实时语音（服务端）、角色记忆（第二套实现，属禁区）、主动式 Agent、多模态。不覆盖：渲染、桌宠、VTuber、叙事

### met4citizen/TalkingHead — adapt
- 核验：2026-10-13 | ref：tag `v1.7.0`（2025-12-08）+ HEAD 2026-10-11 | 活跃度：高（release 后仍持续合入社区 PR）| star 1,603、open issues 8 | API 取回：yes（树 104 路径 truncated=false + raw `modules/talkinghead.mjs` 4,895 行 + npm registry）
- **重要更正**：任务清单称其为"Three.js VRM 数字人库"，与源码不符。它加载 **GLB/glTF 全身 avatar（GLTFLoader + DRACO + Meshopt）+ Mixamo FBX 动画**，要求 avatar 自带 ARKit+Oculus viseme shape keys 与 Mixamo 兼容骨骼；VRM 不是输入格式，需自写转换脚本
- 已实现（源码证据，行号取自 `modules/talkinghead.mjs`）：文本驱动口型 `lipsyncGetProcessor(2814)`/`speakText(2856)` + `modules/lipsync-{en,de,fr,fi,lt,pt_br}.mjs`；外部音频驱动 `speakAudio(3106)`（可只给 `visemes/vtimes/vdurations`）；**流式与打断真实存在** `streamStart(3530)`/`streamAudio(3828)`/`streamInterrupt(3672)`/`pauseSpeaking(3492)` + `modules/playback-worklet.js`（AudioWorklet 分块 PCM）；表达四层 `setMood(2084)`/`setBaselineValue(2153)`/`poseTemplates(207)`/`gestureTemplates(281)`/`animEmojis(625)`/`playGesture(4596)`；注意力 `makeEyeContact(3885)`/`lookAt(4051)`/`touchAt(4131)`；**能量 VAD** `startListening(4320)`（AnalyserNode + silence/active 阈值，无 ASR）；二级动力学 `dynamicbones.mjs`；npm 包 `@met4citizen/talkinghead@1.7.0`，`type: module`，运行时依赖仅 `three ^0.180.0`
- 仅承诺未落地：**无中文口型**（全文 zh/chinese/pinyin 零命中），中文必须自写映射或由 TTS 提供音素时间戳；`scripts.test = "no test specified"`、`tests/` 只有手工 HTML、全树无 `.github/`；README 自述"一次只能处理一路流"
- 许可：代码 MIT；**素材混合且含不可商用项**——`avatars/brunette.glb` 为 **CC BY-NC 4.0（禁商用）**、Mixamo FBX 禁止跨团队再分发与 ML 训练、字体 OFL 1.1、IR 音频公共领域/CC-BY；README 明确警告把 avatar 下发到公开 web app 常违反条款；依赖 `three` MIT
- Windows + React/Tauri 成本：低。`constructor(node, opt)` 只接受一个 DOM 节点，无框架绑定 → React 用 `ref` + `useEffect` 挂载、`stop()` 卸载即可组合；Tauri 走 WebView2，WebGL/WebAudio 可用，无需后端
- 硬件与运行成本：纯前端，无 GPU 服务器、可离线
- 最小可吸收能力 → 归属：① 文本→viseme→时间轴的数据结构与"相邻同 viseme 以 0.7 时长衰减合并"算法 → ASTRYN（改造为 2D 嘴型序列）；② "外部 TTS 只交时间戳、渲染端自行决定口型"的接口分离 + 打断语义 → ASTRYN renderer seam 契约蓝本；③ 能量 VAD 三参数状态机 → ASTRYN 陪伴行为层（是否采信用户语音仍归 AAOS）；④ mood/baseline/pose/gesture/emoji 四层表达模板表 → ASTRYN 角色表达。**不吸收**：内建 Google Cloud TTS 路径（模型路由归 AAOS）、Mixamo/RPM avatar 资产
- 覆盖方向：3D 渲染（实为 GLB 非 VRM）、实时语音（口型/打断/能量 VAD）、数字人驱动、AI VTuber、AI 陪伴表达层

### lipku/LiveTalking — reference
- 核验：2026-10-13 | ref：tag `v2.0.4`（2026-06-20）+ HEAD 2026-10-09 | 活跃度：高 | star 9,855、open issues 238 | API 取回：yes（元数据）；**文件树因匿名配额 403 未取回**，178 个路径改由 jsDelivr flat 清单获得，故 `truncated` 标志与 blob SHA 不可得
- 已实现（源码证据）：`avatars/{wav2lip,musetalk,ultralight}/` + `base_avatar.py`（`put_msg_txt(127)`/`put_audio_frame(131)`/`flush_talk(185)`/`is_speaking(195)`/`notify(226)`/`inference(326)`）；`registry.py` 五类注册表（stt/llm/tts/avatar/output）；11 个 TTS 引擎文件真实存在；`streamout/{webrtc,rtmp,virtualcam}`；**本地 ASR+VAD 真实**：`server/asr_server.py` 用 funasr 加载 SenseVoice + `fsmn-vad`
- 仅承诺未落地：README-EN 仍宣传 **ernerf** 并附 demo，但当前 `avatars/` 已无该目录（"README 在讲、源码已无"）；`models/` 唯一内容是 `put models here.txt` → **权重一个字节都不在仓库**，全靠网盘手动下载；测试仅 1 个文件；`.github/` 下只有 FUNDING.yml
- 许可：代码 Apache-2.0；**权重 UNKNOWN**（外部网盘分发、仓内无 LICENSE/NOTICE）；依赖风险中（`edge_tts` 非官方调用微软服务，商用条款不保证）
- Windows + React/Tauri 成本：高。README 明示 Ubuntu 24.04 / PyTorch 2.9.1 / **CUDA 12.8**；服务端需开 TCP 8010 + **UDP 1-65536**；无 npm 包；Tauri 侧最多做个 WebRTC 播放窗，角色不可编程、表情不可与 React 状态组合
- 硬件与运行成本：必须 NVIDIA GPU 才能实时（README 性能表 wav2lip256@RTX3060=60fps、musetalk@3080Ti=42fps）
- 最小可吸收能力 → 归属：`registry.py` 的按名注册解耦 → 仅作 Host Adapter 接口形状参照（实际路由与权限归 AAOS）；`base_avatar.py` 的队列与事件点协议 → ASTRYN 事件语义蓝本（把视频帧换成 SVG/Canvas 状态）；SenseVoice+fsmn-vad 组合 → AAOS
- 覆盖方向：数字人驱动（服务端视频人脸）、实时语音、AI VTuber

### KlingAIResearch/LivePortrait — defer
- 核验：2026-10-13 | ref：**KlingTeam 链接 301 重定向到 `KlingAIResearch/LivePortrait`**；无 release/tag，最新 commit 2026-06-01 | star ≈19.2k | API 取回：yes
- 已实现（源码证据）：`src/modules/` 完整推理管线，内置 InsightFace ONNX 检测
- 许可：代码 MIT，但**内置 InsightFace 权重仅限非商业研究用途**；主权重许可未能核验 → `UNKNOWN`
- Windows + React/Tauri 成本：高（Python + CUDA sidecar 路线）
- 最小可吸收能力 → 归属：写实照片驱动与本项目"原创 2D 角色"路线错位；若未来做真人级形象，需先解决权重合规链
- 决定：defer —— 合规链不完整 + 路线不匹配

### TMElyralab/MuseTalk — reference
- 核验：2026-10-13 | ref：正确组织名是 **`TMElyralab`**（任务清单写作 tmelyralab，实为同一组织的大小写差异，仓库真实存在）| 最新 commit 2025-09-26（近一年停滞）| star 6.7k | API 取回：yes
- 已实现（源码证据）：实时路径确有源码 `scripts/realtime_inference.py` + `configs/inference/realtime.yaml`，非仅 README 宣称
- 许可：代码 MIT；主权重声明可商用；**自带测试素材为 NC**；API spdx=NOASSERTION 只是因为 LICENSE 文件拼接了第三方条款
- 最小可吸收能力 → 归属：实时口型的架构分层（音频特征→唇形区域合成→时序平滑）可借鉴思想 → ASTRYN 表达层；不接写实视频路线
- 决定：reference

### zhulin025/Codex-QQ-Skin — reference
- 核验：2026-10-13 | **仓库真实存在**：MIT，star 576，最新 release `v3.3.0 "CodexGF-Live 3.3.0"`（2026-08-11）| API 取回：yes
- 已实现（源码证据）：本质是对 Codex Electron 应用的 **loopback CDP 渲染层皮肤注入器**（`injector.mjs` / `renderer-inject.js` + `theme.json` 预设 + 真实测试），派生自 Fei-Away/Codex-Dream-Skin
- 仅承诺未落地：README 的"沉浸式女友/任务状态角色"完整落地**无法核验**（抓取期间网络阻断 → UNVERIFIED）；Windows 能力主要在闭源 `Setup.exe`，按纪律**不作为可移植开源能力**
- 许可：代码 MIT；含 QQ/Codex 商标与美术素材 → 素材侧不可复用
- 最小可吸收能力 → 归属：仅取"任务状态驱动视觉角色、提示反馈与皮肤化交互"的细节思路 → ASTRYN 呈现层交互参照
- 决定：reference —— 与其"不作系统底座"的定位一致

## 3. 空白方向补研（2026-10-13 追加）

首轮矩阵把方向 2、3、5、7、9 标为空白或薄弱。本节为补研结果，共 **43 个候选**（渲染 11、人格与记忆 6、叙事与多角色 8、语音 11、桌宠 7），工作记录在 `.project-local/runs/research/gap-{2-rendering,7-9-persona-narrative,3-5-voice-desktop}.md`。核验方式同上（GitHub REST + npm registry + jsDelivr/unpkg 源码 + 官方文档站）；`raw.githubusercontent.com` 在本机全程超时，故部分目录级证据标 UNVERIFIED。**没有任何候选在真实 WebView2/Tauri 里运行过**，全部为源码/文档级判断。

### 3.1 方向 2：2D 骨骼与 Live2D / VRM

| 候选 | 决定 | 关键事实（许可 / 接入） |
| --- | --- | --- |
| `guansss/pixi-live2d-display`（**上游实名，首轮清单写作 Guu3zz，更正**） | reject | npm 0.4.0 停在 2022-09-04，peer 只到 `@pixi/* ^6`，README 自述"for PixiJS v6" |
| Live2D fork 群（`@naari3/pixi-live2d-display@1.2.5` 等） | adapt（有条件） | MIT + `type: module` + peer `pixi.js ^8` + Cubism 5；仍需自备 `live2dcubismcore.min.js` |
| Live2D 官方 Cubism SDK for Web | reference | `LICENSE.md` 原文三层：Framework=Live2D Open Software License、**Cubism Core=Proprietary**、年营收 ≥ **10,000,000 JPY** 须签 Cubism SDK Release License（官方称"并支付对应许可费用"）；仓库内**不含** Cubism Core；Editor FREE 版参数 ≤30 / 纹理 2048×1 / 网格 ≤100，超限不可导出 |
| `pixiv/three-vrm` | reference | 3.5.5（2026-07-09）MIT，`VRMExpressionManager.setValue()` + `aa/ih/ou/ee/oh/happy` 预设正好是"九态 + 口型"的驱动形状；但 three r163 起**不支持 WebGL 1**（需 WebGL2），且 VRM 是 3D 换形态 |
| **Rive（`@rive-app/canvas` 2.44.2 / `@rive-app/react-canvas` 4.36.0）** | **adopt（P2 第一推荐）** | 全 MIT；`dist/index.js` 实测 `useEffect/useRef/.stop()/.delete()` 齐备并导出 `useRive / useStateMachineInput / useViewModelInstance`；`rive.d.ts` 有 `stateMachineInputs()` 与 `setNumberStateAtPath()`；ToS §D.4 "you own your User Content"，§C.6 仅营收 > USD $10M 强制 Enterprise。**唯一"运行时 MIT + 官方 React 绑定 + 状态机数据驱动"三者齐备** |
| Spine（`@esotericsoftware/*`） | reject | `spine-core` LICENSE 逐字要求"**each user must obtain their own Spine Editor license**"；Essential $69 / Professional $379 / Enterprise $2499+$379/席；npm `license` 字段为 `LicenseRef-LICENSE`，标 MIT 的 `@pixi/spine-pixi` 依赖专有 spine-core（上游已 archived） |
| DragonBones | reject | 官方 MIT 但最新 tag 仍 `V3.0.1`（版权行 2012-2013），无官方 npm，Pixi v8 只剩第三方端口 |
| PixiJS | reference | LICENSE 原文 MIT；8.22.0（2026-10-01）自述 WebGL & WebGPU。仅采纳 Live2D fork 时被动引入，纯 SVG 路线不需要 |
| `motion` / framer-motion 14.1.0（2026-10-09） | **adopt** | MIT + peer `react ^18||^19`，可直接给现有 SVG 角色做九态过渡，零许可闸门、零 GPU |
| GSAP | reference | npm `license` 逐字 **`Standard 'no charge' license`，不是 MIT**（纠正常见假设） |
| `lottie-web` | reference | MIT，但面向预编动画，不适合事件驱动的离散表情 |

**对 P2 的结论修正**：星栖的升级路线首选 **Rive 状态机驱动**（数据驱动、React 绑定官方、许可干净），其次 `three-vrm`（若走 3D），Live2D 仅在确有美术资源与营收规模允许时经 fork 接入；Spine/DragonBones 排除。**当前 M0 不引入任何一项**，只保留 `AstrynAvatarRenderer` seam（本轮已把 seam 真正接上，见 `docs/architecture/astryn-m0.risk-quality.md` R1）。

### 3.2 方向 7：人格一致性与角色记忆

| 候选 | 决定 | 关键事实与边界判定 |
| --- | --- | --- |
| SillyTavern Character Card V2/V3 | adapt（字段语义） | CCv2 规范仓**无 LICENSE（NOASSERTION）**；CCv3 仓 `kwaroran/character-card-spec-v3` MIT；ST 本体 **AGPL-3.0**（`world-info.js` 265KB / `group-chats.js` 88KB 为真实实现）。lorebook 存储与 token 预算**归 AAOS**，只借字段形状 |
| airi `packages/ccc` | adapt 设计 / defer 依赖 | MIT 但 `private:true` 未发布；`characterCardV3.ts` 用 `objectWithRest({}, unknown())` 保留未知键、`png.ts` 以 tEXt 关键字 `ccv3` 嵌入。零边界摩擦 |
| Letta（MemGPT） | reference | Apache-2.0；`schemas/block.py` 的 `label/value/limit/read_only/preserve_on_migration` + `memory_repo.py` MemoryCommit。**persona 块持久化在其 ORM/DB → 星栖内置即第二主库（禁区）** |
| mem0 | reject 运行时 / reference 词表 | Apache-2.0；`configs/prompts.py` 的 ADD/UPDATE/DELETE/NONE 事件真实存在；但自带 vector+graph 库，且**自行裁决"值不值得记"与本项目"只产 candidate、晋升 human-only"冲突** |
| generative_agents（Stanford） | reference | Apache-2.0，**2024-08-05 起停滞**；路径实为 `reverie/backend_server/persona/cognitive_modules/{retrieve,reflect,plan}.py`。检索与反思归 AAOS |
| 一致性评测：PersonaGym / CharacterEval / lost_in_conversation | adapt 探针形式 | 均 MIT。CharacterEval 为 1,785 段 / 77 角色 / 4 维 13 指标，但**数据是 GPT-4 合成、CharacterRM 权重许可 UNKNOWN**；PersonaGym 执行需付费 API。→ 评测**执行需授权且禁止落盘建库** |

**最值得吸收的单一设计**：把人格做成**受治理的状态块** `label + value + chars_limit + read_only + preserve_on_migration`，并把 `read_only=true / chars_limit=N` **直接渲染进系统提示本身**。归属切分：槽的存储、改写权限与版本化归 **AAOS**；槽内分节文本与人格语义归 **ASTRYN**。星栖侧的 `AstrynCharacterProfile` 已是后者的雏形，缺的是前者。

### 3.3 方向 9：交互叙事与多角色

| 候选 | 决定 | 关键事实 |
| --- | --- | --- |
| ink / inkjs | adapt（双状态通道） | **更正：官方 JS 端口是 `y-lohse/inkjs`（MIT, 2026-09-01），`inkle/inkjs` 是 5★ 陈旧仓**；`variablesState` / `state.ToJson()` / external function 白名单，与九态状态机可零冲突并存 |
| Evennia | reference | BSD-3-Clause；`typeclasses/attributes.py` 66KB + `objects.py` 145KB 实为 Django 持久属性库 → 只取 Account/Character/Session 三分与"一账号多角色"，**持久化面 reject** |
| Twine / Twison | reference（数据格式） | 官方 `klembot/twinejs` 是 **GPL-3.0（不可嵌入）**；Twison 实为 `lazerwalker/twison` MIT 且 2022-12-30 停滞，`passages{title,tags,text}` 无状态 |
| Fungus | reference | MIT，README 明示已转社区 `Fungus-Community-Edition/Fungus`（MIT, 2026-07-27）；Unity 绑定 + 测试薄弱，只取"台词 + 演出意图"节点形状 |
| BehaviorTree.CPP | defer | MIT，`blackboard.h` + decorators 齐全；但 tick 式共享变量与"事件单向写任务态"相抵，仅取作用域与节流概念 |
| pipecat / pipecat-flows / NVIDIA ACE | adapt 三件套 | pipecat **BSD-2**、pipecat-flows BSD-2 且 **archived（已并入 `pipecat.flows`）**、`NVIDIA/ace-controller` BSD-2；官方 ACE 文档：开源=Controller/Audio2Face-3D SDK/Maya/训练框架，**UE 插件 2.5 与 NIM 为 EULA 闭源** |
| 多角色编排（swarm / langgraph-swarm / autogen / ST 群聊） | reference | swarm MIT（自陈教学用）；**autogen 文档 CC-BY-4.0 + 代码 LICENSE-CODE=MIT，API 的 license 字段会误报 CC-BY-4.0**；ST 群聊 AGPL-3.0。**handoff 必须走宿主事件，角色间授权不得传染** |
| `microsoft/DialoGPT` | reject | **archived=True**、MIT、2022-10-17，判定过时成立 |

### 3.4 方向 3：Windows 本地流式 ASR / TTS / VAD / 口型

工作记录 `.project-local/runs/research/gap-3-5-voice-desktop.md`。**归属前提**：语音能力按架构属 **AAOS**（模型与音频服务），星栖只消费结果并决定"何时张嘴、何时被打断"的呈现时机。

| 候选 | 决定 | 关键事实（许可 / 真实能力） | 归属 |
| --- | --- | --- | --- |
| **sherpa-onnx 1.13.8** | **adopt（AAOS 首选）** | `sherpa-onnx/csrc/online-*.cc` + `silero-vad-model.cc` + `wasm/` 为真实流式实现；npm `sherpa-onnx-node` 含 `streaming-asr.js`/`vad.js`；Windows CI 有 4 条 `windows-*.yaml`；Apache-2.0。**逐包权重许可 UNVERIFIED** | AAOS |
| **silero-vad 6.2.3** | adopt（AAOS） | LICENSE 正文实为 MIT（徽章自相矛盾已记档）；模型随仓 `src/silero_vad/data/*.onnx`；README 原话"30+ms 块单线程 <1ms" | AAOS |
| **`@ricky0123/vad-web` 0.0.31** | **adapt 限定（ASTRYN）** | ISC（仓库 LICENSE 正文）+ AudioWorklet 分帧 + vendored silero v5/v6。**只用于呈现时机（何时停止说话动画/何时让角色闭嘴），是否采信用户语音由 AAOS 判定** | ASTRYN（时机）/ AAOS（采信） |
| Piper（`OHF-Voice/piper1-gpl` 1.8.0） | reference 暂缓 | **`COPYING` 正文是 GPL-3.0**（旧的 `rhasspy/piper` 才是 MIT，常见误传）；需常驻 `http_server`。但其 `voice.synthesize(..., include_alignments=True)` 给出**逐音素时间戳**，正是口型契约的蓝本；音色许可 UNVERIFIED | AAOS（引擎）/ ASTRYN（时间戳→口型） |
| **Kokoro** | adopt（AAOS） | README 原话 82M 参数、"Apache-licensed weights"；`kokoro-onnx` License 段"MIT / kokoro model Apache 2.0"；**npm `kokoro-js@1.2.1` Apache-2.0，包内 54 音色含 `zf_xia*`/`zm_yun*` 中文**，`tts.stream()` 分句流式。**更正：`raydium-io/kokoro-js` 不存在（404），实际作者是 hexgrad** | AAOS |
| whisper.cpp 1.9.5 | reference | `examples/stream/stream.cpp` 自称"quick-n-dirty … proof of concept"，默认 `step_ms=3000` → **秒级伪流式**；MIT；模型许可 UNVERIFIED | AAOS |
| faster-whisper 1.2.1 | reference（离线） | 文件树**无流式模块**；自带 `assets/silero_vad_v6.onnx`；实时需下游 `ufal/whisper_streaming` | AAOS |
| FunASR / SenseVoice | defer | 代码 MIT，但文件树与权重许可本次全不可得 → 明确 UNVERIFIED，不声称能力 | AAOS |
| **微软 Edge TTS** | **reject** | PyPI 自述调用 "Microsoft Edge's **online** TTS"（非本地、非官方支持）；npm `edge-tts` 许可为 **CC BY-NC-SA 4.0（禁商用）** | — |
| onnxruntime-web 1.30.0 + `@huggingface/transformers` 4.3.1 | adopt（运行时层） | MIT / Apache-2.0；**更正：仓库是 `microsoft/onnxruntime`，不是 `-web`** | AAOS |
| sherpa-rs 0.6.8 | reference | MIT；Tauri/Rust 侧候选路径（若语音走原生宿主） | AAOS |

所有首包延迟与 RTF 数值均 **UNVERIFIED**（无本机实测）。

### 3.5 方向 5：桌宠 / 悬浮窗 / 托盘（Windows + Tauri 2）

基准：`tauri 2.12.3` + `@tauri-apps/api 2.12.3`，**文档与源码双层确证，零运行验证**。

**确证可用的能力**：`transparent`（含 `tauri-runtime-wry` 的 `is_window_transparent`）、`decorations:false`、`alwaysOnTop`、`setIgnoreCursorEvents`（`window.ts:2030` + `window/mod.rs:2357`，需 `core:window:allow-set-ignore-cursor-events` 权限）、`startDragging`（2050/2366）、多窗口、`TrayIconBuilder`（`tray/mod.rs:203`，含 `set_visible`/`rect()`）、global-shortcut 2.4.1、single-instance 2.5.3（**必须最先注册**）、autostart 2.7.0、`skipTaskbar`、`windowEffects`。

**纠正两条会被直接照抄的误解**：

- `acceptFirstMouse` 是 **macOS 专用**，语义是"未激活窗口的首次点击是否落进 webview"，**不是鼠标穿透**。
- `visibleOnAllWorkspaces` 文档与源码均标注 **Windows / iOS / Android: Unsupported**。

**未确证**：鼠标穿透无声明式配置项（只有运行时 API）；Windows DWM 合成、hit-test、多屏 DPI、WebView2 上 WebGPU/AudioWorklet/权限与常驻成本；`noRedirectionBitmap` 落点。

| 桌宠参照 | 真相 | 决定 |
| --- | --- | --- |
| **CoPet（MIT）** | **唯一确证的真实 Tauri 2 桌宠**：`tauri.conf.json` 内 pet/settings 双窗，`transparent` + `decorations:false` + `skipTaskbar` + `focusable:false`；`window_placement.rs` 仍用 Win32 `SetWindowPos(HWND_TOPMOST)` 补强置顶；`src-tauri/src/agents/adapters/*.rs` 与星栖"事件→角色反应"同构 | **reference（只读参照，最对口）** |
| BongoCat（Apache-2.0） | 2.3.0 **已无 tauri 路径**，改用 `windows` crate 的 DirectComposition/D3D11 + `tray-icon`/`muda`/`cargo-packager` 原生叠加层 | reference（原生路线证据） |
| tiny-roommate | 有 Tauri 2 透明置顶配置，但**无 LICENSE → 不可复用** | reject（许可） |
| WindowPet | 实为 **Tauri 1.5.4 + Phaser**，不可当 2.x 证据 | reject |
| Shimeji-ee | `mouse07410` 地址**未能证实存在**；可核实的只有 `gil/LavenderSnek` 镜像与 Kilkakon 自拟 BSD 条款，Java + Windows-only | reference（不可依赖） |
| `ram-on/SurfaceDetector` | **未能证实存在** | 剔除 |
| Open-LLM-VTuber 桌宠模式 | 两仓只有 README 截图 `assets/i4_pet_desktop.jpg`，**无实现路径 → 宣称未证实** | 记为未证实 |

**归属结论（P2）**：走"**宿主（AAOS / 宿主 shell）提供窗口、托盘、穿透、单实例、自启与权限；星栖只提供角色内容与口型/打断呈现时机**"。若届时 AAOS 没有窗口宿主，星栖侧也只能建"**呈现运行时**"——复用同一 `src` 渲染树，不新增前端、不新增存储、不新增模型路由——且必须先有一条 DECISIONS 记录 + `PROJECT_CONTRACT.yaml` 的 architecture 段同步 + 单独授权。本轮 `NOT_EXECUTED`。

### 3.6 补研的未核验项（不粉饰）

- GitHub API 匿名配额在十余个仓库后归零（403）：各 fork 的 star/最近提交、`rive-app/rive-react` README、`three-vrm` LICENSE 全文（仅 spdx 字段）为 UNVERIFIED。
- `raw.githubusercontent.com` 全程 ECONNRESET，改走 api.github.com contents/license + unpkg + cdn.jsdelivr；因此 CharacterEval 全树、CharacterRM 权重许可、PersonaGym 目录树、Fungus `Assets/**`、pipecat `src/pipecat/flows/` 为目录级 UNVERIFIED。
- Live2D PRO 价格与 Release License 费用细则、Rive 免费计划额度与三档运行时后端归属、VRM 1.0 meta 许可字段、Spine 跨版本兼容矩阵、DragonBones 编辑器条款：UNVERIFIED。
- `normanb/cog-agent-chat-with-voice`、"Linecraft"、`aiwaves-cn/narrative_control`、RoleBench、CoSER、CPv2、plumpr/space、Endnight、Inworld 官方 SDK 仓、NVIDIA Avatar Connector：404 或未定位，按不可用处理。
- **无一项在真实 WebView2 / Tauri 环境运行验证过**；所有"接入成本低"的判断都是源码与文档级推断。

## 4. 十类方向的首轮覆盖情况

| 方向 | 本轮覆盖 | 缺口与后续候选（均未深度核验） |
| --- | --- | --- |
| 1 AI 陪伴 | airi、OLVT、Fay | 商业闭源产品未评估；SillyTavern 待查 |
| 2 Live2D/VRM/2D 骨骼 | airi、OLVT + **补研 11 项**（见 §3.1） | 已收敛：P2 首选 Rive 状态机驱动，次选 three-vrm；Live2D 经 fork 且受 Cubism Core 专有许可与 Release License 约束；Spine/DragonBones 排除 |
| 3 实时语音 ASR/TTS/VAD/打断/口型 | airi、OLVT、OAC、LiveTalking、TalkingHead + **补研 11 项**（见 §3.4） | 已收敛：AAOS 侧首选 sherpa-onnx（真流式 + Windows CI）+ silero-vad + Kokoro（Apache 权重含中文音色）；星栖侧只取 vad-web 的呈现时机与 Piper 的音素时间戳口型契约。Edge TTS 因 CC BY-NC-SA 与非官方调用排除 |
| 4 数字人/人物驱动 | OAC、LiveTalking、LivePortrait、MuseTalk | 写实路线合规链普遍不完整 |
| 5 桌宠/浮窗/托盘 | airi `stage-tamagotchi`（Electron）+ **补研 7 个参照 + Tauri 2.12.3 能力双层确证**（见 §3.5） | 已收敛：透明/无边框/置顶/穿透 API/拖拽/托盘/单实例/自启在 2.x 文档与源码中均确证；`acceptFirstMouse` 是 macOS 专用、`visibleOnAllWorkspaces` 在 Windows 不支持（两处常见误解已纠正）。真实 Tauri 2 桌宠参照只有 CoPet（MIT）；BongoCat 2.3.0 已弃 Tauri。**零运行验证**，归属定为"宿主提供窗口，星栖提供角色内容" |
| 6 AI VTuber | airi、OLVT、OAC、LiveTalking | 覆盖充分 |
| 7 角色人格一致性与角色记忆 | OLVT、airi、Fay（禁区）+ **补研 6 项**（见 §3.2） | 已收敛方向：人格做成受治理状态块（label/value/chars_limit/read_only/preserve_on_migration）；存储与改写权限归 AAOS，槽内语义归 ASTRYN。评测执行仍需授权 |
| 8 主动式 Agent / 情境感知 | airi core-agent、Fay scheduler | 事件驱动与授权边界的具体实现均未深入；须与 AAOS 权限面合并评估 |
| 9 游戏 NPC/交互叙事/多角色 | OLVT 群聊 + **补研 8 项**（见 §3.3） | 已收敛：叙事状态与角色状态走双通道（ink `variablesState` / `ToJson()`），handoff 必须经宿主事件；Evennia/Twine 的持久化与 GPL 面排除 |
| 10 多模态与受控桌面协作 | airi screen-capture/mediapipe | 受控性与授权模型未评估，须由 AAOS 主导 |

首轮覆盖结论：九仓足以支撑 M0 的路线判定（原创 2D + seam），但方向 2、7、9 是明确空白，P2/P4 前需补做；不得对外声称已深度验证所有项目。
