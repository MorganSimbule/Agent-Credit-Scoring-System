import hashlib
import json
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from pathlib import Path

import joblib
import pandas as pd
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Query, Request, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader, OAuth2PasswordRequestForm
from pydantic import BaseModel, Field, field_validator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

# ------------------------------------------------------------------
# Environment configuration
# ------------------------------------------------------------------
BACKEND_DIR = Path(__file__).resolve().parent
load_dotenv(BACKEND_DIR / ".env")


def resolve_backend_path(value: str) -> str:
    path = Path(value)
    return str(path if path.is_absolute() else BACKEND_DIR / path)


if os.getenv("PREDICTIONS_DB_PATH"):
    os.environ["PREDICTIONS_DB_PATH"] = resolve_backend_path(os.environ["PREDICTIONS_DB_PATH"])


try:
    from db import (
        init_db, log_prediction, get_summary, get_recent, get_feature_means, get_recent_count,
        create_user, get_user_by_username, get_user_by_id, list_users, set_user_active,
        reset_user_password, log_audit_event, get_audit_events,
        update_user_role, change_user_password, add_session, revoke_session, revoke_session_by_id, list_sessions,
        record_drift_history, get_drift_history, record_model_deployment, get_model_deployments,
        get_user_predictions, update_prediction_status, create_saved_profile, list_saved_profiles, delete_saved_profile,
    )
    from schemas import (
        LogSummaryResponse, LogRecentResponse, DriftReport,
        AgentRegister, UserOut, Token, AgentStatusUpdate,
    )
    import auth
except ModuleNotFoundError:
    from .db import (
        init_db, log_prediction, get_summary, get_recent, get_feature_means, get_recent_count,
        create_user, get_user_by_username, get_user_by_id, list_users, set_user_active,
        reset_user_password, log_audit_event, get_audit_events,
        update_user_role, change_user_password, add_session, revoke_session, revoke_session_by_id, list_sessions,
        record_drift_history, get_drift_history, record_model_deployment, get_model_deployments,
        get_user_predictions, update_prediction_status, create_saved_profile, list_saved_profiles, delete_saved_profile,
    )
    from .schemas import (
        LogSummaryResponse, LogRecentResponse, DriftReport,
        AgentRegister, UserOut, Token, AgentStatusUpdate,
    )
    from . import auth

BINARY_MODEL_PATH = resolve_backend_path(
    os.getenv("BINARY_MODEL_PATH", "models/binary_default_pipeline(1).joblib")
)
MULTICLASS_MODEL_PATH = resolve_backend_path(
    os.getenv("MULTICLASS_MODEL_PATH", "models/multiclass_risk_pipeline(1).joblib")
)
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY")  # required to call /admin/reload-models

# Admin *user* accounts (for the dashboard/agent-management endpoints) are
# never created through self-registration — agents self-register, admins
# don't. If set, one admin login is seeded/updated at startup so there's
# always a way in. Change the password by changing these and restarting.
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
ALLOWED_ORIGINS = [
    o.strip()
    for o in os.getenv(
        "ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000"
    ).split(",")
    if o.strip()
]
PREDICT_RATE_LIMIT = os.getenv("PREDICT_RATE_LIMIT", "60/minute")
BATCH_RATE_LIMIT = os.getenv("BATCH_RATE_LIMIT", "10/minute")

# ------------------------------------------------------------------
# Logging
# ------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("credit-scoring-api")

if not ADMIN_API_KEY:
    logger.warning(
        "ADMIN_API_KEY is not set — /admin/reload-models will reject all requests "
        "until it is configured via environment variable or .env file."
    )

RISK_CATEGORY_LABELS = {0: "LOW RISK", 1: "MEDIUM RISK", 2: "HIGH RISK", 3: "VERY HIGH RISK"}

# Occupations actually seen during training — used for a soft warning, not a hard block
# (OneHotEncoder has handle_unknown='ignore', so unseen values won't crash, but it's
# useful for the caller to know the model has no learned signal for a new one)
KNOWN_OCCUPATIONS = {"Trader", "Farmer", "Vendor", "Driver", "Unspecified"}  # adjust to match your actual training data

