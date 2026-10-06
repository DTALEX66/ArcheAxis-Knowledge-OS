"""F03: a page whose text only exists after its own scripts ran is reachable, and that is proved
against a real browser - not asserted.

The recorded gap said "there is still no browser". Playwright and a chromium build are installed on
this host, so the honest questions were whether the render lane reaches it, whether the address
policy still runs when a browser follows redirects by itself, and whether a render that cannot
happen is refused instead of quietly answered with the served bytes. The last test decides the
claim: it renders a page whose body is produced by a script and asserts the served document does not
contain that text.

One headless browser launch, against a loopback server this test starts; no external host is
contacted. Patching `public_addresses` is a test seam for a loopback host, not a hole in the policy -
the policy tests below check that the calls still happen.
"""

from __future__ import annotations

import base64
import importlib.util
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

REPO = Path(__file__).resolve().parents[2]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


webpage = _load("render_test_webpage", REPO / "services/python-workers/web/worker_webpage.py")
driver = _load("render_test_driver", REPO / "scripts/ingest/url_snapshot.py")

SCRIPTED_MARKER = "TEXT THAT ONLY EXISTS AFTER SCRIPTING"
SERVED_MARKER = "this text is in the served document"
# The scripted text is not in this markup at all: it arrives from a second request that only a
# page which executed its script makes. So "the served document does not contain it" is a real
# difference rather than a string that happens to sit inside a <script> tag.
PAGE = (
    "<!doctype html><html><head><title>rendered proof</title></head><body>"
    f"<p>{SERVED_MARKER}</p>"
    "<script>fetch('/late').then(r => r.text()).then(t => {"
    "const grown = document.createElement('div');"
    "grown.id = 'grown';grown.textContent = t;"
    "document.body.appendChild(grown);});</script>"
    "</body></html>"
)


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802 - the name http.server requires
        body = (SCRIPTED_MARKER if self.path == "/late" else PAGE).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):  # keep the test output readable
        pass


class FakePage:
    """A stand-in page whose scroll height is whatever the test says it is."""

    def __init__(self, heights, *, url="https://elsewhere.example/page"):
        self._heights = list(heights)
        self.gotos: list[str] = []
        self.url = url

    def goto(self, url, **_kwargs):
        self.gotos.append(url)

    def evaluate(self, script):
        if "scrollBy" in script:
            return None
        return self._heights.pop(0) if self._heights else self._heights[0] if self._heights else 1000

    def wait_for_timeout(self, _ms):
        return None

    def title(self):
        return "rendered proof"

    def inner_text(self, _selector):
        return SCRIPTED_MARKER

    def content(self):
        return PAGE


def _fake_browser(page, state: dict):
    """A `_browser` replacement that records that the render closed what it opened."""

    class FakeSession:
        def stop(self):
            state["session_stopped"] = True

    class FakeBrowser:
        version = "999.0.test"

        def close(self):
            state["closed"] = True

        def new_page(self, **_kwargs):
            return page

    def factory():
        return FakeSession(), FakeBrowser()

    return factory


def _served(box: Path, final_url: str = "https://elsewhere.example/page") -> dict:
    snapshot = box / "snapshot.html"
    snapshot.write_bytes(b"<p>served</p>")
    return {
        "engine": webpage.ENGINE,
        "engine_version": webpage.ENGINE_VERSION,
        "final_url": final_url,
        "http_status": 200,
        "snapshot": {"path": str(snapshot), "sha256": "a" * 64, "bytes": 13},
        "fetched_at": "2026-10-07T00:00:00+00:00",
        "loss_receipt": {"params": {}},
    }


