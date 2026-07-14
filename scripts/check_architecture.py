"""AST-based architecture boundary guard for Cognitive-Loop-OS."""

from __future__ import annotations

import argparse
import ast
import json
import re
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

_SCAN_ROOTS = (
    "app",
    "shared",
    "knowledge_base",
    "inspiration_research",
    "Inspiration-Research",
    "shared-contracts",
    "platform",
    "scripts",
)
_BUSINESS_MODULES = {"app", "shared", "knowledge_base", "inspiration_research"}
_PATH_MUTATING_METHODS = {"append", "clear", "extend", "insert", "pop", "remove", "reverse", "sort"}
_ABSOLUTE_PATH = re.compile(
    r"(?i)(?<![A-Za-z0-9])(?:"
    r"[A-Z]:[\\/]"
    r"|\\\\[^\\/\s]+[\\/][^\\/\s]+"
    r"|(?<!:)//[^/\s]+/[^/\s]+"
    r"|/(?:Users|home|opt|var|tmp|etc|srv|root|data|workspace|usr)(?:[\\/]|$)"
    r"|/mnt/[A-Z](?:[\\/]|$)"
    r")"
)

# Historical compatibility is locked to path + line + normalized AST expression.
_GRANDFATHERED_SYS_PATH_CALLS = {
    ("shared/backlinks.py", 21, "sys.path.insert(0, str(_PROJECT_ROOT))"),
    ("shared/block_refs.py", 25, "sys.path.insert(0, str(_PROJECT_ROOT))"),
    ("shared/bulk_ops.py", 10, "sys.path.insert(0, str(_PROJECT_ROOT))"),
    ("shared/canvas.py", 22, "sys.path.insert(0, str(_PROJECT_ROOT))"),
    ("shared/collection_views.py", 22, "sys.path.insert(0, str(_PROJECT_ROOT))"),
    ("shared/cross_reference.py", 23, "sys.path.insert(0, str(_PROJECT_ROOT))"),
    ("shared/daily_notes.py", 20, "sys.path.insert(0, str(_PROJECT_ROOT))"),
    ("shared/dataview.py", 24, "sys.path.insert(0, str(_PROJECT_ROOT))"),
    ("shared/diversity_audit.py", 17, "sys.path.insert(0, str(_PROJECT_ROOT))"),
    ("shared/evidence_index.py", 16, "sys.path.insert(0, str(_PROJECT_ROOT))"),
    ("shared/feed_collector.py", 22, "sys.path.insert(0, str(_PROJECT_ROOT))"),
    ("shared/graph_rag.py", 19, "sys.path.insert(0, str(_PROJECT_ROOT))"),
    ("shared/knowledge_gardener.py", 20, "sys.path.insert(0, str(_PROJECT_ROOT))"),
    ("shared/learning_analytics.py", 17, "sys.path.insert(0, str(_PROJECT_ROOT))"),
    ("shared/media_extractor.py", 17, "sys.path.insert(0, str(_PROJECT_ROOT))"),
    ("shared/mermaid_gen.py", 15, "sys.path.insert(0, str(_PROJECT_ROOT))"),
    ("shared/object_types.py", 28, "sys.path.insert(0, str(_PROJECT_ROOT))"),
    ("shared/project_generator.py", 16, "sys.path.insert(0, str(_PROJECT_ROOT))"),
    ("shared/retro_summary.py", 18, "sys.path.insert(0, str(_PROJECT_ROOT))"),
    ("shared/source_discovery.py", 16, "sys.path.insert(0, str(_PROJECT_ROOT))"),
    ("shared/web_search.py", 21, "sys.path.insert(0, str(_PROJECT_ROOT))"),
    ("shared/youtube_extractor.py", 21, "sys.path.insert(0, str(_PROJECT_ROOT))"),

    (
        "scripts/check_repository_conventions.py",
        19,
        "sys.path.insert(0, str(_REPOSITORY_ROOT))",
    ),

    ("scripts/sleep_loop_worker.py", 18, "sys.path.insert(0, str(PROJECT_ROOT))"),
}
_GRANDFATHERED_REVERSE_IMPORTS = {
    (
        "shared-contracts/adapters/crawlers/crawl4ai_adapter.py",
        29,
        "app.ingestion.multi_format",
    ),
    (
        "shared-contracts/adapters/crawlers/crawl4ai_adapter.py",
        43,
        "shared.web_search",
    ),
}


@dataclass(frozen=True, order=True)
class ArchitectureIssue:
    code: str
    path: str
    line: int
    detail: str


