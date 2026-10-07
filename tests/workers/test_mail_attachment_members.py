"""R15/F13: a mail's attachments leave the mail and become members the Core can import.

The declaration shape is the container one (`params.structure.extractable_members` with
name/file/bytes/sha256) because the Core already knows how to verify that, import each part as
its own source and queue the route the part's own name selects. What is new is only that a mail
can say it has parts.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import sys
import tempfile
from email.message import EmailMessage
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
TEXT = REPO / "services" / "python-workers" / "document" / "worker_text.py"
TRANSPORT = REPO / "services" / "python-workers" / "transport" / "text_ndjson.py"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


worker_text = _load("mail_member_worker_text", TEXT)
transport = _load("mail_member_transport", TRANSPORT)


def _mail(count: int = 2, body: str = "Please find the two files.\n") -> bytes:
    message = EmailMessage()
    message["From"] = "sender@example.invalid"
    message["To"] = "reader@example.invalid"
    message["Subject"] = "Two files"
    message.set_content(body)
    for index in range(1, count + 1):
        message.add_attachment(
            f"attachment value {index} 6371\n".encode("utf-8"),
            maintype="text",
            subtype="plain",
            filename=f"note-{index}.txt",
        )
    return message.as_bytes()


def _write(tmp_path: Path, raw: bytes) -> Path:
    path = tmp_path / "letter.eml"
    path.write_bytes(raw)
    return path


def _members(result: dict) -> list[dict]:
    return result["loss_receipt"]["params"]["structure"]["extractable_members"]


def test_attachments_are_written_flat_and_declared_by_digest(tmp_path: Path):
    box = tmp_path / "members"
    result = worker_text.extract(str(_write(tmp_path, _mail())), "message/rfc822",
                                 member_dir=str(box))
    members = _members(result)
    assert len(members) == 2, members
    assert {item["name"] for item in members} == {"note-1.txt", "note-2.txt"}
    for item in members:
        assert "/" not in item["file"] and "\\" not in item["file"] and ".." not in item["file"]
        written = (box / item["file"]).read_bytes()
        assert len(written) == item["bytes"]
        assert hashlib.sha256(written).hexdigest() == item["sha256"], "the digest is of the bytes written"
    losses = result["loss_receipt"]["losses"]
    assert any("2 attachments extracted" in line for line in losses), losses
    assert not any("independent extraction is not performed" in line for line in losses), (
        "the inventory-only loss line must not survive an extraction that actually happened"
    )


def test_the_written_name_is_safe_but_the_declaration_keeps_the_real_name(tmp_path: Path):
    message = EmailMessage()
    message.set_content("body\n")
    message.add_attachment(b"escaped payload", maintype="application", subtype="octet-stream",
                           filename="../evil report.png")
    box = tmp_path / "members"
    result = worker_text.extract(str(_write(tmp_path, message.as_bytes())), "message/rfc822",
                                 member_dir=str(box))
    members = _members(result)
    assert len(members) == 1
    assert members[0]["name"] == "../evil report.png", "the true name travels in the declaration"
    assert (box / members[0]["file"]).is_file()
    assert list(box.iterdir()) == [box / members[0]["file"]], "nothing was written outside the area"
    assert members[0]["sha256"] == hashlib.sha256(b"escaped payload").hexdigest()


def test_no_transfer_area_means_no_members_and_the_inventory_stays(tmp_path: Path):
    result = worker_text.extract(str(_write(tmp_path, _mail())), "message/rfc822")
    assert _members(result) == []
    assert result["loss_receipt"]["params"]["attachment_extraction"] == {
        "count": 0, "requested": False, "only_for": "message/rfc822",
    }
    assert len(result["loss_receipt"]["params"]["format"]["attachments"]) == 2


def test_the_count_budget_is_reported_rather_than_silently_truncated(tmp_path: Path):
    box = tmp_path / "members"
    result = worker_text.extract(str(_write(tmp_path, _mail(count=51))), "message/rfc822",
                                 member_dir=str(box))
    members = _members(result)
    assert len(members) == 50, members
    problems = [line for line in result["loss_receipt"]["losses"] if "only the first" in line]
    assert problems == ["only the first 50 of 51 attachments were extracted"], problems
    assert len(list(box.iterdir())) == 50


def test_a_non_mail_media_type_is_never_handed_a_transfer_directory(tmp_path: Path):
    box = tmp_path / "members"
    path = tmp_path / "plain.txt"
    path.write_text("just text\n", encoding="utf-8")
    result = worker_text.extract(str(path), "text/plain", member_dir=str(box))
    assert _members(result) == []
    assert not box.exists(), "a text file gets no attachment extraction and no directory"


def _request(media_type: str, digest: str) -> dict:
    return {
        "schema": "archeaxis.worker-request/v1", "type": "job_request", "request_id": "r",
        "job_id": "j", "attempt": 1, "protocol_minor": 0, "capability": "text.extract",
        "capability_version": "1", "deadline_ms": 60_000,
        "inputs": [{"uri": f"job://input/{digest}", "sha256": digest, "media_type": media_type}],
        "parameters": {},
    }


def _run(tmp_path: Path, raw: bytes, media_type: str, label: str):
    staging = tmp_path / "staging"
    digest = hashlib.sha256(raw).hexdigest()
    (staging / "input").mkdir(parents=True, exist_ok=True)
    (staging / "input" / digest).write_bytes(raw)
    # One attempt root per call: the Core gives each attempt its own, and sharing one here
    # would let the mail run's directory be read as the plain text run's result.
    root = staging / f"attempt-{label}"
    outputs, _measurements, _losses = transport.execute(_request(media_type, digest), staging,
                                                        artifact_root=root)
    loss = next(o for o in outputs if o["kind"] == "loss_report")
    receipt = json.loads((staging / "output" / loss["uri"].rsplit("/", 1)[-1]).read_bytes())
    return receipt, root


def test_the_transport_hands_the_mail_route_a_transfer_area_and_nothing_else(tmp_path: Path):
    receipt, root = _run(tmp_path, _mail(), "message/rfc822; charset=utf-8", "mail")
    members = receipt["params"]["structure"]["extractable_members"]
    assert len(members) == 2, members
    for item in members:
        assert (root / "members" / item["file"]).read_bytes()
    plain, plain_root = _run(tmp_path, b"plain note 6371\n", "text/plain", "plain")
    assert plain["params"]["structure"]["extractable_members"] == []
    assert not (plain_root / "members").exists(), (
        "the plain text route must never receive the directory that only a mail may write into"
    )


def _bodyless_mail(*, headers: bool = True, attachments: int = 1, empty_body: bool = False) -> bytes:
    """A mail whose body lane carries no readable text: no part, an empty part, or both.

    This is the shape that used to fail the whole job - "see attached" with nothing typed.
    """
    message = EmailMessage()
    if headers:
        message["From"] = "sender@example.invalid"
        message["To"] = "reader@example.invalid"
        message["Subject"] = "Only a file"
        message["Date"] = "Wed, 07 Oct 2026 04:40:00 +0800"
    if empty_body:
        message.set_content("   \n")
    for index in range(1, attachments + 1):
        message.add_attachment(
            f"attachment value {index} 6371\n".encode("utf-8"),
            maintype="text",
            subtype="plain",
            filename=f"only-{index}.txt",
        )
    return message.as_bytes()


def test_a_mail_with_no_readable_body_projects_its_own_headers(tmp_path: Path):
    """A bodyless mail is not an unreadable one: its headers are the file's own text.

    F13 names mail headers as a required output, so failing the job here lost the headers
    together with the absent body. The projection is the header block, and the receipt says
    that no body is claimed.
    """
    box = tmp_path / "members"
    result = worker_text.extract(str(_write(tmp_path, _bodyless_mail())), "message/rfc822",
                                 member_dir=str(box))
    text = result["text"]
    assert text.startswith("From: sender@example.invalid\nTo: reader@example.invalid\n"), text
    assert "Subject: Only a file" in text and "Date: Wed, 07 Oct 2026 04:40:00 +0800" in text
    assert "Please find" not in text, "no body may be claimed for a mail that has none"
    assert len(result["structure"]) == 4, result["structure"]

    facts = result["loss_receipt"]["params"]["format"]
    assert facts["has_readable_body"] is False
    assert facts["text_body_parts"] == 0
    assert {item["kind"] for item in facts["locations"]} == {"mail_header"}
    losses = " ".join(result["loss_receipt"]["losses"])
    assert "no text body part exists" in losses
    assert "no body is claimed" in losses
    assert "mail MIME body decoded" not in losses, losses
    # the extraction did happen, so the not-performed line must not survive into the receipt
    assert "independent extraction is not performed" not in losses, losses
    assert "1 attachments extracted" in losses, losses


def test_a_mail_whose_text_part_is_empty_is_stated_as_empty(tmp_path: Path):
    """The two shapes are different facts and must not collapse into one claim."""
    result = worker_text.extract(str(_write(tmp_path, _bodyless_mail(empty_body=True))),
                                 "message/rfc822")
    losses = " ".join(result["loss_receipt"]["losses"])
    assert "every text body part is empty" in losses, losses
    assert "no text body part exists" not in losses, losses
    assert result["loss_receipt"]["params"]["format"]["text_body_parts"] == 1


def test_a_bodyless_mail_without_headers_still_reaches_its_attachments(tmp_path: Path):
    """Without headers there is nothing to project, and the receipt says so rather than
    inventing text - but the attachments are still declared for the Core to import."""
    box = tmp_path / "members"
    result = worker_text.extract(
        str(_write(tmp_path, _bodyless_mail(headers=False))), "message/rfc822",
        member_dir=str(box),
    )
    assert result["text"] == ""
    assert result["structure"] == []
    assert result["loss_receipt"]["coverage"] == 1.0
    losses = " ".join(result["loss_receipt"]["losses"])
    assert "the projection claims no text" in losses, losses
    assert "no readable headers are present" in losses, losses
    assert len(_members(result)) == 1, _members(result)


def test_a_mail_with_nothing_readable_at_all_is_refused(tmp_path: Path):
    raw = (b"MIME-Version: 1.0\r\nContent-Type: application/octet-stream\r\n\r\n")
    try:
        worker_text.extract(str(_write(tmp_path, raw)), "message/rfc822")
    except ValueError as exc:
        assert "no readable text body, headers or attachments" in str(exc), exc
    else:
        raise AssertionError("a mail with nothing readable must not be reported as a success")


def test_a_mail_with_a_real_body_is_unchanged(tmp_path: Path):
    result = worker_text.extract(str(_write(tmp_path, _mail(count=1))), "message/rfc822")
    assert result["text"] == "Please find the two files.\n"
    facts = result["loss_receipt"]["params"]["format"]
    assert facts["has_readable_body"] is True and facts["text_body_parts"] == 1
    assert {item["kind"] for item in facts["locations"]} == {"mail_mime_part"}
    assert "mail MIME body decoded" in " ".join(result["loss_receipt"]["losses"])



@pytest.mark.skipif(sys.platform != "win32", reason="the plain-path limit is a Windows fact")
def test_an_attachment_is_still_declared_at_the_depth_the_host_transfer_area_has():
    """The attempt-keyed transfer area reaches 247 characters in an ordinary worktree.

    A mail's own attachment name puts the written file past the length Windows enforces on a
    plain path, where the create fails as ERROR_FILE_NOT_FOUND and the worker reported the part
    as unwritable - so the mail declared zero members while the Core was never told a limit was
    hit. The premise is measured here, not assumed: the same plain write is refused before the
    worker is asked to do it, and the declared bytes are read back through the transport's own
    IO-boundary helper.
    """
    box = Path(tempfile.mkdtemp())
    try:
        node = box
        if len(str(node)) < 239:
            node = node / ("c" * (239 - len(str(node)) - 1))
        if len(str(node)) > 243:
            pytest.skip("the temporary base is already too deep to express the host shape")
        node.mkdir(parents=True, exist_ok=True)
        members = node / "members"
        members.mkdir()
        target = members / "0001-note-1.txt"
        assert len(str(members)) <= 251 and len(str(target)) >= 261
        try:
            target.write_bytes(b"x")
        except OSError:
            pass
        else:
            pytest.skip("this machine creates files past the limit, so the shape is absent")

        source = node / "letter.eml"
        source.write_bytes(_mail())
        result = worker_text.extract(str(source), "message/rfc822", member_dir=str(members))
        declared = _members(result)
        assert {item["name"] for item in declared} == {"note-1.txt", "note-2.txt"}, declared
        assert not any("could not be written" in line
                       for line in result["loss_receipt"]["losses"]), result["loss_receipt"]["losses"]
        for item in declared:
            written = transport.filesystem_path(members / item["file"]).read_bytes()
            assert hashlib.sha256(written).hexdigest() == item["sha256"]
    finally:
        shutil.rmtree(transport.filesystem_path(box), ignore_errors=True)
