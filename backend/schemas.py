"""
Pydantic schemas for auth, monitoring, and drift detection endpoints.
"""

from typing import Optional, Any, Literal
from pydantic import BaseModel, Field


# ------------------------------------------------------------------
# Auth / users
# ------------------------------------------------------------------
class AgentRegister(BaseModel):
    """Self-registration — always creates role='agent'. Admin accounts
    are seeded separately and never created through this endpoint."""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8, max_length=128)
    full_name: Optional[str] = Field(default=None, max_length=100)


class UserOut(BaseModel):
    id: int
    username: str
    full_name: Optional[str]
    role: str
    is_active: bool
    created_at: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    username: str


class AgentStatusUpdate(BaseModel):
    is_active: bool


class PredictionsSummary(BaseModel):
    """Summary statistics of logged predictions."""
    total_predictions: int
    by_risk_tier: dict
    avg_default_probability: Optional[float]


class DriftFeature(BaseModel):
    """Individual feature drift analysis."""
    baseline_mean: float
    recent_mean: float
    z_score: float
    flagged: bool


class DriftReport(BaseModel):
    """Full drift detection report."""
    sample_size: int
    trained_at: Optional[str]
    features: dict[str, DriftFeature]
    any_drift_detected: bool


class ModelInfo(BaseModel):
    """Metadata about trained models."""
    binary_model_name: str
    multiclass_model_name: str
    binary_metrics: dict
    multiclass_metrics: dict
    occupations: list[str]
    feature_baseline: Optional[dict] = None
    trained_at: Optional[str] = None


class LogSummaryResponse(BaseModel):
    """Response for /api/logs/summary endpoint."""
    total_predictions: int
    by_risk_tier: dict
    avg_default_probability: Optional[float]


class PredictionLogEntry(BaseModel):
    """A single logged prediction entry."""
    id: int
    timestamp: str
    source: str
    client_id: Optional[str]
    loan_count: Optional[float]
    avg_loan: Optional[float]
    transaction_frequency: Optional[float]
    average_transaction_value: Optional[float]
    audit_activity: Optional[float]
    occupation: Optional[str]
    default_probability: Optional[float]
    default_prediction: Optional[int]
    risk_category: Optional[int]
    risk_label: Optional[str]
    submitted_by_user_id: Optional[int] = None
    submitted_by_username: Optional[str] = None


class LogRecentResponse(BaseModel):
    """Response for /api/logs/recent endpoint."""
    count: int
    predictions: list[PredictionLogEntry]