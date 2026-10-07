# DT ALEX STUDIOS・文案校准 V2

> 用途：① 三个个人项目（AAOS / WORK-LAB / DESIGN-LAB）的
>
> **准确文案**
>
> ，可直接落地 
>
> `projects.js`
>
>  与 
>
> `project.html`
>
>  个人模板；
> ② 占位作品位 PROJECT 06 / 07 / 08 的高赞配图文案参考（临时使用，后期替换）。
> 调研依据（数据时点 2026-10-06）：
> GitHub 仓库 README：
>
> `DTALEX66/ArcheAxis-Knowledge-OS`
>
> 、
>
> `DTALEX66/WORK-LAB`
>
> 、
>
> `DTALEX66/DESIGN-LAB`
> 本地素材：
>
> `web/work/archeaxis-site/`
>
> （十页产品官网）、
>
> `src-media/work-lab/`
>
> 、
>
> `src-media/design-lab/`
>
>  界面截图、
>
> `web/assets/js/projects.js`
>
>  现有文案
> 全网配图文案：JAGDA 2025 获奖海报、站酷高赞作品、Behance /abduzeedo 报道等（见第二部分来源链接）



***

## 第一部分・三个个人项目准确文案

### 0. 总修正说明

现有三句一句话（`summary`）都偏泛，其中两处存在**方向性错误**：



| 项目         | 原描述的问题                     | 实际定位（依据 GitHub README）                                        |
| ---------- | -------------------------- | ------------------------------------------------------------- |
| AAOS       | 写成「知识整理 + 长期上下文 + AI 使用方式」 | 本地优先、证据驱动、人机双向学习的**系统级知识工作台**，重点在原件保全、证据可追溯、人机共学              |
| WORK-LAB   | 写成「整理 AI Agent 和自动化工作流程」   | **客户端中立的 AI Agent 控制平面**：多客户端能力层收敛到一个规范源，按客户端原生投影，任务包可审计闭环    |
| DESIGN-LAB | 写成「设计工具与工作流项目」             | **AI 原生、平台中立、宿主原生的设计智能与生产能力系统**：研究→方法→领域能力→质量→预检→交付→证据（E0–E5） |

正文遵循简报规格：一句话 ≤60 字；mediaText 每段 ≤120 字；语气用「我」、克制、不写空话；事实底线全部保留。



***

### 1. AAOS — 星环知识平台 ArcheAxis Knowledge

**一句话（列表 / 卡片，≤60 字）**



* 中：本地优先、证据驱动的个人知识系统：原件保全、来源可溯，人与 AI 从同一份可信知识持续学习。

* EN：A local-first, evidence-driven knowledge system: originals preserved, sources traceable, human and AI keep learning from the same trusted knowledge.

**mediaText（详情页 2–3 段）**



1. **怎么想的**：用 AI 越久，资料、聊天记录和研究堆得越多，真正重要的那条却越来越难找回来；换一个工具，历史就断一次。所以想做一个自己的知识系统，而不是继续加一个工具。

2. **怎么做的**：内容先保存，识别忠实度核验与专业依据分析分开记录；六空间、五十个入口、十六个能力家族，每条回答都带可追溯的证据链。机器学习不训练基础模型，候选内容不会自动变成可信事实。

3. **现在的状态**：界面与信息结构已可用（开发版本 0.6.14）。下一步补完多格式内容的本地识别闭环（OCR / ASR / 抽帧），让人机共学从候选走向受治理的资产。

**站点个人字段（projects.js 对应）**



* `summary` / `summaryEn`：如上「一句话」

* `why`：用 AI 越久，资料、聊天记录和研究堆得越多，真正重要的那条却越来越难找回来；换一个工具，历史就断一次。所以做自己的知识系统，而不是继续加一个工具。

* `problem`：

1. 资料散在文档、对话、代码和模型输出里，原件与来源身份常常丢。

2. 识别结果和专业判断混在一起，分不清哪些有依据。

3. 换工具或改配置，历史和学习记录就断一次。

* `current`：已有一套可用的界面与信息结构：六空间、五十个入口、十六个能力家族；资料先保存，识别忠实度核验与专业依据分析分开记录，每条回答都带可追溯的证据链。

* `next`：补完多格式内容的本地识别闭环（OCR / ASR / 抽帧），让人机共学从候选走向受治理的资产。

