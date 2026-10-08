"""Crosswalk of every open-source absorption entry onto one honest surface class.

Two vocabularies describe the same absorptions and were never joined:

* `scripts/audit/build_oss_reuse_inventory.py` joins the hand-reviewed
  `docs/current/OSS-REUSE-DECISIONS-20261008.json` (A-E verification tiers) with
  `docs/current/OSS-REUSE-VERIFICATION-20261008.json`.
* `docs/truth/CAPABILITY_ABSORPTION_REGISTRY.yaml` carries `allowed_absorption_modes`
  (DIRECT_DEPENDENCY / ALGORITHM_DONOR / UX_DONOR / ...) and a status enum pinned by
  `config/schemas/capability-absorption-registry.schema.json`.

The UI needs one answer per source: *what is this*, so absorption sources are not all rendered as
enable-able plugins. `surface_class` is exactly one of seven values and every derived field is
computed from files, never typed.

Why a sibling script instead of more lines in `build_oss_reuse_inventory.py`: that generator is
byte-pinned by `docs/current/OSS-REUSE-CROSSWALK-20261008.manifest.json`, and
`tests/workflow/test_oss_reuse_artifact_manifest.py` fails on `generator-drift` for any edit to it,
so extending it in place would rewrite a governance record that a different line owns. This artifact
also is not that artifact: the lossless 691-row payload stays out of Git by that manifest's
decision, while this is one row per absorption entry (~100 rows) and is committed precisely because
the UI reads it. The A-E tiers come from importing that module and calling its `build()`, so they
are the same numbers rather than a second opinion.

Derivation, one place per field:

`verification_tier`  the A-E category the lossless crosswalk carries for this entry's records. B is
                     promoted to A only by bound verification, never by a decision.
`absorption_mode`    the declared values kept per namespace (registry `absorption_mode`,
                     supply-chain `disposition`) plus `derived_mode` from the artifact shape.
`atlas_capability_id` joined two ways from files: the entry's dotted capability id appearing in
                     `config/capability-map.v1.json` `runtime_capabilities`, and the donor name
                     appearing in `docs/truth/CAPABILITY_ATLAS_V2.yaml` `dependencies`.
`map_state`          `config/capability-map.v1.json` for that atlas id.
`adoption`           donor-specific artifact. The same identifier/stub/mention discipline as
                     `scripts/audit/oss_disposition_evidence.py` (reused as a module), plus a
                     package-name probe that reads declared package names instead of any line that
                     contains the word, plus the bound external-resource index. That module's
                     per-row `evidence_state` is carried alongside as a *claim* to be checked.
`surface_class`      the ordered rules in `derive_surface_class`.

Three traps this refuses, all measured here rather than asserted:

* A grep hit is not an adoption. A donor must be a declared package name, a vendor root, a bound
  external resource, or an identifier in first-party code that does not mark itself unavailable.
  Tokens that are only the capability's own name or acronym are stripped before probing, which is
  how A008 Silero VAD loses a credit it never held: the VAD that runs is faster-whisper's.
* A legacy path is not the formal route. `media.transcribe.sensevoice` is absent from
  `services/python-workers/routes.json`, whose `media.transcribe` worker imports faster-whisper
  only, while the real SenseVoice code lives in `app/ingestion/asr_adapter.py`.
* The two id namespaces must not be merged. `CAP-00NN` (atlas) and `CAP-[A-Z0-9-]+` (absorption
  registry) overlap in *pattern* — `CAP-0010` satisfies the registry regex — so the atlas column is
  validated against the atlas's own id set, never against a regex alone.

Where the sources disagree the row keeps both values and a `conflict` reason; no winner is picked
silently.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

import yaml

ROOT_DEFAULT = Path(__file__).resolve().parents[2]

DECISIONS = "docs/current/OSS-REUSE-DECISIONS-20261008.json"
VERIFICATION = "docs/current/OSS-REUSE-VERIFICATION-20261008.json"
REGISTRY = "docs/truth/CAPABILITY_ABSORPTION_REGISTRY.yaml"
REGISTRY_SCHEMA = "config/schemas/capability-absorption-registry.schema.json"
LEDGER = "docs/truth/SUPPLY_CHAIN_LEDGER.json"
ATLAS = "docs/truth/CAPABILITY_ATLAS_V2.yaml"
CAPABILITY_MAP = "config/capability-map.v1.json"
ROUTES = "services/python-workers/routes.json"
EXTERNAL_RESOURCES = "config/environment/external-resources-index.json"
DISPOSITION = "docs/current/AAOS-OSS-DONOR-DISPOSITION-V2-20261002.json"
INVENTORY_SCRIPT = "scripts/audit/build_oss_reuse_inventory.py"
EVIDENCE_SCRIPT = "scripts/audit/oss_disposition_evidence.py"

OUTPUT_RELPATH = "docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json"
TS_RELPATH = "frontend/src/api/generated/absorption-surface.ts"

SURFACE_CLASSES = (
    "enableable_plugin",
    "absorbed_algorithm",
    "ux_donor",
    "format_spec",
    "base_dependency",
    "future_candidate",
    "not_adopted",
)

SURFACE_CLASS_MEANING = {
    "enableable_plugin": "Bound to a real capability lifecycle: an atlas capability id that exists "
                         "in docs/truth/CAPABILITY_ATLAS_V2.yaml, a state in "
                         "config/capability-map.v1.json, and donor-specific adoption evidence. The "
                         "only class the UI may render as an enable-able source.",
    "absorbed_algorithm": "The donor's behaviour is carried in product code, but no capability "
                          "lifecycle handle binds it (no atlas join, an undeclared route id, a "
                          "legacy-path binding, or a route served by a different engine). Real, "
                          "and not a plugin.",
    "ux_donor": "Carried in the client/UI layer or declared as a UX donor: it shapes an interaction "
                "instead of serving a capability route.",
    "format_spec": "A format/protocol/contract reference that was extracted rather than installed; "
                   "tier C means no runtime adoption is implied.",
    "base_dependency": "Substrate: a declared package, a vendored copy, a bound external tool, or "
                       "first-party core that the product runs on and does not expose as an "
                       "enable-able source.",
    "future_candidate": "Deferred: a stated value and demand trigger with no adoption record.",
    "not_adopted": "Not adopted for the stated role: tier E, REJECT-CORE/REVIEW-BLOCK with nothing "
                   "carried, or a claimed adoption whose donor artifact is absent.",
}

ATLAS_ID_PATTERN = re.compile(r"^CAP-[0-9]{4}$")
REGISTRY_ID_PATTERN = re.compile(r"^CAP-[A-Z][A-Z0-9-]+$")
TIER_RANK = {"A": 5, "B": 4, "C": 3, "D": 2, "E": 1}
RUNTIME_MODES = {"DIRECT_DEPENDENCY", "VENDORED_COMPONENT", "CONTRACT_ADAPTER", "PYTHON_WORKER",
                 "SIDECAR"}
NON_RUNTIME_MODES = {"ALGORITHM_DONOR", "UX_DONOR", "REFERENCE_ONLY", "SELF_BUILD_GAP"}
RUNTIME_DISPOSITIONS = {"CURRENT", "ADOPT", "SIDECAR", "ADOPT_PRODUCT_BASE"}
NON_RUNTIME_DISPOSITIONS = {"EVALUATE", "REFERENCE", "DEFER", "BENCHMARK", "REVIEW-BLOCK",
                            "REJECT-CORE"}
NOT_ADOPTED_DISPOSITIONS = {"REJECT-CORE", "REVIEW-BLOCK"}
CARRIED_ARTIFACTS = ("package_declared", "vendored", "imported_in_source", "pipeline_invoked",
                     "tool_invoked")
# A first-party code path that implements a capability for an external service (a REST donor) is
# absorbed by writing a client, not by adding a dependency.
FIRST_PARTY_CLIENT_MODES = {"CONTRACT_ADAPTER"}
ENABLEABLE_TIERS = {"A", "B"}
IMPLEMENTED_REGISTRY_STATUSES = {"integrated", "adapter", "provider"}


def _read_json(root: Path, relpath: str):
    return json.loads((root / relpath).read_text(encoding="utf-8"))


def norm(value: object) -> str:
    """Fold to a comparable identity: accent-stripped, lowercase, alphanumerics only."""
    folded = unicodedata.normalize("NFKD", str(value))
    stripped = "".join(char for char in folded if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]", "", stripped.casefold())


def donor_name(value: object) -> str:
    """The donor part of a display name: drop parentheticals/brackets and an owner prefix."""
    parts = donor_candidates(value)
    return parts[0] if parts else ""


def donor_candidates(value: object) -> list[str]:
    """Every donor a name can state, as reviewed text rather than as a guess.

    `FunASR / SenseVoice` names two donors, so a spaced slash splits into both. A tight `owner/repo`
    or URL is a path, so only its last segment is the donor. Parentheticals and brackets are
    commentary about the donor, not the donor.
    """
    text = re.sub(r"\s*[\(\[].*$", "", str(value or "").strip(), flags=re.DOTALL).strip()
    if not text:
        return []
    if " / " in text:
        parts: list[str] = []
        for piece in text.split(" / "):
            parts.extend(donor_candidates(piece))
        return parts
    if text.lower().startswith(("http://", "https://")):
        text = text.split("?")[0].rstrip("/").rsplit("/", 1)[-1]
    elif "/" in text:
        text = text.rsplit("/", 1)[-1]
    return [text.removesuffix(".git").strip()]


def github_repo(name: object) -> str | None:
    """The repo segment of a github.com/owner/repo url, which is the donor's package name."""
    text = str(name or "")
    match = re.match(r"^https?://github\.com/([^/?#]+)/([^/?#]+)", text)
    return match.group(2) if match else None