class RenderPolicyTests(unittest.TestCase):
    def test_the_address_policy_runs_before_the_browser_is_sent_anywhere(self):
        """A fetch that was allowed does not make the redirect target allowed."""
        checked: list[str] = []

        def record(host, resolver=None):
            checked.append(host)
            return ["93.184.216.34"]

        with TemporaryDirectory() as box:
            page = FakePage([1000, 1000], url="https://elsewhere.example/page")
            with mock.patch.object(webpage, "public_addresses", record), \
                    mock.patch.object(webpage, "_browser", _fake_browser(page, {})), \
                    mock.patch.object(webpage, "fetch", return_value=_served(Path(box))):
                webpage.render("https://example.com/page", Path(box))

        self.assertEqual(checked, ["example.com", "elsewhere.example"],
                         "the requested host, then the host the browser would be sent to")

    def test_a_refused_landing_host_stops_the_render_after_a_successful_fetch(self):
        def refuse(host, resolver=None):
            if host == "internal.invalid":
                raise ValueError(f"{host} resolves to a non-public address")
            return ["93.184.216.34"]

        with TemporaryDirectory() as box:
            page = FakePage([1000, 1000], url="https://internal.invalid/page")
            with mock.patch.object(webpage, "public_addresses", refuse), \
                    mock.patch.object(webpage, "_browser", _fake_browser(page, {})), \
                    mock.patch.object(webpage, "fetch",
                                      return_value=_served(Path(box), "https://internal.invalid/page")):
                with self.assertRaises(ValueError):
                    webpage.render("https://example.com/page", Path(box))

            self.assertEqual(page.gotos, [], "the browser is never sent to a refused host")
            self.assertFalse((Path(box) / "rendered.html").exists())

    def test_a_page_that_navigated_somewhere_else_is_checked_too(self):
        """The URL the browser ended on is a fourth opinion, not the one we asked for."""
        checked: list[str] = []

        def record(host, resolver=None):
            checked.append(host)
            if host == "swapped.example":
                raise ValueError(f"{host} resolves to a non-public address")
            return ["93.184.216.34"]

        with TemporaryDirectory() as box:
            page = FakePage([1000, 1000], url="https://swapped.example/page")
            with mock.patch.object(webpage, "public_addresses", record), \
                    mock.patch.object(webpage, "_browser", _fake_browser(page, {})), \
                    mock.patch.object(webpage, "fetch",
                                      return_value=_served(Path(box), "https://elsewhere.example/page")):
                with self.assertRaises(ValueError):
                    webpage.render("https://example.com/page", Path(box))

        self.assertEqual(checked[-1], "swapped.example")
        self.assertEqual(len(page.gotos), 1, "the browser did navigate, and the landing was re-checked")


class RenderLifecycleTests(unittest.TestCase):
    def test_the_browser_is_closed_even_when_the_page_fails(self):
        state: dict = {}

        class Boom(FakePage):
            def goto(self, url, **kwargs):
                raise RuntimeError("navigation refused by the browser")

        with TemporaryDirectory() as box, \
                mock.patch.object(webpage, "public_addresses", return_value=["93.184.216.34"]), \
                mock.patch.object(webpage, "_browser", _fake_browser(Boom([]), state)), \
                mock.patch.object(webpage, "fetch", return_value=_served(Path(box))):
            with self.assertRaises(RuntimeError):
                webpage.render("https://example.com/page", Path(box))

        self.assertEqual(state, {"closed": True, "session_stopped": True})

    def test_no_browser_is_a_named_refusal_and_never_a_relabelled_fetch(self):
        def missing():
            raise RuntimeError("render engine missing: chromium could not be launched")

        with TemporaryDirectory() as box, \
                mock.patch.object(webpage, "public_addresses", return_value=["93.184.216.34"]), \
                mock.patch.object(webpage, "_browser", missing), \
                mock.patch.object(webpage, "fetch", return_value=_served(Path(box))):
            with self.assertRaises(RuntimeError) as caught:
                webpage.render("https://example.com/page", Path(box))

        self.assertIn("render engine missing", str(caught.exception))
        self.assertFalse((Path(box) / "rendered.html").exists(),
                         "a render that did not happen must not leave an artefact behind")

    def test_the_probe_states_the_engine_state_without_launching_anything(self):
        report = webpage.probe()
        self.assertTrue(report["params"]["scroll_limit"])
        self.assertIn("playwright", report["engines"])
        self.assertIn("only established by an actual render", report["note"])


class ScrollBudgetTests(unittest.TestCase):
    def test_a_page_that_keeps_growing_reports_the_budget_running_out(self):
        page = FakePage([1000 + 1000 * index for index in range(200)])
        coverage = webpage.scroll_to_bottom(page, scroll_limit=3)
        self.assertEqual(coverage["scrolls"], 3)
        self.assertTrue(coverage["budget_exhausted"])
        self.assertFalse(coverage["height_stabilized"])

    def test_a_page_that_stops_growing_is_reported_as_reached(self):
        """One scroll whose height did not change is the whole signal: the page is finished."""
        coverage = webpage.scroll_to_bottom(FakePage([1000, 1000]), scroll_limit=10)
        self.assertEqual(coverage["scrolls"], 1)
        self.assertTrue(coverage["height_stabilized"])
        self.assertFalse(coverage["budget_exhausted"])
        self.assertEqual(coverage["final_scroll_height"], 1000)