**锁死事实（不得改动）**：六空间、五十个入口、十六个能力家族；每条回答带可追溯证据链；本地优先；机器学习不训练基础模型。

**JSON（按简报第一部分规格）**



```
{
  "slug": "aaos",
  "title": "星环知识平台 ArcheAxis Knowledge",
  "titleEn": "ARCHEAXIS KNOWLEDGE",
  "year": "2026",
  "category": ["PERSONAL", "DIGITAL"],
  "type": "Personal Knowledge System / Product",
  "role": "Product / Design / System",
  "client": "自定项目",
  "description": "本地优先、证据驱动的个人知识系统：原件保全、来源可溯，人与 AI 从同一份可信知识持续学习。",
  "mediaText": [
    { "title": "为什么", "body": "用 AI 越久，资料、聊天记录和研究堆得越多，真正重要的那条却越来越难找回来；换一个工具，历史就断一次。所以想做一个自己的知识系统。" },
    { "title": "怎么做", "body": "内容先保存，识别忠实度核验与专业依据分析分开记录；六空间、五十个入口、十六个能力家族，每条回答都带可追溯的证据链。" },
    { "title": "现在", "body": "界面与信息结构已可用，下一步补完多格式本地识别闭环（OCR / ASR / 抽帧），让人机共学从候选走向受治理的资产。" }
  ]
}
```



***

### 2. WORK-LAB — 工作流实验室（Workflow Lab）

**一句话（列表 / 卡片，≤60 字）**



* 中：客户端中立的 AI Agent 控制平面：把多个客户端的规则、技能、记忆与工作流策略收敛到一个规范源，按客户端原生投影。

* EN：A client-neutral AI-agent control plane: one canonical source for rules, skills, memory and workflow policy, projected natively into each client.

**mediaText（详情页 2–3 段）**



1. **怎么想的**：不同 Agent 客户端（Hermes、Codex、DSH、GitHub 等）各管一套规则、技能和记忆，能力声明重复且容易漂移；任务从计划到交付也没有统一的审计视角。想用一个规范源替代多处维护。

2. **怎么做的**：任务以任务包（task pack）走可审计闭环 —— 单写者写入、只读并行审计、交付门禁；观测面板二十二个只读视图，把任务、执行、审批、审计与成本放在同一屏，缺数据如实写 UNKNOWN，不用零值补曲线。

3. **现在的状态**：控制平面与观测面板已成型。下一步把审批回路、失败恢复与发布门禁做完整，从「看得见」走到「控得住」；新客户端通过同一 Adapter 契约接入。

**站点个人字段（projects.js 对应）**



* `summary` / `summaryEn`：如上「一句话」

* `why`：不同 Agent 客户端（Hermes、Codex、DSH、GitHub 等）各管一套规则、技能和记忆，能力声明重复且不一致；任务从计划到交付也没有统一的时间线与确认点。

* `problem`：

1. 同一份能力配置要在多个客户端里各维护一份，容易漂移。

2. 高风险动作缺少明确的确认点，运行结果不被记录。

3. 哪一步慢、哪一步贵、哪一步失败过，说不清。

* `current`：观测面板已成型：二十二个只读视图，把任务、执行、审批、审计与成本放在同一屏；单写者 + 只读并行审计，缺数据如实写 UNKNOWN，不用零值补曲线。

* `next`：把审批回路、失败恢复与发布门禁做完整，从「看得见」走到「控得住」；新客户端通过同一 Adapter 契约接入。

**锁死事实（不得改动）**：二十二个只读视图；缺数据如实写 UNKNOWN；Observer 只读（无批准 / 拒绝 / 撤销 / 重试）；客户端中立（Hermes・Codex・DSH・GitHub・Open Design・OpenHuman）；外部变更需显式批准。

**JSON（按简报第一部分规格）**



