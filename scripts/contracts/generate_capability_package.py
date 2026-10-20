"""从能力包声明Schema生成TS；只生成类型，不建立安装/运行注册器。"""

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "packages/contracts/v2/capability-package.schema.json"
TARGET = ROOT / "frontend/src/api/generated/capability-package.ts"


def ts(node):
    if "$ref" in node:
        return node["$ref"].split("/")[-1]
    if "const" in node:
        return json.dumps(node["const"])
    if "enum" in node:
        return " | ".join(json.dumps(v) for v in node["enum"])
    if "anyOf" in node:
        return " | ".join(ts(v) for v in node["anyOf"])
    kind = node.get("type")
    if kind == "object":
        props = node["properties"]
        required = node["required"]
        return (
            "{ "
            + "; ".join(
                f"{key}{'' if key in required else '?'}: {ts(value)}"
                for key, value in props.items()
            )
            + " }"
        )
    if kind == "array":
        return "Array<" + ts(node["items"]) + ">"
    if kind not in {"string", "integer", "number", "boolean", "null"}:
        raise ValueError("UNSUPPORTED_SCHEMA_CONSTRUCT")
    return {"integer": "number"}.get(kind, kind)


def generate(source=SOURCE, target=TARGET, check=False):
    raw = source.read_bytes()
    schema = json.loads(raw)
    result = "// Generated from capability-package.schema.json; declaration only, no runtime authority.\n"
    result += "// schema_sha256=" + hashlib.sha256(raw).hexdigest() + "\n"
    result += (
        "\n".join(f"export type {name} = {ts(node)};" for name, node in schema["$defs"].items())
        + "\n"
    )
    if check:
        return target.is_file() and target.read_text(encoding="utf-8") == result
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(result, encoding="utf-8", newline="\n")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--schema", type=Path, default=SOURCE)
    parser.add_argument("--target", type=Path, default=TARGET)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    raise SystemExit(0 if generate(args.schema, args.target, args.check) else 1)
