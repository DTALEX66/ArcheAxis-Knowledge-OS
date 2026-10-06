"""The one mapping from capability to the worker script that implements it.

The mapping used to be written out three times - in `stage_backend_runtime.py`,
`desktop_launch.py` and `assemble_green_candidate.py` - and the copies drifted twice in ways that
reached the product: `machine.answer` was declared in one profile and not another, and later
`search.semantic` and `course.general` shipped in the workers directory while two of the three
profiles never declared them, so a packaged product answered 503 "derived worker is not
registered" for routes whose code was finished.

The canonical file is `services/python-workers/routes.json`, beside the workers it names. Every
path in it is relative to that directory; a caller adds the prefix its own layout uses, which is
why the staged runtime and the candidate ask for `workers/` and the desktop launch asks for
nothing.

Only the *first existing* path of a capability is ever declared, by the caller: a route that names
an absent script makes the Core refuse the whole profile, and a capability with no worker present
is left out rather than declared and then failing at job time.
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO / "services" / "python-workers"
MANIFEST = SOURCE_ROOT / "routes.json"
SCHEMA = "archeaxis.worker-routes/v1"


def load(prefix: str = "") -> dict[str, tuple[str, ...]]:
    """Capability -> worker scripts in preference order, each under `prefix`."""
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if data.get("schema") != SCHEMA:
        raise ValueError(f"{MANIFEST.name} is not {SCHEMA}")
    raw = data.get("routes")
    if not isinstance(raw, dict) or not raw:
        raise ValueError(f"{MANIFEST.name} declares no capability routes")
    out: dict[str, tuple[str, ...]] = {}
    for capability, scripts in raw.items():
        if not isinstance(scripts, list) or not scripts:
            raise ValueError(f"{capability} declares no worker script")
        out[capability] = tuple(f"{prefix}{script}" for script in scripts)
    return out