```
{
  "slug": "work-lab",
  "title": "WORK-LAB 工作流实验室",
  "titleEn": "WORKFLOW LAB",
  "year": "2026",
  "category": ["PERSONAL", "DIGITAL"],
  "type": "Agent Control Plane / System",
  "role": "Product / System Design / Observability",
  "client": "自定项目",
  "description": "客户端中立的 AI Agent 控制平面：把多个客户端的规则、技能、记忆与工作流策略收敛到一个规范源，按客户端原生投影。",
  "mediaText": [
    { "title": "为什么", "body": "不同 Agent 客户端各管一套规则、技能和记忆，能力声明重复且容易漂移；任务从计划到交付也没有统一的审计视角。想用一个规范源替代多处维护。" },
    { "title": "怎么做", "body": "任务以任务包走可审计闭环——单写者写入、只读并行审计、交付门禁；观测面板二十二个只读视图，缺数据如实写 UNKNOWN。" },
    { "title": "现在", "body": "控制平面与观测面板已成型，下一步把审批回路、失败恢复与发布门禁做完整，从「看得见」走到「控得住」。" }
  ]
}
```



***

### 3. DESIGN-LAB — 视觉设计实验室（Visual Design Lab）

**一句话（列表 / 卡片，≤60 字）**



* 中：AI 原生、平台中立的设计能力系统：把参考、方法、领域能力、预检与证据组织成可验证、可回滚的设计闭环。

* EN：An AI-native, platform-neutral design system: references, methods, domain packs, preflight and evidence in one verifiable, rollback-safe loop.

**mediaText（详情页 2–3 段）**



1. **怎么想的**：一天里在参考、生成、排版、改稿、导出之间来回切换十几次，问题不是工具不够，而是它们彼此不通；做过什么判断、为什么这样改，也没人记得。

2. **怎么做的**：参考导入后由服务端读回预览，Brief → Direction → DesignSystem 每一步存成可回溯的版本链，并发提交会被拦下而不是静默覆盖；预检只探测与报告，不安装、不改变环境。

3. **现在的状态**：工作台与版本链可用，证据分级 E0–E5 已接通。下一步把预检规则做细，让交付问题在设计阶段就暴露；按需接入更多宿主与工具适配器。

**站点个人字段（projects.js 对应）**



* `summary` / `summaryEn`：如上「一句话」

* `why`：一天里在参考、生成、排版、改稿、导出之间来回切换十几次，问题不是工具不够，而是它们彼此不通；判断依据不落地，改到第七版说不清为什么好。

* `problem`：

1. 参考素材进来之后，做过什么判断没人记得。

2. 同一个方向改了七版，第七版为什么好说不清。

3. 交付前才发现字体和色值被改过，问题暴露太晚。

* `current`：工作台可用：参考导入后由服务端读回预览，Brief → Direction → DesignSystem 每一步存成可回溯的版本链，并发提交会被拦下而不是静默覆盖。

* `next`：把预检规则做得更细，让交付前的问题尽量在设计阶段就暴露；按需接入更多宿主与工具适配器。

**锁死事实（不得改动）**：Brief → Direction → DesignSystem 版本链；并发提交 409 拦截；证据分级 E0–E5 不互相冒充；宿主原生（不重建画布 / 聊天客户端 / 模型网关 / SaaS 后端）。

**JSON（按简报第一部分规格）**



```
{
  "slug": "design-lab",
  "title": "DESIGN-LAB 视觉设计实验室",
  "titleEn": "VISUAL DESIGN LAB",
  "year": "2026",
  "category": ["PERSONAL", "DIGITAL"],
  "type": "Design Intelligence / System",
  "role": "Product / System Design / Workflow",
  "client": "自定项目",
  "description": "AI 原生、平台中立的设计能力系统：把参考、方法、领域能力、预检与证据组织成可验证、可回滚的设计闭环。",
  "mediaText": [
    { "title": "为什么", "body": "一天里在参考、生成、排版、改稿、导出之间来回切换十几次，问题不是工具不够，而是它们彼此不通；判断依据也不落地。" },
    { "title": "怎么做", "body": "参考导入后由服务端读回预览，Brief → Direction → DesignSystem 每一步存成可回溯的版本链，并发提交被拦下而不是静默覆盖。" },
    { "title": "现在", "body": "工作台与版本链可用，证据分级 E0–E5 已接通；下一步把预检规则做细，让交付问题在设计阶段就暴露。" }
  ]
}
```



***

## 第二部分・占位作品位（06 / 07 / 08）高赞配图文案参考

> **使用说明**
>
> ：以下均来自他人
>
> **高赞 / 获奖作品**
>
> 的公开配图文案，仅作
>
> **风格与结构参考**
>
> ，请勿直接用于描述自己的作品。
> 占位位页面仍需保留 
>
> `Replace with real work`
>
>  标注（符合站点真实性约定）；后期用自己旧作 / 练习稿替换时，按对应类别句式改写即可。

