"use client";
import { useState } from "react";
import Link from "next/link";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000/api";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function onSubmit(e) {
    e.preventDefault();
    setBusy(true); setError("");
    try {
      await fetch(`${API_BASE}/auth/password-reset/`, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email }),
      });
      setSent(true);
    } catch { setError("Something went wrong — try again."); }
    setBusy(false);
  }

  return (
    <div className="auth-wrap">
      <div className="hero"><h1>Reset your password</h1><p>We'll email you a link to set a new one.</p></div>
      {sent ? (
        <div className="card"><p style={{ margin: 0 }}>If that email has a Postroom account, a reset link is on its way. Check your inbox.</p></div>
      ) : (
        <form className="card" onSubmit={onSubmit}>
          <label htmlFor="email">Email</label>
          <input id="email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
          {error && <p className="error">{error}</p>}
          <button className="btn primary" style={{ marginTop: 16, width: "100%" }} disabled={busy} type="submit">
            {busy ? <span className="spin" /> : "Send reset link"}
          </button>
        </form>
      )}
      <p className="hint" style={{ textAlign: "center", marginTop: 14 }}>
        <Link href="/login">Back to login</Link>
      </p>
    </div>
  );
}
