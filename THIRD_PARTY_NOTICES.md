# Third-Party Notices

ArcheAxis Knowledge / archeaxis-workspace is licensed under the MIT License; see
[`LICENSE`](LICENSE). That license does not replace the licenses of third-party
packages, bundled binaries, fonts, or other components.

## Declared direct Python dependencies

The release dependency contract is `pyproject.toml` plus the exact resolved
`uv.lock`. At version 0.4.2 the direct runtime declarations are:

`fastapi`, `python-multipart`, `uvicorn`, `pydantic`, `numpy`, `requests`,
`pyyaml`, `beautifulsoup4`, `defusedxml`, `apscheduler`, `sqlite-vec`, `loguru`,
`structlog`, `markitdown[pdf]` (with `pdfminer-six`, `pdfplumber`, and
`pypdfium2` for PDF extraction), `trafilatura`, `networkx`, `litellm`,
`pillow`, and
`pytesseract`.

Optional or development groups additionally declare `setuptools`,
`playwright`, `httpx2`, `jinja2`, `jsonschema`, `pytest`, `ruff`, `tomli`,
`newspaper4k`, `readabilipy`, `youtube-transcript-api`, `mypy`, `pre-commit`,
`crawl4ai`, `langfuse`, and `promptfoo`. The desktop dependency contract is
`desktop/package.json`, `desktop/package-lock.json`, `desktop/src-tauri/Cargo.toml`,
and `desktop/src-tauri/Cargo.lock`.

The lockfiles, not this summary, are authoritative for exact names, versions,
and transitive packages. Each component remains subject to its own upstream
license and notices. A redistributor must preserve those terms and audit the
exact built artifact; this document does not claim that every optional package
is bundled into every distribution.

## External tools

Some development or verification paths can invoke separately installed tools
such as Git, GitHub CLI, Tesseract OCR, Node.js/npm, Rust/Cargo, and NSIS. They
are not relicensed by this repository. Their presence in a build log is not
proof that they are included in a published asset.

## Vendored web assets

The workspace UI bundles third-party browser assets that are redistributed
with the wheel under their own licenses:

| Asset | Version | License | Bundled location |
|---|---|---|---|
| PDF.js (`pdf.min.js`, `pdf.worker.min.js`) | 3.11.174 | Apache-2.0 | `app/workspace/ui/assets/` |
| PDF.js LICENSE | 3.11.174 | Apache-2.0 | `app/workspace/ui/assets/licenses/pdfjs-3.11.174-LICENSE.txt` |

PDF.js is © Mozilla and contributors, licensed under the Apache License 2.0.
The full license text is preserved alongside the assets; redistribution must
retain that notice. See `app/workspace/ui/assets/licenses/pdfjs-3.11.174-LICENSE.txt`.

## Vendored models

| Asset | Version | License | Bundled location |
|---|---|---|---|
| Magika ONNX model (`model.onnx`, `config.min.json`) | standard_v3_0 | Apache-2.0 | `shared/models/magika/` |
| Magika LICENSE | standard_v3_0 | Apache-2.0 | `shared/models/magika/LICENSE` |

Magika is © Google LLC, licensed under the Apache License 2.0. The full
license text is preserved alongside the model; inference code is
`shared/file_detection.py` (pure Python, no magika pip dependency).

## 2026-08-11 上游许可纠错与补充

本轮吸收审计（来源：`ArcheAxis_Workspace_Project_History_and_OSS_Absorption_Master_Atlas_v1.md`）
在上游仓库当前默认分支上重新核验了以下项目的许可证，发现多处历史记录需更正：

| 项目 | 旧记录 | 2026-08-11 更新 |
|---|---|---|
| Marker (`datalab-to/marker`) | "GPL-3.0" | **代码 Apache-2.0**；权重另受修改版 OpenRAIL-M 许可 |
| MinerU (`opendatalab/MinerU`) | "Apache-2.0" | Apache-2.0 + 附加 MAU/收入阈值与在线服务标识义务 |
| H5P PHP Library (`h5p/h5p-php-library`) | "core MIT" | **GPL-3.0**（因 HTML Purifier 依赖、README 明确声明） |
| Phoenix (`Arize-ai/phoenix`) | "开源观测工具" | **Elastic License 2.0**（source-available，不是 open-source） |
| tldraw (`tldraw/tldraw`) | "候选画图 SDK" | 生产使用要求商业 license key，不是默认 OSS 组件 |
| Firecrawl (`firecrawl/firecrawl`) | 单一许可总结 | 主体 **AGPL-3.0**；部分 SDK/UI **MIT**（组件级审查必需） |
| Kùzu (`kuzudb/kuzu`) | "graph DB 候选" | **上游已归档**（2025-10-10） |
| LiteLLM (`BerriAI/litellm`) | "MIT" | 核心 MIT；`enterprise/` 目录另许可 |
| Langfuse (`langfuse/langfuse`) | "MIT" | 核心 MIT；`ee/` 目录另许可 |
| Meilisearch (`meilisearch/meilisearch`) | "MIT" | MIT AND BUSL-1.1；EE 路径另许可 |

上述项目在通过独立的 exact-revision RDR（ReuseDecisionRecord）且 Owner 明确授权前不得进入依赖锁、vendor 目录或发行物。现有已接入组件（LiteLLM、Langfuse）继续保留薄 Adapter 模式，不扩大能力声明。

权威吸收决策见 `docs/truth/SUPPLY_CHAIN_LEDGER.json`（v2，46 组件）。
