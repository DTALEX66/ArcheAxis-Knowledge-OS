"""Read-only environment capability registry resolver and probe engine.

This resolves the repository's declared capability requirements to observable
command availability. It never installs tools, never expands a guess into a binding, and
never reports an index entry as availability.

Two rules define this module, and both exist because they were measured being broken:

1. **Declared paths first.** `config/environment/capability-requirements.yaml` is the
   binding. A `shutil.which()` hit on `PATH` used to win over it, so a global binary
   silently substituted for the project's declared one. `PATH` is now consulted only when
   the declaration names nothing, and that case is recorded as
   ``binding: "unbound_path_fallback"`` — visible, and never the project's binding.
2. **A row is certified by its own probe, with its own interpreter.** The old code reduced
   `uv run python -c "import faster_whisper"` to the token `uv` and ran `--version` against
   whatever ambient `uv` sat on `PATH`, then certified faster-whisper, rapidocr,
   sherpa-onnx, magika and the CI venv as ``uv 0.12.23``. That is a fabricated
   RESULT_VERIFIED. Each entry now declares a `probe` block naming the executable,
   interpreter, registry key, path or HTTP lane that actually answers for it, and a
   directory can never satisfy a version probe. Where the real probe cannot run, the row is
   recorded `unavailable` or `NOT_RUN` with the reason — it never inherits a version from a
   wrapper binary.

Verification levels are measured, not declared:
`REGISTERED` (the entry parsed) < `FILE_EXISTS` < `VERSION_PROBED` < `RESULT_VERIFIED`,
with `NOT_RUN` and `unavailable` as explicit non-claims. A declaration states only the
ceiling a passing probe may reach (`probe.reaches`).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - the project preflight reports this
    yaml = None

ROOT = Path(__file__).resolve().parents[2]

LEVELS = ("REGISTERED", "FILE_EXISTS", "VERSION_PROBED", "RESULT_VERIFIED")
NOT_RUN = "NOT_RUN"
UNAVAILABLE = "unavailable"

# Resolution order, highest first: an explicit per-tool override, then the declared
# external path, then (only as a labelled fallback) PATH.
OVERRIDE_ENV = ("ARCHEAXIS_EXTERNAL_ROOT", "OS_EXTERNAL_CONFIG")
DEFAULT_TIMEOUT = 30


def _command_name(command: str | None) -> str | None:
    """The first token of a healthcheck string, for *reporting only*.

    This is deliberately no longer used to decide what to execute: reducing
    `uv run python -c "import X"` to `uv` is what let an unrelated binary certify an engine.
    Each probe now names its own executable or interpreter.
    """
    if not command:
        return None
    match = re.match(r"\s*([\w.-]+)", command)
    return match.group(1) if match else None


def _run(argv: list[str], *, cwd: str | None = None, env: dict | None = None,
         timeout: int = DEFAULT_TIMEOUT, stdin_devnull: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(argv, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=timeout, check=False, cwd=cwd, env=env,
                          stdin=subprocess.DEVNULL if stdin_devnull else None)


def _output(result: subprocess.CompletedProcess, *, stderr_is_normal: bool = False) -> str:
    if stderr_is_normal:
        return ((result.stderr or "") + "\n" + (result.stdout or "")).strip()
    return ((result.stdout or "") + "\n" + (result.stderr or "")).strip()


def sibling_root(root: Path, declared: object, name: object) -> Path | None:
    """The declared sibling root `name` resolves to, or None.

    A shared resource beside the external root — the model library is the real case — is reached
    through a root this manifest names, never by writing `..` into `external_paths`. One level up
    and one directory down is the whole allowance, so the reachable set is what the manifest says
    rather than wherever a traversal happens to point.
    """
    if not isinstance(declared, dict) or not isinstance(name, str):
        return None
    relative = declared.get(name)
    if not isinstance(relative, str):
        return None
    parts = Path(relative).parts
    if len(parts) != 2 or parts[0] != ".." or Path(relative).is_absolute():
        return None
    candidate = (root / Path(relative)).resolve()
    return candidate if candidate.is_dir() else None


def _entry_base(entry: dict, root: Path | None, siblings: object) -> Path | None:
    """The root this entry's declarations are relative to: the external root, or its sibling root."""
    if root is None:
        return None
    if entry.get("sibling_root") is None:
        return root
    return sibling_root(root, siblings, entry.get("sibling_root"))


