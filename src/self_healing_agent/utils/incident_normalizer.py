from __future__ import annotations

import re
from typing import Any


def _clean_text(value: str | None) -> str:
    """Light text normalization for embedding-friendly strings."""
    if not value:
        return ""

    text = value.strip()
    text = text.replace("_", " ")
    text = text.replace("-", " ")
    text = re.sub(r"\s+", " ", text)

    return text.strip()

def get_primary_metric(metric_names: list[str]) -> str:
    return metric_names[0].strip() if metric_names else ""


def normalize_datacenter(dc: str | None) -> str:
    if not dc:
        return ""
    return dc.upper().replace("-", "").replace("_", "").strip()


def normalize_incident_type(value: str | None) -> str:
    if not value:
        return ""

    mapping = {
        "Host Infra": "host infrastructure",
        "Service Instance": "service instance",
        "Service DC": "service datacenter",
        "System Instance": "system instance",
        "System DC": "system datacenter",
    }

    return mapping.get(value.strip(), value.strip().lower())


def normalize_hosts(hosts: list[str] | None) -> list[str]:
    """
    Normalize host list.
    Removes ports when present (embedding does not benefit from ports).
    """

    if not hosts:
        return []

    normalized: list[str] = []

    for host in hosts:
        host = host.strip()

        if ":" in host:
            hostname, rest = host.split(":", 1)

            if rest.isdigit():
                host = hostname

        normalized.append(host)

    return normalized


def _metric_aware_reason_phrase(metric_name: str | None, reason: str) -> str:
    """
    Convert generic threshold wording into more semantic wording for
    mismatch/status-style metrics.
    """
    if not reason:
        return ""

    metric = _clean_text(metric_name).lower()
    normalized_reason = reason.strip()
    lowered_reason = normalized_reason.lower()

    mismatch_like_terms = (
        "mismatch",
        "status mismatch",
        "queue status",
    )

    detected_like_terms = (
        "mismatch",
        "status mismatch",
        "lag",
        "errors",
        "error",
        "blocked",
        "blocker",
    )

    if any(term in metric for term in mismatch_like_terms):
        if "exceeded threshold" in lowered_reason:
            normalized_reason = re.sub(
                r"\bexceeded threshold\b",
                "detected",
                normalized_reason,
                flags=re.IGNORECASE,
            )
        elif "above threshold" in lowered_reason:
            normalized_reason = re.sub(
                r"\babove threshold\b",
                "detected",
                normalized_reason,
                flags=re.IGNORECASE,
            )

    elif any(term in metric for term in detected_like_terms):
        if lowered_reason.endswith("exceeded threshold"):
            normalized_reason = re.sub(
                r"\bexceeded threshold\b",
                "detected",
                normalized_reason,
                flags=re.IGNORECASE,
            )

    return re.sub(r"\s+", " ", normalized_reason).strip(" ,;:")


