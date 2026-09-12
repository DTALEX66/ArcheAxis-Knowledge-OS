"""Prepare a layered public-domain corpus for AXW-096A benchmarking.

Downloads Project Gutenberg public-domain books (txt.utf-8) into a
layered layout: small/ (1 book), medium/ (4 books), large/ (all books).
Records source/license/acquired-at/sha256 per sample in sources.json so
the corpus satisfies the baseline's provenance requirements. The corpus
lives under the project data dir (never committed).

Usage: python scripts/prepare_benchmark_corpus.py --output DIR
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# Public-domain titles on Project Gutenberg (English).
GUTENBERG_BOOKS: dict[int, str] = {
    84: "frankenstein-shelley",
    1342: "pride-and-prejudice-austen",
    11: "alice-in-wonderland-carroll",
    1661: "sherlock-adventures-doyle",
    98: "tale-of-two-cities-dickens",
    2701: "moby-dick-melville",
    1400: "great-expectations-dickens",
    74: "tom-sawyer-twain",
    76: "huck-finn-twain",
    43: "dracula-stoker",
}

# Public-domain Chinese titles on Project Gutenberg (classical novels).
GUTENBERG_BOOKS_ZH: dict[int, str] = {
    23962: "xiyouji",
    24264: "hongloumeng",
    24032: "rulingwaishi",
    24141: "jingshitongyan",
}


def _sha256_bytes(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def download_book(book_id: int, *, proxy: str | None) -> bytes:
    url = f"https://www.gutenberg.org/files/{book_id}/{book_id}-0.txt"
    handlers = [urllib.request.ProxyHandler({})]
    if proxy:
        handlers.append(urllib.request.ProxyHandler({"http": proxy, "https": proxy}))
    opener = urllib.request.build_opener(*handlers)
    request = urllib.request.Request(url, headers={"User-Agent": "archeaxis-benchmark-corpus/1.0"})
    with opener.open(request, timeout=60) as response:
        return response.read()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=".project-local/task-runtime/corpus", help="corpus root")
    parser.add_argument("--proxy", default=None, help="HTTP(S) proxy, e.g. 127.0.0.1:7890")
    parser.add_argument("--limit", type=int, default=None, help="max books to download (for testing)")
    args = parser.parse_args()

    output = Path(args.output)
    layers = {"small": output / "small", "medium": output / "medium", "large": output / "large"}
    for layer_dir in layers.values():
        layer_dir.mkdir(parents=True, exist_ok=True)

    sources: list[dict[str, object]] = []
    acquired_at = datetime.now(timezone.utc).isoformat()
    book_ids = list(GUTENBERG_BOOKS)
    if args.limit:
        book_ids = book_ids[: args.limit]

    for book_id in book_ids:
        name = GUTENBERG_BOOKS[book_id]
        target = layers["large"] / f"{book_id}-{name}.txt"
        if target.exists():
            print(f"cached {name}")
            sources.append(
                {
                    "id": book_id,
                    "title": name,
                    "language": "en",
                    "source": f"https://www.gutenberg.org/ebooks/{book_id}",
                    "license": "public-domain (Project Gutenberg)",
                    "acquired_at": acquired_at,
                    "sha256": _sha256_bytes(target.read_bytes()),
                }
            )
            continue
        print(f"downloading {book_id} {name} ...")
        try:
            blob = download_book(book_id, proxy=args.proxy)
        except Exception as exc:  # network is best-effort for the benchmark
            print(f"  SKIP {book_id}: {exc}")
            continue
        if len(blob) < 10_000:
            print(f"  SKIP {book_id}: suspiciously small ({len(blob)} bytes)")
            continue
        target.write_bytes(blob)
        sources.append(
            {
                "id": book_id,
                "title": name,
                "language": "en",
                "source": f"https://www.gutenberg.org/ebooks/{book_id}",
                "license": "public-domain (Project Gutenberg)",
                "acquired_at": acquired_at,
                "sha256": _sha256_bytes(blob),
            }
        )

    zh_ids = list(GUTENBERG_BOOKS_ZH)
    if args.limit:
        zh_ids = zh_ids[: max(0, args.limit - len(book_ids))]
    for book_id in zh_ids:
        name = GUTENBERG_BOOKS_ZH[book_id]
        target = layers["large"] / f"{book_id}-{name}.txt"
        if target.exists():
            print(f"cached {name} (zh)")
            sources.append(
                {
                    "id": book_id,
                    "title": name,
                    "language": "zh",
                    "source": f"https://www.gutenberg.org/ebooks/{book_id}",
                    "license": "public-domain (Project Gutenberg)",
                    "acquired_at": acquired_at,
                    "sha256": _sha256_bytes(target.read_bytes()),
                }
            )
            continue
        print(f"downloading {book_id} {name} (zh) ...")
        try:
            blob = download_book(book_id, proxy=args.proxy)
        except Exception as exc:
            print(f"  SKIP {book_id}: {exc}")
            continue
        if len(blob) < 10_000:
            print(f"  SKIP {book_id}: suspiciously small ({len(blob)} bytes)")
            continue
        target.write_bytes(blob)
        sources.append(
            {
                "id": book_id,
                "title": name,
                "language": "zh",
                "source": f"https://www.gutenberg.org/ebooks/{book_id}",
                "license": "public-domain (Project Gutenberg)",
                "acquired_at": acquired_at,
                "sha256": _sha256_bytes(blob),
            }
        )

    # Layering: small = first en book + first zh book, medium = first 4 en
    # + first 2 zh, large = all (identified by book id in the filename).
    def book_id_of(path: Path) -> int:
        return int(path.name.split("-", 1)[0])

    all_books = sorted((layers["large"]).glob("*.txt"))
    en_books = sorted(p for p in all_books if book_id_of(p) in GUTENBERG_BOOKS)
    zh_books = sorted(p for p in all_books if book_id_of(p) in GUTENBERG_BOOKS_ZH)
    small_books = list(en_books[:1]) + list(zh_books[:1])
    medium_books = list(en_books[:4]) + list(zh_books[:2])
    for layer_name, selected in (("small", small_books), ("medium", medium_books)):
        layer_dir = layers[layer_name]
        for book_path in selected:
            target = layer_dir / book_path.name
            if not target.exists():
                target.write_bytes(book_path.read_bytes())

    (output / "sources.json").write_text(
        json.dumps({"samples": sources, "acquired_at": acquired_at}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    for layer_name in ("small", "medium", "large"):
        layer_dir = layers[layer_name]
        total = sum(p.stat().st_size for p in layer_dir.glob("*.txt"))
        print(f"{layer_name}: {len(list(layer_dir.glob('*.txt')))} files, {total / 1024:.1f} KiB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