def _inside(base: Path, declared: object) -> Path | None:
    """A declared location kept inside one root; absolute and `..` forms are refused here."""
    if not isinstance(declared, str) or not declared.strip():
        return None
    relative = Path(declared)
    if relative.is_absolute() or ".." in relative.parts:
        return None
    path = (base / relative).resolve()
    return path if path.is_relative_to(base) else None


def _external_path(entry: dict, root: Path | None, siblings: object = None) -> str | None:
    """The declared shared-tool path that exists on this host, or None.

    No guessing and no installing: a declaration that does not resolve stays None so the
    caller records the gap. `PATH` is not consulted here — that is a separate, labelled step.
    """
    base = _entry_base(entry, root, siblings)
    if base is None:
        return None
    for candidate in entry.get("external_paths", []) or []:
        path = _inside(base, candidate)
        if path is not None and (path.is_file() or path.is_dir()):
            return str(path)
    return None


def _declared_relative(entry: dict, base: Path | None) -> str | None:
    """The declared relative location that exists — the location *as declared*, not as a
    machine-specific absolute path, so a report stays comparable across hosts."""
    if base is None:
        return None
    for candidate in entry.get("external_paths", []) or []:
        path = _inside(base, candidate)
        if path is not None and (path.is_file() or path.is_dir()):
            return candidate if isinstance(candidate, str) else None
    return None


def required_environment(entry: dict, root: Path | None, siblings: object,
                         *, only_existing: bool = True) -> dict[str, str]:
    """The process environment a declared resource needs, with paths resolved.

    Same rule as `services/python-workers/tool_paths.py::required_environment`, over the same
    manifest: values are paths relative to the entry's declared root, absolute and `..` forms
    are refused, and a path that does not exist is skipped rather than exported. tesseract
    without `TESSDATA_PREFIX` dies with a `std::filesystem` abort, and `10-toolchains/cargo/bin/
    rustc.exe` without `RUSTUP_HOME`/`CARGO_HOME` dies with ``Missing manifest in toolchain``;
    both are "the file is there, it still cannot run", which is exactly what this carries.
    """
    declared = entry.get("required_env") or {}
    if not isinstance(declared, dict):
        return {}
    base = _entry_base(entry, root, siblings)
    if base is None:
        return {}
    found: dict[str, str] = {}
    for variable, location in declared.items():
        path = _inside(base, location)
        if path is None:
            continue
        if only_existing and not (path.is_file() or path.is_dir()):
            continue
        found[str(variable)] = str(path)
    return found


def _child_env(extra: dict[str, str]) -> dict[str, str]:
    env = dict(os.environ)
    env.update({k: v for k, v in extra.items() if v})
    return env


def _display_path(path: str | None, *, binding: str | None) -> str | None:
    """Return a sanitized path label for reports, never a private absolute path."""
    if not path:
        return None
    label = {"declared": "external", "unbound_path_fallback": "path"}.get(binding or "", "path")
    return f"{label}:{Path(path).name}"


def _text_match(pattern: str | None, text: str) -> str | None:
    """The matched line for *pattern*, or None when it does not match."""
    if not pattern:
        return text.splitlines()[0].strip()[:200] if text.strip() else None
    for line in text.splitlines():
        if re.search(pattern, line):
            return line.strip()[:200]
    return None


def _json_path(payload: object, dotted: str) -> object:
    current = payload
    for part in dotted.split("."):
        if isinstance(current, list):
            try:
                current = current[int(part)]
            except (ValueError, IndexError):
                return None
        elif isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current


# ------------------------------------------------------------------------------------------
# probes: each kind states what a pass certifies, and returns (level, version, evidence)
# ------------------------------------------------------------------------------------------

