"""Resolve public document identity and fail on live authority routing drift.

Does not inspect private/global software state or turn source material into grants.
The document-authority CI entry invokes check_routes; --resolve is for readers.
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import io
import json
import re
import stat
import zipfile
from pathlib import Path, PurePosixPath
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = "docs/current/AAOS-AUTHORITY-ROUTES.json"
CONSOLIDATION = "docs/history/repository-consolidation-20261019/MANIFEST.json"
PUBLIC_RECORDS = "docs/history/2026-11-01-preoct-archive/MANIFEST.json"
PRIVATE = {".git", ".codex", ".claude", ".hermes", ".ssh", "memory", "memories",
           "session", "sessions", "credentials", "cookies", "browser-data",
           ".project-local", ".hilo", ".dsh", ".zcode", ".npmrc", ".pypirc",
           "id_rsa", "id_ed25519"}
LINK = re.compile(r"\]\(([^)]+)\)")


def public_path(root: Path, name: str) -> Path:
    if not isinstance(name, str) or not name or "\\" in name or ":" in name or name.startswith("/"):
        raise ValueError("outside or non-repository path")
    parts = PurePosixPath(name).parts
    if ".." in parts or any(p.casefold() in PRIVATE or p.casefold().startswith(".env") for p in parts):
        raise ValueError("private or traversal path")
    for i in range(1, len(parts) + 1):
        candidate = root.joinpath(*parts[:i])
        try:
            info = candidate.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise ValueError("reparse path")
    return root.joinpath(*parts)


class PreservedRecords:
    """Read byte-identical public records after their textual trees are retired.

    The tracked ZIP is available in a fresh checkout. Neither a missing local
    archive nor an index entry alone is accepted as preservation evidence.
    Each instance verifies immutable ZIP bytes once, without extracting paths.
    """

    def __init__(self, root: Path):
        self.root = root
        self.rows: dict[str, dict] = {}
        self.payloads: dict[str, bytes] = {}
        self.archive_path: str | None = None
        descriptor = public_path(root, PUBLIC_RECORDS)
        if not descriptor.is_file():
            return
        data = json.loads(descriptor.read_text(encoding="utf-8"))
        if data["schema"] != "aaos.preoct-public-records/v1":
            raise ValueError("invalid public record archive schema")
        archive = data["archive"]
        location = archive["path"]
        if location != str(PurePosixPath(PUBLIC_RECORDS).parent / "preoct-public-records.zip"):
            raise ValueError("public record archive outside its registered owner")
        raw = public_path(root, location).read_bytes()
        self._identity(raw, archive, "public record ZIP")
        self.archive_path = location
        for row in data["files"]:
            name = row["path"]
            public_path(root, name)
            if not name.startswith("docs/history/") or name.startswith(str(PurePosixPath(PUBLIC_RECORDS).parent) + "/"):
                raise ValueError("invalid public record source")
            if name in self.rows:
                raise ValueError("duplicate preserved record")
            self.rows[name] = row
        with zipfile.ZipFile(io.BytesIO(raw)) as source:
            members = source.infolist()
            names = [member.filename for member in members]
            if len(names) != len(set(names)) or set(names) != set(self.rows):
                raise ValueError("public record ZIP membership mismatch")
            for member in members:
                mode = member.external_attr >> 16
                if member.is_dir() or stat.S_IFMT(mode) not in (0, stat.S_IFREG) or member.flag_bits & 1:
                    raise ValueError("linked, encrypted or non-file public record")
                row = self.rows[member.filename]
                size = row["bytes"]
                if type(size) is not int or size < 0 or member.file_size != size:
                    raise ValueError("public record member size mismatch")
                with source.open(member) as stream:
                    payload = stream.read(size + 1)
                self._identity(payload, row, "public record member")
                self.payloads[member.filename] = payload

    @staticmethod
    def _identity(raw: bytes, record: dict, label: str) -> None:
        size, digest = record["bytes"], record["sha256"]
        if (type(size) is not int or size < 0 or not isinstance(digest, str)
                or not re.fullmatch(r"[0-9a-f]{64}", digest)
                or len(raw) != size or hashlib.sha256(raw).hexdigest() != digest):
            raise ValueError(label + " identity mismatch")

    def read(self, name: str) -> bytes:
        path = public_path(self.root, name)
        if path.is_file():
            return path.read_bytes()
        if name in self.payloads:
            return self.payloads[name]
        raise FileNotFoundError("missing preserved public record: " + name)

    def location(self, name: str) -> dict:
        if name not in self.rows:
            return {}
        return {"canonical_path": PUBLIC_RECORDS, "archive_path": self.archive_path,
                "archive_member": name, "sha256": self.rows[name]["sha256"]}


def resolve(name: str, data: dict, root: Path = ROOT) -> dict:
    public_path(root, name)
    records = PreservedRecords(root)
    if name in records.rows:
        return {"path": name, "role": "ARCHIVED_PUBLIC_RECORD", **records.location(name)}
    manifest = public_path(root, CONSOLIDATION)
    if manifest.is_file():
        consolidation = json.loads(manifest.read_text(encoding="utf-8"))
        for item in consolidation["files"]:
            if name == item["original_path"]:
                public_path(root, item["archive_path"])
                public_path(root, item["replacement"])
                result = {"path": name, "role": "RETIRED_LOCATOR",
                        "canonical_path": item["archive_path"],
                        "replacement": item["replacement"]}
                result.update(records.location(item["archive_path"]))
                return result
    for alias in data["aliases"]:
        if name == alias["old_path"]:
            result = {"path": name, "role": "RETIRED_LOCATOR", "canonical_path": alias["canonical_path"]}
            result.update(records.location(alias["canonical_path"]))
            return result
    for entry in data["entries"]:
        if name == entry["path"]:
            return entry.copy()
    for rule in data["rules"]:
        if fnmatch.fnmatchcase(name, rule["pattern"]):
            return {"path": name, "role": rule["role"]}
    return {"path": name, "role": "UNCLASSIFIED_REFERENCE"}


def check_consolidation(root: Path = ROOT) -> list[str]:
    """Check one byte-preserving archive and live links; never inspect private trees."""
    problems: list[str] = []
    try:
        records = PreservedRecords(root)
        manifest = json.loads(public_path(root, CONSOLIDATION).read_text(encoding="utf-8"))
        if manifest["schema"] != "archeaxis.repository-consolidation/v1":
            raise ValueError("invalid schema")
        if not re.fullmatch(r"[0-9a-f]{40}", manifest["source_commit"]):
            raise ValueError("invalid source_commit")
        originals: set[str] = set()
        archives: set[str] = set()
        for item in manifest["files"]:
            old, archived = item["original_path"], item["archive_path"]
            old_path = public_path(root, old)
            public_path(root, archived)
            replacement = public_path(root, item["replacement"])
            if old in originals or archived in archives:
                problems.append("duplicate consolidation identity: " + old)
            originals.add(old)
            archives.add(archived)
            if not archived.startswith(str(PurePosixPath(CONSOLIDATION).parent) + "/"):
                problems.append("archive outside consolidation root: " + archived)
            if not re.fullmatch(r"[0-9a-f]{40}", item["baseline_commit"]):
                problems.append("invalid baseline_commit: " + old)
            if not isinstance(item["role"], str) or not item["role"]:
                problems.append("missing archive role: " + old)
            if old_path.exists():
                problems.append("retired original still exists: " + old)
            if not replacement.is_file():
                problems.append("missing consolidation replacement: " + item["replacement"])
            size, digest = item["bytes"], item["sha256"]
            if (type(size) is not int or size < 0 or not isinstance(digest, str)
                    or not re.fullmatch(r"[0-9a-f]{64}", digest)):
                problems.append("invalid archive identity metadata: " + old)
                continue
            try:
                raw = records.read(archived)
            except FileNotFoundError:
                problems.append("missing consolidated archive: " + archived)
                continue
            if len(raw) != size or hashlib.sha256(raw).hexdigest() != digest:
                problems.append("consolidated archive identity mismatch: " + archived)
        for item in manifest.get("navigation_snapshots", []):
            public_path(root, item["archive_path"])
            current = public_path(root, item["original_path"])
            if not current.is_file():
                problems.append("missing navigation snapshot or current entry: " + item["original_path"])
                continue
            try:
                raw = records.read(item["archive_path"])
            except FileNotFoundError:
                problems.append("missing navigation snapshot or current entry: " + item["original_path"])
                continue
            if len(raw) != item["bytes"] or hashlib.sha256(raw).hexdigest() != item["sha256"]:
                problems.append("navigation snapshot identity mismatch: " + item["archive_path"])
        # Inspect public residual paths only. Never follow symlinks/junctions or
        # enter private state left behind by a public-source archival operation.
        for directory in manifest["whole_directories"]:
            pending = [public_path(root, directory)]
            while pending:
                current = pending.pop()
                if not current.exists():
                    continue
                if not current.is_dir():
                    problems.append("retired directory has public residual: "
                                    + current.relative_to(root).as_posix())
                    continue
                for child in current.iterdir():
                    name = child.relative_to(root).as_posix()
                    try:
                        safe = public_path(root, name)
                    except ValueError:
                        # No read or traversal of a private/reparse child.
                        if child.name.casefold() not in PRIVATE and not child.name.casefold().startswith(".env"):
                            problems.append("uninspectable retired directory child: " + name)
                        continue
                    if safe.is_dir():
                        pending.append(safe)
                    else:
                        problems.append("retired directory has public residual: " + name)
        routes = json.loads(public_path(root, REGISTRY).read_text(encoding="utf-8"))
        for entry in routes["entries"]:
            if entry["role"] != "LIVE_NAVIGATION" or not entry["path"].endswith(".md"):
                continue
            name = entry["path"]
            page = public_path(root, name)
            if not page.is_file():
                continue  # check_routes owns missing live entries.
            for token in LINK.findall(page.read_text(encoding="utf-8-sig")):
                target = unquote(token.strip("<> ").split("#", 1)[0])
                if not target or ":" in target or target.startswith("/") or "<" in target:
                    continue
                parts: list[str] = []
                for part in (PurePosixPath(name).parent / target).parts:
                    if part == "..":
                        if not parts:
                            raise ValueError("live link escapes repository")
                        parts.pop()
                    elif part != ".":
                        parts.append(part)
                normalized = "/".join(parts)
                public_path(root, normalized)
                if normalized in originals:
                    problems.append(f"{name}: live link targets retired original: {target}")
    except (ValueError, OSError, KeyError, TypeError, zipfile.BadZipFile) as error:
        problems.append(f"{CONSOLIDATION}: {error}")
    return problems


def check_routes(root: Path = ROOT) -> list[str]:
    problems: list[str] = []
    try:
        records = PreservedRecords(root)
        data = json.loads(public_path(root, REGISTRY).read_text(encoding="utf-8"))
        if data["schema"] != "archeaxis.authority-routes/v1":
            raise ValueError("invalid schema")
        paths = [entry["path"] for entry in data["entries"]]
        if len(paths) != len(set(paths)):
            raise ValueError("duplicate exact routes")
        for required in ("README.md", "AUTHORITY.md", "AGENTS.md", data["active_pointer"]):
            if required not in paths:
                problems.append("required public entry not classified: " + required)
        for entry in data["entries"]:
            path = public_path(root, entry["path"])
            if not path.is_file() and entry["path"] not in records.payloads:
                problems.append("missing exact route: " + entry["path"])
        for alias in data["aliases"]:
            public_path(root, alias["old_path"])
            if (not public_path(root, alias["canonical_path"]).is_file()
                    and alias["canonical_path"] not in records.payloads):
                problems.append("missing alias destination: " + alias["canonical_path"])
        pointer = json.loads(public_path(root, data["active_pointer"]).read_text(encoding="utf-8"))
        if pointer.get("authority_routes") != REGISTRY:
            problems.append("active pointer does not route through this registry")
        control = pointer.get("execution_control", {})
        if control.get("state") == "PAUSED_BY_OWNER":
            if control.get("automatic_continuation") is not False:
                problems.append("product automatic continuation is not disabled while paused")
        elif control.get("state") == "RUNNING_BY_OWNER":
            revision = control.get("owner_resume_record")
            if not isinstance(revision, str) or not revision.startswith("docs/current/"):
                problems.append("product resume lacks a new Owner-selected routing revision")
            else:
                decision = json.loads(public_path(root, revision).read_text(encoding="utf-8"))
                if (
                    decision.get("schema") != "archeaxis.owner-execution-resume/v1"
                    or decision.get("resumes_product_execution") is not True
                    or not decision.get("owner_instruction")
                    or decision.get("active_taskpack") != pointer.get("active_taskpack")
                    or decision.get("active_progress") != pointer.get("active_progress")
                ):
                    problems.append("product resume revision does not match the selected scope")
        else:
            problems.append("product pause changed without a new Owner-selected routing revision")
        for frozen in pointer.get("frozen_source_inputs", []):
            if frozen.get("state") != "FROZEN_BY_OWNER" or frozen.get("execution") != "NOT_EXECUTED":
                problems.append("frozen input promoted to execution")
            for field in ("index", "manifest"):
                name = frozen[field]
                if not public_path(root, name).is_file() or resolve(name, data, root)["role"] != "FROZEN_SOURCE_INPUT":
                    problems.append("frozen input routing missing: " + name)
        # Actual historical failures: a dated current/handoff path must not become an active router.
        for name in ("HERMES_HANDOFF.md", "docs/current/AAOS01-AGENT-HANDOFF-20261006.txt",
                     "docs/current/AAOS-CLOUD-AUDIT-HANDOFF-20260926.md"):
            if resolve(name, data, root)["role"] in {"ACTIVE_ROUTER", "LIVE_NAVIGATION", "SCOPED_PROGRESS"}:
                problems.append("historical path promoted to live authority: " + name)
        for entry in data["entries"]:
            if entry["role"] != "LIVE_NAVIGATION":
                continue
            name = entry["path"]
            path = public_path(root, name)
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8-sig")
            if "AAOS-AUTHORITY-ROUTES.json" not in text and name not in {"frontend/README.md", "src-tauri/README.md", "crates/README.md"}:
                problems.append("live entry lacks document identity route: " + name)
            for token in LINK.findall(text):
                target = unquote(token.strip("<> ").split("#", 1)[0])
                if not target or target.startswith(("https://", "http://", "mailto:", "app://")):
                    continue
                # Existing machine locators are not probed or treated as cloud paths.
                if ":" in target or target.startswith("/") or "<" in target:
                    continue
                joined = PurePosixPath(name).parent / target
                parts: list[str] = []
                for part in joined.parts:
                    if part == "..":
                        if not parts:
                            raise ValueError("live link escapes repository")
                        parts.pop()
                    elif part != ".":
                        parts.append(part)
                reference = public_path(root, "/".join(parts))
                if not reference.exists():
                    problems.append(f"{name}: unresolved live link: {target}")
    except (ValueError, OSError, KeyError, TypeError, zipfile.BadZipFile) as error:
        problems.append(f"{REGISTRY}: {error}")
    problems.extend(check_consolidation(root))
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resolve", metavar="REPOSITORY_PATH")
    args = parser.parse_args()
    if args.resolve:
        data = json.loads(public_path(ROOT, REGISTRY).read_text(encoding="utf-8"))
        try:
            print(json.dumps(resolve(args.resolve, data), ensure_ascii=False))
            return 0
        except ValueError as error:
            print(str(error))
            return 1
    errors = check_routes()
    for error in errors:
        print(error)
    if not errors:
        print("authority routes: PASS (public navigation only; runtime/CI qualification not established)")
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
