"""R6 A13 Local Green candidate identity contract."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class LocalGreenIdentityV1(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    schema_: Literal["archeaxis.local-green-identity/v1"] = Field(
        default="archeaxis.local-green-identity/v1", alias="schema"
    )
    distribution: Literal["local-green"]
    public_release_base: Literal["v0.6.14"]
    source_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    source_tree: str = Field(pattern=r"^[0-9a-f]{40}$")
    build_timestamp: str = Field(min_length=1)
    runtime_manifest_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    published: Literal[False] = False
    candidate_status: Literal["staged", "verified", "replaced", "rolled_back"]