# ------------------------------------------------------------------
# Models are loaded once per worker process, at startup, via lifespan.
# Each gunicorn/uvicorn worker gets its own copy — no shared mutable
# state between requests or processes. The API process can use multiple
# workers, but prediction logs require a shared external database before
# running multiple container replicas.
#
# model_metadata tracks, per pipeline, a short content hash (fingerprint
# of the .joblib file bytes) and the load timestamp, so every prediction
# response can be traced back to exactly which model artifact produced it.
# ------------------------------------------------------------------
ml_models: dict = {}
model_metadata: dict = {}


def _file_hash(path: str, length: int = 8) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()[:length]


def _load_models() -> None:
    logger.info("Loading models...")
    loaded_models = {
        "binary": joblib.load(BINARY_MODEL_PATH),
        "multiclass": joblib.load(MULTICLASS_MODEL_PATH),
    }
    for name, model in loaded_models.items():
        if not callable(getattr(model, "predict", None)) or not callable(getattr(model, "predict_proba", None)):
            raise ValueError(f"{name} model must provide predict and predict_proba")

    binary_classes = set(loaded_models["binary"].named_steps["model"].classes_)
    multiclass_classes = set(loaded_models["multiclass"].named_steps["model"].classes_)
    if binary_classes != {0, 1}:
        raise ValueError(f"binary model classes must be {{0, 1}}, got {binary_classes}")
    if not multiclass_classes.issubset(set(RISK_CATEGORY_LABELS)):
        raise ValueError(f"multiclass model has unsupported classes: {multiclass_classes}")

    ml_models.update(loaded_models)

    loaded_at = datetime.now(timezone.utc).isoformat()
    model_metadata["binary"] = {"version": _file_hash(BINARY_MODEL_PATH), "loaded_at": loaded_at}
    model_metadata["multiclass"] = {"version": _file_hash(MULTICLASS_MODEL_PATH), "loaded_at": loaded_at}
    logger.info(
        "Models loaded successfully. binary=%s multiclass=%s",
        model_metadata["binary"]["version"], model_metadata["multiclass"]["version"],
    )


def _seed_admin_user() -> None:
    """Ensure at least one admin account exists. Admins are never created
    via self-registration, so this is the only way one gets made."""
    if not ADMIN_USERNAME or not ADMIN_PASSWORD:
        logger.warning(
            "ADMIN_USERNAME / ADMIN_PASSWORD not set — no admin login will exist "
            "until you set them and restart. Agent self-registration is unaffected."
        )
        return
    existing = get_user_by_username(ADMIN_USERNAME)
    if existing is None:
        create_user(ADMIN_USERNAME, auth.hash_password(ADMIN_PASSWORD), role="admin", full_name="Administrator")
        logger.info("Seeded admin account '%s'.", ADMIN_USERNAME)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()  # Initialize database on startup
    _seed_admin_user()
    _load_models()
    record_model_deployment("startup", model_metadata["binary"]["version"], model_metadata["multiclass"]["version"], "loaded")
    yield
    ml_models.clear()
    model_metadata.clear()
    logger.info("Models unloaded, shutting down.")


app = FastAPI(
    title="Credit Scoring API",
    description=(
        "Multi-class credit scoring service for mobile money agents. "
        "Serves two trained scikit-learn pipelines: a binary default-risk "
        "classifier and a four-class risk-category classifier. Built as "
        "part of a University of Zambia capstone project in partnership "
        "with Hobbiton Investments."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# ------------------------------------------------------------------
# Rate limiting — per-client-IP, different ceilings for single vs batch
# endpoints since batch calls are heavier per-request.
# ------------------------------------------------------------------
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ------------------------------------------------------------------
# CORS — origins come from ALLOWED_ORIGINS in .env; comma-separated for
# multiple values. Defaults to localhost:3000 for local dev.
# ------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["*"],
)


# ------------------------------------------------------------------
# Basic request logging middleware — request id, path, latency, status
# ------------------------------------------------------------------
@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = str(uuid.uuid4())[:8]
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "id=%s method=%s path=%s status=%d duration_ms=%.1f",
        request_id, request.method, request.url.path, response.status_code, duration_ms,
    )
    response.headers["X-Request-ID"] = request_id
    return response


# ------------------------------------------------------------------
# Admin auth — simple API key check via the X-API-Key header.
# Not a substitute for real auth (OAuth/JWT) in a real production system,
# but stops the endpoint being wide open to anyone who finds the URL.
# ------------------------------------------------------------------
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_admin_key(provided_key: str = Security(api_key_header)) -> None:
    if not ADMIN_API_KEY:
        raise HTTPException(status_code=503, detail="Admin endpoint is disabled: ADMIN_API_KEY is not configured.")
    if provided_key != ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key.")


