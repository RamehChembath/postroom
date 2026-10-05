"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "../../../../lib/api";
import { useWorkspace } from "../../../../lib/workspace";

const PERSONAS = [
  { value: "individual", title: "Myself", desc: "Posts in your own first-person voice — personal opinions and experience." },
  { value: "company", title: "Company spokesperson", desc: "Posts as the official voice of a company page — \"we\", not \"I\"." },
];

export default function NewWorkspacePage() {
  const router = useRouter();
  const { createWorkspace } = useWorkspace();
  const [name, setName] = useState("");
  const [persona, setPersona] = useState("individual");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [pendingCost, setPendingCost] = useState(undefined); // undefined = loading, null = no extra cost

  useEffect(() => { api("/billing/usage/").then((u) => setPendingCost(u.pending_extra_avatar_cost_inr)).catch(() => setPendingCost(null)); }, []);

  async function onSubmit(e) {
    e.preventDefault();
    if (!name.trim()) { setError("Give this avatar a name"); return; }
    setBusy(true); setError("");
    try {
      await createWorkspace(name.trim(), persona);
      router.push("/onboarding");
    } catch (err) { setError(err.message); }
    setBusy(false);
  }

  return (
    <main className="page">
      <div className="hero"><h1>Add an avatar</h1><p>A separate full workspace — its own strategy, calendar, posts, dashboard and goals.</p></div>
      <form className="card" onSubmit={onSubmit}>
        <label htmlFor="ws-name">Name</label>
        <input id="ws-name" value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Northwind — company page" />

        <label>Who are you writing as?</label>
        <div className="persona-choice">
          {PERSONAS.map((p) => (
            <button type="button" key={p.value} className={`persona-card ${persona === p.value ? "on" : ""}`} onClick={() => setPersona(p.value)}>
              <h3>{p.title}</h3>
              <p>{p.desc}</p>
            </button>
          ))}
        </div>

        {pendingCost ? (
          <p className="hint">This avatar isn't included in your plan — it adds <strong>+₹{pendingCost}/month</strong> to your bill.</p>
        ) : pendingCost === null ? (
          <p className="hint">Included in your current plan — no extra charge.</p>
        ) : null}
        {error && <p className="error">{error}</p>}
        <button className="btn primary" style={{ marginTop: 16 }} disabled={busy} type="submit">
          {busy ? <span className="spin" /> : pendingCost ? `Create avatar (+₹${pendingCost}/mo)` : "Create avatar"}
        </button>
      </form>
    </main>
  );
}
