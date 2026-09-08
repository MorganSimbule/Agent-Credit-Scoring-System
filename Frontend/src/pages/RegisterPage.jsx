import React, { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { Loader2, CircleAlert, CircleCheck, Lock, User, IdCard, Eye, EyeOff } from "lucide-react";
import styles from "./LandingPage.module.css";
import heroImage from "../assets/hero.jpg";
import logoImage from "../assets/hobbiton.png";
import { registerAgent } from "../api/auth";

export default function RegisterPage() {
  const navigate = useNavigate();
  const [fullName, setFullName] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setError(null);

    if (!fullName.trim() || !username.trim() || !password.trim()) {
      setError("Fill in all fields.");
      return;
    }
    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    if (password !== confirmPassword) {
      setError("Passwords don't match.");
      return;
    }

    setLoading(true);
    try {
      await registerAgent({
        username: username.trim(),
        password,
        full_name: fullName.trim(),
      });
      setSuccess(true);
      setTimeout(() => navigate("/"), 1500);
    } catch (err) {
      const detail = err.response?.data?.detail;
      if (err.response?.status === 409) {
        setError("That Agent ID is already taken.");
      } else if (Array.isArray(detail)) {
        setError(detail.map((d) => d.msg).join(", "));
      } else {
        setError(detail || "Registration failed. Check your connection and try again.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.page} style={{ "--hero-image": `url(${heroImage})` }}>
      <div className={styles.photoLayer} />
      <div className={styles.grain} />

      <div className={styles.card}>
        <div className={styles.logo}>
          <img src={logoImage} alt="Hobbiton" />
        </div>

        <p className={styles.projectName}>Agent Credit Scoring System</p>
        <h1>Create Agent Account</h1>

        {success ? (
          <div className={styles.error} style={{ background: "#f0fdf4", borderColor: "#bbf7d0", color: "#16a34a" }} role="status">
            <CircleCheck size={15} />
            <span>Account created. Redirecting to login…</span>
          </div>
        ) : (
          <>
            <form onSubmit={submit} className={styles.form}>
              <label className={styles.field}>
                <span>Full Name</span>
                <div className={styles.inputWrap}>
                  <IdCard size={17} strokeWidth={1.8} className={styles.icon} />
                  <input
                    type="text"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="e.g. Chanda Mwale"
                    autoComplete="name"
                    disabled={loading}
                  />
                </div>
              </label>

              <label className={styles.field}>
                <span>Agent ID</span>
                <div className={styles.inputWrap}>
                  <User size={17} strokeWidth={1.8} className={styles.icon} />
                  <input
                    type="text"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder="e.g. AG-10493"
                    autoComplete="username"
                    disabled={loading}
                  />
                </div>
              </label>

              <label className={styles.field}>
                <span>Password</span>
                <div className={styles.inputWrap}>
                  <Lock size={17} strokeWidth={1.8} className={styles.icon} />
                  <input
                    type={showPassword ? "text" : "password"}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="At least 8 characters"
                    autoComplete="new-password"
                    disabled={loading}
                  />
                  <button
                    type="button"
                    className={styles.toggleVisibility}
                    onClick={() => setShowPassword((v) => !v)}
                    aria-label={showPassword ? "Hide password" : "Show password"}
                    tabIndex={-1}
                  >
                    {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </label>

              <label className={styles.field}>
                <span>Confirm Password</span>
                <div className={styles.inputWrap}>
                  <Lock size={17} strokeWidth={1.8} className={styles.icon} />
                  <input
                    type={showPassword ? "text" : "password"}
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="Re-enter password"
                    autoComplete="new-password"
                    disabled={loading}
                  />
                </div>
              </label>

              <button type="submit" className={styles.btn} disabled={loading}>
                {loading ? <Loader2 size={16} className={styles.spin} /> : null}
                {loading ? "Creating account…" : "Create account"}
              </button>
            </form>

            {error && (
              <div className={styles.error} role="alert" aria-live="assertive">
                <CircleAlert size={15} />
                <span>{error}</span>
              </div>
            )}

            <div className={styles.forgotRow} style={{ justifyContent: "center", marginTop: "16px" }}>
              <Link to="/" className={styles.forgotLink}>
                Already have an account? Log in
              </Link>
            </div>
          </>
        )}
      </div>

      <p className={styles.footer}>Hobbiton Investments · Credit Scoring Platform</p>
    </div>
  );
}