def name_tokens(value: object) -> list[str]:
    return [token for token in re.split(r"[^A-Za-z0-9]+", str(value or "")) if token]


def primary_key(value: object) -> str:
    return norm(donor_name(value))


def capability_stopwords(capability_label: object) -> set[str]:
    """Tokens (and the acronym) of a capability label: these cannot identify a donor.

    Derived from the row's own `capability` field, never hand-listed, so
    `voice-activity-detection` contributes {voice, activity, detection, vad}. Without this, the
    term `vad` matches `vad_filter=True` in faster-whisper's own call and credits Silero.
    """
    stop: set[str] = set()
    pieces = [token for token in name_tokens(capability_label) if token]
    for piece in pieces:
        stop.add(norm(piece))
    initials = "".join(piece[0] for piece in pieces)
    if len(pieces) >= 2:
        stop.add(norm(initials))
    stop.discard("")
    return stop


# ---------------------------------------------------------------------------------------------
# Artifact probing
# ---------------------------------------------------------------------------------------------

class ArtifactProbe:
    """Answers, for one donor's own name, whether this repository actually carries it."""

    def __init__(self, root: Path, evidence_module):
        self.root = root
        self.evidence = evidence_module
        if Path(evidence_module.REPO).resolve() != root:
            raise ValueError(f"{EVIDENCE_SCRIPT} is bound to {evidence_module.REPO}, not {root}")
        self.manifest_paths = self._manifest_paths()
        self.pipeline_paths = self._pipeline_paths()
        self.self_packages, self.self_prefixes = self._first_party_names()
        self.declared_packages = self._declared_packages()
        self.index_entries = self._index_entries()
        self.index_text = (root / EXTERNAL_RESOURCES).read_text(encoding="utf-8").casefold()

    def _first_party_names(self) -> tuple[set[str], set[str]]:
        """Names this repository declares for itself, so a donor is never credited to the product.

        "ArcheAxis Core Knowledge" otherwise matched the project's own crate names in uv.lock and
        read as an external dependency.
        """
        names: set[str] = set()
        pyproject = self.root / "pyproject.toml"
        if pyproject.is_file():
            match = re.search(r'^\s*name\s*=\s*"([^"]+)"', pyproject.read_text(encoding="utf-8"),
                              re.MULTILINE)
            if match:
                names.add(match.group(1))
        for cargo in sorted(self.root.glob("crates/*/Cargo.toml")):
            match = re.search(r'^\s*name\s*=\s*"([^"]+)"', cargo.read_text(encoding="utf-8"),
                              re.MULTILINE)
            if match:
                names.add(match.group(1))
        frontend = self.root / "frontend/package.json"
        if frontend.is_file():
            payload = json.loads(frontend.read_text(encoding="utf-8"))
            if payload.get("name"):
                names.add(payload["name"])
        prefixes = {norm(token) for name in names for token in name_tokens(name)}
        return {norm(name) for name in names}, {key for key in prefixes if len(key) >= 6}

    def _is_first_party(self, package_name: str) -> bool:
        key = norm(package_name)
        return key in self.self_packages or any(key.startswith(prefix) for prefix in self.self_prefixes)

    # -- scopes -------------------------------------------------------------------------------
    def _manifest_paths(self) -> list[Path]:
        return [self.root / rel for rel in [*self.evidence.MANIFESTS, "Cargo.lock"]
                if (self.root / rel).is_file()]

    def _pipeline_paths(self) -> list[Path]:
        """A tool a pipeline invokes is absorbed without appearing in any manifest.

        `scripts/audit/oss_disposition_evidence.py` established this scope for pip-audit and
        gitleaks, which run as CI gates and are in no dependency graph.
        """
        paths = []
        for glob in self.evidence.PIPELINE_GLOBS:
            paths.extend(sorted(self.root.glob(glob)))
        return [path for path in paths if path.is_file()]

    def _declared_packages(self) -> dict[str, list[str]]:
        """Package names the product declares, read from the declaration position, not from prose.

        Whole-word line matching credited donors for the word `community` or `browsers` appearing in
        a lockfile URL. A declared package name is a name, so names are extracted as names.
        """
        found: dict[str, list[str]] = defaultdict(list)

        def add(name: str, location: str) -> None:
            key = norm(name)
            if key and not self._is_first_party(name):
                found[key].append(location)

        for path in self.manifest_paths:
            relative = path.relative_to(self.root).as_posix()
            text = path.read_text(encoding="utf-8", errors="surrogateescape")
            lines = text.splitlines()
            if relative.endswith("Cargo.lock") or relative.endswith("uv.lock"):
                for number, line in enumerate(lines, start=1):
                    match = re.match(r'\s*name\s*=\s*"([^"]+)"', line)
                    if match:
                        add(match.group(1), f"{relative}:{number}")
            elif relative.endswith(("pyproject.toml", "requirements.txt")):
                patterns = (re.compile(r'^\s*"([A-Za-z0-9][A-Za-z0-9_.\-]*)\s*[<>=!~;\[]'),
                            re.compile(r'^\s*([A-Za-z0-9][A-Za-z0-9_.\-]*)\s*[<>=!~;]'))
                for number, line in enumerate(lines, start=1):
                    for pattern in patterns:
                        match = pattern.match(line)
                        if match:
                            add(match.group(1), f"{relative}:{number}")
                            break
            elif relative.endswith("package.json") or relative.endswith("package-lock.json"):
                found_names = self._npm_package_names(text, relative)
                for name, location in found_names:
                    add(name, location)
            else:
                continue
        return dict(found)

    def _npm_package_names(self, text: str, relative: str) -> list[tuple[str, str]]:
        """Package names as declared keys, not as words that happen to appear in a lockfile."""
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return []
        pairs: list[tuple[str, str]] = []
        for section in ("dependencies", "devDependencies", "optionalDependencies"):
            for name in (payload.get(section) or {}):
                pairs.append((name, f"{relative}:{section}"))
        for key in (payload.get("packages") or {}):
            if key:
                pairs.append((key.rsplit("node_modules/", 1)[-1], f"{relative}:packages"))
        return pairs

    def _index_entries(self) -> dict[str, list[str]]:
        """Names of the entries in the external resource index, tokenised for matching."""
        payload = _read_json(self.root, EXTERNAL_RESOURCES)
        names: set[str] = set()

        def walk(node):
            if isinstance(node, dict):
                for key, value in node.items():
                    if key in {"id", "name", "tool", "binary", "capability"} and isinstance(value, str):
                        names.add(value)
                    else:
                        walk(value)
            elif isinstance(node, list):
                for value in node:
                    walk(value)

        walk(payload.get("entries", payload))
        found: dict[str, list[str]] = {}
        for name in names:
            tokens = {norm(token) for token in name_tokens(name) if len(norm(token)) >= 4}
            tokens.add(norm(name))
            for token in tokens - {""}:
                found.setdefault(token, []).append(name)
        return found

    # -- probes -------------------------------------------------------------------------------
    @staticmethod
    def _pattern(term: str) -> re.Pattern[str]:
        return re.compile(rf"(?<![A-Za-z0-9]){re.escape(term)}(?![A-Za-z0-9])", re.IGNORECASE)

    def package_declared(self, terms: list[str]) -> dict[str, list[str]]:
        found: dict[str, list[str]] = {}
        for term in terms:
            for key in {norm(term), norm(term).replace("-", "")}:
                for location in self.declared_packages.get(key, []):
                    if location not in found.setdefault(term, []):
                        found[term].append(location)
        return {term: locations[:3] for term, locations in found.items()}

    def pipeline_invoked(self, terms: list[str]) -> dict[str, list[str]]:
        """A tool the pipeline runs is absorbed even though no manifest names it."""
        return self.named_in_files(terms, self.pipeline_paths)

    def direct_declaration(self, hits: dict[str, list[str]]) -> bool:
        """True when the donor is declared by the product itself, not only resolved in a lockfile."""
        direct = {"pyproject.toml", "requirements.txt", "frontend/package.json"}
        return any(location.split(":", 1)[0] in direct
                   for locations in hits.values() for location in locations)

    def index_bound(self, terms: list[str]) -> dict[str, list[str]]:
        found: dict[str, list[str]] = {}
        for term in terms:
            candidates = {norm(term)} | {norm(token) for token in name_tokens(term)}
            hits = sorted({name for key in candidates if len(key) >= 4
                           for name in self.index_entries.get(key, [])})
            if hits:
                found[term] = hits[:3]
        return found

    def named_in_files(self, terms: list[str], files: list[Path]) -> dict[str, list[str]]:
        found: dict[str, list[str]] = {}
        for term in terms:
            pattern = self._pattern(term)
            hits = []
            for path in files:
                try:
                    text = path.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue
                for number, line in enumerate(text.splitlines(), start=1):
                    if pattern.search(line):
                        hits.append(f"{path.relative_to(self.root).as_posix()}:{number}")
                        break
            if hits:
                found[term] = hits[:3]
        return found

    def route_workers(self, route_paths: list[str]) -> list[Path]:
        base = self.root / "services" / "python-workers"
        return [base / rel for rel in route_paths if (base / rel).is_file()]

    def probe(self, terms: list[str]) -> dict:
        """The donor-specific artifact shape, from files only."""
        if not terms:
            return {"artifact": "NO_DONOR_TERM", "carried": False, "terms": [], "hits": {},
                    "detail": "no donor-specific term survived capability-stopword filtering, so "
                              "nothing can be credited to this donor by name"}
        packages = self.package_declared(terms)
        pipelines = self.pipeline_invoked(terms)
        # `vendor_hits` answers for every term it is given, including an empty list; keeping the
        # empties made a non-empty dict, which read as "this donor is vendored" for all 68 rows.
        vendored = {term: hits for term, hits in self.evidence.vendor_hits(terms).items() if hits}
        code, stub, mention = self.evidence.source_hits(terms)
        index_hits = self.index_bound(terms)
        # A bound tool is credited by the resource-entry name the product resolves, because that is
        # the string the worker actually asks for (`_declared_path("zulu-jre")`), not the vendor's
        # marketing name.
        entry_names = sorted({name for names in index_hits.values() for name in names})
        bound = self.named_in_files(entry_names, self._tool_scope_files()) if entry_names else {}
        tool: dict[str, list[str]] = {}
        for term, names in index_hits.items():
            located = [hit for name in names for hit in bound.get(name, [])]
            if located:
                tool[term] = [*names[:2], *located[:2]]
        hits = {"package_declared": packages, "pipeline_invoked": pipelines, "vendored": vendored,
                "imported_in_source": code, "tool_invoked": tool,
                "stub_only": stub, "mentioned_only": mention}
        hits = {bucket: value for bucket, value in hits.items() if value}
        artifact = "NONE"
        if packages:
            artifact = "package_declared"
        elif vendored:
            artifact = "vendored"
        elif code:
            artifact = "imported_in_source"
        elif pipelines:
            artifact = "pipeline_invoked"
        elif tool:
            artifact = "tool_invoked"
        elif stub:
            artifact = "stub_only"
        elif mention:
            artifact = "mentioned_only"
        elif index_hits:
            artifact = "indexed_unbound"
        return {"artifact": artifact, "carried": artifact in CARRIED_ARTIFACTS, "terms": terms,
                "hits": hits, "bound_resource_entries": sorted(bound) if bound else [],
                "direct_declaration": self.direct_declaration(packages)}

    def _tool_scope_files(self) -> list[Path]:
        files: list[Path] = []
        for root_name in self.evidence.SOURCE_ROOTS:
            base = self.root / root_name
            if not base.is_dir():
                continue
            for path in sorted(base.rglob("*.py")):
                if any(part in self.evidence.SKIP_DIRS for part in path.relative_to(self.root).parts):
                    continue
                files.append(path)
        return files


