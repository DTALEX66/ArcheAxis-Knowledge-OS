"""Local trace adapter — writes traces locally. Langfuse optional upgrade."""
import json
from pathlib import Path


def write_trace(trace: dict, output_dir: str = "data/traces") -> Path:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    path = output / f"{trace.get('id', 'trace')}.json"
    path.write_text(json.dumps(trace, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
