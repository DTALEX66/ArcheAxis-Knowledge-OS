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
`crawl4ai`, `langfuse`, and `promptfoo`.

Admitted 2026-10-07 for R15/F14: `xlrd` 2.0.2, declared in the `ci-adapters` group and read by
`services/python-workers/document/worker_office.py` for the legacy binary `.xls` family. Licence
as shipped: `BSD` in the package metadata, with two BSD-style clauses in its `LICENSE` file
(3,771 bytes, sha256 `b5a5dbce60265e305a815a6cb83ed07f24519d8ba644f2a307994488bced8815`) - the main one covering Stephen John Machin / Lingfo Pty
Ltd work, the second covering the 2001 David Gilbert contribution. Windows probe: the committed
fixture `tests/fixtures/golden/golden-xls-anchor.xls` (5,632 bytes, sha256
`3225b8bb590f799dc0a16a92118a1f80aec8cde53e0b4c71bc200f451aa72353`) was read on this host through
the route, producing two sheet projections, cell-type counts and two declared CSV conversions.
The fixture is project-authored synthetic content (no personal data); it was written once with
`xlwt` 1.3.0 as an authoring tool, which is deliberately **not** a declared runtime or test
dependency, so no lane needs it to reproduce the read. The desktop dependency contract is
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

### Probed external sidecar: antiword (not bundled, not required)

Admitted as a *probed* reader on 2026-10-07 for R15/F14: `.doc` (Word 97 binary, OLE2) reaches
`office.structure` through `antiword`, an external console binary. The product never assumes it
exists. `services/python-workers/document/worker_office.py` resolves it from
`ARCHEAXIS_ANTIWORD_CMD`, then the declared capability manifest, then `PATH`, and asks the binary
who it is (`-h`) before handing it a document; an unresolved or unidentifiable binary is a named
failure that projects nothing. Nothing is downloaded, installed, copied or relicensed by this
repository. Measured on this host: `antiword.exe` 284,448 bytes, sha256 `d30a37489c64ada474d8d5aa5abb0778a6955d3ce6cdbb7c8c659e37b89d3da9`,
self-reporting `Version: 0.37  (21 Oct 2005)`, `Author: (C) 1998-2005 Adri van Os`,
`Status: GNU General Public License`, shipped inside the Git for Windows mingw64 bundle with 30
character-mapping files beside it. The package index that redistributes it names the licence as GPL-3.0-or-later and
the version as 0.37-3; the binary itself states only
`Status: GNU General Public License`, so both are recorded rather than merged into one
claim. `docs/truth/SUPPLY_CHAIN_LEDGER.json` row A025 now carries this disposition. What
is still open is the binding to a declared external root, which is why the capability
manifest has no antiword entry and resolution today is environment or PATH.

### Third-party test fixture: `tests/fixtures/golden/golden-word-anchor.doc`

32,768 bytes, sha256 `5ca19b67876f284a0e04ed06df44a004f850629a871fe522d014e1fdff912799`, OLE2 container magic `D0 CF 11 E0 A1 B1 1A E1`, Word 97
`nFib 0x00C1` with a `Word.Document.8` registration block - a genuine Word-authored document, not
one written by tooling for this test. Published as Apache Tika's
`tika-parser-microsoft-module/src/test/resources/test-documents/testWORD.doc`, retrieved from the
pinned commit `b8a6916eab70ccdb5d4551c69be1a46af29c2cff` (annotated tag `3.3.2`), git blob
`c1f4f3d0b0c1e475bf03e9eba3ed7c7ac166d557`, and redistributed here under the
**Apache License, Version 2.0** of that project with attribution, as recorded in
`tests/fixtures/golden/manifest.json`. It contains no personal data; its author is named by the
file's own metadata as published by Tika. It is read through the sidecar above, so a host without
the sidecar cannot reproduce the projection - which the fixture record states rather than hides.

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
- Apache Tika 4.1.0 (`tika-app` distribution), Apache License 2.0 - https://tika.apache.org/ ; used only as a probed external sidecar for `.ppt` text extraction, resolved from the declared external tool root and never bundled with this repository.
- Azul Zulu Community JRE 21.0.12.1 (build 21.52.203), GPLv2 with the Classpath Exception - https://www.azul.com/downloads/ ; the runtime that executes the Tika sidecar above. Local placement under the external tool root, not a system install and not redistributed here.
- Third-party test fixture: `tests/fixtures/golden/golden-ppt-anchor.ppt` - a Microsoft PowerPoint 97 presentation redistributed under Apache-2.0 from Apache Tika's microsoft-module test resources, pinned commit b8a6916eab70ccdb5d4551c69be1a46af29c2cff (tag 3.3.2), 16,384 bytes, sha256 499ccd0de7c0778afa4f6ed08793afd2406b62547373a619a5a78658ae65c4b7, git blob b48cfaf2bd7045c21c5f65e1478725e8cee84ed7.
