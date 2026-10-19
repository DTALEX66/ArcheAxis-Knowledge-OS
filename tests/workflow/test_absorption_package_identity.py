"""Package evidence must name a declared donor package, not a UI label."""
import importlib.util
from pathlib import Path


def test_tiptap_scoped_package_is_credited_but_similar_name_is_not():
    path = Path(__file__).resolve().parents[2] / 'scripts/audit/build_oss_absorption_crosswalk.py'
    spec = importlib.util.spec_from_file_location('package_identity_crosswalk', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    probe = module.ArtifactProbe.__new__(module.ArtifactProbe)
    probe.declared_packages = {module.norm('@tiptap/core'): ['frontend/package.json:dependencies'],
                              module.norm('xyflow-like-label'): ['frontend/package-lock.json:packages']}
    assert probe.package_declared(['Tiptap']) == {'Tiptap': ['frontend/package.json:dependencies']}
    assert probe.package_declared(['XYFlow']) == {}
