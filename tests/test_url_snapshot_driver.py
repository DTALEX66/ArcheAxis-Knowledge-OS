"""R15/F02: the URL snapshot driver records a capture time it can honestly claim.

Two halves are tested here: the address policy that lets a fetch exist at all without turning the
product into a way to reach internal services, and the driver's receipt - what it sends to the Core,
and what it does when the fetch never happened.
"""

from __future__ import annotations

import importlib.util
import json
import socket
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[1]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


webpage = _load("url_test_webpage", REPO / "services/python-workers/web/worker_webpage.py")
driver = _load("url_test_driver", REPO / "scripts/ingest/url_snapshot.py")


class AddressPolicyTests(unittest.TestCase):
    def test_internal_addresses_are_refused_by_number(self):
        for host in ["127.0.0.1", "127.1.2.3", "10.0.0.5", "172.16.0.9", "192.168.1.1",
                     "169.254.169.254", "0.0.0.0", "::1", "fe80::1", "fc00::1",
                     "::ffff:127.0.0.1", "224.0.0.1"]:
            with self.subTest(host=host):
                with self.assertRaises(ValueError) as caught:
                    webpage.public_addresses(host)
                self.assertIn("refused", str(caught.exception))

    def test_a_public_literal_is_accepted(self):
        self.assertEqual(webpage.public_addresses("93.184.216.34"), ["93.184.216.34"])

    def test_a_name_is_judged_by_every_answer_it_resolves_to(self):
        # the resolver is stubbed so the answer is fixed: a name that really resolves today could
        # resolve anywhere tomorrow, and a test must not depend on live DNS to make its point
        def resolving(*answers):
            return mock.patch.object(
                webpage.socket, "getaddrinfo",
                return_value=[(2, 1, 6, "", (answer, 0)) for answer in answers])

        with resolving("93.184.216.34"):
            self.assertEqual(webpage.public_addresses("example.com"), ["93.184.216.34"])
        with resolving("93.184.216.34", "127.0.0.1"):
            with self.assertRaises(ValueError) as caught:
                webpage.public_addresses("split-horizon.example")
            self.assertIn("127.0.0.1", str(caught.exception))
        with mock.patch.object(webpage.socket, "getaddrinfo",
                               side_effect=socket.gaierror("no such host")):
            with self.assertRaises(ValueError):
                webpage.public_addresses("does.not.resolve.invalid")

    def test_a_redirect_is_refused_before_it_is_followed(self):
        handler = webpage._GuardedRedirects()
        request = webpage.urllib.request.Request("https://example.com/a")
        for target, reason in (("http://127.0.0.1/admin", "127.0.0.1"),
                               ("ftp://example.com/x", "unsupported scheme"),
                               ("http://169.254.169.254/latest", "169.254.169.254")):
            with self.subTest(target=target):
                with self.assertRaises(ValueError) as caught:
                    handler.redirect_request(request, None, 302, "Found", {}, target)
                self.assertIn(reason, str(caught.exception))

    def test_the_scheme_rule_still_holds(self):
        with tempfile.TemporaryDirectory() as box:
            with self.assertRaises(ValueError):
                webpage.fetch("file:///etc/passwd", Path(box))
            with self.assertRaises(ValueError):
                webpage.fetch("gopher://example.com/", Path(box))

    def test_an_oversized_body_is_not_written_off_as_a_snapshot(self):
        class Body:
            def __init__(self, chunks):
                self._chunks = list(chunks)

            def read(self, _size):
                return self._chunks.pop(0) if self._chunks else b""

            def geturl(self):
                return "https://example.com/big"

            status = 200

            headers = {"Content-Type": "text/html"}

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

        original = webpage.MAX_BYTES
        webpage.MAX_BYTES = 1024
        try:
            with tempfile.TemporaryDirectory() as box:
                with mock.patch.object(webpage, "public_addresses", return_value=["93.184.216.34"]), \
                        mock.patch.object(webpage, "checked_open",
                                          return_value=Body([b"x" * 900, b"y" * 900])):
                    with self.assertRaises(RuntimeError) as caught:
                        webpage.fetch("https://example.com/big", Path(box))
                    self.assertIn("byte cap", str(caught.exception))
                    self.assertFalse((Path(box) / "snapshot.html").exists(),
                                     "a truncated body must not be kept as if it were the page")
        finally:
            webpage.MAX_BYTES = original

    def test_probe_reports_its_bounds(self):
        self.assertTrue(webpage.probe()["capability"])


