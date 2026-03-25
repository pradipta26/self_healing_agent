from __future__ import annotations

import os
import re
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import psycopg2
from psycopg2 import sql

from pydantic import BaseModel
from self_healing_agent.agent.nodes.parse_raw_incident_text import parse_raw_incident_details
from self_healing_agent.agent.nodes.validate_input import validate_input
from self_healing_agent.utils.incident_normalizer import build_resolution_text, build_query_text
from self_healing_agent.utils.rag_utils import DEFAULT_EMBEDDING_MODEL, embed_text
from self_healing_agent.utils.utils import get_db_connection

class NormalizedJSONIncident(BaseModel):
    incident_type: str
    incident_id: str
    app_name: str
    service_domain: str
    metric_names: list[str]
    datacenter: str
    hosts: list[str] | None
    instances: list[str] | None
    instance_hosts: list[str] | None
    incident_reason: str
    closure_remarks: str
    closure_remarks_normalized: str
    incident_text_raw: str
    incident_reason_normalized: str
    normalized_reason_hash: str
    warnings: list[str] | None
    created_date: str | None
    updated_date: str | None


DEFAULT_SOURCE_TIMEZONE = "America/New_York"
SOURCE_TIMESTAMP_PATTERN = re.compile(
    r"^(?P<date>\d{2}-[A-Z]{3}-\d{2}) "
    r"(?P<time>\d{2}\.\d{2}\.\d{2})"
    r"(?:\.(?P<fraction>\d{1,9}))? "
    r"(?P<meridiem>AM|PM)"
    r"(?: (?P<tz>[A-Za-z_]+(?:/[A-Za-z_]+)?))?$"
)


def build_payload_hash(normalized_text: str) -> str:
    canonical = re.sub(r"\s+", " ", normalized_text).strip().lower()
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _parse_source_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None

    raw_value = value.strip()
    if not raw_value:
        return None

    match = SOURCE_TIMESTAMP_PATTERN.match(raw_value)
    if not match:
        raise ValueError(f"Unsupported source timestamp format: {raw_value}")

    fraction = (match.group("fraction") or "").ljust(6, "0")[:6]
    normalized_value = (
        f"{match.group('date')} {match.group('time').replace('.', ':')}."
        f"{fraction} {match.group('meridiem')}"
    )
    parsed = datetime.strptime(normalized_value, "%d-%b-%y %I:%M:%S.%f %p")

    timezone_name = match.group("tz") or DEFAULT_SOURCE_TIMEZONE
    return parsed.replace(tzinfo=ZoneInfo(timezone_name))

def _load_history_incidents(incident_id: str | None = None) -> list[dict[str, Any]]:
    """
    Load historical incidents from data/synthetic_incident_history_records.json.

    Args:
        incident_id: If provided, return only matching INCIDENT_ID rows.

    Returns:
        List of incident records.
    """
    project_root = Path(__file__).resolve().parents[3]
    data_path = project_root / "data" / "synthetic_incident_history_records.json"
    #data_path = project_root / "data" / "synthetic_incident_history_records_testing.json"
    if not data_path.exists():
        raise FileNotFoundError(f"History file not found: {data_path}")

    with data_path.open("r", encoding="utf-8") as handle:
        loaded = json.load(handle)

    if not isinstance(loaded, list):
        raise ValueError(f"Expected JSON array in {data_path}")

    rows = [row for row in loaded if isinstance(row, dict)]
    if incident_id is None:
        return rows

    incident_id = str(incident_id).strip()
    return [row for row in rows if str(row.get("INCIDENT_ID", "")).strip() == incident_id]


