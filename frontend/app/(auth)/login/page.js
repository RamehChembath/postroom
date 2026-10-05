"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { login } from "../../../lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function onSubmit(e) {
    e.preventDefault();
    setBusy(true); setError("");
    try {
      await login(email, password);
      router.push("/dashboard");
    } catch (err) {
      setError(err.message);
    }
    setBusy(false);
  }

  return (
    <div className="auth-wrap">
      <div className="hero"><h1>Welcome back</h1><p>Log in to Postroom.</p></div>
      <form className="card" onSubmit={onSubmit}>
        <label htmlFor="email">Email</label>
        <input id="email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        <div className="card-row" style={{ margin: "14px 0 0" }}>
          <label htmlFor="password" style={{ margin: 0 }}>Password</label>
          <Link href="/forgot-password" className="hint" style={{ fontSize: "0.82rem" }}>Forgot password?</Link>
        </div>
        <input id="password" type="password" required value={password} onChange={(e) => setPassword(e.target.value)} />
        {error && <p className="error">{error}</p>}
        <button className="btn primary" style={{ marginTop: 16, width: "100%" }} disabled={busy} type="submit">
          {busy ? <span className="spin" /> : "Log in"}
        </button>
      </form>
      <p className="hint" style={{ textAlign: "center", marginTop: 14 }}>
        No account? <Link href="/register">Create one</Link>
      </p>
    </div>
  );
}