class DriverTests(unittest.TestCase):
    def test_a_file_name_for_a_url_cannot_escape_or_stay_nameless(self):
        cases = {
            "https://example.com": "example.com-index.html",
            "https://example.com/a/b/report.HTML": "example.com-report.HTML",
            # only the last plain segment survives, so a traversal-shaped path yields its tail
            "https://example.com/../../etc/passwd": "example.com-passwd.html",
            "https://docs.example.io/v2/api": "docs.example.io-api.html",
            "https://example.com/page?q=1": "example.com-page.html",
        }
        for url, expected in cases.items():
            with self.subTest(url=url):
                self.assertEqual(driver.snapshot_name(url), expected)
                self.assertNotIn("/", driver.snapshot_name(url))
                self.assertNotIn("..", driver.snapshot_name(url))

    def run_driver(self, fetch_result, calls):
        def core_call(method, path, body):
            calls.append((method, path, body))
            if path == "/api/v1/imports":
                return 201, {"source_id": "src_abc"}
            return 201, {"job_id": body["job_id"]}

        with tempfile.TemporaryDirectory() as box:
            with mock.patch.object(driver, "_load", lambda name, path: webpage), \
                    mock.patch.object(webpage, "fetch", return_value=fetch_result):
                return driver.run_snapshot("https://example.com/a", core_call,
                                           workspace=Path(box))

    def test_the_import_carries_the_moment_the_body_arrived(self):
        with tempfile.TemporaryDirectory() as box:
            snapshot = Path(box) / "snap" / "snapshot.html"
            snapshot.parent.mkdir(parents=True)
            snapshot.write_bytes(b"<html><body>6371</body></html>")
            fetched = {
                "final_url": "https://example.com/final",
                "http_status": 200,
                "fetched_at": "2026-10-07T03:04:05+00:00",
                "snapshot": {"path": str(snapshot), "sha256": "a" * 64, "bytes": 30},
            }
            calls = []
            record = self.run_driver(fetched, calls)

        self.assertEqual(record["status"], "enqueued", record)
        imports = [call for call in calls if call[1] == "/api/v1/imports"]
        self.assertEqual(len(imports), 1)
        body = imports[0][2]
        self.assertEqual(body["origin_kind"], "url")
        self.assertEqual(body["origin_ref"], "https://example.com/final",
                         "the origin names the URL that was actually served, after redirects")
        self.assertEqual(body["received_at"], "2026-10-07T03:04:05+00:00",
                         "F02's capture time is the fetch clock, not a caller's guess")
        jobs = [call for call in calls if call[1] == "/api/v1/jobs"]
        self.assertEqual(jobs[0][2]["kind"], "html")
        self.assertEqual(jobs[0][2]["input_ref"], "src_abc")
        self.assertEqual(record["source_id"], "src_abc")
        self.assertEqual(record["received_at"], "2026-10-07T03:04:05+00:00")

    def test_a_fetch_that_did_not_happen_produces_no_source_and_no_invented_time(self):
        calls = []
        with tempfile.TemporaryDirectory() as box:
            with mock.patch.object(driver, "_load", lambda name, path: webpage), \
                    mock.patch.object(webpage, "fetch",
                                      side_effect=ValueError("refused 127.0.0.1: it is not a public address")):
                record = driver.run_snapshot("http://127.0.0.1/admin", lambda *args: calls.append(args),
                                             workspace=Path(box))
        self.assertEqual(record["status"], "failed")
        self.assertIsNone(record["source_id"])
        self.assertIsNone(record["job_id"])
        self.assertNotIn("received_at", record, "no fetch, therefore no capture time")
        self.assertIn("not a public address", record["error"])
        self.assertEqual(calls, [], "a failed fetch must not reach the Core at all")

    def test_dry_run_reports_what_it_would_do_without_touching_the_core(self):
        with tempfile.TemporaryDirectory() as box:
            snapshot = Path(box) / "snap" / "snapshot.html"
            snapshot.parent.mkdir(parents=True)
            snapshot.write_bytes(b"<html>x</html>")
            fetched = {"final_url": "https://example.com/final", "http_status": 200,
                       "fetched_at": "2026-10-07T03:04:05+00:00",
                       "snapshot": {"path": str(snapshot), "sha256": "b" * 64, "bytes": 12}}
            calls = []
            with mock.patch.object(driver, "_load", lambda name, path: webpage), \
                    mock.patch.object(webpage, "fetch", return_value=fetched):
                record = driver.run_snapshot("https://example.com/a", lambda *args: calls.append(args),
                                             workspace=Path(box), dry_run=True)
        self.assertEqual(record["status"], "dry_run")
        self.assertEqual(calls, [])
        self.assertEqual(record["received_at"], "2026-10-07T03:04:05+00:00")

    def test_a_failed_import_is_recorded_as_failure_not_as_a_queued_job(self):
        with tempfile.TemporaryDirectory() as box:
            snapshot = Path(box) / "snap" / "snapshot.html"
            snapshot.parent.mkdir(parents=True)
            snapshot.write_bytes(b"<html>x</html>")
            fetched = {"final_url": "https://example.com/final", "http_status": 200,
                       "fetched_at": "2026-10-07T03:04:05+00:00",
                       "snapshot": {"path": str(snapshot), "sha256": "c" * 64, "bytes": 12}}

            def core_call(method, path, body):
                return 413, "payload too large"

            with mock.patch.object(driver, "_load", lambda name, path: webpage), \
                    mock.patch.object(webpage, "fetch", return_value=fetched):
                record = driver.run_snapshot("https://example.com/a", core_call, workspace=Path(box))
        self.assertEqual(record["status"], "failed")
        self.assertIsNone(record["job_id"])
        self.assertIn("413", record["error"])

    def test_the_receipt_is_appended_as_one_json_line_per_run(self):
        with tempfile.TemporaryDirectory() as box:
            path = Path(box) / "receipts.jsonl"
            driver.append_record(path, {"status": "enqueued", "url": "https://a"})
            driver.append_record(path, {"status": "failed", "url": "https://b"})
            lines = path.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 2)
        self.assertEqual([json.loads(line)["url"] for line in lines], ["https://a", "https://b"])


if __name__ == "__main__":
    unittest.main()