class DriverRenderTests(unittest.TestCase):
    @staticmethod
    def _capture(out_dir: Path) -> dict:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "rendered.html").write_text(PAGE, encoding="utf-8")
        return {
            "engine": webpage.ENGINE,
            "engine_version": webpage.ENGINE_VERSION,
            "final_url": "https://example.com/page",
            "http_status": 200,
            "title": "rendered proof",
            "snapshot": {"path": str(out_dir / "snapshot.html"), "sha256": "s" * 64, "bytes": 13},
            "rendered": {
                "path": str(out_dir / "rendered.html"),
                "text_path": str(out_dir / "rendered-text.txt"),
                "sha256": "r" * 64,
                "bytes": len(PAGE.encode("utf-8")),
                "text_chars": 900,
                "rendered_at": "2026-10-07T00:00:00+00:00",
            },
            "fetched_at": "2026-10-07T00:00:00+00:00",
            "loss_receipt": {"params": {"scroll": {"scrolls": 2, "height_stabilized": True}}},
        }

    def test_the_rendered_body_is_what_gets_imported_and_both_digests_are_kept(self):
        calls: list[tuple[str, dict]] = []

        def core_call(method, path, body):
            calls.append((path, body))
            return 201, {"source_id": "src-rendered"}

        stub = mock.Mock()
        stub.render.side_effect = lambda url, out_dir, scroll_limit=None: self._capture(out_dir)
        stub.fetch.side_effect = AssertionError("the driver fell back to the served bytes")
        with TemporaryDirectory() as directory, \
                mock.patch.object(driver, "_load", lambda name, path: stub):
            record = driver.run_snapshot(
                "https://example.com/page", core_call, workspace=Path(directory), render=True
            )

        self.assertEqual(record["status"], "enqueued", record)
        self.assertEqual(record["mode"], "rendered")
        path, body = calls[0]
        self.assertEqual(path, "/api/v1/imports")
        self.assertEqual(base64.b64decode(body["content_base64"]).decode("utf-8"), PAGE,
                         "what is imported is the browser's reading, not the served bytes")
        self.assertEqual(record["sha256"], "r" * 64)
        self.assertEqual(record["served_sha256"], "s" * 64)
        self.assertEqual(record["title"], "rendered proof")
        self.assertEqual(record["scroll"], {"scrolls": 2, "height_stabilized": True})

    def test_a_refused_render_is_recorded_as_a_failure_with_no_source(self):
        class Refuses:
            @staticmethod
            def render(url, out_dir, scroll_limit=None):
                raise RuntimeError("render engine missing: chromium could not be launched")

            @staticmethod
            def fetch(url, out_dir):
                raise AssertionError("the driver fell back to the served bytes")

        with TemporaryDirectory() as directory, \
                mock.patch.object(driver, "_load", lambda name, path: Refuses()):
            record = driver.run_snapshot(
                "https://example.com/page", lambda *_a: (201, {}), workspace=Path(directory), render=True
            )

        self.assertEqual(record["status"], "failed")
        self.assertIsNone(record["source_id"])
        self.assertIn("render engine missing", record["error"])


class RealBrowserTests(unittest.TestCase):
    """The claim itself, against the browser this host actually has."""

    @classmethod
    def setUpClass(cls):
        try:
            import playwright.sync_api  # noqa: F401
        except ImportError as exc:
            raise unittest.SkipTest(f"playwright is not installed here: {exc}") from exc
        cls.server = HTTPServer(("127.0.0.1", 0), _Handler)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.port = cls.server.server_address[1]

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_a_scripted_body_is_present_in_the_render_and_absent_from_the_served_bytes(self):
        url = f"http://127.0.0.1:{self.port}/"
        with TemporaryDirectory() as box, \
                mock.patch.object(webpage, "public_addresses", return_value=["127.0.0.1"]):
            try:
                captured = webpage.render(url, Path(box))
            except RuntimeError as exc:
                if "render engine missing" in str(exc):
                    raise unittest.SkipTest(str(exc)) from exc
                raise

            served = (Path(box) / "snapshot.html").read_text(encoding="utf-8")
            rendered = Path(captured["rendered"]["path"]).read_text(encoding="utf-8")
            text = Path(captured["rendered"]["text_path"]).read_text(encoding="utf-8")

        self.assertIn(SERVED_MARKER, served)
        self.assertNotIn(SCRIPTED_MARKER, served,
                         "the served document must not already carry the scripted text")
        self.assertIn(SCRIPTED_MARKER, rendered)
        self.assertIn(SCRIPTED_MARKER, text)
        self.assertEqual(captured["title"], "rendered proof")
        params = captured["loss_receipt"]["params"]
        self.assertFalse(params["served_vs_rendered"]["same_digest"],
                         "a render that produced the same bytes rendered nothing")
        self.assertTrue(params["browser"].startswith("chromium "))
        self.assertIn("scrolls", params["scroll"])


if __name__ == "__main__":
    unittest.main()
