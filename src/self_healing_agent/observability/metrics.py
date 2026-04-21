

from __future__ import annotations

import logging
from typing import Any

from self_healing_agent.observability.metrics_contract import ALL_METRICS

logger = logging.getLogger(__name__)



def _validate_metric_name(metric_name: str) -> str:
    normalized = str(metric_name).strip()
    if not normalized:
        raise ValueError("Metric name is required.")
    if normalized not in ALL_METRICS:
        raise ValueError(f"Unknown metric name: {normalized}")
    return normalized



def emit_counter(metric_name: str, value: int = 1, **labels: Any) -> None:
    """
    Emit a counter-style metric as a structured log event.

    This is intentionally lightweight for Phase 4 V1.
    Later this can be replaced or wrapped with a real backend
    (Prometheus, OpenTelemetry, CloudWatch, etc.).
    """
    normalized = _validate_metric_name(metric_name)
    logger.info(
        "metric_counter",
        extra={
            "metric_name": normalized,
            "metric_type": "counter",
            "metric_value": int(value),
            "metric_labels": labels,
        },
    )



def emit_gauge(metric_name: str, value: float, **labels: Any) -> None:
    """
    Emit a gauge-style metric as a structured log event.
    """
    normalized = _validate_metric_name(metric_name)
    logger.info(
        "metric_gauge",
        extra={
            "metric_name": normalized,
            "metric_type": "gauge",
            "metric_value": float(value),
            "metric_labels": labels,
        },
    )



def emit_histogram(metric_name: str, value: float, **labels: Any) -> None:
    """
    Emit a histogram-style observation as a structured log event.
    """
    normalized = _validate_metric_name(metric_name)
    logger.info(
        "metric_histogram",
        extra={
            "metric_name": normalized,
            "metric_type": "histogram",
            "metric_value": float(value),
            "metric_labels": labels,
        },
    )