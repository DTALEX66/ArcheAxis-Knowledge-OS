# ASTRYN M0 测试审计报告（第四轮 A 队列）

日期：2026-10-14（Asia/Shanghai）
方法：两路只读子智能体并行深审（UI/适配层 22 个测试文件；核心逻辑 8 个，合计 30 个），我自己逐项复核产品行为并执行修复。
判据：**每条断言必须能对其名称所述命题失败**——永远通过的空洞断言、与名称不符的正文、弱反例都算缺陷；缺陷只算测试质量问题，不算产品缺陷，除非在源码中复核出真实行为错误。

## 结论

- 发现 **23 项测试质量问题**（19 个文件），全部为测试自身缺陷；**未发现产品行为缺陷**。
- 过程中复核的两处"疑似产品缺陷"经读源码确认为有意设计：SSE `flush` 在流结束派发残留半行（完整性由下游 `JSON.parse` → `MALFORMED_STREAM` 把关，`src/adapters/sse.ts:33-44`）；取消分类顺序（`openai-compatible.ts:206` `signal.aborted` 先于 `streamError`/`MALFORMED`）。
- 桥接层 `onAuthoritativeEvent` 一处接口带 handler 参数、实现不接收（`contracts/host.ts:75` vs `src/adapters/aaos-bridge.ts:196`），属已登记的 `BLOCKED_BY_HOST_CONTRACT` 缺口，非本轮新缺陷。
- 23/23 已修复，只触碰 `tests/`（19 文件，+162/−41 行）；`src/`、`contracts/`、`dev-host/` 零改动。
- 修复后封存：`gate-20261014-005737.log` 八阶段全 `EXIT=0`，**36 文件 324 项通过**（修复前 323），`AAOS_DRIFT=VERIFIED`，`ARCHIVE_FIDELITY=OK`，文档锚点 0 问题；`docs/verification/gates.json` `allGreen=true`（源码树 101 文件，树哈希 `e75bc5032c4e0cd6…`）。

## 判定分类

| 类别 | 含义 |
| --- | --- |
| VACUOUS 空洞 | 断言恒真：`0===0`、共享常量对自身、无正控制的反例 |
| PRESENCE-ONLY 弱存在性 | 只断言"存在/返回了东西"，不断言内容与效果 |
| NAME-BODY 错位 | 名称声称的命题超出正文实际断言 |
| TAUTOLOGICAL 循环 | 断言两侧同源（共享常量、同一次调用的输入输出互比） |
| WEAK-COUNTER 弱计数 | 阈值弱于名称要求（如"互不相同"只断言 ≥8/9） |
| BARE-THROW 裸抛 | 只断言抛出，不断言类型或消息 |
| HARDCODED-SET 硬编码集合 | 输入集合是拷贝粘贴而非取自契约真源 |
| ABSENCE 缺席误报 | 声称"不再出现/不可达"但构造下无从证伪 |

## 发现与处置（23 项 / 19 文件）

