# API Reference

Base URL: `http://localhost:8000` in local development. Docker exposes the service through Nginx at `http://localhost:8080`.

Interactive OpenAPI documentation is available at `/docs` when the API is running.

## Authentication

Protected routes use:

```http
Authorization: Bearer <access_token>
```

Roles:

| Role | Access |
| --- | --- |
| `agent` | Submit single and batch predictions; view own profile |
| `admin` | All prediction access plus agent management and monitoring |

## Common Input Schema

```json
{
  "ClientID": "optional-client-id",
  "LoanCount": 5,
  "AvgLoan": 1200.50,
  "TransactionFrequency": 45,
  "AverageTransactionValue": 350.75,
  "AuditActivity": 1,
  "Occupation": "Trader"
}
```

Validation rules: `LoanCount` is 0-100, numeric values are non-negative, loan and transaction values must not exceed 1,000,000, and `Occupation` is required and title-cased.

## Endpoint Summary

| Method | Route | Auth | Purpose |
| --- | --- | --- | --- |
| `GET` | `/` | Public | Health and model versions |
| `POST` | `/auth/register` | Public | Register an agent account |
| `POST` | `/auth/login` | Public | Return a JWT bearer token |
| `GET` | `/auth/me` | Bearer | Return current profile |
| `POST` | `/auth/change-password` | Bearer | Change current password |
| `POST` | `/auth/logout` | Bearer | Revoke current session |
| `GET` | `/admin/agents` | Admin | List agent accounts |
| `GET` | `/admin/users` | Admin | List all users |
| `PATCH` | `/admin/agents/{agent_id}` | Admin | Enable or disable an agent |
| `PATCH` | `/admin/agents/{agent_id}/password` | Admin | Reset agent password |
| `PATCH` | `/admin/users/{user_id}/role` | Admin | Change a user's role |
| `GET` | `/admin/sessions` | Admin | List login sessions |
| `PATCH` | `/admin/sessions/{session_id}/revoke` | Admin | Revoke a login session |
| `POST` | `/predict` | Agent/admin | Binary default prediction |
| `POST` | `/predict-risk-category` | Agent/admin | Multiclass risk prediction |
| `POST` | `/predict/batch` | Agent/admin | Up to 5,000 binary predictions |
| `POST` | `/predict-risk-category/batch` | Agent/admin | Up to 5,000 risk predictions |
| `POST` | `/admin/reload-models` | `X-API-Key` | Reload model files |
| `GET` | `/api/logs/summary` | Admin | Prediction totals and averages |
| `GET` | `/api/logs/recent` | Admin | Recent prediction rows |
| `GET` | `/api/logs/drift` | Admin | Feature drift report |
| `GET` | `/api/logs/drift-history` | Admin | Historical drift checks |
| `GET` | `/api/alerts` | Admin | Current monitoring alerts |
| `GET` | `/api/audit-events` | Admin | Administrator audit events |
| `GET` | `/api/model-deployments` | Admin | Model deployment history |
| `GET` | `/api/my-predictions` | Agent/admin | Current user's prediction history |
| `PATCH` | `/api/my-predictions/{prediction_id}/status` | Agent/admin | Update own follow-up status |

## Auth Endpoints

### `POST /auth/register`

JSON body:

```json
{"username":"agent01","password":"at-least-8-chars","full_name":"Agent One"}
```

Creates an active `agent`. Admin accounts are seeded from server configuration and cannot be self-registered. Returns `409` for a duplicate username and `422` for invalid input.

### `POST /auth/login`

Send OAuth2 form data, not JSON:

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=agent01&password=at-least-8-chars"
```

Returns `access_token`, `token_type`, `role`, and `username`. Invalid credentials return `401`; disabled accounts return `403`.

## Prediction Endpoints

### `POST /predict`

Returns:

```json
{
  "probability_of_default": 0.23,
  "predicted_default_flag": 0,
  "model_version": "a1b2c3d4"
}
```

### `POST /predict-risk-category`

Returns a category code, label, probability distribution, and model version:

```json
{
  "risk_category": "LOW RISK",
  "risk_category_code": 0,
  "risk_category_probabilities": {"LOW RISK": 0.8, "MEDIUM RISK": 0.15, "HIGH RISK": 0.04, "VERY HIGH RISK": 0.01},
  "model_version": "e5f6a7b8"
}
```

Risk codes are `0=LOW`, `1=MEDIUM`, `2=HIGH`, `3=VERY HIGH`.

### Batch routes

Batch body:

```json
{"customers": [{"LoanCount":5,"AvgLoan":1200.5,"TransactionFrequency":45,"AverageTransactionValue":350.75,"AuditActivity":1,"Occupation":"Trader"}]}
```

The list must contain 1-5,000 valid customers. Validation is all-or-nothing. Responses contain `count`, `model_version`, and `results`.

Batch routes remain available through the API, but batch scoring is not exposed in the current agent console.

## Agent Workspace

`GET /api/my-predictions` returns only predictions submitted by the authenticated user. The agent can update its follow-up status to `New`, `Under Review`, `Approved`, `Declined`, or `Needs More Information`.

The current agent console does not expose saved profiles, CSV batch scoring, search, or export.

## Monitoring Endpoints

- `/api/logs/summary` returns `total_predictions`, `by_risk_tier`, and `avg_default_probability`.
- `/api/logs/recent?limit=10` returns recent rows; `limit` is capped to 1,000 and defaults to 50.
- `/api/logs/drift?baseline_window=500` compares recent means with `models/metadata.json`; valid windows are 1-5,000.
- `/api/logs/drift` persists each check for `/api/logs/drift-history` and `/api/alerts`.
- `/api/model-deployments` lists model startup and reload events.

## Errors and Limits

| Status | Meaning |
| --- | --- |
| `401` | Missing, invalid, or expired bearer token; or bad admin API key |
| `403` | Valid user lacks the required role or account is disabled |
| `404` | User, route resource, or model metadata not found |
| `409` | Username already exists |
| `422` | Request validation failed |
| `429` | Rate limit exceeded |
| `500` | Model inference or server error |
| `503` | Admin model reload is disabled because `ADMIN_API_KEY` is missing |

Single prediction routes default to `60/minute` per client IP. Batch routes default to `10/minute`.
