from __future__ import annotations

import fnmatch
import json
import os
import re
import sqlite3
from argparse import Namespace
from contextlib import contextmanager
from pathlib import Path

import pytest
import yaml

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 compatibility
    import tomli as tomllib

ROOT = Path(__file__).resolve().parents[1]


def _dockerignore_patterns() -> list[tuple[bool, str]]:
    lines = []
    for raw_line in (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        negated = line.startswith("!")
        lines.append((negated, line[1:] if negated else line))
    return lines


def _pattern_matches(pattern: str, path: str) -> bool:
    normalized = path.strip("/")
    pattern = pattern.strip("/")
    if not pattern:
        return False
    if pattern.endswith("/"):
        pattern = pattern[:-1]
    if "/" not in pattern and (
        any(part == pattern for part in normalized.split("/"))
        or fnmatch.fnmatch(normalized, pattern)
        or fnmatch.fnmatch(Path(normalized).name, pattern)
    ):
        return True
    return (
        fnmatch.fnmatch(normalized, pattern)
        or fnmatch.fnmatch(normalized, f"{pattern}/*")
        or fnmatch.fnmatch(normalized, f"**/{pattern}")
        or fnmatch.fnmatch(normalized, f"**/{pattern}/*")
    )


def _dockerignore_excludes(path: str) -> bool:
    excluded = False
    for negated, pattern in _dockerignore_patterns():
        if _pattern_matches(pattern, path):
            excluded = not negated
    return excluded


def test_dockerignore_excludes_sensitive_runtime_and_generated_context():
    dockerignore = ROOT / ".dockerignore"
    assert dockerignore.is_file()
    assert dockerignore.read_text(encoding="utf-8").strip()

    excluded = [
        ".git/config",
        ".hermes/session.json",
        ".codex/session.json",
        ".venv/pyvenv.cfg",
        "data/cognitive_os.sqlite",
        "data/cognitive_os.sqlite-wal",
        "data/cognitive_os.sqlite-shm",
        "data/backups/cognitive_os_20260716.sqlite",
        "logs/app.log",
        "__pycache__/module.pyc",
        ".pytest_cache/v/cache/nodeids",
        ".env",
        ".env.container",
        ".ssh/id_rsa",
        ".aws/credentials",
        ".azure/config",
        ".kube/config",
        ".npmrc",
        ".pypirc",
        "auth.json",
        "service.credentials.json",
        "config/api_keys.json",
        "secrets/caddy.key",
        "dist/cognitive_loop_os-0.4.0-py3-none-any.whl",
        "build/lib/app/main.py",
        "app.egg-info/PKG-INFO",
    ]
    retained = [
        ".env.container.example",
        "Dockerfile",
        "pyproject.toml",
        "requirements.txt",
        "app/main.py",
        "shared/migration.py",
        "config/settings.yaml",
        "knowledge_base/api.py",
        "inspiration_research/api.py",
    ]

    assert {path for path in excluded if not _dockerignore_excludes(path)} == set()
    assert {path for path in retained if _dockerignore_excludes(path)} == set()


def test_dockerfile_builds_installed_wheel_and_runs_single_non_root_worker():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "# syntax=" not in dockerfile
    assert "RUN --mount=" not in dockerfile
    assert (ROOT / "uv.lock").is_file()
    assert "ARG PYTHON_IMAGE=python:3.11.15-slim-bookworm@sha256:" in dockerfile
    assert "COPY pyproject.toml uv.lock README.md ./" in dockerfile
    assert "uv export --frozen --no-dev --no-emit-project" in dockerfile
    assert "locked-build-requirements.txt" in dockerfile
    assert "pip install --no-cache-dir --require-hashes" in dockerfile
    assert "pip install --no-cache-dir --requirement /tmp/requirements.txt" not in dockerfile
    assert len(re.findall(r"^FROM\s+", dockerfile, flags=re.MULTILINE)) >= 2
    assert " AS wheel-builder" in dockerfile
    assert " AS runtime" in dockerfile
    assert "uv build --python /usr/local/bin/python --wheel --no-build-isolation" in dockerfile
    assert "apt-get" not in dockerfile
    assert "pip install --no-cache-dir --no-deps /wheels/" in dockerfile
    assert "pip uninstall --yes setuptools wheel jaraco.context" in dockerfile
    assert "pip uninstall --yes pip" in dockerfile
    assert "('pip', 'setuptools', 'wheel', 'jaraco')" in dockerfile
    assert "python -m pip check" in dockerfile
    assert "sha256:" in dockerfile
    assert "COPY --from=wheel-builder /wheels/" in dockerfile
    assert "USER cognitive" in dockerfile
    assert "ENTRYPOINT [\"python\", \"-m\", \"app.container_entrypoint\"]" in dockerfile
    assert "--reload" not in dockerfile
    assert "COPY . ." not in dockerfile
    assert not (ROOT / "docker" / "Dockerfile").exists()

    entrypoint = (ROOT / "app" / "container_entrypoint.py").read_text(encoding="utf-8")
    assert '"--workers", "1"' in entrypoint
    assert "--reload" not in entrypoint
    assert '"--no-proxy-headers"' in entrypoint
    for command in ("core", "migrate", "backup", "restore-activate"):
        assert f'"{command}"' in entrypoint
    assert 'add_parser("research"' not in entrypoint


def test_build_backend_and_registry_data_are_frozen_package_inputs():
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    lock = (ROOT / "uv.lock").read_text(encoding="utf-8")
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert pyproject["build-system"]["requires"] == ["setuptools==83.0.0"]
    assert pyproject["dependency-groups"]["build"] == ["setuptools==83.0.0"]
    assert all(
        not dependency.startswith("setuptools")
        for dependency in pyproject["project"]["dependencies"]
    )
    assert "--only-group build" in dockerfile
    assert 'name = "setuptools"' in lock
    assert 'version = "83.0.0"' in lock
    assert "sha256:29b23c360f22f414dc7336bb39178cc7bcbf6021ed2733cde173f09dba19abb3" in lock
    assert "sha256:025bccbbf0fa05b6192bc64ae1e7b16e001fd6d6d4d5de03c97b1c1ade523bef" in lock
    assert "COPY shared-contracts/" not in dockerfile
    ci_workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert '"shared/core_schema.py"' in ci_workflow
    assert (ROOT / "inspiration_research" / "resources" / "open_source_project_registry.json").is_file()
    assert not (ROOT / "shared-contracts" / "registries" / "open_source_project_registry.json").exists()
    assert not (ROOT / "shared-contracts" / "registries" / "open_source_project_registry.csv").exists()


def test_packaged_research_registry_is_valid_and_non_empty():
    from scripts.batch_score_registry import ABSORPTION_BONUS

    registry_path = ROOT / "inspiration_research" / "resources" / "open_source_project_registry.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    repos = {project["name"] for project in registry["projects"]}
    modes = {project["absorption_mode"] for project in registry["projects"]}

    assert len(registry["projects"]) == 101
    assert "sst/opencode" in repos
    assert modes <= set(ABSORPTION_BONUS)
    assert registry["projects"][0]["absorption_mode"] == "参考/候选Adapter"
    assert registry["projects"][0]["note"]


def test_container_entrypoint_delegates_to_existing_migration_and_backup_apis():
    entrypoint = (ROOT / "app" / "container_entrypoint.py").read_text(encoding="utf-8")
    assert "MigrationOperator" in entrypoint
    assert "for owner in operator.registry.owners" in entrypoint
    assert 'if owner.kind.startswith("sqlite")' in entrypoint
    assert "operator.apply(owner.owner)" in entrypoint
    assert 'operator.apply("taskpack.sqlite")' not in entrypoint
    assert "migration.migrate" not in entrypoint
    assert "from shared import backup" in entrypoint
    assert "backup.backup" in entrypoint
    assert "backup.restore" in entrypoint
    assert "backup.activate_restore" in entrypoint
    assert "backup.acquire_runtime_lock" in entrypoint
    assert "with backup.runtime_lease()" in entrypoint
    assert "storage.init()" not in entrypoint
    assert "memory_database.init_db()" not in entrypoint
    assert "CREATE TABLE schema_migrations" not in entrypoint
    assert "INSERT INTO schema_migrations" not in entrypoint


def test_core_restart_checkpoints_residual_sidecars_after_acquiring_runtime_lock(monkeypatch):
    from app import container_entrypoint
    from shared import backup

    events: list[str] = []

    class ExecReachedError(RuntimeError):
        pass

    monkeypatch.setattr(backup, "acquire_runtime_lock", lambda: events.append("lock"))
    monkeypatch.setattr(
        backup,
        "prepare_runtime_database",
        lambda: events.append("checkpoint"),
        raising=False,
    )
    monkeypatch.setattr(
        container_entrypoint,
        "_validate_storage_schema",
        lambda: events.append("validate"),
    )

    def stop_at_exec(_command):
        events.append("exec")
        raise ExecReachedError

    monkeypatch.setattr(container_entrypoint, "_exec_process", stop_at_exec)

    with pytest.raises(ExecReachedError):
        container_entrypoint.run_core(Namespace())
    assert events == ["lock", "checkpoint", "validate", "exec"]


def test_migration_checkpoints_wal_before_constructing_operator(monkeypatch, tmp_path):
    from types import SimpleNamespace

    from app import container_entrypoint
    from shared import backup, migration, migration_runner

    database = tmp_path / "runtime.sqlite"
    backup_dir = tmp_path / "backups"
    database.touch()
    events: list[str] = []

    @contextmanager
    def recording_lease():
        events.append("lease-enter")
        try:
            yield
        finally:
            events.append("lease-exit")

    def prepare_file():
        events.append("prepare-file")
        return database

    def checkpoint():
        events.append("checkpoint")

    class RecordingOperator:
        def __init__(self, *, db_path, backup_dir):
            assert Path(db_path) == database
            assert Path(backup_dir) == backup_dir_path
            assert events == ["lease-enter", "prepare-file", "checkpoint"]
            events.append("operator-init")
            self.registry = SimpleNamespace(
                owners=(SimpleNamespace(owner="core.sqlite", kind="sqlite_core"),)
            )

        def apply(self, owner):
            assert owner == "core.sqlite"
            assert events == [
                "lease-enter",
                "prepare-file",
                "checkpoint",
                "operator-init",
            ]
            events.append("apply")
            return {"owner": owner, "state": "applied"}

        def status(self):
            return []

    backup_dir_path = backup_dir
    monkeypatch.setattr(backup, "runtime_lease", recording_lease)
    monkeypatch.setattr(backup, "prepare_runtime_database", checkpoint)
    monkeypatch.setattr(migration, "BACKUP_DIR", backup_dir)
    monkeypatch.setattr(container_entrypoint, "_prepare_database_file", prepare_file)
    monkeypatch.setattr(migration_runner, "MigrationOperator", RecordingOperator)
    monkeypatch.setattr(backup, "ensure_volume_identity", lambda _database: None)

    assert container_entrypoint.run_migration(Namespace()) == 0
    assert events == [
        "lease-enter",
        "prepare-file",
        "checkpoint",
        "operator-init",
        "apply",
        "lease-exit",
    ]


def test_container_migration_records_operator_provenance_and_backup(
    monkeypatch, tmp_path, capsys
):
    from app import container_entrypoint
    from app.memory import database as memory_database
    from shared import backup, migration, storage

    database = tmp_path / "runtime" / "cognitive.sqlite"
    backup_dir = tmp_path / "backups"
    for module in (storage, memory_database, backup, migration):
        monkeypatch.setattr(module, "DB_PATH", database)
    monkeypatch.setattr(backup, "BACKUP_DIR", backup_dir)
    monkeypatch.setattr(migration, "BACKUP_DIR", backup_dir)

    assert container_entrypoint.run_migration(Namespace()) == 0
    payload = json.loads(capsys.readouterr().out)
    owners = {result["owner"] for result in payload["operator_results"]}
    assert owners == {"core.sqlite", "research.sqlite", "taskpack.sqlite"}
    assert all(result["state"] == "applied" for result in payload["operator_results"])
    with sqlite3.connect(database) as connection:
        rows = set(
            connection.execute(
                "SELECT owner, state, operation FROM migration_operator_runs "
                "WHERE operation='apply'"
            ).fetchall()
        )
        research_table = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='research_packages_v1'"
        ).fetchone()
    assert {(owner, "applied", "apply") for owner in owners} <= rows
    assert research_table == (1,)
    assert list(backup_dir.glob("*.sqlite"))


