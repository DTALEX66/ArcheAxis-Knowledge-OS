from pathlib import Path
import json

try:
    import jsonschema
except ImportError:
    raise SystemExit("请先安装 jsonschema：pip install jsonschema")

BASE = Path(__file__).resolve().parents[1]
SCHEMAS = BASE / "schemas"
FIXTURES = BASE / "fixtures"

pairs = {
    "course_pack.schema.json": "sample_course_pack.json",
    "context_pack.schema.json": "sample_context_pack.json",
    "taskpack.schema.json": "sample_taskpack.json",
    "execution_trace.schema.json": "sample_execution_trace.json",
    "machine_lesson.schema.json": "sample_machine_lesson.json",
    "intake_card.schema.json": "sample_intake_card.json",
    "engineering_contract.schema.json": "sample_engineering_contract.json",
    "obsidian_projection.schema.json": "sample_obsidian_projection.json",
    "daily_brief.schema.json": "sample_daily_brief.json",
    "open_source_project_profile.schema.json": "sample_open_source_project_profile.json",

}

def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def main():
    failed = 0
    for schema_name, fixture_name in pairs.items():
        schema_path = SCHEMAS / schema_name
        fixture_path = FIXTURES / fixture_name
        schema = load_json(schema_path)
        fixture = load_json(fixture_path)
        try:
            jsonschema.validate(instance=fixture, schema=schema)
            print(f"PASS {fixture_name}")
        except jsonschema.ValidationError as exc:
            failed += 1
            print(f"FAIL {fixture_name}: {exc.message}")
    if failed:
        raise SystemExit(f"{failed} fixture(s) failed validation.")
    print("All fixtures passed.")

if __name__ == "__main__":
    main()
