"""ArcheAxis v2 — unified runtime for the Cognitive Loop.

Port 8000: Core OS (route → execute → trace → eval → lesson)
Port 8000/kb: Knowledge-Base (live-counted endpoints, dashboard, capabilities)

Start: python -m app.runtime_entrypoint core
Then:  http://localhost:8000/docs     — Core API
       http://localhost:8000/kb/docs   — Knowledge-Base API
       http://localhost:8000/kb        — Dashboard
"""

from __future__ import annotations

import time
from contextlib import asynccontextmanager
from hashlib import sha256
from ipaddress import ip_address, ip_network
from threading import Lock

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from shared.config import config, validate_runtime_config
from shared.rate_limit import RateLimiter
from shared.research_boundary import unreviewed_research_references

validate_runtime_config(config)

# ── Core app ─────────────────────────────────────────────


@asynccontextmanager
async def core_runtime_lifespan(_: FastAPI):
    from shared.runtime_guard import core_runtime_guard
    from shared.storage import validate_schema

    with core_runtime_guard(validate=validate_schema):
        yield


app = FastAPI(
    lifespan=core_runtime_lifespan,
    title="ArcheAxis Knowledge — Human–AI Learning Workspace",
    version=str(config.get("app.version", "0.5.0")),
    description="Local-first, evidence-driven Human–AI learning and knowledge workspace. "
    "The current vertical targets approved Vault roots, Markdown, JSON Canvas, revisions, conflicts and readback. "
    "Third-party projects are reference or planned adapters unless the compatibility matrix says otherwise.",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.get("cors.allow_origins", ["*"]),
    allow_methods=config.get("cors.allow_methods", ["GET", "POST"]),
    allow_headers=config.get("cors.allow_headers", ["Authorization", "Content-Type"]),
)

_RATE_LIMITER_LOCK = Lock()
_RATE_LIMITER_SIGNATURE: tuple[int, int, int, int, int] | None = None
_RATE_LIMITERS: dict[str, RateLimiter] = {}


def _positive_rate_limit(name: str, default: int) -> int:
    value = config.get(f"rate_limit.{name}", default)
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise RuntimeError(f"rate_limit.{name} must be a positive integer")
    return value


def _gateway_rate_limiters() -> dict[str, RateLimiter]:
    """Return process-local policy limiters, rebuilding after a config change."""
    global _RATE_LIMITER_SIGNATURE, _RATE_LIMITERS
    window = _positive_rate_limit("window_seconds", 60)
    signature = (
        window,
        _positive_rate_limit("ordinary_read", 200),
        _positive_rate_limit("sensitive_write", 30),
        _positive_rate_limit("auth_token", 5),
        _positive_rate_limit("max_buckets_per_policy", 10_000),
    )
    with _RATE_LIMITER_LOCK:
        if signature != _RATE_LIMITER_SIGNATURE:
            _RATE_LIMITERS = {
                "ordinary_read": RateLimiter(signature[1], window, max_keys=signature[4]),
                "sensitive_write": RateLimiter(signature[2], window, max_keys=signature[4]),
                "auth_token": RateLimiter(signature[3], window, max_keys=signature[4]),
            }
            _RATE_LIMITER_SIGNATURE = signature
        return _RATE_LIMITERS


def _rate_limit_policy(request: Request) -> str:
    if request.url.path == "/auth/token":
        return "auth_token"
    if request.method.upper() in {"POST", "PUT", "PATCH", "DELETE"}:
        return "sensitive_write"
    return "ordinary_read"


def _trusted_proxy_networks():
    configured = config.get("rate_limit.trusted_proxies", [])
    if not isinstance(configured, list):
        return []
    try:
        return [ip_network(entry, strict=False) for entry in configured if isinstance(entry, str)]
    except ValueError:
        return []


def _direct_peer_is_trusted(request: Request) -> bool:
    if not request.client:
        return False
    try:
        peer = ip_address(request.client.host)
    except ValueError:
        return False
    return any(peer in network for network in _trusted_proxy_networks())


def _has_proxy_identity_headers(request: Request) -> bool:
    return any(request.headers.get(name) for name in ("X-Forwarded-For", "Forwarded", "X-Real-IP"))


def _has_ambiguous_credentials(request: Request) -> bool:
    return bool(request.headers.get("X-API-Key") and request.headers.get("Authorization"))


