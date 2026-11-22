import base64
import hashlib
import io
import zipfile

import pytest

from scripts.ingest import git_snapshot


def sha(data):
    return hashlib.sha256(data).hexdigest()


@pytest.fixture
def core(monkeypatch):
    commit = "a13f" * 10
    body = b"print('kept as source')\n"
    content = io.BytesIO()
    with zipfile.ZipFile(content, "w") as archive:
        archive.comment = commit.encode()
        archive.writestr("code/example.py", body)
        archive.writestr("original-only.txt", b"another member")
    raw = content.getvalue()
    member = {"name": "code/example.py", "sha256": sha(body)}
    recorded = []
    monkeypatch.setattr(git_snapshot.core_client, "archive_job_result", lambda *args: (
        {"source_id": "zip", "raw_sha256": sha(raw)},
        {"params": {"structure": {"extractable_members": [member]}}}))

    def call(method, path, data=None):
        if path == "/api/v1/sources/zip/members":
            return {"members": [{"member": member["name"], "source_id": "code", "sha256": member["sha256"]}]}
        if path == "/api/v1/documents" and method == "POST":
            recorded.append(data)
            return {"document_id": "index", "version": 1}
        blob = {"/api/v1/sources/zip/original": raw, "/api/v1/sources/code/original": body}[path]
        return {"sha256": sha(blob), "content_base64": base64.b64encode(blob).decode()}
    return call, commit, raw, body, recorded


def test_fixed_snapshot_keeps_original_and_only_indexes_admitted_members(core, tmp_path):
    call, commit, raw, body, docs = core
    result = git_snapshot.save_snapshot(call, "archive", commit.upper())
    index = docs[0]["editor_json"]["attrs"]["archeaxis_git_snapshot"]
    assert result["commit"] == index["commit"] == commit
    assert index["archive_files"] == 2
    assert index["members"] == [{"path": "code/example.py", "source_id": "code", "sha256": sha(body)}]
    assert docs[0]["source_revision"] == sha(raw)
    target = tmp_path / "returned.py"
    result = git_snapshot.export_original(call, "archive", commit, "code/example.py", target)
    assert target.read_bytes() == body and result["sha256"] == sha(body)
    with pytest.raises(FileExistsError):
        git_snapshot.export_original(call, "archive", commit, None, target)
    assert target.read_bytes() == body


def test_mismatched_commit_cannot_save_or_export(core, tmp_path):
    call, _, _, _, docs = core
    with pytest.raises(ValueError, match="differs from the selected commit"):
        git_snapshot.save_snapshot(call, "archive", "0" * 40)
    with pytest.raises(ValueError, match="differs from the selected commit"):
        git_snapshot.export_original(call, "archive", "0" * 40, None, tmp_path / "absent.zip")
    assert not docs and not (tmp_path / "absent.zip").exists()
