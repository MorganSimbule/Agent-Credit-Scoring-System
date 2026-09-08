import { useState } from "react";
import { Loader2 } from "lucide-react";
import { predictDefault, predictRiskCategory } from "../api/scoring";
import RiskBadge from "./RiskBadge";

const initialForm = {
  LoanCount: "",
  AvgLoan: "",
  TransactionFrequency: "",
  AverageTransactionValue: "",
  AuditActivity: "",
  Occupation: "Trader",
};

const FIELDS = [
  ["LoanCount", "Loan count", "0", "100"],
  ["AvgLoan", "Average loan amount", "0"],
  ["TransactionFrequency", "Transaction frequency", "0"],
  ["AverageTransactionValue", "Average transaction value", "0"],
  ["AuditActivity", "Audit activity", "0"],
];

export default function ScoreForm({ occupations = [] }) {
  const [form, setForm] = useState(initialForm);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const update = (event) => setForm({ ...form, [event.target.name]: event.target.value });

  async function submit(event) {
    event.preventDefault();
    setLoading(true);
    setError("");
    setResult(null);
    const payload = {
      ...form,
      LoanCount: Number(form.LoanCount),
      AvgLoan: Number(form.AvgLoan),
      TransactionFrequency: Number(form.TransactionFrequency),
      AverageTransactionValue: Number(form.AverageTransactionValue),
      AuditActivity: Number(form.AuditActivity),
    };

    try {
      const [defaultResult, riskResult] = await Promise.all([
        predictDefault(payload),
        predictRiskCategory(payload),
      ]);
      setResult({ ...defaultResult, ...riskResult });
    } catch (requestError) {
      const detail = requestError.response?.data?.detail;
      setError(
        Array.isArray(detail)
          ? detail.map((item) => item.msg).join(", ")
          : detail || "Could not reach the scoring API."
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 max-w-2xl">
      <form onSubmit={submit} className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {FIELDS.map(([name, label, min, max]) => (
          <label className="flex flex-col gap-1.5 text-left" key={name}>
            <span className="text-xs font-semibold uppercase tracking-wide text-gray-500">
              {label}
            </span>
            <input
              name={name}
              type="number"
              min={min}
              max={max}
              step={name.includes("Loan") || name.includes("Value") ? "0.01" : "1"}
              value={form[name]}
              onChange={update}
              required
              disabled={loading}
              className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#1a5c3a]/20 focus:border-[#1a5c3a] disabled:opacity-60 transition"
            />
          </label>
        ))}

        <label className="flex flex-col gap-1.5 text-left sm:col-span-2">
          <span className="text-xs font-semibold uppercase tracking-wide text-gray-500">
            Occupation
          </span>
          <input
            name="Occupation"
            list="occupations"
            value={form.Occupation}
            onChange={update}
            required
            disabled={loading}
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#1a5c3a]/20 focus:border-[#1a5c3a] disabled:opacity-60 transition"
          />
          <datalist id="occupations">
            {occupations.map((occupation) => (
              <option key={occupation} value={occupation} />
            ))}
          </datalist>
        </label>

        <button
          type="submit"
          disabled={loading}
          className="sm:col-span-2 flex items-center justify-center gap-2 bg-[#1a5c3a] hover:bg-[#144d2f] text-white font-semibold text-sm py-2.5 rounded-lg disabled:opacity-60 transition"
        >
          {loading && <Loader2 size={16} className="animate-spin" />}
          {loading ? "Scoring..." : "Score agent"}
        </button>
      </form>

      {error && (
        <div
          role="alert"
          aria-live="assertive"
          className="mt-4 p-3 bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg"
        >
          {error}
        </div>
      )}

      {result && (
        <div className="mt-6 pt-6 border-t border-gray-100 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-600">Risk category</span>
            <RiskBadge label={result.risk_category} />
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-600">Default probability</span>
            <strong className="text-sm text-gray-900">
              {(result.probability_of_default * 100).toFixed(1)}%
            </strong>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-600">Predicted default flag</span>
            <strong className="text-sm text-gray-900">{result.predicted_default_flag}</strong>
          </div>
          <div className="text-xs text-gray-400 pt-2">
            Model version: {result.model_version}
          </div>
        </div>
      )}
    </section>
  );
}
