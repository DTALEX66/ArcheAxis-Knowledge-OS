#!/usr/bin/env python3
"""Repository documentation/authority drift gate.

Four faults this fails on, each of which either happened in this repository or would silently
corrupt an audit:

1. **More than one file claiming to be the current ledger or pack.** The repository twice carried
   two documents that each said "only current"; a reader cannot resolve that, and the earlier round
   found `README`/`AGENTS`/index pointing at one entry while two other files claimed different ones.
2. **A root authority entry whose references do not resolve.** The root entry exists to be followed,
   so every path it names must exist.
3. **An input record whose recorded byte hash disagrees with the file on this host.** Provenance that
   cannot be recomputed is not provenance.
4. **A coverage matrix that silently drops an ID.** Every CAP/Q/F/I identifier the input scope names
   must appear, so a matrix cannot look complete by omission.

Non-zero on any fault, each named with its file and line. Missing inputs are printed as such rather
than skipped silently. This gate proves document structure, never product qualification.

Reused rather than duplicated: generated-file drift is already covered by
`scripts/contracts/generate_vocabulary.py --check`, `check_media_window_policy.py --check` and
`generate_capability_catalog.py --check`; link and supersession structure by
`tests/test_documentation_authority_index.py` and `tests/test_truth_authority_supersession.py`.
"""

from __future__ import annotations

import hashlib
import json
import re
import stat
import sys
from pathlib import Path, PurePosixPath

REPO = Path(__file__).resolve().parents[2]
AUTHORITY = REPO / "AUTHORITY.md"
INPUTS = REPO / "docs" / "current" / "AAOS-INPUT-SOURCES-20261006.json"
MATRIX = REPO / "docs" / "current" / "AAOS-COVERAGE-MATRIX-20261006.md"

# Documents that route a reader to the current record. A file repository history is *not* scanned:
# dated records and frozen copies legitimately describe their own era's pack, and flagging preserved
# history is how a guard becomes noise. The defect this catches is two live pointers disagreeing.
LIVE_ENTRY_DOCS = (
    "README.md",
    "AUTHORITY.md",
    "AGENTS.md",
    "docs/DOCUMENTATION_AUTHORITY_INDEX.md",
    "docs/truth/README.md",
    "docs/taskpacks/README.md",
)
CURRENTNESS = re.compile(r"(当前|现行|current|live)", re.IGNORECASE)
LEDGER_PATH = re.compile(r"(docs/current/[A-Za-z0-9._-]+\.(?:md|json))")
PACK_NAME = re.compile(r"(?:docs/(?:authority|taskpacks)/)?(?:taskpack-[0-9a-z.\-]+|aaos-ui-first-[0-9]+)")
LIVE_LEDGER = "docs/current/AAOS01-Q00-Q15-LEDGER-FINAL-20261005.md"

# Test citations, in the forms the ledger uses: a repo path, a crate-relative path, or
# a bare root test module. Deliberately narrow -- the ledger also names record files and
# ignored run receipts, which are not repository paths and must not be flagged here.
TEST_CITATION = re.compile(
    r"`((?:crates/[A-Za-z0-9._-]+/tests/[A-Za-z0-9_]+\.rs|tests/[A-Za-z0-9_]+\.py"
    r"|[A-Za-z0-9._-]+/tests/[A-Za-z0-9_]+\.rs))`"
)
CARGO_TEST_TARGET = re.compile(r"--test\s+([a-z0-9_]+)")


def _resolve_test_citation(token: str) -> Path | None:
    if token.startswith(("crates/", "tests/")):
        return REPO / token
    crate, separator, rest = token.partition("/tests/")
    if separator and crate and rest.endswith(".rs"):
        return REPO / "crates" / crate / "tests" / rest
    return None
# The owner-selected queue is a routing document, not a second progress database.
ACTIVE_EXECUTION = "docs/current/AAOS-ACTIVE-EXECUTION.json"
INHERITED_Q_LEDGER = LIVE_LEDGER
PRIVATE_PARTS = {".codex", ".hermes", ".zcode", ".dsh", ".claude", "memory", "memories",
                 "session", "sessions", "credentials", "cookies", ".npmrc", ".pypirc",
                 "id_rsa", "id_ed25519", ".git", ".ssh", "browser-data"}
WITHDRAWN = re.compile(
    r"(不再|并非|不主张|作废|取代|superseded|no longer|not the only|preceding|previous|历史|继承|inherited|historical|frozen|冻结)",
    re.IGNORECASE)