### 06・Poster / Print（海报与印刷）

**参考 1：JAGDA 2025 国际学生海报大赛获奖作品陈述（专业赛事级）**



* 作品：*Safe is disappearing*（岩永美月，長岡造形大学，资生堂创意奖）

* 来源：[https://www.shejijingsai.com/2026/06/1558686.html](https://www.shejijingsai.com/2026/06/1558686.html)

* 原配图文案（节选）：「于海洋鱼类而言，纯粹无塑的洁净海域，便是最大的安全。作品聚焦海洋塑料污染问题，以褪色破碎的蓝色海域，展现塑料垃圾不断侵蚀海洋生态的现状。三连幅海报组合可拼接成完整鱼形，单幅亦可独立表意…… 希望借由作品，唤醒大众对海洋生态保护的重视。」

* 结构拆解：**观点一句（鱼的安全＝无塑的海）→ 画面如何转译（褪色破碎的蓝、三连幅拼鱼形）→ 对观者的期望**。观点先行，画面服从观点，收尾落在公共意义。

* 同页可参考金奖 *Safety first*（鲁辰阳）：「青少年被父母过度的保护牢牢束缚…… 这种保护确实安全，却也令人窒息」—— 比喻（气球被束缚）+ 反讽收尾；以及《Red Light》《Caged Marriage》等单句陈述式。

**参考 2：「我的 BUG 父亲」叙事海报（站酷高赞）**



* 来源：[https://www.zcool.com.cn](https://www.zcool.com.cn)（作品「我的 BUG 父亲，讲个笑话，你别哭」，站酷 / 抖音分享）

* 原配图文案（节选）：「这是一组关于『父亲角色失灵』的叙事海报。我把父亲理解成一个反复出现、反复掉线的 BUG…… 有些 BUG 不是为了修复父亲，而是为了修复自己。」系列创意思路：「父亲的 BUG 不是突然消失，而是总在关键时刻掉线；不是完全不爱，而是爱没有指向她…… 画面表面是温暖的，故事内核却是失落的。视觉上像一组被孩子小心保存下来的记忆切片：暖黄的光、旧纸纹理、电影感构图、手写标题，以及一条贯穿始终的编号系统。」

* 结构拆解：**概念比喻（BUG）→ 故事梗概 → 创意思路（比喻展开）→ 视觉手法（光 / 纹理 / 构图 / 编号）**。叙事型海报的完整文案范本。

**参考 3：电影海报系列合集（站酷精选）**



* 来源：[https://www.zcool.com.cn/collection/ZNDYxNzEwOTI=](https://www.zcool.com.cn/collection/ZNDYxNzEwOTI=)（《姜子牙》《哪吒》《刺杀小说家》《囧妈》等系列海报）

* 可借鉴点：电影海报文案常用「一句主题句 + 视觉隐喻 + 上映信息」，主海报 / 角色版 / 终版共用同一视觉母题；项目页可写「为 X 主题做的系列海报：用同一视觉母题贯穿主视觉与延展」。

### 07・Motion / Video（动态与影像）

**参考 1：Knife Motion — Kinetic Typography（Behance 14,000+ 赞）**



* 来源：abduzeedo 报道 [https://abduzeedo.com/kinetic-typography-motion-design-words-move-bodies/](https://abduzeedo.com/kinetic-typography-motion-design-words-move-bodies/)（作品全文在 Knife Motion 的 Behance 主页）

* 原报道文案（节选）：「把字母当作物理对象：加速、碰撞、抵抗、释放，在严格的空间栅格里运动…… 不是线性路径，而是机械惯性；每一帧都有严格的基线对齐与计算过的边距。受限的配色把注意力全部留给字形结构；印刷质感模拟让数字屏幕上有触觉对比。」

* 结构拆解：**运动理念（字＝物体）→ 技术手段（手动关键帧 / 惯性）→ 视觉系统（配色 / 质感）→ 结果（任何速度下可读）**。Motion 作品页的「理念 — 手法 — 系统」三段式。

**参考 2：Changhoon Nam — Herman Miller Aeron（Behance 个人项目）**



* 来源：[https://www.behance.net/gallery/232279839/Herman-Miller-Aeron](https://www.behance.net/gallery/232279839/Herman-Miller-Aeron)

* 原配图说明（转述）：个人项目，通过参考 Herman Miller 过去的经典复古海报，采用平面化设计风格，动态展示 Aeron 椅子的多种功能。

* 可借鉴点：个人动态项目写「参考了什么风格 → 怎么转译 → 展示什么功能」；**静帧做封面 + 悬停静音播放**的呈现方式与占位位 07 完全一致。

**参考 3：Bryan Gancedo-Gonzalez — KNVB Beker（ESPN 合作）**



* 来源：[https://bryangmotion.com/](https://bryangmotion.com/)

* 原配图说明（节选）：「与知名体育设计工作室 GRAPHICHUNTERS 合作，为 ESPN 制作了 70+ 个动画资产，从直播图形到完整推广包与社媒内容。」

* 可借鉴点：**数量词（70+）+ 合作方（ESPN）+ 资产类型（直播图形 / 推广包 / 社媒）**—— 一屏讲清规模与类型。

### 08・Campaign / Key Visual（活动主视觉）

**参考 1：第三届王者荣耀全国大赛 KV & 海报（站酷，深圳三帅）**



* 来源：[https://www.zcool.com.cn/collection/ZMzA3MTA0MjA=](https://www.zcool.com.cn/collection/ZMzA3MTA0MjA=)

* 可借鉴点：赛事 KV 文案＝**赛事主张一句 + 主视觉阐述 + 延展物（海报 / 长图 / 投放）清单**；正好对应占位位 08 的「主视觉 + 延展物料 + 投放画面」结构。

**参考 2：大众汽车金融服务 ×「简为 ×」品牌艺术系列 KV（站酷）**



* 来源：[https://m.zcool.com.cn/work/ZNzMwNDg0OTI=.html](https://m.zcool.com.cn/work/ZNzMwNDg0OTI=.html)

* 原配图文案（节选）：「本系列共 5 张主视觉 KV，每张对应一款核心车型（Lavida、Tayron、Touareg、CC、Tharu）…… 以『简为生动』『简为澎湃』『简为探索』『简为热烈』为核心 slogan，传递『0 利率、一站式服务、极简申请、极速审批』的极致便利感。海报风格大胆融合中国水墨泼彩、抽象几何与现代极简主义。」

* 结构拆解：**数量与对应（5 张 KV × 5 车型）→ slogan 体系（简为 ×）→ 核心卖点 → 视觉风格**。Campaign 文案四件套。

**参考 3：Story Beer & Cocktail 露台酒吧品牌系列海报 campaign（站酷）**



* 来源：[https://m.zcool.com.cn/work/ZNzMwMzg2ODQ=.html](https://m.zcool.com.cn/work/ZNzMwMzg2ODQ=.html)

* 原配图文案（节选）：「核心海报系列以老北京爷们儿为视觉主角…… 营造『说不出口的心里话，都让酒来说』的情绪张力。倒计时海报转向年轻都市夜生活场景，融入胡同、夜景、猫、情侣、孤独喝酒等元素，slogan 直击人性：欠债、欠情、欠故事…… 用酒来…」

* 可借鉴点：**一句话 slogan 立住情绪 → 分系列展开（主系列 / 倒计时系列）→ 每个系列说清视觉主角与场景**。

### 附：三类占位位的通用写作模板（由上述例句归纳）



* **Poster**：为「X」做的一组海报。观点（一句）→ 视觉如何转译观点 → 系列 / 媒介延展 → 希望观看者……

* **Motion**：一段关于「X」的动态设计。运动理念（图形 = 什么）→ 手法（手动关键帧 / 惯性 / 节奏）→ 视觉系统（配色 / 质感）→ 使用场景（静帧封面 + 悬停播放）。

* **Campaign**：为「X」做的活动主视觉。主张（slogan 一句）→ 主视觉阐述 → 延展物料（海报 / 长图 / 投放）→ 规模与节奏。



***

## 命名定案（2026-10-06）



| 内部代号       | 对外名                        | 英文名                 |
| ---------- | -------------------------- | ------------------- |
| AAOS       | 星环知识平台 ArcheAxis Knowledge | ArcheAxis Knowledge |
| WORK-LAB   | 工作流实验室                     | Workflow Lab        |
| DESIGN-LAB | 视觉设计实验室                    | Visual Design Lab   |

三个项目状态保持 `Ongoing`。