"""M0 general learning chain contracts.

The contract keeps the first-use slice domain-scoped: typed knowledge
components feed learning objectives, which are carried by a general course
manifest and its source-grounded courseware artifacts.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.contracts.courseware_v1 import CoursewareArtifactV1

KnowledgeComponentKind = Literal["concept", "fact", "procedure", "method", "case"]


class KnowledgeComponentV1(BaseModel):
    """One typed, reusable unit in the general learning ontology."""

    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
        json_schema_extra={"$id": "https://archeaxis.local/contracts/v1/knowledge-component.schema.json"},
    )

    schema_: Literal["archeaxis.knowledge-component/v1"] = Field(
        default="archeaxis.knowledge-component/v1", alias="schema"
    )
    component_id: str = Field(min_length=1)
    kind: KnowledgeComponentKind
    title: str = Field(min_length=1)
    statement: str = Field(min_length=1)
    source_ids: list[str] = Field(default_factory=list)
    prerequisite_ids: list[str] = Field(default_factory=list)


class LearningObjectiveV1(BaseModel):
    """A learner-observable objective grounded in one or more components."""

    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
        json_schema_extra={"$id": "https://archeaxis.local/contracts/v1/learning-objective.schema.json"},
    )

    schema_: Literal["archeaxis.learning-objective/v1"] = Field(
        default="archeaxis.learning-objective/v1", alias="schema"
    )
    objective_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    statement: str = Field(min_length=1)
    knowledge_component_ids: list[str] = Field(min_length=1)


class CourseManifestV1(BaseModel):
    """A general-only course chain with linked components and artifacts."""

    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
        json_schema_extra={"$id": "https://archeaxis.local/contracts/v1/course-manifest.schema.json"},
    )

    schema_: Literal["archeaxis.course-manifest/v1"] = Field(
        default="archeaxis.course-manifest/v1", alias="schema"
    )
    manifest_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    domain_pack_id: Literal["general"]
    status: Literal["candidate", "ready", "blocked"]
    knowledge_components: list[KnowledgeComponentV1] = Field(min_length=1)
    learning_objectives: list[LearningObjectiveV1] = Field(min_length=1)
    artifacts: list[CoursewareArtifactV1] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_chain(self) -> CourseManifestV1:
        component_ids = [item.component_id for item in self.knowledge_components]
        if len(component_ids) != len(set(component_ids)):
            raise ValueError("knowledge component ids must be unique")
        component_id_set = set(component_ids)

        objective_ids = [item.objective_id for item in self.learning_objectives]
        if len(objective_ids) != len(set(objective_ids)):
            raise ValueError("learning objective ids must be unique")
        for objective in self.learning_objectives:
            unknown = set(objective.knowledge_component_ids) - component_id_set
            if unknown:
                raise ValueError(
                    "learning objective references unknown knowledge components: "
                    + ", ".join(sorted(unknown))
                )

        if not any(artifact.artifact_type == "lesson" for artifact in self.artifacts):
            raise ValueError("general course manifest requires a lesson artifact")
        artifact_ids = [artifact.artifact_id for artifact in self.artifacts]
        if len(artifact_ids) != len(set(artifact_ids)):
            raise ValueError("courseware artifact ids must be unique")
        for artifact in self.artifacts:
            if artifact.domain_pack_id != "general":
                raise ValueError("general course manifest cannot include another domain")
            unknown = set(artifact.knowledge_ids) - component_id_set
            if unknown:
                raise ValueError(
                    "courseware artifact references unknown knowledge components: "
                    + ", ".join(sorted(unknown))
                )
        return self
