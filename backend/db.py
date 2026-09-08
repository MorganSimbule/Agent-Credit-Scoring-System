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
import hashlib
import json
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
            risk_label TEXT,
            review_status TEXT NOT NULL DEFAULT 'New',
            submitted_by_user_id INTEGER,
            submitted_by_username TEXT
        )
        """
    )
    existing_columns = {
        row["column_name"]
        for row in conn.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'predictions'
            """
        ).fetchall()
    } if DATABASE_URL else {
        row["name"] for row in conn.execute("PRAGMA table_info(predictions)").fetchall()
    }
    for column, definition in (
        ("submitted_by_user_id", "INTEGER"),
        ("submitted_by_username", "TEXT"),
        ("review_status", "TEXT NOT NULL DEFAULT 'New'"),
    ):
        if column not in existing_columns:
            conn.execute(f"ALTER TABLE predictions ADD COLUMN {column} {definition}")
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS users (
            id {id_definition},
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            full_name TEXT,
            role TEXT NOT NULL DEFAULT 'agent',
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS audit_events (
            id {id_definition},
            timestamp TEXT NOT NULL,
            actor_user_id INTEGER,
            actor_username TEXT,
            action TEXT NOT NULL,
            target_user_id INTEGER,
            target_username TEXT,
            details TEXT
        )
        """
    )
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS drift_history (
            id {id_definition}, timestamp TEXT NOT NULL, sample_size INTEGER NOT NULL,
            any_drift_detected INTEGER NOT NULL, report_json TEXT NOT NULL
        )
        """
    )
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS model_deployments (
            id {id_definition}, deployed_at TEXT NOT NULL, deployed_by TEXT,
            binary_version TEXT NOT NULL, multiclass_version TEXT NOT NULL,
            status TEXT NOT NULL, details TEXT
        )
        """
    )
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS sessions (
            id {id_definition}, token_hash TEXT NOT NULL UNIQUE, user_id INTEGER NOT NULL,
            username TEXT NOT NULL, created_at TEXT NOT NULL, expires_at TEXT NOT NULL,
            revoked INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS saved_profiles (
            id {id_definition}, user_id INTEGER NOT NULL, name TEXT NOT NULL,
            client_id TEXT, loan_count REAL, avg_loan REAL,
            transaction_frequency REAL, average_transaction_value REAL,
            audit_activity REAL, occupation TEXT, created_at TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


# ------------------------------------------------------------------
# User accounts (agents + admins)
# ------------------------------------------------------------------
def create_user(username: str, password_hash: str, role: str, full_name: str | None = None) -> dict:
    conn = get_conn()
    placeholder = "%s" if DATABASE_URL else "?"
    created_at = datetime.now(timezone.utc).isoformat()
    conn.execute(
        f"""
        INSERT INTO users (username, password_hash, full_name, role, is_active, created_at)
        VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, 1, {placeholder})
        """,
        (username, password_hash, full_name, role, created_at),
    )
    conn.commit()
    row = conn.execute(
        f"SELECT id, username, full_name, role, is_active, created_at FROM users WHERE username = {placeholder}",
        (username,),
    ).fetchone()
    conn.close()
    return dict(row)


def get_user_by_username(username: str) -> dict | None:
    conn = get_conn()
    placeholder = "%s" if DATABASE_URL else "?"
    row = conn.execute(f"SELECT * FROM users WHERE username = {placeholder}", (username,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_by_id(user_id: int) -> dict | None:
    conn = get_conn()
    placeholder = "%s" if DATABASE_URL else "?"
    row = conn.execute(f"SELECT * FROM users WHERE id = {placeholder}", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def list_users(role: str | None = None) -> list[dict]:
    conn = get_conn()
    if role:
        placeholder = "%s" if DATABASE_URL else "?"
        rows = conn.execute(
            f"SELECT id, username, full_name, role, is_active, created_at FROM users WHERE role = {placeholder} ORDER BY id",
            (role,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT id, username, full_name, role, is_active, created_at FROM users ORDER BY id"
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def set_user_active(user_id: int, is_active: bool) -> dict | None:
    conn = get_conn()
    placeholder = "%s" if DATABASE_URL else "?"
    conn.execute(
        f"UPDATE users SET is_active = {placeholder} WHERE id = {placeholder}",
        (1 if is_active else 0, user_id),
    )
    conn.commit()
    row = conn.execute(
        f"SELECT id, username, full_name, role, is_active, created_at FROM users WHERE id = {placeholder}",
        (user_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def reset_user_password(user_id: int, password_hash: str) -> dict | None:
    conn = get_conn()
    placeholder = "%s" if DATABASE_URL else "?"
    conn.execute(
        f"UPDATE users SET password_hash = {placeholder} WHERE id = {placeholder}",
        (password_hash, user_id),
    )
    conn.commit()
    row = conn.execute(
        f"SELECT id, username, full_name, role, is_active, created_at FROM users WHERE id = {placeholder}",
        (user_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def update_user_role(user_id: int, role: str) -> dict | None:
    conn = get_conn()
    placeholder = "%s" if DATABASE_URL else "?"
    conn.execute(f"UPDATE users SET role = {placeholder} WHERE id = {placeholder}", (role, user_id))
    conn.commit()
    row = conn.execute(
        f"SELECT id, username, full_name, role, is_active, created_at FROM users WHERE id = {placeholder}",
        (user_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def change_user_password(user_id: int, password_hash: str) -> None:
    conn = get_conn()
    placeholder = "%s" if DATABASE_URL else "?"
    conn.execute(f"UPDATE users SET password_hash = {placeholder} WHERE id = {placeholder}", (password_hash, user_id))
    conn.commit()
    conn.close()


def add_session(token: str, user: dict, expires_at: str) -> None:
    conn = get_conn()
    placeholder = "%s" if DATABASE_URL else "?"
    conn.execute(
        f"INSERT INTO sessions (token_hash, user_id, username, created_at, expires_at) VALUES ({', '.join([placeholder] * 5)})",
        (hashlib.sha256(token.encode()).hexdigest(), user["user_id"], user["username"], datetime.now(timezone.utc).isoformat(), expires_at),
    )
    conn.commit()
    conn.close()


def is_session_revoked(token: str) -> bool:
    conn = get_conn()
    placeholder = "%s" if DATABASE_URL else "?"
    row = conn.execute(f"SELECT revoked, expires_at FROM sessions WHERE token_hash = {placeholder}", (hashlib.sha256(token.encode()).hexdigest(),)).fetchone()
    conn.close()
    return bool(row and (row["revoked"] or row["expires_at"] <= datetime.now(timezone.utc).isoformat()))


def revoke_session(token: str) -> None:
    conn = get_conn()
    placeholder = "%s" if DATABASE_URL else "?"
    conn.execute(f"UPDATE sessions SET revoked = 1 WHERE token_hash = {placeholder}", (hashlib.sha256(token.encode()).hexdigest(),))
    conn.commit()
    conn.close()


def revoke_session_by_id(session_id: int) -> None:
    conn = get_conn()
    placeholder = "%s" if DATABASE_URL else "?"
    conn.execute(f"UPDATE sessions SET revoked = 1 WHERE id = {placeholder}", (session_id,))
    conn.commit()
    conn.close()


def list_sessions(limit: int = 100) -> list[dict]:
    conn = get_conn()
    placeholder = "%s" if DATABASE_URL else "?"
    rows = conn.execute(f"SELECT id, user_id, username, created_at, expires_at, revoked FROM sessions ORDER BY id DESC LIMIT {placeholder}", (limit,)).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def record_drift_history(sample_size: int, any_drift_detected: bool, report: dict) -> None:
    conn = get_conn()
    placeholder = "%s" if DATABASE_URL else "?"
    conn.execute(f"INSERT INTO drift_history (timestamp, sample_size, any_drift_detected, report_json) VALUES ({', '.join([placeholder] * 4)})", (datetime.now(timezone.utc).isoformat(), sample_size, int(any_drift_detected), json.dumps(report)))
    conn.commit()
    conn.close()


def get_drift_history(limit: int = 50) -> list[dict]:
    conn = get_conn()
    placeholder = "%s" if DATABASE_URL else "?"
    rows = conn.execute(f"SELECT * FROM drift_history ORDER BY id DESC LIMIT {placeholder}", (limit,)).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def record_model_deployment(deployed_by: str, binary_version: str, multiclass_version: str, status: str, details: str | None = None) -> None:
    conn = get_conn()
    placeholder = "%s" if DATABASE_URL else "?"
    conn.execute(f"INSERT INTO model_deployments (deployed_at, deployed_by, binary_version, multiclass_version, status, details) VALUES ({', '.join([placeholder] * 6)})", (datetime.now(timezone.utc).isoformat(), deployed_by, binary_version, multiclass_version, status, details))
    conn.commit()
    conn.close()


def get_model_deployments(limit: int = 50) -> list[dict]:
    conn = get_conn()
    placeholder = "%s" if DATABASE_URL else "?"
    rows = conn.execute(f"SELECT * FROM model_deployments ORDER BY id DESC LIMIT {placeholder}", (limit,)).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def log_audit_event(actor: dict, action: str, target: dict | None = None, details: str | None = None):
    conn = get_conn()
    placeholder = "%s" if DATABASE_URL else "?"
    conn.execute(
        f"""
        INSERT INTO audit_events (
            timestamp, actor_user_id, actor_username, action,
            target_user_id, target_username, details
        ) VALUES ({', '.join([placeholder] * 7)})
        """,
        (
            datetime.now(timezone.utc).isoformat(),
            actor.get("user_id"),
            actor.get("username"),
            action,
            (target or {}).get("id"),
            (target or {}).get("username"),
            details,
        ),
    )
    conn.commit()
    conn.close()


def get_audit_events(limit: int = 100) -> list[dict]:
    conn = get_conn()
    placeholder = "%s" if DATABASE_URL else "?"
    rows = conn.execute(
        f"SELECT * FROM audit_events ORDER BY id DESC LIMIT {placeholder}", (limit,)
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def log_prediction(features: dict, result: dict, source: str, submitted_by: dict | None = None):
    """source is one of 'single', 'batch', 'csv' — lets you tell which
    endpoint a logged row came from. submitted_by is the authenticated
    user dict ({user_id, username, role}) from auth.get_current_user,
    so admins can trace every prediction back to the agent who ran it."""
    conn = get_conn()
    placeholders = "%s" if DATABASE_URL else "?"
    conn.execute(
        f"""
        INSERT INTO predictions (
            timestamp, source, client_id, loan_count, avg_loan,
            transaction_frequency, average_transaction_value, audit_activity,
            occupation, default_probability, default_prediction, risk_category, risk_label,
            submitted_by_user_id, submitted_by_username
        ) VALUES ({', '.join([placeholders] * 15)})
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
            (submitted_by or {}).get("user_id"),
            (submitted_by or {}).get("username"),
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