# ---------------------------------------------------------------------------------------------
# The two id namespaces, the atlas join and the declared routes
# ---------------------------------------------------------------------------------------------

class CapabilityJoin:
    def __init__(self, root: Path):
        atlas = yaml.safe_load((root / ATLAS).read_text(encoding="utf-8"))
        mapping = _read_json(root, CAPABILITY_MAP)
        routes = _read_json(root, ROUTES)["routes"]
        self.atlas_ids = [entry["capability_id"] for entry in atlas["capabilities"]]
        if len(self.atlas_ids) != len(set(self.atlas_ids)):
            raise ValueError("atlas capability ids must be unique")
        bad = [cap for cap in self.atlas_ids if not ATLAS_ID_PATTERN.match(cap)]
        if bad:
            raise ValueError(f"atlas ids outside ^CAP-[0-9]{{4}}$: {bad}")
        self.map_state = {entry["capability_id"]: entry["state"] for entry in mapping["capabilities"]}
        self.map_runtime = {entry["capability_id"]: list(entry["runtime_capabilities"])
                           for entry in mapping["capabilities"]}
        owner: dict[str, list[str]] = defaultdict(list)
        for cap_id, capabilities in self.map_runtime.items():
            for runtime in capabilities:
                owner[runtime].append(cap_id)
        self.runtime_owner = dict(owner)
        dependencies: dict[str, list[str]] = defaultdict(list)
        for entry in atlas["capabilities"]:
            for dependency in entry.get("dependencies") or []:
                # Indexed by the whole donor name and by its parts, so `Crossref REST` reaches the
                # atlas dependency `Crossref` without any substring guessing.
                keys = {primary_key(dependency)} | {norm(token) for token in donor_candidates(dependency)}
                keys |= {norm(token) for token in name_tokens(dependency) if len(norm(token)) >= 4}
                for key in keys - {""}:
                    dependencies[key].append(entry["capability_id"])
        self.atlas_dependency = {key: sorted(set(value)) for key, value in dependencies.items() if key}
        self.routes = routes

    def by_runtime_capability(self, capability_id: str | None) -> list[str]:
        return list(self.runtime_owner.get(capability_id, [])) if capability_id else []

    def by_donor_name(self, keys: set[str]) -> list[str]:
        found: list[str] = []
        for key in keys:
            found.extend(self.atlas_dependency.get(key, []))
        return sorted(set(found))

    def declared_prefixes(self) -> set[str]:
        return {capability.split(".", 1)[0] for capability in self.routes}


