# 开源池捐赠项处置的实测核对（2026-10-06）

对象：`docs/current/AAOS-OSS-DONOR-DISPOSITION-V2-20261002.json`（47 条供应链 + 11 条能力吸收 + 369 池规模声明）。
方法：只读核对，不修改该文档。脚本 `scripts/audit/oss_disposition_evidence.py`，逐条在**声明文件**（`pyproject.toml`、`uv.lock`、`requirements.txt`、`frontend/package*.json`）、**流水线**（`.github/workflows/*.yml`、`scripts/ci/*`）、**源码**（`shared/`、`services/`、`app/`、`crates/`、`frontend/src/`）与**vendor 根**中按整词匹配查找该项的证据，并输出每条证据的确切文件与行号。

证据：`.project-local/task-runtime/aaos01-oss-evidence-20261006/report.txt`（SHA-256 `3eb0634b11ac1eb355d55822765fee3fc7a93507e44cdeded54e7666b314beee`）与同目录 `disposition-evidence.json`（SHA-256 `158c1d800fe038c0622bbab43c08bce8647e1f25a795e739995adce592843711`）。

## 一、实测分布（47 条）

| 实测状态 | 条数 | 含义 |
| --- | --- | --- |
| `DECLARED` | 24 | 在声明文件/流水线中确有该依赖或其调用 |
| `IMPLEMENTED_IN_SOURCE` | 9 | 无依赖声明，但在本仓库源码中以自建客户端实现（Crossref / DataCite / OpenAlex / Wikidata 等 REST 项） |
| `DECLARED_AND_VENDORED` | 1 | 既有声明又有实拷 |
| `VENDORED_ONLY` | 1 | 只有实拷，无依赖声明 |
| `NONE` | 12 | 声明、流水线、源码、vendor 四处均无证据 |

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

先前的处置表述里，`A023 pip-audit` 与 `A024 Gitleaks` 一度被写成未吸收——更正依据是本轮实测：两者由 `.github/workflows/ci.yml`（第 153、152 行）以流水线工具形式实际调用，属于"以 CI 门禁形式吸收"，不体现在任何依赖清单里。核对脚本因此把**流水线调用**列为独立证据来源；只看依赖清单会给出一份与事实相反的结论。

## 四、未做的部分（明确边界）

- **未修改**该处置文档，未把任何行改写为"已吸收"或"未吸收"。本节只提交可核对的证据。
- 369 池条目仍保持"判定框架"状态：文档 `not_done_here` 自述"本文件不安装任何项目……填充 369 行需要基准比较存在之后才是机械工作"。本轮未虚填。
- 未安装任何捐赠项。`NONE` 的 12 条保持原状。