def _observed_client_host(request: Request) -> str:
    """Resolve a client only through an explicitly trusted direct proxy chain."""
    peer = request.client.host if request.client else "unknown-peer"
    networks = _trusted_proxy_networks()
    if not networks or not _direct_peer_is_trusted(request):
        return peer

    forwarded_for = request.headers.get("X-Forwarded-For", "")
    try:
        chain = [ip_address(item.strip()) for item in forwarded_for.split(",") if item.strip()]
    except ValueError:
        return peer
    if not chain:
        return peer
    for candidate in reversed(chain):
        if not any(candidate in network for network in networks):
            return str(candidate)
    return str(chain[0])


def _rate_limit_identity(request: Request, user: dict) -> str:
    auth_method = str(user.get("auth_method", "none"))
    if auth_method == "api_key":
        # Hash the credential immediately; raw keys never enter limiter state or responses.
        credential = request.headers.get("X-API-Key", "")
        if not credential:
            authorization = request.headers.get("Authorization", "")
            credential = authorization.removeprefix("Bearer ")
        material = f"api_key\0{credential}".encode()
    elif auth_method == "jwt":
        material = f"jwt\0{user.get('sub', '')}".encode()
    else:
        material = f"anonymous\0{_observed_client_host(request)}".encode()
    return sha256(material).hexdigest()


def _pre_auth_identity(request: Request, *, untrusted_proxy_headers: bool) -> str:
    if untrusted_proxy_headers:
        # The socket peer may already have been rewritten by an outer ASGI layer.
        # A fixed opaque bucket avoids trusting attacker-controlled header identity.
        return sha256(b"untrusted-proxy-identity-headers").hexdigest()
    return _rate_limit_identity(request, {"auth_method": "none"})


def _rate_limit_rejection(policy: str, result) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={
            "error": "rate_limit_exceeded",
            "detail": "request rate limit exceeded",
            "policy": policy,
            "retry_after_seconds": result.retry_after_seconds,
        },
        headers={
            "Retry-After": str(result.retry_after_seconds),
            "X-RateLimit-Limit": str(result.limit),
            "X-RateLimit-Remaining": "0",
        },
    )


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    untrusted_proxy_headers = _has_proxy_identity_headers(request) and not _direct_peer_is_trusted(
        request
    )
    ambiguous_credentials = _has_ambiguous_credentials(request)
    rate_result = None
    rate_policy = _rate_limit_policy(request)
    limiter = None
    pre_auth_key = ""

    # Reserve capacity before every early rejection and credential parse. When an
    # outer ASGI layer may have rewritten the peer, use one fixed fail-closed bucket.
    if bool(config.get("rate_limit.enabled", True)):
        limiter = _gateway_rate_limiters()[rate_policy]
        pre_auth_key = (
            f"{rate_policy}:pre_auth:"
            f"{_pre_auth_identity(request, untrusted_proxy_headers=untrusted_proxy_headers)}"
        )
        rate_result = limiter.check(pre_auth_key)
        if not rate_result.allowed:
            return _rate_limit_rejection(rate_policy, rate_result)

    rejection_headers = {}
    if rate_result is not None:
        rejection_headers = {
            "X-RateLimit-Limit": str(rate_result.limit),
            "X-RateLimit-Remaining": str(rate_result.remaining),
        }
    if untrusted_proxy_headers:
        return JSONResponse(
            status_code=400,
            content={
                "error": "untrusted_proxy_headers",
                "detail": "proxy identity headers require an explicit trusted-proxy policy",
            },
            headers=rejection_headers,
        )
    if ambiguous_credentials:
        return JSONResponse(
            status_code=400,
            content={
                "error": "ambiguous_credentials",
                "detail": "send exactly one of Authorization or X-API-Key",
            },
            headers=rejection_headers,
        )

    # ── Auth check (skip allowlist) ──
    from shared.auth import authenticate_request, authorize_request

    user = authenticate_request(
        request.url.path,
        request.headers.get("X-API-Key", ""),
        request.headers.get("Authorization", ""),
    )
    if not user:
        headers = {}
        if rate_result is not None:
            headers = {
                "X-RateLimit-Limit": str(rate_result.limit),
                "X-RateLimit-Remaining": str(rate_result.remaining),
            }
        return JSONResponse(
            status_code=401,
            content={
                "error": "unauthorized",
                "detail": "Valid API key or token required. Use X-API-Key header.",
            },
            headers=headers,
        )

    request.state.identity = user

    if limiter is not None and user.get("auth_method") in {"api_key", "jwt"}:
        limiter.release(pre_auth_key)
        rate_result = limiter.check(f"{rate_policy}:{_rate_limit_identity(request, user)}")
        if not rate_result.allowed:
            return _rate_limit_rejection(rate_policy, rate_result)

    if not authorize_request(user, request.method, request.url.path):
        return JSONResponse(
            status_code=403,
            content={
                "error": "forbidden",
                "detail": "The authenticated role is not allowed to perform this operation.",
            },
            headers=rejection_headers,
        )

    response = await call_next(request)
    duration = round((time.time() - start) * 1000, 1)
    response.headers["X-Process-Time-ms"] = str(duration)
    if rate_result is not None:
        response.headers["X-RateLimit-Limit"] = str(rate_result.limit)
        response.headers["X-RateLimit-Remaining"] = str(rate_result.remaining)
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    environment = str(config.get("app.environment", "development")).lower()
    detail = str(exc)[:200] if environment not in {"production", "prod"} else "request failed"
    return JSONResponse(
        status_code=500,
        content={"error": "internal_error", "detail": detail},
    )