def test_container_migration_status_uses_current_authoritative_backup_dir(
    monkeypatch, tmp_path, capsys
):
    from app import container_entrypoint
    from shared import migration, migration_runner, storage

    database = tmp_path / "runtime" / "cognitive.sqlite"
    backup_dir = tmp_path / "configured-backups"
    monkeypatch.setattr(storage, "DB_PATH", database)
    monkeypatch.setattr(migration, "BACKUP_DIR", backup_dir)

    class RecordingOperator:
        def __init__(self, *, db_path, backup_dir):
            assert Path(db_path).resolve() == database.resolve()
            assert Path(backup_dir).resolve() == backup_dir_path

        def status(self):
            return [{"owner": "core.sqlite", "state": "pending"}]

    backup_dir_path = backup_dir.resolve()
    monkeypatch.setattr(migration_runner, "MigrationOperator", RecordingOperator)

    assert container_entrypoint.run_migration_status(Namespace()) == 0
    assert json.loads(capsys.readouterr().out) == {
        "database": str(database),
        "status": [{"owner": "core.sqlite", "state": "pending"}],
    }


def test_core_schema_validation_requires_phase4_research_migration(
    monkeypatch, tmp_path, capsys
):
    from app import container_entrypoint
    from app.memory import database as memory_database
    from shared import backup, migration, storage

    database = tmp_path / "runtime" / "cognitive.sqlite"
    backup_dir = tmp_path / "backups"
    for module in (storage, memory_database, backup, migration):
        monkeypatch.setattr(module, "DB_PATH", database)
    monkeypatch.setattr(backup, "BACKUP_DIR", backup_dir)
    monkeypatch.setattr(migration, "BACKUP_DIR", backup_dir)

    assert container_entrypoint.run_migration(Namespace()) == 0
    capsys.readouterr()
    with sqlite3.connect(database) as connection:
        connection.execute("DROP TABLE research_packages_v1")

    with pytest.raises(RuntimeError, match="research migration schema"):
        storage.validate_schema()


