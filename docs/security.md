# Security Documentation

## Authentication

The API uses JWT bearer tokens signed with `JWT_SECRET_KEY`. Tokens contain the user id, username, role, and expiry. Issued tokens are hashed in the `sessions` table and checked on protected requests; logout and admin actions can revoke them.

`JWT_SECRET_KEY` must be a long random secret and must not be committed to source control.

## Authorization

| Resource | Agent | Admin |
| --- | ---: | ---: |
| Register as agent | Public | Public endpoint, creates agent only |
| Sign in/profile | Yes | Yes |
| Submit predictions | Yes | Yes |
| Manage agent accounts | No | Yes |
| View monitoring data | No | Yes |
| Reload models | API key | API key |

The model reload route uses a separate `X-API-Key` check through `ADMIN_API_KEY`.

The role-management UI supports `agent`, `admin`, `analyst`, and `auditor`. Additional roles are stored and audited, but route access should be explicitly expanded before using them in production.

## Passwords and secrets

Passwords are stored as bcrypt hashes. Do not log passwords, access tokens, database URLs, or API keys. Keep `.env` files outside version control and use a secret manager in production.

## Network controls

- Configure `ALLOWED_ORIGINS` to the actual frontend origins.
- Put the API behind Nginx or another TLS-terminating reverse proxy in production.
- Restrict PostgreSQL so it is reachable only from the API network.
- Use non-default database credentials and rotate them periodically.
- Keep the model reload API key separate from the JWT secret.

## Input and abuse controls

Pydantic validates ranges, required fields, occupation length, and batch size. Slowapi applies per-client-IP limits: `60/minute` for single prediction routes and `10/minute` for batch routes.

These controls do not replace request-body size limits, TLS, firewall rules, monitoring, or a WAF where appropriate.

## Data protection

Prediction rows contain agent activity features and optional client identifiers. Treat the database and backups as sensitive. Limit admin access, encrypt backups, define retention rules, and avoid putting client identifiers in logs or screenshots.

## Security review checklist

- [ ] `JWT_SECRET_KEY` is configured with a random production value.
- [ ] `ADMIN_API_KEY` is configured and not the example value.
- [ ] Admin credentials are not stored in source control.
- [ ] `ALLOWED_ORIGINS` contains only trusted origins.
- [ ] API and database traffic use protected networks/TLS where required.
- [ ] Database backups are encrypted and access-controlled.
- [ ] Disabled users cannot obtain new tokens.
- [ ] Session revocation is tested for user logout and admin revocation.
- [ ] Role changes are audited.
- [ ] Dependencies are patched and audited regularly.
