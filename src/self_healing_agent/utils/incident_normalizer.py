# src/self_healing_agent/utils/incident_normalizer.py

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


def build_problem_chunk(record: dict[str, Any]) -> str:
    """
    Generate normalized semantic problem description used for embeddings.
    """

    service = _clean_text(record.get("SERVICE_DOMAIN"))
    app = _clean_text(record.get("APP_NAME"))
    metric = _clean_text(record.get("METRIC_NAME"))
    dc = normalize_datacenter(record.get("DATACENTER"))
    incident_type = normalize_incident_type(record.get("INCIDENT_TYPE"))
    hosts = normalize_hosts(record.get("HOSTS"))

    reason = extract_reason_signal(
        record.get("INCIDENT_REASON"),
        record.get("METRIC_NAME"),
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


def _normalize_resolution_text(closure_remarks: str | None) -> str:
    """
    Normalize resolution text for embedding generation.
    """

    if not closure_remarks:
        return ""

    text = closure_remarks.lower().strip()

    text = text.replace("_", " ")
    text = text.replace("-", " ")

    # normalize common remediation actions
    text = re.sub(
        r"\bkilled\s+\d+(?:/\d+)?\s+for\s+([a-z0-9_]+)",
        r"killed database sessions for \1",
        text,
    )
    # normalize common remediation actions
    text = re.sub(
        r"\bserver\(s\)\s+restarted\b",
        "restarted application server",
        text,
    )
    # normalize common remediation actions
    text = re.sub(
        r"\bstarted\s+the\s+jvms\b",
        "started jvms",
        text,
    )

    text = re.sub(
        r"\bsuppresses\s+this\s+alert\b",
        "suppressed alert",
        text,
    )

    # remove IDs
    text = re.sub(r"\b\d+(?:/\d+)?\b", " ", text)

    # normalize hostnames
    text = re.sub(
        r"\b[a-z0-9.-]+\.rds\.amazonaws\.com\b",
        "database host",
        text,
    )
    # normalize common domain patterns
    text = re.sub(
        r"\b[a-z0-9.-]+\.mydomain\.com\b",
        "application host",
        text,
    )
    # normalize example.com hosts (common in synthetic data and tests)
    text = re.sub(
        r"\b[a-z0-9.-]+\.example\.com\b",
        "host",
        text,
    )
    # remove control-plane labels
    text = re.sub(
        r"\b[a-z0-9._-]+:[a-z0-9._:-]+\b",
        " ",
        text,
    )
    # remove numeric thresholds
    text = re.sub(r"\s+", " ", text).strip(" ,;:.")
    return text

def normalized_resolution(resolution_text: str) -> tuple[str, str]:
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