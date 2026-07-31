# Third-Party Notices

ArcheAxis OS / Cognitive-Loop-OS is licensed under the MIT License; see
[`LICENSE`](LICENSE). That license does not replace the licenses of third-party
packages, bundled binaries, fonts, or other components.

## Declared direct Python dependencies

The release dependency contract is `pyproject.toml` plus the exact resolved
`uv.lock`. At version 0.4.1 the direct runtime declarations are:

`fastapi`, `python-multipart`, `uvicorn`, `pydantic`, `numpy`, `requests`,
`pyyaml`, `beautifulsoup4`, `defusedxml`, `apscheduler`, `sqlite-vec`, `loguru`,
`structlog`, `markitdown`, `trafilatura`, `networkx`, `litellm`, `pillow`, and
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