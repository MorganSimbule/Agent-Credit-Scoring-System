# Agent Credit Scoring System Architecture

This document describes the system implemented in this repository. Mermaid diagrams are rendered by GitHub, VS Code Markdown preview extensions, and most modern documentation tools.

## Editable System Drawing

- [system-architecture.drawio](system-architecture.drawio) contains the editable diagrams.net system drawing.
- [system-architecture.svg](system-architecture.svg) is a standalone preview of the drawing.

Open the `.drawio` file in [diagrams.net](https://app.diagrams.net/) or import it into a compatible diagram editor.

## 1. System Context

The system scores mobile money agents using two trained scikit-learn pipelines. Agents submit feature data through the React application. Administrators review prediction history, aggregate risk statistics, and feature drift.

```mermaid
flowchart LR
    Agent[Credit scoring agent]
    Admin[Administrator]
    UI[React and Vite frontend]
    API[FastAPI scoring API]
    Models[Binary and multiclass ML pipelines]
    Store[(Prediction and user database)]
    Metadata[Model metadata and training baseline]

    Agent -->|Register, sign in, submit features| UI
    Admin -->|Sign in, manage agents, monitor| UI
    UI -->|Bearer-authenticated HTTP| API
    API -->|Validate and score| Models
    API -->|Write prediction audit row| Store
    API -->|Read summaries, recent logs, drift inputs| Store
    API -->|Read model versions and baseline| Metadata
```

## 2. Container and Deployment Diagram

Local development uses SQLite when `DATABASE_URL` is unset. The supplied Docker Compose deployment uses PostgreSQL, the API container, and Nginx.

```mermaid
flowchart TB
    Browser[Browser]
    Frontend[Frontend dev server\nVite, usually :5173]
    Nginx[Nginx\n:8080]
    API[API container\nGunicorn + Uvicorn workers\n:8000 internal]
    DB[(PostgreSQL 16\ncredit_scoring database)]
    Models[/Joblib model files/]
    Baseline[/models/metadata.json/]

    Browser --> Frontend
    Browser --> Nginx
    Nginx --> API
    API --> DB
    API --> Models
    API --> Baseline

    subgraph Local fallback
        SQLite[(backend/predictions.db)]
    end
    API -. DATABASE_URL unset .-> SQLite
```

### Runtime responsibilities

| Container or module | Responsibility |
| --- | --- |
| React frontend | Login, registration, prediction form, agent workspace, admin monitoring, account and session management |
| Nginx | Reverse proxy and public entry point for Compose deployment |
| FastAPI app | Auth, validation, rate limiting, model inference, agent workspace, governance, logging, monitoring endpoints |
| `db.py` | SQLite/PostgreSQL connection abstraction, schema initialization, prediction/user queries |
| Joblib artifacts | Binary default model and multiclass risk model |
| `metadata.json` | Training feature baseline, model metrics, and training timestamp |
| PostgreSQL or SQLite | Durable predictions, users, sessions, audit, drift history, deployment history, and agent profile data |

## 3. Frontend Route Diagram

```mermaid
flowchart TD
    Root[/]
    Register[/register]
    Console[/console]
    Predict[/console/predict]
    Workspace[/console/workspace]
    Monitoring[/console/monitoring]
    Agents[/console/agents]
    Admin[/admin]

    Root -->|Register| Register
    Root -->|Authenticated user| Console
    Admin -->|Redirect| Monitoring
    Console --> Predict
    Console -->|admin role| Monitoring
    Console -->|admin role| Agents
    Console -->|agent role| Predict
    Console -->|agent role| Workspace
```

All console routes are protected by `ProtectedRoute`. Monitoring and agent management additionally require the `admin` role.

## 4. Prediction Request Sequence

The current prediction page sends two requests for one form submission: one for binary default risk and one for multiclass risk category. Each endpoint writes one audit row, so a single UI submission produces two related `predictions` rows with complementary output fields.

```mermaid
sequenceDiagram
    actor Agent
    participant UI as React Predict page
    participant Auth as AuthContext
    participant API as FastAPI
    participant Validator as Pydantic CustomerRequest
    participant Binary as Binary pipeline
    participant Multi as Multiclass pipeline
    participant DB as predictions table

    Agent->>UI: Enter client and agent features
    UI->>Auth: Read bearer token
    par Binary request
        UI->>API: POST /predict
        API->>Validator: Validate and normalize payload
        Validator-->>API: CustomerRequest
        API->>Binary: predict_proba and predict
        Binary-->>API: Probability and default flag
        API->>DB: Insert source=single binary result
        API-->>UI: PredictionResponse
    and Risk request
        UI->>API: POST /predict-risk-category
        API->>Validator: Validate and normalize payload
        Validator-->>API: CustomerRequest
        API->>Multi: predict and predict_proba
        Multi-->>API: Risk code and probabilities
        API->>DB: Insert source=single risk result
        API-->>UI: RiskCategoryResponse
    end
    UI-->>Agent: Render default and risk results
```

### Prediction endpoints

| Method and route | Role | Purpose | Log source |
| --- | --- | --- | --- |
| `POST /predict` | agent or admin | Binary default probability and flag | `single` |
| `POST /predict-risk-category` | agent or admin | Four-class risk category | `single` |
| `POST /predict/batch` | agent or admin | Up to 5,000 binary predictions | `batch` |
| `POST /predict-risk-category/batch` | agent or admin | Up to 5,000 risk classifications | `batch` |

## 5. Authentication and Authorization Flow

```mermaid
sequenceDiagram
    actor User
    participant UI as React frontend
    participant API as FastAPI auth routes
    participant DB as users table
    participant JWT as JWT signer

    alt New agent
        User->>UI: Submit registration
        UI->>API: POST /auth/register
        API->>DB: Check username and create role=agent
        DB-->>API: User record
        API-->>UI: UserOut
    end

    User->>UI: Submit username and password
    UI->>API: POST /auth/login form data
    API->>DB: Load user by username
    DB-->>API: Password hash, role, active status
    API->>JWT: Create bearer token
    JWT-->>API: access_token
    API-->>UI: token, username, role
    UI->>API: Protected request with Authorization header
    API->>JWT: Decode and validate token
    JWT-->>API: user_id, username, role
    API-->>UI: Authorized response or 401/403
```

Admin accounts are seeded from server environment configuration at startup. Self-registration always creates an agent account.

## 6. Database Schema / ERD

The application supports the following logical schema. The `submitted_by_*` columns are attribution fields; the current implementation does not create a database foreign key between `predictions.submitted_by_user_id` and `users.id`.

```mermaid
erDiagram
    USERS ||--o{ PREDICTIONS : submits

    USERS {
        integer id PK
        string username UK
        string password_hash
        string full_name
        string role
        boolean is_active
        string created_at
    }

    PREDICTIONS {
        integer id PK
        string timestamp
        string source
        string client_id
        float loan_count
        float avg_loan
        float transaction_frequency
        float average_transaction_value
        float audit_activity
        string occupation
        float default_probability
        integer default_prediction
        integer risk_category
        string risk_label
        integer submitted_by_user_id FK_logical
        string submitted_by_username FK_logical
    }
```

### `users`

| Column | Type | Constraints / meaning |
| --- | --- | --- |
| `id` | integer / serial | Primary key |
| `username` | text | Required and unique |
| `password_hash` | text | Bcrypt password hash; never return to clients |
| `full_name` | text | Optional display name |
| `role` | text | `agent` or `admin` |
| `is_active` | boolean/integer | Account status |
| `created_at` | text/timestamp | Account creation time |

### `predictions`

| Column | Type | Constraints / meaning |
| --- | --- | --- |
| `id` | integer / bigserial | Primary key |
| `timestamp` | text/timestamp | UTC insert time |
| `source` | text | `single`, `batch`, or `csv` |
| `client_id` | text | Optional client identifier |
| `loan_count` | numeric | Input feature |
| `avg_loan` | numeric | Input feature |
| `transaction_frequency` | numeric | Input feature |
| `average_transaction_value` | numeric | Input feature |
| `audit_activity` | numeric | Input feature |
| `occupation` | text | Input feature |
| `default_probability` | numeric | Binary model output; nullable for risk-only row |
| `default_prediction` | integer | Binary model flag; nullable for risk-only row |
| `risk_category` | integer | 0 to 3; nullable for binary-only row |
| `risk_label` | text | Human-readable risk tier |
| `submitted_by_user_id` | integer | Authenticated submitter id; nullable for legacy rows |
| `submitted_by_username` | text | Authenticated submitter name; nullable for legacy rows |

## 7. Monitoring and Drift Detection

```mermaid
flowchart LR
    Prediction[Prediction endpoint] --> Log[Insert audit row]
    Log --> Recent[Recent prediction query]
    Log --> Summary[Summary aggregation]
    Log --> Means[Recent feature means]
    Baseline[metadata.json feature baseline] --> Compare[Z-score comparison]
    Means --> Compare
    Compare --> Drift[DriftReport]
    Summary --> Dashboard[Admin Monitoring page]
    Recent --> Dashboard
    Drift --> Dashboard
```

The admin monitoring page calls:

- `GET /api/logs/summary` for total predictions, risk-tier counts, and average default probability.
- `GET /api/logs/recent?limit=10` for the latest audit rows.
- `GET /api/logs/drift` for feature means compared with the training baseline.
- `GET /api/logs/drift-history` and `/api/alerts` for persisted drift checks and current warnings.
- `/api/model-deployments` for startup and reload history.
- `/api/audit-events` for administrator actions.

For a feature $x$, the drift score is calculated as:

$$
z_x = \frac{\bar{x}_{recent} - \mu_{training}}{\sigma_{training} + 10^{-8}}
$$

A feature is flagged when $|z_x| > 2$.

## 8. Model Training and Serving Lifecycle

```mermaid
flowchart LR
    Generator[generate_training_data.py] --> CSV[data/training_data.csv]
    CSV --> Trainer[train_export.py]
    Trainer --> Binary[binary_default_pipeline.joblib]
    Trainer --> Multi[multiclass_risk_pipeline.joblib]
    Trainer --> Metadata[models/metadata.json]
    Binary --> Startup[FastAPI lifespan startup]
    Multi --> Startup
    Metadata --> Monitoring[Drift monitoring]
    Startup --> Predict[Prediction endpoints]
    Predict --> Audit[(Prediction database)]
```

At API startup, both joblib pipelines are loaded and validated. The API records a short file hash as the model version returned in prediction responses. `/admin/reload-models` can reload both artifacts when a configured `X-API-Key` is supplied.

## 9. Operational Boundaries and Failure Points

```mermaid
flowchart TD
    Request[Incoming request] --> CORS[CORS check]
    CORS --> Auth[JWT and role check]
    Auth --> Validate[Pydantic validation]
    Validate --> Rate[Rate limit]
    Rate --> Infer[Model inference]
    Infer --> Persist[Database insert]
    Persist --> Response[Prediction response]
    Persist -. database error logged .-> Response

    Startup[API startup] --> Init[init_db schema initialization and migration]
    Init --> Load[Load and validate model artifacts]
    Load --> Ready[Healthy API]
```

Prediction logging is intentionally best-effort in the current implementation: a database logging exception is logged by the API and does not fail the prediction response. Database availability and schema migration should therefore be checked during startup and monitored through application logs.

## 10. Source-of-Truth Files

For expanded ERDs, table-level diagrams, column definitions, indexes, and migration details, see [database-schema.md](database-schema.md).

| Concern | File |
| --- | --- |
| API routes and model lifecycle | `backend/app.py` |
| Database connection, migrations, and queries | `backend/db.py` |
| Request and response schemas | `backend/schemas.py` |
| Authentication and JWT | `backend/auth.py` |
| PostgreSQL bootstrap schema | `backend/postgresql/init.sql` |
| Compose deployment | `backend/docker-compose.yml` |
| Frontend route tree | `Frontend/src/App.jsx` |
| Prediction UI | `Frontend/src/pages/Predict.jsx` |
| Agent workspace UI | `Frontend/src/pages/AgentWorkspace.jsx` |
| Admin monitoring UI | `Frontend/src/pages/Monitoring.jsx` |
| Admin account/session UI | `Frontend/src/pages/Agents.jsx` |
