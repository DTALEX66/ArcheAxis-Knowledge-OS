from __future__ import annotations

import base64
import hashlib
import hmac
import importlib
import json

import pytest
from fastapi.testclient import TestClient

import shared.config as config_module
from app.main import _http_route_counts, app
from knowledge_base.api import app as standalone_kb_app
from shared import auth
from shared.bulk_ops import export_kb
from shared.collection_views import render_view
from shared.config import Config, config, resolve_runtime_path, validate_runtime_config
from shared.dataview import query
from shared.storage import _resolve_database_path, select_all


def test_storage_rejects_dynamic_sql_identifiers():
    with pytest.raises(ValueError, match="invalid SQL identifier"):
        select_all("kb_documents); DROP TABLE kb_documents; --")
    with pytest.raises(ValueError, match="invalid SQL order"):
        select_all("kb_documents", order="created_at DESC; DROP TABLE kb_documents")


def test_export_uses_explicit_table_allowlist():
    with pytest.raises(ValueError, match="unsupported export table"):
        export_kb(tables=["sqlite_master"])


def test_user_facing_query_planes_reject_internal_tables():
    result = query("FROM episodic_memory LIMIT 1")
    assert "not available to public query APIs" in result["error"]
    with pytest.raises(ValueError, match="not available to public query APIs"):
        render_view("episodic_memory")

    client = TestClient(app)
    response = client.post(
        "/kb/dataview/query",
        params={"query_str": "FROM episodic_memory LIMIT 1"},
    )
    assert response.status_code == 400
    assert client.get("/kb/views/episodic_memory").status_code == 400


def test_static_routes_are_not_shadowed_by_dynamic_parameters():
    client = TestClient(app)
    block = client.get("/kb/blocks/resolve")
    assert block.status_code == 200
    assert block.json() == {"error": "block not found", "ref": ""}

    radar = client.get("/kb/diversity/radar")
    assert radar.status_code == 200
    assert "items" in radar.json()


def test_database_path_configuration_is_used(monkeypatch, tmp_path):
    configured = tmp_path / "isolated.sqlite"
    monkeypatch.setitem(config._data["database"], "path", str(configured))
    assert _resolve_database_path() == configured


def test_installed_runtime_paths_use_configured_writable_root(monkeypatch, tmp_path):
    installed_root = tmp_path / "site-packages"
    runtime_root = tmp_path / "runtime"
    installed_root.mkdir()
    monkeypatch.setattr(config_module, "_PROJECT_ROOT", installed_root)
    monkeypatch.setenv("COGNITIVE_DATA_DIR", str(runtime_root))

    assert resolve_runtime_path("data/cognitive.sqlite") == runtime_root / "cognitive.sqlite"
    assert resolve_runtime_path("config/api_keys.json") == runtime_root / "api_keys.json"


def test_source_checkout_honours_explicit_runtime_root(monkeypatch, tmp_path):
    source_root = tmp_path / "source"
    runtime_root = tmp_path / "runtime"
    source_root.mkdir()
    (source_root / "pyproject.toml").write_text("[project]\nname = 'fixture'\n")
    monkeypatch.setattr(config_module, "_PROJECT_ROOT", source_root)
    monkeypatch.setenv("COGNITIVE_DATA_DIR", str(runtime_root))

    assert resolve_runtime_path("data/cognitive.sqlite") == runtime_root / "cognitive.sqlite"
    assert resolve_runtime_path("config/api_keys.json") == runtime_root / "api_keys.json"


def test_installed_runtime_fails_closed_without_explicit_runtime_root(monkeypatch, tmp_path):
    installed_root = tmp_path / "site-packages"
    installed_root.mkdir()
    monkeypatch.setattr(config_module, "_PROJECT_ROOT", installed_root)
    monkeypatch.delenv("COGNITIVE_DATA_DIR", raising=False)

    with pytest.raises(RuntimeError, match="COGNITIVE_DATA_DIR"):
        resolve_runtime_path("data/cognitive.sqlite")


def test_generated_jwt_secret_uses_runtime_data_root(monkeypatch, tmp_path):
    installed_root = tmp_path / "site-packages"
    runtime_root = tmp_path / "runtime"
    installed_root.mkdir()
    monkeypatch.setattr(config_module, "_PROJECT_ROOT", installed_root)
    monkeypatch.setenv("COGNITIVE_DATA_DIR", str(runtime_root))
    monkeypatch.delenv("COGNITIVE_JWT_SECRET", raising=False)

    secret = auth._get_secret()
    assert secret
    assert (runtime_root / ".jwt_secret").read_text() == secret


