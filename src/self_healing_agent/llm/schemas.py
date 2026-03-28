MODEL_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "category": {
            "type": "string",
            "enum": [
                "CPU",
                "MEMORY",
                "NETWORK",
                "APPLICATION",
                "DATABASE",
                "JVM",
                "STORAGE",
                "DEPENDENCY",
                "CONFIGURATION",
                "UNKNOWN",
            ],
        },
        "confidence": {
            "type": "string",
            "enum": ["HIGH", "MEDIUM", "LOW", "UNKNOWN"],
        },
        "actionability": {
            "type": "string",
            "enum": [
                "SAFE_TO_PROPOSE",
                "HUMAN_REQUIRED",
                "INSUFFICIENT_EVIDENCE",
                "CONFLICTING_SIGNALS",
            ],
        },
        "description": {"type": "string"},
        "evidence_ids": {
            "type": "array",
            "items": {"type": "integer"},
        },
        "remediation": {
            "type": "array",
            "items": {"type": "string"},
        },
        "hypotheses": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": [
        "category",
        "confidence",
        "actionability",
        "description",
        "evidence_ids",
        "remediation",
        "hypotheses",
    ],
}