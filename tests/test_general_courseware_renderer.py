from __future__ import annotations

import json

import pytest

from app.adapters.courseware_lesson import _path_segment, render_general_lesson
from app.contracts.general_learning_v1 import CourseManifestV1
from shared.obsidian_projection import Projection


def _manifest() -> CourseManifestV1:
    return CourseManifestV1.model_validate(
        {
            "manifest_id": "general-course-1",
            "title": "Evidence basics",
            "domain_pack_id": "general",
            "status": "candidate",
            "knowledge_components": [
                {
                    "component_id": "kc-concept",
                    "kind": "concept",
                    "title": "Evidence anchor",
                    "statement": "An anchor points to a source location.",
                },
                {
                    "component_id": "kc-procedure",
                    "kind": "procedure",
                    "title": "Record an anchor",
                    "statement": "Record the source revision before the location.",
                    "prerequisite_ids": ["kc-concept"],
                },
            ],
            "learning_objectives": [
                {
                    "objective_id": "obj-anchor",
                    "title": "Record evidence",
                    "statement": "The learner can record a source anchored claim.",
                    "knowledge_component_ids": ["kc-concept", "kc-procedure"],
                }
            ],
            "artifacts": [
                {
                    "artifact_id": "lesson-anchor",
                    "artifact_type": "lesson",
                    "title": "Anchored evidence lesson",
                    "domain_pack_id": "general",
                    "source_ids": ["source-candidate-1"],
                    "knowledge_ids": ["kc-concept", "kc-procedure"],
                    "renderer": "native-lesson",
                    "renderer_version": "1.0.0",
                    "status": "candidate",
                    "interactive": False,
                }
            ],
        }
    )


def test_general_lesson_renderer_preserves_bound_contract_fields() -> None:
    manifest = _manifest()
    artifact = manifest.artifacts[0]

    projection = render_general_lesson(manifest, artifact)

    assert isinstance(projection, Projection)
    assert projection.path == "Courses/general-course-1/lesson-anchor.md"
    assert projection.frontmatter == {
        "manifest_id": "general-course-1",
        "artifact_id": "lesson-anchor",
        "domain_pack_id": "general",
        "artifact_type": "lesson",
        "source_ids": ["source-candidate-1"],
        "knowledge_ids": ["kc-concept", "kc-procedure"],
        "renderer": "native-lesson",
        "renderer_version": "1.0.0",
        "tags": ["archeaxis", "courseware", "general", "lesson"],
    }
    assert "source-candidate-1" in projection.content
    assert "kc-concept" in projection.content
    assert "native-lesson@1.0.0" in projection.content


def test_general_lesson_renderer_is_deterministic_and_readable_as_receipt() -> None:
    manifest = _manifest()
    artifact = manifest.artifacts[0]

    first = render_general_lesson(manifest, artifact)
    second = render_general_lesson(manifest, artifact)

    assert (first.path, first.content, first.frontmatter) == (
        second.path,
        second.content,
        second.frontmatter,
    )
    receipt = json.loads(json.dumps(first.frontmatter, sort_keys=True))
    assert receipt["manifest_id"] == "general-course-1"
    assert receipt["artifact_id"] == "lesson-anchor"
    assert receipt["source_ids"] == ["source-candidate-1"]
    assert receipt["knowledge_ids"] == ["kc-concept", "kc-procedure"]


@pytest.mark.parametrize(
    "changes, message",
    [
        ({"domain_pack_id": "programming"}, "general domain"),
        ({"artifact_type": "quiz"}, "lesson artifact"),
    ],
)
def test_general_lesson_renderer_rejects_non_general_or_non_lesson(
    changes: dict[str, str], message: str
) -> None:
    manifest = _manifest()
    artifact = manifest.artifacts[0].model_copy(update=changes)

    with pytest.raises(ValueError, match=message):
        render_general_lesson(manifest, artifact)


def test_general_lesson_renderer_rejects_artifact_not_bound_to_manifest() -> None:
    manifest = _manifest()
    artifact = manifest.artifacts[0].model_copy(
        update={"artifact_id": "other-lesson", "title": "Other lesson"}
    )

    with pytest.raises(ValueError, match="not bound to the course manifest"):
        render_general_lesson(manifest, artifact)


def test_path_segments_disambiguate_lossy_ids_and_windows_reserved_names() -> None:
    slash_id = _path_segment("a/b")
    dash_id = _path_segment("a-b")

    assert slash_id != dash_id
    assert "/" not in slash_id
    assert "\\" not in slash_id
    assert _path_segment("CON").casefold() != "con"
    assert _path_segment("   ").startswith("item--")
