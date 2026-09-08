# User Guide

## 1. Open the application

Start the backend and frontend, then open the frontend URL, normally `http://localhost:5173`.

## 2. Register as an agent

1. Select the registration option.
2. Enter a username of 3-50 characters.
3. Enter a password of 8-128 characters.
4. Optionally enter a full name.
5. Submit the form and sign in.

Self-registration creates an `agent` account. Only administrators can manage account status.

## 3. Run a prediction

1. Open **Score Agent**.
2. Optionally enter a client identifier.
3. Enter loan count, average loan, transaction frequency, average transaction value, and audit activity.
4. Enter an occupation such as `Trader`, `Farmer`, `Vendor`, or `Driver`.
5. Select **Run Prediction**.

The application sends the input to both scoring models and displays:

- Default probability
- Predicted default flag
- Risk category
- Risk-category probabilities
- Model versions used

A single form submission creates two audit records, one for each model endpoint.

## 4. Interpret the result

The binary result estimates default probability and returns a `0` or `1` flag. The multiclass result assigns one of four categories:

| Category | Meaning |
| --- | --- |
| `LOW RISK` | Lowest predicted risk tier |
| `MEDIUM RISK` | Intermediate predicted risk |
| `HIGH RISK` | Elevated predicted risk |
| `VERY HIGH RISK` | Highest predicted risk tier |

These outputs are model predictions, not a replacement for institutional credit policy or human review.

## 5. My Workspace

Open **My Workspace** to review your own prediction history. You can filter by risk category, open a prediction for full details, set a follow-up status, and read risk guidance. High-risk results produce a follow-up notification.

The workspace supports the statuses `New`, `Under Review`, `Approved`, `Declined`, and `Needs More Information`.

The current agent console intentionally does not include saved client profiles, batch scoring, search, or export. Change your password from the console header and use **Sign Out** to revoke the current session.

## 6. Common problems

| Symptom | Action |
| --- | --- |
| Login rejected | Check username/password and whether an admin disabled the account |
| Prediction returns `422` | Check required fields, non-negative numbers, and occupation text |
| Prediction returns `401` | Sign in again; the bearer token may be expired |
| Models unavailable | Ask the administrator to check backend startup logs and model files |
| Result appears but monitoring is unchanged | Ask the administrator to inspect database connection and schema migration logs |
