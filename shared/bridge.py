"""Retired IR → KB promotion bridges pending server-owned Phase 5 review provenance."""


def bridge_intake_to_kb(intake_card: dict) -> dict:
    """Reject intake promotion until Phase 5 provides server-owned review provenance."""
    del intake_card
    raise RuntimeError(
        "intake-to-KB promotion is disabled until server-owned review provenance exists"
    )


def bridge_contract_to_kb(contract: dict) -> dict:
    """Reject contract promotion until Phase 5 provides server-owned review provenance."""
    del contract
    raise RuntimeError(
        "contract-to-KB promotion is disabled until server-owned review provenance exists"
    )


def bridge_trending_to_kb(trending_repos: list[dict]) -> dict:
    """Reject the retired trending-to-KB persistence bypass."""
    del trending_repos
    raise RuntimeError("legacy trending bridge is disabled; use the canonical ResearchPackage API")
