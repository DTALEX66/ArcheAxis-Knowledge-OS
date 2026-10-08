"""Emission discipline for audit generators.

Why this module exists (FINDING 6): two generators wrote documents whose conclusions
were typed into the source. One printed "PASS/CI(force_full) only for frozen candidate
72a0bbc2", "PARTIAL", "BLOCKED-ON-SUPPLY", "NOT_EXECUTED" and fixed counts regardless of
what the receipts said; the other claimed in its own docstring that "nothing is typed in
by hand" while hard-coding "（前端 365、Rust 526）", "（应为 2）" and "实测为 31".

The rule this module enforces:

* a value that can be computed from artifacts is taken from a **resolver** -- a callable
  that reads the artifact -- and the template it is substituted into may not contain a
  literal number of its own (``computed`` refuses it at construction time);
* a value that cannot be computed is emitted as ``CLAIM`` with the named source, or as
  ``INSUFFICIENT-EVIDENCE`` with the named reason;
* every non-structural line of the document carries one of those markers, and
  ``check_written`` re-reads the **written bytes** and fails the run when anything else
  reaches the output. It also cross-checks that every marked line is one the run actually
  produced through ``computed``/``claim``/``insufficient``, so a hand-typed line cannot
  buy itself a fake marker;
* the generator never says "all fields are recomputed from disk". It prints the tally of
  COMPUTED / CLAIM / INSUFFICIENT-EVIDENCE lines it produced, itself computed.

Nothing is deleted by this rule: information that cannot be sourced is still emitted,
labelled as what it is.
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Mapping, Sequence

COMPUTED = "COMPUTED"
CLAIM = "CLAIM"
INSUFFICIENT = "INSUFFICIENT-EVIDENCE"
VERBATIM = "VERBATIM-FROM"
PROVENANCE_CLASSES: tuple[str, ...] = (COMPUTED, CLAIM, INSUFFICIENT)

MARK_RE = re.compile(
    r"〔(?P<kind>COMPUTED|CLAIM|INSUFFICIENT-EVIDENCE|VERBATIM-FROM)[:：]\s*(?P<spec>[^〕]*)〕")

#: Words that assert a state of the work. Kept for reporting only: the discipline rule is
#: that every claim carries a marker, whichever words it uses.
VERDICT_WORDS = (
    "PASS", "PARTIAL", "BLOCKED-ON-SUPPLY", "NOT_EXECUTED", "NOT_RUN", "NOT_APPLICABLE",
    "UNVERIFIED", "UNRESOLVED", "AMBIGUOUS", "HASH_MISMATCH", "HISTORICAL", "TESTED_LOCAL",
    "AWAITING_OWNER", "AVAILABLE", "UNAVAILABLE", "REAL_MODEL", "NO-GAP",
)
VERDICT_RE = re.compile(
    r"\b(" + "|".join(re.escape(word) for word in VERDICT_WORDS) + r"[A-Z_]*)\b"
    r"|已闭|无缺口|全部通过|均已解析")

#: Digits standing alone -- not part of an identifier, path, version, hex run or range.
NUMBER_RE = re.compile(r"(?<![\w./:\-])\d+(?:[.,]\d+)?(?![\w./:\-])")
PLACEHOLDER_RE = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")

_EXEMPT_LINE_PATTERNS = (
    re.compile(r"^\s*$"),                              # blank
    re.compile(r"^#{1,6} "),                           # section heading
    re.compile(r"^\s*---+\s*$"),                       # rule
    re.compile(r"^\s*\|[\s:|\-]+\|\s*$"),              # table separator row
    re.compile(r"^```"),                              # fence (may carry a VERBATIM marker)
)


class DisciplineViolation(RuntimeError):
    """Raised when an unmarked or hand-typed conclusion reaches the output."""


@dataclass(frozen=True)
class Item:
    """One emission: text plus the provenance that justifies it."""

    text: str
    provenance: str
    source: str

    def render(self) -> str:
        return f"{self.text} 〔{self.provenance}: {self.source}〕"


def _substitute(template: str, values: Mapping[str, Callable[[], object] | object]) -> str:
    """Fill ``{name}`` from resolvers. A literal number left in the template after the
    placeholders are removed is hand-typed, so this refuses it."""
    stripped = PLACEHOLDER_RE.sub(lambda m: "#", template)
    offenders = [m.group(0) for m in NUMBER_RE.finditer(stripped)]
    if offenders:
        raise DisciplineViolation(
            f"computed template hard-codes {offenders}: take the number from a resolver "
            f"instead of typing it -- template was {template!r}")
    missing = [name for name in PLACEHOLDER_RE.findall(template) if name not in values]
    if missing:
        raise DisciplineViolation(f"template {template!r} has no resolver for {missing}")
    text = template
    for name, value in values.items():
        resolved = value() if callable(value) else value
        text = text.replace("{" + name + "}", str(resolved))
    return text


def computed(template: str, source: str,
             **values: Callable[[], object] | object) -> Item:
    """Emit a line whose numbers come from artifact readers, not from the source text.

    ``source`` names the artifact and the field read from it, e.g.
    ``<dir>/receipt.json#commands[0].tests_passed``.
    """
    return Item(text=_substitute(template, values), provenance=COMPUTED, source=source)


def claim(text: str, source: str) -> Item:
    """Emit a statement that cannot be recomputed from artifacts, labelled as a claim."""
    if not source.strip():
        raise DisciplineViolation(f"claim without a source: {text!r}")
    return Item(text=text, provenance=CLAIM, source=source)


def insufficient(text: str, reason: str) -> Item:
    """Emit the honest absence: this cannot be established, and here is why."""
    if not reason.strip():
        raise DisciplineViolation(f"INSUFFICIENT-EVIDENCE without a reason: {text!r}")
    return Item(text=text, provenance=INSUFFICIENT, source=reason)


def verbatim(lines: Sequence[str], source: str) -> list[str]:
    """A fenced block of artifact content, opened with the bytes it came from.

    Content inside is quoted, not asserted, so the marker sits on the fence opener.
    """
    return [f"``` 〔{VERBATIM}: {source}〕", *[line.rstrip("\n") for line in lines], "```"]


def render(items: Iterable[Item | str]) -> list[str]:
    out: list[str] = []
    for item in items:
        out.append(item.render() if isinstance(item, Item) else str(item))
    return out


def tally(items: Sequence[Item | str]) -> dict[str, int]:
    counts: dict[str, int] = {kind: 0 for kind in PROVENANCE_CLASSES}
    for item in items:
        if isinstance(item, Item) and item.provenance in counts:
            counts[item.provenance] += 1
    return counts


def is_exempt(line: str) -> bool:
    return any(pattern.match(line) for pattern in _EXEMPT_LINE_PATTERNS)


def scan_unmarked(text: str) -> list[str]:
    """Every offending line in a rendered document (the self-check's core)."""
    offenders: list[str] = []
    inside_verbatim = False
    for line in text.splitlines():
        if line.startswith("```"):
            inside_verbatim = ("VERBATIM-FROM" in line and MARK_RE.search(line) is not None)
            continue
        if inside_verbatim or is_exempt(line):
            continue
        match = MARK_RE.search(line)
        if match is None:
            offenders.append(f"UNMARKED  {line!r}")
            continue
        if not match.group("spec").strip():
            offenders.append(f"EMPTY_SOURCE  {line!r}")
    return offenders


def scan_unproduced(text: str, items: Sequence[Item | str]) -> list[str]:
    """A marked line must be one this run actually emitted through a resolver.

    Without this, a hard-coded string could be saved by typing a ``〔COMPUTED: ...〕``
    suffix onto it -- which is the same defect wearing a label.
    """
    produced = {item.render() for item in items if isinstance(item, Item)}
    offenders: list[str] = []
    for line in text.splitlines():
        if MARK_RE.search(line) and not is_exempt(line) and line not in produced:
            offenders.append(f"MARKED_BUT_NOT_EMITTED  {line!r}")
    return offenders


def assert_discipline(text: str, items: Sequence[Item | str] | None = None) -> None:
    """Fail the run when an unmarked verdict/number reaches the output."""
    offenders = scan_unmarked(text)
    if items is not None:
        offenders += scan_unproduced(text, items)
    if offenders:
        raise DisciplineViolation(
            "emission discipline violated; these lines assert without a usable source:\n"
            + "\n".join(f"  {offender}" for offender in offenders))


def check_written(path: Path, items: Sequence[Item | str] | None = None) -> str:
    """Re-read the written bytes and police them. A generator's own exit code is not a
    verdict, so this reads the artifact from disk."""
    text = path.read_text(encoding="utf-8")
    assert_discipline(text, items)
    return text


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("document", help="generated document to police")
    args = parser.parse_args(argv)
    try:
        check_written(Path(args.document))
    except DisciplineViolation as error:
        print(str(error))
        return 1
    print("emission discipline: every non-structural line carries a sourced marker")
    return 0


if __name__ == "__main__":
    sys.exit(main())