def _probe_command(entry: dict, resolved: str | None, context: dict) -> tuple[str, str | None, dict]:
    probe = entry.get("probe") or {}
    reaches = probe.get("reaches", "VERSION_PROBED")
    base = context.get("base")
    steps = [{"path": resolved, "args": probe.get("args") or [],
              "expect_pattern": probe.get("expect_pattern")}]
    for extra in probe.get("also") or []:
        path = _inside(base, extra.get("path")) if base else None
        steps.append({"path": str(path) if path else None, "args": extra.get("args") or [],
                      "expect_pattern": extra.get("expect_pattern")})
    evidence: dict = {"steps": [], "kind": "command"}
    observed: str | None = None
    for step in steps:
        if not step["path"]:
            return UNAVAILABLE, None, {**evidence, "reason": "no declared executable resolved for this probe"}
        if Path(step["path"]).is_dir():
            # A directory is never a version source. This is the shape that let a model
            # directory be "probed" before: the honest record is that the declared location
            # exists, and that this probe certified nothing beyond that.
            return "FILE_EXISTS", None, {**evidence, "reaches_not_exceeded": True,
                                         "reason": f"probe target is a directory, so no version was "
                                                   f"certified: {step['path']}"}
        try:
            result = _run([step["path"], *step["args"]], env=_child_env(context.get("env") or {}),
                          timeout=int(probe.get("timeout_seconds") or DEFAULT_TIMEOUT))
        except (OSError, subprocess.SubprocessError) as error:
            return "probe_failed", None, {**evidence, "reason": f"{type(error).__name__}: {error}",
                                          "command": [step["path"], *step["args"]]}
        accept_rc = probe.get("accept_rc") or [0]
        text = _output(result, stderr_is_normal=bool(probe.get("stderr_is_normal")))
        line = _text_match(step["expect_pattern"], text)
        record = {"command": [Path(step["path"]).name, *step["args"]], "returncode": result.returncode,
                  "matched": line}
        evidence["steps"].append(record)
        if result.returncode not in accept_rc:
            return "probe_failed", None, {**evidence, "reason": f"returncode {result.returncode} not accepted"}
        if step["expect_pattern"] and line is None:
            return "probe_failed", None, {**evidence,
                                          "reason": f"output did not match {step['expect_pattern']!r}"}
        observed = observed or line
    if not observed:
        return "probe_failed", None, {**evidence, "reason": "probe produced no identifiable output"}
    return reaches, observed, evidence


def _probe_cmd_chain(entry: dict, context: dict) -> tuple[str, str | None, dict]:
    """Run the declared cmd lines from the declared working directory.

    MSVC's vcvars64.bat only initialises when called by name from its own directory on this
    host; an absolute-path `call` of the same file returns rc 1 with "The filename, directory
    name, or volume label syntax is incorrect" (measured 2026-10-08). The declaration carries
    the working form, so the probe stops inventing one — and stops recording the error text
    as a version.
    """
    probe = entry.get("probe") or {}
    reaches = probe.get("reaches", "VERSION_PROBED")
    base = context.get("base")
    if not base or not str(base).strip():
        return UNAVAILABLE, None, {"kind": "cmd_chain", "reason": "no declared external root"}
    cwd = _inside(base, probe.get("cwd")) or base
    if not Path(cwd).is_dir():
        return UNAVAILABLE, None, {"kind": "cmd_chain", "reason": f"declared cwd missing: {cwd}"}
    if os.name != "nt":
        return NOT_RUN, None, {"kind": "cmd_chain",
                               "reason": "cmd_chain needs a Windows host; this platform has no declared equivalent"}
    lines = ["@echo off", f'cd /d "{cwd}"', *(probe.get("lines") or [])]
    with tempfile.NamedTemporaryFile("w", suffix=".bat", delete=False, encoding="utf-8") as handle:
        handle.write("\r\n".join(lines) + "\r\n")
        script = handle.name
    try:
        result = _run(["cmd", "/c", script], env=_child_env(context.get("env") or {}),
                      timeout=int(probe.get("timeout_seconds") or 120))
    finally:
        os.unlink(script)
    text = _output(result)
    line = _text_match(probe.get("expect_pattern"), text)
    evidence = {"kind": "cmd_chain", "lines": probe.get("lines"), "returncode": result.returncode,
                "matched": line, "script_lines": len(lines)}
    if result.returncode != 0 or (probe.get("expect_pattern") and line is None):
        return "probe_failed", None, {**evidence,
                                      "reason": f"returncode {result.returncode}, pattern matched: {bool(line)}"}
    return reaches, line, evidence


def _probe_interpreter_import(entry: dict, context: dict) -> tuple[str, str | None, dict]:
    """Import the module with **its own interpreter**, never a wrapper binary's version."""
    probe = entry.get("probe") or {}
    reaches = probe.get("reaches", "VERSION_PROBED")
    interpreter_name = probe.get("interpreter")
    resolved = context.get("interpreters", {}).get(interpreter_name)
    if not resolved:
        return UNAVAILABLE, None, {"kind": "interpreter_import",
                                   "reason": f"declared interpreter {interpreter_name!r} did not resolve"}
    if Path(resolved).is_dir():
        return UNAVAILABLE, None, {"kind": "interpreter_import", "reason": "interpreter is a directory"}
    module = probe.get("module") or ""
    attribute = probe.get("version_attribute") or ""
    statement = (f"import {module}\n"
                 f"print(getattr(__import__({module!r}), {attribute!r}, '') or {module!r})")
    try:
        result = _run([resolved, "-B", "-c", statement], env=_child_env(context.get("env") or {}),
                      timeout=int(probe.get("timeout_seconds") or 120))
    except (OSError, subprocess.SubprocessError) as error:
        return "probe_failed", None, {"kind": "interpreter_import",
                                      "reason": f"{type(error).__name__}: {error}"}
    line = _text_match(probe.get("expect_pattern"), _output(result))
    evidence = {"kind": "interpreter_import", "interpreter": Path(resolved).name, "module": module,
                "returncode": result.returncode, "observed": line}
    if result.returncode != 0:
        return "probe_failed", None, {**evidence, "reason": f"import failed with rc {result.returncode}: "
                                                            f"{(result.stderr or '')[:200]}"}
    if not line:
        return "probe_failed", None, {**evidence, "reason": "module imported but reported no identity"}
    return reaches, line, evidence


