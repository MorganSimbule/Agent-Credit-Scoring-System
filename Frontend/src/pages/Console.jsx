import React, { useEffect, useState } from "react";
import { useNavigate, NavLink, Outlet } from "react-router-dom";
import { BrainCircuit, BarChart3, Users, ClipboardList, LogOut, AlertTriangle, KeyRound } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import styles from "./Console.module.css";
import logoImage from "../assets/hobbiton.png";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function Console() {
  const { user, role, logout } = useAuth();
  const navigate = useNavigate();
  const [collapsed, setCollapsed] = useState(false);
  const [modelsLoaded, setModelsLoaded] = useState(true);
  const [passwordOpen, setPasswordOpen] = useState(false);
  const [passwords, setPasswords] = useState({ current_password: "", new_password: "" });
  const [passwordMessage, setPasswordMessage] = useState("");

  useEffect(() => {
    fetch(`${API_URL}/`)
      .then((r) => r.json())
      .then((h) => setModelsLoaded(h.models_loaded))
      .catch(() => setModelsLoaded(false));
  }, []);

  const handleLogout = async () => {
    await fetch(`${API_URL}/auth/logout`, { method: "POST", headers: { Authorization: `Bearer ${user?.access_token}` } }).catch(() => {});
    logout();
    navigate("/");
  };

  const changePassword = async (event) => {
    event.preventDefault();
    setPasswordMessage("");
    const res = await fetch(`${API_URL}/auth/change-password`, { method: "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${user?.access_token}` }, body: JSON.stringify(passwords) });
    const body = await res.json().catch(() => ({}));
    if (!res.ok) { setPasswordMessage(body.detail || "Password change failed."); return; }
    setPasswordMessage("Password changed successfully.");
    setPasswords({ current_password: "", new_password: "" });
  };

  const links =
    role === "admin"
      ? [
          { to: "/console/monitoring", label: "Monitoring", icon: BarChart3 },
          { to: "/console/agents", label: "Agent Accounts", icon: Users },
        ]
      : [
          { to: "/console/predict", label: "Score Agent", icon: BrainCircuit },
          { to: "/console/workspace", label: "My Workspace", icon: ClipboardList },
        ];

  return (
    <div className={styles.console}>
      <aside className={`${styles.sidebar} ${collapsed ? styles.collapsed : ""}`}>
        <div className={styles.sidebarHeader}>
          <img src={logoImage} alt="Hobbiton" className={styles.logo} />
          <button className={styles.collapseBtn} onClick={() => setCollapsed(!collapsed)}>
            {collapsed ? "›" : "‹"}
          </button>
        </div>

        <nav className={styles.nav}>
          {links.map((link) => {
            const Icon = link.icon;
            return (
              <NavLink
                key={link.to}
                to={link.to}
                className={({ isActive }) =>
                  `${styles.navItem} ${isActive ? styles.active : ""}`
                }
              >
                <Icon size={20} strokeWidth={1.8} />
                {!collapsed && <span>{link.label}</span>}
                {!collapsed && <div className={styles.indicator} />}
              </NavLink>
            );
          })}
        </nav>

        <div className={styles.sidebarFooter}>
          {!collapsed && (
            <div className={styles.userInfo}>
              <span className={styles.userName}>{user?.username}</span>
              <span className={styles.userRole}>{role}</span>
            </div>
          )}
          <button className={styles.logoutBtn} onClick={handleLogout}>
            <LogOut size={18} />
            {!collapsed && <span>Sign Out</span>}
          </button>
        </div>
      </aside>

      <main className={styles.main}>
        <header className={styles.header}>
          <h2>Agent Credit Scoring Console</h2>
          <div className={styles.headerRight}>
            <span className={styles.roleBadge}>{role}</span>
            <button className={styles.headerAction} onClick={() => { setPasswordOpen(true); setPasswordMessage(""); }} title="Change password"><KeyRound size={16} /> Change password</button>
          </div>
        </header>

        {!modelsLoaded && (
          <div className={styles.warningBanner}>
            <AlertTriangle size={16} />
            <span>Models aren't loaded on the backend yet. Run train_export.py and restart the server.</span>
          </div>
        )}

        <div className={styles.content}>
          <Outlet />
        </div>
      </main>
      {passwordOpen && <div className={styles.modalBackdrop} onClick={() => setPasswordOpen(false)} role="presentation"><form className={styles.passwordModal} onSubmit={changePassword} onClick={(event) => event.stopPropagation()}><h3>Change password</h3><input type="password" placeholder="Current password" value={passwords.current_password} onChange={(event) => setPasswords({ ...passwords, current_password: event.target.value })} required /><input type="password" placeholder="New password (8+ characters)" minLength={8} value={passwords.new_password} onChange={(event) => setPasswords({ ...passwords, new_password: event.target.value })} required />{passwordMessage && <p>{passwordMessage}</p>}<div className={styles.modalActions}><button type="button" onClick={() => setPasswordOpen(false)}>Close</button><button type="submit">Change password</button></div></form></div>}
    </div>
  );
}