# ------------------------------------------------------------------
# Auth routes — agent self-registration/login, plus admin agent management.
# Admin accounts are seeded at startup (see _seed_admin_user), never
# created here: this router only ever mints role='agent' accounts.
# ------------------------------------------------------------------
@app.post(
    "/auth/register",
    response_model=UserOut,
    tags=["Auth"],
    summary="Self-register as an agent",
    description="Creates a new agent account, active immediately. Always role='agent' — admin accounts are not created through this endpoint.",
)
def register_agent(payload: AgentRegister):
    if get_user_by_username(payload.username) is not None:
        raise HTTPException(status_code=409, detail="Username is already taken.")
    user = create_user(
        username=payload.username,
        password_hash=auth.hash_password(payload.password),
        role="agent",
        full_name=payload.full_name,
    )
    user["is_active"] = bool(user["is_active"])
    return UserOut(**user)


@app.post(
    "/auth/login",
    response_model=Token,
    tags=["Auth"],
    summary="Log in and receive a bearer token",
    description="Accepts standard OAuth2 password-grant form fields (username, password). Works with the Swagger 'Authorize' button.",
)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = get_user_by_username(form_data.username)
    if user is None or not auth.verify_password(form_data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Incorrect username or password.")
    if not user["is_active"]:
        raise HTTPException(status_code=403, detail="This account has been disabled by an admin.")
    token = auth.create_access_token(user["id"], user["username"], user["role"])
    add_session(token, {"user_id": user["id"], "username": user["username"]}, (datetime.now(timezone.utc) + timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)).isoformat())
    return Token(access_token=token, role=user["role"], username=user["username"])


@app.get(
    "/auth/me",
    response_model=UserOut,
    tags=["Auth"],
    summary="Get the logged-in user's profile",
)
def get_me(current_user: dict = Depends(auth.get_current_user)):
    user = get_user_by_id(current_user["user_id"])
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")
    return UserOut(**user, is_active=bool(user["is_active"]))


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1, max_length=128)
    new_password: str = Field(..., min_length=8, max_length=128)


@app.post("/auth/change-password", tags=["Auth"], summary="Change the current user's password")
def change_password(payload: ChangePasswordRequest, current_user: dict = Depends(auth.get_current_user)):
    user = get_user_by_id(current_user["user_id"])
    if user is None or not auth.verify_password(payload.current_password, user["password_hash"]):
        raise HTTPException(status_code=400, detail="Current password is incorrect.")
    change_user_password(current_user["user_id"], auth.hash_password(payload.new_password))
    log_audit_event(current_user, "password_changed", user)
    return {"status": "password_changed"}


@app.post("/auth/logout", tags=["Auth"], summary="Revoke the current session")
def logout(token: str = Depends(auth.oauth2_scheme), current_user: dict = Depends(auth.get_current_user)):
    revoke_session(token)
    log_audit_event(current_user, "session_revoked", current_user)
    return {"status": "logged_out"}


@app.get(
    "/admin/agents",
    response_model=list[UserOut],
    tags=["Admin"],
    summary="List all agent accounts",
    description="Admin-only. Lists every agent account so the admin can oversee who's registered and active.",
)
def list_agents(current_user: dict = Depends(auth.require_role("admin"))):
    users = list_users(role="agent")
    return [UserOut(**{**u, "is_active": bool(u["is_active"])}) for u in users]


@app.get("/admin/users", response_model=list[UserOut], tags=["Admin"], summary="List all users")
def list_all_users(current_user: dict = Depends(auth.require_role("admin"))):
    users = list_users()
    return [UserOut(**{**u, "is_active": bool(u["is_active"])}) for u in users]


@app.patch(
    "/admin/agents/{agent_id}",
    response_model=UserOut,
    tags=["Admin"],
    summary="Activate or disable an agent account",
    description="Admin-only. Disabling an agent immediately blocks new logins; existing tokens still expire naturally within ACCESS_TOKEN_EXPIRE_MINUTES.",
)
def update_agent_status(agent_id: int, payload: AgentStatusUpdate, current_user: dict = Depends(auth.require_role("admin"))):
    target = get_user_by_id(agent_id)
    if target is None or target["role"] != "agent":
        raise HTTPException(status_code=404, detail="Agent not found.")
    updated = set_user_active(agent_id, payload.is_active)
    log_audit_event(current_user, "agent_status_changed", updated, f"is_active={payload.is_active}")
    return UserOut(**{**updated, "is_active": bool(updated["is_active"])})