# ---------------------------------------------------------------------------------------------
# Entry grouping: three sources, joined only on a donor's own normalized name
# ---------------------------------------------------------------------------------------------

class Group:
    def __init__(self, key: str):
        self.key = key
        self.decision: dict | None = None
        self.ledger: dict | None = None
        self.registry: dict | None = None
        self.disposition_archive: list[dict] = []
        self.tiers: set[str] = set()
        self.authored: set[str] = set()
        self.tier_scopes: set[str] = set()
        self.capability_ids: set[str] = set()
        self.names: list[str] = []

    def add_name(self, value: object) -> None:
        text = str(value or "").strip()
        if text and text not in self.names:
            self.names.append(text)


class Folder:
    def __init__(self):
        self.groups: dict[str, Group] = {}
        self.by_key: dict[str, Group] = {}

    def new(self, key: str) -> Group:
        group = self.groups.setdefault(key, Group(key))
        self.by_key.setdefault(key, group)
        return group

    def resolve(self, keys: set[str], label: str) -> Group:
        """One group per donor; a name shared by two donors is refused, not merged."""
        touched = sorted(key for key in keys if key in self.by_key)
        distinct = list(dict.fromkeys(self.by_key[key] for key in touched))
        if len(distinct) > 1:
            raise ValueError(f"{label} would merge distinct donors {distinct[0].key} and "
                             f"{[group.key for group in distinct[1:]]} via {sorted(keys)}")
        if distinct:
            target = distinct[0]
        else:
            target = self.new(sorted(keys)[0])
        for key in keys:
            self.by_key.setdefault(key, target)
        return target


def donor_keys(value: object) -> set[str]:
    """Identity keys a name states: each donor part, normalized. `None` states nothing."""
    if value is None:
        return set()
    return {norm(candidate) for candidate in donor_candidates(value) if norm(candidate)}


def build_groups(root: Path, probe: ArtifactProbe, inventory: dict) -> list[Group]:
    decisions = _read_json(root, DECISIONS)
    ledger = _read_json(root, LEDGER)
    registry_document = yaml.safe_load((root / REGISTRY).read_text(encoding="utf-8"))
    disposition = _read_json(root, DISPOSITION)
    folder = Folder()
    archive_by_id = {row["id"]: row for row in disposition["supply_chain_47_as_archived"]}
    archive_by_capability = {row["capability_id"]: row
                            for row in disposition["capability_absorption_11_as_archived"]}

    for item in decisions["decisions"]:
        keys = donor_keys(item["canonical_name"])
        for alias in item.get("aliases", []):
            keys |= donor_keys(alias)
        group = folder.resolve(keys or {norm(item["canonical_name"])},
                              f"decision {item['canonical_name']}")
        if group.decision is not None:
            raise ValueError(f"duplicate decision row for {group.key}")
        group.decision = item
        group.add_name(item["canonical_name"])
        for alias in item.get("aliases", []):
            group.add_name(alias)
        if item.get("capability_id"):
            group.capability_ids.add(item["capability_id"])

    for row in ledger["components"]:
        keys = set(donor_keys(row["name"]))
        repo = github_repo(row.get("canonical_url"))
        if repo:
            keys.add(norm(repo))
        group = folder.resolve(keys or {norm(row["id"])}, f"supply-chain row {row['id']}")
        if group.ledger is not None and group.ledger["id"] != row["id"]:
            raise ValueError(f"supply-chain rows {group.ledger['id']} and {row['id']} are both "
                             f"donor {group.key}")
        group.ledger = row
        group.add_name(row["name"])
        if row.get("capability"):
            group.capability_ids.add(row["capability"])
        if archive := archive_by_id.get(row["id"]):
            group.disposition_archive.append(archive)

    for entry in registry_document["entries"]:
        # Only `upstream_project` names a donor. `legacy_donor` is a shared internal label ("legacy
        # knowledge stores" appears on several entries) and joining on it would merge unrelated
        # donors into one row.
        keys = donor_keys(entry.get("upstream_project"))
        group = folder.resolve(keys or {norm(entry["capability_id"])},
                              f"registry entry {entry['capability_id']}")
        if group.registry is not None:
            raise ValueError(f"registry entries collide on {group.key}")
        group.registry = entry
        group.add_name(entry.get("upstream_project") or entry["capability_name"])
        group.add_name(entry["capability_name"])
        if archive := archive_by_capability.get(entry["capability_id"]):
            group.disposition_archive.append(archive)
            group.add_name(archive.get("upstream_or_owner"))

    # Tiers are read back from the lossless crosswalk's own records, matched on reviewed names.
    for record in inventory["records"]:
        keys = donor_keys(record["canonical_name"]) | donor_keys(record["original_name"])
        for key in keys:
            group = folder.by_key.get(key)
            if group is None:
                continue
            group.tiers.add(record["category"])
            if record["match_basis"] == "explicit_reviewed_alias":
                group.authored.add(record["category"])
            group.tier_scopes.add(record["scope"])
            if record.get("capability_id"):
                group.capability_ids.add(record["capability_id"])
    return sorted(folder.groups.values(), key=lambda group: group.key)


# ---------------------------------------------------------------------------------------------
# Term selection and surface class
# ---------------------------------------------------------------------------------------------

def entry_terms(group: Group, probe: ArtifactProbe, curated: list[str],
                stopwords: set[str]) -> list[str]:
    """Names that identify this donor, and nothing else.

    Kept deliberately narrow: the donor's own name as reviewed text, its `owner/repo` slug, and the
    hand-reviewed evidence terms the donor-disposition check curates per supply-chain row. Broad
    token expansion credited donors for English words (`community`, `runtime`, `browser`, `python`)
    that appear in lockfiles for unrelated reasons, and the product's own name credited
    first-party entries as external dependencies.
    """
    raw: list[str] = []
    for name in [*group.names, *curated]:
        candidates = list(donor_candidates(name))
        repo = github_repo(name)
        if repo:
            candidates.append(repo)
        for candidate in candidates:
            for variant in (candidate, candidate.replace("_", "-"), candidate.replace("-", "_")):
                key = norm(variant)
                if not key or not variant.isascii() or key in stopwords:
                    continue
                if probe._is_first_party(variant):
                    continue
                if len(key) < 4:
                    continue
                if variant not in raw:
                    raw.append(variant)
    return raw


def promote(category: str, capability_id: str | None, verification: dict) -> str:
    """The generator's own B-to-A promotion, mirrored so a reviewed decision with no source row
    still gets a tier. tests/test_oss_absorption_crosswalk.py pins that the mirror agrees with
    `build_oss_reuse_inventory.build()` wherever both see the same entry."""
    proof = (verification.get("capabilities") or {}).get(capability_id or "", {})
    if category == "B" and proof.get("status") == "PASS" and proof.get("level") in {"INTEGRATED",
                                                                                  "REAL"} and \
            proof.get("entry") and proof.get("assertions"):
        return "A"
    return category


def is_first_party(group: Group, probe: ArtifactProbe) -> bool:
    """Whether the "donor" is this product itself rather than an external source."""
    if group.registry is not None and not group.registry.get("upstream_project"):
        return True
    for name in group.names:
        if norm(name) in probe.self_packages:
            return True
        if any(norm(token) in probe.self_prefixes for token in name_tokens(name)):
            return True
    return False


