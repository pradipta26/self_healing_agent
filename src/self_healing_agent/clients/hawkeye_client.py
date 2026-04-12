from __future__ import annotations

from typing import Any


# ------------------------------------------------------------------
# Dummy in-memory store (simulates Hawkeye backend)
# ------------------------------------------------------------------
# NOTE: This is only for local testing.
# Replace with real API calls later.


# ------------------------------------------------------------------
# 1. Get incident runtime status
# ------------------------------------------------------------------
def get_incident_runtime_status(incident_id: str) -> dict[str, Any]:
    """
    Simulates fetching incident status from Hawkeye.

    Possible statuses:
        - OPEN
        - PROCESSING
        - CLOSED

    Returns:
    {
        "incident_id": str,
        "status": str,
        "owner": str | None
    }
    """

    return {
        "incident_id": incident_id,
        "status": "OPEN",
        "owner": None,
    }


# ------------------------------------------------------------------
# 2. Claim incident if OPEN (compare-and-set semantics)
# ------------------------------------------------------------------
def claim_incident_if_open(incident_id: str, actor_id: str) -> dict[str, Any]:
    """
    Dummy compare-and-set style ownership claim.

    In real implementation:
    - if current status == OPEN, set to PROCESSING with owner=actor_id
    - else return current owner/status
    """
    return {
        "incident_id": incident_id,
        "claimed": True,
        "status": "PROCESSING",
        "owner": actor_id,
    }