"""
Test suite for the Credit Scoring API.

Run from the backend/ folder with:
    pytest

Notes:
- Validator tests run with no dependencies beyond pydantic — they don't
  need the .joblib model files and always run.
- Endpoint tests spin up the full app via TestClient, which triggers the
  lifespan handler and therefore DOES need models/*.joblib to be present
  at the paths configured in .env (or the defaults in app.py). If the
  model files aren't found, these tests will fail at the TestClient
  fixture step rather than silently skipping — that's intentional, since
  a missing model file is itself something worth catching in CI.
"""
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app import CustomerRequest, app

VALID_CUSTOMER = {
    "LoanCount": 5,
    "AvgLoan": 1200.50,
    "TransactionFrequency": 45,
    "AverageTransactionValue": 350.75,
    "AuditActivity": 1,
    "Occupation": "Trader",
}


# ------------------------------------------------------------------
# Validator tests — no model loading required
# ------------------------------------------------------------------
class TestCustomerRequestValidation:
    def test_valid_payload_accepted(self):
        customer = CustomerRequest(**VALID_CUSTOMER)
        assert customer.LoanCount == 5
        assert customer.Occupation == "Trader"

    def test_negative_loan_count_rejected(self):
        payload = {**VALID_CUSTOMER, "LoanCount": -5}
        with pytest.raises(ValidationError):
            CustomerRequest(**payload)

    def test_loan_count_over_max_rejected(self):
        payload = {**VALID_CUSTOMER, "LoanCount": 101}
        with pytest.raises(ValidationError):
            CustomerRequest(**payload)

    def test_blank_occupation_rejected(self):
        payload = {**VALID_CUSTOMER, "Occupation": "   "}
        with pytest.raises(ValidationError):
            CustomerRequest(**payload)

    def test_occupation_is_title_cased(self):
        payload = {**VALID_CUSTOMER, "Occupation": "farmer"}
        customer = CustomerRequest(**payload)
        assert customer.Occupation == "Farmer"

    def test_unreasonably_large_avg_loan_rejected(self):
        payload = {**VALID_CUSTOMER, "AvgLoan": 5_000_000}
        with pytest.raises(ValidationError):
            CustomerRequest(**payload)

    def test_negative_avg_loan_rejected(self):
        payload = {**VALID_CUSTOMER, "AvgLoan": -100}
        with pytest.raises(ValidationError):
            CustomerRequest(**payload)


# ------------------------------------------------------------------
# Endpoint tests — require model files to be present
# ------------------------------------------------------------------
@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


class TestHealthCheck:
    def test_health_check_reports_models_loaded(self, client):
        response = client.get("/")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert body["models_loaded"] is True


class TestPredictEndpoint:
    def test_valid_request_returns_prediction(self, client):
        response = client.post("/predict", json=VALID_CUSTOMER)
        assert response.status_code == 200
        body = response.json()
        assert "probability_of_default" in body
        assert body["predicted_default_flag"] in (0, 1)
        assert "model_version" in body

    def test_invalid_request_returns_422(self, client):
        payload = {**VALID_CUSTOMER, "LoanCount": -5}
        response = client.post("/predict", json=payload)
        assert response.status_code == 422

    def test_client_id_is_preserved_in_recent_logs(self, client):
        payload = {**VALID_CUSTOMER, "ClientID": "client-regression-test"}
        response = client.post("/predict", json=payload)
        assert response.status_code == 200

        recent = client.get("/api/logs/recent?limit=1")
        assert recent.status_code == 200
        assert recent.json()["predictions"][0]["client_id"] == "client-regression-test"


class TestPredictRiskCategoryEndpoint:
    def test_valid_request_returns_risk_category(self, client):
        response = client.post("/predict-risk-category", json=VALID_CUSTOMER)
        assert response.status_code == 200
        body = response.json()
        assert body["risk_category_code"] in (0, 1, 2, 3)
        probs = body["risk_category_probabilities"]
        assert abs(sum(probs.values()) - 1.0) < 1e-6

    def test_invalid_request_returns_422(self, client):
        payload = {**VALID_CUSTOMER, "Occupation": ""}
        response = client.post("/predict-risk-category", json=payload)
        assert response.status_code == 422


class TestBatchEndpoints:
    def test_batch_predict_returns_one_result_per_customer(self, client):
        payload = {"customers": [VALID_CUSTOMER, VALID_CUSTOMER, VALID_CUSTOMER]}
        response = client.post("/predict/batch", json=payload)
        assert response.status_code == 200
        body = response.json()
        assert body["count"] == 3
        assert len(body["results"]) == 3

    def test_batch_risk_category_returns_one_result_per_customer(self, client):
        payload = {"customers": [VALID_CUSTOMER, VALID_CUSTOMER]}
        response = client.post("/predict-risk-category/batch", json=payload)
        assert response.status_code == 200
        assert response.json()["count"] == 2

    def test_one_invalid_customer_rejects_whole_batch(self, client):
        bad_customer = {**VALID_CUSTOMER, "LoanCount": -5}
        payload = {"customers": [VALID_CUSTOMER, bad_customer]}
        response = client.post("/predict-risk-category/batch", json=payload)
        assert response.status_code == 422

    def test_empty_batch_rejected(self, client):
        response = client.post("/predict-risk-category/batch", json={"customers": []})
        assert response.status_code == 422


class TestAdminReload:
    def test_reload_without_api_key_rejected(self, client):
        response = client.post("/admin/reload-models")
        assert response.status_code in (401, 503)

    def test_reload_with_wrong_api_key_rejected(self, client):
        response = client.post("/admin/reload-models", headers={"X-API-Key": "wrong-key"})
        assert response.status_code in (401, 503)


class TestMonitoringEndpoints:
    def test_drift_reports_actual_sample_size(self, client):
        response = client.get("/api/logs/drift?baseline_window=1")
        assert response.status_code == 200
        assert response.json()["sample_size"] == 1

    def test_drift_window_is_bounded(self, client):
        response = client.get("/api/logs/drift?baseline_window=0")
        assert response.status_code == 422


def test_compatibility_entrypoint_exports_active_app():
    from main import app as compatibility_app

    assert compatibility_app is app
