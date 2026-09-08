import { useState } from "react";
import { predictDefault, predictRiskCategory } from "../api/scoring";
import RiskBadge from "../components/RiskBadge";

const initialForm = {
  LoanCount: "",
  AvgLoan: "",
  TransactionFrequency: "",
  AverageTransactionValue: "",
  AuditActivity: "",
  Occupation: "",
};

export default function ScoringForm() {
  const [form, setForm] = useState(initialForm);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  function handleChange(e) {
    setForm({ ...form, [e.target.name]: e.target.value });
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);

    const payload = {
      LoanCount: Number(form.LoanCount),
      AvgLoan: Number(form.AvgLoan),
      TransactionFrequency: Number(form.TransactionFrequency),
      AverageTransactionValue: Number(form.AverageTransactionValue),
      AuditActivity: Number(form.AuditActivity),
      Occupation: form.Occupation,
    };

    try {
      const [defaultResult, riskResult] = await Promise.all([
        predictDefault(payload),
        predictRiskCategory(payload),
      ]);
      setResult({ ...defaultResult, ...riskResult });
    } catch (err) {
      const detail = err.response?.data?.detail;
      setError(Array.isArray(detail) ? detail.map(d => d.msg).join(", ") : detail || "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-xl mx-auto p-6">
      <h1 className="text-2xl font-bold mb-6 text-gray-800">Score an Agent</h1>

      <form onSubmit={handleSubmit} className="space-y-4 bg-white p-6 rounded-lg shadow">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Loan Count</label>
          <input
            type="number" name="LoanCount" value={form.LoanCount} onChange={handleChange}
            required min="0" max="100"
            className="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:outline-none"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Average Loan Amount</label>
          <input
            type="number" name="AvgLoan" value={form.AvgLoan} onChange={handleChange}
            required min="0" step="0.01"
            className="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:outline-none"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Transaction Frequency</label>
          <input
            type="number" name="TransactionFrequency" value={form.TransactionFrequency} onChange={handleChange}
            required min="0"
            className="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:outline-none"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Average Transaction Value</label>
          <input
            type="number" name="AverageTransactionValue" value={form.AverageTransactionValue} onChange={handleChange}
            required min="0" step="0.01"
            className="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:outline-none"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Audit Activity</label>
          <input
            type="number" name="AuditActivity" value={form.AuditActivity} onChange={handleChange}
            required min="0"
            className="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:outline-none"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Occupation</label>
          <input
            type="text" name="Occupation" value={form.Occupation} onChange={handleChange}
            required placeholder="e.g. Trader, Farmer, Vendor, Driver"
            className="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:outline-none"
          />
        </div>

        <button
          type="submit" disabled={loading}
          className="w-full bg-blue-600 text-white font-semibold py-2 rounded-md hover:bg-blue-700 disabled:opacity-50 transition"
        >
          {loading ? "Scoring..." : "Score Agent"}
        </button>
      </form>

      {error && (
        <div className="mt-4 p-4 bg-red-50 border border-red-200 text-red-700 rounded-md">
          {error}
        </div>
      )}

      {result && (
        <div className="mt-6 bg-white p-6 rounded-lg shadow space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-gray-600">Risk Category</span>
            <RiskBadge label={result.risk_category} />
          </div>
          <div className="flex items-center justify-between">
            <span className="text-gray-600">Default Probability</span>
            <span className="font-semibold text-gray-800">
              {(result.probability_of_default * 100).toFixed(1)}%
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-gray-600">Predicted Default Flag</span>
            <span className="font-semibold text-gray-800">{result.predicted_default_flag}</span>
          </div>
          <div className="text-xs text-gray-400 pt-2 border-t">
            Model version: {result.model_version}
          </div>
        </div>
      )}
    </div>
  );
}