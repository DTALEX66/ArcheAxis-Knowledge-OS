"""Project scorer — evaluates GitHub/AI projects on 6 dimensions."""
from dataclasses import dataclass


@dataclass
class ProjectScores:
    token_saving: float = 0.0
    efficiency_gain: float = 0.0
    local_first: float = 0.0
    system_fit: float = 0.0
    risk_penalty: float = 0.0
    total: float = 0.0
    qualifies: bool = False


def score_project(
    token_saving: float = 0.0,
    efficiency_gain: float = 0.0,
    local_first: float = 0.0,
    system_fit: float = 0.0,
    risk_penalty: float = 0.0,
    risk_level: str = "low",
    threshold: float = 3.5,
) -> ProjectScores:
    total = token_saving + efficiency_gain + local_first + system_fit - risk_penalty
    qualifies = total >= threshold and risk_level != "critical"
    return ProjectScores(
        token_saving=token_saving,
        efficiency_gain=efficiency_gain,
        local_first=local_first,
        system_fit=system_fit,
        risk_penalty=risk_penalty,
        total=round(total, 2),
        qualifies=qualifies,
    )