def test_core_schema_validation_requires_baseline_operator_provenance(
    monkeypatch, tmp_path, capsys
):
    from app import container_entrypoint
    from app.memory import database as memory_database
    from shared import backup, migration, storage

    database = tmp_path / "runtime" / "cognitive.sqlite"
    backup_dir = tmp_path / "backups"
    for module in (storage, memory_database, backup, migration):
        monkeypatch.setattr(module, "DB_PATH", database)
    monkeypatch.setattr(backup, "BACKUP_DIR", backup_dir)
    monkeypatch.setattr(migration, "BACKUP_DIR", backup_dir)

    assert container_entrypoint.run_migration(Namespace()) == 0
    capsys.readouterr()
    with sqlite3.connect(database) as connection:
        connection.execute("DELETE FROM migration_operator_runs WHERE owner='core.sqlite'")

    with pytest.raises(RuntimeError, match="operator provenance"):
        storage.validate_schema()


def test_core_schema_validation_rejects_named_but_malformed_baseline_table(
    monkeypatch, tmp_path, capsys
):
    from app import container_entrypoint
    from app.memory import database as memory_database
    from shared import backup, migration, storage

    database = tmp_path / "runtime" / "cognitive.sqlite"
    backup_dir = tmp_path / "backups"
    for module in (storage, memory_database, backup, migration):
        monkeypatch.setattr(module, "DB_PATH", database)
    monkeypatch.setattr(backup, "BACKUP_DIR", backup_dir)
    monkeypatch.setattr(migration, "BACKUP_DIR", backup_dir)

    assert container_entrypoint.run_migration(Namespace()) == 0
    capsys.readouterr()
    with sqlite3.connect(database) as connection:
        connection.execute("DROP TABLE permission_decisions")
        connection.execute("CREATE TABLE permission_decisions (id TEXT PRIMARY KEY)")

    with pytest.raises(RuntimeError, match="baseline schema"):
        storage.validate_schema()


