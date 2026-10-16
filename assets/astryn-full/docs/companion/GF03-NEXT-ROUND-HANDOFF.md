# GF03 下一轮 MINIMAX 交接清单（2026-10-16）

> 用途：本文件是下一轮交给 MINIMAX DESIGN 执行方的待办集合。凡标注【需授权】的项，未经用户明确同意不发起；其余为生成/确认类任务。
> 现状基线：`assets/character/STATE-ASSET-INDEX.json`（schema v2，2026-10-16）。
> 本轮已本地闭合的缺口（不再交接）：四张 429 去背全部本地派生（derived-alpha 四件，含 pose_listening v3 颜色投影细化；thinking/completed/failed 三件亦已 v3 回灌）；E 组口闭合/半开/眼闭合候选帧（derived-frames，ACCEPTED_LOCAL，runtimeUsable=true）；A3 头部补充页（derived-refs）；D 组三呈现构图（derived-refs）。

---

## H1 【需授权】四张原生去背 429 重试（原任务 retry，不重画）

本地派生件是过渡件（经 v3 颜色投影细化，软边/光晕已显著下降且只缩不增；pose_listening 为 v2 场拟合 + v3 细化件）。原生 alpha 仍以 MINIMAX 通道为准：

| 用途 | 原任务 ID | 本地过渡件 |
| --- | --- | --- |
| state thinking | `tsk_8e8eb75ed3e7` | derived-alpha/xiaoqi_state_thinking_sleepwear_v1.png |
| state completed | `tsk_97a4374d4ed6` | derived-alpha/xiaoqi_state_completed_sleepwear_v1.png |
| state failed | `tsk_f85cfb34ae92` | derived-alpha/xiaoqi_state_failed_sleepwear_v1.png |
| pose listening | `tsk_3aeb57ddebfc` | derived-alpha/xiaoqi_pose_listening_sleepwear_v1.png（v2 场拟合） |

执行要点：**用原任务 ID 发起 retry，不要重新生成**（保持与已登记件像素血缘）；成功后按 §7 命名回传，项目侧替换过渡件并把过渡件移入 superseded。

## H2 360° 转台视频（三视图抽帧源）

简报 §8.3 提示词原文现成可直接粘贴：A-pose 全身、相机水平匀速环绕 360°、平视、距离恒定、纯深空蓝黑底 #0C141F、10 秒 24fps、首尾帧一致。取回后项目侧本地抽 0°/90°/180° 帧规整为三视图。如需 T-pose 版按 §8.3 末段替换站姿描述。

## H3 B/C 组 4K 升档

现交付半身/体态母版为 2048 级（1696×2528）。简报 §5 要求母版 ≥4096 长边。以 A1/现交付件为参考图做升档重生成（保持身份与构图不变），逐张记录 seed。

## H4 写实机甲第二服装线（已定夺，2026-10-16）

用户确认两套造型并存：机甲线立为第二服装线。生成材料已备于简报 §10（身份块、机甲服装块、参考图清单、M-A1' 基准卡提示词、M-B 九状态编辑指令版、命名 `xiaoqi_<类别>_<状态或视角>_mecha_v1`、落库与验收要求）。两张概念图（concepts/ 节，仅参考永不进运行时）：
- `xiaoqi_concept_learning_cabin_v1.png`（sha256 7908573b…c689，1672×940）
- `xiaoqi_concept_knowledge_cabin_v1.png`（sha256 da5fed5f…79b6，1672×941）

执行顺序：M-A1' + M-B idle/listening 两张 → 人工确认风格与身份 → 其余七态。

## H5 【需确认】简报 §1/§2.1 身份同步改写

实际交付身份与简报 §1 身份不变量漂移（简报写紫罗兰发 #2B2154/星形发夹/赛璐璐；交付为灰蓝渐变发/星球发夹/写实数字角色风格——见交付清单 ver_4adf7eb2e9c7）。已备好改写稿（下方【补充提示词】），确认后落入简报 §1/§2.1，后续轮次统一按新身份执行。身份锚参考图：`assets/character/upgraded/v1/xiaoqi_primary_face_reference_v2.png`。

## H6 记录规范（每轮强制执行）

逐张记录：模型名/seed/日期/参考图/任务 ID；`prompt_optimizer=false` 显式关闭；透明底一律纯色底生成后去背，不指望原生透明。

## H7 动态微动素材（idle 呼吸循环，先验证一条链路）

运行时不做视频播放——动态路线 = 短循环视频 → 本地抽帧 → 去背 → 序列帧交换（帧交换接线在 CODEX 侧，条目见 `docs/companion/CODEX-HANDOFF.md` C1）。先只出 idle 一条，验证"抽帧→去背→可循环序列帧"全链路；通过后再谈 listening/speaking 微动扩展，不批量。

【提示词】（参考图 = `xiaoqi_primary_face_reference_v2.png` 与已交付 `xiaoqi_state_idle_sleepwear_v1.png`）：

```
参考图中的角色。保持人物身份、发型与星球发夹、瞳色、服装、半身机位、
构图、光照、背景完全不变。角色保持原地静止，仅做自然呼吸的轻微起伏
与发丝、衣摆的轻微浮动；无位移、无转身、无表情变化、口部始终闭合、
无手势变化。使用纯色深空蓝黑背景（#0C141F），无渐变、无纹理、无地面、
无投影、无文字、无水印、无其他元素。视频 5 秒、24fps，首尾帧画面一致
（可无缝循环）。
```

- 预算参考（2026-10-13 调研档）：H3 视频 768p ≈ 0.5 元/秒、2K ≈ 0.8 元/秒 → 5 秒约 2.5–4 元。
- 回传后项目侧：抽 8–12 帧（覆盖一个完整呼吸周期）→ 逐帧去背 → 登记 → 交 CODEX 帧交换接线。
- 红线沿用：无文字无水印；纯色底；不做表情与口部变化（表情归 B 组、口部归帧交换）。

---

## 【补充提示词】简报 §1 身份不变量改写稿（待确认后替换）

```
角色：小栖（Xiaoqi），原创成年女性学习陪伴角色，气质自然亲近而克制，
温柔安静，不是偶像、不是战斗角色、不幼态、不夸张表演。
发型：灰蓝渐变长发（根部的深灰蓝过渡到发梢浅灰蓝），垂至腰际，
中分刘海、两侧鬓发垂落胸前，发丝柔顺有层次。
发饰：刘海左侧一枚星球（带环行星）形发夹，蓝色星球配细环。
瞳色：温和深色瞳，眼型友好。眉毛细而柔和。
肤色：暖白柔和渐层，脸颊有极淡红晕。
服装：柔软纯色短袖家居上衣与宽松家居短裤（浅灰蓝系），
胸前小口袋缀星球徽点，无夸张装饰。
比例：成年女性，约 6–7 头身，肩线与手部自然。
画风：写实数字角色渲染（柔和体积光、细腻发丝与皮肤材质），
不做赛璐璐平涂、不做塑料感 3D、不照片拼贴。
```

依据：交付清单 `虚拟人物/小栖/store/ver_4adf7eb2e9c7.md` 载明的实际身份描述 + 全部落库件目视一致（灰蓝渐变发、星球发夹、写实风格）。
