import React, { useEffect, useState } from "react";
import { Users, Loader2, ToggleLeft, ToggleRight, KeyRound } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import styles from "./Agents.module.css";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function Agents() {
  const { token } = useAuth();
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [resetAgent, setResetAgent] = useState(null);
  const [newPassword, setNewPassword] = useState("");
  const [actionError, setActionError] = useState("");
  const [actionLoading, setActionLoading] = useState(false);
  const [sessions, setSessions] = useState([]);

  useEffect(() => {
    fetchAgents();
    fetchSessions();
  }, []);

  const fetchAgents = async () => {
    try {
      const res = await fetch(`${API_URL}/admin/users`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) setAgents(await res.json());
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const fetchSessions = async () => {
    const res = await fetch(`${API_URL}/admin/sessions`, { headers: { Authorization: `Bearer ${token}` } });
    if (res.ok) setSessions((await res.json()).sessions);
  };

  const changeRole = async (id, role) => {
    const res = await fetch(`${API_URL}/admin/users/${id}/role`, { method: "PATCH", headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` }, body: JSON.stringify({ role }) });
    if (res.ok) fetchAgents();
  };

  const revokeSession = async (id) => {
    const res = await fetch(`${API_URL}/admin/sessions/${id}/revoke`, { method: "PATCH", headers: { Authorization: `Bearer ${token}` } });
    if (res.ok) fetchSessions();
  };

  const toggleStatus = async (id, current) => {
    try {
      const res = await fetch(`${API_URL}/admin/agents/${id}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ is_active: !current }),
      });
      if (res.ok) fetchAgents();
    } catch (e) {
      console.error(e);
    }
  };

  const openPasswordReset = (agent) => {
    setResetAgent(agent);
    setNewPassword("");
    setActionError("");
  };

  const resetPassword = async (event) => {
    event.preventDefault();
    setActionError("");
    if (newPassword.length < 8) {
      setActionError("Password must be at least 8 characters.");
      return;
    }

    setActionLoading(true);
    try {
      const res = await fetch(`${API_URL}/admin/agents/${resetAgent.id}/password`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ password: newPassword }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(Array.isArray(body.detail) ? body.detail.map((item) => item.msg).join(", ") : body.detail || "Password reset failed.");
      }
      setResetAgent(null);
      setNewPassword("");
    } catch (error) {
      setActionError(error.message);
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) {
    return (
      <div className={styles.loading}>
        <Loader2 size={28} className={styles.spin} />
        <span>Loading agents…</span>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <div className={styles.card}>
        <div className={styles.header}>
          <Users size={20} />
          <h3>Agent Accounts</h3>
          <span className={styles.count}>{agents.length} total</span>
        </div>

        <div className={styles.tableWrap}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>ID</th>
                <th>Username</th>
                <th>Full Name</th>
                <th>Role</th>
                <th>Status</th>
                <th>Role</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {agents.map((agent) => (
                <tr key={agent.id}>
                  <td>{agent.id}</td>
                  <td className={styles.mono}>{agent.username}</td>
                  <td>{agent.full_name || "—"}</td>
                  <td>
                    <span className={styles.roleBadge}>{agent.role}</span>
                  </td>
                  <td>
                    <select value={agent.role} onChange={(event) => changeRole(agent.id, event.target.value)} className={styles.roleSelect}>
                      <option value="agent">Agent</option><option value="analyst">Analyst</option><option value="auditor">Auditor</option><option value="admin">Admin</option>
                    </select>
                  </td>
                  <td>
                    <span className={`${styles.statusBadge} ${agent.is_active ? styles.active : styles.inactive}`}>
                      {agent.is_active ? "Active" : "Disabled"}
                    </span>
                  </td>
                  <td>
                    <button
                      className={styles.toggleBtn}
                      onClick={() => toggleStatus(agent.id, agent.is_active)}
                      title={agent.is_active ? "Disable agent" : "Activate agent"}
                    >
                      {agent.is_active ? <ToggleRight size={20} color="#16a34a" /> : <ToggleLeft size={20} color="#94a3b8" />}
                    </button>
                    <button
                      className={styles.resetBtn}
                      onClick={() => openPasswordReset(agent)}
                      title={`Reset password for ${agent.username}`}
                    >
                      <KeyRound size={17} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className={styles.card}>
        <div className={styles.header}><KeyRound size={20} /><h3>Active sessions</h3><span className={styles.count}>{sessions.filter((session) => !session.revoked).length} active</span></div>
        <div className={styles.tableWrap}><table className={styles.table}><thead><tr><th>User</th><th>Created</th><th>Expires</th><th>Status</th><th>Action</th></tr></thead><tbody>{sessions.map((session) => <tr key={session.id}><td>{session.username}</td><td>{new Date(session.created_at).toLocaleString()}</td><td>{new Date(session.expires_at).toLocaleString()}</td><td>{session.revoked ? "Revoked" : "Active"}</td><td><button className={styles.revokeBtn} onClick={() => revokeSession(session.id)} disabled={session.revoked}>Revoke</button></td></tr>)}</tbody></table></div>
      </div>

      {resetAgent && (
        <div className={styles.modalBackdrop} role="presentation" onClick={() => setResetAgent(null)}>
          <form className={styles.modal} onSubmit={resetPassword} onClick={(event) => event.stopPropagation()}>
            <h3>Reset agent password</h3>
            <p>Set a new password for <strong>{resetAgent.username}</strong>.</p>
            <label className={styles.passwordField}>
              New password
              <input
                type="password"
                value={newPassword}
                onChange={(event) => setNewPassword(event.target.value)}
                minLength={8}
                maxLength={128}
                autoFocus
                required
              />
            </label>
            {actionError && <div className={styles.error} role="alert">{actionError}</div>}
            <div className={styles.modalActions}>
              <button type="button" className={styles.cancelBtn} onClick={() => setResetAgent(null)}>Cancel</button>
              <button type="submit" className={styles.confirmBtn} disabled={actionLoading}>
                {actionLoading ? "Resetting…" : "Reset password"}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}