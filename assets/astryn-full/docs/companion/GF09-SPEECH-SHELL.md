# GF09 声音字幕与口型接口外壳（交付说明）

任务包 `ASTRYN-COMPANION-20261013` · 分支 `feat/astryn-learning-companion-v1` · 依赖 GF01（档案 v3 迁移）/ GF04（宿主端口纪律）/ GF08（设置面与槽位呈现）。

本卡三条 work 的落点：①麦克风、音色、朗读、字幕、音量与停止的前端配置及状态（设置页「声音」节重做）；②预留 ASR、TTS 与音频主时钟、utterance、chunk、viseme 字段及可替换适配器（`contracts/speech.ts` 合同提案 + `src/speech/playback.ts` 回放外壳）；③首期没有真实语音端口时保持文本模式——运行按钮明确禁用并标注 `BLOCKED_BY_HOST_CONTRACT`（BE01），不播放任何假语音。

## 1. 交付物

| 路径 | 内容 |
| --- | --- |
| `contracts/speech.ts` (new) | 任务包 `speech_optional` 原文冻结：state `FRONTEND_FIELDS_NOW_RUNTIME_OPTIONAL`、12 字段（session_id / utterance_id / chunk_id / sequence / audio_ref / sample_rate / start_offset_ms / viseme_events / subtitle_segments / locale / provenance / end_of_utterance）、3 条规则（audio clock is master；cancel stops audio/subtitles/mouth；no phoneme events means basic amplitude mouth only）、formalization_gate 4 项原文、合同属主 `AX-HOST-20261013/BE01`；四能力可用性模型（缺省全不可用 + `HOST_CONTRACT_MISSING`，reason 引用 BLOCKED_BY_HOST_CONTRACT）；口型三态 `resolveMouthMode`（无音频→文本帧口型；有音频无音素→基础口型；有音素→viseme）；`AstrynSpeechPort` 可替换适配器接口（protocol / providerId / evidenceLevel / availability / speak，speak 接 AbortSignal）。 |
| `src/speech/playback.ts` (new) | SpeechPlayback 回放外壳（§3 音频主时钟与打断设计）：时钟单调不减（回退 tick 被忽略）；字幕 = 区间∩时钟投影、结束保留最后一条、停止即清空；ingest 四守卫按序 NOT_SPEAKING→FOREIGN_SESSION→STALE_UTTERANCE→OUT_OF_ORDER；stop 原子复位（信号中止 + 状态回 idle + 通知）；无端口 speak 拒发 `NO_PORT` 且状态保持 idle（不播放假语音、不创建 utterance）。 |
| `contracts/character.ts` (modified) | 档案 schema **v3**：`voiceStyle` 增 `microphone`(默认 false，采集归宿主权限面) / `subtitles`(默认 true) / `volume`(0–1 clamp)；迁移注记新增 `MIGRATED_V1_TO_V3` / `MIGRATED_V2_TO_V3`（v2→v3 保留既有偏好与 profileRevision）。 |
| `src/presentation/companion-settings.tsx` (modified) | 声音节重做：4 能力徽章（麦克风 / 语音识别 / 朗读 / 音频播放，缺省全「未接」）+ 未接通说明 + 音色（禁用下拉，目录归宿主）+ 语速 / 音高 / 音量滑块 + 朗读 / 麦克风 / 字幕偏好开关 + 运行时按钮（试听一段 / 停止朗读 / 按住说话，未接通一律禁用并挂原因 title）+ 口型模式行 + 朗读状态行 + 字幕行 + 通知行；「朗读偏好已开启但端口未接通」显式降级说明。 |
| `src/presentation/companion-shell.tsx` (modified) | 新 prop `speech?: AstrynSpeechPort \| null`；回放控制器经 useMemo 绑定 sessionId、订阅快照；不构造任何语音/模型端口（同 GF08 纪律）。 |
| `src/index.ts` (modified) | 导出 `consumeSpeechChunks` / `createSpeechPlayback` / `readSpeechAvailability` 与四个类型（SpeechIngestResult / SpeechPlaybackController / SpeechPlaybackSnapshot / SpeechSpeakResult / SpeechStopResult）。 |
| `dev-host/app.tsx` (modified) | 「语音接口外壳」区：提案 state、12 字段、3 规则、合同属主、未接通原因实测可读；边界清单新增语音条目。 |
| `tests/speech/speech-shell.test.ts` (new, 11) | 提案逐字（12 字段 / 3 规则 / 4 门控项 / BE01）；口型三态；未接通可用性；NO_PORT 拒发；可用性读取失败→UNKNOWN；ingest 四守卫 + 停止复位；字幕时钟投影（含回退 tick）；viseme + 结束保留；流中停止（迟到块静默丢弃）；完整消费（SYNTHETIC 标注）；订阅通知与空文本拒绝。 |
| `tests/presentation/voice-settings.test.tsx` (new, 3) | 未接通：4 徽章 data-available=false、说明含 BLOCKED_BY_HOST_CONTRACT+BE01、三个运行按钮与音色禁用（title 指原因）、口型「文本帧」、页面无 audio 元素；偏好可编辑（字幕 / 麦克风 / 朗读开关、音量标签）；接通形态（合成端口）：徽章点亮→试听→字幕行→运行中→基础口型→停止→字幕消失回文本帧。 |
| `tests/companion/character-profile.test.ts` · `profile-store.test.ts` · `tests/presentation/companion-settings.test.tsx` (modified) | v1→v3、v2→v3 迁移与音量 clamp 断言；GF01 种子注记更新；GF09 声音节断言替换旧「朗读」节。 |

