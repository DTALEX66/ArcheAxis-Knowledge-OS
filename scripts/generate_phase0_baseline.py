"""Generate the reproducible Phase 0 repository baseline.

The collector is intentionally read-only with respect to business code and databases. It writes
only the requested reports under ``migrations/reports/phase-0``. Runtime imports and tests use a
fresh temporary data root that is removed after every run.
"""

from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
from collections import Counter
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from fastapi.routing import APIRoute
from starlette.routing import Mount

REQUIRED_REPORTS = (
    "ASSET_MAP.md",
    "FILE_INVENTORY.csv",
    "API_ROUTE_MAP.json",
    "DEPENDENCY_REPORT.md",
    "TEST_BASELINE.md",
    "SECURITY_BASELINE.md",
    "ARCHITECTURE_GAPS.md",
    "REUSE_DECISIONS.md",
    "PHASE_1_TASKPACK.md",
)

_INVENTORY_FIELDS = ("path", "category", "extension", "bytes", "lines", "sha256")
_SECRET_PATTERNS = {
    "private-key": re.compile(rb"-----BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----"),
    "github-token": re.compile(rb"gh[pousr]_[A-Za-z0-9_]{36,}"),
    "openai-key": re.compile(rb"sk-[A-Za-z0-9]{32,}"),
    "aws-access-key": re.compile(rb"AKIA[0-9A-Z]{16}"),
}


def _task_runtime_tmp_root() -> Path:
    root = Path(__file__).resolve().parents[1] / ".hermes" / "task-runtime" / "tmp"
    root.mkdir(parents=True, exist_ok=True)
    return root.resolve()


@contextmanager
def _temporary_runtime() -> Iterator[Path]:
    """Provide a unique project-contained runtime root and restore the caller environment."""
    previous_data_root = os.environ.get("COGNITIVE_DATA_DIR")
    previous_bytecode = os.environ.get("PYTHONDONTWRITEBYTECODE")
    with TemporaryDirectory(prefix="cognitive-phase0-", dir=_task_runtime_tmp_root()) as directory:
        runtime_root = Path(directory).resolve()
        os.environ["COGNITIVE_DATA_DIR"] = str(runtime_root)
        os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
        try:
            yield runtime_root
        finally:
            if previous_data_root is None:
                os.environ.pop("COGNITIVE_DATA_DIR", None)
            else:
                os.environ["COGNITIVE_DATA_DIR"] = previous_data_root
            if previous_bytecode is None:
                os.environ.pop("PYTHONDONTWRITEBYTECODE", None)
            else:
                os.environ["PYTHONDONTWRITEBYTECODE"] = previous_bytecode


def load_dependency_data(path: Path) -> dict[str, Any]:
    """Read the project dependency arrays using only Python 3.10 standard library APIs."""
    project: dict[str, Any] = {"dependencies": [], "optional-dependencies": {}}
    lines = path.read_text(encoding="utf-8").splitlines()
    section = ""
    index = 0
    while index < len(lines):
        line = lines[index].strip()
        index += 1
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1]
            continue
        if "=" not in line or section not in {"project", "project.optional-dependencies"}:
            continue
        key, raw_value = (part.strip() for part in line.split("=", 1))
        while raw_value.count("[") > raw_value.count("]") and index < len(lines):
            raw_value += "\n" + lines[index].strip()
            index += 1
        if section == "project" and key not in {"requires-python", "dependencies"}:
            continue
        try:
            value = ast.literal_eval(raw_value)
        except (SyntaxError, ValueError) as exc:
            raise ValueError(f"unsupported dependency declaration for {key}") from exc
        if section == "project" and key in {"requires-python", "dependencies"}:
            project[key] = value
        elif section == "project.optional-dependencies":
            project["optional-dependencies"][key] = value
    return {"project": project}


def _normalise_path(path: str) -> str:
    normalised = path.replace("\\", "/")
    while normalised.startswith("./"):
        normalised = normalised[2:]
    return normalised


def _category(path: str) -> str:
    normalised = _normalise_path(path)
    return normalised.split("/", 1)[0] if "/" in normalised else "root"


def _line_count(data: bytes) -> int:
    if not data:
        return 0
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return 0
    return len(text.splitlines())


