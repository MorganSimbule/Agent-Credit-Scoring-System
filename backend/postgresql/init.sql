-- The API also runs this schema through db.init_db() at startup.
-- Keeping this file here makes the PostgreSQL schema visible and lets a
-- freshly created database be inspected before the API starts.
CREATE TABLE IF NOT EXISTS predictions (
    id BIGSERIAL PRIMARY KEY,
    timestamp TEXT NOT NULL,
    source TEXT NOT NULL,
    client_id TEXT,
    loan_count DOUBLE PRECISION,
    avg_loan DOUBLE PRECISION,
    transaction_frequency DOUBLE PRECISION,
    average_transaction_value DOUBLE PRECISION,
    audit_activity DOUBLE PRECISION,
    occupation TEXT,
    default_probability DOUBLE PRECISION,
    default_prediction INTEGER,
    risk_category INTEGER,
    risk_label TEXT,
    review_status TEXT NOT NULL DEFAULT 'New',
    submitted_by_user_id INTEGER,
    submitted_by_username TEXT
);

CREATE INDEX IF NOT EXISTS idx_predictions_timestamp ON predictions (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_predictions_source ON predictions (source);

CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    full_name TEXT,
    role TEXT NOT NULL DEFAULT 'agent',
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_events (
    id BIGSERIAL PRIMARY KEY,
    timestamp TEXT NOT NULL,
    actor_user_id BIGINT,
    actor_username TEXT,
    action TEXT NOT NULL,
    target_user_id BIGINT,
    target_username TEXT,
    details TEXT
);

CREATE INDEX IF NOT EXISTS idx_audit_events_timestamp ON audit_events (timestamp DESC);

CREATE TABLE IF NOT EXISTS drift_history (
    id BIGSERIAL PRIMARY KEY,
    timestamp TEXT NOT NULL,
    sample_size INTEGER NOT NULL,
    any_drift_detected INTEGER NOT NULL,
    report_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS model_deployments (
    id BIGSERIAL PRIMARY KEY,
    deployed_at TEXT NOT NULL,
    deployed_by TEXT,
    binary_version TEXT NOT NULL,
    multiclass_version TEXT NOT NULL,
    status TEXT NOT NULL,
    details TEXT
);

CREATE TABLE IF NOT EXISTS sessions (
    id BIGSERIAL PRIMARY KEY,
    token_hash TEXT NOT NULL UNIQUE,
    user_id BIGINT NOT NULL,
    username TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    revoked INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS saved_profiles (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    name TEXT NOT NULL,
    client_id TEXT,
    loan_count DOUBLE PRECISION,
    avg_loan DOUBLE PRECISION,
    transaction_frequency DOUBLE PRECISION,
    average_transaction_value DOUBLE PRECISION,
    audit_activity DOUBLE PRECISION,
    occupation TEXT,
    created_at TEXT NOT NULL
);