def test_core_schema_validation_uses_readonly_research_connection(
    monkeypatch, tmp_path, capsys
):
    from app import container_entrypoint
    from app.memory import database as memory_database
    from shared import backup, migration, research_migration, storage

    database = tmp_path / "runtime" / "cognitive.sqlite"
    backup_dir = tmp_path / "backups"
    for module in (storage, memory_database, backup, migration):
        monkeypatch.setattr(module, "DB_PATH", database)
    monkeypatch.setattr(backup, "BACKUP_DIR", backup_dir)
    monkeypatch.setattr(migration, "BACKUP_DIR", backup_dir)
    assert container_entrypoint.run_migration(Namespace()) == 0
    capsys.readouterr()

    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        connection.execute("PRAGMA journal_mode=DELETE")
    sidecars = [Path(f"{database}{suffix}") for suffix in ("-wal", "-shm")]
    assert all(not path.exists() for path in sidecars)
    calls: list[Path] = []
    original_connect = sqlite3.connect

    def recording_connect(target: Path):
        calls.append(target)
        uri = f"{target.resolve().as_uri()}?mode=ro&immutable=1"
        connection = original_connect(uri, uri=True, timeout=30.0)
        connection.execute("PRAGMA busy_timeout=30000")
        connection.execute("PRAGMA query_only=ON")
        connection.row_factory = sqlite3.Row
        return connection

    def forbidden_connect(target, *args, **kwargs):
        if str(target) == ":memory:":
            return original_connect(target, *args, **kwargs)
        raise AssertionError("startup validation bypassed the unified readonly connector")

    def forbidden_status(*_args, **_kwargs):
        raise AssertionError("startup validation opened a second migration status connection")

    monkeypatch.setattr(
        research_migration, "_connect_readonly", recording_connect, raising=False
    )
    monkeypatch.setattr(storage.sqlite3, "connect", forbidden_connect)
    monkeypatch.setattr(migration, "status", forbidden_status)
    storage.validate_schema()

    assert calls == [database]
    assert all(not path.exists() for path in sidecars)


