# self_healing_agent/src/self_healing_agent/agent/service.py
import os
import json
from typing import Any
import uuid
from datetime import datetime,  timezone
import time
from self_healing_agent.agent.graph import build_graph
from self_healing_agent.core.models import IncidentPayload
from self_healing_agent.agent.state import AgentState

def run_incident(payload: IncidentPayload) -> dict[str, Any]:

    start_time_ms = int(time.time() * 1000)
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
        "decision_start_time_ms": start_time_ms,
        "timestamp_utc": datetime.now(timezone.utc).isoformat()
    }
    graph = build_graph()
    response = graph.invoke(state)
    return response


def _quick_test_main() -> None:
    samples = [
        (
            "Host Infra",
            ";System: ABCD , DC: CDC , MetricName: jvm mismatch ,Application: ABCD-JVM-STATUS for host: CDC-S POS-MS LP 2.0 ABCD Jvm Status Mismatch, 4 missing app-host-01:sample-assisted-msf-appointment-service:sample-assisted-msf-appointment-service01:3116 = missing,app-host-01:sample-assisted-msf-appointment-service:sample-assisted-msf-appointment-service02:3117 = missing,app-host-01:sample-assisted-msf-appointment-service:sample-assisted-msf-appointment-service01:3116 = missing,app-host-01:sample-assisted-msf-appointment-service:sample-assisted-msf-appointment-service02:3117 = missing, Instance: Reference List: CDC.POS-MS-LP.jvmlistx has jvm mismatch >= 0.0",
        ),
        # (
        #     "Service DC",
        #     "Reason: 3 hosts have oracle-db-gg-lag >= 510.0, Configured Host Capacity - 10;System: ABDC, DC: BDC, MetricName: oracle-db-gg-lag, Application: SPLEX-Common-Operations",
        # ),
        # (
        #     "System Instance",
        #     "Reason: mssql-sqldb-cpu-usage >= 95.0;System: EFGH ,DC: BDC ,MetricName: mssql-sqldb-cpu-usage ,Application: DASHBOARD-DB-MSSQL-WLS-DASHBOARD, Host: DB-HOST-01",
        # ),
        # (
        #     "System Instance",
        #     "Reason: oracle-db-session-blocker >= 1000.0;System: IJKL ,DC: AWS-E ,MetricName: oracle-db-session-blocker ,Application: Databases-MESSAGING, Host: db.example.com:2055",
        # ),
        
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
