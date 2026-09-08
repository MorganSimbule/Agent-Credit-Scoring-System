import React, { useState } from "react";
import { Loader2, BrainCircuit, AlertTriangle, CheckCircle2, ShieldAlert } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import styles from "./Predict.module.css";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

const initialForm = {
  ClientID: "",
  LoanCount: "",
  AvgLoan: "",
  TransactionFrequency: "",
  AverageTransactionValue: "",
  AuditActivity: "",
  Occupation: "",
};

const riskColors = {
  "LOW RISK": "#16a34a",
  "MEDIUM RISK": "#f59e0b",
  "HIGH RISK": "#ea580c",
  "VERY HIGH RISK": "#dc2626",
};

const riskBg = {
  "LOW RISK": "#dcfce7",
  "MEDIUM RISK": "#fef9c3",
  "HIGH RISK": "#ffedd5",
  "VERY HIGH RISK": "#fee2e2",
};

export default function Predict() {
  const { token } = useAuth();
  const [form, setForm] = useState(initialForm);
  const [loading, setLoading] = useState(false);
  const [binaryResult, setBinaryResult] = useState(null);
  const [riskResult, setRiskResult] = useState(null);
  const [error, setError] = useState(null);

  const update = (field) => (e) => {
    setForm({ ...form, [field]: e.target.value });
    setBinaryResult(null);
    setRiskResult(null);
    setError(null);
  };

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setBinaryResult(null);
    setRiskResult(null);

    const clientId = form.ClientID.trim() || undefined;

    const payload = {
      // Sending both casings until the backend's field name is confirmed —
      // the logged rows were coming back with client_id always null even
      // when this was filled in, so this covers whichever key the API
      // actually reads.
      ClientID: clientId,
      client_id: clientId,
      LoanCount: Number(form.LoanCount),
      AvgLoan: Number(form.AvgLoan),
      TransactionFrequency: Number(form.TransactionFrequency),
      AverageTransactionValue: Number(form.AverageTransactionValue),
      AuditActivity: Number(form.AuditActivity),
      Occupation: form.Occupation,
    };

    try {
      const [binaryRes, riskRes] = await Promise.all([
        fetch(`${API_URL}/predict`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify(payload),
        }),
        fetch(`${API_URL}/predict-risk-category`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify(payload),
        }),
      ]);

      if (!binaryRes.ok) {
        const err = await binaryRes.json();
        throw new Error(err.detail || "Binary prediction failed");
      }
      if (!riskRes.ok) {
        const err = await riskRes.json();
        throw new Error(err.detail || "Risk category prediction failed");
      }

      const binaryData = await binaryRes.json();
      const riskData = await riskRes.json();

      setBinaryResult(binaryData);
      setRiskResult(riskData);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const defaultRiskColor = (prob) => {
    if (prob < 0.3) return "#16a34a";
    if (prob < 0.6) return "#f59e0b";
    return "#dc2626";
  };

  return (
    <div className={styles.page}>
      <div className={styles.formCard}>
        <div className={styles.cardHeader}>
          <BrainCircuit size={22} />
          <h3>Score an Agent</h3>
        </div>

        <form onSubmit={submit} className={styles.form}>
          <div className={styles.grid}>
            <label className={styles.field}>
              <span>Client ID</span>
              <input type="text" value={form.ClientID} onChange={update("ClientID")} placeholder="Optional" />
            </label>

            <label className={styles.field}>
              <span>Loan Count *</span>
              <input type="number" min="0" max="100" value={form.LoanCount} onChange={update("LoanCount")} placeholder="0-100" required />
            </label>

            <label className={styles.field}>
              <span>Avg Loan (ZMW) *</span>
              <input type="number" min="0" step="0.01" value={form.AvgLoan} onChange={update("AvgLoan")} placeholder="e.g. 2500" required />
            </label>

            <label className={styles.field}>
              <span>Transaction Freq *</span>
              <input type="number" min="0" value={form.TransactionFrequency} onChange={update("TransactionFrequency")} placeholder="Monthly count" required />
            </label>

            <label className={styles.field}>
              <span>Avg Transaction (ZMW) *</span>
              <input type="number" min="0" step="0.01" value={form.AverageTransactionValue} onChange={update("AverageTransactionValue")} placeholder="e.g. 150" required />
            </label>

            <label className={styles.field}>
              <span>Audit Activity *</span>
              <input type="number" min="0" value={form.AuditActivity} onChange={update("AuditActivity")} placeholder="Log events" required />
            </label>

            <label className={`${styles.field} ${styles.fullWidth}`}>
              <span>Occupation *</span>
              <input
                type="text"
                value={form.Occupation}
                onChange={update("Occupation")}
                placeholder="e.g. Trader, Farmer, Vendor, Driver"
                required
              />
            </label>
          </div>

          <button type="submit" className={styles.submitBtn} disabled={loading}>
            {loading ? <Loader2 size={16} className={styles.spin} /> : <BrainCircuit size={16} />}
            {loading ? "Scoring…" : "Run Prediction"}
          </button>
        </form>

        {error && (
          <div className={styles.errorBox}>
            <AlertTriangle size={16} />
            <span>{error}</span>
          </div>
        )}
      </div>

      {(binaryResult || riskResult) && (
        <div className={styles.resultsWrap}>
          {/* Binary Result */}
          {binaryResult && (
            <div className={styles.resultCard}>
              <div className={styles.resultHeader}>
                <CheckCircle2 size={20} color="#16a34a" />
                <h4>Default Risk Assessment</h4>
              </div>

              <div className={styles.resultGrid}>
                <div className={styles.resultItem}>
                  <span className={styles.resultLabel}>Default Probability</span>
                  <span className={styles.resultValue} style={{ color: defaultRiskColor(binaryResult.probability_of_default) }}>
                    {(binaryResult.probability_of_default * 100).toFixed(2)}%
                  </span>
                </div>
                <div className={styles.resultItem}>
                  <span className={styles.resultLabel}>Predicted Flag</span>
                  <span className={`${styles.badge} ${binaryResult.predicted_default_flag ? styles.danger : styles.safe}`}>
                    {binaryResult.predicted_default_flag ? "DEFAULT RISK" : "NO DEFAULT"}
                  </span>
                </div>
                <div className={styles.resultItem}>
                  <span className={styles.resultLabel}>Model Version</span>
                  <span className={styles.meta}>{binaryResult.model_version}</span>
                </div>
              </div>
            </div>
          )}

          {/* Risk Category Result */}
          {riskResult && (
            <div className={styles.resultCard}>
              <div className={styles.resultHeader}>
                <ShieldAlert size={20} color={riskColors[riskResult.risk_category] || "#64748b"} />
                <h4>Risk Category Classification</h4>
              </div>

              <div className={styles.categoryWrap}>
                <div
                  className={styles.categoryBadge}
                  style={{
                    background: riskBg[riskResult.risk_category],
                    color: riskColors[riskResult.risk_category],
                  }}
                >
                  {riskResult.risk_category}
                </div>
                <span className={styles.categoryCode}>Code: {riskResult.risk_category_code}</span>
              </div>

              <div className={styles.probBars}>
                {Object.entries(riskResult.risk_category_probabilities)
                  .sort((a, b) => b[1] - a[1])
                  .map(([label, prob]) => (
                    <div key={label} className={styles.probRow}>
                      <span className={styles.probLabel}>{label}</span>
                      <div className={styles.probTrack}>
                        <div
                          className={styles.probFill}
                          style={{
                            width: `${(prob * 100).toFixed(1)}%`,
                            background: riskColors[label] || "#cbd5e1",
                          }}
                        />
                      </div>
                      <span className={styles.probValue}>{(prob * 100).toFixed(1)}%</span>
                    </div>
                  ))}
              </div>

              <div className={styles.resultFooter}>
                <span className={styles.meta}>Model: {riskResult.model_version}</span>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
