"""The three launch profiles must declare the same capability routes.

A capability exists in a launch only if the profile declares it, and the mapping from capability
to worker script is written out in three separate places::

    scripts/release/stage_backend_runtime.py   ROUTE_SCRIPTS      (staged runtime, ships Green)
    scripts/launch/desktop_launch.py           _route_workers     (dev desktop launch)
    scripts/release/assemble_green_candidate.py route_workers     (candidate assembly)

That duplication has already cost real time twice: `machine.answer` was declared in one place and
not another, and later `search.semantic` / `course.general` shipped in the workers directory while
two of the three profiles never declared them, so a packaged product answered
`503 derived worker is not registered` for routes whose code was finished. These assertions make
the three lists agree or fail, instead of leaving the difference to be discovered by hand.
"""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKERS = ROOT / "services" / "python-workers"

SOURCES = {
    "stage_backend_runtime.py": (ROOT / "scripts/release/stage_backend_runtime.py", ("ROUTE_SCRIPTS",)),
    "desktop_launch.py": (ROOT / "scripts/launch/desktop_launch.py", ("_route_workers",)),
    "assemble_green_candidate.py": (ROOT / "scripts/release/assemble_green_candidate.py", ("route_workers",)),
}


def _literal(node):
    """The dict literal behind an assignment, with strings and 1-tuples normalised."""
    if isinstance(node, ast.Dict):
        out = {}
        for key, value in zip(node.keys, node.values):
            if not isinstance(key, ast.Constant) or not isinstance(key.value, str):
                continue
            if isinstance(value, ast.Tuple) and len(value.elts) == 1:
                value = value.elts[0]
            if not isinstance(value, ast.Constant) or not isinstance(value.value, str):
                continue
            out[key.value] = value.value
        return out
    return {}


def declared(name):
    """capability -> path relative to services/python-workers, read from the source itself."""
    path, targets = SOURCES[name]
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            names = [t.id for t in node.targets if isinstance(t, ast.Name)]
            value = node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names, value = [node.target.id], node.value
        else:
            continue
        if not any(target in names for target in targets):
            continue
        found.update(_literal(value))
    return {capability: script[len("workers/"):] if script.startswith("workers/") else script
            for capability, script in found.items()}


def test_every_profile_declares_a_non_empty_route_set():
    for name in SOURCES:
        routes = declared(name)
        assert routes, f"{name} declares no capability routes; the parser or the file changed shape"


def test_the_three_profiles_declare_the_same_routes():
    reference_name = "stage_backend_runtime.py"
    reference = declared(reference_name)
    for name in SOURCES:
        routes = declared(name)
        missing = sorted(set(reference) - set(routes))
        extra = sorted(set(routes) - set(reference))
        assert not missing, f"{name} does not declare {missing}, which {reference_name} declares"
        assert not extra, f"{name} declares {extra}, which {reference_name} does not"
        for capability, script in routes.items():
            assert script == reference[capability], (
                f"{name} points {capability} at {script}, {reference_name} at {reference[capability]}")


def test_every_declared_worker_script_exists():
    for name in SOURCES:
        for capability, script in declared(name).items():
            assert (WORKERS / script).is_file(), (
                f"{name} declares {capability} at {script}, which is not in services/python-workers")