# ── Mount packaged sub-applications (fault-tolerant) ──
from app.workspace.router import router as workspace_router

_research_app = None
_kb_app = None
try:
    from inspiration_research.api import app as research_app
    _research_app = research_app
except ImportError:
    pass
try:
    from knowledge_base.api import app as kb_app
    _kb_app = kb_app
except ImportError:
    pass

if _research_app is not None:
    app.mount("/internal/research", _research_app)
if _kb_app is not None:
    app.mount("/kb", _kb_app)
app.include_router(workspace_router)
# Naming contract §4: canonical API root is /api/v1/ (workspace router
# mounted under both the legacy /workspace path and the canonical root;
# the legacy path stays until all clients flip).
app.include_router(workspace_router, prefix="/api/v1")


def _http_route_counts() -> dict[str, int]:
    """Count OpenAPI operations without depending on FastAPI's private route wrappers."""
    operation_names = {"get", "put", "post", "delete", "options", "head", "patch", "trace"}

    def count_schema(current_app: FastAPI) -> int:
        return sum(
            1
            for path_item in current_app.openapi().get("paths", {}).values()
            for method in path_item
            if method.lower() in operation_names
        )

    core = count_schema(app)
    kb = count_schema(kb_app)
    return {"core": core, "kb": kb, "total": core + kb}


# ── Core endpoints ───────────────────────────────────────

from app.api.ingest import ingest
from app.core.compiler import compile_task
from app.core.router import route
from app.core.trace import list_traces
from app.evaluation.governance import list_reviewed_feedback
from app.facades.runtime import run_runtime_task
from app.ingestion.file import IngestionError, ingest_directory, ingest_file
from app.ingestion.multi_format import convert_directory as multi_convert_directory
from app.ingestion.multi_format import convert_file, convert_url
from app.memory.store import list_lessons, save_lesson, save_memory, search_memory
from app.rag.retriever import retrieve
from app.tools.registry import list_tools
from shared import storage


@app.get("/health")
def health():
    """Comprehensive system health check."""
    from shared.storage import count as _c

    return {
        "status": "ok",
        "system": "ArcheAxis-Knowledge-OS",
        "version": str(config.get("app.version", "0.5.0")),
        "endpoints": _http_route_counts(),
        "stats": {
            "documents": _c("kb_documents"),
            "cards": _c("kb_cards"),
            "reviews": _c("kb_reviews"),
            "machine_knowledge": _c("machine_knowledge_units"),
            "graph_nodes": _c("graph_entities"),
            "tools": len(list_tools()),
        },
    }


@app.get("/diagnostics")
def diagnostics():
    """Return a safe, read-only summary of runtime and migration status."""
    from collections import Counter

    from shared.migration_runner import MigrationOperator

    try:
        migrations = dict(Counter(item["state"] for item in MigrationOperator().status())) or {
            "unavailable": 1
        }
    except Exception:
        migrations = {"unavailable": 1}
    from app.release import safe_release_summary

    release = safe_release_summary()
    return {
        "schema_version": "v1",
        "health": health(),
        "migrations": migrations,
        "release": release,
    }


@app.get("/version")
def version():
    from app.release import effective_capabilities, load_release_manifest, safe_release_summary

    manifest = load_release_manifest()
    return {
        "product": manifest["product"]["english_name"],
        "version": manifest["product"]["version"],
        "release": safe_release_summary(),
        "capabilities": effective_capabilities(),
    }


@app.get("/tools")
def tools():
    return {"items": list_tools()}


def _reject_unreviewed_input_source(input_data: dict) -> None:
    if unreviewed_research_references([input_data.get("source", "")]):
        raise HTTPException(
            status_code=409,
            detail="candidate or external sources require server-owned Phase 5 review provenance",
        )


