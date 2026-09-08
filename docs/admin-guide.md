# Administrator Guide

## Administrator responsibilities

Administrators manage agent access, monitor prediction traffic, review drift signals, and control model reloads. Admin accounts are seeded at API startup from server environment configuration.

## Sign in

Use the configured admin username and password. The exact environment variable names should be confirmed in the deployment configuration before production use.

## Manage agents

Open the admin console and use the agent management view to:

- List registered agent accounts.
- Review role and active status.
- Enable or disable an agent.
- Reset an agent password.
- Change user roles between `agent`, `admin`, `analyst`, and `auditor`.
- Review and revoke login sessions.

Disabling an account blocks new logins. Existing JWTs expire naturally according to `ACCESS_TOKEN_EXPIRE_MINUTES`.

## Monitor predictions

The Monitoring page displays:

- Total logged prediction rows.
- Average default probability.
- Drift detected status.
- Recent prediction rows with timestamp, client id, risk, probability, and source.
- Prediction trend charts.
- Drift history and current alerts.
- Model deployment history.
- Administrator audit events.

Prediction rows can be searched, filtered, opened for full detail, and reviewed without exporting them from the UI.

Because one UI submission calls two model endpoints, the database normally receives two complementary rows.

## Review drift

The drift endpoint compares recent feature means with the training baseline in `backend/models/metadata.json`. A feature is flagged when its absolute z-score is greater than 2.

Treat drift as an investigation signal. Check data quality, traffic changes, and model age before retraining.
Each drift check is stored in `drift_history`; `/api/alerts` reports a warning when the latest check detects drift.

## Reload models

`POST /admin/reload-models` requires the configured `X-API-Key` header:

```bash
curl -X POST http://localhost:8000/admin/reload-models \
  -H "X-API-Key: $ADMIN_API_KEY"
```

Use this after replacing both joblib artifacts. Confirm the returned model versions and check the API logs for load errors.
Startup and reload events are stored in `model_deployments`.

## Password and session administration

Administrators can change their own password from the console header. The account page lists login sessions and allows administrators to revoke them. Passwords are stored only as bcrypt hashes.

## Database checks

The API initializes the database during startup. It creates missing tables and adds missing prediction attribution columns without deleting existing rows. For local SQLite:

```powershell
Set-Location backend
..\.venv\Scripts\python.exe -c "import sqlite3; c=sqlite3.connect('predictions.db'); print(c.execute('SELECT COUNT(1) FROM predictions').fetchone()[0]); c.close()"
```

For Docker, use PostgreSQL rather than inspecting the local SQLite file.

## Incident checklist

1. Check `GET /` and confirm `models_loaded` is true.
2. Check API process logs for database or model exceptions.
3. Confirm `DATABASE_URL` points to the intended database.
4. Confirm the schema contains `users`, `predictions`, `audit_events`, `drift_history`, `model_deployments`, and `sessions`.
5. Confirm the admin token has the `admin` role.
6. Re-run a controlled prediction and check `/api/logs/recent` and the submitting agent's `/api/my-predictions` response.
