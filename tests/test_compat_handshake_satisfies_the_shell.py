"""The composed handshake must satisfy the rules the product shell actually applies.

The shell pins the product id and the contract, requires product name, versions, runtime mode and
workspace to be non-empty, requires the schema version to be an integer of at least one, requires
capabilities to be strings, and refuses any migration state other than ready
(frontend/src/api/client.ts). These tests restate those rules against the composer so the projection
is checked in the same terms the frontend checks it, rather than on terms of its own choosing.
"""

from __future__ import annotations

import pytest

from app.workspace.compat_handshake import (
    REQUIRED_API_CONTRACT,
    REQUIRED_PRODUCT_ID,
    HandshakeCompositionError,
    RuntimeIdentity,
    compose_handshake,
)

# The Core's real answer shape, as read from crates/archeaxis-api/src/lib.rs.
CORE_VERSION = {"runtime": "archeaxis-api", "contract": "0.1.0-outline", "schema_version": 15}


def identity(**overrides):
    base = {
        "product_name": "ArcheAxis Knowledge",
        "backend_version": "0.6.14",
        "source_commit": "0123456",
        "runtime_mode": "desktop",
        "workspace_id": "workspace-001",
        "capabilities": ("text.extract", "pdf.extract"),
    }
    base.update(overrides)
    return RuntimeIdentity(**base)


def shell_accepts(document):
    """The frontend predicate, restated field for field."""
    assert document["product_id"] == "archeaxis-workspace"
    assert isinstance(document["product_name"], str) and document["product_name"]
    assert document["api_contract"] == "1.x"
    for field in ("backend_version", "source_commit", "runtime_mode", "workspace_id"):
        assert isinstance(document[field], str) and document[field], field
    assert isinstance(document["schema_version"], int) and document["schema_version"] >= 1
    assert isinstance(document["capabilities"], list)
    assert all(isinstance(item, str) for item in document["capabilities"])
    assert document["migration_state"] == "ready"


def test_the_composed_handshake_passes_the_shell_predicate():
    document = compose_handshake(CORE_VERSION, identity())
    shell_accepts(document)


def test_the_two_pinned_values_come_from_the_shell_not_from_the_core():
    document = compose_handshake(CORE_VERSION, identity())
    assert document["product_id"] == REQUIRED_PRODUCT_ID
    assert document["api_contract"] == REQUIRED_API_CONTRACT
    # The Core never emits these names; the projection supplies them.
    assert "product_id" not in CORE_VERSION and "api_contract" not in CORE_VERSION


def test_the_cores_outline_self_description_survives_the_projection():
    document = compose_handshake(CORE_VERSION, identity())
    assert document["core_contract"] == "0.1.0-outline"
    assert document["core_runtime"] == "archeaxis-api"


@pytest.mark.parametrize("bad", [
    {"schema_version": 0},
    {"schema_version": None},
    {"schema_version": "15"},
    {"runtime": ""},
])


def test_an_unusable_core_answer_fails_closed(bad):
    version = dict(CORE_VERSION)
    version.update(bad)
    with pytest.raises(HandshakeCompositionError):
        compose_handshake(version, identity())


def test_a_non_object_core_answer_fails_closed():
    with pytest.raises(HandshakeCompositionError):
        compose_handshake(["not", "an", "object"], identity())


@pytest.mark.parametrize("field", ["product_name", "backend_version", "source_commit",
                                   "runtime_mode", "workspace_id"])


def test_a_missing_identity_fact_fails_closed(field):
    with pytest.raises(HandshakeCompositionError):
        compose_handshake(CORE_VERSION, identity(**{field: "   "}))


def test_a_migration_state_other_than_ready_is_refused():
    with pytest.raises(HandshakeCompositionError):
        compose_handshake(CORE_VERSION, identity(migration_state="migrating"))


def test_capabilities_must_be_strings():
    with pytest.raises(HandshakeCompositionError):
        compose_handshake(CORE_VERSION, identity(capabilities=("text.extract", "  ")))


@pytest.mark.parametrize("field", ["schema_version", "runtime"])
def test_a_field_missing_from_the_core_answer_fails_closed(field):
    version = dict(CORE_VERSION)
    version.pop(field)
    with pytest.raises(HandshakeCompositionError):
        compose_handshake(version, identity())