@app.post("/ingest")
def ingest_api(input_data: dict):
    _reject_unreviewed_input_source(input_data)
    doc = ingest(input_data)
    save_memory(doc)
    return doc


@app.post("/ingest/file")
def ingest_file_api(payload: dict):
    _reject_unreviewed_input_source(payload)
    try:
        doc = ingest_file(
            str(payload.get("path", "")),
            source=payload.get("source"),
            metadata=payload.get("metadata"),
        )
    except IngestionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    decision = route(doc)
    doc.attention_score = decision.score
    doc.route = decision.route
    if decision.route != "DROP":
        save_memory(doc)
    return {"document": doc, "route": decision}


@app.post("/ingest/directory")
def ingest_directory_api(payload: dict):
    _reject_unreviewed_input_source(payload)
    try:
        docs = ingest_directory(
            str(payload.get("path", "")),
            pattern=str(payload.get("pattern", "*.md")),
            limit=int(payload.get("limit", 50)),
            source=payload.get("source"),
            metadata=payload.get("metadata"),
        )
    except IngestionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    items = []
    for doc in docs:
        decision = route(doc)
        doc.attention_score = decision.score
        doc.route = decision.route
        if decision.route != "DROP":
            save_memory(doc)
        items.append({"document": doc, "route": decision})
    return {"count": len(items), "items": items}


@app.post("/route")
def route_api(input_data: dict):
    doc = ingest(input_data)
    return route(doc)


@app.post("/run")
def run(input_data: dict):
    _reject_unreviewed_input_source(input_data)
    doc = ingest(input_data)
    decision = route(doc)
    doc.attention_score = decision.score
    doc.route = decision.route
    if decision.route == "DROP":
        return {"status": "ignored", "document": doc, "route": decision}
    if decision.route == "REVIEW":
        save_memory(doc)
        return {"status": "needs_review", "document": doc, "route": decision}
    save_memory(doc)
    context = retrieve(doc.content)
    task = compile_task(
        context,
        reviewed_feedback=list_reviewed_feedback(db_path=storage.DB_PATH),
    )
    runtime = run_runtime_task(doc, task, decision=decision)
    if runtime.permission.requires_human_review:
        return {
            "status": "blocked",
            "document": doc,
            "route": decision,
            "task": task,
            "permission": runtime.permission.model_dump(),
        }
    trace = runtime.trace
    eval_result = runtime.evaluation
    lesson = runtime.lesson
    if trace is None or eval_result is None or lesson is None:
        raise RuntimeError("runtime composite port returned an incomplete terminal result")
    save_lesson(lesson)
    return {
        "status": runtime.status,
        "document": doc,
        "route": decision,
        "context": context,
        "task": task,
        "permission": runtime.permission.model_dump(),
        "trace": trace,
        "eval": eval_result,
        "lesson": lesson,
    }


@app.post("/convert/file")
def convert_file_api(payload: dict):
    path = str(payload.get("path", ""))
    fmt = payload.get("format")
    try:
        content, engine = convert_file(path, fmt)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "path": path,
        "format": fmt or "auto",
        "engine": engine,
        "content": content,
        "char_count": len(content),
    }


@app.post("/convert/url")
def convert_url_api(payload: dict):
    url = str(payload.get("url", ""))
    try:
        content, engine = convert_url(url)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"url": url, "engine": engine, "content": content, "char_count": len(content)}


@app.post("/convert/directory")
def convert_directory_api(payload: dict):
    directory = str(payload.get("path", ""))
    pattern = str(payload.get("pattern", "*.*"))
    limit = int(payload.get("limit", 50))
    results = multi_convert_directory(directory, pattern, limit)
    return {"path": directory, "count": len(results), "items": results}


@app.post("/memory/search")
def memory_search(payload: dict):
    query = str(payload.get("query", ""))
    top_k = int(payload.get("top_k", 5))
    return {"query": query, "items": search_memory(query, top_k=top_k)}


@app.get("/traces")
def traces():
    return {"items": list_traces()}


@app.get("/memory/lessons")
def lessons():
    return {"items": list_lessons()}


# ── Auth + Backup + Architecture ─────────────────────────