def _probe_path_exists(entry: dict, context: dict) -> tuple[str, str | None, dict]:
    probe = entry.get("probe") or {}
    base = context.get("base")
    paths = probe.get("paths") or entry.get("external_paths") or []
    if not base or not paths:
        return UNAVAILABLE, None, {"kind": "path_exists", "reason": "no declared root or no declared path"}
    checked, missing = [], []
    for declared in paths:
        path = _inside(base, declared)
        if path is None:
            return UNAVAILABLE, None, {"kind": "path_exists",
                                       "reason": f"declaration left the root: {declared!r}"}
        present = path.is_file() or path.is_dir()
        checked.append({"declared": declared, "exists": present})
        if not present:
            missing.append(declared)
    if missing:
        return UNAVAILABLE, None, {"kind": "path_exists", "checked": checked,
                                   "reason": "declared path not present: " + ", ".join(missing)}
    return probe.get("reaches", "FILE_EXISTS"), None, {"kind": "path_exists", "checked": checked}


def _probe_glob_exists(entry: dict, context: dict) -> tuple[str, str | None, dict]:
    probe = entry.get("probe") or {}
    base = context.get("base")
    patterns = probe.get("patterns") or []
    if not base or not patterns:
        return UNAVAILABLE, None, {"kind": "glob_exists", "reason": "no declared root or pattern"}
    hits = []
    for pattern in patterns:
        if ".." in Path(pattern).parts or Path(pattern).is_absolute():
            return UNAVAILABLE, None, {"kind": "glob_exists", "reason": f"pattern left the root: {pattern!r}"}
        hits.extend(str(match) for match in Path(base).glob(pattern))
    if not hits:
        return UNAVAILABLE, None, {"kind": "glob_exists", "reason": "no declared pattern matched",
                                   "patterns": patterns}
    return probe.get("reaches", "FILE_EXISTS"), f"{len(hits)} asset(s) present", {
        "kind": "glob_exists", "matched": sorted(hits)[:3], "count": len(hits)}


def _probe_registry_key(entry: dict, context: dict) -> tuple[str, str | None, dict]:
    """Read a registry value directly — the detection a PowerShell healthcheck could never run."""
    probe = entry.get("probe") or {}
    reaches = probe.get("reaches", "VERSION_PROBED")
    if os.name != "nt":
        return NOT_RUN, None, {"kind": "registry_key",
                               "reason": "registry detection is Windows-specific; no declared equivalent here"}
    import winreg

    hives = {"HKLM": winreg.HKEY_LOCAL_MACHINE, "HKCU": winreg.HKEY_CURRENT_USER}
    wanted = [probe.get("hive"), probe.get("fallback_hive")]
    tried = []
    for name in wanted:
        if not name or name not in hives:
            continue
        tried.append(name)
        try:
            with winreg.OpenKey(hives[name], probe.get("key", "")) as key:
                value, _ = winreg.QueryValueEx(key, probe.get("value", ""))
        except OSError:
            continue
        text = str(value)
        line = _text_match(probe.get("expect_pattern"), text)
        if line is None:
            return "probe_failed", None, {"kind": "registry_key", "hives_tried": tried,
                                          "reason": f"value {text!r} did not match expectation"}
        return reaches, f"{probe.get('value')}={line}", {"kind": "registry_key", "hive": name,
                                                          "key": probe.get("key"), "tried": tried}
    return UNAVAILABLE, None, {"kind": "registry_key", "hives_tried": tried or list(hives),
                               "reason": "registry value not present on this host",
                               "key": probe.get("key")}


