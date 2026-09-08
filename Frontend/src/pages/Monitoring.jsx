import React, { useEffect, useState } from "react";
import {
  BarChart3,
  AlertTriangle,
  Activity,
  TrendingUp,
  Clock,
  Loader2,
  Search,
  X,
} from "lucide-react";
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { useAuth } from "../context/AuthContext";
import styles from "./Monitoring.module.css";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function Monitoring() {
  const { token } = useAuth();
  const [summary, setSummary] = useState(null);
  const [recent, setRecent] = useState([]);
  const [drift, setDrift] = useState(null);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");
  const [riskFilter, setRiskFilter] = useState("");
  const [selectedPrediction, setSelectedPrediction] = useState(null);
  const [auditEvents, setAuditEvents] = useState([]);
  const [driftHistory, setDriftHistory] = useState([]);
  const [deployments, setDeployments] = useState([]);
  const [alerts, setAlerts] = useState([]);

  useEffect(() => {
    fetchAll();
  }, []);

  const fetchAll = async () => {
    setLoading(true);
    try {
      const [sumRes, recRes, driftRes, auditRes, historyRes, deploymentRes, alertRes] = await Promise.all([
        fetch(`${API_URL}/api/logs/summary`, { headers: { Authorization: `Bearer ${token}` } }),
        fetch(`${API_URL}/api/logs/recent?limit=1000`, { headers: { Authorization: `Bearer ${token}` } }),
        fetch(`${API_URL}/api/logs/drift`, { headers: { Authorization: `Bearer ${token}` } }),
        fetch(`${API_URL}/api/audit-events?limit=25`, { headers: { Authorization: `Bearer ${token}` } }),
        fetch(`${API_URL}/api/logs/drift-history?limit=20`, { headers: { Authorization: `Bearer ${token}` } }),
        fetch(`${API_URL}/api/model-deployments`, { headers: { Authorization: `Bearer ${token}` } }),
        fetch(`${API_URL}/api/alerts`, { headers: { Authorization: `Bearer ${token}` } }),
      ]);

      if (sumRes.ok) setSummary(await sumRes.json());
      if (recRes.ok) setRecent((await recRes.json()).predictions);
      if (driftRes.ok) setDrift(await driftRes.json());
      if (auditRes.ok) setAuditEvents((await auditRes.json()).events);
      if (historyRes.ok) setDriftHistory((await historyRes.json()).history);
      if (deploymentRes.ok) setDeployments((await deploymentRes.json()).deployments);
      if (alertRes.ok) setAlerts((await alertRes.json()).alerts);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const trendData = Object.values(recent.reduce((groups, row) => {
    const day = new Date(row.timestamp).toLocaleDateString();
    groups[day] ||= { day, predictions: 0, highRisk: 0 };
    groups[day].predictions += 1;
    if (["HIGH RISK", "VERY HIGH RISK"].includes(row.risk_label)) groups[day].highRisk += 1;
    return groups;
  }, {})).reverse();

  const filteredRecent = recent.filter((row) => {
    const searchText = query.trim().toLowerCase();
    const matchesQuery = !searchText || [row.client_id, row.occupation, row.submitted_by_username, row.source]
      .some((value) => String(value || "").toLowerCase().includes(searchText));
    return matchesQuery && (!riskFilter || row.risk_label === riskFilter);
  });

  if (loading) {
    return (
      <div className={styles.loading}>
        <Loader2 size={28} className={styles.spin} />
        <span>Loading monitoring data…</span>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      {/* Stats */}
      <div className={styles.statsGrid}>
        <div className={styles.statCard}>
          <div className={styles.statIcon} style={{ background: "#1a5c3a15", color: "#1a5c3a" }}>
            <Activity size={22} />
          </div>
          <div>
            <span className={styles.statValue}>{summary?.total_predictions || 0}</span>
            <span className={styles.statLabel}>Total Predictions</span>
          </div>
        </div>
        <div className={styles.statCard}>
          <div className={styles.statIcon} style={{ background: "#f59e0b15", color: "#f59e0b" }}>
            <TrendingUp size={22} />
          </div>
          <div>
            <span className={styles.statValue}>
              {summary?.avg_default_probability
                ? (summary.avg_default_probability * 100).toFixed(1) + "%"
                : "—"}
            </span>
            <span className={styles.statLabel}>Avg Default Prob</span>
          </div>
        </div>
        <div className={styles.statCard}>
          <div className={styles.statIcon} style={{ background: "#d6282815", color: "#d62828" }}>
            <AlertTriangle size={22} />
          </div>
          <div>
            <span className={styles.statValue}>{drift?.any_drift_detected ? "YES" : "NO"}</span>
            <span className={styles.statLabel}>Drift Detected</span>
          </div>
        </div>
        <div className={styles.statCard}>
          <div className={styles.statIcon} style={{ background: "#2563eb15", color: "#2563eb" }}>
            <Clock size={22} />
          </div>
          <div>
            <span className={styles.statValue}>{recent.length}</span>
            <span className={styles.statLabel}>Recent Logs</span>
          </div>
        </div>
      </div>

      {/* Drift Alert */}
      {drift?.any_drift_detected && (
        <div className={styles.driftAlert}>
          <AlertTriangle size={18} />
          <span>Feature drift detected! Model may need retraining.</span>
        </div>
      )}

      {alerts.map((alert) => <div className={styles.alertBanner} key={`${alert.type}-${alert.message}`}><AlertTriangle size={17} /><span>{alert.message}</span></div>)}

      <div className={styles.chartGrid}>
        <section className={styles.chartCard}><div className={styles.cardHeader}><TrendingUp size={18} /><h3>Prediction trends</h3></div><div className={styles.chart}><ResponsiveContainer width="100%" height={220}><LineChart data={trendData}><CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" /><XAxis dataKey="day" /><YAxis allowDecimals={false} /><Tooltip /><Line type="monotone" dataKey="predictions" stroke="#2563eb" strokeWidth={2} name="Predictions" /><Line type="monotone" dataKey="highRisk" stroke="#dc2626" strokeWidth={2} name="High risk" /></LineChart></ResponsiveContainer></div></section>
        <section className={styles.chartCard}><div className={styles.cardHeader}><Activity size={18} /><h3>Drift history</h3></div><div className={styles.chart}><ResponsiveContainer width="100%" height={220}><BarChart data={[...driftHistory].reverse()}><CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" /><XAxis dataKey="timestamp" tickFormatter={(value) => new Date(value).toLocaleDateString()} /><YAxis allowDecimals={false} /><Tooltip /><Bar dataKey="sample_size" fill="#f59e0b" name="Sample size" /></BarChart></ResponsiveContainer></div></section>
      </div>

      {/* Recent Predictions */}
      <div className={styles.tableCard}>
        <div className={styles.cardHeader}>
          <BarChart3 size={18} />
          <h3>Recent Predictions</h3>
        </div>
        <div className={styles.filters}>
          <label className={styles.searchField}>
            <Search size={16} />
            <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search client, agent, occupation..." />
          </label>
          <select value={riskFilter} onChange={(event) => setRiskFilter(event.target.value)} aria-label="Filter by risk">
            <option value="">All risk levels</option>
            <option value="LOW RISK">Low risk</option>
            <option value="MEDIUM RISK">Medium risk</option>
            <option value="HIGH RISK">High risk</option>
            <option value="VERY HIGH RISK">Very high risk</option>
          </select>
          <span className={styles.filterCount}>{filteredRecent.length} shown</span>
        </div>
        <div className={styles.tableWrap}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Time</th>
                <th>Client ID</th>
                <th>Risk</th>
                <th>Probability</th>
                <th>Source</th>
              </tr>
            </thead>
            <tbody>
              {filteredRecent.map((row) => (
                <tr key={row.id} onClick={() => setSelectedPrediction(row)} className={styles.clickableRow}>
                  <td>{new Date(row.timestamp).toLocaleString()}</td>
                  <td>{row.client_id || "—"}</td>
                  <td>
                    <span className={`${styles.riskBadge} ${styles[row.risk_label?.replace(/\s/g, "")] || ""}`}>
                      {row.risk_label || "—"}
                    </span>
                  </td>
                  <td>
                    {row.default_probability != null
                      ? (row.default_probability * 100).toFixed(1) + "%"
                      : "—"}
                  </td>
                  <td>{row.source}</td>
                </tr>
              ))}
              {!filteredRecent.length && (
                <tr><td colSpan="5" className={styles.empty}>No predictions match these filters.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div className={styles.auditCard}>
        <div className={styles.cardHeader}><Activity size={18} /><h3>Admin Audit Log</h3></div>
        <div className={styles.auditList}>
          {auditEvents.length ? auditEvents.map((event) => (
            <div className={styles.auditItem} key={event.id}>
              <strong>{event.action.replaceAll("_", " ")}</strong>
              <span>{event.actor_username || "system"} → {event.target_username || "—"}</span>
              <time>{new Date(event.timestamp).toLocaleString()}</time>
            </div>
          )) : <div className={styles.empty}>No administrator actions recorded yet.</div>}
        </div>
      </div>

      <div className={styles.auditCard}>
        <div className={styles.cardHeader}><TrendingUp size={18} /><h3>Model deployment history</h3></div>
        <div className={styles.auditList}>{deployments.length ? deployments.map((deployment) => <div className={styles.auditItem} key={deployment.id}><strong>{deployment.status}</strong><span>{deployment.deployed_by || "system"} · binary {deployment.binary_version}</span><time>{new Date(deployment.deployed_at).toLocaleString()}</time></div>) : <div className={styles.empty}>No model deployments recorded.</div>}</div>
      </div>

      {selectedPrediction && (
        <div className={styles.modalBackdrop} onClick={() => setSelectedPrediction(null)} role="presentation">
          <section className={styles.detailModal} onClick={(event) => event.stopPropagation()}>
            <div className={styles.detailHeader}>
              <div><span className={styles.eyebrow}>Prediction #{selectedPrediction.id}</span><h3>Prediction details</h3></div>
              <button className={styles.closeBtn} onClick={() => setSelectedPrediction(null)} title="Close details"><X size={18} /></button>
            </div>
            <div className={styles.detailGrid}>
              {Object.entries(selectedPrediction).map(([key, value]) => (
                <div key={key} className={styles.detailItem}><span>{key.replaceAll("_", " ")}</span><strong>{value ?? "—"}</strong></div>
              ))}
            </div>
          </section>
        </div>
      )}
    </div>
  );
}
