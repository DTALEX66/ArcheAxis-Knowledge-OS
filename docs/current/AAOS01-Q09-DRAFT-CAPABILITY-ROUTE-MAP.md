# AAOS-01 Q09：**缺失映射的草案（DRAFT —— 不是权威，未采纳）**

## 0. 这份文件的地位（请先读这一段）

> **这是草案。它不是权威文件，我没有把它写进任何 Authority 位置，也没有改任何既有文件。**

它存在的理由：第 79 轮查明「已批准能力目录」与「运行时实现」之间**缺少显式映射**。
**本草案把那个缺口的形状做出来**，好让你判断该不该补、以及补成什么样。

**方法只有一种，而且很弱：按名称对应。** 我**没有**任何权威依据把 `CAP-00x0` 绑到一条路由上 ——
**下面每一条都标了依据与置信度，凡是我推不出来的就写 UNMAPPED。**

## 1. 两份权威的原文（再列一次，便于对照）

**声明侧** —— `docs/truth/CAPABILITY_ATLAS_V2.yaml`，16 项，`technical_state ∈ {supported, in_progress, planned}`；
**实现侧** —— 候选 `worker-profile.json`，11 条路由（能力 → 脚本）。

## 2. 草案映射表

**置信度含义**：`高` = 名称与语义几乎直指；`中` = 名称相关但职责可能不同；`低` = 只是同域；`UNMAPPED` = 我推不出来。

| capability | 名称 | 我推测的实现 | 依据 | 置信度 |
| --- | --- | --- | --- | --- |
| CAP-0010 | 原件资产与来源接入 | （Core 原生，无 worker 路由） | `capability-map` 标 `core_native`；且 `objects` 含 `RawAsset`/`SourceRecord`/`Hash` | **高** |
| CAP-0020 | 多格式转换 | `pdf.extract` · `office.structure` · `html.structure` · `canvas.structure` · `subtitles.structure` · `archive.inventory` | 名称与「多格式转换」直接对应 | **高** |
| CAP-0030 | 证据锚定与交叉核验 | **UNMAPPED** | 11 条路由里没有锚定/核验类脚本 | — |
| CAP-0040 | 人类深度学习系统 | **UNMAPPED** | 学习类路由不在候选的 11 条里（`workers/learning/` 目录存在但无路由条目） | — |
| CAP-0050 | AI 学习资产与受控调用 | `machine.answer`（推测） | 与 AI 资产/受控调用同域，但**职责未必相同** | **低** |
| CAP-0060 | LER 视觉教学与课件 | **UNMAPPED** | 无课件/教学类路由 | — |
| CAP-0070 | 动态解释与仿真 | **UNMAPPED** | 无 | — |
| CAP-0080 | 空间记忆与沉浸学习 | **UNMAPPED** | 无 | — |
| CAP-0090 | 研究、课程与项目工作空间 | **UNMAPPED** | 无 | — |
| CAP-0100 | 开放互操作与生态适配器 | **UNMAPPED** | 无（`archive.inventory` 更近 CAP-0020） | — |
| CAP-0110 | 搜索、图谱与索引 | （Core 原生） | `capability-map` 标 `core_native` | **中** |
| CAP-0120 | 桌面、平台与可选协作 | （宿主层，不是 worker 能力） | `product_layer` 层面 | **中** |
| CAP-0130 | 受限受控执行探索 | **UNMAPPED** | 无 | — |
| CAP-0140 | 备份、同步与发布 | （Core 原生 —— 我在 Q11 实测过备份/恢复） | 与实测一致 | **高** |
| CAP-0150 | 模型、Provider 与数据出境治理 | **UNMAPPED** | 无 | — |
| CAP-0160 | 可视化与空间学习表征 | **UNMAPPED** | 无 | — |

**11 条路由的归属（反向看）：**

| 路由 | 我推测归属的 capability |
| --- | --- |
| `pdf.extract` · `office.structure` · `html.structure` · `canvas.structure` · `subtitles.structure` · `archive.inventory` | **CAP-0020 多格式转换** |
| `image.ocr` · `image.caption` | **UNMAPPED**（可能是 CAP-0020 或 CAP-0060 的一部分，我判不了） |
| `media.probe` · `media.transcribe` | **UNMAPPED** |
| `machine.answer` | **CAP-0050（低置信）** |

## 3. 这份草案真正说明的事

```
声明 16 项
  ├─ 我敢按名称对应的：      4 项（CAP-0010/0020/0140 高，CAP-0110/0120 中）
  ├─ 我只能低置信猜的：      1 项（CAP-0050）
  └─ 我完全推不出来的：     11 项

实现 11 条路由
  ├─ 有明确归属的：          6 条（全归 CAP-0020）
  └─ 归属不明的：            5 条（image.* · media.* · machine.answer）
```

**结论：即使把名称对应用到极致，也只能覆盖一小部分。**
**这说明缺的不是「一张纸」，而是**能力与实现之间真正的对应关系** —— 而它现在没有权威来源。**

## 4. 我不做的事

1. **不把这 15 条推测写成事实** —— 每条都标了置信度；
2. **不把它落到任何 Authority 位置** —— 它是 `docs/current/` 下的草案；
3. **不为了「填满表格」而编造映射** —— 11 项 UNMAPPED 就是 UNMAPPED；
4. **不改任何既有权威文件**。

## 5. 如果你的判断是要补这个映射，我做这件事需要什么

| 需要 | 说明 |
| --- | --- |
| 权威来源 | 谁有权定义「能力 ↔ 路由」的对应（`capability-map` 的 `note` 指向 atlas，但 atlas 没有该字段） |
| 落点 | 是在 atlas 加字段，还是新建一份 join 文件 |
| 判定依据 | 按脚本目录（`workers/learning/`、`workers/machine/`…）还是按路由名 |

**在你说之前，我不会创建它。**
