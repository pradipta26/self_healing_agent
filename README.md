**Self-Healing Agent**

Production-Governed Autonomous Remediation Framework for SRE

LLMs suggest. Systems decide. Policies govern. Humans retain control.

⸻

📌 **Overview**

This repository demonstrates a production-safe self-healing agent where autonomy is bounded by policy resolution, execution envelope gating, and per-action readiness checks. It separates execution permission from decision authority and encodes escalation as a structural boundary crossing rather than a model output.
The goal of this project is not to build a “clever bot,” but to design a trustworthy autonomy control plane where:
	•	Autonomous actions are policy-bound.
	•	Escalation semantics are deterministic.
	•	Execution blast radius is explicitly controlled.
	•	Every decision is auditable.
	•	Humans remain in control.

This repository demonstrates a production-style self-healing SRE agent.

The system was originally inspired by enterprise incident management workflows, but all datasets included here are synthetic and generated for demonstration purposes only.

⸻

🎯 **Objectives**
	•	Design a safe autonomy architecture suitable for real production environments.
	•	Separate execution envelope from decision authority.
	•	Encode escalation policies structurally (not via prompts).
	•	Prevent silent autonomy.
	•	Provide audit-ready, explainable decision logs.
	•	Enable progressive rollout (OFF → SHADOW → LIVE).

⸻

🏗 **Architecture**

System Readiness (Execution Mode) controls whether side effects are allowed.
Policy Resolution computes effective autonomy per incident.
Action Readiness validates whether execution is safe right now.
Escalation represents authority boundary crossing — not alerting.

				                           ┌─────────────────────────────┐
				                           │  Incident / Signal Ingest   │
				                           │  (alerts, logs, metrics)    │
				                           └───────────────┬─────────────┘
				                                           │
				                                           ▼
				                           ┌─────────────────────────────┐
				                           │  Suggestion Layer           │
				                           │  (LLM + Multi-stage RAG +   │
				                           │   deterministic rules)      │
				                           └───────────────┬─────────────┘
				                                           │
				                                           ▼
				                    ┌────────────────────────────────────────────┐
				                    │            Governance Control Plane        │
				                    │                                            │
				                    │  1. System Readiness → Mode                │
				                    │     OFF | SHADOW | LIVE                    │
				                    │                                            │
				                    │  2. Policy Resolution → Effective Autonomy │
				                    │     L0–L4 + Escalation Floor               │
				                    │                                            │
				                    │  3. Action Readiness → Execution Safety    │
				                    │     rollback • idempotency • tool health   │
				                    └───────────────────┬────────────────────────┘
				                                        │
				                                        ▼
				                         ┌───────────────────────────┐
				                         │ Escalation Router         │
				                         │ NONE | APPROVAL | HANDOFF │
				                         └───────────────┬───────────┘
				                                         │
				                  ┌──────────────────────┼──────────────────────┐
				                  │                      │                      │
				                  ▼                      ▼                      ▼
				           ┌────────────┐        ┌───────────────┐      ┌────────────┐
				           │ Execute    │        │ Human Approval│      │ Human Owns │
				           │ (LIVE only)│        │ Required      │      │ Incident   │
				           └────────────┘        └───────────────┘      └────────────┘
**The system is built around five governance axes:**


⸻

Axis 1 — System Readiness (Execution Mode)

Execution Envelope:
OFF | SHADOW | LIVE

Controls whether side effects are allowed at all.
	•	OFF → No tools. No mutation. Blast radius = 0.
	•	SHADOW → Full planning + validation. No execution. Dry-run only.
	•	LIVE → Real execution permitted (if policy allows).

Mode is computed deterministically using:
	•	Kill switch
	•	Change freeze
	•	Policy engine health
	•	Audit logging health
	•	Control-plane tool readiness

LIVE is a privilege, not a default.

⸻

Axis 2 — Autonomy Level (Decision Authority)

L0–L4

	Level		Meaning
	L0		Recommendation only
	L1		Human approval required
	L2		Rule-based execution
	L3		Execute unless anomaly
	L4		Near-full autonomy

