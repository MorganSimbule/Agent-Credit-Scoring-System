import { useEffect, useState } from "react";
import { Loader2, AlertTriangle } from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { api } from "../api.js";
import RiskBadge from "./RiskBadge";

const TIER_COLORS = {
  "LOW RISK": "#16a34a",
  "MEDIUM RISK": "#ca8a04",
  "HIGH RISK": "#ea580c",
  "VERY HIGH RISK": "#dc2626",
};

const TIER_ORDER = ["LOW RISK", "MEDIUM RISK", "HIGH RISK", "VERY HIGH RISK"];

export default function Dashboard() {
  const [summary, setSummary] = useState(null);
  const [recent, setRecent] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError("");
      try {
        const [summaryData, recentData] = await Promise.all([api.summary(), api.recent(10)]);
        if (!cancelled) {
          setSummary(summaryData);
          setRecent(recentData.predictions || []);
        }
      } catch (err) {
        if (!cancelled) {
          setError("Could not load monitoring data from the API.");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, []);

  const chartData = TIER_ORDER.map((tier) => ({
    tier,
    count: summary?.by_risk_tier?.[tier] || 0,
  }));

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-gray-500 text-sm py-12 justify-center">
        <Loader2 size={18} className="animate-spin" />
        Loading dashboard...
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center gap-2 bg-amber-50 border border-amber-200 text-amber-800 text-sm rounded-lg px-4 py-3">
        <AlertTriangle size={16} />
        {error}
      </div>
    );
  }

  const hasData = summary && summary.total_predictions > 0;

  return (
    <div className="space-y-6">
      {/* Summary stat cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
          <div className="text-xs font-semibold uppercase tracking-wide text-gray-500 mb-1">
            Total Predictions Logged
          </div>
          <div className="text-2xl font-bold text-gray-900">{summary.total_predictions}</div>
        </div>
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
          <div className="text-xs font-semibold uppercase tracking-wide text-gray-500 mb-1">
            Avg Default Probability
          </div>
          <div className="text-2xl font-bold text-gray-900">
            {summary.avg_default_probability != null
              ? `${(summary.avg_default_probability * 100).toFixed(1)}%`
              : "—"}
          </div>
        </div>
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
          <div className="text-xs font-semibold uppercase tracking-wide text-gray-500 mb-1">
            Highest Risk Tier
          </div>
          <div className="text-2xl font-bold text-gray-900">
            {hasData
              ? TIER_ORDER.filter((t) => summary.by_risk_tier?.[t] > 0).slice(-1)[0] || "—"
              : "—"}
          </div>
        </div>
      </div>

      {/* Risk tier distribution chart */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <h2 className="text-sm font-semibold text-gray-700 mb-4">Risk Tier Distribution</h2>
        {hasData ? (
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis dataKey="tier" tick={{ fontSize: 11 }} interval={0} angle={-15} textAnchor="end" height={60} />
              <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
              <Tooltip />
              <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                {chartData.map((entry) => (
                  <Bar key={entry.tier} dataKey="count" fill={TIER_COLORS[entry.tier]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <p className="text-sm text-gray-400 text-center py-10">
            No predictions logged yet. Score an agent to see data here.
          </p>
        )}
      </div>

      {/* Recent predictions table */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <h2 className="text-sm font-semibold text-gray-700 mb-4">Recent Predictions</h2>
        {recent.length === 0 ? (
          <p className="text-sm text-gray-400 text-center py-10">No recent predictions.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs font-semibold uppercase tracking-wide text-gray-500 border-b border-gray-100">
                  <th className="pb-2 pr-4">Timestamp</th>
                  <th className="pb-2 pr-4">Source</th>
                  <th className="pb-2 pr-4">Occupation</th>
                  <th className="pb-2 pr-4">Default Prob.</th>
                  <th className="pb-2">Risk Tier</th>
                </tr>
              </thead>
              <tbody>
                {recent.map((row) => (
                  <tr key={row.id} className="border-b border-gray-50 last:border-0">
                    <td className="py-2.5 pr-4 text-gray-500 whitespace-nowrap">
                      {new Date(row.timestamp).toLocaleString()}
                    </td>
                    <td className="py-2.5 pr-4 text-gray-600 capitalize">{row.source}</td>
                    <td className="py-2.5 pr-4 text-gray-600">{row.occupation || "—"}</td>
                    <td className="py-2.5 pr-4 text-gray-900">
                      {row.default_probability != null
                        ? `${(row.default_probability * 100).toFixed(1)}%`
                        : "—"}
                    </td>
                    <td className="py-2.5">
                      {row.risk_label ? <RiskBadge label={row.risk_label} /> : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