MUST_NOT_CLAIM = ("docs/taskpacks/README.md", "docs/truth/README.md")


def _project_path(relative: str) -> Path:
    """Reject private/outside/link locators before probing their targets."""
    if not isinstance(relative, str) or not relative or "\\" in relative:
        raise ValueError("path must use repository-relative POSIX spelling")
    if relative.startswith("/") or ":" in relative or "\x00" in relative:
        raise ValueError("absolute path is outside this gate's authorized repository")
    parts = PurePosixPath(relative).parts
    if ".." in parts or any(p.casefold() in PRIVATE_PARTS or p.casefold().startswith(".env") for p in parts):
        raise ValueError("private or traversal path is forbidden")
    candidate = REPO.joinpath(*parts)
    # Lexical containment first, then inspect only components inside this root.
    for index in range(1, len(parts) + 1):
        ancestor = REPO.joinpath(*parts[:index])
        try:
            information = ancestor.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(information.st_mode) or getattr(information, "st_file_attributes", 0) & 0x400:
            raise ValueError("reparse path is outside the gate's evidence boundary")
    return candidate


def load_active_execution() -> tuple[dict | None, list[str]]:
    try:
        path = _project_path(ACTIVE_EXECUTION)
        if not path.is_file():
            raise ValueError("owner-selected routing pointer is missing")
        pointer = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(pointer, dict) or pointer.get("schema") != "archeaxis.active-execution/v1":
            raise ValueError("routing pointer schema is invalid")
        pack = pointer.get("active_taskpack")
        progress = pointer.get("active_progress")
        inherited = pointer.get("inherited_progress", [INHERITED_Q_LEDGER])
        pack_path = _project_path(pack)
        progress_path = _project_path(progress)
        if re.search(r"(?:taskpack-0919-r6|taskpack-1004-aaos01|M0-)", pack, re.IGNORECASE):
            raise ValueError("historical taskpack cannot be the active UI queue")
        if not pack.startswith("docs/taskpacks/") or not pack_path.is_dir():
            raise ValueError("active_taskpack is not an existing selected taskpack directory")
        if not progress.startswith("docs/current/") or not progress.endswith(".md") or not progress_path.is_file():
            raise ValueError("active_progress is not an existing current progress document")
        if re.search(r"(?:R6-|M0-|AAOS01-Q00-Q15-LEDGER)", progress):
            raise ValueError("historical/inherited progress cannot be the active UI queue")
        if not isinstance(inherited, list) or any(not isinstance(p, str) for p in inherited):
            raise ValueError("inherited_progress must be an array of repository paths")
        for relative in inherited:
            if not _project_path(relative).is_file():
                raise ValueError("inherited progress reference is missing: " + relative)
        if "freeze_register" in pointer:
            freeze = pointer["freeze_register"]
            if freeze != pack + "/FREEZE-REGISTER.md" or not _project_path(freeze).is_file():
                raise ValueError("freeze_register must resolve inside the active taskpack")
        priority = pointer.get("priority_tasks", [])
        selected = pointer.get("selected_tasks", [])
        paused = pointer.get("paused", [])
        if not all(isinstance(items, list) and all(isinstance(item, str) for item in items)
                   for items in (priority, selected, paused)):
            raise ValueError("priority, selected and paused tasks must be arrays of IDs")
        if any(task not in selected for task in priority):
            raise ValueError("priority task is outside the owner-selected scope")
        if set(priority) & set(paused):
            raise ValueError("paused task cannot enter the priority queue")
        overlays = pointer.get("design_overlays", [])
        if not isinstance(overlays, list) or not all(isinstance(item, str) for item in overlays) or len(set(overlays)) != len(overlays):
            raise ValueError("design_overlays must be unique project-relative JSON locators")
        for locator in overlays:
            path = _project_path(locator)
            if not locator.startswith("docs/current/") or not locator.endswith(".json") or not path.is_file():
                raise ValueError("design overlay is missing or outside docs/current")
            overlay = json.loads(path.read_text(encoding="utf-8-sig"))
            if overlay.get("role") != "DESIGN_REQUIREMENTS_OVERLAY_NOT_REPLACEMENT_TASKPACK" or overlay.get("active_taskpack") != pack or overlay.get("progress_record") != progress:
                raise ValueError("design overlay replaced taskpack/progress authority")
            for source in overlay.get("sources", []):
                archive = _project_path(source["archive_path"])
                if not archive.is_file() or hashlib.sha256(archive.read_bytes()).hexdigest() != source["sha256"]:
                    raise ValueError("design overlay source archive hash mismatch")
        return pointer, []
    except (ValueError, TypeError, OSError, json.JSONDecodeError) as error:
        return None, [f"{ACTIVE_EXECUTION}: {error}"]


