# 开源池捐赠项处置的实测核对（2026-10-06）

对象：`docs/current/AAOS-OSS-DONOR-DISPOSITION-V2-20261002.json`（47 条供应链 + 11 条能力吸收 + 369 池规模声明）。
方法：只读核对，不修改该文档。脚本 `scripts/audit/oss_disposition_evidence.py`，逐条在**声明文件**（`pyproject.toml`、`uv.lock`、`requirements.txt`、`frontend/package*.json`）、**流水线**（`.github/workflows/*.yml`、`scripts/ci/*`）、**源码**（`shared/`、`services/`、`app/`、`crates/`、`frontend/src`，只取代码文件）与**vendor 根**中查找该项的证据，并输出每条证据的确切文件与行号。

匹配规则（2026-10-06 修订，原因见第五节）：源码证据按**标识符**判定（`CrossrefClient` 命中 `crossref`），因此 `DataCiteClient`/`OpenAlexClient` 这类不再漏判；注释、文档字符串与字符串字面量（含域名）只算**提及**，不算实现；`__pycache__`、编译产物与生成目录不作为证据；`shared/` 是本仓第一方源码，不再当作 vendor 根，文件名也不等于实拷。

证据：`.project-local/task-runtime/aaos01-oss-evidence-20261006/report.txt`（SHA-256 `0e78c1d21582cf8767037f6ff6b1e3d257b7b2095bdccdb5339e71a3c36195ba`）与同目录 `disposition-evidence.json`（SHA-256 `123faa26762d33169a78d4a79fcb8c524cb99e050afd045b1154f42952d62052`）。修订前的两份证据为 `3eb0634b…68b314beee`（report）与 `158c1d80…592843711`（json），保留不改写。

## 一、实测分布（47 条）

| 实测状态 | 条数 | 含义 |
| --- | --- | --- |
| `DECLARED` | 25 | 在声明文件/流水线中确有该依赖或其调用 |
| `IMPLEMENTED_IN_SOURCE` | 6 | 第一方代码用**标识符**命名该项，且命中处不在“不可用”标记附近。其中 4 条是真自建客户端：A018 Crossref / A019 DataCite / A020 OpenAlex / A021 Wikidata（`shared/evidence_connectors.py:61/93/114/153`，被 `shared/public_evidence.py:12-17` 使用）；另 2 条见第五节 |
| `STUB_IN_SOURCE` | 2 | 只在自述“unavailable-honest”的桩注册表里命名（A002、A003，`shared/bakeoff_engines.py`）——命名不等于可用 |
| `MENTIONED_IN_SOURCE` | 2 | 名称只出现在文档字符串、注释或字符串字面量里（A011 mozilla、A006 whisper.cpp），是引用不是实现 |
| `NONE` | 12 | 声明、流水线、源码、vendor 四处均无证据 |

修订前该表为 `DECLARED` 24、`IMPLEMENTED_IN_SOURCE` 9、`DECLARED_AND_VENDORED` 1、`VENDORED_ONLY` 1、`NONE` 12；两个 `VENDORED` 类别经核实是文件名命中的产物，不再存在。

`NONE` 的 12 条中 9 条是 `REVIEW-BLOCK`、1 条是 `EVALUATE`——这两类本就不该落地，无证据与判定自洽。真正值得追问的是另外两条：

- **A012 Crawlee Python**，判定 `SIDECAR`。`SIDECAR` 是该文档**自己定义过**的判定（"runs beside the Core under the worker protocol"），意为已按 worker 协议侧挂运行；实测在声明、流水线、源码、vendor 四处均无 `crawlee` 证据。
  **阻断原因是设计边界，不是漏做**：本仓的 HTML 路由只读**已保存的快照**——transport 在 `html.structure` 路由处写明 "Fetching a URL is not part of this route: the snapshot is the input, so no network client exists here"。
  即 worker 侧**不持网络客户端**。要让 Crawlee 侧挂，先得决定是否允许 worker 出网；那是产品/安全决策，不在本轮擅自动手。
- **A022 Syft**，判定 `ADOPT`。实测四处均无 `syft` 证据。（该判定词本身未在文档中定义，见下。）
  **能力已由第一方实现**：`scripts/release_sbom.py` 生成 CycloneDX 的 SBOM（`"bomFormat": "CycloneDX"`），来源为 `uv.lock` / `package-lock.json` / `Cargo.lock`，并已接入 `.github/workflows/release.yml`。
  故该行不是"缺一个捐赠包"，而是**能力已第一方重写**——按该文档自己的词表应记 `ABSORB`（"the capability is reimplemented first-party"）。判定更正记录为 `DECISION_SUPERSESSION_LEDGER.yaml` **SUP-024**，原行保留不改写。

## 二、判定词表与实际行不一致（比缺证据更根本）

文档 `rule` 写明每项恰好取 `REFERENCE / ADAPTER / ABSORB / PROVIDER / SIDECAR / BENCHMARK / REJECT` 之一，`verdict_definitions` 也正好定义了这 7 个。但 47 行的实际取值是：

`ADOPT, CURRENT, EVALUATE, REFERENCE, REJECT-CORE, REVIEW-BLOCK, SIDECAR`

