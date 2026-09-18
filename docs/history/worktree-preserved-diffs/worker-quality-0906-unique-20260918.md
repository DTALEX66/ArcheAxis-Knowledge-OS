# Preserved unique content - worktree worker-quality-0906 (2026-09-18)

Extracted read-only from `.project-local/worktrees/worker-quality-0906`.
Only lines that exist on that worktree's disk but NOT in the current `main`
version of the same file are listed, with one line of context. `main` has
advanced by hundreds of lines in these files since the worktree's base
Total unique lines across 9 checked files: 56
(2026-09-06), so this is an archival excerpt for semantic review, not a
patch that can be applied directly.

## `services/python-workers/document/worker_text.py`

unique lines: 10 (main has 449 lines)

```text
  ctx| #!/usr/bin/env python3
  NEW| # -*- coding: utf-8 -*-
  ctx|
  NEW| Provenance: pure-parser behaviour distilled from the legacy ingestion
  ctx| Provenance: pure-parser behaviour distilled from the legacy ingestion
  NEW| adapters (app/ingestion/multi_format.py `_via_read`/`_decode_text_bytes`
  ctx| adapters (app/ingestion/multi_format.py `_via_read`/`_decode_text_bytes`
  NEW| semantics) without importing the legacy package.
  ctx| Usage:
  NEW|     python worker_text.py <input-file>
  ctx|
  NEW| def extract(path: str) -> dict:
  ctx|         "params": {"decode": decode_note["encoding"], "cap_lines": 5000,
  NEW|                    "coverage_unit": "line anchors", "line_splitting": "str.splitlines(keepends=True)"},
  ctx| def main() -> int:
  NEW|     if len(sys.argv) != 2:
  ctx|     if len(sys.argv) != 2:
  NEW|         print(json.dumps({"error": "usage: worker_text.py <input-file>"}))
  ctx|     try:
  NEW|         out = extract(sys.argv[1])
```

## `services/python-workers/evaluation/worker_quality.py`

unique lines: 1 (main has 224 lines)

```text
  ctx| #!/usr/bin/env python3
  NEW| # -*- coding: utf-8 -*-
```

## `services/python-workers/vision/worker_ocr.py`

unique lines: 17 (main has 554 lines)

```text
  ctx| #!/usr/bin/env python3
  NEW| # -*- coding: utf-8 -*-
  ctx|         raise RuntimeError("tesseract binary not found on PATH (OCR engine unavailable)")
  NEW|     return binary
  ctx|         binary = _tesseract()
  NEW|         version = subprocess.run(
  ctx|             raise RuntimeError(f"tesseract version probe failed (exit {version.returncode})")
  NEW|         listed = subprocess.run(
  ctx|
  NEW|     plain = subprocess.run(
  ctx|
  NEW|     tsv = subprocess.run(
  ctx|                 if len(fields) < 12:
  NEW|                     continue
  ctx|                     conf = float(fields[10])
  NEW|                 except (ValueError, IndexError):
  ctx|                 except (ValueError, IndexError):
  NEW|                     continue
  ctx|                             "confidence": round(conf, 1),
  NEW|                             "x": int(fields[6]),
  ctx|                             "x": int(fields[6]),
  NEW|                             "y": int(fields[7]),
  ctx|                             "y": int(fields[7]),
  NEW|                             "w": int(fields[8]),
  ctx|                             "w": int(fields[8]),
  NEW|                             "h": int(fields[9]),
  ctx|                        "tessdata_dir": str(tessdata_dir) if tessdata_dir is not None else None,
  NEW|                        "tsv_renderer": "tessedit_create_tsv=1", "warnings": warnings},
  ctx|             "loss_note": (
  NEW|                 "OCR text with per-word boxes/confidence; reading order follows "
  ctx|                 "OCR text with per-word boxes/confidence; reading order follows "
  NEW|                 "Tesseract layout; diagram semantics, handwriting and low-quality "
  ctx|                 "Tesseract layout; diagram semantics, handwriting and low-quality "
  NEW|                 "region retries are separate lanes"
```

## `services/python-workers/transport/text_ndjson.py`

unique lines: 13 (main has 533 lines)