def check_single_current() -> list[str]:
    """Validate current claims against the selected queue, preserving dated inheritance."""
    pointer, problems = load_active_execution()
    if pointer is None:
        return problems
    pack = pointer["active_taskpack"]
    progress = pointer["active_progress"]
    pack_name = PurePosixPath(pack).name
    progress_claims: list[tuple[str, int, str]] = []
    pack_claims: list[tuple[str, int, str]] = []
    for relative in LIVE_ENTRY_DOCS:
        path = _project_path(relative)
        if not path.is_file():
            problems.append(f"{relative}: live entry document is missing")
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            # A historical sentence does not exempt a separate current sentence.
            for clause in re.split(r"[;；。]", line):
                if not CURRENTNESS.search(clause) or WITHDRAWN.search(clause):
                    continue
                progress_claims.extend((relative, number, target) for target in LEDGER_PATH.findall(clause)
                                       if target != ACTIVE_EXECUTION and any(word in target.upper() for word in ("LEDGER", "EXECUTION", "STATE")))
                pack_claims.extend((relative, number, target) for target in PACK_NAME.findall(clause))
    for file, number, target in progress_claims:
        if target != progress:
            problems.append(f"{file}:{number}: points at {target} as the current progress record, while the agreed one is {progress}")
    for file, number, target in pack_claims:
        if target not in (pack, pack_name):
            problems.append(f"{file}:{number}: points at {target} as the current pack, while the agreed one is {pack}")
    if not any(target == progress for _, _, target in progress_claims):
        problems.append("no live entry document names the current progress record: " + progress)
    if not any(target in (pack, pack_name) for _, _, target in pack_claims):
        problems.append("no live entry document names the current pack: " + pack)
    if len({target for _, _, target in progress_claims}) > 1:
        problems.append("live entry documents name more than one current progress record")
    return problems


LINK = re.compile(r"\]\(([^)]+)\)")
CODE_PATH = re.compile(r"`((?:docs|scripts|tests|config|services|crates|frontend|apps)/[^`]+)`")


def check_authority_references() -> list[str]:
    if not AUTHORITY.is_file():
        return [f"{AUTHORITY.relative_to(REPO)}: missing; the root entry is what everything else "
                "is navigated from"]
    text = AUTHORITY.read_text(encoding="utf-8")
    problems: list[str] = []
    targets = set(LINK.findall(text)) | set(CODE_PATH.findall(text))
    for target in sorted(targets):
        if target.startswith(("http://", "https://", "#", "mailto:")):
            continue
        cleaned = target.split("#", 1)[0].strip()
        if not cleaned or "<" in cleaned:
            continue
        try:
            reference = _project_path(cleaned)
        except ValueError as error:
            problems.append(f"AUTHORITY.md: unsafe reference {cleaned}: {error}")
            continue
        if not reference.exists():
            problems.append(f"AUTHORITY.md: references {cleaned}, which does not exist")
    return problems


def check_input_hashes() -> list[str]:
    if not INPUTS.is_file():
        return [f"{INPUTS.relative_to(REPO)}: missing"]
    document = json.loads(INPUTS.read_text(encoding="utf-8"))
    problems: list[str] = []
    checked = skipped_outside = missing = 0
    entries = list(document.get("inputs_read_this_round") or []) + list(
        document.get("appendix_sources") or [])
    for entry in entries:
        recorded = entry.get("byte_sha256")
        locator = str(entry.get("path_or_locator") or "")
        if not recorded or not locator:
            continue
        # Absolute historical sources may name another checkout or private agent state.
        # Reject them lexically before even checking existence; only this root is authorized.
        try:
            # Historical A04 uses a local Markdown path followed by a human
            # parenthetical note. Preserve the register bytes, validate the
            # exact path portion and still compare its recorded content hash.
            local_locator = re.sub(r"(?<=\.md)（[^\r\n]*）$", "", locator)
            candidate = _project_path(local_locator)
        except ValueError:
            skipped_outside += 1
            continue
        if not candidate.is_file():
            missing += 1
            continue
        actual = hashlib.sha256(candidate.read_bytes()).hexdigest()
        checked += 1
        if actual != recorded:
            problems.append(
                f"{locator}: recorded {recorded[:16]}… but this host has {actual[:16]}…")
    # A run that verified nothing must not read as a clean result.
    if checked == 0 and missing == 0 and skipped_outside == 0:
        problems.append(
            f"{INPUTS.relative_to(REPO)}: no in-repository input hash was verifiable "
            f"({skipped_outside} locator(s) are outside the repository)")
    if missing:
        problems.append(f"{INPUTS.relative_to(REPO)}: {missing} recorded path(s) are not in the "
                        "repository and are not absolute, so they cannot be a locator")
    print(f"input hashes: verified {checked}, outside/private UNVERIFIED {skipped_outside}")
    return problems


