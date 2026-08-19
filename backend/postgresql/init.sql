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
    risk_label TEXT
);

CREATE INDEX IF NOT EXISTS idx_predictions_timestamp ON predictions (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_predictions_source ON predictions (source);