Autonomy is not static. It is computed per incident.

⸻

Axis 3 — Escalation (Boundary Crossing)

Escalation occurs when the system reaches an authority boundary.

Escalation	Meaning
NONE	Proceed
APPROVAL	Human must approve
HANDOFF	Human takes ownership

Escalation is policy-driven — not model-driven.

⸻

Axis 4 — Policy Resolution Engine

Computes Effective Autonomy Level using:
	•	Global caps
	•	Environment caps (prod stricter than dev)
	•	Service caps
	•	Action-type caps
	•	Blast-radius caps
	•	Incident context caps (SEV1, instability, novelty)
	•	Trust posture metrics
	•	Manual autonomy overrides

Output:
	•	Effective Autonomy Level
	•	Escalation Floor
	•	Deny/Allow decision
	•	Machine-readable reason codes

⸻

Axis 5 — Action Readiness Gate

Per-action execution validation:
	•	Tool health
	•	Rollback availability
	•	Idempotency
	•	Target state validation
	•	Recurrence guard
	•	Runtime blast-radius validation

Even if policy allows execution, Action Readiness can escalate or block.

⸻

🔐 Governance Model

The system enforces:

	System Mode
    	↓
	Policy Resolution
    	↓
	Action Readiness
    	↓
	Escalation
    	↓
	Execution (only if LIVE)

Clear separation of:
	•	Execution safety
	•	Decision authority
	•	Governance caps
	•	Runtime safety checks

⸻

🛠 Supported Actions (Initial Scope)
	1.	Kubernetes Pod Restart
	•	Bounded blast radius
	•	Verification after restart
	•	Recurrence guard
	2.	High Disk Space Remediation
	•	Privileged operation
	•	Rollback required
	•	Rollout-gated in production
	3.	Site Failover (GSLB Switch)
	•	Cross-DC blast radius
	•	Default: approval or handoff
	•	Strict governance caps

⸻

📂 **Repository Structure**

policy/                 # YAML policy definitions
autonomicity/
    system_readiness.py
    policy_engine.py
    action_readiness.py
    executor.py
    models.py
examples/
tests/
docs/


⸻

🧪 **Example Scenario**

Mode = LIVE
Service = I2IV (SRE tools)
Action = Pod Restart
Blast Radius = SINGLE_POD

Result:
	•	Effective Level = L3
	•	No escalation
	•	Execute
	•	Decision snapshot logged

⸻

Mode = LIVE
Service = EV6V (Billing)
Action = Site Failover
Severity = SEV1

Result:
	•	Incident context cap → L1
	•	Escalation → HANDOFF
	•	No automatic execution
	•	Human takes ownership

⸻

📊 Decision Logging

Every decision emits a structured snapshot including:
	•	Mode
	•	Effective Autonomy Level
	•	Escalation Floor
	•	Reason Codes
	•	Policy Version
	•	Incident ID
	•	Action Type

This enables:
	•	Audit trails
	•	Postmortem analysis
	•	Trust posture tracking
	•	Escalation tuning

⸻

🧠 **Design Principles**
	•	Prompts are hints. State is truth.
	•	Escalation is a feature, not a failure.
	•	Unsafe paths must not exist in the graph.
	•	Autonomy must decrease under instability.
	•	Human accountability must remain explicit.
	•	Execution Mode and Autonomy Level are orthogonal.

⸻

🚀 **Operational Philosophy**

Default lifecycle: OFF → SHADOW → LIVE

Promotion to LIVE requires:
	•	Stable shadow metrics
	•	Human review
	•	Verified rollback paths
	•	Low novelty and unknown rates

Automatic downgrade is allowed.
Automatic upgrade is not.

⸻

📈 **Production Readiness Goals**

This project aims to demonstrate:
	•	Enterprise-grade escalation semantics
	•	Blast-radius-aware automation
	•	Policy-driven autonomy control
	•	Explicit human-in-the-loop integration
	•	Deterministic system governance
	•	Production observability