def _http(url: str, *, payload: bytes | None = None, timeout: int = 5) -> tuple[int | str, str]:
    import urllib.error
    import urllib.request

    request = urllib.request.Request(url, data=payload,
                                     headers={"Content-Type": "application/json"} if payload else {})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read(65536).decode("utf-8", "replace")
    except urllib.error.HTTPError as error:
        return error.code, error.read(2000).decode("utf-8", "replace")
    except Exception as error:  # noqa: BLE001 - a lane that is not answering is a measurement
        return f"{type(error).__name__}", str(error)[:300]


def _probe_http_get(entry: dict, context: dict) -> tuple[str, str | None, dict]:
    probe = entry.get("probe") or {}
    endpoint = entry.get("endpoint") or {}
    base_url = str(endpoint.get("base_url") or "")
    path = str(endpoint.get("list_path") or "")
    if not base_url:
        return UNAVAILABLE, None, {"kind": "http_get", "reason": "entry declares no endpoint base_url"}
    url = base_url.rstrip("/") + path
    status, body = _http(url, timeout=int(probe.get("timeout_seconds") or 5))
    evidence = {"kind": "http_get", "url": url, "status": status}
    if status != probe.get("expect_status", 200):
        return UNAVAILABLE, None, {**evidence, "reason": f"no HTTP {probe.get('expect_status', 200)} answer "
                                                          f"(observed {status}: {body[:120]})"}
    line = _text_match(probe.get("expect_pattern"), body)
    if probe.get("expect_pattern") and line is None:
        return "probe_failed", None, {**evidence, "reason": "answer did not match expectation",
                                      "body_head": body[:200]}
    observed = line
    if not observed:
        try:
            payload = json.loads(body)
            models = [item.get("id") or item.get("name") or "" for item in
                      (_json_path(payload, "data") or _json_path(payload, "models") or [])]
            observed = f"{len([m for m in models if m])} model(s) served"
        except ValueError:
            observed = f"HTTP {status}"
    return probe.get("reaches", "VERSION_PROBED"), observed, {**evidence, "observed": observed}


def _probe_http_roundtrip(entry: dict, context: dict) -> tuple[str, str | None, dict]:
    """Actually ask the lane to do its job; a model list is not a result."""
    probe = entry.get("probe") or {}
    endpoint = entry.get("endpoint") or {}
    base_url = str(endpoint.get("base_url") or "")
    path = str(endpoint.get("embed_path") or endpoint.get("list_path") or "")
    if not base_url:
        return UNAVAILABLE, None, {"kind": "http_roundtrip", "reason": "entry declares no endpoint base_url"}
    url = base_url.rstrip("/") + path
    template = probe.get("body_template") or "{}"
    body = template.replace("{model_id}", str(endpoint.get("model_id") or "")).encode("utf-8")
    status, text = _http(url, payload=body, timeout=int(probe.get("timeout_seconds") or 60))
    evidence = {"kind": "http_roundtrip", "url": url, "status": status}
    if status != probe.get("expect_status", 200):
        return UNAVAILABLE, None, {**evidence, "reason": f"no HTTP {probe.get('expect_status', 200)} "
                                                          f"answer (observed {status})"}
    try:
        payload = json.loads(text)
    except ValueError:
        return "probe_failed", None, {**evidence, "reason": "answer was not JSON", "body_head": text[:200]}
    if isinstance(payload, dict) and payload.get("error"):
        return "probe_failed", None, {**evidence, "reason": f"lane returned an error object: "
                                                             f"{str(payload['error'])[:180]}"}
    value = _json_path(payload, probe.get("expect_json_path", "")) if probe.get("expect_json_path") else None
    if not isinstance(value, list) or len(value) < int(probe.get("min_vector_length") or 1):
        return "probe_failed", None, {**evidence,
                                      "reason": f"{probe.get('expect_json_path')} was not a vector of the "
                                                f"declared minimum length"}
    return probe.get("reaches", "RESULT_VERIFIED"), f"{len(value)}-dim vector returned", {
        **evidence, "dimensions": len(value)}


