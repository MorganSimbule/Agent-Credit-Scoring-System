"""Prediction logging for monitoring using PostgreSQL or SQLite.

Set DATABASE_URL to use PostgreSQL. If it is unset, the module uses SQLite,
which keeps local tests and lightweight development self-contained.

This intentionally stays simple: it logs inputs + outputs + a timestamp,
and offers a couple of read helpers for a summary view and a basic
distribution-shift check against the training baseline saved by
train_export.py. It is NOT a full drift-detection system (that needs
weeks of accumulated traffic and is out of scope here) — it's a
"does today's traffic look like what the model was trained on" signal.
"""
import os
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:  # PostgreSQL is optional for SQLite-only development.
    psycopg = None
    dict_row = None

DATABASE_URL = os.getenv("DATABASE_URL")
configured_db_path = os.getenv("PREDICTIONS_DB_PATH")
DB_PATH = Path(configured_db_path) if configured_db_path else Path(__file__).parent / "predictions.db"

NUMERIC_FEATURES = ["LoanCount", "AvgLoan", "TransactionFrequency", "AverageTransactionValue", "AuditActivity"]


def get_conn():
    if DATABASE_URL:
        if psycopg is None:
            raise RuntimeError("DATABASE_URL is set but psycopg is not installed")
        return psycopg.connect(DATABASE_URL, row_factory=dict_row)

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute("PRAGMA busy_timeout = 10000")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    id_definition = "BIGSERIAL PRIMARY KEY" if DATABASE_URL else "INTEGER PRIMARY KEY AUTOINCREMENT"
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS predictions (
            id {id_definition},
            timestamp TEXT NOT NULL,
            source TEXT NOT NULL,
            client_id TEXT,
            loan_count REAL,
            avg_loan REAL,
            transaction_frequency REAL,
            average_transaction_value REAL,
            audit_activity REAL,
            occupation TEXT,
            default_probability REAL,
            default_prediction INTEGER,
            risk_category INTEGER,
            risk_label TEXT
        )
        """
    )
    conn.commit()
    conn.close()


def log_prediction(features: dict, result: dict, source: str):
    """source is one of 'single', 'batch', 'csv' — lets you tell which
    endpoint a logged row came from."""
    conn = get_conn()
    placeholders = "%s" if DATABASE_URL else "?"
    conn.execute(
        f"""
        INSERT INTO predictions (
            timestamp, source, client_id, loan_count, avg_loan,
            transaction_frequency, average_transaction_value, audit_activity,
            occupation, default_probability, default_prediction, risk_category, risk_label
        ) VALUES ({', '.join([placeholders] * 13)})
        """,
        (
            datetime.now(timezone.utc).isoformat(),
            source,
            features.get("ClientID"),
            features.get("LoanCount"),
            features.get("AvgLoan"),
            features.get("TransactionFrequency"),
            features.get("AverageTransactionValue"),
            features.get("AuditActivity"),
            features.get("Occupation"),
            result.get("default_probability"),
            result.get("default_prediction"),
            result.get("risk_category"),
            result.get("risk_label"),
        ),
    )
    conn.commit()
    conn.close()


def get_recent(limit: int = 50) -> list[dict]:
    conn = get_conn()
    placeholder = "%s" if DATABASE_URL else "?"
    rows = conn.execute(f"SELECT * FROM predictions ORDER BY id DESC LIMIT {placeholder}", (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_summary() -> dict:
    conn = get_conn()
    total = conn.execute("SELECT COUNT(*) AS c FROM predictions").fetchone()["c"]
    by_tier = conn.execute(
        "SELECT risk_label, COUNT(*) AS c FROM predictions GROUP BY risk_label"
    ).fetchall()
    avg_default_proba = conn.execute("SELECT AVG(default_probability) AS a FROM predictions").fetchone()["a"]
    conn.close()
    return {
        "total_predictions": total,
        "by_risk_tier": {r["risk_label"]: r["c"] for r in by_tier if r["risk_label"]},
        "avg_default_probability": avg_default_proba,
    }


def get_feature_means(limit: int = 500) -> dict:
    """Mean of each numeric feature over the most recent `limit` logged
    predictions — used to compare against the training baseline."""
    conn = get_conn()
    cols = ", ".join(f"AVG({c}) AS {c}" for c in
                      ["loan_count", "avg_loan", "transaction_frequency", "average_transaction_value", "audit_activity"])
    placeholder = "%s" if DATABASE_URL else "?"
    row = conn.execute(
        f"SELECT {cols} FROM (SELECT * FROM predictions ORDER BY id DESC LIMIT {placeholder}) AS recent", (limit,)
    ).fetchone()
    conn.close()
    if row is None:
        return {}
    mapping = {
        "loan_count": "LoanCount",
        "avg_loan": "AvgLoan",
        "transaction_frequency": "TransactionFrequency",
        "average_transaction_value": "AverageTransactionValue",
        "audit_activity": "AuditActivity",
    }
    return {mapping[k]: v for k, v in dict(row).items() if v is not None}


def get_recent_count(limit: int = 500) -> int:
    """Return how many rows were actually included in a recent-window query."""
    conn = get_conn()
    placeholder = "%s" if DATABASE_URL else "?"
    count = conn.execute(
        f"SELECT COUNT(*) AS c FROM (SELECT id FROM predictions ORDER BY id DESC LIMIT {placeholder}) AS recent",
        (limit,),
    ).fetchone()["c"]
    conn.close()
    return count