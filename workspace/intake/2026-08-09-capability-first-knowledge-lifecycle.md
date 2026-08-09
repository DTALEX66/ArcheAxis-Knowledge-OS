# 2026-08-09 Capability-first Knowledge Lifecycle Intake

## Owner clarification

The owner clarified that Crawl4AI and the project referred to as Spidering are not mandatory runtime dependencies. Their useful capabilities are mandatory and may be provided by better maintained, more accurate, more compatible, or more legally suitable open-source implementations. Self-development is allowed only after reusable options cannot satisfy the governed capability contract.

The mandatory product chain is:

```text
search and discovery
→ governed acquisition
→ multi-format conversion
→ evidence and knowledge
→ course and learning-object production
→ human learning and mastery
→ evidence-grounded AI reuse
→ evaluation and feedback
```

## Repository facts

- The existing Web Addendum freezes useful security, RawAsset, Evidence, frontend/backend, recovery, Windows and installed-E2E requirements, but its original acceptance text binds some tasks to Crawl4AI and Spider brands.
- The frozen baseline already defines RawAsset, DerivedDocument, EvidenceAnchor, Claim/Evidence, LearningArtifact, FSRS, cited AI answers and a single-topic loop. It does not fully decompose federated discovery, course production, multi-style learning objects or a provider-neutral end-to-end quality system.
- Current Crawl4AI-named code still does not prove direct Crawl4AI execution. Planning or a dependency entry is not implementation evidence.

## Official-source candidate findings

- Crawlee for Python is Apache-2.0 and exposes HTTP and Playwright crawlers with queue/storage concepts that fit the existing Python backend; it is a high-priority unified-provider benchmark candidate.
- Crawl4AI provides dynamic rendering and LLM-ready extraction, but its LICENSE appends an additional attribution requirement after the Apache-2.0 text. It remains a quality candidate subject to legal and NOTICE review.
- spider-rs/spider is MIT and offers Rust, CLI, Node and Python surfaces for streaming, HTTP-first site crawling with browser-on-demand. It is suitable for a sidecar benchmark, not an automatic dependency.
- Scrapy is BSD-3-Clause and remains a mature static crawling candidate. Playwright is Apache-2.0 and is the browser substrate, not the knowledge model.
- Firecrawl and SearXNG are AGPL-3.0. Their API, job and discovery designs are useful, but default core vendoring is not justified; optional sidecar or reference use requires license and deployment review.
- Docling (MIT), MarkItDown (MIT), Apache Tika (Apache-2.0), Unstructured (Apache-2.0), PaddleOCR/Tesseract (Apache-2.0), Whisper (MIT) and a license-controlled FFmpeg build form a stronger multi-format candidate portfolio than one universal converter.
- Open edX (AGPL-3.0), Moodle and H5P (GPL-3.0) are initially architecture/UX/interoperability references, not products to copy into the core. py-fsrs (MIT) remains the scheduling candidate. xAPI 2.0 semantics can be absorbed locally without requiring a remote LRS.
- Haystack, LlamaIndex, Qdrant and Ragas are optional component/reference candidates. They cannot replace the repository's governed lifecycle, human truth, Evidence or SQLite baseline.

## Decision

A separately hashed capability-first addendum preserves both previously frozen documents and provides the later authoritative interpretation:

- brands are replaceable;
- static, dynamic, site, structured, document, OCR, media, code, course, learning and AI-reuse profiles are not replaceable;
- the Spidering exact URL is no longer an execution blocker;
- selected providers must win a pre-frozen representative benchmark and pass Windows, safety, license, recovery and installed-E2E gates;
- the project should self-build governance, provenance, orchestration and lifecycle integration, not commodity browser/parser/OCR/ASR/database engines unless all legal reusable candidates fail documented acceptance criteria.

## Evidence boundary

This intake and its taskpack are planning/governance artifacts. They do not claim that federated search, Crawlee/Crawl4AI/Spider, Docling/PaddleOCR/Whisper, Course Studio, Learning Player or AI reuse is currently implemented or release-qualified. No E drive content, credentials, private browser state or private corpus was accessed.
