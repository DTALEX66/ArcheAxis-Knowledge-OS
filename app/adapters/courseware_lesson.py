"""Local deterministic renderer for the first general lesson artifact."""

from __future__ import annotations

import hashlib
import re

from app.contracts.courseware_v1 import CoursewareArtifactV1
from app.contracts.general_learning_v1 import CourseManifestV1
from shared.obsidian_projection import (
    Projection,
    _extract_tags,
    _extract_wikilinks,
    _render_frontmatter,
    _render_output_lines,
)


def _path_segment(value: str) -> str:
    """Make an identifier safe and deterministic as a relative path segment."""
    segment = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip(".-")
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:10]
    reserved = {
        "con",
        "prn",
        "aux",
        "nul",
        *(f"com{i}" for i in range(1, 10)),
        *(f"lpt{i}" for i in range(1, 10)),
    }
    base_name = segment.split(".", 1)[0].casefold()
    # Keep ordinary IDs readable, but retain enough identity after any
    # lossy normalization so two source IDs cannot silently share a target.
    needs_disambiguation = (
        not segment
        or segment != value
        or segment.casefold() != segment
        or base_name in reserved
        or len(segment) > 120
    )
    if needs_disambiguation:
        suffix = f"--{digest}"
        prefix = (segment or "item")[: 120 - len(suffix)]
        segment = f"{prefix}{suffix}"
    return segment


def render_general_lesson(
    manifest: CourseManifestV1, artifact: CoursewareArtifactV1
) -> Projection:
    """Render one manifest-bound general lesson as a local Markdown projection.

    This adapter deliberately has no provider or runtime dependency.  The
    manifest and artifact remain the source of truth; the Markdown body and
    frontmatter are a deterministic derived projection.
    """
    if artifact.domain_pack_id != "general":
        raise ValueError("general domain renderer only accepts the general domain")
    if artifact.artifact_type != "lesson":
        raise ValueError("general lesson renderer only accepts a lesson artifact")

    bound = next(
        (item for item in manifest.artifacts if item.artifact_id == artifact.artifact_id),
        None,
    )
    if bound is None or bound.model_dump(mode="json") != artifact.model_dump(mode="json"):
        raise ValueError("artifact is not bound to the course manifest")
    if artifact.renderer != "native-lesson":
        raise ValueError("static native lesson renderer only supports renderer=native-lesson")
    if artifact.interactive:
        raise ValueError("static native lesson renderer requires interactive=false")

    frontmatter = {
        "manifest_id": manifest.manifest_id,
        "artifact_id": artifact.artifact_id,
        "domain_pack_id": artifact.domain_pack_id,
        "artifact_type": artifact.artifact_type,
        "source_ids": list(artifact.source_ids),
        "knowledge_ids": list(artifact.knowledge_ids),
        "renderer": artifact.renderer,
        "renderer_version": artifact.renderer_version,
        "tags": ["archeaxis", "courseware", "general", "lesson"],
    }

    selected_components = [
        component
        for component in manifest.knowledge_components
        if component.component_id in artifact.knowledge_ids
    ]
    selected_objectives = [
        objective
        for objective in manifest.learning_objectives
        if set(objective.knowledge_component_ids) & set(artifact.knowledge_ids)
    ]

    sections = [
        f"# {artifact.title}",
        "",
        f"Course: {manifest.title}",
        f"Manifest: `{manifest.manifest_id}`",
        f"Artifact: `{artifact.artifact_id}`",
        f"Renderer: `{artifact.renderer}@{artifact.renderer_version}`",
        "",
        "## Source References",
        "",
    ]
    sections.extend(f"- `{source_id}`" for source_id in artifact.source_ids)
    sections.extend(["", "## Knowledge Components", ""])
    sections.extend(
        f"- `{component.component_id}` ({component.kind}): {component.title} — {component.statement}"
        for component in selected_components
    )
    sections.extend(["", "## Learning Objectives", ""])
    sections.extend(
        f"- `{objective.objective_id}`: {objective.title} — {objective.statement}"
        for objective in selected_objectives
    )
    sections.extend(
        [
            "",
            "> [!note] Derived courseware projection",
            "> This lesson is rendered from a general CourseManifestV1 and remains source-grounded.",
            "",
        ]
    )

    body = "\n".join(sections)
    content = _render_frontmatter(frontmatter) + "\n" + _render_output_lines(body)
    return Projection(
        path=(
            f"Courses/{_path_segment(manifest.manifest_id)}"
            f"/{_path_segment(artifact.artifact_id)}.md"
        ),
        content=content,
        frontmatter=frontmatter,
        wikilinks=_extract_wikilinks(body),
        tags=_extract_tags(body, frontmatter),
        source=f"courseware:{manifest.manifest_id}:{artifact.artifact_id}",
    )
