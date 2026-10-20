# AAOS-01 Q09：**能力普查已取得 —— 而「连接」并不存在**

## 1. 两份权威各给一维

### `docs/truth/CAPABILITY_ATLAS_V2.yaml` —— 16 项能力，五个维度

```
schema_version: 2.0   atlas_name: ArcheAxis Knowledge — Capability Atlas   updated: 2026-08-12
status_rules: docs/truth/AUTHORITY_AND_STATUS_RULES_V1.md
```

每项能力的字段：`capability_id` · `canonical_name` · `pillar` · `product_layer` ·
`authority_status` · `roadmap_state` · `activation_horizon` · `technical_state` ·
`objects` · `views` · `dependencies` · `entry_gate` · `exit_evidence` · `fallbacks` · `origin_requirement_ids` ✓

**普查结果：**

| 维度 | 分布 |
| --- | --- |
| **`technical_state`** | **`supported: 2` · `in_progress: 6` · `planned: 8`** |
| **`authority_status`** | **`binding_core: 7` · `binding_long_term: 8` · `exploration: 1`** |

**16 项全表：**

| id | 名称 | authority | technical | roadmap |
| --- | --- | --- | --- | --- |
| CAP-0010 | 原件资产与来源接入 | binding_core | **supported** | critical_now |
| CAP-0020 | 多格式转换 | binding_core | in_progress | core_next |
| CAP-0030 | 证据锚定与交叉核验 | binding_core | **supported** | critical_now |
| CAP-0040 | 人类深度学习系统 | binding_core | in_progress | formal_later |
| CAP-0050 | AI 学习资产与受控调用 | binding_long_term | planned | formal_later |
| CAP-0060 | LER 视觉教学与课件 | binding_long_term | planned | formal_later |
| CAP-0070 | 动态解释与仿真 | binding_long_term | planned | formal_later |
| CAP-0080 | 空间记忆与沉浸学习 | binding_long_term | planned | experimental_later |
| CAP-0090 | 研究、课程与项目工作空间 | binding_long_term | planned | formal_later |
| CAP-0100 | 开放互操作与生态适配器 | binding_core | in_progress | core_next |
| CAP-0110 | 搜索、图谱与索引 | binding_core | in_progress | core_next |
| CAP-0120 | 桌面、平台与可选协作 | binding_core | in_progress | critical_now |
| CAP-0130 | 受限受控执行探索 | exploration | planned | deferred_retained |
| CAP-0140 | 备份、同步与发布 | binding_long_term | in_progress | formal_later |
| CAP-0150 | 模型、Provider 与数据出境治理 | binding_long_term | planned | formal_later |
| CAP-0160 | 可视化与空间学习表征 | binding_long_term | planned | formal_later |

### `config/capability-map.v1.json` —— 16 项，另一种状态词表

```
schema: archeaxis.capability-map/v1
states: core_native(7) / worker_backed(4) / not_implemented(5)
```

## 2. ⚠️ 关键发现：**「连接」被声称，但并不存在**

`capability-map.v1.json` 的 `note` 字段写着：

> The join between the approved capability directory and what the runtime implements.
> **The atlas (`docs/truth/CAPABILITY_ATLAS_V2.yaml`) owns capability_id**...

**我在 atlas 全文里逐个搜了所有可能的连接键，全部落空：**

| 搜索词 | 在 atlas 中 |
| --- | --- |
| `archive.inventory` · `canvas.structure` · `html.structure` | **False** |
| `machine.answer` · `pdf.extract` · `image.ocr` | **False** |
| `worker_` · `routes` · `runtime` | **False** |

**而且两份文件的状态字段根本不是同一套：**

| 文件 | 字段 | 取值 |
| --- | --- | --- |
| `capability-map.v1.json` | `state` | `core_native` / `worker_backed` / `not_implemented` |
| `CAPABILITY_ATLAS_V2.yaml` | `technical_state` | `supported` / `in_progress` / `planned` |

**结论：**

> **atlas 里没有任何字段把 `CAP-00x0` 指向一条路由或一个 worker 脚本。**
> **「已批准能力目录」与「运行时真正实现了什么」之间，缺少一个显式的、可机读的映射。**

**所以 Q09 的「能力差集」无法从这两份权威文件直接算出** —— 它需要一个**尚不存在的映射记录**。
**这就是诚实的答案，我不去拼一个看起来成立、实则无效的差集。**

## 3. 已存在的那一半：**实现侧**是清楚的

候选 `worker-profile.json` 给出 **11 条真实路由**（能力 → 脚本），这是**实现侧**的权威：

```
archive.inventory   canvas.structure   html.structure    image.caption    image.ocr
machine.answer      media.probe        media.transcribe  office.structure pdf.extract
subtitles.structure
```

**声明侧 16 项、实现侧 11 条，缺的是两者之间的桥。**

## 4. atlas 自己的 `tombstone_rule`（直接对应目标句）

> **任何 capability 的删除、降级、改名、合并均需 Owner Decision 和可追溯映射；
> 删除 `binding_core` / `binding_long_term` 的测试/校验失败。**

**即：能力层面的「合并/删除」与目录层面一样，都需要你的决定 + 可追溯映射。**

## 5. 本轮未做

1. **未**创建那个缺失的映射（**那是 Authority 级新增，需你确认**）；
2. **未**改任何实现文件；**未**触碰官方 Green 的 `data/` 与资料库；**全程只读**。
