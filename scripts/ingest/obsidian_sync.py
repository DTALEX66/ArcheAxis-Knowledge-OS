"""Exchange changed Vault files with the same Core documents across local sync runs."""

from __future__ import annotations

import base64
import json
import os
import shutil
import tempfile
from collections import Counter
from contextlib import contextmanager, suppress
from difflib import SequenceMatcher
from pathlib import Path, PurePosixPath
from urllib.parse import quote

from scripts.ingest import obsidian_vault as vault
from scripts.ingest.directory_batch import EXCLUDED_DIRS, iter_files, sha256_of, source_folder
from scripts.runtime.dev import safe_path

SCHEMA = "archeaxis.vault-sync/v1"
EXPORT_SCHEMA = "archeaxis.vault-sync-export/v1"
FILE_LIMIT = 64 * 1024 * 1024


def member_path(root, name):
    parts = name.split("/")
    if (not name or ":" in name or "\\" in name or any(not p or p.startswith(".") or p.casefold() in EXCLUDED_DIRS
                                                        or any(ord(c) < 32 for c in p) for p in parts)):
        raise ValueError(f"invalid Vault file path: {name}")
    return safe_path(root.joinpath(*parts))


def write_json(path, value):
    data = json.dumps(value, ensure_ascii=False, indent=2).encode()
    if path.is_file() and path.read_bytes() == data:
        return
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        temp = Path(stream.name)
        try:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        except BaseException:
            stream.close()
            temp.unlink(missing_ok=True)
            raise
    try:
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


@contextmanager
def connection_lock(directory):
    # A crashed process releases the OS lock. The same lock covers all receipts for this Vault.
    with safe_path(directory / "sync.lock").open("a+b") as lock:
        if os.name == "nt":
            import msvcrt

            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


def source(call, batch, name, data):
    result = call("POST", "/api/v1/imports", {"name": name, "origin_kind": "path",
                  "origin_ref": "vault/" + batch + "/" + quote(name), "origin_name": name,
                  "content_base64": base64.b64encode(data).decode("ascii")})
    if result["sha256"] != vault.digest(data):
        raise ValueError(f"Core stored a different file for {name}")
    return {"source_id": result["source_id"], "sha256": result["sha256"]}


def install_if_absent(staged, target):
    # Both operations publish the complete file without replacing a name another writer just created.
    if os.name == "nt":
        staged.rename(target)
    else:
        os.link(staged, target)


def finish_write(call, root, directory, batch):
    """Finish a journaled write. Capture a racing writer's displaced bytes before clearing the journal."""
    journal = directory / "pending.json"
    op = json.loads(journal.read_text(encoding="utf8"))
    target = member_path(root, op["path"])
    old, new = safe_path(directory / "previous"), safe_path(directory / "next")
    expected, wanted = op["previous"], op["next"]
    if not old.exists() and expected is not None and target.is_file() and sha256_of(target) == expected:
        target.rename(old)
    displaced = None
    if old.is_file() and sha256_of(old) != expected:
        displaced = source(call, batch, op["path"], old.read_bytes())
        if not target.exists():
            with suppress(FileExistsError):
                install_if_absent(old, target)
    elif (old.is_file() or expected is None) and not target.exists():
        if not new.is_file() or sha256_of(new) != wanted:
            raise ValueError(f"incomplete pending Vault write: {op['path']}")
        with suppress(FileExistsError):
            install_if_absent(new, target)
    installed = target.is_file() and sha256_of(target) == wanted
    # A present previous file is either the already-preserved common revision or the captured racing revision.
    old.unlink(missing_ok=True)
    new.unlink(missing_ok=True)
    journal.unlink()
    return {"path": op["path"], "installed": installed, "intervening_source": displaced}