| # | 文件 | 类别 | 发现与处置（修复后如何变红） |
| --- | --- | --- | --- |
| 1 | `tests/adapters/sse.test.ts` | NAME-BODY | 名字声称"不派发半行"，正文掩盖了 flush 在流结束派发残行的故意语义。改为如实命名并注明截断可用性由调用方判定；JSON 失败用例先钉 `payload === '{不是json'` 证明输入确实到达判定点后再断言抛错。 |
| 2 | `tests/adapters/openai-compatible.test.ts` | WEAK-COUNTER | 取消用例只断言失败、未钉分类。钉 `code === 'ABORTED'`；若产品丢失 abort 前置判定（退化为 MALFORMED）即红。 |
| 3 | `tests/adapters/port-compatibility.test.ts` | BARE-THROW | 裸 `toThrow()` 不断言消息。收为 `/unknown presentation mode/`；替换错误消息即红。 |
| 4 | `tests/boundary/presentation-modes.test.ts` | BARE-THROW | 同上。 |
| 5 | `tests/presentation/approval-flow.test.tsx` | ABSENCE | 拒绝后未证明任务条消失。补 `queryByTestId('astryn-task-chip')` 为 null（渲染条件在 `companion-view.tsx:147`）；若任务条在拒绝后仍挂载即红。 |
| 6 | `tests/presentation/avatar-fallback.test.tsx` | PRESENCE-ONLY | 正常驱动只断言 `svg` 存在，空壳 SVG 也会通过。补断言状态环 `astryn-ring` 在场；渲染退回占位即红。 |
| 7 | `tests/presentation/host-slots.test.tsx` | VACUOUS | 隐藏/恢复只断言容器结构，未证明隐藏期间会话照常入账。改为真实提交→隐藏→恢复后断言日志同时含提交与回复文本；隐藏期吞消息即红。 |
| 8 | `tests/presentation/presentation-tokens.test.ts` | HARDCODED-SET | 视图档位列表是拷贝而非取自契约。改为遍历 `AVATAR_VIEW_PROFILES` 键集合并断言槽位映射值属于该集合；契约增删档位而映射漏改即红。 |
| 9 | `tests/presentation/voice-settings.test.tsx` | PRESENCE-ONLY | 只断言控件禁用、未断言"原因可见"。补断言 label 文本含「接通后生效」（`companion-settings.tsx:316`）；删除原因文案即红。 |
| 10 | `tests/memory/memory-panel.test.tsx` | VACUOUS | 导出测试"已删除不再出现"在只登记过一条时无从证伪（导出任何状态都可能为空）。改为登记两条→删第一条→断言导出含 `cand-2`、不含 `cand-1`；导出不过滤即红。 |
| 11 | `tests/adapters/aaos-bridge.test.ts` | PRESENCE-ONLY | `onAuthoritativeEvent` 只断言返回函数、未证明不误触。注入监听器后断言收不到任何调用；实现意外开始广播即红。 |
| 12 | `tests/avatar/render-profiles.test.ts` | VACUOUS | 几何断言与渲染输出无绑定（改渲染不改测试）。改从渲染 markup 正则解析圆环/光晕几何，核对头环四边均在头像取景视框内；取景裁剪不当即红。 |
| 13 | `tests/boundary/design-tokens.test.ts` | WEAK-COUNTER | 「九态环色互不相同」只断言 ≥8。钉 `Set(...).size === 9`；两态合色即红。 |
| 14 | `tests/interaction/session-manager.test.ts` | NAME-BODY | 名字声称"同一请求只执行一次"，但只测了一种并发。补提交重复问题与另一问题均拒 `SESSION_BUSY`；单飞退化即红。 |
| 15 | `tests/interaction/session-manager.test.ts` | VACUOUS | 零视图断言 `0===0` 在推送通道全坏时也通过。补正控制 `pushesAtZero > 0`（暂停前推送确实工作过）；通道从不推送即红。 |
| 16 | `tests/companion/reducer.test.ts` | NAME-BODY | 「重复序号不会自行推进动画」与实现不符：`reduceCompanionState` 不读 seq，去重在守卫层（`guard.test.ts`）。改名并钉"序号回退的 delta 仍推进口型帧"——守卫一旦被绕过，这里先变红。 |
| 17 | `tests/companion/character-profile.test.ts` | VACUOUS | 黑名单扫描对常量档案永远为真（新命名可绕过）。保留黑名单并补结构化遍历：任何函数、类实例、非平凡对象按路径点名失败。 |
| 18 | `tests/learning/learning-journey.test.ts:109` | VACUOUS | 移除后 `review=[]` 在从未排程时为真。补正控制：移除前队列含该材料，且 `recordOutcome` 结果在场；排程失效而测试仍绿的情况被消除。 |
| 19 | `tests/learning/learning-journey.test.ts:359` | NAME-BODY | 名字含 `unrated` 腿但正文未断言。补旅程开始前 `level === 'unrated'`；无结果时猜测等级即红。 |
| 20 | `tests/learning/learning-journey.test.ts:412` | TAUTOLOGICAL | 断言与共享常量互比，常量被改错两边同绿。先钉常量字面量 `[86_400_000, 259_200_000, 604_800_000]`，再钉绝对到期时刻与封顶复用末档；改错任一档即红。 |
| 21 | `tests/memory/manager.test.ts:187` | VACUOUS | 「分离」靠"管理器从未见过的本地对象保持原样"证明。补结构化断言：管理器自有属性不含档案/学习存储引用（端口为唯一存储接触面、作为正控制在场）；管理器日后持有第二存储即红。 |
| 22 | `tests/memory/policy.test.ts:103` | NAME-BODY | 名字声称"模型自述不可自证"，但拒绝实为 `trustedIssuers` 为空驱动（`policy.ts:55` 不读 `issuedBy`）。改名为「无可信宿主合同时…回执自报签发方不作数」并断言 `HOST_CONTRACT_MISSING` ×2（含自称 `aaos-core` 亦被拒）。 |
| 23 | `tests/memory/policy.test.ts`（覆盖盲区） | ABSENCE | `ASTRYN_MEMORY_CONSUMER_FORBIDDEN` 表与 `CONSUMER_FORBIDDEN_FOR_SCOPE` 分支（`policy.ts:31`）无任何测试触达。新增行为测试：task/knowledge × character_fiction 持授权仍被拒 + companion 正控制；夹具端到端补一行同理由断言。 |

## 过程纪律

1. **先验证产品行为，再收紧断言**：两处"疑似产品缺陷"都先读源码定性（见上），是测试名错了就改测试名，不是把确定性行为弱化成"只要失败就行"。
2. **每项修复都让"去掉所指机制即变红"成立**：如 #15 的 `pushesAtZero>0`、#10 的两候选先删后查、#20 的字面量钉死。
3. **不虚构新覆盖、不删真覆盖**：唯一新增测试是 #23 的覆盖盲区（分支此前 0 触达）；总数 323 → 324。所有修复均为收紧或改写，未删除任何既有断言。
4. **产品侧零改动**：`git diff` 证明 `src/`、`contracts/`、`dev-host/` 无任何改动；审计不夹带功能变更。

## 残余与边界

- 独立审计覆盖 30/36 个测试文件；其余 6 个不在本轮深审范围，如实标为未获本轮背书。
- 审计由子智能体 + 本人复核完成，非第三方人工审计；判据是"能否为名字失败"，不保证语义完备性。
- 视觉像素级回归仍靠 CDP 探针（Q7）与人工走查，测试不替代渲染实测；宿主集成与真实模型链路不应因本报告改变证据级别（仍 `BLOCKED_BY_HOST_CONTRACT` / `UNVERIFIED`）。
