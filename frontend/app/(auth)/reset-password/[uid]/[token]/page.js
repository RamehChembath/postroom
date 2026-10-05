"use client";
import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000/api";

export default function ResetPasswordPage() {
  const { uid, token } = useParams();
  const router = useRouter();
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [done, setDone] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function onSubmit(e) {
    e.preventDefault();
    if (password !== confirm) { setError("Passwords don't match"); return; }
    setBusy(true); setError("");
    try {
      const res = await fetch(`${API_BASE}/auth/password-reset/confirm/`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ uid, token, password }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "That link is invalid or has expired.");
      setDone(true);
      setTimeout(() => router.push("/login"), 2000);
    } catch (err) { setError(err.message); }
    setBusy(false);
  }

  return (
    <div className="auth-wrap">
      <div className="hero"><h1>Set a new password</h1></div>
      {done ? (
        <div className="card"><p style={{ margin: 0 }}>Password updated — taking you to login...</p></div>
      ) : (
        <form className="card" onSubmit={onSubmit}>
          <label htmlFor="password">New password</label>
          <input id="password" type="password" required minLength={8} value={password} onChange={(e) => setPassword(e.target.value)} />
          <label htmlFor="confirm">Confirm password</label>
          <input id="confirm" type="password" required minLength={8} value={confirm} onChange={(e) => setConfirm(e.target.value)} />
          {error && <p className="error">{error}</p>}
          <button className="btn primary" style={{ marginTop: 16, width: "100%" }} disabled={busy} type="submit">
            {busy ? <span className="spin" /> : "Update password"}
          </button>
        </form>
      )}
      <p className="hint" style={{ textAlign: "center", marginTop: 14 }}>
        <Link href="/login">Back to login</Link>
      </p>
    </div>
  );
}