def test_cli_pipeline_holds_target_runtime_lease(monkeypatch):
    from app.cli import cmd_pipeline
    from shared import backup, pipeline, storage

    events: list[tuple[str, Path]] = []

    @contextmanager
    def recording_lease(target):
        resolved = Path(target).resolve()
        events.append(("enter", resolved))
        try:
            yield
        finally:
            events.append(("exit", resolved))

    def recording_pipeline(*, source, input_data):
        assert events == [("enter", storage.DB_PATH.resolve())]
        return {"source": source, "input": input_data}

    monkeypatch.setattr(backup, "runtime_lease", recording_lease)
    monkeypatch.setattr(pipeline, "run_pipeline", recording_pipeline)

    cmd_pipeline("text", "payload")

    assert events == [
        ("enter", storage.DB_PATH.resolve()),
        ("exit", storage.DB_PATH.resolve()),
    ]


@pytest.mark.parametrize("action", ("apply", "rollback"))
def test_cli_effectful_migration_holds_explicit_target_runtime_lease(
    action, monkeypatch, tmp_path, capsys
):
    from app.cli import cmd_migrate
    from shared import backup, migration_runner

    database = tmp_path / "explicit.sqlite"
    backup_dir = tmp_path / "backups"
    events: list[tuple[str, Path]] = []

    @contextmanager
    def recording_lease(target):
        resolved = Path(target).resolve()
        events.append(("enter", resolved))
        try:
            yield
        finally:
            events.append(("exit", resolved))

    class RecordingOperator:
        def __init__(self, *, db_path, backup_dir):
            assert Path(db_path).resolve() == database.resolve()
            assert Path(backup_dir).resolve() == backup_dir_path

        def apply(self, owner):
            assert events == [("enter", database.resolve())]
            return {"action": "apply", "owner": owner}

        def rollback(self, owner):
            assert events == [("enter", database.resolve())]
            return {"action": "rollback", "owner": owner}

    backup_dir_path = backup_dir.resolve()
    monkeypatch.setattr(backup, "runtime_lease", recording_lease)
    monkeypatch.setattr(migration_runner, "MigrationOperator", RecordingOperator)
    monkeypatch.delenv("COGNITIVE_DB_PATH", raising=False)

    cmd_migrate(
        [
            action,
            "--owner",
            "taskpack.sqlite",
            "--db",
            str(database),
            "--backup-dir",
            str(backup_dir),
        ]
    )

    assert events == [
        ("enter", database.resolve()),
        ("exit", database.resolve()),
    ]
    assert "COGNITIVE_DB_PATH" not in os.environ
    assert json.loads(capsys.readouterr().out)["action"] == action


