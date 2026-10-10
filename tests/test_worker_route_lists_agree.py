"""The capability routes come from one file, and every caller reads it.

The mapping used to be written out three times - in the staged runtime, the desktop launch and the
candidate assembler - and the copies drifted twice in ways that reached the shipped product, so a
finished route answered 503 because one profile had not declared it. These assertions keep the one
source and check that each caller reads it rather than carrying its own copy.
"""

import importlib.util
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "services" / "python-workers" / "routes.json"
LOADER = ROOT / "scripts" / "release" / "worker_routes.py"
SCHEMA = "archeaxis.worker-routes/v1"
CALLERS = {
    "stage_backend_runtime.py": ROOT / "scripts/release/stage_backend_runtime.py",
    "desktop_launch.py": ROOT / "scripts/launch/desktop_launch.py",
    "assemble_green_candidate.py": ROOT / "scripts/release/assemble_green_candidate.py",
}


def _routes():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))["routes"]


def _loader():
    spec = importlib.util.spec_from_file_location("test_worker_routes", LOADER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_manifest_is_the_single_mapping_and_its_scripts_exist():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert data["schema"] == SCHEMA
    routes = data["routes"]
    assert routes, "the manifest declares no capability routes"
    for capability, scripts in routes.items():
        assert scripts, f"{capability} names no worker script"
        for script in scripts:
            assert (ROOT / "services" / "python-workers" / script).is_file(), (
                f"{capability} points at {script}, which is not in services/python-workers")


def test_every_caller_reads_the_manifest():
    for name, path in CALLERS.items():
        text = path.read_text(encoding="utf-8")
        assert "worker_routes.load(" in text, f"{name} does not read the single mapping"


def test_no_caller_still_writes_the_mapping_out_by_hand():
    scripts = [s for group in _routes().values() for s in group]
    for name, path in CALLERS.items():
        text = path.read_text(encoding="utf-8")
        for script in scripts:
            for form in (script, "workers/" + script):
                assert f'"{form}"' not in text and f"'{form}'" not in text, (
                    f"{name} still writes {form} out by hand instead of reading the manifest")


def test_the_loader_returns_one_shape_under_any_prefix():
    module = _loader()
    plain = module.load()
    prefixed = module.load(prefix="workers/")
    assert sorted(plain) == sorted(prefixed) == sorted(_routes())
    for capability, scripts in prefixed.items():
        assert all(script.startswith("workers/") for script in scripts)
        assert plain[capability] == tuple(s[len("workers/"):] for s in scripts)


def test_the_loader_refuses_a_manifest_that_is_not_ours():
    module = _loader()
    # Bytes, put back byte for byte. Writing text would let the host translate newlines and
    # rewrite a tracked file, leaving the working tree dirty for every later check that reads
    # git diff - a test must not be able to dirty the repository it is checking.
    original = MANIFEST.read_bytes()
    try:
        MANIFEST.write_bytes(b'{"schema": "something-else", "routes": {}}')
        try:
            module.load()
            raise AssertionError("a foreign schema must be refused")
        except ValueError:
            pass
    finally:
        MANIFEST.write_bytes(original)


def test_the_transport_dispatches_exactly_the_declared_routes() -> None:
    """`routes.json` is what the Core may enqueue; the transport table is what answers.

    The two were allowed to differ, and that is how a route ends up registered in the Core,
    claimed by a capability, and still answered with `unsupported capability` the moment a real
    job arrives - a declaration nobody can reach. The diarization route hit exactly this.
    """
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "route_transport", ROOT / "services" / "python-workers" / "transport" / "text_ndjson.py")
    assert spec and spec.loader
    transport = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(transport)

    declared = set(_routes())
    dispatched = set(transport.ROUTES)
    rust_kinds = Path(ROOT / "crates" / "archeaxis-application" / "src" / "attempts.rs").read_text(
        encoding="utf-8")
    rust_caps = {match.group(2) for match in re.finditer(
        r'^\s*\("([a-z._-]+)", "([a-z._-]+)", "[^"]+"\),', rust_kinds, re.MULTILINE)}
    for capability in sorted(declared - dispatched):
        # A capability may sit outside the job transport only while no Core job kind reaches it:
        # the derived trio answer over their own request contracts, and the transport says so -
        # its job protocol requires empty parameters, so a route there would fail its own
        # validation. The moment a job kind names one, that exemption becomes a dead declaration.
        assert capability not in rust_caps, (
            f"{capability} is enqueued as a Core job but the transport cannot serve it: a real job "
            "would be answered 'unsupported capability', which is how the diarization route was left")
    for capability, route in transport.ROUTES.items():
        if capability not in declared:
            # the one other-direction asymmetry kept on purpose: the Core's native text capability
            # keeps its legacy alias here without being declared as a worker route.
            assert capability == "text.extract", capability
            continue
        worker = ROOT / Path(route["worker"])
        assert worker.is_file(), f"{capability} dispatches to a missing {route['worker']}"
        # the Core's own mapping names the same script, or the two tables disagree about who runs
        assert [Path(ROOT / "services" / "python-workers" / script).name
                for script in _routes()[capability]] == [worker.name], capability
        assert route["media_types"], f"{capability} dispatches but accepts nothing"
