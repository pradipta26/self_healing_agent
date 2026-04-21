import os
import json
from typing import Any
import uuid
from datetime import datetime,  timezone
import time
from self_healing_agent.agent.graph import build_graph
from self_healing_agent.agent.ingress.incident_lock import (
    try_acquire_incident_workflow_lock,
    mark_incident_workflow_completed,
    mark_incident_workflow_failed,
)
from self_healing_agent.core.models import IncidentPayload
from self_healing_agent.agent.state import AgentState
from self_healing_agent.config.config_loader import load_env_from_config
from functools import lru_cache
from langgraph.checkpoint.memory import InMemorySaver
from self_healing_agent.clients.hawkeye_client import update_incident_status
from self_healing_agent.observability.metrics import emit_counter, emit_histogram
from self_healing_agent.observability.metrics_contract import (
    AGENT_RUNS_STARTED,
    AGENT_RUNS_COMPLETED,
    AGENT_RUNS_FAILED,
    AGENT_RUN_LATENCY_MS,
)

load_env_from_config("dev")

# InMemorySaver is a temporary V1 checkpointer for local HITL testing, to be replaced by a durable checkpointer later.
@lru_cache(maxsize=1)
def get_graph():
    checkpointer = InMemorySaver()
    return build_graph(checkpointer=checkpointer)

def run_incident(payload: IncidentPayload) -> dict[str, Any]:
    
    start_time_ms = int(time.time() * 1000)
    now_utc = datetime.now(timezone.utc).isoformat()
    he_incident_id = getattr(payload, "hawkeye_incident_id", None)
    if not he_incident_id:
        return {
            "incident_raw": getattr(payload, "incident_details", ""),
            "warnings": ["MISSING_HAWKEYE_INCIDENT_ID"],
            "trace": ["run_incident:missing_hawkeye_incident_id"],
            "error_flag": True,
            "error_message": "Missing required field 'hawkeye_incident_id' in payload.",
            "event_ids": [],
            "autonomy_mode": os.getenv("AUTONOMY_MODE", "SHADOW"),
            "kill_switch_state": os.getenv("KILL_SWITCH_STATE", "DISABLED"),
            "decision_start_time_ms": start_time_ms,
            "timestamp_utc": now_utc,
        }
    
    thread_id = str(uuid.uuid4())
    state: AgentState = {
        "trace_id": str(uuid.uuid4()),
        "incident_id": str(uuid.uuid4()),
        "source_incident_id": he_incident_id,
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
        "timestamp_utc": now_utc
    }
    emit_counter(
        AGENT_RUNS_STARTED,
        autonomy_mode=state["autonomy_mode"],
        kill_switch_state=state["kill_switch_state"],
    )
    # Add Ingress Idempotency Checkpoint
    lock = try_acquire_incident_workflow_lock(
        hawkeye_incident_id=he_incident_id,
        incident_id=state["incident_id"],
        thread_id=thread_id,
    )

    if not lock["acquired"]:
        workflow_status = lock.get("workflow_status")
        if workflow_status == "ACTIVE":
            return {
                "status": "DUPLICATE_IGNORED",
                "source_incident_id": he_incident_id,
                "existing_thread_id": lock.get("existing_thread_id"),
                "existing_incident_id": lock.get("existing_incident_id"),
                "existing_decision_id": lock.get("decision_id"),
                "workflow_status": workflow_status,
            }

        return {
            "status": "INGRESS_LOCK_NOT_ACQUIRED",
            "source_incident_id": he_incident_id,
            "existing_thread_id": lock.get("existing_thread_id"),
            "existing_incident_id": lock.get("existing_incident_id"),
            "existing_decision_id": lock.get("decision_id"),
            "workflow_status": workflow_status,
        }

    graph = get_graph()
    config = {"configurable": {"thread_id": thread_id}}
    response = graph.invoke(state, config=config)

    run_latency_ms = int(time.time() * 1000) - start_time_ms
    emit_histogram(
        AGENT_RUN_LATENCY_MS,
        run_latency_ms,
        autonomy_mode=state["autonomy_mode"],
        kill_switch_state=state["kill_switch_state"],
    )

    if response.get("error_flag", False):
        emit_counter(
            AGENT_RUNS_FAILED,
            autonomy_mode=state["autonomy_mode"],
            kill_switch_state=state["kill_switch_state"],
        )
    else:
        emit_counter(
            AGENT_RUNS_COMPLETED,
            autonomy_mode=state["autonomy_mode"],
            kill_switch_state=state["kill_switch_state"],
        )

    decision_id = response.get("decision_id") or response.get("decision", {}).get("decision_id")
    action_verification = response.get("action_verification_result", {}) or {}

    try:
        if response.get("error_flag", False):
            mark_incident_workflow_failed(
                hawkeye_incident_id=he_incident_id,
                decision_id=decision_id,
            )
        else:
            mark_incident_workflow_completed(
                hawkeye_incident_id=he_incident_id,
                decision_id=decision_id,
            )
    except Exception:
        pass

    try:
        if action_verification.get("ok", False):
            update_incident_status(
                incident_id=he_incident_id,
                status="CLOSED",
                owner=thread_id,
            )
        else:
            update_incident_status(
                incident_id=he_incident_id,
                status="OPEN",
                owner=None,
            )
    except Exception:
        pass

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
        payload = IncidentPayload(
            hawkeye_incident_id=f"HE-TEST-{idx}",
            incident_details=details,
        )
        state: AgentState = run_incident(payload)
        print(f"state keys: {list(state.keys())}")
        print(f"\n[{idx}] {label}")
        print(json.dumps(state, indent=2))


if __name__ == "__main__":
    _quick_test_main()

# Execution command for quick test:
# cd self_healing_agent                                        
# PYTHONPATH=src python src/self_healing_agent/agent/service.py
