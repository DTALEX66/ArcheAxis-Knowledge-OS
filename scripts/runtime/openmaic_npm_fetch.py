"""Fetch a fixed set of Owner-locked public npm archives under storage review.

No npm/pnpm process, package script, model, credential or provider is used.
The byte caps are enforced while reading and extracting; the growth projection
also includes the temporary copy, retained archive, extracted files and evidence.
"""
from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import http.client
import io
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import ssl
import stat
import sys
import tarfile
import time
import zipfile

import yaml

from scripts.release import tauri_portable_candidate as portable
from scripts.runtime import cargo_test_growth, dev


REPO = Path(__file__).resolve().parents[2]
OWNER_ZIP = REPO / ".project-local/archives/owner-inputs/20261101-learning-platform-sources/OpenMAIC-1.3.0.zip"
OWNER_ZIP_SHA256 = "7cea2a5850083bdc261114d8433daa6ea24c1c0157beae3939a2e9fac3a98f40"
LOCK_MEMBER = "OpenMAIC-1.3.0/pnpm-lock.yaml"
LOCK_SHA256 = portable.OPENMAIC_OWNER_LOCK_SHA256
PACKAGES = {
    "jsonrepair": {"version": "3.13.3", "sri": "sha512-BTznj0owIt2CBAH/LTo7+1I5pMvl1e1033LRl/HUowlZmJOIhzC0zbX5bxMngLkfT4WnzPP26QnW5wMr2g9tsQ=="},
    "nanoid": {"version": "5.1.14", "sri": "sha512-5c8l8kVzqpnDPaicbEop/fV0Q1w16FmbWtVhMqugTozAwYdlIQojWH5a/M7UfziFmGdQRrUdV+EPzc9Xng3VAQ=="},
}
PARTIAL_JSON = {
    "version": "0.1.7",
    "sri": "sha512-Njv/59hHaokb/hRUjce3Hdv12wd60MtM9Z5Olmn+nehe0QDAsRtRbJPvJ0Z91TusF0SuZRIvnM+S4l6EIP8leA==",
}
POSTCSS_VALUE_PARSER = {
    "version": "4.2.0",
    "sri": "sha512-1NNCs6uurfkVbeXG4S8JFT9t19m45ICnif8zWLd5oPSZ50QnwMfK+H3jv408d4jw/7Bttv5axS5IiHoLaVNHeQ==",
}
ES_MODULE_LEXER = {
    "version": "2.0.0",
    "sri": "sha512-5POEcUuZybH7IdmGsD8wlf0AI55wMecM9rVBTI/qEAy2c1kTOm3DjFYjrBdI2K3BaJjJYfYFeRtM0t9ssnRuxw==",
}
GEOMETRY_PACKAGES = {
    "entities": {"version": "6.0.1", "sri": "sha512-aN97NXWF6AWBTahfVOIrB/NShkzi5H7F9r1s9mD3cDj4Ko5f2qhhVoYMibXF7GlLveb/D2ioWay8lxI97Ven3g=="},
    "svg-pathdata": {"version": "8.0.0", "sri": "sha512-2Zqf5zsrX44Ws9y52EdHYrzGGnzyQG0jgREw+S3nP7zdx7QeH3QJonnGPvjtxPmYzU5mJMJ2YM+q2hUWGENWFg=="},
    "tinycolor2": {"version": "1.6.0", "sri": "sha512-XPaBkWQJdsf3pLKJV9p4qN/S+fm2Oj8AIPo1BTUhg5oxkvm9+SVEGFdhyOz7tTdUTfvxMiAs4sp6/eZO2Ew+pw=="},
}
PARSE5_PACKAGES = {
    "parse5": {"version": "8.0.1", "sri": "sha512-z1e/HMG90obSGeidlli3hj7cbocou0/wa5HacvI3ASx34PecNjNQeaHNo5WIZpWofN9kgkqV1q5YvXe3F0FoPw=="},
    "entities": {"version": "8.0.0", "sri": "sha512-zwfzJecQ/Uej6tusMqwAqU/6KL2XaB2VZ2Jg54Je6ahNBGNH6Ek6g3jjNCF0fG9EWQKGZNddNjU5F1ZQn/sBnA=="},
}
KATEX_PACKAGES = {
    "katex": {"version": "0.16.38", "sri": "sha512-cjHooZUmIAUmDsHBN+1n8LaZdpmbj03LtYeYPyuYB7OuloiaeaV6N4LcfjcnHVzGWjVQmKrxxTrpDcmSzEZQwQ=="},
    "commander": {"version": "8.3.0", "sri": "sha512-OkTL9umf+He2DZkUq8f8J9of7yL6RJKI24dVITBmNfZBmri9zYZQrKkuXiKhyfPSu8tUhnVBB1iKXevvnlR4Ww=="},
}
POSTCSS_PACKAGES = {
    "postcss": {"version": "8.5.23", "sri": "sha512-g50586zr4bZmwFiTlflMu8E0bDTb5I5gertgwAKmsdUlTQIhZtunzUlD1WSzwcVWPoAVpsrA6vlfCD7oXvRwgg=="},
    "nanoid": {"version": "3.3.19", "sri": "sha512-Y2tUNy4ouw6tq5oDSKeQYGOyhkUBhNOcGV/02KC+6kd9eDGqdZd++mjMiIDilrBYvjEnCYvVtsuHCuP+okSfug=="},
    "picocolors": {"version": "1.1.1", "sri": "sha512-xceH2snhtb5M9liqDsmEw56le376mTZkEX/jEb/RxNFyegNul7eNslCXP9FDj/Lcu0X8KEyMceP2ntpaHrDEVA=="},
    "source-map-js": {"version": "1.2.1", "sri": "sha512-UXWMKhLOwVKb728IUtQPXxfYU+usdybtUrK/8uGE8CQMvrhOpwvzDBwj0QhSL7MQc7vIsISBG8VQ8+IDQxpfQA=="},
}
POSTCSS_SELECTIONS = {"postcss": "postcss", "postcss-nanoid": "nanoid",
                      "postcss-picocolors": "picocolors", "postcss-source-map": "source-map-js"}