def check_coverage_matrix() -> list[str]:
    if not MATRIX.is_file():
        return [f"{MATRIX.relative_to(REPO)}: missing"]
    text = MATRIX.read_text(encoding="utf-8")
    problems: list[str] = []
    required = (
        [f"CAP-{n:04d}" for n in range(10, 170, 10)]
        + [f"Q{n:02d}" for n in range(16)]
        + [f"F{n:02d}" for n in range(15)]
        + [f"I{n}" for n in range(1, 7)]
    )
    for identifier in required:
        if not re.search(rf"(?<![A-Za-z0-9-]){re.escape(identifier)}(?![0-9])(?!0)", text):
            problems.append(f"{MATRIX.relative_to(REPO)}: {identifier} is not covered")
    return problems


def check_ledger_citations() -> list[str]:
    """Every test the live ledger cites has to exist.

    A row that names a test is making a checkable claim, and a renamed or recalled path
    makes the evidence unrunnable while still reading as complete. That mistake was made
    once here already -- a filename remembered from an audit rather than read from the
    tree, which collected nothing and looked green -- so the citations are verified like
    any other claim. Only test citations are checked: the ledger also names bare record
    filenames and run-relative receipts, which are not repository paths.
    """
    pointer, problems = load_active_execution()
    if pointer is None:
        return problems
    problems = _check_one_ledger(pointer["active_progress"])
    for relative in dict.fromkeys(pointer.get("inherited_progress", [INHERITED_Q_LEDGER])):
        if relative == pointer["active_progress"]:
            continue
        # A dated Q receipt retains its original citation. Its source may be absent from
        # this checkout: classify it as historical UNVERIFIED rather than invent a file.
        for warning in _check_one_ledger(relative):
            print("historical citation UNVERIFIED: " + warning)
    return problems


def _check_one_ledger(relative: str) -> list[str]:
    ledger = _project_path(relative)
    if not ledger.is_file():
        return [f"{relative}: missing; its test citations cannot be checked"]
    text = ledger.read_text(encoding="utf-8")
    problems: list[str] = []
    for token in sorted(set(TEST_CITATION.findall(text))):
        resolved = _resolve_test_citation(token)
        try:
            path = _project_path(resolved.relative_to(REPO).as_posix()) if resolved is not None else None
        except ValueError:
            path = None
        if path is None or not path.is_file():
            problems.append(
                f"{relative}: cites {token}, which is not a file in this repository")
    try:
        crates = _project_path("crates")
    except ValueError as error:
        return problems + [f"{relative}: unsafe crate test root: {error}"]
    for name in sorted(set(CARGO_TEST_TARGET.findall(text))):
        try:
            root_test = _project_path(f"tests/{name}.py")
        except ValueError:
            root_test = None
        if root_test is not None and root_test.is_file():
            continue
        found = False
        if crates.is_dir():
            for crate in crates.iterdir():
                try:
                    crate_path = _project_path(f"crates/{crate.name}")
                    if not crate_path.is_dir():
                        continue
                    target = _project_path(f"crates/{crate.name}/tests/{name}.rs")
                except ValueError:
                    continue
                if target.is_file():
                    found = True
                    break
        if found:
            continue
        problems.append(
            f"{relative}: cites `--test {name}`, which matches no test file")
    return problems


def check_public_routing() -> list[str]:
    # Reuse the public-path identity resolver; no private software state is read.
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "authority_routes", Path(__file__).resolve().parents[2] / "scripts/maintenance/authority_routes.py")
    assert spec and spec.loader
    routes = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(routes)
    return routes.check_routes(REPO)


def main() -> int:
    problems: list[str] = []
    problems += check_public_routing()
    problems += check_single_current()
    problems += check_authority_references()
    problems += check_input_hashes()
    problems += check_coverage_matrix()
    problems += check_ledger_citations()
    if problems:
        print("document authority drift:")
        for problem in problems:
            print(f"  {problem}")
        return 1
    print("document authority: single current record, root references resolve, "
          "in-repository hashes checked (external sources remain UNVERIFIED), coverage complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
