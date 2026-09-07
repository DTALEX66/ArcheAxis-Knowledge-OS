"""X07 public-retrieval probe (C09: reproducible, in-repo copy).

One real public-source retrieval plus a local-model judge attempt. Requires
working outbound HTTPS from the python environment (intermittent on some
hosts) and a running local ollama (qwen3:8b) for the judge. Prints JSON.
"""

from __future__ import annotations

import json
import sys
import urllib.request

CLAIM = "地球的平均半径约为 6371 公里"
URL = "https://en.wikipedia.org/w/api.php?action=query&format=json&prop=extracts&explaintext=1&redirects=1&titles=Earth"


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "ArcheAxis-X07/0.1 probe"})
    with urllib.request.urlopen(req, timeout=40) as resp:
        raw = json.loads(resp.read().decode("utf-8"))
    return next(iter(raw["query"]["pages"].values()))["extract"]


def numeric_support(extract: str) -> tuple[bool, str]:
    for token, label in [("6371", "6371"), ("6,371", "6,371"),
                         ("6 371", "6 371"), ("12,742", "12,742(diameter)")]:
        if token in extract:
            return True, f"found {label}"
    return False, "no radius/diameter literal found"


def local_judge(extract: str) -> str:
    prompt = ("判断来源是否支持该主张。只答：支持/不支持/无法判断，加一句理由。\n"
              f"主张：{CLAIM}\n来源：{extract[:900]}\n")
    body = json.dumps({"model": "qwen3:8b", "prompt": prompt, "stream": False,
                       "options": {"num_predict": 60}}).encode("utf-8")
    req = urllib.request.Request("http://127.0.0.1:11434/api/generate", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=200) as resp:
        return json.loads(resp.read().decode("utf-8")).get("response", "").strip()


def main() -> int:
    try:
        extract = fetch(URL)
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"fetch_error": str(exc)[:200]}))
        return 2
    supported, note = numeric_support(extract)
    try:
        verdict = local_judge(extract)
    except Exception as exc:  # noqa: BLE001
        verdict = f"model error: {str(exc)[:120]}"
    print(json.dumps({"source_url": URL, "extract_head": extract[:120],
                      "numeric_support": supported, "numeric_note": note,
                      "local_model_verdict": verdict}, ensure_ascii=False, indent=2))
    return 0 if supported and "error" not in verdict else 1


if __name__ == "__main__":
    sys.exit(main())