def _probe_list_langs(entry: dict, resolved: str | None, context: dict) -> tuple[str, str | None, dict]:
    """Ask the declared engine to list the languages of **this** language pack.

    The pack is a directory, and a directory cannot answer `--version`; the honest probe runs
    the interpreter the entry names with `TESSDATA_PREFIX` set to this entry's own resolved
    path. Without that prefix tesseract dies with a `std::filesystem` abort (measured), so a
    bare listing is not evidence of anything.
    """
    probe = entry.get("probe") or {}
    interpreter = context.get("interpreters", {}).get(probe.get("interpreter"))
    if not interpreter:
        return UNAVAILABLE, None, {"kind": "list_langs",
                                   "reason": f"declared interpreter {probe.get('interpreter')!r} did not resolve"}
    if not resolved:
        return UNAVAILABLE, None, {"kind": "list_langs",
                                   "reason": "this entry's declared language directory did not resolve"}
    env = _child_env(context.get("env") or {})
    env["TESSDATA_PREFIX"] = str(resolved)
    try:
        result = _run([interpreter, "--list-langs"], env=env,
                      timeout=int(probe.get("timeout_seconds") or 60))
    except (OSError, subprocess.SubprocessError) as error:
        return "probe_failed", None, {"kind": "list_langs", "reason": f"{type(error).__name__}: {error}"}
    text = _output(result)
    evidence = {"kind": "list_langs", "returncode": result.returncode,
                "tessdata": Path(str(resolved)).name}
    if result.returncode != 0:
        return "probe_failed", None, {**evidence, "reason": f"rc {result.returncode}: {text[:180]}"}
    line = _text_match(probe.get("expect_pattern"), text)
    if line is None:
        return "probe_failed", None, {**evidence, "reason": "language listing did not match expectation",
                                      "head": text[:180]}
    labels = {item.strip() for item in text.splitlines()}
    required = [item for item in (probe.get("require_values") or []) if item not in labels]
    if required:
        return "probe_failed", None, {**evidence, "reason": f"required languages missing: {required}"}
    return probe.get("reaches", "RESULT_VERIFIED"), line, {**evidence, "observed": line}


def _probe_ocr_roundtrip(entry: dict, context: dict) -> tuple[str, str | None, dict]:
    """Render a known string, OCR it back, and require the string.

    This is the level AGENTS.md §7 actually depends on: a `tesseract --version` line says
    nothing about `TESSDATA_PREFIX`, and on this host the bare engine aborts on
    `--list-langs` with a `std::filesystem` error while a correctly bound engine reads the
    probe string back. The declaration names the expectation; a pass here is a result, not a
    version banner.
    """
    probe = entry.get("probe") or {}
    interpreter = context.get("interpreters", {}).get("tesseract")
    tessdata = (context.get("env") or {}).get("TESSDATA_PREFIX")
    if not interpreter:
        return UNAVAILABLE, None, {"kind": "ocr_roundtrip", "reason": "declared tesseract did not resolve"}
    if not tessdata or not Path(tessdata).is_dir():
        return UNAVAILABLE, None, {"kind": "ocr_roundtrip",
                                   "reason": "TESSDATA_PREFIX from required_env did not resolve"}
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError as error:
        return NOT_RUN, None, {"kind": "ocr_roundtrip",
                               "reason": f"no image library in the probing interpreter ({error})"}
    sentinel = "ARCHEAXIS OCR PROBE 42"
    windows = os.environ.get("WINDIR")
    if not windows:
        return NOT_RUN, None, {"kind": "ocr_roundtrip", "reason": "WINDIR is not declared"}
    fonts = Path(windows) / "Fonts"
    script = next((str(candidate) for candidate in (
        fonts / "arial.ttf", fonts / "segoeui.ttf", fonts / "calibri.ttf") if candidate.is_file()), None)
    if script is None:
        return NOT_RUN, None, {"kind": "ocr_roundtrip",
                               "reason": "no scalable font available to render the probe string"}
    directory = Path(context.get("workdir") or tempfile.gettempdir())
    directory.mkdir(parents=True, exist_ok=True)
    image_path = directory / "archeaxis-ocr-probe.png"
    try:
        image = Image.new("RGB", (1100, 220), "white")
        draw = ImageDraw.Draw(image)
        draw.text((40, 80), sentinel, fill="black", font=ImageFont.truetype(script, 64))
        image.save(image_path)
        result = _run([interpreter, str(image_path), "stdout", "--psm", "7", "-l", "eng"],
                      env=_child_env(context.get("env") or {}),
                      timeout=int(probe.get("timeout_seconds") or 120))
    except (OSError, subprocess.SubprocessError) as error:
        return "probe_failed", None, {"kind": "ocr_roundtrip", "reason": f"{type(error).__name__}: {error}"}
    text = _output(result)
    evidence = {"kind": "ocr_roundtrip", "returncode": result.returncode,
                "tessdata": Path(tessdata).name, "read_back": text.strip()[:160]}
    if result.returncode != 0:
        return "probe_failed", None, {**evidence, "reason": f"ocr run returned rc {result.returncode}"}
    line = _text_match(probe.get("expect_pattern"), text)
    if line is None:
        return "probe_failed", None, {**evidence,
                                      "reason": f"probe string not read back (expected {probe.get('expect_pattern')!r})"}
    return probe.get("reaches", "RESULT_VERIFIED"), line, evidence


