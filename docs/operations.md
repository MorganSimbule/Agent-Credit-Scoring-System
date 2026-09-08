# Deployment and Operations Guide

## Local development

### Backend

```powershell
Set-Location backend
..\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item env.example .env
uvicorn app:app --reload --port 8000
```

The local fallback database is `backend/predictions.db` when `DATABASE_URL` is empty.

### Frontend

```powershell
Set-Location Frontend
npm install
npm run dev
```

Set `VITE_API_URL` when the API is not at the frontend default. Build and preview with:

```powershell
npm run build
npm run preview
```

## Docker deployment

From `backend/`:

```bash
docker compose up -d --build
docker compose ps
docker compose logs -f api
docker compose down
```

Compose runs Nginx, the API, and PostgreSQL. Nginx publishes port `8080`; the API listens on port `8000` inside the Compose network.

## Required configuration

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | PostgreSQL connection; empty means SQLite fallback |
| `PREDICTIONS_DB_PATH` | SQLite path when PostgreSQL is not used |
| `BINARY_MODEL_PATH` | Binary joblib artifact path |
| `MULTICLASS_MODEL_PATH` | Multiclass joblib artifact path |
| `ALLOWED_ORIGINS` | Comma-separated frontend origins |
| `ADMIN_API_KEY` | Key for model reload endpoint |
| `PREDICT_RATE_LIMIT` | Single prediction limit |
| `BATCH_RATE_LIMIT` | Batch prediction limit |
| `JWT_SECRET_KEY` | JWT signing secret; required by auth |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT lifetime |

Never commit `.env`, passwords, JWT secrets, or API keys.

## Health checks

```bash
curl http://localhost:8000/
```

A healthy response reports `status: ok`, `models_loaded: true`, and model versions.

## Backups

For SQLite, stop writes or stop the API and copy `backend/predictions.db` to protected storage. For PostgreSQL, use the standard `pg_dump` and `pg_restore` tools against the configured database.

## Logs and troubleshooting

The API logs request id, method, path, status, and latency. Search for:

- `Loading models` and `Models loaded successfully`
- `Failed to log prediction`
- `Failed to get logs summary`
- `Model reload failed`

If a prediction succeeds but no monitoring row appears, inspect database connectivity, schema columns, and the `Failed to log prediction` message.

## Upgrade procedure

1. Back up the database.
2. Replace code or model artifacts.
3. Install dependencies or rebuild the image.
4. Start the API and wait for the health check.
5. Confirm model versions.
6. Run an authenticated test prediction.
7. Verify the new row in admin monitoring.
8. Keep the previous model artifacts available for rollback.