## 2. 验收对照（任务包 GF09 卡）

| 验收项 | 状态 | 证据 |
| --- | --- | --- |
| 未接语音明确禁用 | PASS | 设置页 4 能力徽章全「未接」（浏览器实测 data-available="false"）；试听 / 停止 / 按住说话 / 音色选择全部 disabled 且 title 挂未接通原因（单测 + 浏览器实测）；朗读偏好开启时显式降级文案「当前保持文本模式，不播放任何语音」（浏览器实测开关往返）；无端口 speak 返回 `NO_PORT` 且状态保持 idle（单测）。 |
| 缺音素时间戳仅标基础口型 | PASS | `resolveMouthMode` 三态单测：无音频→text-frames；有音频无 viseme→basic-amplitude；有音素→viseme。反证：移除 viseme 分支后 speech-shell 2 条转红，恢复全绿（§4）。 |
| 停止动作与将来的音频、字幕、嘴形同步 | PASS（外壳层） | stop 原子复位：signal 中止 + 状态回 idle + 字幕清空 + 口型回文本帧 + 通知文案；流中途停止后迟到块被守卫静默丢弃（可控端口单测）。M0 无真实音频时钟，同步语义由合成时钟单测钉住（tick 投影断言，见 §3.2 / §3.3）。 |
| 不播放假语音 | PASS | NO_PORT 拒发路径不改变 idle 状态、不创建 utterance、不请求麦克风；页面无 `audio` 元素（浏览器实测）；反证：拒发时置 speaking 后测试转红，恢复全绿（§4）。 |
| work① 前端配置与状态 | PASS | 见 §1 `companion-settings.tsx` 行（麦克风 / 音色 / 朗读 / 字幕 / 音量 / 停止六项齐备）。 |
| work② 字段与可替换适配器 | PASS（提案在 ASTRYN 侧冻结，正式化门控 4 项待 BE01） | `contracts/speech.ts` 原文 + `ASTRYN_SPEECH_FORMALIZATION_GATE`；适配器经 `AstrynSpeechPort` 可替换。 |
| work③ 首期保持文本模式 | PASS | 未接通原因常驻设置页与 dev-host；运行按钮禁用；口型行标注「文本帧口型（无音频）」。 |

## 3. SpeechPlayback 提案与音频主时钟设计

### 3.1 合同提案（任务包原文，逐字冻结于 contracts/speech.ts）

