"""Turn pytest JUnit failures into GitHub Actions error annotations.

The Actions public API exposes check annotations even when raw job logs require
authentication.  Keep this stdlib-only helper beside the CI workflow so a
failing test remains diagnosable from the exact-SHA check run.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from xml.etree import ElementTree


def _message(testcase: ElementTree.Element) -> str:
    failure = testcase.find("failure")
    if failure is None:
        failure = testcase.find("error")
    if failure is None:
        return ""
    message = (failure.get("message") or failure.text or "pytest failure").strip()
    return " ".join(message.split())


def main() -> None:
    parser = argparse.ArgumentParser(description="emit GitHub annotations from pytest JUnit XML")
    parser.add_argument("junit_xml", type=Path)
    args = parser.parse_args()

    root = ElementTree.parse(args.junit_xml).getroot()
    failures = 0
    for testcase in root.iter("testcase"):
        message = _message(testcase)
        if not message:
            continue
        failures += 1
        classname = testcase.get("classname", "unknown")
        name = testcase.get("name", "unknown")
        print(f"::error title=Pytest failure::{classname}::{name}: {message}")
    print(f"pytest-annotation-summary: failures={failures}")


if __name__ == "__main__":
    main()