```text
  ctx|
  NEW| def execute(request, staging: Path):
  ctx|         request[field] = integer_value(request[field], minimum)
  NEW|     if request["capability"] != "text.extract":
  ctx|         raise Rejected("unsupported capability")
  NEW|     if request["capability_version"] != "1" or request["protocol_minor"] != 0:
  ctx|             or request["parameters"] or not isinstance(request["inputs"], list) or len(request["inputs"]) != 1):
  NEW|         raise Rejected("text.extract v1 requires one input, integer minor and empty parameters")
  ctx|         raise Rejected("input URI must match its sha256")
  NEW|     allowed_media = {"text/plain", "text/markdown", "text/csv", "text/tab-separated-values", "application/json", "application/xml", "text/xm
  ctx|     if asset["media_type"].split(";", 1)[0].strip().lower() not in allowed_media:
  NEW|         raise Rejected("unsupported text media type", "AAK-VAL-002")
  ctx|     check_deadline()
  NEW|     spec = importlib.util.spec_from_file_location("worker_text", ROOT / "services/python-workers/document/worker_text.py")
  ctx|     spec = importlib.util.spec_from_file_location("worker_text", ROOT / "services/python-workers/document/worker_text.py")
  NEW|     worker = importlib.util.module_from_spec(spec)
  ctx|     worker = importlib.util.module_from_spec(spec)
  NEW|     spec.loader.exec_module(worker)
  ctx|     spec.loader.exec_module(worker)
  NEW|     result = worker.extract(str(source))
  ctx|           "protocol": {"major": 1, "min_minor": 0, "max_minor": 0},
  NEW|           "worker": {"name": "python-worker-text-ndjson", "version": "1"},
  ctx|           "worker": {"name": "python-worker-text-ndjson", "version": "1"},
  NEW|           "capabilities": ["text.extract"], "schemas": OUTPUT_SCHEMAS})
  ctx|         response = response_for(request)
  NEW|         outputs, measurements, warnings = execute(request, args.staging_root)
```

## `scripts/maintenance/inventory_project.py`

unique lines: 7 (main has 328 lines)

```text
  ctx| OPAQUE_NAMES = frozenset({
  NEW|     ".git", ".codex", ".dsh", ".hermes", ".openhuman", ".claude",
  ctx|                 # Recheck queued directories before opening; never resolve targets.
  NEW|                 if is_reparse(directory.lstat()):
  ctx|                     continue
  NEW|                 with os.scandir(directory) as entries:
  ctx|                         entry_group = entry.name if directory == root else group
  NEW|                         if entry.name.casefold() in opaque:
  ctx|                         try:
  NEW|                             info = path.lstat()
  ctx|     report = inventory_project(args.root, exclude_names=args.exclude_name)
  NEW|     print(json.dumps(report, ensure_ascii=False, indent=2))
  ctx|     print(json.dumps(report, ensure_ascii=False, indent=2))
  NEW|     return 1 if report["errors"] else 0
```

## `tests/contract/test_contract_examples.py`

unique lines: 1 (main has 241 lines)

```text
  ctx|     assert "launchToken" in security_schemes
  NEW|     assert security_schemes["launchToken"]["type"] == "http"
```

## `tests/workers/test_quality_regressions.py`

unique lines: 2 (main has 195 lines)

```text
  ctx|         report = self.evaluate(b"a", b"a")
  NEW|         self.assertTrue(callable(getattr(quality, "validate_report_metrics", None)), "metric boundary validation missing")
  ctx|         report = self.evaluate(b"a", b"a")
  NEW|         self.assertTrue(callable(getattr(quality, "validate_report_metrics", None)), "metric boundary validation missing")
```

## `tests/workers/test_text_ndjson.py`

unique lines: 3 (main has 335 lines)

```text
  ctx|         (self.staging / "output").mkdir()
  NEW|         # The integration branch owns the current shared protocol schema.
  ctx|         # The integration branch owns the current shared protocol schema.
  NEW|         main_root = Path(os.environ["ARCHEAXIS_DEV_ROOT"]).parent
  ctx|         main_root = Path(os.environ["ARCHEAXIS_DEV_ROOT"]).parent
  NEW|         schema = json.loads((main_root / "packages/contracts/v1/worker-protocol.schema.json").read_text(encoding="utf-8"))
```

## `tests/maintenance/test_inventory_project.py`

unique lines: 2 (main has 286 lines)

```text
  ctx|     def test_private_directories_and_mixed_hermes_are_opaque_unknown_size(self):
  NEW|         for name in (".codex", ".dsh", ".openhuman", ".hermes"):
  ctx|         def reject_private_scan(path):
  NEW|             self.assertNotIn(Path(path).name, {".git", ".codex", ".dsh", ".openhuman", ".hermes", ".claude"})
```