- state：`FRONTEND_FIELDS_NOW_RUNTIME_OPTIONAL`。
- 字段（12）：session_id / utterance_id / chunk_id / sequence / audio_ref / sample_rate / start_offset_ms / viseme_events / subtitle_segments / locale / provenance / end_of_utterance。
- 规则（3）：audio playback clock is master；cancel stops audio/subtitles/mouth；no phoneme events means basic amplitude mouth only。
- 正式化门控（4，归 BE01）：发布 schemas/DTOs；绑定确切原生路由；正负合同测试；版本与校验和一致。

### 3.2 音频主时钟

- 唯一时间源：`tick(clockMs)`（由宿主/播放器喂入）；时钟单调不减——回退 tick 被忽略（单测：1500 后喂 1000，读数仍 1500）。
- 字幕 = `[startMs, endMs) ∩ clock` 的投影；utterance 结束保留最后一条（finishUtterance），停止则清空。
- 口型模式由「有无音频 / 有无音素」决定，与时钟同拍；M0 呈现层仍是 GF03 文本帧口型（expressionFrame 驱动），viseme 选帧是未来口型驱动器——本卡只交付合同面与选择函数。
- 序列守卫：`sequence` 必须严格递增（`OUT_OF_ORDER`）；外来会话 / 过期 utterance / 非朗读中的块一律拒收（`FOREIGN_SESSION` / `STALE_UTTERANCE` / `NOT_SPEAKING`）。

### 3.3 打断（停止 / 取消）设计

- `stop(reason)` 原子复位：中止 AbortSignal → 状态 idle → 字幕 / 口型 / utterance 清空 → 通知「音频订阅、字幕与嘴形已同步复位」；
- 消费循环每块先查 signal（aborted 即返回，不 ingest）；
- 迟到块在 idle 态被 NOT_SPEAKING 守卫静默丢弃——与 GF07「停止后晚到事件被 SETTLED_REQUEST 丢弃」同一纪律；
- `user`（按钮）/ `cancel`（程序性）/ `dispose`（视图卸载）区分原因，不改变复位语义。

### 3.4 未接通语义（偏好 vs 运行时）

- `unconnectedSpeechAvailability()`：四能力全不可用、`failureCode: 'HOST_CONTRACT_MISSING'`、reason 含 `BLOCKED_BY_HOST_CONTRACT` + `BE01`；
- 设置页把「偏好」与「运行时」分开：偏好（朗读 / 麦克风 / 字幕开关、音量）可预先编辑并进档案 v3；运行时（试听 / 停止 / 按住说话）在未接通时禁用（title 给出原因）；
- 不播放占位语音、不生成假音频、不请求麦克风（边界扫描 `tests/boundary/no-sensitive-apis.test.ts` 钉住 `getUserMedia` / `mediaDevices` / `MediaRecorder` 等字面量不在 src / contracts / dev-host）。

## 4. 门禁与封存（GF09 终局）

- 命令：`bash .project-local/runs/gate-chain.sh`，日志 `.project-local/runs/gate-20261013-235531.log`：**lint=0 typecheck=0 test=0 build=0 record=0 anchors=0**（六阶段全 0，一次通过）。
- 测试：**36 文件 / 319 通过**（GF09 新增 14：speech-shell 11 + voice-settings 3；档案 v3 迁移与音量 clamp 另 +2；此前 GF08 终局为 34 文件 / 303 通过）。
- 封存收据 `docs/verification/gates.json`：源码树 **100 文件**（+4：contracts/speech.ts、src/speech/playback.ts、tests/speech/speech-shell.test.ts、tests/presentation/voice-settings.test.tsx），树哈希 `8027cfe9186a9c4d265a8074faca1b2933c95f9b5c6f3641245a582bae0771ff`；`allGreen: true`；`git.head` `e27cec3`（GF09 提交前的分支头）。
- 构建产物（实测磁盘字节）：`index-P5YjlFx8.js` 295,268 B，sha256 `03e4f907786bb3c3811038ff7109106005a63d9c9521a61fd0f91652c4925574`；`index-P5YjlFx8.js.map` 845,331 B，sha256 `c4f7ad965d8dd56f53eaf963f373804476d58d88f54c27f60be6c7051cfdba06`；`index-PqCch4VI.css` 11,670 B（与 GF08 终局相同，本卡无新 CSS），sha256 `3e8d7372f43837ecad034ac17102b90fa1a51fa5d13dddb4dfc680fe3ff6ec64`。
- 反证（test falsification；两份被改字节均从备份还原并复验 sha256 与原值一致，收据树哈希事后不漂移）：
  ① 移除 `resolveMouthMode` 的 viseme 分支（有音素也回基础口型）⇒ `tests/speech/speech-shell.test.ts` `2 failed | 9 passed`；还原后全绿。
  ② NO_PORT 拒发时置 `status:'speaking'`（伪造播放态）⇒ 同套件 `1 failed | 10 passed`；还原后全绿。