def derive_mode(adoption: dict, registry_mode: str | None, has_client: bool) -> str:
    """A mode in the registry's own vocabulary, computed from the artifact shape."""
    if registry_mode:
        return registry_mode
    artifact = adoption["artifact"]
    if artifact == "package_declared":
        return "DIRECT_DEPENDENCY"
    if artifact == "vendored":
        return "VENDORED_COMPONENT"
    if artifact in ("tool_invoked", "pipeline_invoked"):
        # No registry mode says "a CLI the pipeline runs"; SIDECAR (separate compliance path, not a
        # core dependency) is the nearest, and `adoption.artifact` keeps the precise shape.
        return "SIDECAR"
    if artifact == "imported_in_source":
        return "CONTRACT_ADAPTER" if has_client else "PYTHON_WORKER"
    if artifact in ("NONE", "NO_DONOR_TERM", "indexed_unbound", "mentioned_only"):
        return "REFERENCE_ONLY"
    return "SELF_BUILD_GAP"


def route_binding(join: CapabilityJoin, probe: ArtifactProbe, entry: dict) -> dict:
    """Whether the donor is bound to a declared capability lifecycle, and if not, the reason."""
    capability_ids = sorted(entry["_capability_ids"])
    adoption = entry["adoption"]
    atlas_id = entry["atlas_capability_id"]
    state = entry["map_state"]
    named = [cap for cap in capability_ids if cap in join.routes]
    legacy = [cap for cap in capability_ids if cap.startswith("legacy.")]
    prefixes = set()
    for cap in capability_ids:
        stripped = cap[len("legacy."):] if cap.startswith("legacy.") else cap
        prefixes.add(stripped.split(".", 1)[0])
    binding = {
        "named_route": named[0] if named else None,
        "legacy_bound": legacy,
        "capability_domain_declared": bool(prefixes & join.declared_prefixes()),
        "undeclared_capability_ids": [cap for cap in capability_ids
                                     if cap not in join.routes and cap not in join.runtime_owner],
        "enableable": False,
        "degrade_reason": None,
    }
    if entry["declared_modes"]["capability_absorption_registry"] == "UX_DONOR":
        binding["degrade_reason"] = "the absorption registry declares UX_DONOR"
        return binding
    if adoption["artifact"] not in CARRIED_ARTIFACTS:
        binding["degrade_reason"] = (f"no donor-specific artifact (probed {adoption['artifact']} "
                                    f"for terms {adoption['terms']})")
        return binding
    if not atlas_id:
        binding["degrade_reason"] = (f"no single atlas capability joins it: capability ids "
                                    f"{capability_ids or ['(none)']} appear in neither "
                                    f"{CAPABILITY_MAP} runtime_capabilities nor {ATLAS} dependencies")
        return binding
    if state in (None, "not_implemented"):
        binding["degrade_reason"] = (f"{CAPABILITY_MAP} declares no implementable state for "
                                    f"{atlas_id} (found {state})")
        return binding
    if legacy:
        binding["degrade_reason"] = (f"bound to legacy-path capability ids {legacy} rather than a "
                                    f"declared route in {ROUTES}")
        return binding
    if state == "worker_backed":
        if not named:
            binding["degrade_reason"] = (f"{atlas_id} is worker_backed but the entry names no "
                                        f"declared route in {ROUTES} (named {capability_ids})")
            return binding
        route_files = join.routes[named[0]]
        workers = probe.route_workers(route_files)
        binding["route_worker_files"] = [path.relative_to(probe.root).as_posix() for path in workers]
        named_in_route = probe.named_in_files(adoption["terms"], workers)
        if named_in_route:
            binding["named_in_route_worker"] = True
        else:
            binding["named_in_route_worker"] = False
            binding["degrade_reason"] = (f"the declared route {named[0]} is served by "
                                        f"{binding['route_worker_files']}, which never names the "
                                        f"donor; the donor artifact is carried elsewhere")
            return binding
    if entry["verification_tier"] not in ENABLEABLE_TIERS:
        binding["degrade_reason"] = (f"verification tier {entry['verification_tier']} is not one of "
                                    f"{sorted(ENABLEABLE_TIERS)}")
        return binding
    binding["enableable"] = True
    return binding


def derive_surface_class(entry: dict) -> tuple[str, str]:
    """Exactly one class per entry plus the reason that produced it, most explicit verdict first."""
    tier = entry["verification_tier"]
    declared = entry["declared_modes"]
    adoption = entry["adoption"]
    binding = entry["route_binding"]
    modes = {declared.get("capability_absorption_registry"), declared.get("derived_mode")}
    disposition = declared.get("supply_chain_ledger")
    atlas_id = entry["atlas_capability_id"]
    state = entry["map_state"]
    carried = adoption["carried"]

    if tier == "E" or disposition in NOT_ADOPTED_DISPOSITIONS:
        return ("not_adopted", "tier E or disposition " + str(disposition) + ": not adopted for the "
                               "stated role, with the recorded alternative kept in the source row"
                               + (" (a donor artifact exists on this host, which does not lift the "
                                  "gate)" if carried else "") + ".")
    if entry["_first_party"]:
        return ("base_dependency", "this entry names the product itself, not an external donor "
                                  "(registry upstream_project is null or the name is this "
                                  "repository's own declared package/brand). First-party substrate "
                                  "is never an enable-able external source.")
    if "UX_DONOR" in modes:
        return ("ux_donor", "declared UX_DONOR in docs/truth/CAPABILITY_ABSORPTION_REGISTRY.yaml: "
                            "it shapes an interaction rather than serving a capability route.")
    if tier == "C":
        return ("format_spec", "tier C is defined as an extracted behaviour/format/test with no "
                               "runtime adoption implied; the carried reference is a format or "
                               "protocol contract.")
    if binding.get("frontend_only_client") and not atlas_id:
        return ("ux_donor", "the donor is declared only in the client manifest scope "
                            "(frontend/package.json, frontend/package-lock.json) and no atlas "
                            "capability joins it, so it is a UI-layer donor.")
    if binding["enableable"]:
        return ("enableable_plugin",
                f"atlas capability {atlas_id} exists, {CAPABILITY_MAP} state is {state}, and "
                f"{adoption['artifact']} evidence names the donor itself"
                + (f" in the declared route {binding['named_route']}"
                   if binding.get("named_route") else "") + ".")
    if tier == "D" and (entry["_tier_is_authored"] or not carried):
        return ("future_candidate", "tier D" + (" is an authored review verdict: a deferred "
                                                "candidate with a stated demand trigger and no "
                                                "adoption." if entry["_tier_is_authored"]
                                                else " (the generator's default for a source row "
                                                    "with no reviewed verdict) and no donor "
                                                    "artifact was found") +
                " Neither is an adoption." + ("" if not carried else
                " A donor artifact exists; the disagreement is reported as a conflict."))
    if atlas_id or binding["capability_domain_declared"] or (tier == "D" and carried):
        return ("absorbed_algorithm", binding["degrade_reason"]
                or "the donor is carried but its capability lifecycle binding is incomplete.")
    if tier == "D":
        return ("future_candidate", "tier D: a deferred candidate with a stated demand trigger.")
    if carried:
        return ("base_dependency", "carried as substrate (declared package, vendored copy, imported "
                                   "code, invoked pipeline tool or bound external resource) with no "
                                   "atlas capability join and no declared worker route to enable.")
    return ("not_adopted", f"tier {tier} claims an implementation or entry, but no donor-specific "
                           "artifact was found in any dependency manifest, vendor root, source "
                           "identifier, pipeline invocation or bound resource index.")