def test_auth_enabled_configuration_is_honoured(monkeypatch):
    monkeypatch.setitem(config._data["auth"], "enabled", False)
    assert auth.requires_auth("/tools") is False

    monkeypatch.setitem(config._data["auth"], "enabled", True)
    assert auth.requires_auth("/tools") is True
    assert auth.requires_auth("/health") is False


@pytest.mark.parametrize("environment", ["development", "dev", "local", "test", "production"])
def test_absent_configuration_never_loads_an_administrator_key(monkeypatch, tmp_path, environment):
    monkeypatch.setitem(config._data["app"], "environment", environment)
    monkeypatch.setitem(config._data["auth"], "api_key_file", str(tmp_path / "missing.json"))
    monkeypatch.delenv("COGNITIVE_API_KEY", raising=False)
    assert auth._load_api_keys() == {}
    assert auth.validate_api_key("dev-key-change-me") is None


def test_development_administrator_key_requires_explicit_strong_provisioning(
    monkeypatch, admin_api_key
):
    monkeypatch.setitem(config._data["app"], "environment", "development")
    assert auth.validate_api_key(admin_api_key) == {
        "role": "admin",
        "name": "env-admin",
    }


@pytest.mark.parametrize("api_key", ["short", "change-me", "dev-key-change-me"])
def test_development_rejects_weak_or_default_administrator_keys(monkeypatch, tmp_path, api_key):
    monkeypatch.setitem(config._data["app"], "environment", "development")
    monkeypatch.setitem(config._data["auth"], "api_key_file", str(tmp_path / "missing.json"))
    monkeypatch.setenv("COGNITIVE_API_KEY", api_key)
    assert auth._load_api_keys() == {}
    assert auth.validate_api_key(api_key) is None


def test_production_profile_fails_fast_on_development_defaults(monkeypatch):
    monkeypatch.setenv("COGNITIVE_ENV", "production")
    production = Config()
    with pytest.raises(RuntimeError, match="auth.enabled"):
        validate_runtime_config(production)

    production._data["auth"]["enabled"] = True
    with pytest.raises(RuntimeError, match="CORS"):
        validate_runtime_config(production)


def test_production_profile_can_be_configured_entirely_by_environment(monkeypatch):
    monkeypatch.setenv("COGNITIVE_ENV", "production")
    monkeypatch.setenv("COGNITIVE_AUTH_ENABLED", "true")
    monkeypatch.setenv("COGNITIVE_API_KEY", "test-api-key-0123456789abcdef-ABCDEFGH")
    monkeypatch.setenv("COGNITIVE_JWT_SECRET", "test-jwt-secret-fedcba9876543210-HGFEDCBA")
    monkeypatch.setenv("COGNITIVE_CORS_ORIGINS", "https://ui.example, https://admin.example")
    current = Config()
    validate_runtime_config(current)
    assert current.get("cors.allow_origins") == [
        "https://ui.example",
        "https://admin.example",
    ]


def test_production_rejects_empty_api_key_file(monkeypatch, tmp_path):
    monkeypatch.setenv("COGNITIVE_ENV", "production")
    monkeypatch.setenv("COGNITIVE_AUTH_ENABLED", "true")
    monkeypatch.setenv("COGNITIVE_CORS_ORIGINS", "https://ui.example")
    monkeypatch.setenv("COGNITIVE_JWT_SECRET", "test-jwt-secret-fedcba9876543210-HGFEDCBA")
    monkeypatch.delenv("COGNITIVE_API_KEY", raising=False)
    key_file = tmp_path / "api_keys.json"
    key_file.write_text("{}", encoding="utf-8")
    current = Config()
    current._data["auth"]["api_key_file"] = str(key_file)

    with pytest.raises(RuntimeError, match="invalid or weak"):
        validate_runtime_config(current)


def test_standalone_kb_enforces_shared_auth(monkeypatch, admin_api_key):
    monkeypatch.setitem(config._data["auth"], "enabled", True)
    client = TestClient(standalone_kb_app)
    assert client.get("/documents").status_code == 401
    assert client.get("/documents", headers={"X-API-Key": admin_api_key}).status_code == 200