⸻

🧭 **Roadmap**
	•	LangGraph state-machine implementation
	•	Decision trace visualization
	•	Replay harness for shadow evaluation
	•	Metrics dashboard for trust posture
	•	Reinforcement learning feedback loop
	•	Canary deployment by Application

⸻

🏁 **Status**

🚧 Active development
🧪 Experimental but governance-focused
🎓 Learning-driven, production-oriented

⸻

---

---

## 📚 Evidence & Retrieval Pipeline (RAG)

The system uses a **multi-stage, evidence-grounded retrieval pipeline** rather than a simple “retrieve + prompt” approach. The goal is to ensure that all model suggestions are backed by verifiable context before any decision is made.

### 1) Data Ingestion & Normalization
- Incident signals (alerts, logs, metrics)
- Historical resolution data (PRDB-like records)
- Normalized into structured, queryable documents
- Metadata enrichment (service, environment, category, timestamps)

### 2) Multi-Stage Retrieval
- Initial retrieval (hybrid search: keyword + vector)
- Query rewrite (improves recall on sparse/ambiguous inputs)
- Iterative retry (policy-driven, not model-driven)
- Retrieval policy gate:
  - PROCEED → sufficient evidence
  - RETRY → refine query
  - INVESTIGATE → insufficient/low-quality evidence

### 3) Context Validation
- Detects weak context before model usage:
  - empty retrieval
  - low score / low relevance
  - conflicting signals across documents
- Produces structured validity signals (VALID / LOW_QUALITY / CONFLICTING / EMPTY)

### 4) Grounding Verification
- Validates that model claims are supported by retrieved evidence
- Blocks or downgrades outputs when:
  - claims lack evidence
  - evidence IDs are invalid/missing
  - confidence is high but evidence is weak
- Converts LLM output into **verifiable, structured facts**

### 5) Trust Signals (Used by Policy Engine)
- `retrieval_score_avg`
- `retrieval_empty`
- `conflicting_signals`
- grounding verdict (GROUNDED / UNGROUNDED)

These signals feed into **Policy Resolution** to:
- cap autonomy
- force escalation
- prevent unsafe execution

### Key Principle

> Retrieval is not a pre-processing step — it is part of the **governance layer**.

Decisions are never based on model output alone; they require **validated, grounded evidence**.

---

## 🔄 End-to-End Flow

The following flow summarizes how a single incident moves through the system from ingestion to execution, escalation, rollback, and observability.

```text
Incident / Signal
      ↓
Parse + Validate Input
      ↓
Multi-stage Retrieval
  → initial retrieval
  → query rewrite (if needed)
  → retrieval policy decision
      ↓
Context Validation
      ↓
LLM Suggestion
      ↓
Grounding Check
      ↓
Grounding Policy Decision
      ↓
Build Decision Snapshot
      ↓
Action Policy Evaluation
  → BLOCKED                → Investigation
  → PROPOSE_ONLY           → Proposal Output
  → APPROVAL_REQUIRED      → HITL Approval
  → AUTO_EXECUTE           → Pre-Execution Guard
                                   ↓
                           Prepare Tool Call
                                   ↓
                           Tool Log Start
                                   ↓
                           Execute Tool
                                   ↓
                           Retry Classification
                             → RETRY
                             → NO_RETRY
                                   ↓
                           Tool Log Finalize
                                   ↓
                           Tool Output Verification
                                   ↓
                           Action Validation
                             → SUCCESS              → End
                             → FAILURE              → Rollback or Investigation
                                                           ↓
                                                   Prepare Rollback Tool Call
                                                           ↓
                                                   Rollback Tool Log Start
                                                           ↓
                                                   Execute Rollback
                                                           ↓
                                                   Retry Classification
                                                           ↓
                                                   Rollback Tool Log Finalize
                                                           ↓
                                                   Rollback Verification
                                                     → SUCCESS            → End
                                                     → FAILURE            → Investigation
```

