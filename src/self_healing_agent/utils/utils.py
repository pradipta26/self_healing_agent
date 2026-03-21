from datetime import datetime, timezone
import logging
import os
import time

import psycopg2
from psycopg2 import InterfaceError, OperationalError
from psycopg2.extensions import connection as Connection

def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_logger(name: str | None = None) -> logging.Logger:
    """Return a shared logger instance with a standard format."""
    logger_name = name or "self_healing_agent"
    logger = logging.getLogger(logger_name)

    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s | %(name)s | %(levelname)s | %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False

    return logger

def get_db_connection() -> Connection:
    retry_delays = (10, 20)
    logger = get_logger(__name__)

    for attempt in range(len(retry_delays) + 1):
        try:
            return psycopg2.connect(
                host=os.getenv("DB_HOST", "localhost"),
                port=os.getenv("DB_PORT", "5432"),
                database=os.getenv("DB_NAME", "postgres"),
                user=os.getenv("DB_USER", "postgres"),
                password=os.getenv("DB_PASSWORD", "Suvra#10"),
            )
        except (OperationalError, InterfaceError) as exc:
            if attempt == len(retry_delays):
                raise

            delay = retry_delays[attempt]
            logger.warning(
                "Transient DB connection error on attempt %s/%s. Retrying in %s seconds: %s",
                attempt + 1,
                len(retry_delays) + 1,
                delay,
                exc,
            )
            time.sleep(delay)

    raise RuntimeError("Unreachable DB connection retry state")