def _sys_module_aliases(tree: ast.AST) -> set[str]:
    aliases = {"sys"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            aliases.update(
                alias.asname or alias.name
                for alias in node.names
                if alias.name == "sys"
            )
    return aliases


def _is_sys_path(node: ast.AST, aliases: set[str], sys_modules: set[str]) -> bool:
    return (
        isinstance(node, ast.Attribute)
        and node.attr == "path"
        and isinstance(node.value, ast.Name)
        and node.value.id in sys_modules
    ) or (isinstance(node, ast.Name) and node.id in aliases)


def _path_target(node: ast.AST, aliases: set[str], sys_modules: set[str]) -> bool:
    return _is_sys_path(node, aliases, sys_modules) or (
        isinstance(node, ast.Subscript)
        and _is_sys_path(node.value, aliases, sys_modules)
    )


def _path_aliases(tree: ast.AST, sys_modules: set[str]) -> set[str]:
    aliases: set[str] = set()
    changed = True
    while changed:
        changed = False
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "sys":
                for alias in node.names:
                    if alias.name == "path":
                        candidate = alias.asname or alias.name
                        if candidate not in aliases:
                            aliases.add(candidate)
                            changed = True
            elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                value = node.value
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                if value is not None and _is_sys_path(value, aliases, sys_modules):
                    for target in targets:
                        if isinstance(target, ast.Name) and target.id not in aliases:
                            aliases.add(target.id)
                            changed = True
    return aliases


def _sys_path_mutation(
    node: ast.AST, aliases: set[str], sys_modules: set[str]
) -> str | None:
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in _PATH_MUTATING_METHODS
        and _is_sys_path(node.func.value, aliases, sys_modules)
    ):
        return ast.unparse(node)
    if isinstance(node, ast.AnnAssign):
        if node.value is not None and _is_sys_path(node.value, aliases, sys_modules):
            return None
        if _path_target(node.target, aliases, sys_modules):
            return ast.unparse(node)
    if isinstance(node, ast.AugAssign) and _path_target(node.target, aliases, sys_modules):
        return ast.unparse(node)
    if isinstance(node, ast.Assign):
        if _is_sys_path(node.value, aliases, sys_modules) and all(
            isinstance(target, ast.Name) for target in node.targets
        ):
            return None
        if any(_path_target(target, aliases, sys_modules) for target in node.targets):
            return ast.unparse(node)
    if isinstance(node, ast.Delete) and any(
        _path_target(target, aliases, sys_modules) for target in node.targets
    ):
        return ast.unparse(node)
    return None


def _imported_modules(node: ast.Import | ast.ImportFrom, path: str) -> list[str]:
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]

    module = node.module or ""
    if node.level:
        package = path.removesuffix(".py").split("/")[:-1]
        ascend = node.level - 1
        base = package[: max(0, len(package) - ascend)]
        module = ".".join(base + ([module] if module else []))

    modules = [module] if module else []
    if module in {"app", "app.contracts"}:
        modules.extend(
            f"{module}.{alias.name}" for alias in node.names
        )
    return modules


def _importlib_aliases(tree: ast.AST) -> tuple[set[str], set[str]]:
    modules = {"importlib"}
    functions: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(
                alias.asname or alias.name
                for alias in node.names
                if alias.name == "importlib"
            )
        elif isinstance(node, ast.ImportFrom) and node.module == "importlib":
            functions.update(
                alias.asname or alias.name
                for alias in node.names
                if alias.name == "import_module"
            )
    return modules, functions


def _dynamic_import(
    node: ast.Call, importlib_modules: set[str], importlib_functions: set[str]
) -> str | None:
    is_builtin = isinstance(node.func, ast.Name) and node.func.id == "__import__"
    is_function = isinstance(node.func, ast.Name) and node.func.id in importlib_functions
    is_importlib = (
        isinstance(node.func, ast.Attribute)
        and node.func.attr == "import_module"
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id in importlib_modules
    )
    if not (is_builtin or is_function or is_importlib) or not node.args:
        return None
    first = node.args[0]
    return first.value if isinstance(first, ast.Constant) and isinstance(first.value, str) else None


def _non_runtime_string_nodes(tree: ast.AST) -> set[int]:
    result: set[int] = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
            and node.body
            and isinstance(node.body[0], ast.Expr)
        ):
            value = node.body[0].value
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                result.add(id(value))
        if isinstance(node, ast.Raise) and node.exc is not None:
            result.update(
                id(value)
                for value in ast.walk(node.exc)
                if isinstance(value, ast.Constant) and isinstance(value.value, str)
            )
        if isinstance(node, ast.Assert) and node.msg is not None:
            result.update(
                id(value)
                for value in ast.walk(node.msg)
                if isinstance(value, ast.Constant) and isinstance(value.value, str)
            )
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "re"
            and node.func.attr == "compile"
        ):
            result.update(
                id(value)
                for value in ast.walk(node)
                if isinstance(value, ast.Constant) and isinstance(value.value, str)
            )
    return result