### In practical terms
- **Retrieval + validation** determine whether the system has enough trustworthy evidence.
- **Policy resolution** determines whether autonomy is allowed, downgraded, or escalated.
- **Execution safety** is enforced again before any side effect is attempted.
- **Retry and rollback** are structural control paths, not prompt behavior.
- **Observability** is captured throughout via:
  - decision logs
  - lifecycle events
  - tool execution logs
  - real-time metric emission

---

## 📦 Versioning

### ✅ V1.0 — Production-Governed Agent (Completed)

This version establishes a **production-grade foundation** for a trustworthy self-healing system.

**Core Capabilities**
- Deterministic LangGraph state machine (no implicit agent behavior)
- Policy-driven routing (LLM suggests, system decides)
- Explicit escalation semantics:
  - PROPOSE
  - HITL_APPROVAL
  - HITL_INVESTIGATION
  - HITL_SME_REVIEW
- Human-in-the-loop (pause/resume workflow)
- Retry classification:
  - transient vs permanent vs unknown
  - deterministic retry decisions
- Rollback / compensation skeleton:
  - post-action validation → rollback decision → execution
- Tool contract hardening:
  - registry-based tool definitions
  - preconditions
  - structured ToolResult
- Idempotency safeguards (incident-level)
- Lifecycle event logging (decision + execution)
- Tool execution logging (start → finalize pattern)

**Observability (Phase 4)**
- Real-time metric emission (log-based):
  - agent runs (start / success / failure)
  - tool attempts
  - retry rate + failure classification
  - side-effect committed rate
  - rollback invocation / success / failure
- DB-backed analytics:
  - decision_log (audit + reasoning)
  - tool_execution_log (execution trace)
  - decision_lifecycle_event (timeline)
- SQL query pack (time-bounded + global)
- Service-layer query helpers:
  - aggregated summaries
  - incident drilldown (`get_incident_execution_summary`)

**Key Design Guarantees**
- No unsafe execution path exists in the graph
- Execution is always gated by policy + readiness
- Escalation is structural, not prompt-driven
- All decisions are auditable and reproducible

---

### 🚧 V2 — Advanced Production Capabilities (Planned)

V2 focuses on **enterprise-scale robustness, learning, and operability**.

**1. Advanced Escalation Policy System**
- Conflict detection (multiple signals disagree)
- Novelty detection (unknown patterns)
- Multi-path escalation routing (approval vs investigation vs SME)
- Explicit escalation reason modeling

**2. Trust & Stability Feedback Loops**
- Metrics-driven autonomy degradation:
  - high retry rate
  - rollback spikes
  - validation failures
- Trust posture scoring per service / action

**3. Reinforcement Learning / Feedback Integration**
- Use historical logs:
  - tool_execution_log
  - decision_log
  - human approvals/rejections
- Improve:
  - action selection
  - escalation thresholds

**4. Advanced RAG Pipeline (SRE-aware)**
- multi-stage retrieval
- re-ranking
- context validation
- grounding verification improvements

**5. Control Plane Enhancements**
- policy hot-reload (YAML without redeploy)
- canary rollout of autonomy by service
- environment-specific autonomy envelopes

**6. Observability Expansion**
- OpenSearch / Datadog integration for metric streams
- dashboards:
  - system health
  - trust posture
  - execution safety
- alerting on:
  - rollback spikes
  - retry anomalies

**7. Replay & Simulation Harness**
- incident replay engine
- shadow vs live comparison
- regression detection for policy changes

**8. Multi-Service / Multi-Tenant Scaling**
- service isolation
- policy partitioning
- workload-aware autonomy tuning

---

## 🧭 How to Use This Repo (Interview / Portfolio)

This repository demonstrates:

- How to design **trustworthy AI systems** (not just LLM apps)
- How to separate:
  - decision intelligence
  - execution authority
  - governance control
- How to build **production-safe agentic systems**

It is intended to be used as:
- 📌 Resume project (Principal / Staff level)
- 📌 System design discussion anchor
- 📌 Demonstration of real-world AI reliability engineering

---