def plugin_claim_failures(entry: dict, atlas_ids: set[str], map_states: dict[str, str],
                         routes: dict[str, list[str]]) -> list[str]:
    """Why an `enableable_plugin` row is not entitled to that class. Empty means it is.

    Shared by the generator (which refuses to emit a table containing such a row) and by
    tests/test_oss_absorption_crosswalk.py (which re-checks the committed file), so a row planted
    in the file is caught by the same predicate the generator used.
    """
    if entry["surface_class"] != "enableable_plugin":
        return []
    reasons: list[str] = []
    atlas_id = entry["atlas_capability_id"]
    binding = entry["route_binding"]
    adoption = entry["adoption"]
    if not atlas_id:
        reasons.append("no capability id from docs/truth/CAPABILITY_ATLAS_V2.yaml")
    elif atlas_id not in atlas_ids:
        reasons.append(f"atlas capability id {atlas_id} is not in the atlas id set")
    elif not ATLAS_ID_PATTERN.match(atlas_id):
        reasons.append(f"atlas capability id {atlas_id} is outside ^CAP-[0-9]{{4}}$")
    state = map_states.get(atlas_id) if atlas_id else None
    if entry["map_state"] != state:
        reasons.append(f"map state {entry['map_state']!r} is not what "
                       f"{CAPABILITY_MAP} says for {atlas_id} ({state!r})")
    if state not in ("core_native", "worker_backed"):
        reasons.append(f"{CAPABILITY_MAP} has no implementable state for {atlas_id} ({state!r})")
    if not adoption.get("carried"):
        reasons.append(f"no runtime adoption evidence (probed {adoption.get('artifact')} for terms "
                       f"{adoption.get('terms')})")
    if adoption.get("artifact") not in CARRIED_ARTIFACTS:
        reasons.append(f"artifact {adoption.get('artifact')!r} is not a carried adoption")
    if entry["verification_tier"] not in ENABLEABLE_TIERS:
        reasons.append(f"verification tier {entry['verification_tier']!r} is not A or B")
    if not binding.get("enableable"):
        reasons.append(f"route binding is not enableable: {binding.get('degrade_reason')}")
    if binding.get("legacy_bound"):
        reasons.append(f"legacy-path binding {binding['legacy_bound']}")
    if state == "worker_backed":
        route = binding.get("named_route")
        if route not in routes:
            reasons.append(f"named route {route!r} is not declared in {ROUTES}")
        elif not binding.get("named_in_route_worker"):
            reasons.append(f"declared route {route} worker files never name the donor")
    if entry["declared_modes"].get("capability_absorption_registry") == "UX_DONOR":
        reasons.append("declared UX_DONOR cannot be an enable-able plugin")
    if entry["verification_tier"] == "C":
        reasons.append("tier C implies no runtime adoption")
    return reasons


def collect_conflicts(entry: dict) -> list[dict]:
    """Every disagreement between the vocabularies, keeping both values."""
    conflicts: list[dict] = []
    declared = entry["declared_modes"]
    tier = entry["verification_tier"]
    adoption = entry["adoption"]
    disposition = declared.get("supply_chain_ledger")
    registry_mode = declared.get("capability_absorption_registry")
    registry_status = declared.get("capability_absorption_registry_status")
    reported = adoption["ledger_reported_evidence_state"]

    if len(entry["_tiers_sorted"]) > 1:
        conflicts.append({"reason": "tier-disagreement-inside-one-entry",
                          "values": {"categories": entry["_tiers_sorted"],
                                     "record_scopes": entry["_tier_scopes"]}})
    if len(entry["_atlas_candidates"]) > 1:
        conflicts.append({"reason": "atlas-join-ambiguous",
                          "values": {"atlas_capability_ids": entry["_atlas_candidates"],
                                     "note": "more than one atlas capability names this donor or "
                                             "owns its runtime capability; no winner is picked, so "
                                             "the entry cannot claim the plugin class"}})
    if tier in ("A", "B") and disposition in NON_RUNTIME_DISPOSITIONS:
        conflicts.append({"reason": "tier-says-implemented-disposition-says-not",
                          "values": {"verification_tier": tier, "supply_chain_disposition":
                                     disposition, "adoption_artifact": adoption["artifact"],
                                     "source": f"{DECISIONS} vs {LEDGER}"}})
    if tier in ("D", "E") and disposition in RUNTIME_DISPOSITIONS:
        conflicts.append({"reason": "disposition-says-adopted-tier-says-not",
                          "values": {"verification_tier": tier, "supply_chain_disposition":
                                     disposition, "adoption_artifact": adoption["artifact"]}})
    if (registry_mode in NON_RUNTIME_MODES or disposition in NON_RUNTIME_DISPOSITIONS) and \
            adoption["artifact"] in CARRIED_ARTIFACTS:
        conflicts.append({"reason": "declared-non-runtime-but-artifact-is-carried",
                          "values": {"registry_mode": registry_mode, "ledger_disposition":
                                     disposition, "adoption_artifact": adoption["artifact"],
                                     "hits": adoption["hits"]}})
    if tier in ("A", "B") and adoption["artifact"] not in CARRIED_ARTIFACTS:
        conflicts.append({"reason": "tier-claims-entry-without-donor-artifact",
                          "values": {"verification_tier": tier, "probed_artifact":
                                     adoption["artifact"], "donor_terms_probed": adoption["terms"],
                                     "generic_terms_stripped": entry["_stopwords"],
                                     "ledger_reported_evidence_state": reported}})
    if (registry_status in IMPLEMENTED_REGISTRY_STATUSES or registry_mode in RUNTIME_MODES or
            disposition in RUNTIME_DISPOSITIONS) and adoption["artifact"] not in CARRIED_ARTIFACTS:
        conflicts.append({"reason": "claimed-runtime-adoption-without-donor-artifact",
                          "values": {"registry_mode": registry_mode, "registry_status":
                                     registry_status, "ledger_disposition": disposition,
                                     "verification_tier": tier, "probed_artifact":
                                     adoption["artifact"], "donor_terms_probed": adoption["terms"],
                                     "ledger_reported_evidence_state": reported}})
    if reported in {"DECLARED", "DECLARED_AND_VENDORED", "VENDORED_ONLY", "IMPLEMENTED_IN_SOURCE"} \
            and adoption["artifact"] not in CARRIED_ARTIFACTS:
        conflicts.append({"reason": "donor-disposition-check-credits-a-generic-term",
                          "values": {"evidence_state_from_donor_check": reported,
                                     "donor_specific_artifact": adoption["artifact"],
                                     "donor_terms_probed": adoption["terms"],
                                     "generic_terms_stripped": entry["_stopwords"],
                                     "note": "the disposition check probes the row's curated terms, "
                                             "which include the capability's own name; crediting "
                                             "this donor on those hits is the failure mode this "
                                             "crosswalk exists to refuse"}})
    if entry["_route_engine_mismatch"]:
        conflicts.append({"reason": "formal-route-serves-a-different-engine",
                          "values": entry["_route_engine_mismatch"]})
    for capability_id in entry["route_binding"].get("undeclared_capability_ids") or []:
        nearby = sorted({cap for cap in
                         {runtime for runtime in entry["_all_runtime_capabilities"]
                          if runtime != capability_id}
                         if cap.split(".", 1)[0] == capability_id.split(".", 1)[0]})
        conflicts.append({"reason": "capability-id-is-not-a-declared-route",
                          "values": {"named_by": entry["_capability_source"].get(capability_id,
                                                                                "unknown source"),
                                     "capability_id": capability_id,
                                     "declared_runtime_capabilities_in_the_same_domain": nearby,
                                     "sources": [ROUTES, CAPABILITY_MAP]}})
    return conflicts


# ---------------------------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------------------------

