# Online and repository learning corpus — 2026-08-09

## Scope

The supplied Obsidian material is a useful smoke corpus but is not representative
of the full learning-workspace input surface. This round adds a bounded,
traceable corpus without copying it into the repository source tree:

- Python Tutorial, FastAPI Tutorial, and SQLite documentation as HTML.
- MarkItDown README as an open-source Markdown project document.
- JSON Canvas README, v1.0 specification, and sample `.canvas` as Markdown and
  JSON Canvas project knowledge.
- Think Python 2 as a public educational PDF sample.
- The repository's `open_source_project_registry.json`, absorption ledger, and
  related absorption/verification documents as learning knowledge. Project
  source code is not downloaded or executed.

Downloaded inputs, conversion outputs, manifests, hashes, and restart evidence
are retained only under the ignored `.hermes/task-artifacts/web-learning-*`
directory. The source manifest records the URL and licensing/reference page for
each external item.

## Conversion outcome

- Online corpus: 8/8 converted on the dependency-complete packaged runtime;
  restart readback resumed 8/8.
- Repository OSS corpus: 8/8 converted; the two JSON ledgers also converted
  directly and through the resumable path after JSON became a first-class input
  format; restart readback resumed 8/8.
- Formats exercised: HTML, Markdown, JSON Canvas, JSON, and PDF. Existing
  Vault tests continue to cover Markdown, Canvas, TXT, and CSV at scale.
- JSON is preserved as UTF-8 text, with MarkItDown projection when available;
  Canvas remains intentionally degraded until semantic node/edge indexing is
  qualified.

## Boundary

This corpus is for conversion and evidence testing, not for product data
import. No E: drive path was accessed or modified. No external repository was
cloned, executed, or merged; the existing `Obsidian-Assistance` exclusion remains
in force.