PROBES = {
    "command": lambda entry, resolved, context: _probe_command(entry, resolved, context),
    "cmd_chain": lambda entry, resolved, context: _probe_cmd_chain(entry, context),
    "interpreter_import": lambda entry, resolved, context: _probe_interpreter_import(entry, context),
    "path_exists": lambda entry, resolved, context: _probe_path_exists(entry, context),
    "glob_exists": lambda entry, resolved, context: _probe_glob_exists(entry, context),
    "registry_key": lambda entry, resolved, context: _probe_registry_key(entry, context),
    "http_get": lambda entry, resolved, context: _probe_http_get(entry, context),
    "http_roundtrip": lambda entry, resolved, context: _probe_http_roundtrip(entry, context),
    "list_langs": lambda entry, resolved, context: _probe_list_langs(entry, resolved, context),
    "ocr_roundtrip": lambda entry, resolved, context: _probe_ocr_roundtrip(entry, context),
}


def run_probe(entry: dict, resolved: str | None, context: dict) -> tuple[str, str | None, dict]:
    """Execute the probe *entry* declares and return (level, observed identity, evidence).

    An entry that declares no probe is certified at `FILE_EXISTS` at most, and only when a
    declared path actually resolved: existence is a measurement, a version is not. That is the
    line the old code crossed when it ran `--version` against a `.bat` file and a directory and
    recorded whatever came back.
    """
    probe = entry.get("probe")
    if not isinstance(probe, dict) or not probe.get("kind"):
        if resolved and context.get("binding") == "declared":
            return "FILE_EXISTS", None, {"kind": None,
                                         "reason": "entry declares no probe; existence of the declared "
                                                   "path is the only claim made"}
        return NOT_RUN, None, {"kind": None,
                               "reason": "entry declares no probe; nothing was certified"}
    kind = str(probe["kind"])
    if kind == "not_run":
        return NOT_RUN, None, {"kind": "not_run", "reason": probe.get("reason") or "not run on this host"}
    handler = PROBES.get(kind)
    if handler is None:
        return NOT_RUN, None, {"kind": kind, "reason": "declared probe kind is not implemented"}
    return handler(entry, resolved, context)


def _level_rank(level: str) -> int:
    return LEVELS.index(level) if level in LEVELS else -1


