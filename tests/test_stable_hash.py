from __future__ import annotations

from app.memory.vector_db import SimpleTextEmbedder
from shared.stable_hash import (
    STABLE_HASH_ALGORITHM,
    stable_hash_bytes,
    stable_hash_text,
)


def test_stable_hash_contract_is_versioned_and_deterministic():
    assert STABLE_HASH_ALGORITHM == "sha256-v1"
    assert stable_hash_text("same") == stable_hash_text("same")
    assert stable_hash_text("same") != stable_hash_text("different")
    assert stable_hash_bytes(b"same") == stable_hash_text("same")


def test_stable_hash_supports_explicit_namespace():
    assert stable_hash_text("id", namespace="vector-rowid") != stable_hash_text(
        "id", namespace="embedding-ngram"
    )


def test_stable_hash_rejects_invalid_inputs():
    try:
        stable_hash_text("ok", namespace="")
    except ValueError:
        pass
    else:
        raise AssertionError("empty namespace must fail closed")


def test_text_embedder_is_process_stable():
    first = SimpleTextEmbedder(dim=32).embed("stable embedding")
    second = SimpleTextEmbedder(dim=32).embed("stable embedding")
    assert first.tobytes() == second.tobytes()