def push(call, root, directory, batch, name, expected, data):
    target = member_path(root, name)
    target.parent.mkdir(parents=True, exist_ok=True)
    staged = safe_path(directory / "next")
    with staged.open("wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    if target.is_file():
        shutil.copymode(target, staged)
    write_json(directory / "pending.json", {"path": name, "previous": expected, "next": vault.digest(data)})
    return finish_write(call, root, directory, batch)


def document_summaries(call, ids):
    needed = set(ids)
    result = {}
    route = vault.DOCUMENTS
    while needed:
        page = call("GET", route)
        for doc in page["documents"]:
            if doc["document_id"] in needed:
                result[doc["document_id"]] = doc
                needed.remove(doc["document_id"])
        if not page["next_cursor"]:
            break
        route = vault.DOCUMENTS + "?cursor=" + quote(page["next_cursor"], safe="")
    if needed:
        raise ValueError("a synchronized document is absent from this Core workspace")
    return result


def verified_baseline(call, name, row, document_sha=None):
    if row["doc"]:
        route = vault.DOCUMENTS + "/" + quote(row["doc"], safe="") + f"/versions/{row['version']}"
        doc = call("GET", route)
        if document_sha is not None and doc["content_sha256"] != document_sha:
            raise ValueError(f"exported document version differs for {name}")
        raw = rendered(call, row, doc)
    else:
        raw = vault.original_bytes(call, row["blob"]["source_id"], row["blob"]["sha256"])
    if vault.digest(raw) != row["common"]:
        raise ValueError(f"saved document or source differs from the selected Vault baseline for {name}")


def initial_state(call, receipt, identity):
    batch = receipt["batch_id"]
    _, workspace, members = vault.batch_members(call, batch)
    if receipt["workspace_id"] != workspace or workspace != identity["workspace_id"]:
        raise ValueError("the Vault receipt belongs to another Core workspace")
    state = {"schema": SCHEMA, "workspace_id": workspace, "restore_epoch": identity["restore_epoch"],
             "batch_id": batch, "files": {}, "conflicts": {}}
    files = state["files"]
    if receipt.get("schema") == EXPORT_SCHEMA:
        if receipt["restore_epoch"] != identity["restore_epoch"]:
            raise ValueError("the Vault export belongs to another restore epoch")
        for item in receipt["files"]:
            name = item["path"]
            if name in files:
                raise ValueError(f"duplicate exported path: {name}")
            row = {"origin": item["origin"], "blob": item["blob"], "common": item["sha256"],
                   "doc": item["document_id"], "version": item["version"]}
            if row["doc"] and not item["document_sha256"]:
                raise ValueError(f"exported document digest is missing for {name}")
            verified_baseline(call, name, row, item["document_sha256"])
            files[name] = row
        return state
    imported = receipt.get("schema") == "archeaxis.vault-exchange/v1"
    if not imported and not (receipt.get("schema") in {None, "archeaxis.vault-export/v1"} and "files" in receipt):
        raise ValueError("select a Vault import or export receipt")
    selections = {} if imported else {item["path"]: item for item in receipt["files"]}
    classes = vault.classify(call, [m["relative_path"] for m in members])
    for member in members:
        name = member["relative_path"]
        if (not member["source_id"] or classes[name]["disposition"] not in {"import_as_source", "import_as_knowledge"}
                or (not imported and name not in selections)):
            continue
        raw = {"source_id": member["source_id"], "sha256": member["source_revision"]}
        if imported:
            doc_id = receipt["documents"].get(name)
            common, version = raw["sha256"], 1 if doc_id else None
        else:
            selected = selections[name]
            if selected["source_sha256"] != raw["sha256"]:
                raise ValueError(f"exported source identity differs from the batch for {name}")
            doc = selected["document"] or {}
            common, version, doc_id = selected["export_sha256"], doc.get("version"), doc.get("document_id")
        files[name] = {"origin": raw, "blob": raw, "common": common, "doc": doc_id, "version": version}
        if doc_id:
            verified_baseline(call, name, files[name], None if imported else selected["document"]["content_sha256"])
    return state


def rendered(call, row, doc):
    origin = row["origin"]
    if origin and (doc["source_id"], doc["source_revision"]) != (origin["source_id"], origin["sha256"]):
        raise ValueError("document and original Vault member belong to different sources")
    raw = b""
    baseline = row["blob"] or origin
    if baseline and not doc["editor_json"].get("attrs", {}).get("obsidian_sync_source"):
        raw = vault.original_bytes(call, baseline["source_id"], baseline["sha256"])
    return vault.current_markdown(call, doc, raw)


def changed_block(previous, text):
    node = {"type": "paragraph"}
    value = text
    if len(previous) == 1:
        old = previous[0]
        if old["type"] == "paragraph":
            node = dict(old)
            prefix = vault._markdown({"content": previous})
            if prefix and text.startswith(prefix):
                extra = text[len(prefix):]
                node["content"] = list(old.get("content", []))
                if extra:
                    node["content"].append({"type": "text", "text": extra})
                return node
        elif old["type"] == "heading":
            marker = "#" * old["attrs"]["level"] + " "
            if text.startswith(marker) and "\n" not in text:
                node, value = dict(old), text[len(marker):]
    node["content"] = [{"type": "text", "text": value}] if value else []
    return node


def updated_editor(editor, text, raw_source):
    """Keep untouched blocks, their identities, and unrelated document attributes when importing an edit."""
    attrs = {**editor.get("attrs", {}), "obsidian_sync_source": raw_source}
    if vault._markdown(editor) == text:
        return {**editor, "attrs": attrs}
    blocks = editor["content"]
    before, after = [], []
    first, last = 0, len(blocks)
    while first < last:
        fragment = vault._markdown({"content": [blocks[first]]})
        if not text.startswith(fragment + "\n\n"):
            break
        before.append(blocks[first])
        text = text[len(fragment) + 2:]
        first += 1
    while last > first:
        fragment = vault._markdown({"content": [blocks[last - 1]]})
        if not text.endswith("\n\n" + fragment):
            break
        after.append(blocks[last - 1])
        text = text[:-(len(fragment) + 2)]
        last -= 1
    region = blocks[first:last]
    if len(region) <= 1:
        middle = [changed_block(region, text)]
    else:
        # Disjoint edits can surround an unchanged heading or cited block. Carry its exact node across.
        previous = [vault._markdown({"content": [b]}) for b in region]
        parts = text.split("\n\n")
        middle = []
        for tag, a, b, c, d in SequenceMatcher(None, previous, parts).get_opcodes():
            if tag == "equal":
                middle.extend(region[a:b])
            elif c < d:
                middle.append(changed_block(region[a:b], "\n\n".join(parts[c:d])))
    return {**editor, "attrs": attrs, "content": [*before, *middle, *reversed(after)]}


def save_external(call, row, name, data, blob, doc):
    if not row["doc"]:
        return None
    editor = updated_editor(doc["editor_json"], data.decode("utf-8-sig"), blob)
    bundle = editor["attrs"].get("archeaxis_relations", {"schema": "archeaxis.relations/v1", "relations": []})
    link_id = "obsidian_sync_" + vault.digest(row["doc"].encode())[:32]
    links = [link for link in bundle["relations"] if link["id"] != link_id]
    links.append({"id": link_id, "kind": "related", "label": "Obsidian Vault · " + name,
                  "target": {"kind": "source", **blob}})
    editor["attrs"]["archeaxis_relations"] = {**bundle, "relations": links}
    saved = call("PUT", vault.DOCUMENTS + "/" + quote(row["doc"], safe="") + "/draft", {
        "expected_version": doc["version"], "editor_json": editor,
        "revision_basis": {"reference_version": doc["version"], "rationale": "Updated from the connected Obsidian Vault.",
                           "position": {"vault_path": name, **blob}}})
    return saved["version"]


def inventory(call, root):
    paths, skipped = iter_files(root)
    paths = {path.relative_to(root).as_posix(): path for path in paths}
    roles = vault.classify(call, list(paths))
    available, excluded = {}, set()
    for name, path in paths.items():
        if roles[name]["disposition"] not in {"import_as_source", "import_as_knowledge"} or path.stat().st_size > FILE_LIMIT:
            excluded.add(name)
            skipped.append(name)
        else:
            available[name] = sha256_of(path)
    return available, roles, excluded, skipped


def bind_moves(files, disk, excluded, actions):
    missing, added = {}, {}
    previous_count = Counter(row["common"] for row in files.values() if not row.get("detached"))
    current_count = Counter(disk.values())
    for name, row in files.items():
        if name not in disk and name not in excluded and not row.get("detached") and row["common"]:
            missing.setdefault(row["common"], []).append(name)
    for name, digest in disk.items():
        if name not in files:
            added.setdefault(digest, []).append(name)
    for digest, old_names in missing.items():
        new_names = added.get(digest, [])
        if len(old_names) == len(new_names) == previous_count[digest] == current_count[digest] == 1:
            old, new = old_names[0], new_names[0]
            if PurePosixPath(old).suffix.casefold() == PurePosixPath(new).suffix.casefold():
                files[new] = files.pop(old)
                actions.append({"action": "renamed", "from": old, "path": new, "match": "unique_file_digest"})


def external_add(call, state, name, data, role):
    blob = source(call, state["batch_id"], name, data)
    doc = None
    if role == "note":
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = None
        if text is not None:
            doc = vault._save_note(call, blob, name, text, state["batch_id"])
    return {"origin": blob, "blob": blob, "common": blob["sha256"],
            "doc": doc["document_id"] if doc else None, "version": doc["version"] if doc else None}


def observed_bytes(path, expected):
    try:
        data = path.read_bytes()
    except FileNotFoundError:
        return None
    return data if vault.digest(data) == expected else None


def reconcile_file(call, root, directory, batch, name, row, external, version, previous, resolution):
    """Compare both sides with the last common bytes, then apply at most one direction."""
    path = member_path(root, name)
    common, doc_id = row["common"], row["doc"]
    doc = body = raw = None
    local = common
    if doc_id and version != row.get("version"):
        doc = call("GET", vault.DOCUMENTS + "/" + quote(doc_id, safe=""))
        version = doc["version"]
        body = rendered(call, row, doc)
        local = vault.digest(body)
    if external == local:
        action = "converged" if common != local or row.get("detached") else "unchanged"
        if common != local and external is not None:
            raw = observed_bytes(path, external)
            if raw is None:
                return {"action": "retry"}
            row["blob"] = source(call, batch, name, raw)
        row.update(common=local, version=version)
        row.pop("detached", None)
        return {"action": action}

    if external is not None:
        raw = observed_bytes(path, external)
        if raw is None:
            return {"action": "retry"}

    conflict = ((local != common and external != common) or bool(previous.get("reason"))
                or (external is None and row.get("detached") and local != common))
    take_vault = local == common
    conflict_info = {"common_sha256": common, "vault_sha256": external, "aaos_sha256": local,
                     "document_id": doc_id, "version": version}
    if conflict:
        observed = (previous.get("vault_sha256"), previous.get("aaos_sha256"), previous.get("version"))
        if resolution is None or observed != (external, local, version):
            kept = previous.get("vault_source") if previous.get("vault_sha256") == external else None
            blob = (kept or source(call, batch, name, raw)) if raw is not None else None
            return {"action": "conflict", **conflict_info, "vault_source": blob,
                    **({"reason": previous["reason"]} if "reason" in previous else {})}
        take_vault = resolution == "vault"
    if take_vault and external is None:
        action = "unchanged" if row.get("detached") else "removed_from_vault"
        row.update(detached=True, common=local, version=version)
        return {"action": action, "retained_document": doc_id}

    if take_vault:
        blob = source(call, batch, name, raw)
        if doc_id:
            doc = doc or call("GET", vault.DOCUMENTS + "/" + quote(doc_id, safe=""))
            if doc["version"] != version:
                return {"action": "retry"}
            try:
                version = save_external(call, row, name, raw, blob, doc)
            except (UnicodeDecodeError, vault.CoreError) as exc:
                if isinstance(exc, vault.CoreError):
                    if exc.status == 409:
                        return {"action": "retry"}
                    if exc.status not in {400, 413, 422}:
                        raise
                return {"action": "conflict", **conflict_info, "vault_source": blob,
                        "reason": "original bytes retained; " + str(exc)[:220]}
        elif PurePosixPath(name).suffix.casefold() in {".md", ".markdown"}:
            # A formerly source-only note can become editable when its encoding or size changes.
            with suppress(UnicodeDecodeError):
                attached = vault._save_note(call, blob, name, raw.decode("utf-8-sig"), batch)
                if attached:
                    doc_id, version = attached["document_id"], attached["version"]
                    row.update(doc=doc_id, origin=blob)
        row.update(blob=blob, common=external, version=version)
        change = {"action": "pulled", "source": blob, "document_id": doc_id, "version": version}
    else:
        doc = doc or call("GET", vault.DOCUMENTS + "/" + quote(doc_id, safe=""))
        if doc["version"] != version:
            return {"action": "retry"}
        body = body if body is not None else rendered(call, row, doc)
        if raw is not None and (not row["blob"] or row["blob"]["sha256"] != external):
            source(call, batch, name, raw)
        result = push(call, root, directory, batch, name, external, body)
        if not result["installed"]:
            return {"action": "retry", **result}
        row.update(common=local, version=version)
        change = {"action": "pushed", "document_id": doc_id, "version": version}
    row.pop("detached", None)
    return change


def sync_vault(call, root: Path, receipt=None, resolutions=None, additions=None):
    resolutions, additions = resolutions or {}, additions or {}
    if any(side not in {"vault", "aaos"} for side in resolutions.values()):
        raise ValueError("choose vault or aaos for each conflict")
    root = source_folder(root)
    identity = call("GET", vault.BATCHES + "?limit=1")
    directory = safe_path(root / ".aaos-sync")
    cursor = safe_path(directory / "cursor.json")
    if receipt is None and not cursor.is_file():
        raise ValueError("for the first sync, pass --receipt with this Vault's import or export receipt")
    if receipt is not None and receipt["workspace_id"] != identity["workspace_id"]:
        raise ValueError("select the Core workspace named by the receipt")
    directory.mkdir(exist_ok=True)
    with connection_lock(directory):
        fresh = not cursor.exists()
        if fresh and any(entry.name != "sync.lock" for entry in directory.iterdir()):
            raise ValueError("the existing .aaos-sync folder has no matching connection cursor")
        state = initial_state(call, receipt, identity) if fresh else json.loads(cursor.read_text(encoding="utf8"))
        batch = state["batch_id"]
        if (state["schema"] != SCHEMA or (receipt is not None and receipt["batch_id"] != batch)
                or any(state[key] != identity[key] for key in ("workspace_id", "restore_epoch"))):
            raise ValueError("the connected Vault and the current workspace or restore epoch differ")
        if fresh:
            for name in state["files"]:
                member_path(root, name)
        actions, conflicts, retry, issues = [], {}, [], {}
        if (directory / "pending.json").exists():
            actions.append({"action": "recovered_file_write", **finish_write(call, root, directory, batch)})
        disk, roles, excluded, skipped = inventory(call, root)
        files = state["files"]
        if set(resolutions) - state["conflicts"].keys():
            raise ValueError("only a previously reported conflict can be resolved")
        bind_moves(files, disk, excluded, actions)
        attached = {row["doc"] for row in files.values() if row["doc"]}
        for name, doc_id in additions.items():
            member_path(root, name)
            if name in files and files[name]["doc"] == doc_id:
                continue
            if name in files or doc_id in attached or PurePosixPath(name).suffix.casefold() not in {".markdown", ".md"}:
                raise ValueError(f"choose an unused Markdown path and document for {name}")
            files[name] = {"origin": None, "blob": None, "common": None, "doc": doc_id, "version": None}
            attached.add(doc_id)
        summaries = document_summaries(call, attached)
        if fresh or additions or actions:
            write_json(cursor, state)
        unchanged = 0
        for name in sorted(set(disk) | files.keys()):
            if name in excluded:
                continue
            path = member_path(root, name)
            external = disk.get(name)
            row = files.get(name)
            if row is None:
                raw = observed_bytes(path, external)
                if raw is None:
                    retry.append(name)
                    continue
                files[name] = external_add(call, state, name, raw, roles[name]["role"])
                actions.append({"path": name, "action": "added_from_vault", "source": files[name]["blob"],
                                "document_id": files[name]["doc"]})
                continue
            doc_id = row["doc"]
            version = summaries[doc_id]["version"] if doc_id else None
            try:
                change = reconcile_file(call, root, directory, batch, name, row, external, version,
                                        state["conflicts"].get(name, {}), resolutions.get(name))
            except vault.UnsupportedMarkdownError as exc:
                issues[name] = {"document_id": doc_id, "version": version, "reason": str(exc)}
                if name in state["conflicts"]:
                    conflicts[name] = state["conflicts"][name]
                continue
            action = change.pop("action")
            if action == "unchanged":
                unchanged += 1
            elif action == "conflict":
                conflicts[name] = change
            elif action == "retry":
                retry.append(name)
                if change.get("intervening_source"):
                    actions.append({"action": "intervening_file_change", **change})
            else:
                actions.append({"path": name, "action": action, **change})
        state["conflicts"] = conflicts
        write_json(cursor, state)
        return {"schema": "archeaxis.vault-sync-result/v1", "cursor": str(cursor), "batch_id": batch,
                "actions": actions, "unchanged": unchanged, "conflicts": conflicts,
                "retry": retry, "issues": issues, "excluded": [s for s in skipped if not s.startswith(".aaos-sync ")]}


def export_synced(call, cursor, output, after_restore=False):
    actual = call("GET", vault.BATCHES + "?limit=1")
    if cursor["workspace_id"] != actual["workspace_id"]:
        raise ValueError("the sync cursor belongs to a different workspace")
    restored = cursor["restore_epoch"] != actual["restore_epoch"]
    if restored and not after_restore:
        raise ValueError("the restore epoch changed; use export --after-restore to recover a new Vault")
    if output.exists():
        raise ValueError("choose a new directory for the exported Vault")
    if restored:
        vault.batch_members(call, cursor["batch_id"])
        for name, conflict in cursor["conflicts"].items():
            observed = conflict.get("vault_source")
            if observed:
                vault.original_bytes(call, observed["source_id"], conflict["vault_sha256"])
            if conflict.get("document_id"):
                row = {**cursor["files"][name], "version": conflict["version"], "common": conflict["aaos_sha256"]}
                verified_baseline(call, name, row)
    saved = []
    with tempfile.TemporaryDirectory(prefix=".aaos-vault-", dir=output.parent) as tmp:
        folder = Path(tmp) / "vault"
        folder.mkdir()
        for name, row in cursor["files"].items():
            if row.get("detached"):
                continue
            target = member_path(folder, name)
            version = document_sha = None
            if row["doc"]:
                doc = call("GET", vault.DOCUMENTS + "/" + quote(row["doc"], safe=""))
                raw = rendered(call, row, doc)
                version = doc["version"]
                document_sha = doc["content_sha256"]
            else:
                raw = vault.original_bytes(call, row["blob"]["source_id"], row["blob"]["sha256"])
            if restored:
                if row["doc"] and version != row["version"]:
                    verified_baseline(call, name, row)
                elif vault.digest(raw) != row["common"]:
                    raise ValueError(f"restored bytes differ from the selected Vault baseline for {name}")
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as stream:
                stream.write(raw)
            saved.append({"path": name, "sha256": vault.digest(raw), "document_id": row["doc"], "version": version,
                          "document_sha256": document_sha, "origin": row["origin"], "blob": row["blob"]})
        folder.rename(output)
    return {"schema": EXPORT_SCHEMA, "workspace_id": actual["workspace_id"], "restore_epoch": actual["restore_epoch"],
            **({"recovered_from_epoch": cursor["restore_epoch"]} if restored else {}),
            "batch_id": cursor["batch_id"], "path": str(output), "files": saved, "conflicts": cursor["conflicts"]}
