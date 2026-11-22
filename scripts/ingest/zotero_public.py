"""Read selected public Zotero Web API v3 objects, their child records and collections."""

from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request


class PublicGroup:
    def __init__(self, group: int, page_size: int = 50):
        if group < 1 or not 1 <= page_size <= 100:
            raise ValueError("use a positive public group ID and a page size of 1 to 100")
        self.group = group
        self.page_size = page_size
        self.base = f"https://api.zotero.org/groups/{group}/"

    def _get(self, url, save_source):
        request = urllib.request.Request(url, headers={"Zotero-API-Version": "3", "User-Agent": "AAOS-bibliography/0.6.14"})
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read()
            headers = response.headers
        data = json.loads(raw)
        source = save_source("zotero-" + urllib.parse.urlsplit(url).path.strip("/").replace("/", "-") + ".json", raw)
        origin = {"source_id": source["source_id"], "sha256": source["sha256"], "url": url,
                  "api_version": headers.get("Zotero-API-Version"), "library_version": headers.get("Last-Modified-Version")}
        return data, origin, headers.get("Link", "")

    def _pages(self, endpoint, params, save_source):
        url = self.base + endpoint + "?" + urllib.parse.urlencode({**params, "limit": self.page_size})
        visited = set()
        while url:
            if url in visited or not url.startswith(self.base):
                raise ValueError("Zotero returned an invalid pagination link for the selected library")
            visited.add(url)
            data, origin, links = self._get(url, save_source)
            if not isinstance(data, list):
                raise ValueError("Zotero did not return an object page")
            yield data, origin
            match = re.search(r'<([^>]+)>;\s*rel="next"', links)
            url = match.group(1) if match else None

    def capture(self, keys, collection, save_source):
        """Keep original API responses as Core sources; attachment records describe file availability."""
        if bool(keys) == bool(collection):
            raise ValueError("select item keys or one collection")
        selected = list(dict.fromkeys(keys or [collection]))
        if not all(re.fullmatch(r"[A-Z0-9]{8}", key) for key in selected):
            raise ValueError("Zotero item and collection keys have eight uppercase letters or digits")
        pages, records, expected, collections = [], [], {}, {}
        if collection:
            for rows, page in self._pages(f"collections/{collection}/items/top", {"include": "data"}, save_source):
                pages.append(page)
                expected.update((row["key"], row["version"]) for row in rows)
        else:
            expected = dict.fromkeys(selected)

        def collect(key):
            pending = [key]
            while pending:
                current = pending.pop()
                if current in collections:
                    continue
                row, origin, _ = self._get(self.base + "collections/" + current, save_source)
                data = row["data"]
                collections[current] = {"key": row["key"], "version": row["version"], "name": data["name"],
                                        "parent": data.get("parentCollection") or None, **origin}
                if collections[current]["parent"]:
                    pending.append(collections[current]["parent"])

        if collection:
            collect(collection)
        for key, version in expected.items():
            row, origin, _ = self._get(self.base + "items/" + key + "?include=data,csljson", save_source)
            if row["key"] != key or (version is not None and row["version"] != version):
                raise ValueError(f"Zotero item {key} changed during capture; retry this selection")
            if row["data"].get("parentItem") or row["data"].get("itemType") in {"attachment", "note", "annotation"}:
                if collection:
                    records.append({"record": row, "origin": origin, "excluded": "not a top-level bibliography record"})
                    continue
                raise ValueError(f"select the bibliographic parent of Zotero item {key}")
            for collection_key in row["data"].get("collections", []):
                collect(collection_key)
            children = []
            if row.get("meta", {}).get("numChildren"):
                for objects, child_page in self._pages("items/" + key + "/children", {"include": "data"}, save_source):
                    pages.append(child_page)
                    for child in objects:
                        data = child["data"]
                        if data.get("parentItem") != key:
                            raise ValueError("child record names a different parent item")
                        fields = {k: data[k] for k in ("itemType", "parentItem", "title", "url", "note", "linkMode",
                                  "contentType", "filename", "annotationType", "annotationText", "annotationComment") if k in data}
                        # Page size/order may change even when the child is the same revision.
                        # Keep the exact response in pages and address the child independently.
                        object_bytes = json.dumps(child, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
                        snapshot = save_source(f"zotero-{self.group}-{child['key']}-v{child['version']}.json", object_bytes)
                        children.append({**fields, "key": child["key"], "version": child["version"],
                                         "source_id": snapshot["source_id"], "source_sha256": snapshot["sha256"],
                                         "source_kind": "canonical_api_object", "source_url": child["links"]["self"]["href"]})
            # Preserve each relationship chain independently of other selected items.
            memberships = {}
            for member in row["data"].get("collections", []):
                cursor = member
                while cursor and cursor not in memberships:
                    memberships[cursor] = {field: value for field, value in collections[cursor].items() if field != "library_version"}
                    cursor = collections[cursor]["parent"]
            records.append({"record": row, "origin": origin, "children": sorted(children, key=lambda child: child["key"]),
                            "collections": memberships})
        return records, pages, collections
