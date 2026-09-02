"""Regression coverage for the source-only G0 first-wave consumer audit."""

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ci" / "audit_first_wave_consumers.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("first_wave_consumer_audit", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_audit_excludes_definitions_and_test_paths_but_keeps_consumers(tmp_path: Path) -> None:
    (tmp_path / "app" / "evidence").mkdir(parents=True)
    (tmp_path / "app" / "learning").mkdir(parents=True)
    (tmp_path / "app" / "integrations").mkdir(parents=True)
    (tmp_path / "app" / "tests").mkdir(parents=True)
    (tmp_path / "app" / "evidence" / "source_store_v2.py").write_text(
        "class SourceStoreV2: pass\n", encoding="utf-8"
    )
    (tmp_path / "app" / "learning" / "event_store.py").write_text(
        "def append_event(): pass\ndef record_machine_receipt(): pass\n", encoding="utf-8"
    )
    (tmp_path / "app" / "integrations" / "bridge.py").write_text(
        "SourceStoreV2()\nappend_event()\nrecord_machine_receipt()\n",
        encoding="utf-8",
    )
    (tmp_path / "app" / "tests" / "test_bridge.py").write_text(
        "SourceStoreV2()\nappend_event()\n", encoding="utf-8"
    )

    module = _load_module()

    assert module.audit_first_wave_consumers(tmp_path) == {
        "evidence_bundle_review": [],
        "evidence_bundle_store": [],
        "human_learning_event": ["app/integrations/bridge.py"],
        "machine_competence_receipt": ["app/integrations/bridge.py"],
        "source_anchor_provenance_v2": ["app/integrations/bridge.py"],
    }


def test_current_consumer_map_matches_the_documented_first_wave_baseline() -> None:
    module = _load_module()

    assert module.audit_first_wave_consumers(ROOT) == {
        "evidence_bundle_review": [],
        "evidence_bundle_store": [],
        "human_learning_event": ["app/integrations/deeptutor_bridge.py"],
        "machine_competence_receipt": [],
        "source_anchor_provenance_v2": [],
    }