MAX_COMPRESSED = 16 * 1024 ** 2
MAX_UNPACKED = 64 * 1024 ** 2
MAX_TAR_STREAM = MAX_UNPACKED + 16 * 1024 ** 2
MAX_FILES = 4096
MAX_PACKAGE_JSON = 128 * 1024
MAX_LICENSE = 1024 * 1024
MAX_LOCK = 2 * 1024 ** 2
MAX_SECONDS = 1800
TEMP_EVIDENCE_ALLOWANCE = 32 * 1024 ** 2
# Two simultaneous copies of each compressed archive, one extracted copy per
# package, and run evidence. Every network/extraction writer enforces its cap.
PLAN_BYTES = ((len(PACKAGES) * (2 * MAX_COMPRESSED + MAX_UNPACKED)
               + TEMP_EVIDENCE_ALLOWANCE) * 5 + 3) // 4
PARTIAL_JSON_PLAN_BYTES = ((2 * MAX_COMPRESSED + MAX_UNPACKED
                            + TEMP_EVIDENCE_ALLOWANCE) * 5 + 3) // 4
POSTCSS_VALUE_PARSER_PLAN_BYTES = PARTIAL_JSON_PLAN_BYTES
ES_MODULE_LEXER_PLAN_BYTES = PARTIAL_JSON_PLAN_BYTES
GEOMETRY_PLAN_BYTES = ((len(GEOMETRY_PACKAGES) * (2 * MAX_COMPRESSED + MAX_UNPACKED)
                        + TEMP_EVIDENCE_ALLOWANCE) * 5 + 3) // 4
PARSE5_PLAN_BYTES = ((len(PARSE5_PACKAGES) * (2 * MAX_COMPRESSED + MAX_UNPACKED)
                      + TEMP_EVIDENCE_ALLOWANCE) * 5 + 3) // 4
