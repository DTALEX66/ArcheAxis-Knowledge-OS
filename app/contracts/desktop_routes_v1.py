"""R6 A12 Avalonia route-to-Core manifest contract."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class DesktopRouteV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    page_id: Literal["knowledge", "source_reader", "learning", "jobs", "machine_assets", "settings", "recovery"]
    core_endpoint: str = Field(pattern=r"^/api/v1/\S+$")
    read_only: bool


class DesktopRouteManifestV1(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    schema_: Literal["archeaxis.desktop-routes/v1"] = Field(
        default="archeaxis.desktop-routes/v1", alias="schema"
    )
    shell_project: Literal["apps/ArcheAxis.Desktop"]
    routes: list[DesktopRouteV1] = Field(min_length=7)
    canonical_writer: Literal["archeaxis-core-rust-sqlite"]