def resolve(manifest: Path, *, probe: bool = True, workdir: Path | None = None) -> dict:
    if yaml is None:
        raise RuntimeError("PyYAML is required to resolve the environment registry")
    data = yaml.safe_load(manifest.read_text(encoding="utf-8")) or {}
    capabilities = data.get("capabilities", {})
    siblings_declaration = data.get("sibling_roots")
    root_value = os.environ.get("ARCHEAXIS_EXTERNAL_ROOT", "").strip() or os.environ.get("OS_EXTERNAL_CONFIG", "").strip()
    root: Path | None = None
    if root_value:
        candidate = Path(root_value).expanduser()
        root = candidate.resolve() if candidate.is_absolute() else None
    siblings = {name: path for name, path in (
        ((name, sibling_root(root, siblings_declaration, name))
         for name in (siblings_declaration or {})) if root else []
    ) if path is not None}
    interpreters: dict[str, str] = {}
    for group in capabilities.values():
        for entry in group or []:
            name = entry.get("name")
            if name and isinstance(name, str):
                found = _external_path(entry, root, siblings_declaration)
                if found:
                    interpreters[name] = found

    resolved_rows: list[dict] = []
    for category, entries in capabilities.items():
        for entry in entries or []:
            command = entry.get("healthcheck_command")
            executable = _command_name(command)
            declared_path = _external_path(entry, root, siblings_declaration)
            binding = "declared" if declared_path else None
            path = declared_path
            path_offering = None
            if executable and root is not None:
                path_offering = shutil.which(executable)
            elif executable:
                path_offering = shutil.which(executable)
            if not path and path_offering:
                # Recorded, never silently accepted as the project's binding.
                path = path_offering
                binding = "unbound_path_fallback"
            base = _entry_base(entry, root, siblings_declaration)
            context = {
                "root": root, "base": base, "siblings": siblings_declaration,
                "interpreters": interpreters,
                "binding": binding,
                "env": required_environment(entry, root, siblings_declaration),
                "workdir": str(workdir) if workdir else None,
            }
            if probe:
                level, observed, evidence = run_probe(entry, path, context)
            elif entry.get("external_paths") and declared_path:
                level, observed, evidence = "FILE_EXISTS", None, {"reason": "probing suppressed"}
            else:
                level, observed, evidence = NOT_RUN, None, {"reason": "probing suppressed"}
            declared_ceiling = (entry.get("probe") or {}).get("reaches")
            # A row that did not pass cannot exceed its ceiling: `ceiling_respected` asks only
            # whether what *was* certified sits at or below what the declaration claimed. Folding
            # a failing level in here would read "this row is unavailable" as "this row lied".
            exceeded = level in LEVELS and declared_ceiling in LEVELS and (
                _level_rank(level) > _level_rank(declared_ceiling))
            reachable = not exceeded
            resolved_rows.append({
                "id": f"{category}/{entry.get('name', '')}",
                "resource_id": entry.get("resource_id"),
                "type": entry.get("type"),
                "category": category,
                "name": entry.get("name"),
                "purpose": entry.get("purpose"),
                "version_range": entry.get("version_range"),
                "version_identification": entry.get("version_identification"),
                "platform": entry.get("platform"),
                "host_platform": host_platform(),
                "required_by": entry.get("required_by", []),
                "local_only": bool(entry.get("local_only", False)),
                "source_url": entry.get("source_url"),
                "license": entry.get("license"),
                "asset_license": entry.get("asset_license"),
                "project_entry": entry.get("project_entry"),
                "writability": entry.get("writability"),
                "fallback": entry.get("fallback"),
                "failure_message": entry.get("failure_message"),
                "healthcheck_command": command,
                "probe_kind": (entry.get("probe") or {}).get("kind"),
                "probe_ceiling": declared_ceiling,
                "executable": executable,
                "binding": binding,
                "path_also_offers": (Path(path_offering).name
                                     if path_offering and binding == "declared" else None),
                "declared_location": _declared_relative(entry, base),
                "available": level in LEVELS,
                "verification_level": level,
                "ceiling_respected": reachable,
                "resolved_path": _display_path(path, binding=binding),
                "version_observed": observed,
                "probe": {"probe_failed": "probe_failed"}.get(level, level),
                "probe_evidence": evidence,
                "required_env": {name: Path(value).name for name, value in context["env"].items()},
                "unavailable_reason": None if level in LEVELS else (evidence.get("reason")
                                                                     or entry.get("failure_message")),
            })
    counts = {level: sum(1 for item in resolved_rows if item["verification_level"] == level)
              for level in (*LEVELS, NOT_RUN, UNAVAILABLE, "probe_failed")}
    return {
        "schema": "archeaxis.environment-registry/v2",
        "manifest": str(manifest),
        "manifest_schema_version": data.get("schema_version"),
        "external_root": str(root) if root else None,
        "sibling_roots": {name: str(path) for name, path in siblings.items()},
        "capabilities": resolved_rows,
        "summary": {
            "total": len(resolved_rows),
            "available": sum(bool(item["available"]) for item in resolved_rows),
            "missing": sum(not bool(item["available"]) for item in resolved_rows),
        },
        "verification_summary": counts,
        "unbound_path_fallback": [item["id"] for item in resolved_rows
                                  if item["binding"] == "unbound_path_fallback"],
        "install_performed": False,
        "private_state_opened": False,
    }


def host_platform() -> str:
    """This host in the manifest's own vocabulary; used to refuse silently elsewhere."""
    import platform as _platform

    system = _platform.system().lower()
    machine = _platform.machine().lower()
    if system.startswith("win"):
        return "windows-x64" if machine in ("amd64", "x86_64") else f"windows-{machine}"
    if system == "linux":
        return "linux-x64" if machine in ("amd64", "x86_64") else f"linux-{machine}"
    if system == "darwin":
        return "macos-arm64" if machine == "arm64" else "macos-x64"
    return f"{system}-{machine}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--no-probe", action="store_true",
                        help="resolve and record declared bindings only, never certify a version")
    args = parser.parse_args()
    # The report carries declared Chinese purpose text; the console codepage would mangle it
    # into bytes a JSON reader cannot decode, so the emitter fixes its own encoding.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):  # pragma: no cover - a redirected stdout may not support it
        pass
    try:
        print(json.dumps(resolve(args.manifest.resolve(), probe=not args.no_probe),
                         ensure_ascii=False, indent=2))
    except (OSError, RuntimeError, ValueError) as error:
        print(json.dumps({"schema": "archeaxis.environment-registry/v2", "error": str(error)}))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
