# self_healing_agent/src/self_healing_agent/agent/service.py
import os
import json
from typing import Any
import uuid
from datetime import datetime, timezone

from self_healing_agent.agent.graph import build_graph
from self_healing_agent.core.models import IncidentPayload
from self_healing_agent.agent.state import AgentState

def run_incident(payload: IncidentPayload) -> dict[str, Any]:
    state: AgentState = {
        "trace_id": str(uuid.uuid4()),
        "incident_id": str(uuid.uuid4()),
        "incident_raw": payload.incident_details,
        "warnings": [],
        "trace": [],
        "error_flag": False,
        "error_message": None,
        "event_ids": [],
        "autonomy_mode": os.getenv("AUTONOMY_MODE", "SHADOW"),
        "kill_switch_state": os.getenv("KILL_SWITCH_STATE", "DISABLED"),
        "timestamp_utc": datetime.now(timezone.utc).isoformat()
    }
    graph = build_graph()
    response = graph.invoke(state)
    return response


def _quick_test_main() -> None:
    samples = [
        (
            "Host Infra",
            ";System: H0JV , DC: CDC , MetricName: jvm mismatch ,Application: H0JV-JVM-STATUS for host: CDC-S POS-MS LP 2.0 H0JV Jvm Status Mismatch, 4 missing tpswpsghzap007:onevz-assisted-msf-appointment-service:onevz-assisted-msf-appointment-service01:3116 = missing,tpswpsghzap007:onevz-assisted-msf-appointment-service:onevz-assisted-msf-appointment-service02:3117 = missing,tpswpsghzap008:onevz-assisted-msf-appointment-service:onevz-assisted-msf-appointment-service01:3116 = missing,tpswpsghzap008:onevz-assisted-msf-appointment-service:onevz-assisted-msf-appointment-service02:3117 = missing, Instance: Reference List: CDC.POS-MS-LP.jvmlistx has jvm mismatch >= 0.0",
        ),
        
    ]

    for idx, (label, details) in enumerate(samples, start=1):
        payload = IncidentPayload(incident_details=details)
        state: AgentState = run_incident(payload)
        print(f"state keys: {list(state.keys())}")
        print(f"\n[{idx}] {label}")
        print(json.dumps(state, indent=2))


if __name__ == "__main__":
    _quick_test_main()

# Execution command for quick test:
# cd self_healing_agent                                        
# PYTHONPATH=src python src/self_healing_agent/agent/service.py