- 行使用而文档**未定义**的判定词有 5 个：`ADOPT`、`CURRENT`、`EVALUATE`、`REJECT-CORE`、`REVIEW-BLOCK`。
- 只有 `REFERENCE`、`SIDECAR` 两个词两边重合。

后果是这份处置表**当前不可逐条核对**：对 `CURRENT`/`ADOPT`/`EVALUATE` 三类，无法从文档判断它们各自承诺了什么，因而"未落地"既不能算违约也不能算符合。按项目自身的"事实与判定分离"原则，这里给出的是事实（哪里有证据、哪里没有），不下判定；补齐词表或改写行取值是文档作者的决策。

## 三、本轮由实测发现并已修正的事实性错误

先前的处置表述里，`A023 pip-audit` 与 `A024 Gitleaks` 一度被写成未吸收——更正依据是本轮实测：两者由 `.github/workflows/ci.yml` 以流水线工具形式实际调用（2026-10-06 复核时 pip-audit 在第 165 行、gitleaks 在第 179 行；本文件原写的 153/152 是报告生成时的旧行号，ci.yml 在其后被编辑过），属于"以 CI 门禁形式吸收"，不体现在任何依赖清单里。核对脚本因此把**流水线调用**列为独立证据来源；只看依赖清单会给出一份与事实相反的结论。

## 五、独立复核与表述更正（2026-10-06 二次只读核对）

本节由一次独立的只读复核追加。判定标准是"已吸收必须有**被产品真正调用**的证据"——文件存在但无人调用不算吸收。结论：

- **已证实有真实调用方**：A018—A021（`shared/evidence_connectors.py` 被 `shared/public_evidence.py:12-17` 使用，另有 `tests/test_public_evidence.py`）；A022（`scripts/release_sbom.py` 被 `.github/workflows/release.yml:202` 调用，产物 CycloneDX）；A023/A024（ci.yml 门禁）；C001 PDF.js（`frontend/package.json` 的 `pdfjs-dist`，`frontend/src/components/PdfReader.tsx:3-4` 导入，`frontend/src/spaces/CanonicalLibrarySpace.tsx:8,312` 渲染）。
- **更正一（已改为实测，不再是人工判断）：** 第一节曾把 9 条记为“自建客户端实现”，其中只有 4 条成立。修订后的核对脚本把三种事实分开测量：`IMPLEMENTED_IN_SOURCE` 6 条 ＝ A018—A021（真客户端，定位到 `shared/evidence_connectors.py:61/93/114/153`）＋ A008（`services/python-workers/media/worker_transcribe.py:158` 的 VAD 使用）＋ A009（`shared/adapter_fixtures.py:135` 的导入探测，`app/ingestion/multi_format.py:297` 同现）；`STUB_IN_SOURCE` 2 条 ＝ A002、A003（`shared/bakeoff_engines.py`，文件自述 unavailable-honest）；`MENTIONED_IN_SOURCE` 2 条 ＝ A011（`mozilla` 只出现在文档字符串与 `developer.mozilla.org` 域名条目里，与 Mozilla Readability 无关）、A006（`whisper.cpp` 仅在提及处）。**命名、桩、提及、实现由此不再混为一谈。**
- **更正二（已修复）：** `VENDORED_ONLY` 与 `DECLARED_AND_VENDORED` 各 1 条的“实拷”证据其实是文件名命中——`shared/audio_vad.py` 自述为 Silero VAD 的 unavailable-honest 桩，`shared/json_canvas.py` 是第一方模块。`shared/` 已从 vendor 根移除，且只有“非空目录”才算实拷；现在没有任何一行是 `VENDORED_ONLY` 或 `DECLARED_AND_VENDORED`。
- **根因与修复（2026-10-06）：** 原脚本把“整词命中任一来源”记为 `IMPLEMENTED_IN_SOURCE`、把“文件名含该项词”记为 `VENDORED`，并把 `__pycache__/*.pyc`、README 词、生成目录字样都当作实现证据；又因为整词匹配，`crossref` 匹配不到 `CrossrefClient`，四条真客户端的判定实际是靠 `.pyc` 与文档字符串撑起来的。修订后：按标识符判定（含 `DataCiteClient`/`OpenAlexClient` 的跨词拼接）、注释与文档字符串不算实现、编译产物与生成目录排除、桩按“命中处附近的不可用标记”判定、`shared/` 不再视为 vendor 根。`tests/workflow/test_oss_disposition_evidence.py` 新增断言固定这些区别（命名/桩/提及/实现四态、定位中不出现 `__pycache__`、没有“文件名即实拷”）。
- 本节不改动 §一—§四的原始事实陈述，也不改写修订前的证据哈希（`3eb0634b…`、`158c1d80…` 保留为修订前状态）；两者不一致时以本节为准。

## 四、未做的部分（明确边界）

- **未修改**该处置文档，未把任何行改写为"已吸收"或"未吸收"。本节只提交可核对的证据。
- 369 池条目仍保持"判定框架"状态：文档 `not_done_here` 自述"本文件不安装任何项目……填充 369 行需要基准比较存在之后才是机械工作"。本轮未虚填。
- 未安装任何捐赠项。`NONE` 的 12 条保持原状。