def extract_reason_signal(
    incident_reason: str | None,
    metric_name: str | None,
) -> str:
    """
    Extract a compact semantic reason from INCIDENT_REASON.
    Works for both formats:

    1)
    Reason: oracle-db-session-blocker >= 1000.0;System: CHHV...

    2)
    ;System: H0JV ... Instance: ... has jvm mismatch >= 0.0
    """

    if not incident_reason:
        return ""

    text = incident_reason.strip()
    metric = _clean_text(metric_name)

    # Case 1: explicit Reason: ...
    match = re.search(r"Reason\s*:\s*(.*?)\s*;\s*System:", text, re.IGNORECASE)
    if not match:
        match = re.search(r"Reason\s*:\s*(.*?)\s*System:", text, re.IGNORECASE)

    if match:
        reason = match.group(1).strip()

    else:
        # Case 2: derive semantic tail
        has_match = re.search(r"Instance:\s*(.*?)\s+has\s+(.*)$", text, re.IGNORECASE)

        if has_match:
            reason = has_match.group(2).strip()
        else:
            # fallback
            if metric_name:
                metric_pattern = re.escape(metric_name)

                tail_match = re.search(
                    rf"({metric_pattern}\s*(>=|<=|>|<|=)\s*[^\s,;]+)",
                    text,
                    re.IGNORECASE,
                )

                if tail_match:
                    reason = tail_match.group(1).strip()
                else:
                    reason = text
            else:
                reason = text

    reason = _clean_text(reason)

    reason = reason.replace(">=", " exceeded threshold ")
    reason = reason.replace("<=", " below threshold ")
    reason = reason.replace(">", " above threshold ")
    reason = reason.replace("<", " below threshold ")
    reason = reason.replace("=", " equal to ")

    # remove control-plane labels
    reason = re.sub(
        r"\b(system|dc|metricname|application|instance|host)\s*:\s*",
        " ",
        reason,
        flags=re.IGNORECASE,
    )

    # remove noisy tails
    reason = re.sub(r"\bfor host\s*:.*", " ", reason, flags=re.IGNORECASE)
    reason = re.sub(r"\breference list\s*:.*", " reference list ", reason, flags=re.IGNORECASE)
    reason = re.sub(r"\b[a-z0-9._-]+:[a-z0-9._:-]+\b", " ", reason, flags=re.IGNORECASE)

    # remove numeric thresholds
    reason = re.sub(r"\b\d+(\.\d+)?\b", " ", reason)

    reason = re.sub(r"\s+", " ", reason).strip(" ,;:")

    if metric and metric.lower() not in reason.lower():
        reason = f"{metric} {reason}".strip()

    reason = _metric_aware_reason_phrase(metric_name, reason)

    return reason


def _normalize_resolution_text(closure_remarks: str | None) -> str:
    """
    Normalize resolution text for embedding generation.

    Goal:
    - preserve the remediation action
    - remove person names, ticket-like ids, ports, host specifics, and noisy instance strings
    - generalize infra details into reusable operational actions
    """

    if not closure_remarks:
        return ""

    text = closure_remarks.lower().strip()
    text = text.replace("_", " ")
    text = text.replace("-", " ")

    # --------------------------------------------------
    # Normalize common remediation actions first
    # --------------------------------------------------
    text = re.sub(
        r"\bkilled\s+\d+(?:/\d+)?\s+for\s+([a-z0-9_]+)",
        r"killed database sessions for \1",
        text,
    )
    text = re.sub(
        r"\bserver\(s\)\s+restarted\b",
        "restarted application server",
        text,
    )
    text = re.sub(
        r"\bstarted\s+the\s+jvms\b",
        "started jvms",
        text,
    )
    text = re.sub(
        r"\brestarted\s+.*?\s+to\s+clear\s+active\s+threads\b",
        "restarted application instance to clear active threads",
        text,
    )
    text = re.sub(
        r"\bsuppresses\s+this\s+alert\b",
        "suppressed alert",
        text,
    )
    text = re.sub(
        r"\bcleared?\s+old\s+logs\b",
        "cleared old logs",
        text,
    )
    text = re.sub(
        r"\badded\s+datafile\b",
        "added datafile",
        text,
    )
    text = re.sub(
        r"\breduced\s+retention\b",
        "reduced retention",
        text,
    )

    # --------------------------------------------------
    # Remove human/operator names before action verbs
    # Example: "syam babu restarted ..."
    # --------------------------------------------------
    text = re.sub(
        r"\b[a-z]+\s+[a-z]+\s+(restarted|started|stopped|killed|cleared|added)\b",
        r"\1",
        text,
        flags=re.IGNORECASE,
    )

    # --------------------------------------------------
    # Normalize hostnames / domains to generic targets
    # --------------------------------------------------
    text = re.sub(
        r"\b[a-z0-9.-]+\.rds\.amazonaws\.com\b",
        "database host",
        text,
    )
    text = re.sub(
        r"\b[a-z0-9.-]+\.mydomain\.com\b",
        "host",
        text,
    )
    text = re.sub(
        r"\b[a-z0-9.-]+\.example\.com\b",
        "host",
        text,
    )

    # Generic FQDNs that survived
    text = re.sub(
        r"\b[a-z0-9-]+(?:\.[a-z0-9-]+){2,}\b",
        "host",
        text,
    )

    # --------------------------------------------------
    # Normalize noisy instance / server tokens
    # --------------------------------------------------
    text = re.sub(
        r"\b[a-z0-9._-]+:[a-z0-9._:-]+\b",
        " application instance ",
        text,
    )
    text = re.sub(
        r"\b(server\d+|cache\d+|esb\d+|mq\d+|node\d+|pod\d+)\b",
        "application instance",
        text,
    )

    # --------------------------------------------------
    # Remove ids / ticket-like numeric noise
    # --------------------------------------------------
    text = re.sub(r"\b\d+(?:/\d+)?\b", " ", text)

    # --------------------------------------------------
    # Collapse over-specific wording into reusable action phrasing
    # --------------------------------------------------
    text = re.sub(
        r"\brestarted\s+application\s+server\s+application\s+instance\b",
        "restarted application server",
        text,
    )
    text = re.sub(
        r"\bkilled\s+database\s+sessions\s+for\s+[a-z0-9_]+\s+on\s+database\s+host\b",
        "killed database sessions on database host",
        text,
    )
    text = re.sub(
        r"\busing\s+sre\s+portal\b",
        "using sre portal",
        text,
    )
    text = re.sub(
        r"\busing\s+startup\s+script\b",
        "using startup script",
        text,
    )

    # Remove lingering punctuation fragments like "application :"
    text = re.sub(r"\b(application|host|instance)\s*:\s*", r"\1 ", text)
    
    # Collapse duplicated synthetic target phrases
    text = re.sub(
        r"\bapplication\s+host\s+application\s+instance\b",
        "application instance",
        text,
    )
    text = re.sub(
        r"\bapplication\s+application\s+instance\b",
        "application instance",
        text,
    )
    text = re.sub(
        r"\brestarted\s+application\s+server(?:\s+application\s+instance)+\b",
        "restarted application server",
        text,
    )
    text = re.sub(
        r"\brestarted\s+application\s+instance(?:\s+application\s+instance)+\b",
        "restarted application instance",
        text,
    )
    text = re.sub(
        r"\bapplication\s+application\b",
        "application",
        text,
    )
    text = re.sub(r"\s+", " ", text).strip(" ,;:.")
    return text


