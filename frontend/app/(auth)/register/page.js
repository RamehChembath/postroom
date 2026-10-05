"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { register } from "../../../lib/api";
import Turnstile from "../../../components/Turnstile";

export default function RegisterPage() {
  const router = useRouter();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [turnstileToken, setTurnstileToken] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function onSubmit(e) {
    e.preventDefault();
    setBusy(true); setError("");
    try {
      await register(email, password, fullName, turnstileToken);
      router.push("/onboarding");
    } catch (err) {
      setError(err.message);
    }
    setBusy(false);
  }

  return (
    <div className="auth-wrap">
      <div className="hero"><h1>Create your account</h1><p>A few steps and we'll start learning your voice.</p></div>
      <form className="card" onSubmit={onSubmit}>
        <label htmlFor="name">Full name</label>
        <input id="name" value={fullName} onChange={(e) => setFullName(e.target.value)} />
        <label htmlFor="email">Email</label>
        <input id="email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        <label htmlFor="password">Password</label>
        <input id="password" type="password" required minLength={8} value={password} onChange={(e) => setPassword(e.target.value)} />
        <Turnstile onToken={setTurnstileToken} />
        {error && <p className="error">{error}</p>}
        <button className="btn primary" style={{ marginTop: 16, width: "100%" }} disabled={busy} type="submit">
          {busy ? <span className="spin" /> : "Create account"}
        </button>
      </form>
      <p className="hint" style={{ textAlign: "center", marginTop: 14 }}>
        Already have an account? <Link href="/login">Log in</Link>
      </p>
      <p className="hint" style={{ textAlign: "center", marginTop: 8, fontSize: "0.78rem" }}>
        By creating an account you agree to our <Link href="/terms">Terms</Link> and <Link href="/privacy">Privacy Policy</Link>.
      </p>
    </div>
  );
}
