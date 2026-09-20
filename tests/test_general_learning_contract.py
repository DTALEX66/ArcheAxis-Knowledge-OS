from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.contracts.general_learning_v1 import (
    CourseManifestV1,
    KnowledgeComponentV1,
    LearningObjectiveV1,
)


def test_general_learning_contract_is_available_for_a_complete_chain() -> None:
    manifest = CourseManifestV1.model_validate(
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

    assert manifest.domain_pack_id == "general"
    assert {item.kind for item in manifest.knowledge_components} == {
        "concept",
        "procedure",
    }
    assert manifest.learning_objectives[0].knowledge_component_ids == [
        "kc-concept",
        "kc-procedure",
    ]
    assert manifest.artifacts[0].artifact_type == "lesson"


def test_general_knowledge_component_kinds_are_explicit() -> None:
    component_type = KnowledgeComponentV1
    assert {
        component_type.model_validate(
            {
                "component_id": f"kc-{kind}",
                "kind": kind,
                "title": kind.title(),
                "statement": f"A general {kind}.",
            }
        ).kind
        for kind in ("concept", "fact", "procedure", "method", "case")
    } == {"concept", "fact", "procedure", "method", "case"}


def test_general_manifest_rejects_cross_domain_or_broken_links() -> None:
    component = {
        "component_id": "kc-1",
        "kind": "fact",
        "title": "Fact",
        "statement": "A fact.",
    }
    objective = {
        "objective_id": "obj-1",
        "title": "Use the fact",
        "statement": "The learner can use the fact.",
        "knowledge_component_ids": ["kc-1"],
    }
    artifact = {
        "artifact_id": "artifact-1",
        "artifact_type": "lesson",
        "title": "Lesson",
        "domain_pack_id": "general",
        "source_ids": ["source-1"],
        "knowledge_ids": ["kc-1"],
        "renderer": "native-lesson",
        "renderer_version": "1.0.0",
        "status": "candidate",
        "interactive": False,
    }
    base = {
        "manifest_id": "manifest-1",
        "title": "General course",
        "domain_pack_id": "general",
        "status": "candidate",
        "knowledge_components": [component],
        "learning_objectives": [objective],
        "artifacts": [artifact],
    }
    with pytest.raises(ValidationError, match="unknown knowledge components"):
        CourseManifestV1.model_validate(
            {**base, "learning_objectives": [{**objective, "knowledge_component_ids": ["missing"]}]}
        )
    with pytest.raises(ValidationError, match="another domain"):
        CourseManifestV1.model_validate(
            {**base, "artifacts": [{**artifact, "domain_pack_id": "programming"}]}
        )
    with pytest.raises(ValidationError, match="lesson artifact"):
        CourseManifestV1.model_validate(
            {**base, "artifacts": [{**artifact, "artifact_type": "quiz"}]}
        )


def test_general_manifest_rejects_unknown_and_cyclic_prerequisites() -> None:
    component = {
        "component_id": "kc-1",
        "kind": "fact",
        "title": "Fact",
        "statement": "A fact.",
    }
    objective = {
        "objective_id": "obj-1",
        "title": "Use the fact",
        "statement": "The learner can use the fact.",
        "knowledge_component_ids": ["kc-1"],
    }
    artifact = {
        "artifact_id": "artifact-1",
        "artifact_type": "lesson",
        "title": "Lesson",
        "domain_pack_id": "general",
        "source_ids": ["source-1"],
        "knowledge_ids": ["kc-1"],
        "renderer": "native-lesson",
        "renderer_version": "1.0.0",
        "status": "candidate",
        "interactive": False,
    }
    base = {
        "manifest_id": "manifest-1",
        "title": "General course",
        "domain_pack_id": "general",
        "status": "candidate",
        "knowledge_components": [component],
        "learning_objectives": [objective],
        "artifacts": [artifact],
    }

    with pytest.raises(ValidationError, match="unknown prerequisite"):
        CourseManifestV1.model_validate(
            {
                **base,
                "knowledge_components": [
                    {**component, "prerequisite_ids": ["missing"]}
                ],
            }
        )
    with pytest.raises(ValidationError, match="cannot prerequisite itself"):
        CourseManifestV1.model_validate(
            {
                **base,
                "knowledge_components": [
                    {**component, "prerequisite_ids": ["kc-1"]}
                ],
            }
        )
    with pytest.raises(ValidationError, match="prerequisite cycle"):
        CourseManifestV1.model_validate(
            {
                **base,
                "knowledge_components": [
                    {**component, "prerequisite_ids": ["kc-2"]},
                    {
                        **component,
                        "component_id": "kc-2",
                        "prerequisite_ids": ["kc-1"],
                    },
                ],
                "learning_objectives": [
                    {**objective, "knowledge_component_ids": ["kc-1", "kc-2"]}
                ],
                "artifacts": [
                    {**artifact, "knowledge_ids": ["kc-1", "kc-2"]}
                ],
            }
        )


def test_general_manifest_rejects_artifact_components_without_learning_objectives() -> None:
    component = {
        "component_id": "kc-uncovered",
        "kind": "fact",
        "title": "Uncovered fact",
        "statement": "A fact needs an objective before it can appear in a lesson.",
    }
    objective = {
        "objective_id": "obj-other",
        "title": "Different objective",
        "statement": "The learner can use a different component.",
        "knowledge_component_ids": ["kc-other"],
    }
    other_component = {
        "component_id": "kc-other",
        "kind": "concept",
        "title": "Other concept",
        "statement": "Another component.",
    }
    artifact = {
        "artifact_id": "lesson-uncovered",
        "artifact_type": "lesson",
        "title": "Lesson with uncovered component",
        "domain_pack_id": "general",
        "source_ids": ["source-1"],
        "knowledge_ids": ["kc-uncovered"],
        "renderer": "native-lesson",
        "renderer_version": "1.0.0",
        "status": "candidate",
        "interactive": False,
    }

    with pytest.raises(ValidationError, match="without learning objectives: kc-uncovered"):
        CourseManifestV1.model_validate(
            {
                "manifest_id": "manifest-uncovered",
                "title": "General course",
                "domain_pack_id": "general",
                "status": "candidate",
                "knowledge_components": [component, other_component],
                "learning_objectives": [objective],
                "artifacts": [artifact],
            }
        )


def test_general_learning_contract_schema_ids_are_stable() -> None:
    assert KnowledgeComponentV1.model_json_schema()["$id"].endswith(
        "knowledge-component.schema.json"
    )
    assert LearningObjectiveV1.model_json_schema()["$id"].endswith(
        "learning-objective.schema.json"
    )
    assert CourseManifestV1.model_json_schema()["$id"].endswith(
        "course-manifest.schema.json"
    )