def test_compose_defines_production_stack_without_direct_app_ports():
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    services = compose["services"]
    assert set(services) >= {
        "migration",
        "core",
        "caddy",
        "backup",
        "integrity",
        "restore-candidate",
        "restore-activate",
    }
    assert "research" not in services
    assert "postgres" not in services
    assert "redis" not in services
    assert "kubernetes" not in services

    for service_name in (
        "migration",
        "core",
        "backup",
        "integrity",
        "restore-candidate",
        "restore-activate",
    ):
        service = services[service_name]
        assert "cognitive-sqlite:/app/data" in service["volumes"]
        assert "env_file" not in service
        assert "ports" not in service
        assert service["user"] == "10001:10001"
        assert service["cap_drop"] == ["ALL"]
        assert service["security_opt"] == ["no-new-privileges:true"]
        assert service["read_only"] is True
        assert any(item.startswith("/tmp:") for item in service["tmpfs"])

    assert services["migration"]["command"] == ["migrate"]
    assert services["migration"]["restart"] == "no"
    assert services["core"]["depends_on"]["migration"]["condition"] == "service_completed_successfully"
    assert services["caddy"]["depends_on"]["core"]["condition"] == "service_healthy"
    assert "research" not in services["caddy"]["depends_on"]
    assert services["caddy"]["networks"]["edge"]["ipv4_address"] == "172.28.0.2"
    assert services["core"]["networks"]["edge"]["ipv4_address"] == "172.28.0.3"
    assert services["core"]["restart"] == "unless-stopped"
    assert services["caddy"]["restart"] == "unless-stopped"
    assert services["caddy"]["user"] == "1000:1000"
    assert services["caddy"]["cap_drop"] == ["ALL"]
    assert services["caddy"]["security_opt"] == ["no-new-privileges:true"]
    assert services["caddy"]["read_only"] is True
    assert services["backup"]["profiles"] == ["ops"]
    assert services["integrity"]["profiles"] == ["ops"]
    assert services["restore-candidate"]["profiles"] == ["ops"]
    assert services["restore-activate"]["profiles"] == ["ops"]
    assert "ports" in services["caddy"]
    assert services["caddy"]["image"] == "cognitive-caddy:${COGNITIVE_IMAGE_TAG:-local}"
    assert services["caddy"]["build"]["dockerfile"] == "docker/Caddy.Dockerfile"
    caddy_dockerfile = (ROOT / "docker" / "Caddy.Dockerfile").read_text(encoding="utf-8")
    assert "golang:1.26.5-alpine3.23@sha256:622e56dbc11a8cfe" in caddy_dockerfile
    assert "github.com/caddyserver/caddy/v2/cmd/caddy@${CADDY_VERSION}" in caddy_dockerfile
    assert "GOSUMDB=sum.golang.org" in caddy_dockerfile
    assert "go version -m /go/bin/caddy > /caddy.buildinfo" in caddy_dockerfile
    assert "FROM scratch" in caddy_dockerfile
    assert "cognitive-sqlite" in compose["volumes"]
    assert compose["networks"]["edge"]["ipam"]["config"][0]["subnet"] == "172.28.0.0/24"

    rendered = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert "COGNITIVE_API_KEY:?Set in .env.container" in rendered
    assert "COGNITIVE_JWT_SECRET:?Set in .env.container" in rendered
    assert "COGNITIVE_TRUSTED_PROXIES" in rendered
    assert "COGNITIVE_TRUSTED_PROXIES: 172.28.0.2/32" in rendered
    assert "172.28.0.0/24}" not in rendered
    assert "env_file" not in rendered
    caddy_environment = services["caddy"]["environment"]
    assert "COGNITIVE_API_KEY" not in caddy_environment
    assert "COGNITIVE_JWT_SECRET" not in caddy_environment
    assert set(services["backup"]["environment"]) == {"COGNITIVE_DATA_DIR", "COGNITIVE_DB_PATH"}