KATEX_PLAN_BYTES = PARTIAL_JSON_PLAN_BYTES
POSTCSS_PLAN_BYTES = PARTIAL_JSON_PLAN_BYTES
ALLOWED_LICENSES = frozenset({"MIT", "ISC", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause"})
RESERVED_NAMES = frozenset({"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)),
                            *(f"LPT{i}" for i in range(1, 10))})


class FetchError(ValueError):
    pass


class UniqueLoader(yaml.SafeLoader):
    pass


def _unique_mapping(loader, node, deep=False):
    loader.flatten_mapping(node)
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in result:
            raise FetchError("duplicate YAML key in Owner lock")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _unique_mapping)


def _checked(path: Path) -> Path:
    """Keep lexical paths ordinary while checking every ancestor with native I/O."""
    raw = os.fspath(path)
    if raw.startswith("\\\\") or (re.match(r"^[A-Za-z]:[\\/]", raw) and raw[:1].upper() in {"E", "F"}):
        raise FetchError("protected drive or UNC npm path")
    normalized = Path(os.path.abspath(raw))
    if normalized.drive.upper() in {"E:", "F:"} or str(normalized).startswith("\\\\"):
        raise FetchError("protected drive or UNC npm path")
    for part in (*reversed(normalized.parents), normalized):
        try:
            info = os.lstat(portable.native(part))
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise FetchError("linked npm path rejected")
    return normalized


def _present(path: Path) -> bool:
    try:
        os.lstat(portable.native(_checked(path)))
    except FileNotFoundError:
        return False
    return True


def _hash_file(path: Path, algorithm: str) -> str:
    digest = hashlib.new(algorithm)
    with open(portable.native(_checked(path)), "rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _selection(selection: str) -> tuple[dict, int]:
    """Only explicitly selected, fixed Owner-lock dependencies."""
    if selection == "default":
        return {name: dict(row) for name, row in PACKAGES.items()}, PLAN_BYTES
    if selection == "partial-json":
        return {"partial-json": dict(PARTIAL_JSON)}, PARTIAL_JSON_PLAN_BYTES
    if selection == "postcss-value-parser":
        return {"postcss-value-parser": dict(POSTCSS_VALUE_PARSER)}, POSTCSS_VALUE_PARSER_PLAN_BYTES
    if selection == "es-module-lexer":
        return {"es-module-lexer": dict(ES_MODULE_LEXER)}, ES_MODULE_LEXER_PLAN_BYTES
    if selection == "geometry":
        return {name: dict(row) for name, row in GEOMETRY_PACKAGES.items()}, GEOMETRY_PLAN_BYTES
    if selection == "parse5":
        return {name: dict(row) for name, row in PARSE5_PACKAGES.items()}, PARSE5_PLAN_BYTES
    if selection in {"katex", "katex-commander"}:
        name = "katex" if selection == "katex" else "commander"
        return {name: dict(KATEX_PACKAGES[name])}, KATEX_PLAN_BYTES
    if selection in POSTCSS_SELECTIONS:
        name = POSTCSS_SELECTIONS[selection]
        return {name: dict(POSTCSS_PACKAGES[name])}, POSTCSS_PLAN_BYTES
    raise FetchError("unknown OpenMAIC npm selection")


def _locked_inputs(packages: dict | None = None) -> None:
    if packages is None:
        packages = PACKAGES
    source = _checked(OWNER_ZIP)
    if not os.path.isfile(portable.native(source)) or _hash_file(source, "sha256") != OWNER_ZIP_SHA256:
        raise FetchError("Owner ZIP identity differs")
    with zipfile.ZipFile(portable.native(source)) as archive:
        found = [info for info in archive.infolist() if info.filename == LOCK_MEMBER]
        if len(found) != 1 or found[0].file_size > MAX_LOCK or found[0].flag_bits & 1:
            raise FetchError("Owner lock member is missing, duplicated or exceeds its bound")
        raw = archive.read(found[0])
    if hashlib.sha256(raw).hexdigest() != LOCK_SHA256:
        raise FetchError("Owner lock identity differs")
    lock = yaml.load(raw, Loader=UniqueLoader)
    if not isinstance(lock, dict) or str(lock.get("lockfileVersion")) != "9.0":
        raise FetchError("Owner lock format is unsupported")
    importers = lock.get("importers", {})
    snapshots = lock.get("snapshots", {})
    if len(packages) == 1 and all(name in POSTCSS_PACKAGES and expected == POSTCSS_PACKAGES[name]
                                  for name, expected in packages.items()):
        declared = importers.get("packages/@openmaic/generation", {}).get("dependencies", {}).get("postcss", {})
        if declared.get("version") != POSTCSS_PACKAGES["postcss"]["version"]:
            raise FetchError("PostCSS generation importer differs from the Owner lock")
        for name, expected in POSTCSS_PACKAGES.items():
            key = f'{name}@{expected["version"]}'
            package = lock.get("packages", {}).get(key, {})
            wanted = ({"dependencies": {"nanoid": "3.3.19", "picocolors": "1.1.1", "source-map-js": "1.2.1"}}
                      if name == "postcss" else {})
            if (package.get("resolution") != {"integrity": expected["sri"]}
                    or package.get("peerDependencies") or not isinstance(snapshots.get(key), dict)
                    or snapshots[key] != wanted):
                raise FetchError("PostCSS dependency graph differs from the Owner lock")
        return
    if any(name in KATEX_PACKAGES for name in packages):
        if (len(packages) != 1 or any(name not in KATEX_PACKAGES or expected != KATEX_PACKAGES[name]
                                      for name, expected in packages.items())):
            raise FetchError("selected package is outside the fixed KaTeX graph")
        # Check the entire pinned parent/child graph even when only one archive
        # is selected, so the transitive package cannot be borrowed from an
        # unrelated importer or a different lock version.
        declared = importers.get("packages/@openmaic/generation", {}).get("dependencies", {}).get("katex", {})
        if declared.get("version") != KATEX_PACKAGES["katex"]["version"]:
            raise FetchError("KaTeX generation importer differs from the Owner lock")
        for name, expected in KATEX_PACKAGES.items():
            key = f'{name}@{expected["version"]}'
            package = lock.get("packages", {}).get(key, {})
            wanted = {"dependencies": {"commander": "8.3.0"}} if name == "katex" else {}
            if (package.get("resolution") != {"integrity": expected["sri"]}
                    or package.get("peerDependencies") or not isinstance(snapshots.get(key), dict)
                    or snapshots[key] != wanted):
                raise FetchError("KaTeX dependency graph differs from the Owner lock")
        return
    parse5_group = packages == PARSE5_PACKAGES
    for name, expected in packages.items():
        # Geometry has a separate importer in the owner's exact lock. A
        # similarly named package in another importer is not sufficient.
        importer_name = ("packages/@openmaic/geometry" if name in GEOMETRY_PACKAGES and not parse5_group
                         else "packages/@openmaic/generation")
        importer = importers.get(importer_name, {})
        version = expected["version"]
        key = f"{name}@{version}"
        declared = importer.get("dependencies", {}).get(name, {})
        package = lock.get("packages", {}).get(key, {})
        snapshot = snapshots.get(key)
        resolution = package.get("resolution", {})
        if parse5_group:
            # The second entities version is reachable only through this exact
            # generation -> parse5 -> entities snapshot edge, not geometry.
            snapshot_expected = {"dependencies": {"entities": "8.0.0"}} if name == "parse5" else {}
            valid_snapshot = snapshot == snapshot_expected and isinstance(snapshot, dict)
            valid_import = name == "entities" or declared.get("version") == version
        else:
            valid_snapshot = (isinstance(snapshot, dict)
                              and (name not in GEOMETRY_PACKAGES or snapshot == {})
                              and not snapshot.get("dependencies") and not snapshot.get("optionalDependencies"))
            valid_import = declared.get("version") == version
        if (not valid_snapshot or not valid_import or resolution != {"integrity": expected["sri"]}
                or package.get("peerDependencies")):
            raise FetchError("selected package is not the exact dependency-free or pinned-edge Owner lock entry")


def _tls_context() -> ssl.SSLContext:
    # Use only the Windows system trust stores: do not consult SSLKEYLOGFILE,
    # SSL_CERT_FILE, SSL_CERT_DIR, home configuration or a proxy environment.
    if os.name != "nt" or not hasattr(ssl, "enum_certificates"):
        raise FetchError("Windows system TLS trust is required")
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    loaded = 0
    for store in ("CA", "ROOT"):
        for certificate, encoding, trust in ssl.enum_certificates(store):
            if encoding == "x509_asn" and (trust is True or ssl.Purpose.SERVER_AUTH.oid in trust):
                context.load_verify_locations(cadata=certificate)
                loaded += 1
    if not loaded:
        raise FetchError("Windows system TLS trust is unavailable")
    return context


def _download(name: str, version: str, part: Path, expected_sri: str) -> dict:
    """Direct fixed-host HTTPS; no redirect, proxy, npm configuration or credentials."""
    if name == "partial-json":
        allowed = PARTIAL_JSON
    elif name == "postcss-value-parser":
        allowed = POSTCSS_VALUE_PARSER
    elif name == "es-module-lexer":
        allowed = ES_MODULE_LEXER
    elif name in POSTCSS_PACKAGES and POSTCSS_PACKAGES[name] == {"version": version, "sri": expected_sri}:
        allowed = POSTCSS_PACKAGES[name]
    elif name in GEOMETRY_PACKAGES or name in PARSE5_PACKAGES or name in KATEX_PACKAGES:
        candidates = (GEOMETRY_PACKAGES.get(name), PARSE5_PACKAGES.get(name), KATEX_PACKAGES.get(name))
        allowed = next((entry for entry in candidates if entry == {"version": version, "sri": expected_sri}), None)
    else:
        allowed = PACKAGES.get(name)
    if allowed != {"version": version, "sri": expected_sri}:
        raise FetchError("network package is outside the fixed Owner lock")
    path = f"/{name}/-/{name}-{version}.tgz"
    connection = http.client.HTTPSConnection("registry.npmjs.org", 443, timeout=30, context=_tls_context())
    deadline = time.monotonic() + MAX_SECONDS
    digest = hashlib.sha512()
    count = 0
    try:
        connection.request("GET", path, headers={"Accept": "application/octet-stream",
                                                  "Accept-Encoding": "identity",
                                                  "User-Agent": "aaos-locked-openmaic-fetch/1"})
        response = connection.getresponse()
        if response.status != 200 or response.getheader("Content-Encoding", "identity").lower() != "identity":
            raise FetchError("official package request failed or attempted a redirect")
        declared = response.getheader("Content-Length")
        if declared is not None and (not declared.isdigit() or int(declared) > MAX_COMPRESSED):
            raise FetchError("package Content-Length exceeds the fixed limit")
        with open(portable.native(_checked(part)), "xb") as output:
            while True:
                remaining_time = deadline - time.monotonic()
                if remaining_time <= 0:
                    raise FetchError("package download exceeded the fixed deadline")
                if connection.sock is not None:
                    connection.sock.settimeout(min(30, remaining_time))
                chunk = response.read(min(65536, MAX_COMPRESSED - count + 1))
                if not chunk:
                    break
                if count + len(chunk) > MAX_COMPRESSED:
                    raise FetchError("package archive exceeds the fixed compressed limit")
                output.write(chunk)
                digest.update(chunk)
                count += len(chunk)
        if declared is not None and count != int(declared):
            raise FetchError("package archive length differs from response")
        observed = "sha512-" + base64.b64encode(digest.digest()).decode("ascii")
        if observed != expected_sri:
            raise FetchError("package archive SRI mismatch")
        return {"archive_bytes": count, "sri": observed}
    finally:
        connection.close()


def _json_no_duplicates(raw: bytes) -> dict:
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise FetchError("duplicate package manifest key")
            result[key] = value
        return result
    def reject_constant(_value):
        raise FetchError("non-finite number in package manifest")
    def finite_float(text):
        value = float(text)
        if not math.isfinite(value):
            raise FetchError("non-finite number in package manifest")
        return value
    value = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs,
                       parse_constant=reject_constant, parse_float=finite_float)
    if not isinstance(value, dict):
        raise FetchError("package manifest is not an object")
    return value


def _relative_member(name: str) -> PurePosixPath:
    if name in {"package", "package/"}:
        return PurePosixPath(".")
    if not name.startswith("package/") or len(name) > 1024 or "\\" in name or "\0" in name:
        raise FetchError("package archive path is invalid")
    relative = PurePosixPath(name[len("package/"):])
    if not relative.parts or len(relative.parts) > 64 or relative.is_absolute():
        raise FetchError("package archive path is invalid")
    for part in relative.parts:
        stem = part.split(".", 1)[0].upper()
        private = part.casefold()
        if (part in {"", ".", ".."} or len(part) > 255
                or any(ord(char) < 32 or char in '<>:"|?*' for char in part)
                or part.endswith((".", " "))
                or stem in RESERVED_NAMES or private in {".git", ".codex", ".hermes", ".ssh", ".agents",
                                                           ".env", ".npmrc", ".netrc", "credentials", "credentials.toml"}
                or private.startswith(".env.")):
            raise FetchError("package archive contains a nonportable path")
    return relative


def _read_verified_archive(part: Path, expected_sri: str) -> bytes:
    with open(portable.native(_checked(part)), "rb") as source:
        data = source.read(MAX_COMPRESSED + 1)
    observed = "sha512-" + base64.b64encode(hashlib.sha512(data).digest()).decode("ascii")
    if len(data) > MAX_COMPRESSED or observed != expected_sri:
        raise FetchError("package archive changed after download or exceeds limit")
    return data


def _inspect_archive(compressed: bytes, name: str, version: str) -> tuple[bytes, list[dict], dict]:
    """Bound gzip expansion and validate all members without extracting them."""
    data = bytearray()
    with gzip.GzipFile(fileobj=io.BytesIO(compressed), mode="rb") as source:
        while True:
            chunk = source.read(min(65536, MAX_TAR_STREAM - len(data) + 1))
            if not chunk:
                break
            if len(data) + len(chunk) > MAX_TAR_STREAM:
                raise FetchError("package tar stream exceeds its expansion limit")
            data.extend(chunk)
    members = []
    seen = set()
    total = 0
    manifest = None
    licenses = []
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:") as archive:
        for member in archive:
            if len(members) >= MAX_FILES:
                raise FetchError("package member count exceeds limit")
            relative = _relative_member(member.name)
            identity = str(relative).casefold()
            if (identity in seen or member.type not in (tarfile.REGTYPE, tarfile.AREGTYPE, tarfile.DIRTYPE)
                    or (not relative.parts and not member.isdir())):
                raise FetchError("package contains duplicate paths or unsupported member types")
            seen.add(identity)
            if member.size < 0:
                raise FetchError("package member has an invalid length")
            total += member.size
            if total > MAX_UNPACKED:
                raise FetchError("package exceeds the extracted byte limit")
            if member.isdir():
                if member.size:
                    raise FetchError("package directory has nonzero content")
                members.append({"name": member.name, "path": str(relative), "kind": "directory", "bytes": 0})
                continue
            is_manifest = str(relative) == "package.json"
            is_license = len(relative.parts) == 1 and relative.name.casefold() in {
                "license", "license.md", "license.txt", "licence", "licence.md", "copying"}
            if is_manifest:
                if member.size > MAX_PACKAGE_JSON:
                    raise FetchError("package manifest exceeds limit")
            if is_license:
                if member.size == 0 or member.size > MAX_LICENSE:
                    raise FetchError("package license text is empty or exceeds limit")
            source = archive.extractfile(member)
            remaining = member.size
            digest = hashlib.sha256()
            captured = bytearray() if is_manifest or is_license else None
            while remaining:
                chunk = source.read(min(65536, remaining))
                if not chunk:
                    raise FetchError("package member is truncated during inspection")
                remaining -= len(chunk)
                digest.update(chunk)
                if captured is not None:
                    captured.extend(chunk)
            member_sha = digest.hexdigest()
            members.append({"name": member.name, "path": str(relative), "kind": "file",
                            "bytes": member.size, "sha256": member_sha})
            if is_manifest:
                manifest = _json_no_duplicates(bytes(captured))
            if is_license:
                if not bytes(captured).strip():
                    raise FetchError("package license text is incomplete")
                licenses.append({"path": str(relative), "sha256": member_sha, "bytes": member.size})
    if (not manifest or manifest.get("name") != name or manifest.get("version") != version
            or not isinstance(manifest.get("license"), str) or manifest.get("license") not in ALLOWED_LICENSES
            or (name == "partial-json" and manifest.get("license") != "MIT")
            or not licenses):
        raise FetchError("package identity or explicit supported license is unavailable")
    if (name in {"postcss-value-parser", "es-module-lexer", *GEOMETRY_PACKAGES, *PARSE5_PACKAGES, *KATEX_PACKAGES,
                 "postcss", "picocolors", "source-map-js"}
            or (name == "nanoid" and version == POSTCSS_PACKAGES["nanoid"]["version"])):
        # Require the same finite dependency graph in the archive manifest as
        # in the Owner lock, including the pinned parse5 and KaTeX edges.
        expected_dependencies = ({"entities": "^8.0.0"} if name == "parse5"
                                 else {"commander": "^8.3.0"} if name == "katex"
                                 else {"nanoid": "^3.3.16", "picocolors": "^1.1.1", "source-map-js": "^1.2.1"}
                                 if name == "postcss" else {})
        for field in ("dependencies", "optionalDependencies", "peerDependencies"):
            expected = expected_dependencies if field == "dependencies" else {}
            if ((field not in manifest and expected)
                    or (field in manifest and (not isinstance(manifest[field], dict) or manifest[field] != expected))):
                raise FetchError("package manifest is not the exact dependency-free or pinned-edge declaration")
        for field in ("bundleDependencies", "bundledDependencies"):
            if field in manifest and not (manifest[field] is False
                                          or (isinstance(manifest[field], list) and not manifest[field])):
                raise FetchError("package manifest is not dependency-free")
    return bytes(data), members, {"name": name, "version": version, "license": manifest["license"],
                                  "license_files": licenses, "unpacked_bytes": total,
                                  "members": len(members),
                                  "files": [{key: entry[key] for key in ("path", "bytes", "sha256")}
                                            for entry in members if entry["kind"] == "file"]}


def _extract(data: bytes, expected: list[dict], target: Path) -> None:
    target = _checked(target)
    os.mkdir(portable.native(target))
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:") as archive:
        for index, member in enumerate(archive):
            kind = "directory" if member.isdir() else "file" if member.isfile() else "unsupported"
            if (index >= len(expected) or member.name != expected[index]["name"]
                    or member.size != expected[index]["bytes"] or kind != expected[index]["kind"]):
                raise FetchError("package archive changed after inspection")
            path = _checked(target.joinpath(*_relative_member(member.name).parts))
            if member.isdir():
                os.makedirs(portable.native(path), exist_ok=True)
                continue
            os.makedirs(portable.native(_checked(path.parent)), exist_ok=True)
            path = _checked(path)
            source = archive.extractfile(member)
            remaining = member.size
            digest = hashlib.sha256()
            with open(portable.native(path), "xb") as output:
                while remaining:
                    chunk = source.read(min(65536, remaining))
                    if not chunk:
                        raise FetchError("package member is truncated")
                    output.write(chunk)
                    digest.update(chunk)
                    remaining -= len(chunk)
            if digest.hexdigest() != expected[index]["sha256"] or _hash_file(path, "sha256") != expected[index]["sha256"]:
                raise FetchError("extracted package member readback mismatch")
        if index + 1 != len(expected):
            raise FetchError("package member set changed after inspection")


def _retain_archive(compressed: bytes, destination: Path, sri: str) -> None:
    digest = hashlib.sha512(compressed).digest()
    if len(compressed) > MAX_COMPRESSED or "sha512-" + base64.b64encode(digest).decode("ascii") != sri:
        raise FetchError("archive changed before being retained")
    destination = _checked(destination)
    with open(portable.native(destination), "xb") as output:
        output.write(compressed)
    if _hash_file(destination, "sha512") != digest.hex():
        raise FetchError("retained archive verification failed")


def run(context: dict, selection: str = "default") -> list[dict]:
    packages, plan_bytes = _selection(selection)
    _locked_inputs(packages)
    paths = context["paths"]
    canonical = dev.layout(REPO, paths["run"].name)
    if any(paths[key] != canonical[key] for key in ("root", "run", "artifacts", "cache")):
        raise FetchError("foreign OpenMAIC npm cache or run")
    destination = _checked(paths["cache"] / "npm" / ("openmaic-owner-" + LOCK_SHA256) / paths["run"].name)
    scratch = _checked(paths["run"] / "tmp/openmaic-locked-npm")
    if _present(destination) or _present(scratch):
        raise FetchError("OpenMAIC npm target already exists; use a fresh run")
    state = portable._storage_pre(destination, plan_bytes, context, formal_npm=True)
    state.update({"producer": "openmaic-locked-npm-fetch/v1", "owner_zip_sha256": OWNER_ZIP_SHA256,
                  "owner_lock_sha256": LOCK_SHA256, "projection_scope": "enforced archive and extracted byte caps plus run allowance; not a filesystem quota",
                  "selection": selection, "packages": [], "network_scope": "direct official registry HTTPS; no scripts, auth, proxy or redirects; no operating-system network sandbox"})
    try:
        raw, identity = portable._identity(_checked(REPO / state["pre"]["path"]))
        if any(identity[key] != state["pre"][key] for key in ("path", "bytes", "sha256")):
            raise FetchError("npm pre-measurement identity changed")
        current = portable._footprint(json.loads(raw))
        cargo_test_growth._require_target_coverage(current, "cache/", destination)
        cargo_test_growth._require_target_coverage(current, "runs/", paths["run"])
        alternatives = {name: cargo_test_growth._alternative_review(current, state["baseline_report"], name, plan_bytes)
                        for name in ("runs/", "build/")}
        state["alternative_projected_reviews"] = alternatives
        if any(review["status"] == "REVIEW_REQUIRED"
               for review in [state["pre_review"], state["projected_review"], *alternatives.values()]):
            raise portable.GrowthReviewRequiredError("OpenMAIC npm storage growth requires review")
        _locked_inputs(packages)
        os.mkdir(portable.native(_checked(scratch)))
        os.makedirs(portable.native(_checked(destination.parent)), exist_ok=True)
        destination = _checked(destination)
        os.mkdir(portable.native(destination))
        state["copy_outcome"] = "STARTED"
        for name, expected in packages.items():
            version = expected["version"]
            part = scratch / f"{name}-{version}.tgz.part"
            download = _download(name, version, part, expected["sri"])
            compressed = _read_verified_archive(part, expected["sri"])
            data, members, description = _inspect_archive(compressed, name, version)
            _extract(data, members, destination / f"{name}-{version}")
            _retain_archive(compressed, destination / f"{name}-{version}.tgz", expected["sri"])
            state["packages"].append({**description, **download})
        state["copy_outcome"] = "VERIFIED_ARCHIVES_AND_LICENSE_FILES"
        return state["packages"]
    finally:
        portable._storage_post(state, sys.exc_info()[1])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", choices=("default", "partial-json", "postcss-value-parser", "es-module-lexer", "geometry", "parse5", "katex", "katex-commander", *POSTCSS_SELECTIONS), default="default")
    args = parser.parse_args()
    try:
        paths = cargo_test_growth._owned_run()
        context = {"paths": paths, "purpose": f"Obtain {args.selection} exact public Owner-locked OpenMAIC dependencies",
                   "sharing": "Project-local per-run verified npm cache", "retention_reason": "Reproducible local dependency and license evidence"}
        result = run(context, args.selection)
        print(json.dumps({"schema": "openmaic-locked-npm-fetch/v1", "packages": result,
                          "scripts_executed": False, "provider_execution": False}))
        return 0
    except (ValueError, TypeError, OSError, EOFError, http.client.HTTPException,
            zipfile.BadZipFile, tarfile.TarError, yaml.YAMLError) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
