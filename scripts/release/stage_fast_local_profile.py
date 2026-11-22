"""Build the offline fast-local supplement for the published Windows backend."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

if __package__:
    from . import stage_backend_runtime as stage
else:
    import stage_backend_runtime as stage


REPOSITORY = Path(__file__).resolve().parents[2]
PUBLISHED_MANIFEST = "d3fb02efa1b42f0bb128fd2c626363cec6004efb785bf2c09ad0cf35c8f2d6c5"
BORROWED = ("core/archeaxis-api.exe", "runtime/python.exe", "worker-profile.json",
            "workers/openmaic/node.exe", "workers/openmaic/NODE-LICENSE")
MANIFEST = "fast-local-profile.json"


def backend_members(backend: Path) -> dict:
    path = stage.growth.safe(backend / "backend-runtime-manifest.json")
    data = stage.filesystem_path(path).read_bytes()
    if hashlib.sha256(data).hexdigest() != PUBLISHED_MANIFEST:
        raise ValueError("Expected the published 0b014775 Windows backend manifest")
    recorded = json.loads(data)["files"]
    borrowed = {name: recorded[name] for name in BORROWED}
    for name, identity in borrowed.items():
        path = stage.growth.safe(backend / name)
        if stage.filesystem_path(path).stat().st_size != identity["bytes"] or stage.sha256(path) != identity["sha256"]:
            raise ValueError(f"Published backend resource changed: {name}")
    return borrowed


def stage_profile(backend: Path, sdk_donor: Path, output: Path) -> Path:
    backend, sdk_donor, output = (stage.growth.safe(path) for path in (backend, sdk_donor, output))
    if output.exists() or any(output.is_relative_to(path) for path in (backend, sdk_donor)):
        raise ValueError("Use a fresh supplement directory outside the selected inputs")
    borrowed = backend_members(backend)
    sdk = stage.lmstudio_sdk_plan(sdk_donor)
    release = REPOSITORY / "scripts/release"
    workers = REPOSITORY / "services/python-workers"
    sources = {
        "start-backend.py": release / "backend_launcher.py",
        "start-fast-local.cmd": release / "fast_local_profile/start-fast-local.cmd",
        "README.zh-CN.md": release / "fast_local_profile/README.zh-CN.md",
        "workers/tool_paths.py": workers / "tool_paths.py",
        "workers/transport/text_ndjson.py": workers / "transport/text_ndjson.py",
        "shared/safe_http.py": REPOSITORY / "shared/safe_http.py",
        "shared/llm_adapter.py": REPOSITORY / "shared-contracts/adapters/llm/litellm_adapter.py",
    }
    for source in (workers / "machine").iterdir():
        if source.suffix == ".py" or source.name == "lmstudio_structured.mjs":
            sources[f"workers/machine/{source.name}"] = source
    for name in ("worker_machine_answer.py", "worker_machine_fast_local.py", "lmstudio_structured.mjs"):
        if f"workers/machine/{name}" not in sources:
            raise ValueError(f"Required machine worker input missing: {name}")
    copies = {name: (source, stage.growth.row(source)) for name, source in sources.items()}
    sdk_prefix = stage.LMSTUDIO_DIRECTORY + "/"
    copies.update({sdk_prefix + name: value for name, value in sdk.items()})
    rows = {name: row for name, (_, row) in copies.items()}

    # The source has machine-specific examples in comments. Preserve the tool
    # declarations in their original line layout for the worker's YAML reader.
    config = REPOSITORY / "config/environment/capability-requirements.yaml"
    lines = config.read_text(encoding="utf-8").splitlines()
    declarations = ("\n".join(line for line in lines if not line.lstrip().startswith("#")) + "\n").encode("utf-8")
    capability = "workers/capability-requirements.yaml"
    rows[capability] = {"bytes": len(declarations), "sha256": hashlib.sha256(declarations).hexdigest()}
    profile = {"schema": "archeaxis.fast-local-supplement/v1", "profile": "fast-local",
               "backend_manifest_sha256": PUBLISHED_MANIFEST, "borrowed_backend_members": borrowed,
               "lmstudio_sdk": stage.runtime_resources.lmstudio_sdk_manifest(True), "files": rows}
    manifest = (json.dumps(profile, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    inputs = {source: row for source, row in copies.values()}
    projected = sum(row["bytes"] for row in rows.values()) + len(manifest)
    with stage.growth.batch(output, inputs, projected):
        stage.filesystem_path(output).mkdir(parents=True, exist_ok=False)
        for name, (source, identity) in copies.items():
            target = output / name
            stage.filesystem_path(target.parent).mkdir(parents=True, exist_ok=True)
            stage.growth.copy2(source, target, identity=identity)
        stage.filesystem_path(output / capability).write_bytes(declarations)
        stage.filesystem_path(output / MANIFEST).write_bytes(manifest)
    return output / MANIFEST


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend-root", required=True, type=Path, help="published backend directory")
    parser.add_argument("--lmstudio-sdk-dir", required=True, type=Path, help="offline installation of the locked npm packages")
    parser.add_argument("--out", required=True, type=Path, help="new supplement payload directory")
    args = parser.parse_args()
    print(stage_profile(args.backend_root, args.lmstudio_sdk_dir, args.out))


if __name__ == "__main__":
    main()