def build_file_inventory(
    repo_root: Path,
    tracked_paths: Iterable[str],
    *,
    file_contents: dict[str, bytes] | None = None,
) -> list[dict[str, Any]]:
    """Return a deterministic, content-addressed inventory for repository-relative paths."""
    rows: list[dict[str, Any]] = []
    for raw_path in sorted({_normalise_path(path) for path in tracked_paths}):
        file_path = repo_root / raw_path
        if file_contents is None:
            if not file_path.is_file():
                continue
            data = file_path.read_bytes()
        else:
            if raw_path not in file_contents:
                continue
            data = file_contents[raw_path]
        rows.append(
            {
                "path": raw_path,
                "category": _category(raw_path),
                "extension": file_path.suffix.lower() or "[none]",
                "bytes": len(data),
                "lines": _line_count(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
        )
    return rows


def _join_route(prefix: str, path: str) -> str:
    joined = f"{prefix.rstrip('/')}/{path.lstrip('/')}"
    return joined if joined.startswith("/") else f"/{joined}"


def build_route_map(app: Any, prefix: str = "") -> list[dict[str, Any]]:
    """Recursively enumerate HTTP operations, including mounted FastAPI applications."""
    routes: list[dict[str, Any]] = []
    for route in app.routes:
        if isinstance(route, Mount) and hasattr(route.app, "routes"):
            routes.extend(build_route_map(route.app, _join_route(prefix, route.path)))
            continue
        if not isinstance(route, APIRoute):
            continue
        methods = sorted(method for method in (route.methods or set()) if method != "HEAD")
        routes.append(
            {
                "path": _join_route(prefix, route.path),
                "methods": methods,
                "name": route.name,
                "operation_id": route.operation_id,
            }
        )
    return sorted(routes, key=lambda item: (item["path"], item["methods"], item["name"]))


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=_INVENTORY_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def _markdown_table(rows: list[tuple[str, str]]) -> str:
    body = ["| 项目 | 结果 |", "|---|---|"]
    body.extend(f"| {key} | {value} |" for key, value in rows)
    return "\n".join(body)


def _operation_count(routes: Iterable[dict[str, Any]]) -> int:
    return sum(len(route.get("methods", [])) for route in routes)


def _service_summary(routes: Iterable[dict[str, Any]]) -> dict[str, dict[str, int]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for route in routes:
        grouped.setdefault(str(route.get("service", "unknown")), []).append(route)
    return {
        service: {
            "route_count": len(service_routes),
            "operation_count": _operation_count(service_routes),
        }
        for service, service_routes in sorted(grouped.items())
    }


def _asset_map(git_head: str, inventory: list[dict[str, Any]], routes: list[dict[str, Any]]) -> str:
    categories = Counter(row["category"] for row in inventory)
    category_rows = "\n".join(
        f"| `{category}` | {count} |" for category, count in sorted(categories.items())
    )
    service_rows = "\n".join(
        f"| `{service}` | {summary['route_count']} | {summary['operation_count']} |"
        for service, summary in _service_summary(routes).items()
    )
    return f"""# Phase 0 资产地图

> Git 基线：`{git_head}`。本报告只覆盖当前仓库中的 Git 跟踪文件。

## 总览

- 跟踪文件：{len(inventory)}
- HTTP 路由条目：{len(routes)}
- HTTP 操作：{_operation_count(routes)}
- 审计边界：当前仓库；外部仓库、个人资料库和运行时用户数据均不在范围内。

## API 服务边界

| 服务 | 路由条目 | HTTP 操作 |
|---|---:|---:|
{service_rows}

## 顶层资产

| 顶层区域 | 文件数 |
|---|---:|
{category_rows}

## 运行资产分工

- `app/`：核心认知运行时、路由、权限、执行、Trace、Evaluation 和 Lesson。
- `knowledge_base/`：可安装知识包、领域路由、检索、复习和机器知识。
- `Inspiration-Research/`：研究发现与项目雷达兼容目录。
- `shared/`：配置、鉴权、SQLite、备份、证据、摄入和 Sleep Loop。
- `shared-contracts/`：Schema、适配器和项目注册。
- `config/`：运行策略与运行时配置。
- `tests/`、`knowledge_base/tests/`、`integration-tests/`：三层门禁。
- `docs/`：当前事实、架构、路线图与历史审计。

## 证据入口

- 文件级证据：`FILE_INVENTORY.csv`
- API 证据：`API_ROUTE_MAP.json`
- 依赖证据：`DEPENDENCY_REPORT.md`
- 测试证据：`TEST_BASELINE.md`
- 风险和迁移决策：`SECURITY_BASELINE.md`、`ARCHITECTURE_GAPS.md`、
  `REUSE_DECISIONS.md`
"""


def _dependency_report(git_head: str, dependency_data: dict[str, Any]) -> str:
    project = dependency_data.get("project", {})
    runtime = project.get("dependencies", [])
    optional = project.get("optional-dependencies", {})
    runtime_rows = "\n".join(f"| `{item}` | runtime |" for item in runtime)
    optional_rows = "\n".join(
        f"| `{item}` | `{group}` |"
        for group, items in sorted(optional.items())
        for item in items
    )
    return f"""# Phase 0 依赖基线

> Git 基线：`{git_head}`。声明来源：`pyproject.toml`。

## Python 与打包

- Python：`>=3.10`
- 构建后端：`setuptools.build_meta`
- CLI：`cognitive-os = app.cli:main`
- 打包范围：`app*`、`shared*`、`knowledge_base*`、`config*`
- 当前 CI：Python 3.10、3.11、3.12。

## 运行依赖

| 声明 | 作用域 |
|---|---|
{runtime_rows}

## 可选依赖

| 声明 | 组 |
|---|---|
{optional_rows}

## 基线判断

1. `litellm` 被精确固定，其他大多数依赖使用下限或兼容范围。
2. `Inspiration-Research/` 不在 setuptools 包发现范围内，仍依赖兼容入口。
3. `requirements.txt` 与 `pyproject.toml` 并存，后续应建立一致性检查。
4. Mypy 已配置但不在正式 CI 门禁中。
5. Phase 1 不升级依赖；只建立 Facade、依赖方向守卫和合同测试。
"""


def _test_baseline(git_head: str, gate_results: dict[str, dict[str, Any]]) -> str:
    rows = []
    details = []
    for name, result in gate_results.items():
        status = str(result.get("status", "not-run"))
        summary = str(result.get("summary", "")).replace("|", "\\|")
        rows.append((f"`{name}`", f"**{status}** — {summary}"))
        command = result.get("command")
        warnings = result.get("warnings", [])
        if command or warnings:
            detail = [f"### {name}\n"]
            if command:
                working_directory = result.get("working_directory", ".")
                detail.append(
                    f"工作目录：`{working_directory}`\n\n"
                    f"```bash\n{command}\n```\n"
                )
            if warnings:
                detail.append(
                    "观测到的告警：\n\n" + "\n".join(f"- {warning}" for warning in warnings)
                )
            details.append("\n".join(detail))
    details_text = "\n\n".join(details)
    return f"""# Phase 0 测试基线

> Git 基线：`{git_head}`。结果由本次真实命令执行生成，不复用历史测试数字。
>
> 隔离：所有子进程在导入项目前设置每次运行唯一且自动删除的 `COGNITIVE_DATA_DIR`、`PYTHONDONTWRITEBYTECODE=1`，pytest 使用 `-p no:cacheprovider`。

## 门禁结果

{_markdown_table(rows)}

## 执行命令

{details_text}
## 解释规则

- `passed` 只表示该命令本次退出码为 0。
- `observed-failure` 是非阻断诊断基线，必须保留真实错误规模，不能改写为通过。
- `failed` 表示阻断门禁失败，保留真实摘要，不能改写为完成。
- `worktree-diff-check` 只检查生成开始时的 worktree↔index；最终 staged diff 必须在暂存后另跑 `git diff --cached --check`。
- Docker 未在本地执行时不得声称容器实机通过。
- GitHub Actions 状态必须在推送后单独核对。
"""


def _security_report(
    git_head: str,
    findings: list[dict[str, str]],
    secret_scan: dict[str, Any],
) -> str:
    finding_rows = "\n".join(
        f"| {item['id']} | {item['status']} | {item['evidence']} | {item['finding']} |"
        for item in findings
    )
    return f"""# Phase 0 安全基线

> Git 基线：`{git_head}`。范围仅限当前仓库 HEAD；证据包括静态代码审计和本次真实门禁，不等同于渗透测试、Git 历史扫描或部署验收。

## 执行摘要

生产配置具备鉴权必须开启、密钥必须显式提供、CORS 禁止通配符的 fail-fast 基线；SQLite 备份使用 online backup，并在恢复前验证候选快照。当前三个 P0 安全边界仍未闭合：

1. 已认证身份缺少端点级 RBAC，`readonly`、`user` 与 `admin` 没有写操作隔离。
2. 用户可控 URL 缺少完整 SSRF 防护，未统一拒绝回环、私网、链路本地、重定向后地址和超大响应。
3. 部分 API 绕过已有路径 containment，可读取、扫描或写入 approved root 之外的本地路径。

## 高置信秘密扫描

- 状态：**{secret_scan.get('status', 'not-run')}**
- 匹配数：{secret_scan.get('matches', 'unknown')}
- 规则：私钥头、GitHub token、OpenAI 风格 key、AWS access key。
- 范围：HEAD 中的 Git 跟踪文件；未扫描 Git 历史，不等同于 gitleaks/detect-secrets。
- 测试占位符和已知开发默认值不被误报为真实生产凭据；报告不得复述任何 credential 值。

## 已实现事实

| 控制域 | 仓库内证据 | 结论 |
|---|---|---|
| 共享鉴权 | `shared/auth.py:174-218`; `app/main.py:46-100`; `knowledge_base/api.py:43-78`; `Inspiration-Research/api.py:35-69` | 三个 FastAPI 应用共享 API key/Bearer 鉴权；公开路径有显式白名单。 |
| Token | `shared/auth.py:103-160`; `app/main.py:333-353` | HMAC-SHA256 token 校验签名与过期时间；token 签发显式要求管理员角色。 |
| 生产 fail-fast | `shared/config.py:177-243`; `docker-compose.yml:8-18,42-52` | 生产拒绝关闭鉴权、弱/缺失 secret、固定开发 key 与通配 CORS。 |
| CORS | `shared/config.py:126-175,213-229` | 生产 origins、methods、headers 均经过约束，默认不允许 credentials。 |
| 安全摄入 | `app/ingestion/file.py:8-51,68-112`; `knowledge_base/routers/quality.py:34-54` | 常规文件摄入与质量目录对仓库根执行 resolve + containment，并限制扩展名和规模。 |
| SQLite/备份 | `app/memory/database.py:19-26`; `shared/storage.py:282-450`; `shared/backup.py:24-91`; `tests/test_backup.py` | 关键 CRUD 使用参数绑定/allowlist；备份使用 SQLite online backup；恢复只生成并校验离线候选。 |
| 部署 | `Dockerfile:28-39`; `.github/workflows/ci.yml` | 容器以非 root 用户运行；现有单元、KB、集成及部署测试可阻断 CI。 |

## P0 缺口

| ID | 事实与影响 | 证据 | Phase 1/3 验收方向 |
|---|---|---|---|
| SEC-P0-01 | **端点级 RBAC 未系统化。** `/auth/token` 已要求 admin，但写入、导入、执行、备份等其他敏感端点未按角色拒绝；认证不等于授权。 | `app/main.py:333-361`; `shared/auth.py`; `knowledge_base/api.py:136-177` | 为敏感路由声明 admin/operator 权限；`readonly` 对所有变更操作稳定返回 403，并补合同测试。 |
| SEC-P0-02 | **SSRF 面。** `/convert/url`、KB pipeline、feed、n8n/Airflow 接受用户影响的 URL，只做 scheme 检查或完全不检查；未防私网、metadata、DNS rebinding、重定向和响应体放大。 | `app/main.py:296-314`; `app/ingestion/multi_format.py:187-211`; `knowledge_base/routers/composite.py:24-34`; `shared/pipeline.py:60-83`; `shared/feed_collector.py:105-118`; `app/workflow/n8n.py:13-16` | 建立 `safe_http_fetch()`：逐跳解析/校验 DNS 与 IP、限制端口/重定向/超时/响应大小；Webhook 使用 allowlist。 |
| SEC-P0-03 | **路径 containment 绕过。** `/convert/file`、`/convert/directory`、KB `/sources`、Obsidian/media 与 projection 路径没有统一允许根目录，可触及任意可读/可写路径。 | `app/main.py:296-362`; `app/ingestion/multi_format.py:152-256`; `knowledge_base/routers/composite.py:143-168`; `shared/source_discovery.py:45-109`; `shared/obsidian_projection.py:180-201` | 输入根与输出根分权；resolve 后验证 containment，并处理 symlink/junction 逃逸。 |
| SEC-P0-04 | 开发默认鉴权关闭且 CORS 为 `*`；若误绑外网，固定开发身份与跨域访问会放大暴露面。 | `shared/config.py:18-55`; `config/settings.yaml:1-14`; `README.md:59-79` | development 默认只绑定 loopback；外网绑定时强制开启鉴权并拒绝 wildcard CORS。 |

## 其他缺口

- JWT/API key 明文存储，未见 `chmod 0600` 或 Windows ACL、key ID、轮换、撤销、`aud`/`iss`；`token_expire_hours` 尚未接入签发路径（`shared/auth.py:82-103`; `shared/config.py:45-49`）。
- `shared/rate_limit.py` 未接鉴权失败和 token 签发；没有锁定策略。
- 未见 Trusted Host、HTTPS redirect 或 HSTS；需由应用或反向代理明确承担。
- 多处 HTTP 客户端整页读取，Crawl4AI 调用缺少显式总超时与响应大小上限。
- `shared.storage` 未统一启用 `foreign_keys`、`busy_timeout`、`synchronous`；多个直接 `sqlite3.connect()` 入口导致 PRAGMA 漂移。
- DB、备份与恢复候选未加密或显式加固 ACL；没有异地副本、调度告警、RPO/RTO 与恢复演练。
- `/backups` 可返回绝对路径，且备份相关端点没有管理员授权。
- 工具参数与结果可原样持久化到 SQLite，缺少集中 secret redaction 和敏感字段白名单（`app/memory/database.py:367-380`）。
- CI 缺少 CodeQL/SAST、依赖审计、Git 历史 secret scan、SBOM、容器扫描和最小 `permissions:`；Actions 未固定完整 SHA，依赖和基础镜像无锁定摘要。

## 生成器控制摘要

| ID | 状态 | 证据 | 结论 |
|---|---|---|---|
{finding_rows}

## 修复优先级

1. **P0：**端点级 RBAC、统一 SSRF 防护、统一 approved-root containment。
2. **P1：**开发 loopback 强制、集中 SQLite 连接工厂、secret redaction、CI 安全门禁。
3. **P2：**token 生命周期、备份加密/异地副本、恢复演练和供应链可复现。

## 验证限制

- 本报告没有声称渗透测试、Git 历史扫描、真实反向代理、TLS 或容器运行时已通过。
- GitHub Actions 状态必须在推送后独立核对。
"""


def _architecture_gaps(git_head: str) -> str:
    return f"""# Phase 0 架构缺口

> Git 基线：`{git_head}`。P0 表示进入 Phase 1 前必须定案或建立 Guard；P1 在 Facade 收口期间处理；P2 按后续路线图实施。

| ID | 优先级 | 事实与影响 | 仓库内证据 | 建议/目标 Phase |
|---|---|---|---|---|
| AG-01 | P0 | 实际依赖为 `app ↔ knowledge_base ↔ shared` 循环；非测试运行时 AST 审计为 app→KB 5、KB→app 3、shared→app 3、shared→KB 8 处。 | `app/main.py:82`; `app/tools/registry.py:203-247`; `knowledge_base/search/vector_search.py:8`; `shared/bridge.py:3-5` | Phase 1 定义单向依赖，Facade 截断反向导入，CI 禁止 Platform/Contracts 导入业务模块。 |
| AG-02 | P0 | **27 个非测试运行时文件**修改 `sys.path`，模块导入依赖源码目录布局。 | `Inspiration-Research/api.py:8-10`; `scripts/run_daily.py:11-13`; `shared/graph_rag.py:18-22`; `shared/web_search.py:20-21` | Phase 1 Guard 禁止新增；Facade 接通后逐步删除。 |
| AG-03 | P0 | 当前不是完整单网关：Core+KB 位于 8000，IR 仍是 8001 独立 FastAPI；三处重复 CORS、鉴权和异常接线。 | `app/main.py:22-103`; `knowledge_base/api.py:31-172`; `Inspiration-Research/api.py:25-136`; `docker-compose.yml:11-60` | Research Facade 先接主网关，独立入口只保留兼容期。 |
| AG-04 | P0 | ContextPack、TaskPack、ExecutionTrace、MachineLesson 在 `app`、`shared` 与 JSON Schema 中存在多个定义面，Schema 不是运行时 SSOT。 | `app/schemas.py`; `shared/schemas.py`; `shared-contracts/schemas/*.schema.json` | Phase 1 明确 legacy adapter；Phase 2 建版本化合同。 |
| AG-05 | P0 | 集成测试手工映射 KB→Runtime TaskPack，并手工保存 Lesson；只证明结构连通，不是完整 `/run → evaluation → reviewed lesson`。 | `integration-tests/test_ir_kb_os_loop.py:69-98` | 提取纯 adapter，增加 Schema/运行时模型合同测试。 |
| AG-06 | P0 | 同一 SQLite 文件由 Runtime、KB/IR、Sleep Loop 多套 DDL/初始化入口管理，部分模块 import 时创建目录或初始化 DB。 | `app/memory/database.py:11-132,431-432`; `shared/storage.py:21-279`; `shared/migration.py:19-232`; `shared/sleep_loop_engine.py:169-229,1087` | Phase 1 统一 composition root/Repository，不改表；正式 Migration Runner 留 Phase 3。 |
| AG-07 | P0 | 持久化 rowid 和文本 embedding 使用 Python `hash()`，跨进程不稳定，重启后可能得到不同 ID/向量。 | `app/memory/vector_db.py:91-109,143-150,300-303`; `docs/EXECUTION_ROADMAP.md:85-90` | Phase 3 换稳定哈希并设计索引重建/回滚；不得作为新 Adapter ID 规则复用。 |
| AG-08 | P1 | `knowledge_base/api.py` 为 1171 行、91 个直接路由的巨型兼容入口，跨 KB/IR/Obsidian 多域。 | `knowledge_base/api.py`; `knowledge_base/routers/composite.py`; `quality.py`; `projection.py` | 冻结新增，按领域拆 router；新 Facade 不直接依赖整个 API app。 |
| AG-09 | P1 | `shared/sleep_loop_engine.py` 为 1087 行、34 个顶层函数，兼有 schema、队列、guard、执行、资源控制和状态查询。 | `shared/sleep_loop_engine.py:34-1087` | 先包 SleepLoop Facade，后拆 repository/service/worker/policy，不复制第二套完成语义。 |
| AG-10 | P1 | 只有 `route_policy.yaml` 被运行时读取；`tools.yaml`、`models.yaml`、agent/codex profile 没有业务消费，工具风险仍硬编码。 | `app/core/router.py:16-29`; `config/*.yaml`; `app/tools/registry.py:20-73` | 明确配置 SSOT，消除 YAML/Python 双写。 |
| AG-11 | P1 | 源码与 wheel 边界不一致：IR 不在 package discovery；Contracts Schema 无明确 package-data/wheel smoke。 | `Dockerfile:17-23`; `pyproject.toml:53-60`; `.github/workflows/ci.yml:57-80` | 从仓库外临时目录验证 IR、Facade 和 Schema 资源。 |
| AG-12 | P0 | CI 缺少架构依赖 Guard 和运行时 Pydantic↔JSON Schema 一致性测试；fixture 自验证不能替代运行时合同。 | `.github/workflows/ci.yml:25-80`; `shared-contracts/validators/validate_fixtures.py` | Phase 1 加 forbidden-import 与 legacy DTO↔canonical 双向合同测试。 |
| AG-13 | P2 / Phase 7 | Planner 仍主要产生固定 echo，Evaluator 主要是二值结果，candidate Lesson 不等于审核闭环。 | `app/agent/planner.py`; `app/core/compiler.py`; `app/evaluation/evaluator.py`; `shared/bridge.py:23-51` | Phase 7 才实施动态规划和证据驱动评价；当前不得宣称完整认知闭环。 |
| AG-14 | P1 | Root 警告审计发现未关闭 SQLite 连接；mypy 正式配置被 NumPy stub/Python 3.10 语法阻断，3.13 诊断仍有项目错误。 | `tests/test_coverage_gap.py::TestLogging`; `TEST_BASELINE.md` | Phase 1/3 关闭连接泄漏；先修类型工具链可复现性，再逐域归零。 |
| AG-15 | P1 | 缺少本地容器、反向代理、TLS 与并发负载实测。 | 当前 Phase 0 执行证据 | Phase 9/10 完成部署与运行时验证；现阶段不得宣称通过。 |

## 迁移顺序

1. **P0-1：**锁定依赖规则、合同边界和禁止新增 `sys.path.insert`。
2. **P0-2：**建立 Research、Knowledge、Enhancement、Runtime、Contracts 五个 Facade，只委托现有实现。
3. **P0-3：**统一 composition root、认证接线和数据库初始化，不改变数据库结构。
4. **P1-1：**以 SafeWriter/Repository 收口散落写入；拆分 KB 巨型入口并包装 Sleep Loop。
5. **P1-2：**补 wheel、合同、权限、安全 HTTP 与路径 containment 门禁。
6. Phase 7 前不得把 echo Planner、二值 Evaluation、preview/candidate Lesson 宣称为完整闭环。
"""


def _reuse_decisions(git_head: str) -> str:
    return f"""# Phase 0 复用决策

> Git 基线：`{git_head}`。原则：Existing Assets First；先包装与验证，再切换。只评估当前仓库已吸收版本，不访问外部项目。

| 资产 | 决策 | 优先级 | 事实与 Phase 1 动作 |
|---|---|---:|---|
| `shared/config.py` + `shared/auth.py` | 适配后复用，作为 Gateway 基础 | P0 | 三个应用已有共享认证，但中间件接线重复；生产使用必须经过 `validate_runtime_config`，并补 RBAC。 |
| `shared-contracts/schemas/*.json` | 作为 canonical contract 候选，不宣称当前 SSOT | P0 | Fixture validator 只证明 fixture；运行时 `app/schemas.py`、`shared/schemas.py` 有字段漂移，先建 legacy adapter。 |
| KB ContextPack/TaskPack builders | 适配后复用 | P0 | 实现位于 `__init__.py`，`builder.py` 近似占位；输出不等于 Runtime DTO。 |
| `shared/storage.py` + `shared/migration.py` | 保留并包 Repository Facade，禁止复制第二套 | P0 | 与 Runtime、Sleep Loop DDL 并存；Phase 1 不移动表、不改 schema。 |
| `shared/safe_writer.py` | 直接复用为安全写原语 | P0 | 默认 dry-run、路径 containment、覆盖备份和审计报告已有测试；用于替代散落写入。 |
| `shared/processing_manifest.py` | 直接复用 | P0 | Append-only JSONL、latest-state、源/输出哈希和 resume 语义完整。 |
| 质量纯函数模块 | 直接复用，保留 candidate/human-review 语义 | P0 | `content_quality`、`accuracy_benchmark`、`evidence_verification`、`oer_crosswalk` 已聚合；不能把 caller evidence 当 server verified。 |
| `app/core/router.py` + `route_policy.yaml` | 直接保留，经 Runtime Facade 暴露 | P1 | 规则已抽 YAML；Permission 仍反向导入私有匹配函数，应提公共 policy API。 |
| `app/tools/registry.py` | 适配后复用，不复制注册表 | P1 | 工具与风险集中，但与 `tools.yaml` 漂移且直接导入 KB；拆 Catalog 与 handler adapters。 |
| IR IntakeCard/EngineeringContract generators | 复用纯生成逻辑 | P1 | 无存储副作用，但字段必须映射版本化 Contracts。 |
| LiteLLM adapter | 适配后复用 | P1 | 会传播 provider 错误而不伪造成功；只有 mock 证据，不得声称真实 provider E2E。 |
| Crawl4AI adapter | 适配后复用为 crawl 聚合 Facade | P1 | Adapter 委托 `app.ingestion.multi_format.convert_url()`，后者真实优先调用 Crawl4AI 再 fallback；需补直接合同测试并让名称反映聚合行为。 |
| MarkItDown adapter | **禁止作为多格式完成能力复用** | P0 | 当前只真实读取文本，二进制返回占位；真实多格式路径在 `app/ingestion/multi_format.py`，应包装现有实现。 |
| vector/security/memory/observability/graph adapters | 不复用，只是空壳命名空间 | P1 | `__init__.py` 仅有 placeholder docstring，不得作为 Facade 已完成证据。 |
| `shared/obsidian_projection.py` | 仅复用纯 render，禁止直接复用 writer | P0 | `write_projection()` 缺少 vault containment；必须接 SafeWriter 和 approved root。 |
| `local_trace_adapter.py` | 禁止服务层直接复用 | P0 | 接受任意 `output_dir` 并直接 mkdir/write，无 containment、备份或原子写；改为 Trace Repository。 |
| `app/memory/vector_db.py` | 只复用 sqlite-vec 技术路线 | P0 | 不复用 Python `hash()` ID/embedding；先建 VectorStore 接口、稳定哈希和 rebuild。 |
| `shared/sleep_loop_engine.py` | 复用行为和数据，通过 Facade 收口 | P1 | 不复制引擎；后续复用统一 Planner/Permission/Executor/Evidence 语义。 |
| `knowledge_base/api.py` | 复用端点行为，不作为新架构边界 | P1 | 兼容保留旧 URL，Facade 调领域 service/repository，不直接依赖整个 FastAPI app。 |
| 外部来源声明 | 只承认当前仓库已吸收代码 | P0 | 禁止再次扫描、验证或同步仓库外项目；任何外部路径只能由显式 adapter/config 提供。 |

## 禁止事项

- 不复制整棵业务目录、注册表、DDL 或 Sleep Loop 到新壳层。
- 不直接执行目标设计 SQL，不在 Phase 1 搭便车迁移数据库。
- 不把 placeholder、preview、dry-run、stub、mock provider 或 candidate 当作完成。
- 不把未实际调用 Crawl4AI/MarkItDown 的兼容层按品牌名宣称为真实集成。
- 不在运行时代码新增 `sys.path.insert`、仓库外绝对路径或无 containment 写入。
"""


def _phase1_taskpack(git_head: str) -> str:
    continuation = "\\"
    return f"""# Phase 1 TaskPack：Facade 与 Architecture Guard

> 输入基线：`{git_head}`。本 TaskPack 只建立可运行边界，不重写业务实现。

## 目标

建立 Research、Knowledge、Enhancement、Runtime、Contracts 五个公共 Facade；每个入口调用
当前真实实现，并以 Architecture Guard 阻止依赖方向继续恶化。

## Ownership

- 允许：新增 Facade、合同测试、架构守卫、最小 CI 接入和对应文档。
- 禁止：数据库迁移、依赖大升级、目录树搬迁、Planner/Evaluator 重写、外部仓库扫描。
- 数据边界：不得写入用户知识、活动数据库或仓库外路径。

## 垂直任务

### TP1.0 基线可信度与完整测试矩阵

1. 保持 NUL/Unicode-safe HEAD 清单、dotfile、报告自排除与 index 隔离回归测试。
2. 在任何测试导入前设置隔离数据目录，禁用 bytecode/pytest cache，保证活动数据库哈希不变。
3. 修复 `Inspiration-Research/tests` 的包导入并加入 CI；每套测试记录 cwd、Python 版本和收集数。
4. API 快照按 core、KB、IR 服务分组，区分 route 与 operation，禁止硬编码漂移数字。

### TP1.1 Runtime Facade tracer bullet

1. 先写失败合同测试：通过 Facade 完成 route → permission → execute → trace。
2. 最小包装现有 `app/core` 与 `app/agent`，不得复制实现。
3. 对比 Facade 与旧入口的标准对象结果。

### TP1.2 Knowledge 与 Research Facade

1. 先写失败测试覆盖一个真实查询和一个 candidate 摄入路径。
2. Knowledge Facade 调用 `knowledge_base` 稳定入口。
3. Research Facade 隔离连字符目录兼容逻辑，调用方不得新增 `sys.path.insert`。

### TP1.3 Enhancement 与 Contracts Facade

1. 用现有摘要/卡片/质量能力完成一个真实 artifact tracer bullet。
2. Contracts Facade 先导出现有对象；版本化对象定义留给 Phase 2。

### TP1.4 Architecture Guard

1. 为禁止依赖方向写失败测试。
2. 禁止新代码增加 `sys.path.insert`。
3. 禁止 Contracts/Platform 反向依赖业务模块。
4. 禁止运行时代码硬编码外部项目或个人资料路径。
5. 仅对白名单中的现有兼容点 grandfather，新增即失败。

### TP1.5 Security Guards

1. 为 write/import/execute/backup 路由建立端点级 RBAC，`readonly` 变更请求必须 403。
2. 建统一 `safe_http_fetch()`，拒绝私网/回环/链路本地和重定向逃逸，并限制响应大小。
3. 所有 API 可达文件路径必须经过 approved-root containment；输入根与输出根分权。
4. 为 SSRF、symlink/junction 逃逸和存储型 XSS 候选补失败优先回归测试。

### TP1.6 CI 与文档收口

1. 将 Architecture Guard 加入 CI。
2. 更新当前架构图和 Facade 所有权表。
3. 保留旧入口兼容期和回滚开关，不删除遗留 API。

## 每个垂直任务门禁

```bash
python -m pytest <targeted-test> -q --tb=short
python -m ruff check <changed-files> --no-cache
python -m pytest tests -q --tb=short
python -m pytest knowledge_base/tests -q --tb=short
python -m pytest Inspiration-Research/tests -q --tb=short
python -m pytest integration-tests -q --tb=short
python -m ruff check app shared knowledge_base Inspiration-Research {continuation}
  shared-contracts/adapters app/workflow integration-tests scripts --no-cache
git diff --check
git diff --cached --check
```

## 验收

- 五个 Facade 至少各有一个调用真实实现的合同测试。
- Architecture Guard 能用故意违规 fixture 证明会失败。
- 旧入口和 Facade 对同一输入的合同对象可比较。
- 无新增 `sys.path.insert`、外部绝对路径、秘密或运行时生成物。
- 每个任务独立提交并写明回滚方法；推送后核对 CI 与远端 SHA。

## 回滚

按 TP1.0–TP1.6 的独立提交逆序回滚。Facade 切换前保留旧入口，因此回滚不得要求数据库恢复。
"""


def write_phase0_reports(
    *,
    repo_root: Path,
    output_dir: Path,
    tracked_paths: Iterable[str],
    routes: list[dict[str, Any]],
    git_head: str,
    dependency_data: dict[str, Any],
    gate_results: dict[str, dict[str, Any]],
    security_findings: list[dict[str, str]],
    file_contents: dict[str, bytes] | None = None,
    secret_scan: dict[str, Any] | None = None,
) -> list[Path]:
    """Write the complete Phase 0 report set and return paths in contract order."""
    output_dir.mkdir(parents=True, exist_ok=True)
    inventory = build_file_inventory(
        repo_root,
        tracked_paths,
        file_contents=file_contents,
    )
    secret_scan = secret_scan or {"status": "not-run", "matches": "unknown"}

    _write_csv(output_dir / "FILE_INVENTORY.csv", inventory)
    (output_dir / "API_ROUTE_MAP.json").write_text(
        json.dumps(
            {
                "git_head": git_head,
                "route_count": len(routes),
                "operation_count": _operation_count(routes),
                "services": _service_summary(routes),
                "routes": routes,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    documents = {
        "ASSET_MAP.md": _asset_map(git_head, inventory, routes),
        "DEPENDENCY_REPORT.md": _dependency_report(git_head, dependency_data),
        "TEST_BASELINE.md": _test_baseline(git_head, gate_results),
        "SECURITY_BASELINE.md": _security_report(
            git_head, security_findings, secret_scan
        ),
        "ARCHITECTURE_GAPS.md": _architecture_gaps(git_head),
        "REUSE_DECISIONS.md": _reuse_decisions(git_head),
        "PHASE_1_TASKPACK.md": _phase1_taskpack(git_head),
    }
    for name, content in documents.items():
        (output_dir / name).write_text(content.rstrip() + "\n", encoding="utf-8")
    return [output_dir / name for name in REQUIRED_REPORTS]


def _extract_warnings(output: str) -> list[str]:
    warnings: set[str] = set()
    for line in output.splitlines():
        match = re.search(r"\b([A-Za-z]+Warning: .*)", line)
        if not match:
            continue
        message = re.sub(r" at 0x[0-9A-Fa-f]+(?=>)", "", match.group(1).strip())
        warnings.add(message)
    return sorted(warnings)


def _run(
    command: list[str],
    cwd: Path,
    *,
    report_command: str | None = None,
    working_directory: str = ".",
) -> dict[str, Any]:
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    output = "\n".join(part.strip() for part in (completed.stdout, completed.stderr) if part.strip())
    summary = output.splitlines()[-1] if output else f"exit code {completed.returncode}"
    warnings = _extract_warnings(output)
    error_lines = [line for line in output.splitlines() if " error:" in line]
    error_files = {
        match.group(1).replace("\\", "/")
        for line in error_lines
        if (match := re.match(r"^(.+?):\d+: error:", line))
    }
    return {
        "status": "passed" if completed.returncode == 0 else "failed",
        "exit_code": completed.returncode,
        "summary": summary,
        "command": report_command or subprocess.list2cmdline(command),
        "working_directory": working_directory,
        "warnings": warnings,
        "error_count": len(error_lines),
        "error_file_count": len(error_files),
    }


def _tracked_paths(
    repo_root: Path,
    *,
    excluded_prefixes: tuple[str, ...] = (),
) -> list[str]:
    result = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", "-z", "HEAD"],
        cwd=repo_root,
        capture_output=True,
        check=True,
    )
    paths = [item.decode("utf-8") for item in result.stdout.split(b"\0") if item]
    return [
        path
        for path in paths
        if not any(path.startswith(prefix) for prefix in excluded_prefixes)
    ]


def _read_head_blobs(repo_root: Path, tracked_paths: Iterable[str]) -> dict[str, bytes]:
    """Read file bytes from Git HEAD so dirty worktree content cannot contaminate the baseline."""
    blobs: dict[str, bytes] = {}
    for path in sorted({_normalise_path(item) for item in tracked_paths}):
        completed = subprocess.run(
            ["git", "show", f"HEAD:{path}"],
            cwd=repo_root,
            capture_output=True,
            check=True,
        )
        blobs[path] = completed.stdout
    return blobs


def _secret_scan(
    repo_root: Path,
    tracked_paths: Iterable[str],
    *,
    file_contents: dict[str, bytes] | None = None,
) -> dict[str, Any]:
    matches: list[dict[str, str]] = []
    for relative in tracked_paths:
        normalised = _normalise_path(relative)
        if file_contents is None:
            path = repo_root / normalised
            if not path.is_file():
                continue
            data = path.read_bytes()
        else:
            if normalised not in file_contents:
                continue
            data = file_contents[normalised]
        for name, pattern in _SECRET_PATTERNS.items():
            if pattern.search(data):
                matches.append({"rule": name, "path": normalised})
    return {
        "status": "passed" if not matches else "failed",
        "matches": len(matches),
        "details": matches,
    }


def _security_findings() -> list[dict[str, str]]:
    return [
        {
            "id": "SEC-01",
            "status": "implemented + tested",
            "evidence": "`shared/config.py`; `tests/test_hardening.py`",
            "finding": "生产环境对鉴权、强密钥和显式 CORS fail-fast。",
        },
        {
            "id": "SEC-02",
            "status": "implemented + tested",
            "evidence": "`shared/auth.py`; `tests/test_hardening.py`",
            "finding": "主网关和独立 KB 共享鉴权；发 token 需要管理员身份。",
        },
        {
            "id": "SEC-03",
            "status": "implemented + tested",
            "evidence": "`shared/backup.py`; `tests/test_backup.py`",
            "finding": "恢复只生成离线候选，不在线覆盖活动数据库。",
        },
        {
            "id": "SEC-04",
            "status": "partial",
            "evidence": "`app/ingestion/file.py`; `app/ingestion/multi_format.py`",
            "finding": "单文件摄入有仓库 containment；多格式目录需统一 approved roots。",
        },
        {
            "id": "SEC-05",
            "status": "gap",
            "evidence": "`app/ingestion/multi_format.py`; `knowledge_base/` collectors",
            "finding": "尚无统一 Safe HTTP Facade 覆盖 DNS、私网、redirect、大小和类型。",
        },
        {
            "id": "SEC-06",
            "status": "gap",
            "evidence": "`.github/workflows/ci.yml`",
            "finding": "CI 尚未接入高置信 secret scan、依赖审计和架构守卫。",
        },
    ]


def _collect_routes(repo_root: Path) -> list[dict[str, Any]]:
    if not os.environ.get("COGNITIVE_DATA_DIR", "").strip():
        raise RuntimeError("route collection requires an isolated COGNITIVE_DATA_DIR")
    from app.main import app

    main_routes = build_route_map(app)
    for route in main_routes:
        route["service"] = (
            "knowledge-base" if str(route["path"]).startswith("/kb") else "core"
        )

    module_name = "phase0_inspiration_research_api"
    api_path = repo_root / "Inspiration-Research" / "api.py"
    spec = importlib.util.spec_from_file_location(module_name, api_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load Inspiration-Research API from {api_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    ir_routes = build_route_map(module.app)
    for route in ir_routes:
        route["service"] = "inspiration-research"

    return sorted(
        [*main_routes, *ir_routes],
        key=lambda item: (
            str(item.get("service", "")),
            str(item["path"]),
            ",".join(item["methods"]),
        ),
    )


def _blocking_gate_failures(gates: dict[str, dict[str, Any]]) -> list[str]:
    return sorted(
        name
        for name, result in gates.items()
        if result.get("blocking", True) and result.get("status") != "passed"
    )


def _as_non_blocking_observation(result: dict[str, Any]) -> dict[str, Any]:
    result["blocking"] = False
    if result.get("exit_code") != 0:
        result["status"] = "observed-failure"
    return result


def _as_non_blocking_diagnostic(result: dict[str, Any]) -> dict[str, Any]:
    _as_non_blocking_observation(result)
    if result.get("exit_code") != 0:
        result["status"] = "observed-failure"
        error_count = int(result.get("error_count", 0))
        file_count = int(result.get("error_file_count", 0))
        error_label = "error" if error_count == 1 else "errors"
        file_label = "file" if file_count == 1 else "files"
        result["summary"] = (
            f"{error_count} {error_label} across {file_count} {file_label}; "
            f"exit code {result.get('exit_code')}"
        )
    return result


def _collect_gates(repo_root: Path, python: Path) -> dict[str, dict[str, Any]]:
    ruff_targets = [
        "app",
        "shared",
        "knowledge_base",
        "Inspiration-Research",
        "shared-contracts/adapters",
        "app/workflow",
        "integration-tests",
        "scripts",
    ]
    return {
        "root-tests": _run(
            [
                str(python),
                "-m",
                "pytest",
                "tests",
                "-q",
                "--tb=short",
                "-W",
                "default",
                "-p",
                "no:cacheprovider",
            ],
            repo_root,
            report_command=(
                "python -m pytest tests -q --tb=short -W default "
                "-p no:cacheprovider"
            ),
        ),
        "knowledge-base-tests": _run(
            [
                str(python),
                "-m",
                "pytest",
                "tests",
                "-q",
                "--tb=short",
                "-p",
                "no:cacheprovider",
            ],
            repo_root / "knowledge_base",
            report_command="python -m pytest tests -q --tb=short -p no:cacheprovider",
            working_directory="knowledge_base",
        ),
        "integration-tests": _run(
            [
                str(python),
                "-m",
                "pytest",
                "integration-tests",
                "-q",
                "--tb=short",
                "-p",
                "no:cacheprovider",
            ],
            repo_root,
            report_command=(
                "python -m pytest integration-tests -q --tb=short -p no:cacheprovider"
            ),
        ),
        "inspiration-research-tests": _as_non_blocking_observation(
            _run(
                [
                    str(python),
                    "-m",
                    "pytest",
                    "Inspiration-Research/tests",
                    "-q",
                    "--tb=short",
                    "-p",
                    "no:cacheprovider",
                ],
                repo_root,
                report_command=(
                    "python -m pytest Inspiration-Research/tests -q --tb=short "
                    "-p no:cacheprovider"
                ),
            )
        ),
        "ruff": _run(
            [str(python), "-m", "ruff", "check", *ruff_targets, "--no-cache"],
            repo_root,
            report_command=(
                "python -m ruff check app shared knowledge_base Inspiration-Research "
                "shared-contracts/adapters app/workflow integration-tests scripts --no-cache"
            ),
        ),
        "mypy-config-preflight": _as_non_blocking_diagnostic(
            _run(
                [
                    str(python),
                    "-m",
                    "mypy",
                    "app",
                    "shared",
                    "knowledge_base",
                    "--ignore-missing-imports",
                    "--no-error-summary",
                ],
                repo_root,
                report_command=(
                    "python -m mypy app shared knowledge_base "
                    "--ignore-missing-imports --no-error-summary"
                ),
            )
        ),
        "mypy-python-3.13-diagnostic": _as_non_blocking_diagnostic(
            _run(
                [
                    str(python),
                    "-m",
                    "mypy",
                    "app",
                    "shared",
                    "knowledge_base",
                    "--ignore-missing-imports",
                    "--python-version",
                    "3.13",
                    "--no-error-summary",
                ],
                repo_root,
                report_command=(
                    "python -m mypy app shared knowledge_base --ignore-missing-imports "
                    "--python-version 3.13 --no-error-summary"
                ),
            )
        ),
        "worktree-diff-check": _run(
            ["git", "diff", "--check"],
            repo_root,
            report_command="git diff --check",
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--python", type=Path, default=Path(sys.executable))
    args = parser.parse_args(argv)

    repo_root = args.repo_root.resolve()
    output_dir = repo_root / "migrations" / "reports" / "phase-0"
    tracked = _tracked_paths(
        repo_root,
        excluded_prefixes=("migrations/reports/phase-0/",),
    )
    head_blobs = _read_head_blobs(repo_root, tracked)
    git_head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    ).stdout.strip()
    dependency_data = load_dependency_data(repo_root / "pyproject.toml")
    with _temporary_runtime():
        gates = _collect_gates(repo_root, args.python.resolve())
        routes = _collect_routes(repo_root)
    scan = _secret_scan(repo_root, tracked, file_contents=head_blobs)
    written = write_phase0_reports(
        repo_root=repo_root,
        output_dir=output_dir,
        tracked_paths=tracked,
        routes=routes,
        git_head=git_head,
        dependency_data=dependency_data,
        gate_results=gates,
        security_findings=_security_findings(),
        file_contents=head_blobs,
        secret_scan=scan,
    )
    print(
        json.dumps(
            {
                "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
                "git_head": git_head,
                "reports": [str(path.relative_to(repo_root)).replace("\\", "/") for path in written],
                "gates": gates,
                "secret_scan": scan,
                "route_count": len(routes),
                "operation_count": _operation_count(routes),
                "inventory_count": len(head_blobs),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if not _blocking_gate_failures(gates) and scan["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
