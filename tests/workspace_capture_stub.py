from __future__ import annotations


def capture_web_stub(content: str, engine: str = "test"):
    """Build a raw-first web capture seam for deterministic workspace tests.

    The production boundary persists the original response before creating a
    research graph.  Tests that use illustrative URLs must exercise that same
    boundary without making network requests.
    """
    raw_html = f"<html><body>{content}</body></html>".encode("utf-8")

    def capture(url, *, raw_store):
        original = raw_store.store_original(raw_html, url, mime_type="text/html")
        return {
            "receipt": {
                "final_url": url,
                "raw_hash": original.sha256,
                "engine": engine,
            },
            # A real extractor associates the capture with its final source.
            # Keeping that provenance in the deterministic body prevents two
            # illustrative URLs from being mistaken for one replayed document.
            "text": f"{content}\n\nSource: {url}",
        }

    return capture