class AgentPasswordReset(BaseModel):
    password: str = Field(..., min_length=8, max_length=128)


@app.patch(
    "/admin/agents/{agent_id}/password",
    response_model=UserOut,
    tags=["Admin"],
    summary="Reset an agent password",
    description="Admin-only. Replaces the selected agent password with a new bcrypt hash.",
)
def reset_agent_password(
    agent_id: int,
    payload: AgentPasswordReset,
    current_user: dict = Depends(auth.require_role("admin")),
):
    target = get_user_by_id(agent_id)
    if target is None or target["role"] != "agent":
        raise HTTPException(status_code=404, detail="Agent not found.")
    updated = reset_user_password(agent_id, auth.hash_password(payload.password))
    log_audit_event(current_user, "agent_password_reset", updated)
    return UserOut(**{**updated, "is_active": bool(updated["is_active"])})


class RoleUpdate(BaseModel):
    role: str = Field(..., pattern="^(agent|admin|analyst|auditor)$")


@app.patch("/admin/users/{user_id}/role", response_model=UserOut, tags=["Admin"], summary="Change a user's role")
def change_role(user_id: int, payload: RoleUpdate, current_user: dict = Depends(auth.require_role("admin"))):
    target = get_user_by_id(user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found.")
    updated = update_user_role(user_id, payload.role)
    log_audit_event(current_user, "role_changed", updated, f"role={payload.role}")
    return UserOut(**{**updated, "is_active": bool(updated["is_active"])})


@app.get("/admin/sessions", tags=["Admin"], summary="List recent login sessions")
def get_sessions(current_user: dict = Depends(auth.require_role("admin"))):
    return {"sessions": list_sessions(100)}


@app.patch("/admin/sessions/{session_id}/revoke", tags=["Admin"], summary="Revoke a login session")
def revoke_admin_session(session_id: int, current_user: dict = Depends(auth.require_role("admin"))):
    revoke_session_by_id(session_id)
    log_audit_event(current_user, "session_revoked", details=f"session_id={session_id}")
    return {"status": "revoked"}


@app.get("/api/model-deployments", tags=["Admin"], summary="List model deployment history")
def model_deployments(current_user: dict = Depends(auth.require_role("admin"))):
    return {"deployments": get_model_deployments(50)}


@app.get(
    "/api/audit-events",
    tags=["Admin"],
    summary="List administrator audit events",
)
def get_admin_audit_events(limit: int = 100, current_user: dict = Depends(auth.require_role("admin"))):
    try:
        return {"events": get_audit_events(limit=max(1, min(limit, 500)))}
    except Exception:
        logger.exception("Failed to get audit events")
        raise HTTPException(status_code=500, detail="Failed to retrieve audit events")


# ------------------------------------------------------------------
# Request schema with validation
# ------------------------------------------------------------------
class CustomerRequest(BaseModel):
    ClientID: str | None = Field(default=None, max_length=100)
    LoanCount: int = Field(..., ge=0, le=100, description="Number of loans taken, must be 0-100")
    AvgLoan: float = Field(..., ge=0, description="Average loan amount, must be non-negative")
    TransactionFrequency: float = Field(..., ge=0, description="Transaction count, must be non-negative")
    AverageTransactionValue: float = Field(..., ge=0, description="Average transaction value, must be non-negative")
    AuditActivity: int = Field(..., ge=0, description="Number of audit log events, must be non-negative")
    Occupation: str = Field(..., min_length=1, max_length=50)

    # TODO if you retrain with Age included:
    # Age: int = Field(..., ge=18, le=100, description="Customer age, must be 18-100")

    @field_validator("Occupation")
    @classmethod
    def occupation_not_blank(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Occupation cannot be blank or whitespace only")
        return cleaned.title()

    @field_validator("AvgLoan", "AverageTransactionValue")
    @classmethod
    def reject_unreasonably_large_values(cls, v: float) -> float:
        # Sanity ceiling — adjust based on your actual data's realistic range.
        # Catches obvious data-entry errors (e.g. an extra zero) without being
        # a proper business-rule check.
        if v > 1_000_000:
            raise ValueError(f"Value {v} looks unrealistic — check for a data entry error")
        return v


class BatchRequest(BaseModel):
    customers: list[CustomerRequest] = Field(..., min_length=1, max_length=5000)


class SavedProfileRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    ClientID: str | None = Field(default=None, max_length=100)
    LoanCount: int = Field(..., ge=0, le=100)
    AvgLoan: float = Field(..., ge=0)
    TransactionFrequency: float = Field(..., ge=0)
    AverageTransactionValue: float = Field(..., ge=0)
    AuditActivity: int = Field(..., ge=0)
    Occupation: str = Field(..., min_length=1, max_length=50)


class ReviewStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(New|Under Review|Approved|Declined|Needs More Information)$")


class PredictionResponse(BaseModel):
    probability_of_default: float
    predicted_default_flag: int
    model_version: str


class RiskCategoryResponse(BaseModel):
    risk_category: str
    risk_category_code: int
    risk_category_probabilities: dict
    model_version: str


class BatchRiskCategoryResponse(BaseModel):
    count: int
    model_version: str
    results: list[RiskCategoryResponse]


class BatchPredictionResponse(BaseModel):
    count: int
    model_version: str
    results: list[PredictionResponse]


# ------------------------------------------------------------------
# Shared helpers
# ------------------------------------------------------------------
def build_feature_row(customer: CustomerRequest) -> pd.DataFrame:
    return pd.DataFrame([customer.model_dump()])


def build_feature_frame(customers: list[CustomerRequest]) -> pd.DataFrame:
    return pd.DataFrame([c.model_dump() for c in customers])


def warn_unknown_occupations(customers: list[CustomerRequest]) -> None:
    unknown = {c.Occupation for c in customers} - KNOWN_OCCUPATIONS
    if unknown:
        logger.warning("Unrecognized occupation(s) not seen during training: %s", unknown)


def log_single_prediction(customer: CustomerRequest, probability: float, prediction: int, risk_code: int, risk_label: str, submitted_by: dict | None = None) -> None:
    """Log a single prediction to the database."""
    try:
        log_prediction(
            features=customer.model_dump(),
            result={
                "default_probability": probability,
                "default_prediction": prediction,
                "risk_category": risk_code,
                "risk_label": risk_label,
            },
            source="single",
            submitted_by=submitted_by,
        )
    except Exception as e:
        logger.error(f"Failed to log prediction: {e}")


def log_batch_predictions(customers: list[CustomerRequest], probabilities: list[float], predictions: list[int], submitted_by: dict | None = None) -> None:
    """Log batch predictions to the database."""
    try:
        for customer, prob, pred in zip(customers, probabilities, predictions):
            log_prediction(
                features=customer.model_dump(),
                result={
                    "default_probability": prob,
                    "default_prediction": pred,
                    "risk_category": None,
                    "risk_label": None,
                },
                source="batch",
                submitted_by=submitted_by,
            )
    except Exception as e:
        logger.error(f"Failed to log batch predictions: {e}")


def log_batch_risk_predictions(customers: list[CustomerRequest], risk_codes: list[int], submitted_by: dict | None = None) -> None:
    """Log batch risk category predictions to the database."""
    try:
        for customer, code in zip(customers, risk_codes):
            log_prediction(
                features=customer.model_dump(),
                result={
                    "default_probability": None,
                    "default_prediction": None,
                    "risk_category": code,
                    "risk_label": RISK_CATEGORY_LABELS.get(int(code), "UNKNOWN"),
                },
                source="batch",
                submitted_by=submitted_by,
            )
    except Exception as e:
        logger.error(f"Failed to log batch risk predictions: {e}")


# ------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------
@app.get(
    "/",
    tags=["Health"],
    summary="Health check",
    description=(
        "Reports whether the service is up and whether both ML pipelines "
        "loaded successfully, along with the currently loaded model versions. "
        "Intended for load balancer / container health checks."
    ),
)
def health_check():
    models_ready = "binary" in ml_models and "multiclass" in ml_models
    return {
        "status": "ok" if models_ready else "degraded",
        "models_loaded": models_ready,
        "model_versions": {
            name: meta["version"] for name, meta in model_metadata.items()
        },
    }


@app.get("/api/my-predictions", tags=["Agent Workspace"], summary="List the current user's predictions")
def my_predictions(current_user: dict = Depends(auth.require_role("agent", "admin"))):
    return {"predictions": get_user_predictions(current_user["user_id"])}


@app.patch("/api/my-predictions/{prediction_id}/status", tags=["Agent Workspace"], summary="Update a prediction follow-up status")
def prediction_status(prediction_id: int, payload: ReviewStatusUpdate, current_user: dict = Depends(auth.require_role("agent", "admin"))):
    row = update_prediction_status(prediction_id, current_user["user_id"], payload.status)
    if row is None:
        raise HTTPException(status_code=404, detail="Prediction not found.")
    return row


@app.get("/api/saved-profiles", tags=["Agent Workspace"], summary="List saved profiles")
def saved_profiles(current_user: dict = Depends(auth.require_role("agent", "admin"))):
    return {"profiles": list_saved_profiles(current_user["user_id"])}


@app.post("/api/saved-profiles", tags=["Agent Workspace"], summary="Save a reusable profile")
def save_profile(payload: SavedProfileRequest, current_user: dict = Depends(auth.require_role("agent", "admin"))):
    return create_saved_profile(current_user["user_id"], payload.model_dump())


@app.delete("/api/saved-profiles/{profile_id}", tags=["Agent Workspace"], summary="Delete a saved profile")
def remove_profile(profile_id: int, current_user: dict = Depends(auth.require_role("agent", "admin"))):
    delete_saved_profile(profile_id, current_user["user_id"])
    return {"status": "deleted"}


@app.post(
    "/predict",
    response_model=PredictionResponse,
    tags=["Default Prediction"],
    summary="Predict default probability for one agent",
    description=(
        "Scores a single mobile money agent using the binary default-risk "
        "pipeline. Returns the probability of default and a 0/1 predicted "
        "flag, along with the model version that produced the prediction. "
        "The prediction is also logged to the database for monitoring."
    ),
)
@limiter.limit(PREDICT_RATE_LIMIT)
def predict(request: Request, customer: CustomerRequest, current_user: dict = Depends(auth.require_role("agent", "admin"))):
    warn_unknown_occupations([customer])
    X_new = build_feature_row(customer)
    try:
        probability_of_default = float(ml_models["binary"].predict_proba(X_new)[0, 1])
        predicted_default_flag = int(ml_models["binary"].predict(X_new)[0])
    except Exception:
        logger.exception("Binary prediction failed")
        raise HTTPException(status_code=500, detail="Prediction failed")

    # Log the prediction
    log_single_prediction(customer, probability_of_default, predicted_default_flag, None, None, submitted_by=current_user)

    return PredictionResponse(
        probability_of_default=round(probability_of_default, 4),
        predicted_default_flag=predicted_default_flag,
        model_version=model_metadata["binary"]["version"],
    )


@app.post(
    "/predict/batch",
    response_model=BatchPredictionResponse,
    tags=["Default Prediction"],
    summary="Predict default probability for multiple agents",
    description=(
        "Scores up to 5000 agents in a single vectorized call to the binary "
        "default-risk pipeline. Validation is all-or-nothing: if any customer "
        "in the array fails validation, the entire batch is rejected with a "
        "422 and no predictions are made. Each prediction is logged to the "
        "database for monitoring."
    ),
)
@limiter.limit(BATCH_RATE_LIMIT)
def predict_batch(request: Request, payload: BatchRequest, current_user: dict = Depends(auth.require_role("agent", "admin"))):
    warn_unknown_occupations(payload.customers)
    X_new = build_feature_frame(payload.customers)
    try:
        probabilities = ml_models["binary"].predict_proba(X_new)[:, 1]
        flags = ml_models["binary"].predict(X_new)
    except Exception:
        logger.exception("Batch binary prediction failed")
        raise HTTPException(status_code=500, detail="Batch prediction failed")

    # Log the batch predictions
    log_batch_predictions(payload.customers, [float(p) for p in probabilities], [int(f) for f in flags], submitted_by=current_user)

    results = [
        PredictionResponse(
            probability_of_default=round(float(p), 4),
            predicted_default_flag=int(f),
            model_version=model_metadata["binary"]["version"],
        )
        for p, f in zip(probabilities, flags)
    ]
    return BatchPredictionResponse(
        count=len(results), model_version=model_metadata["binary"]["version"], results=results
    )


@app.post(
    "/predict-risk-category",
    response_model=RiskCategoryResponse,
    tags=["Risk Category"],
    summary="Classify one agent's risk category",
    description=(
        "Classifies a single mobile money agent into LOW / MEDIUM / HIGH / "
        "VERY HIGH risk using the multiclass pipeline. Returns the predicted "
        "category, its numeric code, and the full probability distribution "
        "across all four categories. The prediction is also logged to the "
        "database for monitoring."
    ),
)
@limiter.limit(PREDICT_RATE_LIMIT)
def predict_risk_category(request: Request, customer: CustomerRequest, current_user: dict = Depends(auth.require_role("agent", "admin"))):
    warn_unknown_occupations([customer])
    X_new = build_feature_row(customer)
    try:
        risk_category_code = int(ml_models["multiclass"].predict(X_new)[0])
        risk_category_probs = ml_models["multiclass"].predict_proba(X_new)[0]
    except Exception:
        logger.exception("Multiclass prediction failed")
        raise HTTPException(status_code=500, detail="Prediction failed")

    risk_label = RISK_CATEGORY_LABELS[risk_category_code]

    # Log the prediction
    log_single_prediction(customer, None, None, risk_category_code, risk_label, submitted_by=current_user)

    return RiskCategoryResponse(
        risk_category=risk_label,
        risk_category_code=risk_category_code,
        risk_category_probabilities={
            RISK_CATEGORY_LABELS[i]: round(float(p), 4) for i, p in enumerate(risk_category_probs)
        },
        model_version=model_metadata["multiclass"]["version"],
    )


@app.post(
    "/predict-risk-category/batch",
    response_model=BatchRiskCategoryResponse,
    tags=["Risk Category"],
    summary="Classify risk category for multiple agents",
    description=(
        "Scores up to 5000 agents in a single call using the multiclass "
        "pipeline's native vectorized predict/predict_proba over the whole "
        "batch, rather than looping row-by-row — this scales far better than "
        "N separate calls to /predict-risk-category for bulk/nightly "
        "re-scoring jobs. Validation is all-or-nothing across the batch, and "
        "each prediction is logged to the database for monitoring."
    ),
)
@limiter.limit(BATCH_RATE_LIMIT)
def predict_risk_category_batch(request: Request, payload: BatchRequest, current_user: dict = Depends(auth.require_role("agent", "admin"))):
    warn_unknown_occupations(payload.customers)
    X_new = build_feature_frame(payload.customers)
    try:
        codes = ml_models["multiclass"].predict(X_new)
        probs = ml_models["multiclass"].predict_proba(X_new)
    except Exception:
        logger.exception("Batch multiclass prediction failed")
        raise HTTPException(status_code=500, detail="Batch prediction failed")

    # Log the batch predictions
    log_batch_risk_predictions(payload.customers, [int(code) for code in codes], submitted_by=current_user)

    results = [
        RiskCategoryResponse(
            risk_category=RISK_CATEGORY_LABELS[int(code)],
            risk_category_code=int(code),
            risk_category_probabilities={
                RISK_CATEGORY_LABELS[i]: round(float(p), 4) for i, p in enumerate(row)
            },
            model_version=model_metadata["multiclass"]["version"],
        )
        for code, row in zip(codes, probs)
    ]
    return BatchRiskCategoryResponse(
        count=len(results), model_version=model_metadata["multiclass"]["version"], results=results
    )


@app.post(
    "/admin/reload-models",
    tags=["Admin"],
    summary="Hot-reload both models from disk",
    description=(
        "Re-reads both .joblib pipelines from disk without restarting the "
        "process — useful after retraining. Requires a valid X-API-Key "
        "header matching ADMIN_API_KEY (set via environment variable or "
        ".env file). Returns 401 if the key is missing/wrong, or 503 if no "
        "ADMIN_API_KEY is configured on the server at all."
    ),
    dependencies=[Depends(require_admin_key)],
)
def reload_models():
    try:
        _load_models()
    except Exception:
        logger.exception("Model reload failed")
        raise HTTPException(status_code=500, detail="Model reload failed")
    record_model_deployment("api-key-admin", model_metadata["binary"]["version"], model_metadata["multiclass"]["version"], "reloaded")
    return {"status": "reloaded", "model_versions": {name: meta["version"] for name, meta in model_metadata.items()}}


# ------------------------------------------------------------------
# Monitoring & Logging Endpoints
# ------------------------------------------------------------------
@app.get(
    "/api/logs/summary",
    response_model=LogSummaryResponse,
    tags=["Monitoring"],
    summary="Summarize logged predictions",
    description=(
        "Aggregates every prediction logged so far: total count, a "
        "breakdown by risk tier, and the average predicted default "
        "probability across all logged single/batch predictions."
    ),
)
def get_logs_summary(current_user: dict = Depends(auth.require_role("admin"))):
    """Get summary of logged predictions: total count, distribution by risk tier, avg default probability."""
    try:
        summary = get_summary()
        return summary
    except Exception:
        logger.exception("Failed to get logs summary")
        raise HTTPException(status_code=500, detail="Failed to retrieve summary")


@app.get(
    "/api/logs/recent",
    response_model=LogRecentResponse,
    tags=["Monitoring"],
    summary="List recent logged predictions",
    description=(
        "Returns the most recent N logged predictions (single or batch), "
        "most recent first, including the full feature inputs and outputs "
        "for each. Defaults to 50, capped at 1000."
    ),
)
def get_logs_recent(limit: int = 50, current_user: dict = Depends(auth.require_role("admin"))):
    """Get the most recent N logged predictions (default 50)."""
    try:
        if limit < 1 or limit > 1000:
            limit = 50
        recent = get_recent(limit=limit)
        return {"count": len(recent), "predictions": recent}
    except Exception:
        logger.exception("Failed to get recent logs")
        raise HTTPException(status_code=500, detail="Failed to retrieve recent logs")


@app.get(
    "/api/logs/drift",
    response_model=DriftReport,
    tags=["Monitoring"],
    summary="Check for feature drift vs. training data",
    description=(
        "Compares the mean of each numeric feature over the most recent "
        "logged predictions against the training-set baseline saved by "
        "train_export.py (models/metadata.json). Reports a z-score per "
        "feature and flags any feature more than 2 standard deviations "
        "from its training mean, as a lightweight signal that incoming "
        "traffic no longer resembles the data the models were trained on. "
        "Not a full drift-detection system — a coarse sanity check only."
    ),
)
def get_drift_check(baseline_window: int = Query(500, ge=1, le=5000), current_user: dict = Depends(auth.require_role("admin"))):
    """
    Compare recent feature means against training baseline (from metadata.json).
    Returns z-scores for each feature to detect distribution shift.
    """
    try:
        metadata_file = BACKEND_DIR / "models" / "metadata.json"
        if not metadata_file.exists():
            raise HTTPException(status_code=404, detail="Metadata file not found. Run train_export.py first.")

        with open(metadata_file) as f:
            metadata = json.load(f)

        feature_baseline = metadata.get("feature_baseline", {})
        if not feature_baseline:
            raise HTTPException(status_code=400, detail="No feature baseline in metadata.")

        # Get recent feature means
        recent_means = get_feature_means(limit=baseline_window)

        # Calculate z-scores for each feature
        drift_report = {}
        for feature, baseline_stats in feature_baseline.items():
            baseline_mean = baseline_stats.get("mean", 0)
            baseline_std = baseline_stats.get("std", 1)
            recent_mean = recent_means.get(feature)

            if recent_mean is None:
                continue

            # Calculate z-score
            z_score = (recent_mean - baseline_mean) / (baseline_std + 1e-8)
            flagged = abs(z_score) > 2.0  # Flag if |z| > 2 (2-sigma shift)

            drift_report[feature] = {
                "baseline_mean": baseline_mean,
                "recent_mean": recent_mean,
                "z_score": round(z_score, 3),
                "flagged": flagged,
            }

        report = {
            "sample_size": get_recent_count(limit=baseline_window),
            "trained_at": metadata.get("trained_at"),
            "features": drift_report,
            "any_drift_detected": any(f["flagged"] for f in drift_report.values()),
        }
        record_drift_history(report["sample_size"], report["any_drift_detected"], report)
        return report
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to get drift check")
        raise HTTPException(status_code=500, detail="Failed to retrieve drift analysis")


@app.get("/api/logs/drift-history", tags=["Monitoring"], summary="List historical drift checks")
def drift_history(limit: int = 50, current_user: dict = Depends(auth.require_role("admin"))):
    return {"history": get_drift_history(max(1, min(limit, 500)))}


@app.get("/api/alerts", tags=["Monitoring"], summary="Get current monitoring alerts")
def alerts(current_user: dict = Depends(auth.require_role("admin"))):
    history = get_drift_history(1)
    current = history[0] if history else None
    return {"alerts": ([{"type": "drift", "severity": "warning", "message": "Feature drift detected in the latest check."}] if current and current["any_drift_detected"] else [])}