def build(root: Path) -> dict:
    root = root.resolve()
    sys.path.insert(0, str(root / "scripts" / "audit"))
    import build_oss_reuse_inventory as inventory_module
    import oss_disposition_evidence as evidence_module

    decisions = _read_json(root, DECISIONS)
    verification = _read_json(root, VERIFICATION)
    registry_document = yaml.safe_load((root / REGISTRY).read_text(encoding="utf-8"))
    ledger_rows = _read_json(root, LEDGER)["components"]
    curated_terms = evidence_module.EVIDENCE_TERMS
    join = CapabilityJoin(root)
    probe = ArtifactProbe(root, evidence_module)
    inventory = inventory_module.build(root, decisions, verification)
    groups = build_groups(root, probe, inventory)
    all_runtime_capabilities = set(join.runtime_owner) | set(join.routes)

    entries: list[dict] = []
    for group in groups:
        decision = group.decision or {}
        ledger_row = group.ledger or {}
        registry_entry = group.registry or {}
        capability_ids = set(group.capability_ids) | {
            value for value in (decision.get("capability_id"),) if value}
        stopwords = set(capability_stopwords(ledger_row.get("capability")))
        terms = entry_terms(group, probe, list(curated_terms.get(ledger_row.get("id") or "", [])),
                           stopwords)
        adoption = probe.probe(terms)
        if ledger_row:
            curated = list(curated_terms.get(ledger_row["id"]) or [donor_name(ledger_row["name"])])
            c_manifests = probe.evidence.search_files(curated)
            c_code, c_stub, c_mention = probe.evidence.source_hits(curated)
            c_vendored = probe.evidence.vendor_hits(curated)
            adoption["ledger_reported_evidence_state"] = probe.evidence.evidence_state(
                c_manifests, c_vendored, c_code, c_stub, c_mention)
        else:
            adoption["ledger_reported_evidence_state"] = None

        donor_keys = {primary_key(name) for name in group.names} | {norm(name) for name in group.names}
        atlas_candidates = sorted(set(
            join.by_runtime_capability(decision.get("capability_id"))
            + join.by_runtime_capability(ledger_row.get("capability"))
            + join.by_donor_name(donor_keys)))
        atlas_id = atlas_candidates[0] if len(atlas_candidates) == 1 else None
        tiers = sorted(group.tiers, key=lambda tier: -TIER_RANK.get(tier, 0))
        frontend_only = False
        package_hits = [location for locations in adoption["hits"].get("package_declared", {}).values()
                        for location in locations]
        if package_hits:
            frontend_only = all(location.startswith("frontend/") for location in package_hits)

        entry = {
            "stable_key": group.key,
            "display_names": group.names,
            "namespaces": {
                "oss_reuse_decision": ({"canonical_name": decision["canonical_name"],
                                       "capability_id": decision.get("capability_id")}
                                      if decision else None),
                "supply_chain_ledger": ({"id": ledger_row["id"], "capability":
                                         ledger_row.get("capability")} if ledger_row else None),
                "capability_absorption_registry": ({"capability_id": registry_entry["capability_id"],
                                                   "absorption_mode": registry_entry["absorption_mode"],
                                                   "status": registry_entry["status"]}
                                                  if registry_entry else None),
                "capability_atlas": atlas_id,
                "atlas_join_candidates": atlas_candidates,
                "donor_disposition_archive": [row.get("id") or row.get("capability_id")
                                             for row in group.disposition_archive] or None,
            },
            "verification_tier": tiers[0] if tiers else None,
            "currently_usable": bool(tiers and tiers[0] == "A"),
            "absorption_mode": None,
            "declared_modes": {
                "capability_absorption_registry": registry_entry.get("absorption_mode"),
                "capability_absorption_registry_status": registry_entry.get("status"),
                "supply_chain_ledger": ledger_row.get("disposition"),
                "derived_mode": derive_mode(adoption, registry_entry.get("absorption_mode"), False),
            },
            "atlas_capability_id": atlas_id,
            "map_state": join.map_state.get(atlas_id) if atlas_id else None,
            "adoption": adoption,
            "route_binding": {},
            "surface_class": None,
            "surface_class_reason": None,
            "conflicts": [],
            "_first_party": is_first_party(group, probe),
            # Only the tier that was actually selected counts: a group can carry an authored
            # verdict for one tier and a derived one for another, and "authored" is what makes a
            # tier D a stated deferral rather than an absence of evidence.
            "_tier_is_authored": bool(tiers) and tiers[0] in group.authored,
            "_capability_ids": capability_ids,
            "_tiers_sorted": tiers,
            "_tier_scopes": sorted(group.tier_scopes),
            "_atlas_candidates": atlas_candidates,
            "_stopwords": sorted(stopwords),
            "_registry_evidence_paths": [path for path in
                                        (registry_entry.get("implementation_evidence") or [])
                                        if (root / path).exists()],
            "_route_engine_mismatch": [],
            "_all_runtime_capabilities": all_runtime_capabilities,
            "_capability_source": {value: source for value, source in
                                  [(decision.get("capability_id"), DECISIONS),
                                   (ledger_row.get("capability"), LEDGER)] if value},
        }
        entry["route_binding"] = route_binding(join, probe, entry)
        entry["route_binding"]["frontend_only_client"] = frontend_only
        entry["surface_class"], entry["surface_class_reason"] = derive_surface_class(entry)
        binding = entry["route_binding"]
        if binding.get("named_route") and binding.get("route_worker_files") and \
                adoption["carried"] and not binding.get("named_in_route_worker"):
            entry["_route_engine_mismatch"].append({
                "declared_route": binding["named_route"],
                "served_by": binding["route_worker_files"],
                "donor_artifact_found_in": {bucket: locations
                                           for bucket, locations in adoption["hits"].items()
                                           if bucket in CARRIED_ARTIFACTS}})
        entry["conflicts"] = collect_conflicts(entry)
        entry["absorption_mode"] = (registry_entry.get("absorption_mode")
                                   or entry["declared_modes"]["derived_mode"])
        for failure in plugin_claim_failures(entry, set(join.atlas_ids), join.map_state, join.routes):
            raise ValueError(f"{group.key}: enableable_plugin claim is not entitled to it: {failure}")
        entries.append({key: value for key, value in entry.items() if not key.startswith("_")})

    counts = dict(Counter(entry["surface_class"] for entry in entries))
    if sorted(counts) and not set(counts) <= set(SURFACE_CLASSES):
        raise ValueError(f"surface_class outside the closed set: {sorted(set(counts) - set(SURFACE_CLASSES))}")
    payload = {
        "schema": "archeaxis.oss-absorption-surface-crosswalk/v1",
        "artifact_name": "oss-absorption-surface-crosswalk-20261008",
        "observed_at": verification.get("observed_at", "2026-10-08"),
        "baseline": verification.get("baseline", "UNVERIFIED"),
        "purpose": "One honest surface_class per open-source absorption entry, joining the A-E "
                   "reuse-verification vocabulary to the capability absorption registry's "
                   "allowed_absorption_modes, so the UI can show absorption sources without "
                   "rendering all of them as enable-able plugins.",
        "generator": {"path": "scripts/audit/build_oss_absorption_crosswalk.py",
                      "sha256": hashlib.sha256(Path(__file__).resolve().read_bytes()).hexdigest()},
        "producing_command": ["<python>", "scripts/audit/build_oss_absorption_crosswalk.py",
                             "--root", "<repository root>", "--output", OUTPUT_RELPATH],
        "entry_universe": {
            "oss_reuse_decisions": len(decisions["decisions"]),
            "capability_absorption_registry": len(registry_document["entries"]),
            "supply_chain_ledger": len(ledger_rows),
            "grouped_entries": len(entries),
            "excluded": "The 369-row historical research pool and the 691-row lossless crosswalk it "
                        "produces. Those rows are candidate names, not absorption entries "
                        "(docs/current/AAOS-OSS-DONOR-DISPOSITION-V2-20261002.json: '369 pool "
                        "entries are not 369 installations'); they stay in the regenerated payload "
                        "described by docs/current/OSS-REUSE-CROSSWALK-20261008.manifest.json, "
                        "which this artifact does not replace.",
        },
        "id_namespaces": {
            "capability_atlas": {"pattern": ATLAS_ID_PATTERN.pattern, "owner": ATLAS,
                                "state_owner": CAPABILITY_MAP,
                                "count": len(join.atlas_ids), "ids": join.atlas_ids},
            "capability_absorption_registry": {"pattern": REGISTRY_ID_PATTERN.pattern,
                                              "owner": REGISTRY,
                                              "count": len(registry_document["entries"]),
                                              "ids": [entry["capability_id"]
                                                      for entry in registry_document["entries"]]},
            "warning": "The registry's schema pattern ^CAP-[A-Z0-9-]+$ also matches an atlas id "
                       "such as CAP-0010, so pattern checking alone cannot separate the "
                       "namespaces. The atlas column is validated against the atlas id set and the "
                       "registry column against the registry id set.",
            "never_merge": True,
        },
        "surface_classes": {key: SURFACE_CLASS_MEANING[key] for key in SURFACE_CLASSES},
        "derivation": {
            "verification_tier": "the category scripts/audit/build_oss_reuse_inventory.py carries "
                                 "for this entry's records; B is promoted to A only by bound "
                                 "verification in " + VERIFICATION + ", never by a decision",
            "absorption_mode": "declared values are kept per namespace and never overwritten; "
                               "derived_mode is computed from the artifact shape in the registry's "
                               "own vocabulary",
            "atlas_capability_id": "the entry's dotted capability id appearing in " + CAPABILITY_MAP
                                   + " runtime_capabilities, or the donor name appearing in "
                                   + ATLAS + " dependencies; two different matches make the row a "
                                   "conflict and refuse the plugin class",
            "adoption": "donor-specific terms only. Tokens that are the capability's own name or "
                        "acronym are stripped first, then probed as declared package names "
                        "(pyproject.toml, uv.lock, requirements.txt, frontend/package.json, "
                        "frontend/package-lock.json, Cargo.lock), vendor roots, first-party source "
                        "identifiers excluding self-declared unavailable stubs, the bound external "
                        "resource index, and the declared route worker files",
            "surface_class": "ordered rules in derive_surface_class; enableable_plugin additionally "
                             "requires an atlas id in the atlas set, a capability-map state, a "
                             "carried donor artifact, tier A or B, and a route binding that names "
                             "the donor in the declared worker. The generator raises rather than "
                             "emitting a table containing an unentitled plugin row.",
        },
        "class_counts": counts,
        "class_order": list(SURFACE_CLASSES),
        "conflict_count": sum(len(entry["conflicts"]) for entry in entries),
        "entries_with_conflicts": sum(1 for entry in entries if entry["conflicts"]),
        "entries": entries,
        "inputs": {},
        "limits": [
            "A row's class is what the tracked files support today, not what a plan intends.",
            "NOT_RUN stays NOT_RUN: nothing here proves installed-desktop or release qualification.",
            "Donor joins are exact-normalized only. A donor spelled differently across sources "
            "stays two rows rather than becoming one merged claim.",
            "shared-contracts/ and inspiration_research/ are outside the source roots the donor "
            "check scans, so an adapter kept only there reports no artifact.",
            "The registry's CAP-XXX ids and the atlas's CAP-00NN ids are separate namespaces; this "
            "table never copies one into the other's column.",
        ],
    }
    for rel in [DECISIONS, VERIFICATION, REGISTRY, REGISTRY_SCHEMA, LEDGER, ATLAS, CAPABILITY_MAP,
                ROUTES, EXTERNAL_RESOURCES, DISPOSITION, INVENTORY_SCRIPT, EVIDENCE_SCRIPT]:
        path = root / rel
        payload["inputs"][rel] = {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                                 "bytes": path.stat().st_size}
    return payload