def test_caddy_exposes_only_the_governed_core_gateway():
    production = (ROOT / "docker" / "Caddyfile").read_text(encoding="utf-8")
    ci = (ROOT / "docker" / "Caddyfile.ci").read_text(encoding="utf-8")
    for text in (production, ci):
        assert "reverse_proxy core:8000" in text
        assert "research:8001" not in text
        assert "handle /internal/*" in text
        assert "header_up -Forwarded" in text
        assert "header_up X-Forwarded-For {http.request.remote.host}" in text
        assert "header_up X-Real-IP {http.request.remote.host}" in text
    assert "{$COGNITIVE_DOMAIN}" in production
    assert "tls {$CADDY_TLS_EMAIL}" in production
    assert ":{$CADDY_INTERNAL_HTTP_PORT}" in ci

    override = yaml.safe_load((ROOT / "docker-compose.ci.yml").read_text(encoding="utf-8"))
    caddy = override["services"]["caddy"]
    assert "./docker/Caddyfile.ci:/etc/caddy/Caddyfile:ro" in caddy["volumes"]


def test_supported_launchers_use_one_unified_writer_process():
    shell = (ROOT / "run_all.sh").read_text(encoding="utf-8")
    batch = (ROOT / "run_all.bat").read_text(encoding="utf-8")
    for launcher in (shell, batch):
        assert "app.container_entrypoint migrate" in launcher
        assert "app.container_entrypoint core" in launcher
        assert "inspiration_research.api:app" not in launcher
        assert "--port 8001" not in launcher