def build_query_text(record: dict[str, Any]) -> str:
    """
    Generate normalized semantic problem description used for embeddings.
    """
    service = _clean_text(record.get("SERVICE_DOMAIN") or record.get("service_domain"))
    app = _clean_text(record.get("APP_NAME") or record.get("app_name"))
    dc = normalize_datacenter(record.get("DATACENTER") or record.get("datacenter"))
    incident_type = normalize_incident_type(record.get("INCIDENT_TYPE") or record.get("incident_type"))
    
    hosts_value = (
        record.get("HOSTS")
        or record.get("hosts")
        or record.get("INSTANCE_HOSTS")
        or record.get("instance_hosts")
        or record.get("instance_host")  # legacy support
    )
    if isinstance(hosts_value, list):
        raw_hosts = hosts_value
    elif isinstance(hosts_value, str):
        raw_hosts = [hosts_value]
    else:
        raw_hosts = []
    hosts = normalize_hosts(raw_hosts)

    metric_value = (
        record.get("METRIC_NAME")
        or record.get("metric_name")
    )
    if not metric_value:
        metric_field = record.get("metric_names")
        if isinstance(metric_field, list):
            metric_value = ", ".join(metric_field)
        else:
            metric_value = metric_field

    metric = _clean_text(metric_value)

    incident_reason = record.get("INCIDENT_REASON") or record.get("reason")
    reason = extract_reason_signal(
        incident_reason,
        metric,
    )

    parts: list[str] = []

    if service:
        parts.append(f"{service} service")

    if incident_type:
        parts.append(f"{incident_type} incident")

    if dc:
        parts.append(f"in {dc} datacenter")

    if app:
        parts.append(f"application {app}")

    if metric:
        parts.append(f"metric {metric}")

    if reason:
        reason = re.sub(r"\s+", " ", reason).strip(" ,;:")
        parts.append(f"reason {reason}")

    if hosts:
        parts.append(f"hosts {', '.join(hosts)}")

    text = ". ".join(parts)

    if not text.endswith("."):
        text += "."

    return text


