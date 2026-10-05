"""Import required engines with the interpreter shipped to the product host."""

from __future__ import annotations

import argparse
import importlib.util
import subprocess
from pathlib import Path

ENGINE_PROBE = """
import importlib, importlib.metadata, json, pathlib, shutil, subprocess, sys
root = pathlib.Path(sys.executable).parent.resolve()
modules = []
for name, distribution in [('openpyxl', 'openpyxl'), ('pptx', 'python-pptx'),
                           ('markitdown', 'markitdown'), ('pytesseract', 'pytesseract')]:
    module = importlib.import_module(name)
    path = pathlib.Path(module.__file__).resolve()
    if not path.is_relative_to(root):
        raise RuntimeError(f'{name} was imported outside the bundled runtime: {path}')
    modules.append({'module': name, 'path': str(path),
                    'version': importlib.metadata.version(distribution)})
ocr = shutil.which('tesseract')
ocr_version = None
if ocr:
    result = subprocess.run([ocr, '--version'], capture_output=True, text=True, check=True)
    ocr_version = result.stdout.splitlines()[0]
print(json.dumps({'executable': sys.executable, 'modules': modules,
                  'ocr': {'path': ocr, 'version': ocr_version,
                          'sample_qualification': 'NOT_EXECUTED'}}, ensure_ascii=False))
"""


def assert_runtime_engines(candidate: Path) -> None:
    repository = Path(__file__).resolve().parents[2]
    spec = importlib.util.spec_from_file_location(
        "engine_launcher", repository / "scripts/release/backend_launcher.py"
    )
    assert spec and spec.loader
    launcher = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(launcher)
    candidate = candidate.resolve()
    profile = launcher.load_profile(candidate)
    python = profile["python"]
    # runtime.rs chooses nested first. A stale cached interpreter must fail this
    # assertion rather than let a different interpreter pass on its behalf.
    nested = candidate / "runtime/python/python.exe"
    selected = nested if nested.is_file() else candidate / "runtime/python.exe"
    if selected.resolve() != python.resolve():
        raise RuntimeError("host interpreter selection differs from worker-profile.json")
    subprocess.run(
        [str(python), "-B", "-I", "-c", ENGINE_PROBE],
        cwd=candidate,
        env=launcher.build_environment(candidate),
        check=True,
        timeout=90,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    args = parser.parse_args()
    assert_runtime_engines(args.candidate)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