def test_env_example_is_placeholder_only_and_keeps_real_env_untracked():
    example = (ROOT / ".env.container.example").read_text(encoding="utf-8")
    assert "replace-with" not in example
    assert re.search(r"^COGNITIVE_API_KEY=$", example, re.MULTILINE)
    assert re.search(r"^COGNITIVE_JWT_SECRET=$", example, re.MULTILINE)
    assert "COGNITIVE_DOMAIN=" in example
    assert ".env.container" in (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "!.env.container.example" in (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "sk-" not in example
    assert re.search(r"(?i)\b[0-9a-f]{32,}\b", example) is None


def test_container_deployment_docs_cover_required_operations_and_limits():
    docs = (ROOT / "docs" / "CONTAINER_DEPLOYMENT.md").read_text(encoding="utf-8")
    for phrase in (
        "Build",
        "Configure",
        "Start",
        "Health",
        "Migration",
        "Backup",
        "Restore Drill",
        "Restore Activation",
        "Upgrade",
        "Rollback",
        "local SSD",
        "single host",
        "single worker",
        "SQLite",
        "shared.migration",
        "one durable SQLite writer",
        "--no-deps",
    ):
        assert phrase in docs


def test_container_workflow_builds_real_stack_and_checks_runtime_contracts():
    workflow = (ROOT / ".github" / "workflows" / "container.yml").read_text(encoding="utf-8")
    assert "pull_request:" in workflow
    assert "openssl rand -hex 32" in workflow
    assert "docker compose --env-file .env.container" in workflow
    assert "build" in workflow
    assert "config --quiet" in workflow
    assert "up -d --wait migration core caddy" in workflow
    assert "sleep " not in workflow
    assert "--retry 60" in workflow
    assert "http://127.0.0.1:8080/health" in workflow
    assert "http://127.0.0.1:8080/internal/research/health" in workflow
    assert "exec -T research" not in workflow
    assert "_load_registry_repos" in workflow
    assert "id -u" in workflow
    assert "restart core" in workflow
    restart = workflow.index("restart core")
    first_backup_write = workflow.index("restore-before")
    post_restart_health = workflow.index(
        "curl --retry 60 --retry-delay 2 --retry-all-errors -fsS http://127.0.0.1:8080/health",
        restart,
    )
    assert restart < post_restart_health < first_backup_write
    assert "restore-candidate" in workflow
    assert "restore-activate" in workflow
    assert workflow.count("run --rm --no-deps") >= 4
    assert "run --rm integrity" not in workflow
    assert "run --rm backup" not in workflow
    assert "integrity" in workflow
    assert "stop caddy core" in workflow
    assert "ghcr.io/${GITHUB_REPOSITORY,,}" in workflow
    assert "docker push" in workflow
    assert "needs: [quality, smoke]" in workflow
    assert "packages: write" in workflow
    top_permissions = workflow.split("jobs:", 1)[0]
    smoke_job = workflow.split("  publish:", 1)[0].split("  smoke:", 1)[1]
    publish_job = workflow.split("  publish:", 1)[1]
    assert "packages: write" not in top_permissions
    assert "packages: write" not in smoke_job
    assert "packages: write" in publish_job
    assert "github.event_name == 'push' && github.ref == 'refs/heads/main'" in workflow
    assert "needs.smoke.outputs.image_id" in workflow
    assert "Capture verified image identity" in workflow
    assert "down -v --remove-orphans" in workflow
    assert "git ls-files" in workflow
    assert "actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5" in workflow
    assert "actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065" in workflow
    assert "astral-sh/setup-uv@d0cc045d04ccac9d8b7881df0226f9e82c39688e" in workflow
    assert workflow.count("aquasecurity/trivy-action@ed142fd0673e97e23eac54620cfb913e5ce36c25") == 2
    assert "image-ref: cognitive-loop-os:ci" in workflow
    assert "image-ref: cognitive-caddy:ci" in workflow
    assert 'caddy /usr/bin/caddy version)" = "v2.11.4"' in workflow
    assert "severity: CRITICAL,HIGH,MEDIUM" in workflow
    assert "ignore-unfixed: true" in workflow
    assert "exit-code: 1" in workflow
    assert "python -m pytest tests -q --tb=short" in workflow


def test_requirements_txt_matches_pyproject_runtime_dependencies():
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    declared = pyproject["project"]["dependencies"]
    requirements = [
        line.strip()
        for line in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    assert requirements == declared


def test_all_ci_actions_are_commit_pinned():
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "actions/checkout@v" not in workflow
    assert "actions/setup-python@v" not in workflow
    assert "astral-sh/setup-uv@v" not in workflow
    for action in (
        "actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5",
        "actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065",
        "astral-sh/setup-uv@d0cc045d04ccac9d8b7881df0226f9e82c39688e",
    ):
        assert action in workflow