def get_user_predictions(user_id: int, limit: int = 1000) -> list[dict]:
    conn = get_conn()
    placeholder = "%s" if DATABASE_URL else "?"
    rows = conn.execute(f"SELECT * FROM predictions WHERE submitted_by_user_id = {placeholder} ORDER BY id DESC LIMIT {placeholder}", (user_id, limit)).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def update_prediction_status(prediction_id: int, user_id: int, status: str) -> dict | None:
    conn = get_conn()
    placeholder = "%s" if DATABASE_URL else "?"
    conn.execute(f"UPDATE predictions SET review_status = {placeholder} WHERE id = {placeholder} AND submitted_by_user_id = {placeholder}", (status, prediction_id, user_id))
    conn.commit()
    row = conn.execute(f"SELECT * FROM predictions WHERE id = {placeholder} AND submitted_by_user_id = {placeholder}", (prediction_id, user_id)).fetchone()
    conn.close()
    return dict(row) if row else None


def create_saved_profile(user_id: int, profile: dict) -> dict:
    conn = get_conn()
    placeholder = "%s" if DATABASE_URL else "?"
    conn.execute(f"INSERT INTO saved_profiles (user_id, name, client_id, loan_count, avg_loan, transaction_frequency, average_transaction_value, audit_activity, occupation, created_at) VALUES ({', '.join([placeholder] * 10)})", (user_id, profile["name"], profile.get("ClientID"), profile.get("LoanCount"), profile.get("AvgLoan"), profile.get("TransactionFrequency"), profile.get("AverageTransactionValue"), profile.get("AuditActivity"), profile.get("Occupation"), datetime.now(timezone.utc).isoformat()))
    conn.commit()
    row = conn.execute(f"SELECT * FROM saved_profiles WHERE user_id = {placeholder} ORDER BY id DESC LIMIT 1", (user_id,)).fetchone()
    conn.close()
    return dict(row)


def list_saved_profiles(user_id: int) -> list[dict]:
    conn = get_conn()
    placeholder = "%s" if DATABASE_URL else "?"
    rows = conn.execute(f"SELECT * FROM saved_profiles WHERE user_id = {placeholder} ORDER BY id DESC", (user_id,)).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def delete_saved_profile(profile_id: int, user_id: int) -> None:
    conn = get_conn()
    placeholder = "%s" if DATABASE_URL else "?"
    conn.execute(f"DELETE FROM saved_profiles WHERE id = {placeholder} AND user_id = {placeholder}", (profile_id, user_id))
    conn.commit()
    conn.close()


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