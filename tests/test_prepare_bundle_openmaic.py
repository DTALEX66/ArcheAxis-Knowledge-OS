"""OpenMAIC Node donor resolution for the desktop bundle build."""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from desktop.scripts import prepare_bundle


def distribution(tmp_path: Path, *, with_license: bool = True, node_bytes: bytes = b"synthetic node\n") -> Path:
    directory = tmp_path / "node-v24.21.0-win-x64"
    directory.mkdir()
    (directory / "node.exe").write_bytes(node_bytes)
    if with_license:
        (directory / "LICENSE").write_bytes(b"synthetic Node licence\n")
    return directory


def test_a_distribution_directory_resolves_node_license_and_digest(tmp_path):
    directory = distribution(tmp_path)
    node, digest, license_file = prepare_bundle.resolve_openmaic_donor(node_dir=directory)
    assert node == directory / "node.exe"
    assert digest == hashlib.sha256((directory / "node.exe").read_bytes()).hexdigest()
    assert license_file == directory / "LICENSE"


def test_the_explicit_trio_is_checked_against_the_selected_file(tmp_path):
    directory = distribution(tmp_path)
    node = directory / "node.exe"
    license_file = directory / "LICENSE"
    digest = hashlib.sha256(node.read_bytes()).hexdigest()
    assert prepare_bundle.resolve_openmaic_donor(
        node=node, node_sha256=digest, node_license=license_file) == (node, digest, license_file)
    with pytest.raises(ValueError, match="does not match"):
        prepare_bundle.resolve_openmaic_donor(
            node=node, node_sha256="0" * 64, node_license=license_file)


def test_directory_and_explicit_forms_cannot_be_mixed(tmp_path):
    directory = distribution(tmp_path)
    with pytest.raises(ValueError, match="either"):
        prepare_bundle.resolve_openmaic_donor(
            node_dir=directory, node=directory / "node.exe",
            node_sha256="0" * 64, node_license=directory / "LICENSE")


def test_a_missing_member_or_partial_trio_is_named(tmp_path):
    directory = distribution(tmp_path, with_license=False)
    with pytest.raises(ValueError, match="LICENSE"):
        prepare_bundle.resolve_openmaic_donor(node_dir=directory)
    with pytest.raises(ValueError, match="together"):
        prepare_bundle.resolve_openmaic_donor(
            node=directory / "node.exe", node_sha256="0" * 64)


def test_no_donor_means_no_openmaic(tmp_path):
    assert prepare_bundle.resolve_openmaic_donor() is None
