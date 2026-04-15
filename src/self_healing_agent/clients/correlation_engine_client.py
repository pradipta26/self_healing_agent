from __future__ import annotations

from typing import Any


_INCIDENT_STORE: dict[str, dict[str, Any]] = {}


def get_incident_runtime_status(incident_id: str) -> dict[str, Any]:
    incident = _INCIDENT_STORE.get(incident_id)

    if not incident:
        return {
            "incident_id": incident_id,
            "status": "OPEN",
            "owner": None,
        }

    return {
        "incident_id": incident_id,
        "status": incident.get("status", "OPEN"),
        "owner": incident.get("owner"),
    }


def claim_incident_if_open(incident_id: str, actor_id: str) -> dict[str, Any]:
    incident = _INCIDENT_STORE.get(incident_id)

    if not incident:
        _INCIDENT_STORE[incident_id] = {
            "status": "PROCESSING",
            "owner": actor_id,
        }
        return {
            "incident_id": incident_id,
            "claimed": True,
            "status": "PROCESSING",
            "owner": actor_id,
        }

    current_status = str(incident.get("status", "OPEN")).upper()
    current_owner = incident.get("owner")

    if current_status == "OPEN":
        incident["status"] = "PROCESSING"
        incident["owner"] = actor_id
        return {
            "incident_id": incident_id,
            "claimed": True,
            "status": "PROCESSING",
            "owner": actor_id,
        }

    return {
        "incident_id": incident_id,
        "claimed": False,
        "status": current_status,
        "owner": current_owner,
    }


def update_incident_status(
    incident_id: str,
    status: str,
    owner: str | None = None,
) -> dict[str, Any]:
    normalized_status = status.strip().upper()

    if normalized_status not in {"OPEN", "PROCESSING", "CLOSED"}:
        raise ValueError(f"Unsupported incident status: {status}")

    incident = _INCIDENT_STORE.get(incident_id, {})
    incident["status"] = normalized_status
    incident["owner"] = owner
    _INCIDENT_STORE[incident_id] = incident

    return {
        "incident_id": incident_id,
        "status": normalized_status,
        "owner": owner,
    }