@app.post("/auth/token")
def auth_token(request: Request, user_id: str = "", role: str = "user", expires_hours: int = 24):
    """Issue a bounded token; only an authenticated administrator may issue tokens."""
    from shared.auth import authenticate_request, create_token

    caller = authenticate_request(
        request.url.path,
        request.headers.get("X-API-Key", ""),
        request.headers.get("Authorization", ""),
    )
    if not caller or caller.get("role") != "admin":
        raise HTTPException(status_code=403, detail="administrator credentials required")
    if role not in {"admin", "user", "readonly"}:
        raise HTTPException(status_code=400, detail="invalid role")
    if not 1 <= expires_hours <= 168:
        raise HTTPException(status_code=400, detail="expires_hours must be between 1 and 168")
    subject = user_id.strip() or str(caller.get("sub", ""))
    if not subject:
        raise HTTPException(status_code=400, detail="user_id is required")
    token = create_token(user_id=subject, role=role, expires_hours=expires_hours)
    return {"token": token, "expires_in_hours": expires_hours}


@app.post("/backup")
def backup_db():
    """Create a database backup."""
    from shared.backup import auto_backup

    return auto_backup()


@app.get("/backup/list")
def backup_list():
    """List available backups."""
    from shared.backup import list_backups

    return {"backups": list_backups()}


@app.get("/architecture")
def architecture():
    """Return system architecture as Mermaid diagram."""
    return {
        "mermaid": """```mermaid
graph TB
    subgraph Clients["客户端"]
        Web["🌐 Dashboard"]; API["📡 API"]; Agent["🤖 MCP"]; Cron["⏰ Cron"]
    end
    subgraph Gateway["网关 :8000"]
        Auth["🔐 JWT"]; CORS["🌍 CORS"]; Log["📝 Log"]
    end
    subgraph Core["Core"]
        Router["🧭 Route"]; Pipeline["⚡ Pipeline"]; Tools["🔧 Tools"]
    end
    subgraph KB["Knowledge-Base"]
        Search["🔍 Search"]; Garden["🌱 Garden"]; Review["📚 SM-2"]
        Canvas["🎨 Canvas"]; MKU["🤖 MKU"]
    end
    subgraph Data["数据"]
        SQLite[("💾 SQLite")]; VecDB[("🧬 Vec")]; GraphDB[("🕸️ Graph")]; Backup[("📦 Backup")]
    end
    Web-->Auth; API-->Auth; Agent-->Auth; Cron-->Auth
    Auth-->Router; Router-->Pipeline; Pipeline-->Search; Pipeline-->Garden
    Search-->SQLite; Search-->VecDB; Garden-->GraphDB; Review-->SQLite; SQLite-->Backup
```""",
        "version": str(config.get("app.version", "0.5.0")),
        "measurement_note": "Module and test counts are intentionally not embedded.",
    }


# ── HERMES bedtime unattended loop engine ─────────────────


@app.get("/sleep-loop")
def sleep_loop_get(
    action: str = "status",
    run_id: str = "",
    task_id: str = "",
    status_filter: str = "",
    limit: int = 100,
):
    """Composite read endpoint for the bedtime unattended loop panel.

    Actions: status | tasks | attempts | logs | config | architecture
    """
    from shared import sleep_loop_engine as sl

    if action == "status":
        return sl.status()
    if action == "tasks":
        return {
            "items": sl.list_tasks(run_id=run_id or None, status=status_filter or None, limit=limit)
        }
    if action == "attempts":
        return {
            "items": sl.list_attempts(
                task_id=task_id or None,
                run_id=run_id or None,
                limit=limit,
            )
        }
    if action == "logs":
        return {"items": sl.list_events(run_id=run_id or None, limit=limit)}
    if action == "config":
        return {"config": sl.status().get("config")}
    if action == "architecture":
        return {"mermaid": sl.sleep_loop_architecture()}
    raise HTTPException(status_code=400, detail=f"unknown sleep-loop action: {action}")


@app.post("/sleep-loop")
async def sleep_loop_post(request: Request, action: str = "tick"):
    """Composite control endpoint for the bedtime unattended loop panel.

    Actions: start | stop | pause | resume | tick | config
    """
    from shared import sleep_loop_engine as sl

    payload = await request.json() if request.headers.get("content-length", "0") != "0" else {}
    if action == "start":
        goal = str(payload.get("goal", "就寝无人值守任务循环"))
        return sl.start_loop(goal, payload)
    if action == "stop":
        return sl.stop_loop(str(payload.get("reason", "manual_stop")))
    if action == "pause":
        return sl.pause_loop(str(payload.get("reason", "manual_pause")))
    if action == "resume":
        return sl.resume_loop()
    if action == "tick":
        from app.sleep_runtime import tick_once as tick_sleep_loop

        return tick_sleep_loop()
    if action == "config":
        return sl.set_config(payload.get("config", payload))
    raise HTTPException(status_code=400, detail=f"unknown sleep-loop action: {action}")
