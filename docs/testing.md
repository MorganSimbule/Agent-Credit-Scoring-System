# Testing Guide

## Backend tests

The backend tests live in `backend/tests/test_app.py` and cover validation, health, single prediction, batch prediction, monitoring, model reload authorization, and compatibility imports.

Run them from the backend directory with the project environment active:

```powershell
Set-Location backend
..\.venv\Scripts\python.exe -m pytest -q tests/test_app.py
```

The endpoint tests load both joblib files during the FastAPI lifespan. Missing model artifacts cause collection or fixture startup failures and should not be silently ignored.

## Frontend checks

From `Frontend/`:

```powershell
npm run lint
npm run build
```

`npm run dev` starts the Vite development server for manual verification.

## Test layers

| Layer | What it checks |
| --- | --- |
| Pydantic validation | Numeric bounds, blank occupations, normalization, large-value rejection |
| Health | API starts and reports both models loaded |
| Prediction endpoints | Response fields and class/probability outputs |
| Batch endpoints | Counts, result lengths, and all-or-nothing validation |
| Monitoring | Drift window validation, recent logging, charts, alerts, and drift history |
| Agent workspace | Own-history access, follow-up statuses, high-risk notifications, and detail view |
| Governance | Password changes, session revocation, role changes, audit events, and deployment history |
| Frontend build/lint | JSX compilation and static lint rules |
| Manual smoke test | Login, prediction, admin monitoring, and agent status workflow |

## Manual smoke test

1. Start the API and frontend.
2. Confirm `GET /` reports `models_loaded: true`.
3. Register an agent and sign in.
4. Submit a valid prediction.
5. Confirm both result panels render.
6. Sign in as an admin.
7. Open Monitoring and verify the prediction rows appear.
8. Open agent management and toggle an agent status.
9. Open My Workspace as an agent and confirm only that agent's history is visible.
10. Run the frontend build before release.

## Known test limitation

The current endpoint test file posts to protected routes without authentication, so those tests may return `401` against the current secured application. Production behavior should remain protected. To make endpoint tests fully representative, add a fixture that creates or seeds a test user and sends a valid JWT before calling agent/admin routes.

## Regression priorities

When changing prediction or persistence code, run:

1. Validation tests.
2. Authenticated single prediction test.
3. Authenticated monitoring recent-log test.
4. Database migration test against an older schema.
5. Frontend lint and build.

The agent workspace intentionally has no saved-profile, batch-scoring, search, or export UI; include those omissions in visual smoke checks.
