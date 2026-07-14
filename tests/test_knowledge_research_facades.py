from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path


def test_knowledge_research_facades_real_isolated_round_trip(tmp_path: Path):
    runtime_root = tmp_path / "runtime"
    env = os.environ.copy()
    env["COGNITIVE_DATA_DIR"] = str(runtime_root)
    env["PYTHONDONTWRITEBYTECODE"] = "1"

    code = textwrap.dedent(
        r"""
        import importlib
        import json
        import os
        import sys
        import uuid
        from pathlib import Path

        runtime_root = Path(os.environ["COGNITIVE_DATA_DIR"]).resolve()
        from shared import storage

        expected_db = runtime_root / "cognitive_os.sqlite"
        assert storage.DB_PATH.resolve() == expected_db
        assert expected_db.is_relative_to(runtime_root)

        from app.facades import ingest_candidate, query_knowledge
        from inspiration_research.api import app as canonical_app

        token = "facadefts" + uuid.uuid4().hex
        document = {
            "id": "doc_" + uuid.uuid4().hex,
            "title": "isolated facade document",
            "content": f"unique real FTS marker {token}",
            "source": "facade-test",
            "tags": ["facade-test"],
        }
        storage.insert("kb_documents", document)
        storage.fts5_sync("kb_documents", document)

        knowledge = query_knowledge(token, mode="keyword", top_k=10)
        assert knowledge.query == token
        assert knowledge.mode == "keyword"
        assert knowledge.count == len(knowledge.items)
        assert any(item.id == document["id"] for item in knowledge.items)
        raw_hit = next(
            hit
            for hit in storage.fts5_search("kb_documents", token, top_k=10)
            if hit["id"] == document["id"]
        )
        assert raw_hit["rank"] != 999

        before_path = tuple(sys.path)
        intake = ingest_candidate(
            title="isolated research candidate",
            why="verify generator and persistence",
            what_to_absorb=["real generator", "real SQLite"],
            what_not_to_absorb=["mock storage"],
            risk_level="low",
            target_repo="Knowledge-Base",
        )
        assert tuple(sys.path) == before_path
        assert intake.intake_id.startswith("intake_")
        stored = storage.select_one("ir_intake_cards", intake.intake_id)
        assert stored is not None
        assert stored["id"] == intake.intake_id
        assert stored["what_to_absorb"] == ["real generator", "real SQLite"]
        assert stored["what_not_to_absorb"] == ["mock storage"]

        legacy_app = importlib.import_module("Inspiration-Research.api").app
        assert legacy_app is canonical_app

        print(json.dumps({
            "db_path": str(storage.DB_PATH.resolve()),
            "document_id": document["id"],
            "intake_id": intake.intake_id,
        }))
        """
    )

    completed = subprocess.run(
        [sys.executable, "-c", code],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, (
        f"stdout:\n{completed.stdout}\n"
        f"stderr:\n{completed.stderr}"
    )
    evidence = json.loads(completed.stdout.strip().splitlines()[-1])
    assert Path(evidence["db_path"]).resolve().is_relative_to(runtime_root.resolve())
    assert (runtime_root / "cognitive_os.sqlite").exists()