def build_retry_query_text(
    record: dict[str, Any],
    *,
    include_hosts: bool = False,
    expansion_hints: list[str] | None = None,
) -> str:
    """
    Build retry query text from validated StructuredInput-like records.

    Assumptions:
    - called only after input validation
    - service_domain, incident_type, datacenter, app_name, metric_names, reason exist
    - metric_names is a non-empty list[str]
    """
    service = _clean_text(record.get("service_domain"))
    app = _clean_text(record.get("app_name"))
    dc = normalize_datacenter(record.get("datacenter"))
    incident_type = normalize_incident_type(record.get("incident_type"))
    
    if include_hosts:
        hosts_value = record.get("hosts") or record.get("instance_hosts")
        
        if isinstance(hosts_value, list):
            raw_hosts = hosts_value
        elif isinstance(hosts_value, str):
            raw_hosts = [hosts_value]
        else:
            raw_hosts = []
        hosts = normalize_hosts(raw_hosts)
    else:
        hosts = []

    # metric_names value existancce and list type is already validated in validate_input() as mandatory field
    metric_names = record.get("metric_names", [])
    primary_metric = get_primary_metric(metric_names)
    metric = _clean_text(", ".join(metric_names))
    
    # reason value existancce is already validated in validate_input() as mandatory field
    incident_reason = record.get("reason")
    reason = extract_reason_signal(incident_reason, metric)

    parts: list[str] = []

    if service:
        parts.append(f"{service} service")

    if incident_type:
        parts.append(f"{incident_type} incident")

    if dc:
        parts.append(f"in {dc} datacenter")

    if app:
        parts.append(f"application {app}")

    if primary_metric:
        parts.append(f"metric {primary_metric}")

    if reason:
        reason = re.sub(r"\s+", " ", reason).strip(" ,;:")
        parts.append(f"reason {reason}")

    if hosts:
        parts.append(f"hosts {', '.join(hosts)}")

    if expansion_hints:
        for hint in expansion_hints:
            cleaned_hint = _clean_text(hint)
            if cleaned_hint: 
                parts.append(f"hint {cleaned_hint}")

    text = ". ".join(parts)

    if not text.endswith("."):
        text += "."

    return text


def build_resolution_text(resolution_text: str) -> tuple[str, str]:
    """
    Return:
    - readable chunk text
    - normalized embedding text
    """

    closure = _clean_text(resolution_text)

    if not closure:
        return "", ""

    normalized_text = _normalize_resolution_text(closure)

    return f"resolution {closure}.", normalized_text


if __name__ == "__main__":
    from pprint import pprint

    structured_input = {
        "incident_type": "Host Infrastructure",
        "env": "DEV",
        "service_domain": "H0JV",
        "datacenter": "CDC",
        "metric_names": [
            "jvm mismatch"
        ],
        "app_name": "H0JV-JVM-STATUS",
        "hosts": [
            "CDC-S POS-MS LP 2.0 H0JV Jvm Status Mismatch"
        ],
        "instances": [
            "Reference List: CDC.POS-MS-LP.jvmlistx"
        ],
        "instance_hosts": [],
        "reason": "jvm mismatch >= 0.0"
    }


    result = build_retry_query_text(structured_input, 
                                    expansion_hints=["jvm status mismatch", "missing jvms", "jvm status check"])
    pprint(result)
    # for match in result["matches"]:
    #     pprint({
    #         "parent_id": match["parent_id"],
    #         "similarity": match["similarity"],
    #         "retrieval_level": match["retrieval_level"],
    #         "rerank_score": match["rerank_score"],
    #         "rerank_signals": match["rerank_signals"],
    #         "resolution_text_normalized": match["resolution_text_normalized"],
    #     })