def test_non_admin_requester_cannot_select_admin_role(monkeypatch):
    monkeypatch.setitem(config._data["auth"], "enabled", True)
    monkeypatch.setenv("COGNITIVE_JWT_SECRET", "test-jwt-secret-value")
    client = TestClient(app)
    user_token = auth.create_token("ordinary-user", role="user")
    denied = client.post(
        "/auth/token?user_id=admin&role=admin",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert denied.status_code == 403


def test_explicitly_provisioned_admin_can_issue_bounded_tokens(monkeypatch, admin_api_key):
    monkeypatch.setitem(config._data["auth"], "enabled", True)
    monkeypatch.setenv("COGNITIVE_JWT_SECRET", "test-jwt-secret-value")
    client = TestClient(app)
    issued = client.post(
        "/auth/token?user_id=operator&role=readonly&expires_hours=2",
        headers={"X-API-Key": admin_api_key},
    )
    assert issued.status_code == 200


def test_gateway_enforces_role_matrix(monkeypatch):
    monkeypatch.setitem(config._data["auth"], "enabled", True)
    monkeypatch.setitem(config._data["rate_limit"], "enabled", False)
    monkeypatch.setenv(
        "COGNITIVE_JWT_SECRET", "role-matrix-test-secret-0123456789-ABCDEF"
    )
    client = TestClient(app)
    readonly = auth.create_token("reader", role="readonly")
    user = auth.create_token("writer", role="user")

    assert client.get(
        "/tools", headers={"Authorization": f"Bearer {readonly}"}
    ).status_code == 200
    assert client.post(
        "/ingest",
        json={"content": "readonly must not write", "source": "test"},
        headers={"Authorization": f"Bearer {readonly}"},
    ).status_code == 403
    for path in ("/backup", "/run", "/internal/research/intake-card"):
        response = client.post(
            path,
            json={"content": "forbidden"},
            headers={"Authorization": f"Bearer {user}"},
        )
        assert response.status_code == 403, path
    for path in (
        "/kb/obsidian/import/apply",
        "/kb/search/rebuild",
        "/kb/bulk/import",
        "/kb/cron/discover",
        "/kb/sources",
        "/kb/pipeline",
        "/kb/project/taskpack/task-1",
        "/kb/projects/generate",
        "/projects/generate",
    ):
        assert not auth.authorize_request(
            {"role": "user", "auth_method": "jwt"}, "POST", path
        ), path
    assert TestClient(standalone_kb_app).post(
        "/search/rebuild", headers={"Authorization": f"Bearer {user}"}
    ).status_code == 403
    allowed = client.post(
        "/ingest",
        json={"content": "ordinary user content", "source": "test"},
        headers={"Authorization": f"Bearer {user}"},
    )
    assert allowed.status_code == 200
    assert auth.authorize_request(
        {"role": "admin", "auth_method": "jwt"}, "POST", "/backup"
    )


def test_readonly_daily_get_has_no_storage_side_effect(monkeypatch):
    from shared.storage import count

    monkeypatch.setitem(config._data["auth"], "enabled", True)
    monkeypatch.setitem(config._data["rate_limit"], "enabled", False)
    monkeypatch.setenv(
        "COGNITIVE_JWT_SECRET", "readonly-daily-secret-0123456789-ABCDEF"
    )
    client = TestClient(app)
    readonly = auth.create_token("reader", role="readonly")
    headers = {"Authorization": f"Bearer {readonly}"}
    before = count("daily_notes")

    response = client.get("/kb/daily?day=2099-12-31", headers=headers)

    assert response.status_code == 404
    assert count("daily_notes") == before
    assert client.post("/kb/daily?day=2099-12-31", headers=headers).status_code == 403
    standalone = TestClient(standalone_kb_app)
    assert standalone.post("/daily?day=2099-12-31", headers=headers).status_code == 403


def test_project_generation_is_not_reachable_through_get_and_is_admin_only(
    monkeypatch, admin_api_key
):
    from shared.storage import count

    monkeypatch.setitem(config._data["auth"], "enabled", True)
    monkeypatch.setitem(config._data["rate_limit"], "enabled", False)
    monkeypatch.setenv(
        "COGNITIVE_JWT_SECRET", "project-route-role-matrix-secret-123456789"
    )
    client = TestClient(app)
    readonly = auth.create_token("reader", role="readonly")
    user = auth.create_token("writer", role="user")
    before = count("kb_taskpacks")

    response = client.get(
        "/kb/projects?action=generate&topic=test",
        headers={"Authorization": f"Bearer {readonly}"},
    )
    assert response.status_code == 200
    assert count("kb_taskpacks") == before
    for token in (readonly, user):
        for route in ("/kb/project/generate", "/kb/projects/generate"):
            denied = client.post(
                f"{route}?topic=test",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert denied.status_code == 403
    assert client.post(
        "/kb/projects/generate?topic=test",
        headers={"X-API-Key": admin_api_key},
    ).status_code == 200
    standalone = TestClient(standalone_kb_app)
    for route in ("/project/generate", "/projects/generate"):
        assert standalone.post(
            f"{route}?topic=test",
            headers={"Authorization": f"Bearer {user}"},
        ).status_code == 403


def test_dashboards_are_not_public_when_auth_is_enabled(monkeypatch, admin_api_key):
    monkeypatch.setitem(config._data["auth"], "enabled", True)
    core = TestClient(app)
    kb = TestClient(standalone_kb_app)
    assert core.get("/kb/").status_code == 401
    assert kb.get("/").status_code == 401
    headers = {"X-API-Key": admin_api_key}
    assert core.get("/kb/", headers=headers).status_code == 200
    assert kb.get("/", headers=headers).status_code == 200


def test_inspiration_research_uses_shared_auth(monkeypatch):
    monkeypatch.setitem(config._data["auth"], "enabled", True)
    monkeypatch.setenv(
        "COGNITIVE_JWT_SECRET", "research-standalone-secret-0123456789-ABCDEF"
    )
    ir_app = importlib.import_module("inspiration_research.api").app
    client = TestClient(ir_app)
    assert client.post("/research-note", json={"title": "x", "content": "y"}).status_code == 401
    user = auth.create_token("writer", role="user")
    assert client.post(
        "/research-note",
        json={"title": "x", "content": "y"},
        headers={"Authorization": f"Bearer {user}"},
    ).status_code == 403


def test_production_rejects_weak_secrets(monkeypatch):
    monkeypatch.setenv("COGNITIVE_ENV", "production")
    monkeypatch.setenv("COGNITIVE_AUTH_ENABLED", "true")
    monkeypatch.setenv("COGNITIVE_CORS_ORIGINS", "https://ui.example")
    monkeypatch.setenv("COGNITIVE_API_KEY", "short")
    monkeypatch.setenv("COGNITIVE_JWT_SECRET", "also-short")
    with pytest.raises(RuntimeError, match="strong COGNITIVE_API_KEY"):
        validate_runtime_config(Config())


@pytest.mark.parametrize(
    ("api_key", "jwt_secret"),
    [
        (
            "replace-with-strong-random-api-key-000000",
            "test-jwt-secret-fedcba9876543210-HGFEDCBA",
        ),
        (
            "test-api-key-0123456789abcdef-ABCDEFGH",
            "replace-with-different-strong-random-jwt-secret-000000",
        ),
        (
            "placeholder-api-key-0123456789abcdef",
            "placeholder-jwt-secret-fedcba9876543210",
        ),
    ],
)
def test_production_rejects_documented_placeholder_secret_patterns(
    monkeypatch, api_key, jwt_secret
):
    monkeypatch.setenv("COGNITIVE_ENV", "production")
    monkeypatch.setenv("COGNITIVE_AUTH_ENABLED", "true")
    monkeypatch.setenv("COGNITIVE_CORS_ORIGINS", "https://ui.example")
    monkeypatch.setenv("COGNITIVE_API_KEY", api_key)
    monkeypatch.setenv("COGNITIVE_JWT_SECRET", jwt_secret)

    with pytest.raises(RuntimeError, match="strong"):
        validate_runtime_config(Config())


def test_production_rejects_weak_key_file_even_with_strong_environment_key(monkeypatch, tmp_path):
    monkeypatch.setenv("COGNITIVE_ENV", "production")
    monkeypatch.setenv("COGNITIVE_AUTH_ENABLED", "true")
    monkeypatch.setenv("COGNITIVE_CORS_ORIGINS", "https://ui.example")
    monkeypatch.setenv("COGNITIVE_API_KEY", "test-api-key-0123456789abcdef-ABCDEFGH")
    monkeypatch.setenv("COGNITIVE_JWT_SECRET", "test-jwt-secret-fedcba9876543210-HGFEDCBA")
    key_file = tmp_path / "api_keys.json"
    key_file.write_text('{"weak": {"role": "admin", "name": "legacy"}}', encoding="utf-8")
    current = Config()
    current._data["auth"]["api_key_file"] = str(key_file)
    with pytest.raises(RuntimeError, match="invalid or weak"):
        validate_runtime_config(current)


def test_production_rejects_key_file_equal_to_jwt_secret(monkeypatch, tmp_path):
    shared_secret = "test-shared-secret-0123456789abcdef-ABCDEFGH"
    monkeypatch.setenv("COGNITIVE_ENV", "production")
    monkeypatch.setenv("COGNITIVE_AUTH_ENABLED", "true")
    monkeypatch.setenv("COGNITIVE_CORS_ORIGINS", "https://ui.example")
    monkeypatch.delenv("COGNITIVE_API_KEY", raising=False)
    monkeypatch.setenv("COGNITIVE_JWT_SECRET", shared_secret)
    key_file = tmp_path / "api_keys.json"
    key_file.write_text(
        json.dumps({shared_secret: {"role": "admin", "name": "admin"}}),
        encoding="utf-8",
    )
    current = Config()
    current._data["auth"]["api_key_file"] = str(key_file)
    with pytest.raises(RuntimeError, match="must be different"):
        validate_runtime_config(current)


def test_production_rejects_string_cors_allowlist(monkeypatch):
    monkeypatch.setenv("COGNITIVE_ENV", "production")
    monkeypatch.setenv("COGNITIVE_AUTH_ENABLED", "true")
    monkeypatch.setenv("COGNITIVE_API_KEY", "test-api-key-0123456789abcdef-ABCDEFGH")
    monkeypatch.setenv("COGNITIVE_JWT_SECRET", "test-jwt-secret-fedcba9876543210-HGFEDCBA")
    current = Config()
    current._data["cors"]["allow_origins"] = "https://ui.example"
    with pytest.raises(RuntimeError, match="list of strings"):
        validate_runtime_config(current)


@pytest.mark.parametrize(
    ("field", "value", "error"),
    [
        ("allow_origins", [" "], "origins"),
        ("allow_headers", [" "], "headers"),
        ("allow_headers", ["Authorization", "*"], "headers"),
    ],
)
def test_production_rejects_blank_or_wildcard_cors_entries(monkeypatch, field, value, error):
    monkeypatch.setenv("COGNITIVE_ENV", "production")
    monkeypatch.setenv("COGNITIVE_AUTH_ENABLED", "true")
    monkeypatch.setenv("COGNITIVE_CORS_ORIGINS", "https://ui.example")
    monkeypatch.setenv("COGNITIVE_API_KEY", "test-api-key-0123456789abcdef-ABCDEFGH")
    monkeypatch.setenv("COGNITIVE_JWT_SECRET", "test-jwt-secret-fedcba9876543210-HGFEDCBA")
    current = Config()
    current._data["cors"][field] = value
    with pytest.raises(RuntimeError, match=error):
        validate_runtime_config(current)


def test_invalid_yaml_fails_closed(monkeypatch, tmp_path):
    root = tmp_path / "installed"
    (root / "config").mkdir(parents=True)
    (root / "config" / "settings.yaml").write_text("app: [broken", encoding="utf-8")
    monkeypatch.setattr(config_module, "_PROJECT_ROOT", root)
    with pytest.raises(RuntimeError, match="unable to load runtime configuration"):
        Config()


def test_verify_token_rejects_invalid_claims(monkeypatch):
    secret = "test-jwt-secret-fedcba9876543210-HGFEDCBA"
    monkeypatch.setenv("COGNITIVE_JWT_SECRET", secret)
    token = auth.create_token("user-1", role="user")
    encoded, _ = token.split(".")
    payload = json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)))
    payload["role"] = "owner"
    forged_payload = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    signature = hmac.new(secret.encode(), forged_payload.encode(), hashlib.sha256).hexdigest()
    assert auth.verify_token(f"{forged_payload}.{signature}") is None


def test_route_counts_come_from_openapi_schemas():
    methods = {"get", "put", "post", "delete", "options", "head", "patch", "trace"}

    def count_operations(schema):
        return sum(1 for item in schema["paths"].values() for method in item if method in methods)

    counts = _http_route_counts()
    assert counts["core"] == count_operations(app.openapi())
    assert counts["kb"] == count_operations(standalone_kb_app.openapi())
    assert counts["total"] == counts["core"] + counts["kb"]


def test_knowledge_base_modules_import_without_top_level_aliases():
    import knowledge_base.cards.generator  # noqa: F401
    import knowledge_base.machine_knowledge.a_to_b  # noqa: F401
    import knowledge_base.search  # noqa: F401


def test_standalone_kb_lazy_routes_use_packaged_modules():
    client = TestClient(standalone_kb_app)
    assert client.get("/reviews/due").status_code == 200
    assert client.get("/a-to-b/candidates").status_code == 200
    assert client.get("/machine-knowledge").status_code == 200