def _is_contract_or_platform(path: str) -> bool:
    return path.startswith(("app/contracts/", "shared-contracts/", "platform/"))


def _is_lower_runtime_module(path: str) -> bool:
    return path.startswith(("app/core/", "app/agent/", "shared/", "knowledge_base/"))


def _python_files(root: Path):
    yield from sorted(root.glob("*.py"))
    for directory in _SCAN_ROOTS:
        base = root / directory
        if base.is_dir():
            yield from sorted(base.rglob("*.py"))


def _dependency_issue(
    path: str,
    line: int,
    modules: list[str],
    remaining_reverse_imports: Counter[tuple[str, int, str]],
) -> ArchitectureIssue | None:
    if _is_contract_or_platform(path):
        for source_module in modules:
            if path.startswith("app/contracts/") and (
                source_module == "app.contracts" or source_module.startswith("app.contracts.")
            ):
                continue
            if source_module.split(".", 1)[0] not in _BUSINESS_MODULES:
                continue
            key = (path, line, source_module)
            if remaining_reverse_imports[key] > 0:
                remaining_reverse_imports[key] -= 1
                continue
            return ArchitectureIssue(
                "reverse-business-dependency",
                path,
                line,
                f"boundary module imports business module {source_module!r}",
            )
    if _is_lower_runtime_module(path) and any(
        module == "app.main" or module.startswith("app.facades") for module in modules
    ):
        return ArchitectureIssue(
            "reverse-facade-dependency",
            path,
            line,
            f"lower runtime module imports public composition layer {modules[0]!r}",
        )
    return None


def scan_architecture(root: Path) -> list[ArchitectureIssue]:
    """Return architecture violations while preserving exact historical compatibility points."""
    root = root.resolve()
    issues: list[ArchitectureIssue] = []
    remaining_sys_path = Counter(_GRANDFATHERED_SYS_PATH_CALLS)
    remaining_reverse_imports = Counter(_GRANDFATHERED_REVERSE_IMPORTS)

    for file in _python_files(root):
        path = file.relative_to(root).as_posix()
        try:
            tree = ast.parse(file.read_text(encoding="utf-8-sig"), filename=path)
        except (OSError, SyntaxError, UnicodeError) as exc:
            issues.append(ArchitectureIssue("python-parse-error", path, 0, str(exc)))
            continue

        sys_modules = _sys_module_aliases(tree)
        aliases = _path_aliases(tree, sys_modules)
        importlib_modules, importlib_functions = _importlib_aliases(tree)
        non_runtime_strings = _non_runtime_string_nodes(tree)
        for node in ast.walk(tree):
            mutation = _sys_path_mutation(node, aliases, sys_modules)
            if mutation is not None:
                key = (path, node.lineno, mutation)
                if remaining_sys_path[key] > 0:
                    remaining_sys_path[key] -= 1
                else:
                    issues.append(
                        ArchitectureIssue(
                            "forbidden-sys-path-mutation",
                            path,
                            node.lineno,
                            f"new sys.path mutation: {mutation}",
                        )
                    )

            modules: list[str] = []
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                modules = _imported_modules(node, path)
            elif isinstance(node, ast.Call):
                imported = _dynamic_import(node, importlib_modules, importlib_functions)
                if imported:
                    modules = [imported]
            if modules:
                issue = _dependency_issue(
                    path, node.lineno, modules, remaining_reverse_imports
                )
                if issue:
                    issues.append(issue)

            if (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and id(node) not in non_runtime_strings
                and _ABSOLUTE_PATH.search(node.value)
            ):
                issues.append(
                    ArchitectureIssue(
                        "forbidden-absolute-path",
                        path,
                        node.lineno,
                        f"runtime string hardcodes an external absolute path: {node.value[:80]!r}",
                    )
                )

    return sorted(issues)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", type=Path, default=Path.cwd())
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)
    issues = scan_architecture(args.root)
    if args.format == "json":
        print(json.dumps([asdict(issue) for issue in issues], ensure_ascii=False, indent=2))
    elif issues:
        for issue in issues:
            print(f"{issue.path}:{issue.line}: {issue.code}: {issue.detail}")
        print(f"architecture guard failed: {len(issues)} issue(s)")
    else:
        print("architecture guard passed")
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