def render_typescript(payload: dict) -> str:
    """The projection the front end can read, generated from the same build() as the JSON.

    Keyed by stable capability id, because that is the only handle a capability detail holds.
    Entries with no id are left out rather than folded into a neighbouring id: a donor that joins
    to nothing must not turn up as a classification for a capability it is not. The class union is
    emitted from SURFACE_CLASSES, so the closed set cannot drift from the generator's own check.
    """
    by_id: dict[str, list[dict]] = {}
    for entry in payload["entries"]:
        capability_id = entry.get("atlas_capability_id")
        if not capability_id:
            continue
        names = entry.get("display_names") or [entry["stable_key"]]
        by_id.setdefault(capability_id, []).append({
            "source": names[0],
            "surface_class": entry["surface_class"],
            "verification_tier": entry["verification_tier"],
            "currently_usable": bool(entry["currently_usable"]),
            "conflicts": len(entry.get("conflicts") or []),
        })
    rows = json.dumps(dict(sorted(by_id.items())), ensure_ascii=False, indent=2)
    union = " | ".join(f'"{name}"' for name in SURFACE_CLASSES)
    return (
        "// Generated by scripts/audit/build_oss_absorption_crosswalk.py - do not edit by hand.\n"
        "// One surface class per absorption source that joins to a stable capability id. Sources\n"
        "// with no id are absent on purpose, and an absent id renders as unclassified rather than\n"
        "// as a guess. Regenerate with the command recorded in the JSON artifact's own provenance.\n"
        f"export type AbsorptionSurfaceClass = {union};\n\n"
        "export type AbsorptionSurfaceRow = {\n"
        "  source: string;\n"
        "  surface_class: AbsorptionSurfaceClass;\n"
        "  verification_tier: string | null;\n"
        "  currently_usable: boolean;\n"
        "  conflicts: number;\n"
        "};\n\n"
        "export const ABSORPTION_SURFACE_BY_CAPABILITY: Readonly<\n"
        f"  Record<string, readonly AbsorptionSurfaceRow[]>\n> = {rows};\n\n"
        f"export const ABSORPTION_SURFACE_CLASSES: readonly AbsorptionSurfaceClass[] = "
        f"{json.dumps(list(SURFACE_CLASSES), ensure_ascii=False)} as const;\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Emit the committed absorption surface crosswalk.")
    parser.add_argument("--root", type=Path, default=ROOT_DEFAULT)
    parser.add_argument("--output", type=Path, default=ROOT_DEFAULT / OUTPUT_RELPATH)
    parser.add_argument("--check", action="store_true",
                        help="exit non-zero when the committed artifact is not what the current "
                             "inputs derive; --check never writes")
    arguments = parser.parse_args()
    root = arguments.root.resolve()
    output = arguments.output if arguments.output.is_absolute() else (root / arguments.output)
    output = output.resolve()
    output.relative_to(root)
    payload = build(root)
    rendered = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    typescript = render_typescript(payload)
    ts_path = root / TS_RELPATH
    if arguments.check:
        current = output.read_text(encoding="utf-8") if output.is_file() else ""
        if current.replace("\r\n", "\n") != rendered:
            print(f"STALE: {output} is not what the current inputs derive; rerun the generator",
                  file=sys.stderr)
            return 1
        ts_current = ts_path.read_text(encoding="utf-8") if ts_path.is_file() else ""
        if ts_current.replace("\r\n", "\n") != typescript:
            print(f"STALE: {ts_path} is not what the crosswalk derives; rerun the generator",
                  file=sys.stderr)
            return 1
        print(json.dumps({"check": "current", "entries": len(payload["entries"]),
                          "ts_capability_ids": len({
                              entry["atlas_capability_id"] for entry in payload["entries"]
                              if entry.get("atlas_capability_id")})},
                         ensure_ascii=False))
        return 0
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(rendered.encode("utf-8"))
    ts_path.parent.mkdir(parents=True, exist_ok=True)
    ts_path.write_text(typescript, encoding="utf-8", newline="\n")
    print(json.dumps({"entries": len(payload["entries"]),
                      "class_counts": payload["class_counts"],
                      "conflicts": payload["conflict_count"],
                      "written": output.relative_to(root).as_posix(),
                      "typescript_written": TS_RELPATH}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
