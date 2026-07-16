"""Local trace adapter — writes traces locally. Langfuse optional upgrade."""

import json
from pathlib import Path

from shared.approved_paths import ApprovedRoots, ApprovedRootsError

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_APPROVED_ROOTS = ApprovedRoots(output_roots=[_PROJECT_ROOT / "data"])


def write_trace(trace: dict, output_dir: str = "data/traces") -> Path:
    requested = Path(output_dir)
    if not requested.is_absolute() and requested.parts[:1] == ("data",):
        requested = Path(*requested.parts[1:])
    try:
        output = _APPROVED_ROOTS.resolve_output(requested)
    except ApprovedRootsError as exc:
        raise ValueError("trace output must stay under the approved data root") from exc
    output.mkdir(parents=True, exist_ok=True)
    path = output / f"{trace.get('id', 'trace')}.json"
    path = _APPROVED_ROOTS.resolve_output(path)
    path.write_text(json.dumps(trace, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
