import json
from pathlib import Path

try:
    import jsonschema
except ImportError as exc:
    raise SystemExit("请先安装 jsonschema：pip install jsonschema") from exc

BASE = Path(__file__).resolve().parents[1]
schema = json.loads((BASE / "schemas" / "github_project_candidate.schema.json").read_text(encoding="utf-8"))
items = json.loads((BASE / "fixtures" / "sample_github_project_candidates.json").read_text(encoding="utf-8"))

failed = 0
for item in items:
    try:
        jsonschema.validate(instance=item, schema=schema)
        print(f"PASS {item.get('candidate_id')}")
    except jsonschema.ValidationError as exc:
        failed += 1
        print(f"FAIL {item.get('candidate_id')}: {exc.message}")

if failed:
    raise SystemExit(f"{failed} candidate(s) failed validation.")
print("All project candidates passed.")
