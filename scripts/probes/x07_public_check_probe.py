"""X07 public-retrieval probe (C09: reproducible, in-repo copy).

VERIFY-01 contract: a check result is not an exit code and "no error" is not
"supported". A PASS requires (a) a real fetched source, (b) a locatable
evidence quote carrying the object, unit and condition of the claim, and
(c) a local-model verdict that explicitly says 支持 ("不支持"/"无法判断" or
any model failure is NOT support). Prints JSON; exit 0 only on full support.
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
import urllib.request
from pathlib import Path

CLAIM = "地球的平均半径约为 6371 公里"
URL = "https://en.wikipedia.org/w/api.php?action=query&format=json&prop=extracts&explaintext=1&redirects=1&titles=Earth"

RADIUS_TOKENS = ("6371", "6,371", "6 371")
DIAMETER_TOKENS = ("12,742", "12742", "12 742")


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "ArcheAxis-X07/0.1 probe"})
    with urllib.request.urlopen(req, timeout=40) as resp:
        raw = json.loads(resp.read().decode("utf-8"))
    return next(iter(raw["query"]["pages"].values()))["extract"]


def evidence_quote(extract: str) -> tuple[bool, str, str]:
    """Locate a quote that carries object (radius/平均半径), unit (km/公里)
    and the number. A bare literal is NOT support; a diameter-only hit is
    recorded as weaker but distinct evidence, never as radius support."""
    for sentence in re.split(r"(?<=[.。])\s+", extract.replace("\n", " ")):
        if any(t in sentence for t in RADIUS_TOKENS):
            lowered = sentence.lower()
            if ("radius" in lowered or "半径" in sentence) and (
                "km" in lowered or "kilomet" in lowered or "公里" in sentence
            ):
                return True, "radius", sentence.strip()[:300]
    for sentence in re.split(r"(?<=[.。])\s+", extract.replace("\n", " ")):
        if any(t in sentence for t in DIAMETER_TOKENS):
            return False, "diameter_only", sentence.strip()[:300]
    return False, "none", ""


def local_judge(extract: str) -> str:
    worker = Path(__file__).resolve().parents[2] / "services/python-workers/machine/worker_machine_answer.py"
    spec = importlib.util.spec_from_file_location("public_check_machine", worker)
    machine = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(machine)
    question = f"判断来源是否支持该主张：{CLAIM}。只答：支持/不支持/无法判断，加一句理由。"
    return machine.answer(extract[:900], question, timeout_s=200, max_tokens=4096)["answer"].strip()


def parse_verdict(verdict: str) -> tuple[bool, str]:
    """支持 is support; 不支持 and 无法判断 are NOT support; anything else
    (empty text, model error) is NOT support."""
    text = verdict.strip()
    if text.startswith("不支持") or "不支持" in text[:6]:
        return False, "unsupported"
    if text.startswith("无法判断") or "无法判断" in text[:6]:
        return False, "undeterminable"
    if text.startswith("支持"):
        return True, "supported"
    return False, "unparseable_or_error"


def main() -> int:
    try:
        extract = fetch(URL)
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"fetch_error": str(exc)[:200], "supported": False}))
        return 2
    has_quote, evidence_kind, quote = evidence_quote(extract)
    try:
        verdict = local_judge(extract)
    except Exception as exc:  # noqa: BLE001
        verdict = f"model error: {str(exc)[:120]}"
    verdict_ok, verdict_kind = parse_verdict(verdict)
    supported = has_quote and verdict_ok
    print(json.dumps({"source_url": URL, "extract_head": extract[:120],
                      "evidence_kind": evidence_kind,
                      "evidence_quote": quote,
                      "local_model_verdict": verdict,
                      "verdict_kind": verdict_kind,
                      "supported": supported}, ensure_ascii=False, indent=2))
    return 0 if supported else 1


if __name__ == "__main__":
    sys.exit(main())