## 5. 浏览器实测（Dev Host，DOM 读数 + 截图）

`VITE_ASTRYN_ALLOW_SYNTHETIC=1` 起 Vite（127.0.0.1:5261，日志 `.project-local/runs/dev-gf09.log`），实测后按 netstat PID 10844 终止、端口释放：

- 「语音接口外壳」区：state=FRONTEND_FIELDS_NOW_RUNTIME_OPTIONAL；12 字段与 3 规则按任务包原文渲染；未接通原因含 BLOCKED_BY_HOST_CONTRACT + BE01。
- 设置页声音节：4 能力徽章 `data-available="false"`（麦克风 / 语音识别 / 朗读 / 音频播放全未接）；`astryn-voice-sample` / `astryn-voice-stop` / `astryn-voice-mic-hold` / `astryn-voice-style` 全部 disabled，title 给出未接通原因；口型行「文本帧口型（无音频）」；运行状态「空闲」；`document.querySelectorAll('audio').length === 0`。
- 偏好降级：勾选「朗读（偏好）」⇒ `astryn-voice-preference-note` 出现「当前保持文本模式，不播放任何语音」；取消勾选 ⇒ 提示消失。
- 控制台：3 条（vite debug×2 + React DevTools info），**0 错误**。
- 截图：`.project-local/artifacts/m0-browser-04-gf09-voice-settings.png` 41,244 B，sha256 `10c735670c717a7138bc69af68b964e58f39ce9f6999f32f4413caa97258d487`（未接徽章 / 禁用按钮 / 文本帧口型 / 空闲状态可见）。

## 6. 诚实边界

- **真实语音运行时未接通（BLOCKED_BY_HOST_CONTRACT）**：ASR / TTS / 音频主时钟归宿主（BE01 未登记）；本卡交付的是前端字段、设置面与回放外壳，不等于语音可用。
- **音频主时钟在 M0 无真实时钟源**：tick 由测试 / 未来宿主喂入；字幕投影与停止语义用合成时钟钉住，未与真实音频对齐验证。
- **口型仍未驱动渲染**：M0 呈现层保持 GF03 文本帧口型；`resolveMouthMode` 与 viseme 字段是未来口型驱动器的合同面。
- **voiceStyle 偏好只在档案里**：没有运行时行为消费 `enabled/subtitles/volume`（端口未接通）；「朗读偏好开启」的降级说明是显式文案，不是功能。
- **dev-host 语音区接线无测试载体**（与 GF05–GF08 同一盲区，仅浏览器实测）。
- **截图证据只证明未接通形态**：接通形态（合成端口按钮流）仅有单测，无浏览器截图。
- **「停止与音频/字幕/嘴形同步」是外壳语义**：在无真实音频的 M0，同步由单一控制器状态机保证；未来接入真实播放器时，播放器必须服从该状态机（端口契约已含 AbortSignal），否则需重新验证。

## 7. 回滚

`git revert` GF09 提交（分支 `feat/astryn-learning-companion-v1` 上单个提交）。新增文件 `contracts/speech.ts`、`src/speech/playback.ts`、`tests/speech/speech-shell.test.ts`、`tests/presentation/voice-settings.test.tsx`；其余为既有文件修改：档案 schema 升至 v3 为**增量**（新字段有默认值，迁移注记新增两种——回滚后按既有 v2 解析路径恢复）；设置页声音节为行为替换（回滚恢复 GF01 旧声音节）；无迁移脚本、无宿主侧写入。
