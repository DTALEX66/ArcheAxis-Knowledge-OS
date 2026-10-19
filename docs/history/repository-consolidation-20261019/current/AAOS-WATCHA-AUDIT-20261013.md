# 观猹报告：星环项目增量审计（2026-10-13）

基线 be79ff90。审计及候选登记；上游代码吸收、安装、真实供应商调用 NOT_EXECUTED。原报告只读保留在 Owner 指定的 Record 路径，报告建议不是执行授权。本轮不修改 WORK-LAB、DESIGN-LAB、ASTRYN 或独立 UI 会话。

## 纠正与冲突

- 71候选混合开源软件、商业服务、闭源产品和体验参考，不能称为71项开源组件。本轮阅读完整报告，重点核查官方入口；原报告2932条目录/72详情的原始响应未提供，数量 UNVERIFIED。
- “LongCut需要先补真实ASR”已过时：现有 WAV/MP3/MP4 已有实际 ASR、时间定位、重解析和重启证据。增量应是章节/问题回到已有时间段。音轨识别仍不等于视频视觉理解。
- 普通保存、用户入库选择、资料处理、模型能力状态已有实现；页面建议不能当源码缺失。避免重复入口、模型中心、主库和学习引擎。
- OpenMAIC、DeepTutor、WeKnora、Crawl4AI已有研究或登记，继续原身份。Crawl4AI历史路径不等于正式宿主资格；HTML已有Trafilatura。
- Minta只可产生诊断发现：旧不等于失效，模型置信度不等于准确性。发现可驳回，不自动删改、入库或更新掌握状态，不借此解冻六项机制。
- OpenMAIC当前README明确1.2起需要常驻Node/PostgreSQL；整体引入与唯一Rust写者重叠。未来仅评估课程资产/局部renderer合同。
- OpenViking主体AGPL-3.0；CLI/examples的其他许可不能泛化。Minta开放核心和高级资产分区、Thesis Skills第三方规则权利都需固定版本后核验。
- KaaS是LLM编译Markdown Wiki，不是直接修复当前向量检索的插件。生成页只能是可重建候选投影。CocoIndex官方示例含Postgres，不证明所有用法必须它，也不授权建立第二outbox。
- Sitor/CauseLink/LongCut等产品未证明开源许可或稳定API，仅体验参考。博查/Exa/Parallel是服务候选，不能计入开源已吸收数量。
- 原报告对其他项目的当前定位仅作外部说法，本轮未核实其源码或变更其权威。

## 后续候选任务

| ID | 增量/供体 | 复用与验收 |
|---|---|---|
| WA01 | 精确来源引文、引用完整性；Thesis Skills确定性规则 | 复用research/version/hash/locator；保存实际阅读快照。引用存在与论点正确分离；原文变化使旧定位失效；普通保存不阻塞。先补Core外发协议边界 |
| WA02 | 过期/冲突/重复只读诊断；Minta机制 | 复用版本/用户选择。合成反例测试、发现可驳回、零自动删改/入库；不读取私人Agent记忆、不实现冻结机制 |
| WA03 | 连贯学习旅程；Sitor/CauseLink/LongCut/拾级体验 | 复用answer/retest/FSRS及ASR锚点；错因是假设可纠正，问题定位原材料，无来源不伪造。呈现由独立UI任务承接 |
| WA04 | 搜索基准合同；博查/Exa/Parallel | 同公开查询比较正文/日期/去重/用量成本，未知保留UNKNOWN；先完成WA01及外发控制，再择必要渠道。本轮不付费实跑 |

这些是已登记后续候选，不自动成为活动队列，不覆盖当前修复与安装资格优先序。实际代码吸收前必须锁revision、许可快照、接口、回退及正式入口验证。

## 整份报告按归属处置

- 星环近期/体验：Minta、Thesis Skills、Sitor、CauseLink、拾级、LongCut、E2N、Heptabase、Ponder。前两项核查了开源入口；其余不新增依赖。
- 既有身份：WeKnora、OpenMAIC、DeepTutor、Crawl4AI，避免重复登记、重跑历史任务。
- 星环未来：Arco、Semantica、Agentero、KaaS、CocoIndex、MineContext、OpenViking、Fish Audio、雾象，见蓝图补充。
- 星环观察/服务：Blinko、WiseMindAI（整个平台重复，仅对照）；博查、Exa、Parallel（服务）。
- 跨项目反馈：EditHere/IntentKit仅参考版本+区域+意图；不复制代码。EditHere的Noncommercial边界需固定许可核验。
- WORK-LAB专属：Nuto、Sesame、Pilion、port22、CoModel、TinyFire、Paseo、BrowserOS Neo、ModelBench、SkillWard、OneCLI、TokenArena、Chops、Agent Deck、SkillKit、Dify，不成为星环运行依赖。找产物不授权读取私人会话。
- DESIGN-LAB专属：Motion Face、DFCine、EasyPick、FRAMEBAIT、IntentKit、Say Action、gtrk、Recraft、Fal、OpenStory、DeckForge、video-shotcraft、OpenMontage、Sinew、QuiverAI、OpenPencil、OpenStoryline、Refore、Design Arena、Hitem3D、Meshy、Tripo，不部署；未来仅接授权资产/工程及rights/hash回执。
- ASTRYN专属：有伴儿、NEKO、OpenPets、EnSoul、OpenDesktop-Pet、AIRI，不在本项目重建角色系统。

## 官方查证入口

2026-10-13公开README/文档核查，不是全源码审计或本机运行证明。上游固定revision均UNVERIFIED，吸收时再锁定。

[Minta](https://github.com/xinchen03/minta)、[开放核心边界](https://github.com/xinchen03/minta/blob/main/OPEN_SOURCE_BOUNDARY.md)、[Thesis Skills](https://github.com/quzhiii/thesis-skills)、[OpenMAIC](https://github.com/THU-MAIC/OpenMAIC)、[OpenViking](https://github.com/volcengine/OpenViking)、[CocoIndex](https://github.com/cocoindex-io/cocoindex)、[官方许可说明](https://cocoindex.io/terms-of-use/)、[KaaS](https://github.com/bybit-exchange/kaas)、[EditHere](https://github.com/Inginnng/EditHere)、[CauseLink](https://linusshyu.dev/causelink/)、[LongCut](https://www.longcut.ai/)、[Parallel官方文档](https://docs.parallel.ai/introduction)。

内部依据：当前活动指针、CONVERSATION-CLOSURE-20261013、D22-18-FORMAT-READBACK、OSS-REUSE-DECISIONS、CAPABILITY_ABSORPTION_REGISTRY、OPEN_SOURCE_REGISTRY_V2。历史ASR未测记录保留原SHA，不修改成新PASS。

原报告SHA-256：61042B05BDDECE774F226BE8EC0F26C801D5FB09F9C89852AD654809A5C45EA6
