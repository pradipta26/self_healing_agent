import os
import json
from typing import Any
import uuid
from datetime import datetime,  timezone
import time
from self_healing_agent.agent.graph import build_graph
from self_healing_agent.core.models import IncidentPayload
from self_healing_agent.agent.state import AgentState
from self_healing_agent.config.config_loader import load_env_from_config
from functools import lru_cache
from langgraph.checkpoint.memory import InMemorySaver

load_env_from_config("dev")

# InMemorySaver is a temporary V1 checkpointer for local HITL testing, to be replaced by a durable checkpointer later.
@lru_cache(maxsize=1)
def get_graph():
    checkpointer = InMemorySaver()
    return build_graph(checkpointer=checkpointer)

def run_incident(payload: IncidentPayload) -> dict[str, Any]:

    start_time_ms = int(time.time() * 1000)
    thread_id = str(uuid.uuid4())
    state: AgentState = {
        "trace_id": str(uuid.uuid4()),
        "incident_id": str(uuid.uuid4()),
        "thread_id": thread_id,
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
    graph = get_graph()
    config = {"configurable": {"thread_id": thread_id}}
    response = graph.invoke(state, config=config)
    return response


def _quick_test_main() -> None:
    samples = [
        (
            "Host Infra",
            ";System: H0JV , DC: CDC , MetricName: jvm mismatch ,Application: H0JV-JVM-STATUS for host: CDC-S POS-MS LP 2.0 H0JV Jvm Status Mismatch, 4 missing tpswpsghzap007:onevz-assisted-msf-appointment-service:onevz-assisted-msf-appointment-service01:3116 = missing,tpswpsghzap007:onevz-assisted-msf-appointment-service:onevz-assisted-msf-appointment-service02:3117 = missing,tpswpsghzap008:onevz-assisted-msf-appointment-service:onevz-assisted-msf-appointment-service01:3116 = missing,tpswpsghzap008:onevz-assisted-msf-appointment-service:onevz-assisted-msf-appointment-service02:3117 = missing, Instance: Reference List: CDC.POS-MS-LP.jvmlistx has jvm mismatch >= 0.0",
        ),
        # (
        #     "Service DC",
        #     "Reason: 3 hosts have oracle-db-gg-lag >= 510.0, Configured Host Capacity - 10;System: BRHV, DC: BDC, MetricName: oracle-db-gg-lag, Application: SPLEX-Common-Operations",
        # ),
        # (
        #     "System Instance",
        #     "Reason: mssql-sqldb-cpu-usage >= 95.0;System: RTVV ,DC: BDC ,MetricName: mssql-sqldb-cpu-usage ,Application: VZDASH-DB-MSSQL-WLS-VZDASH, Host: TDCWPRTVVD003",
        # ),
        # (
        #     "System Instance",
        #     "Reason: oracle-db-session-blocker >= 1000.0;System: CHHV ,DC: AWS-E ,MetricName: oracle-db-session-blocker ,Application: Databases-ONEMSG, Host: onmsrpte.cleqqvmifzmp.us-east-1.rds.amazonaws.com:2055",
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
