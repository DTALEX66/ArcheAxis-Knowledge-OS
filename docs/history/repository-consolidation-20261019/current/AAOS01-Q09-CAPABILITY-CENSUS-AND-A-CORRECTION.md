# AAOS-01 Q09：**能力普查 + 一处对我第 59 轮结论的更正**

顺着你给的权威路径，我在老 Green 的候选里读到了**真实的能力路由表**，它同时给出两样东西。

## 1. ⚠️ 先更正我第 59 轮的一个结论

**候选的 `worker-profile.json` 里有 11 条真实路由，其中一条是：**

```
machine.answer  ->  workers/machine/worker_machine_answer.py
```

**而我第 59 轮得到 `503 no worker is registered for machine.answer`，当时我写下：**

> **「所以 `machine/answers` 这条路**永远不会**派生 Python worker —— 与我看不看、看多久无关。」**

**那句话是错的。**

| 我当时的推断 | 实际 |
| --- | --- |
| 产品没有 `machine.answer` 的 worker | **候选里有这个脚本** |
| 这条路由永不派生 worker | **我启动时只声明了 `text.extract` 一条路由**，没声明 `machine.answer` |

**503 说的是「我这次启动没给它注册这条能力」，不是「产品没有这个能力」。**
**我把「我的启动配置」当成了「产品的能力边界」。**

## 2. 真实的能力路由表（候选 `worker-profile.json`，11 条）

```
archive.inventory    -> workers/document/worker_archive.py
canvas.structure     -> workers/document/worker_canvas.py
html.structure       -> workers/web/worker_html.py
image.caption        -> workers/vision/worker_caption.py
image.ocr            -> workers/vision/worker_ocr.py
machine.answer       -> workers/machine/worker_machine_answer.py
media.probe          -> workers/document/worker_media.py
media.transcribe     -> workers/media/worker_transcribe.py
office.structure     -> workers/document/worker_office.py
pdf.extract          -> workers/document/worker_pdf.py
subtitles.structure  -> workers/document/worker_subtitles.py
```

**这是一张「能力 → 脚本」的真实映射**，正是 `Executor::open_routes(capability, worker)` 需要的输入。

## 3. 仓库的能力普查（`config/capability-map.v1.json`）

```
schema: archeaxis.capability-map/v1
note:   "The join between the approved capability directory and what the runtime implements.
         The atlas (docs/truth/CAPABILITY_ATLAS_V2.yaml) owns capability_id..."
states: worker_backed / core_native / not_implemented
capabilities: 16 项
```

**状态词表本身就是一份诚实的能力普查：**

| 状态 | 含义（原文） | 数量 |
| --- | --- | --- |
| `core_native` | 「由 Core 自己的路由实现，**没有 worker 能力**」 | **7** |
| `worker_backed` | 「由一条或多条**已声明的 worker 路由**实现」 | **4** |
| `not_implemented` | 「已批准并保留，**尚无任何实现**」 | **5** |
| 合计 | | **16** |

**对照候选提供的 11 条 worker 路由** —— 数量上就说明：**实现面比声明面窄**。

## 4. ⚠️ 但我第一版对比是**无意义的**，我得说明

我先直接做集合相减，得到「16 项声明全都没有 worker 路由、11 条路由全都没被声明」。
**那个结果毫无意义** —— 因为：

| 面 | 用的名字 |
| --- | --- |
| 声明面 | **`CAP-0010` … `CAP-0160`**（ID） |
| 实现面 | **`archive.inventory` …**（点分路由名） |

**两个不同的命名空间相减，得到的当然全是差集。**

**而 `note` 字段早就写明了正确做法**：

> The join … **The atlas (`docs/truth/CAPABILITY_ATLAS_V2.yaml`) owns capability_id**

**即：真正的连接键在 atlas 里。** 我下一轮读它，才能算**有意义**的差集。

**这一条我记下来，因为它正是我反复犯的同一类错：拿两个不可比的东西相比。**

## 5. 本轮未做

1. **未**读 `CAPABILITY_ATLAS_V2.yaml`（下一轮 —— 那是正确连接键所在）；

2. **未**改任何实现文件；**未**触碰官方 Green 的 `data/` 与资料库；
3. 全程**只读**。
