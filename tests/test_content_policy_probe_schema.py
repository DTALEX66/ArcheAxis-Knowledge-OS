"""Keep the independent runtime probe aligned with the canonical SQLite schema."""

import ast
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_content_policy_probe_requires_current_canonical_schema():
    canonical = (ROOT / "crates/archeaxis-store-sqlite/src/lib.rs").read_text(encoding="utf-8")
    versions = re.findall(r"pub const SCHEMA_VERSION: i64 = (\d+);", canonical)
    assert len(versions) == 1
    probe = ast.parse((ROOT / "scripts/probes/aaos01_content_policy_runtime_loop.py").read_text(encoding="utf-8"))
    required = []
    for node in ast.walk(probe):
        if not isinstance(node, ast.Assert) or not isinstance(node.test, ast.Compare):
            continue
        left = node.test.left
        if (
            isinstance(left, ast.Subscript)
            and isinstance(left.value, ast.Name)
            and left.value.id == "workspace_info"
            and isinstance(left.slice, ast.Constant)
            and left.slice.value == "schema_version"
        ):
            assert len(node.test.ops) == 1 and isinstance(node.test.ops[0], ast.Eq)
            assert len(node.test.comparators) == 1
            required.append(ast.literal_eval(node.test.comparators[0]))
    assert required == [int(versions[0])]
