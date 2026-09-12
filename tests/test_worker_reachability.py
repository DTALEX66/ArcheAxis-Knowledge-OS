"""R15: an unreachable capability must not look like a missing one.

Twice in this session a worker was found in the tree with no route pointing at it, which
made a present capability look missing in the format matrix. These tests hold the gate
that notices: every capability worker is routed, or exempted with a reason, and an
exemption may not be stale.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MODULE = REPO / "scripts" / "check_worker_reachability.py"
RECORD = REPO / "docs/authority/taskpack-0910-r3/WORKER-REACHABILITY.json"


def _load():
    spec = importlib.util.spec_from_file_location("worker_reachability_under_test", MODULE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


checker = _load()


def _record_for(tmp_path: Path, unrouted: list[dict]) -> Path:
    original = json.loads(RECORD.read_text(encoding="utf-8"))
    original["unrouted"] = unrouted
    target = tmp_path / "record.json"
    target.write_text(json.dumps(original, ensure_ascii=False, indent=2), encoding="utf-8")
    return target


def _failures(record: Path) -> list[str]:
    failures, _ = checker.check(REPO, record)
    return failures


def test_the_committed_record_passes_against_the_real_tree():
    failures, detail = checker.check(REPO, RECORD)
    assert failures == []
    assert detail["workers"] >= 11
    assert detail["routed"] >= 9
    assert detail["exempted"] == 2


def test_the_discovery_rule_finds_the_workers_it_claims_to():
    workers = checker.capability_workers(REPO)
    # a routed capability, an exempted one, and the engines that were wired this session
    assert "services/python-workers/document/worker_text.py" in workers
    assert "services/python-workers/media/worker_video.py" in workers
    assert workers["services/python-workers/web/worker_html.py"] == "python-worker-html"
    assert workers["services/python-workers/document/worker_canvas.py"] == "python-worker-canvas"
    # a dispatcher with no engine of its own is not a capability worker
    assert "services/python-workers/worker_extract.py" not in workers


def test_every_routed_worker_is_really_named_by_a_route():
    routed = checker.routed_workers(REPO)
    assert "services/python-workers/web/worker_html.py" in routed
    assert "services/python-workers/document/worker_office.py" in routed
    assert "services/python-workers/document/worker_subtitles.py" in routed
    # the exempted two must not appear in the route table, or their exemption is stale
    assert "services/python-workers/media/worker_video.py" not in routed
    assert "services/python-workers/media/worker_transcribe.py" not in routed


def test_a_worker_with_no_route_and_no_reason_is_refused(tmp_path):
    record = _record_for(tmp_path, [])
    failures = _failures(record)
    assert any("is not named by any transport route and has no recorded reason" in line for line in failures)
    assert any("worker_video.py" in line for line in failures)


def test_an_exemption_with_no_reason_is_refused(tmp_path):
    record = _record_for(
        tmp_path,
        [
            {"worker": "services/python-workers/media/worker_video.py", "engine": "python-worker-video"},
            {
                "worker": "services/python-workers/media/worker_transcribe.py",
                "engine": "python-worker-transcribe",
                "reason": "needs a model",
            },
        ],
    )
    failures = _failures(record)
    assert any("is exempted with no reason" in line for line in failures)


def test_a_stale_exemption_for_a_routed_worker_is_refused(tmp_path):
    record = _record_for(
        tmp_path,
        [
            {
                "worker": "services/python-workers/web/worker_html.py",
                "engine": "python-worker-html",
                "reason": "this one is in fact routed now",
            },
            {
                "worker": "services/python-workers/media/worker_video.py",
                "engine": "python-worker-video",
                "reason": "needs parameters the contract cannot carry",
            },
            {
                "worker": "services/python-workers/media/worker_transcribe.py",
                "engine": "python-worker-transcribe",
                "reason": "needs a model",
            },
        ],
    )
    failures = _failures(record)
    assert any("is routed and also exempted" in line for line in failures)


def test_an_exemption_for_a_worker_that_does_not_exist_is_refused(tmp_path):
    record = _record_for(
        tmp_path,
        [
            {
                "worker": "services/python-workers/media/worker_gone.py",
                "engine": "python-worker-gone",
                "reason": "removed long ago",
            },
            {
                "worker": "services/python-workers/media/worker_video.py",
                "engine": "python-worker-video",
                "reason": "needs parameters the contract cannot carry",
            },
            {
                "worker": "services/python-workers/media/worker_transcribe.py",
                "engine": "python-worker-transcribe",
                "reason": "needs a model",
            },
        ],
    )
    failures = _failures(record)
    assert any("is exempted but does not exist" in line for line in failures)