def _enhance_raw_json_incident(raw_incidents: list[dict[str, Any]]) -> list[NormalizedJSONIncident]:
    def _required_str(row: dict[str, Any], key: str) -> str:
        value = row.get(key)
        if value is None:
            raise ValueError(f"Missing required field: {key}")
        text = str(value).strip()
        if not text:
            raise ValueError(f"Empty required field: {key}")
        return text

    def _optional_str(row: dict[str, Any], key: str) -> str | None:
        value = row.get(key)
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    enhanced_incidents: list[dict[str, Any]] = []
    error_incidents: list[dict[str, Any]] = []

    for index, raw_incident in enumerate(raw_incidents):
        try:
            if not isinstance(raw_incident, dict):
                raise ValueError("Incident payload must be an object")
            if not raw_incident.get("INCIDENT_REASON"):
                raise ValueError("Missing required field: INCIDENT_REASON")
            
            parse_result = parse_raw_incident_details({"incident_raw": raw_incident["INCIDENT_REASON"]})
            validation_result = validate_input(parse_result)
            if validation_result.get("error_flag"):  # Handle validation error (e.g., log, skip, etc.)
                raise ValueError(f"Validation failed for INCIDENT_REASON parsing: {validation_result.get('error_message', 'Unknown validation error')}")
            
            # Set all mandatory fields with basic normalization from raw incident and parsed results with validated input
            # Set Incident ID
            incident_id = _required_str(raw_incident, "INCIDENT_ID")
            # Set Incident Type
            incident_type = parse_result['structured_input']['incident_type']
            # Set App Name
            app_name = parse_result['structured_input']['app_name']
            # Set Service Domain
            service_domain= parse_result['structured_input']['service_domain']
            # Set Metrics
            metric_names = parse_result['structured_input']['metric_names']
            # Set Datacenter
            datacenter = parse_result['structured_input']['datacenter']
            # Set hosts
            if parse_result.get('structured_input',{}).get('hosts') is not None:
                hosts = parse_result['structured_input']['hosts']
            else:
                host_raw = _optional_str(raw_incident, "HOST")
                hosts = [token.strip() for token in host_raw.split(",") if token.strip()] if host_raw else None
            
            
            # Set Instances
            instances = parse_result['structured_input']['instances']
            # Set Instance Hosts
            instance_hosts = parse_result['structured_input'].get('instance_hosts')
            # Set Incident Reason
            incident_reason = parse_result['structured_input']['reason']
            # Set closure_remarks
            closure_remarks, closure_remarks_normalized = build_resolution_text(raw_incident.get("CLOSURE_REMARKS"))
            
            incident_reason_normalized = build_query_text(raw_incident)
            normalized_reason_hash = build_payload_hash(incident_reason_normalized)
            warnings = parse_result['warnings']
            created_date = _optional_str(raw_incident, "created_date")
            updated_date = _optional_str(raw_incident, "updated_date")
            # Set normalisezed_incident_text 



            normalized = NormalizedJSONIncident(
                incident_id=incident_id,
                incident_type=incident_type,
                app_name=app_name,
                service_domain=service_domain,
                metric_names=metric_names,
                datacenter=datacenter,
                hosts=hosts,
                instances=instances,
                instance_hosts=instance_hosts,
                incident_reason=incident_reason,
                incident_text_raw=json.dumps(raw_incident),
                incident_reason_normalized=incident_reason_normalized,
                normalized_reason_hash=normalized_reason_hash,
                closure_remarks=closure_remarks,
                closure_remarks_normalized=closure_remarks_normalized,
                warnings=warnings,
                created_date=created_date,
                updated_date=updated_date,
            )
            enhanced_incidents.append(normalized.model_dump())
        except Exception as exc:  # noqa: BLE001
            print(f"Error processing incident at index {index}: {exc}")
            error_incidents.append(
                {
                    "error": "INCIDENT_NORMALIZATION_FAILED",
                    "error_message": str(exc),
                    "incident_index": index,
                    "incident_id": (
                        str(raw_incident.get("INCIDENT_ID")).strip()
                        if isinstance(raw_incident, dict) and raw_incident.get("INCIDENT_ID") is not None
                        else None
                    ),
                    "raw_incident": raw_incident,
                }
            )

    return enhanced_incidents, error_incidents

