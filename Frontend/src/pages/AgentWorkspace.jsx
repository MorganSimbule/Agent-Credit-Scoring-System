import { useEffect, useState } from "react";
import { Bell, ClipboardList } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import styles from "./AgentWorkspace.module.css";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
const statuses = ["New", "Under Review", "Approved", "Declined", "Needs More Information"];

const guidance = {
  "LOW RISK": "Continue normal review and document the supporting activity data.",
  "MEDIUM RISK": "Review repayment capacity and request supporting transaction evidence.",
  "HIGH RISK": "Escalate for additional review before making a credit decision.",
  "VERY HIGH RISK": "Pause automated progression and require senior risk review.",
};

export default function AgentWorkspace() {
  const { token } = useAuth();
  const [predictions, setPredictions] = useState([]);
  const [risk, setRisk] = useState("");
  const [selected, setSelected] = useState(null);

  const headers = { Authorization: `Bearer ${token}` };

  const load = async () => {
    const predictionRes = await fetch(`${API_URL}/api/my-predictions`, { headers });
    if (predictionRes.ok) setPredictions((await predictionRes.json()).predictions);
  };

  useEffect(() => { load(); }, []);

  const updateStatus = async (id, status) => {
    await fetch(`${API_URL}/api/my-predictions/${id}/status`, { method: "PATCH", headers: { ...headers, "Content-Type": "application/json" }, body: JSON.stringify({ status }) });
    load();
  };

  const filtered = predictions.filter((item) => !risk || item.risk_label === risk);
  const notifications = predictions.filter((item) => ["HIGH RISK", "VERY HIGH RISK"].includes(item.risk_label));

  return <div className={styles.page}>
    <div className={styles.heading}><div><span className={styles.eyebrow}>Agent workspace</span><h1>My scoring activity</h1></div><span className={styles.count}>{predictions.length} records</span></div>
    {notifications.length > 0 && <div className={styles.notice}><Bell size={17} /><span>{notifications.length} high-risk result{notifications.length === 1 ? "" : "s"} need follow-up review.</span></div>}

    <section className={styles.panel}>
      <div className={styles.panelHeader}><ClipboardList size={18} /><h2>Prediction history</h2></div>
      <div className={styles.filters}>
        <select value={risk} onChange={(event) => setRisk(event.target.value)} aria-label="Filter predictions by risk">
          <option value="">All risk levels</option>
          <option>LOW RISK</option>
          <option>MEDIUM RISK</option>
          <option>HIGH RISK</option>
          <option>VERY HIGH RISK</option>
        </select>
      </div>
      <div className={styles.tableWrap}>
        <table>
          <thead><tr><th>Client</th><th>Date</th><th>Risk</th><th>Probability</th><th>Follow-up</th><th>Guidance</th></tr></thead>
          <tbody>
            {filtered.map((item) => (
              <tr key={item.id} onClick={() => setSelected(item)} className={styles.clickable}>
                <td>{item.client_id || "-"}</td>
                <td>{new Date(item.timestamp).toLocaleDateString()}</td>
                <td>{item.risk_label || "Binary result"}</td>
                <td>{item.default_probability == null ? "-" : `${(item.default_probability * 100).toFixed(1)}%`}</td>
                <td>
                  <select
                    value={item.review_status || "New"}
                    onClick={(event) => event.stopPropagation()}
                    onChange={(event) => updateStatus(item.id, event.target.value)}
                  >
                    {statuses.map((status) => <option key={status}>{status}</option>)}
                  </select>
                </td>
                <td>{guidance[item.risk_label] || "Review the complete prediction detail before proceeding."}</td>
              </tr>
            ))}
            {!filtered.length && <tr><td colSpan="6" className={styles.empty}>No predictions recorded yet.</td></tr>}
          </tbody>
        </table>
      </div>
    </section>

    {selected && <div className={styles.modalBackdrop} onClick={() => setSelected(null)} role="presentation"><section className={styles.detailModal} onClick={(event) => event.stopPropagation()}><h2>Prediction details</h2><p>{guidance[selected.risk_label] || "Review the complete result with your normal credit process."}</p><div className={styles.detailList}>{Object.entries(selected).map(([key, value]) => <div key={key}><span>{key.replaceAll("_", " ")}</span><strong>{value ?? "—"}</strong></div>)}</div><button onClick={() => setSelected(null)}>Close</button></section></div>}
  </div>;
}
