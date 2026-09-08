import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Loader2,
  CircleAlert,
  CircleCheck,
  Lock,
  User,
  Eye,
  EyeOff,
  ShieldCheck,
  UserPlus,
  Mail,
  Phone,
  IdCard,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import styles from "./LandingPage.module.css";
import logoImage from "../assets/hobbiton.png";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function LandingPage() {
  const navigate = useNavigate();
  const { login } = useAuth();

  // "login" | "register"
  const [mode, setMode] = useState("login");
  // "agent" | "admin" — only relevant while mode === "login"
  const [loginRole, setLoginRole] = useState("agent");

  // Login form state
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);

  // Registration form state (new agents only)
  const [regFullName, setRegFullName] = useState("");
  const [regAgentId, setRegAgentId] = useState("");
  const [regPhone, setRegPhone] = useState("");
  const [regEmail, setRegEmail] = useState("");
  const [regPassword, setRegPassword] = useState("");
  const [regConfirm, setRegConfirm] = useState("");
  const [showRegPassword, setShowRegPassword] = useState(false);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  const switchMode = (next) => {
    setMode(next);
    setError(null);
    setSuccess(null);
  };

  const submitLogin = async (e) => {
    e.preventDefault();
    setError(null);

    if (!username.trim() || !password.trim()) {
      setError("Enter your username and password.");
      return;
    }

    setLoading(true);
    try {
      const formData = new URLSearchParams();
      formData.append("username", username);
      formData.append("password", password);

      const res = await fetch(`${API_URL}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: formData,
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Login failed");
      }

      const data = await res.json();
      login(data);
      navigate(loginRole === "admin" ? "/admin" : "/console");
    } catch (err) {
      setError(err.message || "Login failed. Check your credentials.");
    } finally {
      setLoading(false);
    }
  };

  const submitRegister = async (e) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    if (
      !regFullName.trim() ||
      !regAgentId.trim() ||
      !regPhone.trim() ||
      !regPassword.trim()
    ) {
      setError("Fill in all required fields.");
      return;
    }
    if (regPassword.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    if (regPassword !== regConfirm) {
      setError("Passwords do not match.");
      return;
    }

    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          full_name: regFullName,
          username: regAgentId,
          password: regPassword,
        }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        const detail = Array.isArray(err.detail)
          ? err.detail.map((item) => item.msg).join(", ")
          : err.detail;
        throw new Error(detail || "Registration failed");
      }

      setSuccess("Account created. You can now log in.");
      setUsername(regAgentId);
      setRegFullName("");
      setRegAgentId("");
      setRegPhone("");
      setRegEmail("");
      setRegPassword("");
      setRegConfirm("");
      setTimeout(() => switchMode("login"), 1200);
    } catch (err) {
      setError(err.message || "Registration failed. Try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.page}>
      <div className={styles.photoLayer} />
      <div className={styles.overlay} />

      <div className={styles.card}>
        <div className={styles.logoGlow}>
          <div className={styles.logo}>
            <img src={logoImage} alt="Hobbiton" />
          </div>
        </div>

        <div className={styles.tabs}>
          <button
            type="button"
            className={`${styles.tab} ${mode === "login" ? styles.tabActive : ""}`}
            onClick={() => switchMode("login")}
          >
            Log in
          </button>
          <button
            type="button"
            className={`${styles.tab} ${mode === "register" ? styles.tabActive : ""}`}
            onClick={() => switchMode("register")}
          >
            Register
          </button>
        </div>

        {mode === "login" ? (
          <>
            <p className={styles.subtitle}>Agents &amp; Administrators</p>

            <div className={styles.roleToggle}>
              <button
                type="button"
                className={`${styles.roleBtn} ${
                  loginRole === "agent" ? styles.roleBtnActive : ""
                }`}
                onClick={() => setLoginRole("agent")}
              >
                <User size={14} />
                Agent
              </button>
              <button
                type="button"
                className={`${styles.roleBtn} ${
                  loginRole === "admin" ? styles.roleBtnActive : ""
                }`}
                onClick={() => setLoginRole("admin")}
              >
                <ShieldCheck size={14} />
                Admin
              </button>
            </div>

            <form onSubmit={submitLogin} className={styles.form}>
              <label className={styles.field}>
                <span>{loginRole === "admin" ? "Admin Username" : "Agent Username"}</span>
                <div className={styles.inputWrap}>
                  <User size={17} strokeWidth={1.8} className={styles.iconLeft} />
                  <input
                    type="text"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder={loginRole === "admin" ? "admin" : "e.g. AG-10493"}
                    autoComplete="username"
                  />
                </div>
              </label>

              <label className={styles.field}>
                <span>Password</span>
                <div className={styles.inputWrap}>
                  <Lock size={17} strokeWidth={1.8} className={styles.iconLeft} />
                  <input
                    type={showPassword ? "text" : "password"}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Enter password"
                    autoComplete="current-password"
                  />
                  <button
                    type="button"
                    className={styles.iconRight}
                    onClick={() => setShowPassword(!showPassword)}
                    tabIndex={-1}
                  >
                    {showPassword ? <EyeOff size={17} /> : <Eye size={17} />}
                  </button>
                </div>
              </label>

              <button type="submit" className={styles.btn} disabled={loading}>
                {loading ? <Loader2 size={16} className={styles.spin} /> : null}
                {loading
                  ? "Signing in…"
                  : `Log in as ${loginRole === "admin" ? "Admin" : "Agent"}`}
              </button>
            </form>
          </>
        ) : (
          <>
            <p className={styles.subtitle}>New agent registration</p>

            <form onSubmit={submitRegister} className={styles.form}>
              <label className={styles.field}>
                <span>Full Name</span>
                <div className={styles.inputWrap}>
                  <User size={17} strokeWidth={1.8} className={styles.iconLeft} />
                  <input
                    type="text"
                    value={regFullName}
                    onChange={(e) => setRegFullName(e.target.value)}
                    placeholder="e.g. Chanda Mwape"
                    autoComplete="name"
                  />
                </div>
              </label>

              <label className={styles.field}>
                <span>Agent ID</span>
                <div className={styles.inputWrap}>
                  <IdCard size={17} strokeWidth={1.8} className={styles.iconLeft} />
                  <input
                    type="text"
                    value={regAgentId}
                    onChange={(e) => setRegAgentId(e.target.value)}
                    placeholder="e.g. AG-10493"
                  />
                </div>
              </label>

              <label className={styles.field}>
                <span>Phone Number</span>
                <div className={styles.inputWrap}>
                  <Phone size={17} strokeWidth={1.8} className={styles.iconLeft} />
                  <input
                    type="tel"
                    value={regPhone}
                    onChange={(e) => setRegPhone(e.target.value)}
                    placeholder="e.g. 0977 123 456"
                    autoComplete="tel"
                  />
                </div>
              </label>

              <label className={styles.field}>
                <span>Email (optional)</span>
                <div className={styles.inputWrap}>
                  <Mail size={17} strokeWidth={1.8} className={styles.iconLeft} />
                  <input
                    type="email"
                    value={regEmail}
                    onChange={(e) => setRegEmail(e.target.value)}
                    placeholder="you@example.com"
                    autoComplete="email"
                  />
                </div>
              </label>

              <label className={styles.field}>
                <span>Password</span>
                <div className={styles.inputWrap}>
                  <Lock size={17} strokeWidth={1.8} className={styles.iconLeft} />
                  <input
                    type={showRegPassword ? "text" : "password"}
                    value={regPassword}
                    onChange={(e) => setRegPassword(e.target.value)}
                    placeholder="At least 8 characters"
                    autoComplete="new-password"
                  />
                  <button
                    type="button"
                    className={styles.iconRight}
                    onClick={() => setShowRegPassword(!showRegPassword)}
                    tabIndex={-1}
                  >
                    {showRegPassword ? <EyeOff size={17} /> : <Eye size={17} />}
                  </button>
                </div>
              </label>

              <label className={styles.field}>
                <span>Confirm Password</span>
                <div className={styles.inputWrap}>
                  <Lock size={17} strokeWidth={1.8} className={styles.iconLeft} />
                  <input
                    type={showRegPassword ? "text" : "password"}
                    value={regConfirm}
                    onChange={(e) => setRegConfirm(e.target.value)}
                    placeholder="Re-enter password"
                    autoComplete="new-password"
                  />
                </div>
              </label>

              <button type="submit" className={styles.btn} disabled={loading}>
                {loading ? (
                  <Loader2 size={16} className={styles.spin} />
                ) : (
                  <UserPlus size={16} />
                )}
                {loading ? "Creating account…" : "Register as Agent"}
              </button>
            </form>
          </>
        )}

        {error && (
          <div className={styles.error}>
            <CircleAlert size={15} />
            <span>{error}</span>
          </div>
        )}

        {success && (
          <div className={styles.success}>
            <CircleCheck size={15} />
            <span>{success}</span>
          </div>
        )}
      </div>

      <footer className={styles.footer}>
        © 2026 Hobbiton Limited. All rights reserved.
      </footer>
    </div>
  );
}