def _create_parent_incident_db_entries(enhanced_incidents: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Create database entries for the parent incident.
    Maps enhanced_incidents structure to prdb_incident_parent table schema.
    """
    db_input_entries: list[dict[str, Any]] = []
    error_entries: list[dict[str, Any]] = []
    
    for enhanced_incident in enhanced_incidents:
        try:
            # Map to database schema
            db_entry = {
                # External/source identifiers
                "source_incident_id": enhanced_incident.get("incident_id"),
                "source_system": "synthetic",
                
                # Canonical parsed fields
                "incident_type": enhanced_incident.get("incident_type"),
                "env": "PROD",
                "service_domain": enhanced_incident.get("service_domain"),
                "datacenter": enhanced_incident.get("datacenter"),
                "app_name": enhanced_incident.get("app_name"),
                "hosts": enhanced_incident.get("hosts"),
                "reason": enhanced_incident.get("incident_reason"),
                
                # Arrays from canonical parsing
                "metric_names": enhanced_incident.get("metric_names"),
                "instances": enhanced_incident.get("instances"),
                "instance_hosts": enhanced_incident.get("instance_hosts"),
                "warnings": enhanced_incident.get("warnings"),
                
                # Raw source payload
                "raw_incident_text": enhanced_incident.get("incident_text_raw"),
                "normalized_incident_reason": enhanced_incident.get('incident_reason_normalized'),
                "resolution": enhanced_incident.get("closure_remarks", ""),
                
                # Metadata
                "payload_hash": enhanced_incident.get("normalized_reason_hash"),
                "source_created_at": _parse_source_timestamp(enhanced_incident.get("created_date")),
                "source_updated_at": _parse_source_timestamp(enhanced_incident.get("updated_date")),
            }
            db_input_entries.append(db_entry)
            
        except Exception as exc:  # noqa: BLE001
            error_entries.append({
                "incident_id": enhanced_incident.get("incident_id"),
                "error": "DB_ENTRY_CREATION_FAILED",
                "error_message": str(exc),
                "enhanced_incident": enhanced_incident
            })
    
    return db_input_entries, error_entries


def _create_parent_incident_db_entry(enhanced_incident: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_incident_id": enhanced_incident.get("incident_id"),
        "source_system": "synthetic",
        "incident_type": enhanced_incident.get("incident_type"),
        "env": "PROD",
        "service_domain": enhanced_incident.get("service_domain"),
        "datacenter": enhanced_incident.get("datacenter"),
        "app_name": enhanced_incident.get("app_name"),
        "hosts": enhanced_incident.get("hosts"),
        "reason": enhanced_incident.get("incident_reason"),
        "metric_names": enhanced_incident.get("metric_names"),
        "instances": enhanced_incident.get("instances"),
        "instance_hosts": enhanced_incident.get("instance_hosts"),
        "warnings": enhanced_incident.get("warnings"),
        "raw_incident_text": enhanced_incident.get("incident_text_raw"),
        "normalized_incident_reason": enhanced_incident.get("incident_reason_normalized"),
        "resolution": enhanced_incident.get("closure_remarks", ""),
        "payload_hash": enhanced_incident.get("normalized_reason_hash"),
        "source_created_at": _parse_source_timestamp(enhanced_incident.get("created_date")),
        "source_updated_at": _parse_source_timestamp(enhanced_incident.get("updated_date")),
    }


def _create_incident_chunk_db_entries_for_incident(
    enhanced_incident: dict[str, Any],
    parent_id: int,
) -> list[dict[str, Any]]:
    metric_names = enhanced_incident.get("metric_names") or []
    metric_name = metric_names[0] if metric_names else ""

    common_fields = {
        "parent_id": parent_id,
        "service_domain": enhanced_incident.get("service_domain"),
        "metric_name": metric_name,
        "datacenter": enhanced_incident.get("datacenter"),
        "incident_type": enhanced_incident.get("incident_type"),
        "app_name": enhanced_incident.get("app_name"),
        "embedding_model": DEFAULT_EMBEDDING_MODEL,
    }

    chunk_entries: list[dict[str, Any]] = []

    problem_text = (enhanced_incident.get("incident_reason") or "").strip()
    problem_text_normalized = (enhanced_incident.get("incident_reason_normalized") or "").strip()
    if problem_text and problem_text_normalized:
        chunk_entries.append(
            {
                **common_fields,
                "chunk_index": 1,
                "chunk_type": "problem",
                "chunk_text": problem_text,
                "chunk_text_normalized": problem_text_normalized,
                "embedding": embed_text(problem_text_normalized),
            }
        )

    resolution_text = (enhanced_incident.get("closure_remarks") or "").strip()
    resolution_text_normalized = (enhanced_incident.get("closure_remarks_normalized") or "").strip()
    if resolution_text and resolution_text_normalized:
        chunk_entries.append(
            {
                **common_fields,
                "chunk_index": 2,
                "chunk_type": "resolution",
                "chunk_text": resolution_text,
                "chunk_text_normalized": resolution_text_normalized,
                "embedding": embed_text(resolution_text_normalized),
            }
        )
    import time
    time.sleep(1)  # To respect rate limits of embedding API
    return chunk_entries


def _adapt_chunk_value(column: str, value: Any) -> Any:
    if column == "embedding" and value is not None:
        return "[" + ",".join(str(component) for component in value) + "]"
    return value




def _insert_into_parent_incident_db(db_entries: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Insert the given entries into the prdb_incident_parent table.
    Processes each entry independently to ensure one failure does not stop the entire process.
    Skips records if payload_hash already exists in the database.
    
    Args:
        db_entries: List of database entry dictionaries
        
    Returns:
        Summary dictionary with:
        - total: Total number of entries
        - successful: Number of successful inserts
        - skipped: Number of skipped records (duplicate payload_hash)
        - failed: Number of failed inserts
        - failures: List of failure details with incident_id, error, and entry_index
    """
    
    
    summary = {
        "total": len(db_entries),
        "successful": 0,
        "skipped": 0,
        "failed": 0,
        "failures": []
    }
    
    if not db_entries:
        return summary
    
    conn = None
    cursor = None
    
    try:
        # Get database connection from environment variables or use provided credentials
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=os.getenv("DB_PORT", "5432"),
            database=os.getenv("DB_NAME", "postgres"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", "Suvra#10")
        )
        cursor = conn.cursor()
        
        # Process each entry independently
        for idx, entry in enumerate(db_entries):
            try:
                payload_hash = entry.get("payload_hash")
                
                # Check if payload_hash already exists in the database
                if payload_hash:
                    check_query = sql.SQL(
                        "SELECT id FROM prdb_incident_parent WHERE payload_hash = %s LIMIT 1"
                    )
                    cursor.execute(check_query, (payload_hash,))
                    existing_record = cursor.fetchone()
                    
                    if existing_record:
                        # Skip this record as it already exists
                        summary["skipped"] += 1
                        continue
                
                # Build INSERT query using parameterized statements to prevent SQL injection
                columns = list(entry.keys())
                values = [entry[col] for col in columns]
                
                # Create SQL INSERT statement
                insert_query = sql.SQL(
                    "INSERT INTO prdb_incident_parent ({}) VALUES ({}) "
                    "ON CONFLICT (source_system, source_incident_id) DO UPDATE SET "
                    "updated_at = NOW()"
                ).format(
                    sql.SQL(", ").join(map(sql.Identifier, columns)),
                    sql.SQL(", ").join(sql.Placeholder() * len(columns))
                )
                
                cursor.execute(insert_query, values)
                summary["successful"] += 1
                
            except Exception as exc:  # noqa: BLE001
                # Capture failure details without stopping the process
                summary["failed"] += 1
                summary["failures"].append({
                    "incident_id": entry.get("source_incident_id"),
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                    "entry_index": idx
                })
                # Continue processing other entries
                continue
        
        # Commit all successful inserts at once
        conn.commit()
        
    except psycopg2.OperationalError as exc:
        summary["failed"] = len(db_entries)
        summary["successful"] = 0
        summary["skipped"] = 0
        summary["failures"].append({
            "error": f"Database connection failed: {str(exc)}",
            "error_type": "OperationalError",
            "total_entries_not_processed": len(db_entries)
        })
        
    except Exception as exc:  # noqa: BLE001
        summary["failed"] = len(db_entries)
        summary["successful"] = 0
        summary["skipped"] = 0
        summary["failures"].append({
            "error": f"Unexpected database error: {str(exc)}",
            "error_type": type(exc).__name__,
            "total_entries_not_processed": len(db_entries)
        })
        
    finally:
        # Clean up database resources
        if cursor is not None:
            try:
                cursor.close()
            except Exception:  # noqa: BLE001
                pass
        if conn is not None:
            try:
                conn.close()
            except Exception:  # noqa: BLE001
                pass
    
    return summary


def _insert_incidents_into_chunks_db(
    conn: psycopg2.extensions.connection,
    enhanced_incidents: list[dict[str, Any]],
) -> dict[str, Any]:
    summary = {
        "total": len(enhanced_incidents),
        "successful": 0,
        "skipped": 0,
        "failed": 0,
        "parent_rows_inserted": 0,
        "chunk_rows_inserted": 0,
        "failures": [],
    }

    if not enhanced_incidents:
        return summary

    cursor = None

    try:
        cursor = conn.cursor()

        for idx, enhanced_incident in enumerate(enhanced_incidents):
            incident_id = enhanced_incident.get("incident_id")
            try:
                parent_entry = _create_parent_incident_db_entry(enhanced_incident)
                payload_hash = parent_entry.get("payload_hash")

                if payload_hash:
                    cursor.execute(
                        "SELECT id FROM prdb_incident_parent WHERE payload_hash = %s LIMIT 1",
                        (payload_hash,),
                    )
                    if cursor.fetchone():
                        conn.rollback()
                        summary["skipped"] += 1
                        continue

                parent_columns = list(parent_entry.keys())
                parent_values = [parent_entry[column] for column in parent_columns]
                parent_insert_query = sql.SQL(
                    "INSERT INTO prdb_incident_parent ({}) VALUES ({}) "
                    "ON CONFLICT (source_system, source_incident_id) DO UPDATE SET "
                    "updated_at = NOW() "
                    "RETURNING id"
                ).format(
                    sql.SQL(", ").join(map(sql.Identifier, parent_columns)),
                    sql.SQL(", ").join(sql.Placeholder() * len(parent_columns))
                )
                cursor.execute(parent_insert_query, parent_values)
                parent_id = cursor.fetchone()[0]

                chunk_entries = _create_incident_chunk_db_entries_for_incident(
                    enhanced_incident=enhanced_incident,
                    parent_id=parent_id,
                )

                for chunk_entry in chunk_entries:
                    chunk_columns = list(chunk_entry.keys())
                    chunk_values = [
                        _adapt_chunk_value(column, chunk_entry[column])
                        for column in chunk_columns
                    ]
                    chunk_insert_query = sql.SQL(
                        "INSERT INTO prdb_incident_chunk ({}) VALUES ({}) "
                        "ON CONFLICT (parent_id, chunk_index, chunk_type) DO UPDATE SET "
                        "chunk_text = EXCLUDED.chunk_text, "
                        "chunk_text_normalized = EXCLUDED.chunk_text_normalized, "
                        "service_domain = EXCLUDED.service_domain, "
                        "metric_name = EXCLUDED.metric_name, "
                        "datacenter = EXCLUDED.datacenter, "
                        "incident_type = EXCLUDED.incident_type, "
                        "app_name = EXCLUDED.app_name, "
                        "embedding = EXCLUDED.embedding, "
                        "embedding_model = EXCLUDED.embedding_model"
                    ).format(
                        sql.SQL(", ").join(map(sql.Identifier, chunk_columns)),
                        sql.SQL(", ").join(sql.Placeholder() * len(chunk_columns))
                    )
                    cursor.execute(chunk_insert_query, chunk_values)

                conn.commit()
                summary["successful"] += 1
                summary["parent_rows_inserted"] += 1
                summary["chunk_rows_inserted"] += len(chunk_entries)

            except Exception as exc:  # noqa: BLE001
                conn.rollback()
                summary["failed"] += 1
                summary["failures"].append({
                    "incident_id": incident_id,
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                    "entry_index": idx,
                })

    except psycopg2.OperationalError as exc:
        summary["failed"] = len(enhanced_incidents)
        summary["successful"] = 0
        summary["skipped"] = 0
        summary["parent_rows_inserted"] = 0
        summary["chunk_rows_inserted"] = 0
        summary["failures"].append({
            "error": f"Database connection failed: {str(exc)}",
            "error_type": "OperationalError",
            "total_entries_not_processed": len(enhanced_incidents),
        })

    except Exception as exc:  # noqa: BLE001
        if conn is not None:
            conn.rollback()
        summary["failed"] = len(enhanced_incidents)
        summary["successful"] = 0
        summary["skipped"] = 0
        summary["parent_rows_inserted"] = 0
        summary["chunk_rows_inserted"] = 0
        summary["failures"].append({
            "error": f"Unexpected database error: {str(exc)}",
            "error_type": type(exc).__name__,
            "total_entries_not_processed": len(enhanced_incidents),
        })

    finally:
        if cursor is not None:
            try:
                cursor.close()
            except Exception:  # noqa: BLE001
                pass

    return summary


def document_builder() -> dict[str, Any]:
    # Main function to build documents for retrieval.
    summary = {
        "normalization": {},
        "db_insert": {}
    }
    
    try: 
        raw_incidents = _load_history_incidents()
    except Exception as exc:
        print(f"Failed to load raw incidents: {exc}")
        raise ValueError(f"Failed to load raw incidents: {exc}")
    
    enhanced_incidents, error_incidents = _enhance_raw_json_incident(raw_incidents)
    print(f"enhanced incidents: {len(enhanced_incidents)} \n error incidents: {len(error_incidents)}")

    conn = None
    try:
        conn = get_db_connection()
        db_insert_summary = _insert_incidents_into_chunks_db(conn, enhanced_incidents)
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:  # noqa: BLE001
                pass

    summary["db_insert"] = db_insert_summary
    print(f"\nDatabase Insert Summary:")
    print(f"  Total incidents: {db_insert_summary['total']}")
    print(f"  Successful incidents: {db_insert_summary['successful']}")
    print(f"  Skipped incidents: {db_insert_summary['skipped']}")
    print(f"  Failed incidents: {db_insert_summary['failed']}")
    print(f"  Parent rows inserted: {db_insert_summary['parent_rows_inserted']}")
    print(f"  Chunk rows inserted: {db_insert_summary['chunk_rows_inserted']}")
    if db_insert_summary['failures']:
        print(f"  Failures: {json.dumps(db_insert_summary['failures'][:5], indent=2)}")
    
    return summary

if __name__ == "__main__":
    result = document_builder()
    print(f"\nNormalization complete.")
    print(f"Summary: {json.dumps(result, indent=2)}")
