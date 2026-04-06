from __future__ import annotations

import json
import sys
from typing import Any

from self_healing_agent.analytics.decision_metrics_service import get_all_decision_metrics


def _print_section(title: str, data: Any) -> None:
    print(f"\n=== {title} ===")

    if isinstance(data, dict):
        if not data:
            print("(empty)")
            return

        for key, value in data.items():
            if isinstance(value, (dict, list)):
                print(f"{key}:")
                print(json.dumps(value, indent=2, sort_keys=True, default=str))
            else:
                print(f"{key}: {value}")
        return

    if isinstance(data, list):
        if not data:
            print("(empty)")
            return

        print(json.dumps(data, indent=2, sort_keys=True, default=str))
        return

    print(data)


def main() -> int:
    try:
        metrics = get_all_decision_metrics()

        print("Self-Healing Agent Decision Metrics")

        _print_section("Summary", metrics.get("summary", {}))
        _print_section("Safe Proposals", metrics.get("safe_proposals", {}))
        _print_section("Retrieval Weakness", metrics.get("retrieval_weakness", {}))
        _print_section(
            "High Confidence Proposals",
            metrics.get("high_confidence_proposals", {}),
        )

        breakdowns = metrics.get("breakdowns", {})
        _print_section("Route Distribution", breakdowns.get("route_distribution", {}))
        _print_section("Escalation Types", breakdowns.get("escalation_types", {}))
        _print_section(
            "Retrieval Confidence",
            breakdowns.get("retrieval_confidence", {}),
        )
        _print_section(
            "Grounding Verdict",
            breakdowns.get("grounding_verdict", {}),
        )
        _print_section("Warnings", breakdowns.get("warnings", {}))

        _print_section("Latency", metrics.get("latency", {}))
        _print_section(
            "Retrieval Score By Service",
            metrics.get("retrieval_score_by_service", []),
        )

        return 0

    except Exception as exc:
        print(f"Failed to load decision metrics: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())


# Execute: 
# pwd: /Users/pradipta/gen-ai/projects/github/self-healing-agent
# command: python -m self_healing_agent.cli.decision_metrics