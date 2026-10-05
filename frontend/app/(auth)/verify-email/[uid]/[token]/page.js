"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000/api";

export default function VerifyEmailPage() {
  const { uid, token } = useParams();
  const [status, setStatus] = useState("checking"); // checking | ok | error
  const [message, setMessage] = useState("");

  useEffect(() => {
    fetch(`${API_BASE}/auth/verify-email/`, {
      method: "POST", credentials: "include", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ uid, token }),
    })
      .then(async (res) => {
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Verification failed.");
        setStatus("ok");
      })
      .catch((e) => { setStatus("error"); setMessage(e.message); });
  }, [uid, token]);

  return (
    <div className="auth-wrap">
      <div className="hero"><h1>Email verification</h1></div>
      <div className="card">
        {status === "checking" && <p style={{ margin: 0 }}><span className="spin" /> Verifying...</p>}
        {status === "ok" && <p style={{ margin: 0 }}>Your email is verified. <Link href="/dashboard">Go to Postroom</Link></p>}
        {status === "error" && <p className="error" style={{ margin: 0 }}>{message}</p>}
      </div>
    </div>
  );
}
