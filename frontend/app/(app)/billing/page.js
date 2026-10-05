"use client";
import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { api } from "../../../lib/api";

const PLAN_ORDER = ["free", "base", "pro"];

export default function BillingPage() {
  const params = useSearchParams();
  const [usage, setUsage] = useState(null);
  const [plans, setPlans] = useState(null);
  const [busy, setBusy] = useState(null);
  const [error, setError] = useState("");
  const checkoutResult = params.get("checkout");

  async function load() {
    const [u, p] = await Promise.all([api("/billing/usage/"), api("/billing/plans/")]);
    setUsage(u); setPlans(p);
  }
  useEffect(() => { load(); }, []);

  async function upgrade(planKey) {
    setBusy(planKey); setError("");
    try {
      const { url } = await api("/billing/checkout/", { method: "POST", body: { plan: planKey } });
      window.location.href = url;
    } catch (e) { setError(e.message); setBusy(null); }
  }

  async function manage() {
    setBusy("portal"); setError("");
    try {
      const { url } = await api("/billing/portal/", { method: "POST" });
      window.location.href = url;
    } catch (e) { setError(e.message); setBusy(null); }
  }

  if (!usage || !plans) return <main className="page"><p className="hint">Loading...</p></main>;

  return (
    <main className="page">
      <div className="hero"><h1>Billing</h1><p>Your plan, per-avatar AI usage, and payment details.</p></div>

      {checkoutResult === "success" && <p className="success-text">Subscription updated — thanks!</p>}
      {checkoutResult === "canceled" && <p className="hint">Checkout canceled — no changes made.</p>}

      <div className="card">
        <div className="card-row">
          <h3>Current plan: {usage.plan_name}</h3>
          {usage.status !== "active" && <span className="tag" style={{ color: "var(--danger)", borderColor: "var(--danger)" }}>{usage.status.replace("_", " ")}</span>}
        </div>
        <p className="hint">
          {usage.price_monthly_inr === 0 ? "Free" : `₹${usage.price_monthly_inr}/month`}
          {usage.extra_workspace_price_inr ? ` · +₹${usage.extra_workspace_price_inr}/month per avatar beyond the first` : ""}
        </p>
        <p className="hint">{usage.workspace_count} of {usage.max_workspaces} avatars used</p>
        {usage.pending_extra_avatar_cost_inr != null && (
          <p className="hint">Adding another avatar right now would cost +₹{usage.pending_extra_avatar_cost_inr}/month.</p>
        )}
        {usage.current_period_end && <p className="hint">Renews {new Date(usage.current_period_end).toLocaleDateString()}{usage.cancel_at_period_end ? " — cancels at period end" : ""}</p>}
        {usage.plan !== "free" && <button className="btn" style={{ marginTop: 10 }} onClick={manage} disabled={busy === "portal"}>{busy === "portal" ? <span className="spin" /> : "Manage billing"}</button>}
      </div>

      {error && <p className="error">{error}</p>}

      <h2 className="section-title">AI usage by avatar</h2>
      {usage.workspaces.map((w) => {
        const pct = Math.min(100, Math.round(w.pct_used));
        const near = pct >= 80;
        return (
          <div className="card" key={w.workspace_id}>
            <div className="card-row">
              <h3>{w.workspace_name}</h3>
              {!w.ai_enabled ? <span className="tag">AI not available on this plan</span> : <span className="tag accent">${w.spend_usd.toFixed(2)} / ${w.budget_usd}</span>}
            </div>
            {w.ai_enabled && (
              <div style={{ height: 8, background: "var(--line)", borderRadius: 4, overflow: "hidden", marginTop: 6 }}>
                <div style={{ height: "100%", width: `${pct}%`, background: near ? "var(--danger)" : "var(--accent)" }} />
              </div>
            )}
          </div>
        );
      })}

      <h2 className="section-title">Plans</h2>
      <div className="grid-2" style={{ gridTemplateColumns: "repeat(3, 1fr)" }}>
        {PLAN_ORDER.map((key) => {
          const p = plans[key];
          const isCurrent = usage.plan === key;
          return (
            <div className="card" key={key} style={isCurrent ? { borderColor: "var(--accent)" } : undefined}>
              <h3>{p.name}</h3>
              <p style={{ fontFamily: "var(--display)", fontSize: "1.5rem", margin: "6px 0" }}>
                {p.price_monthly_inr === 0 ? "Free" : `₹${p.price_monthly_inr}/mo`}
              </p>
              {p.ai_enabled ? (
                <p className="hint">${p.ai_budget_usd_per_workspace} AI budget per avatar / month</p>
              ) : (
                <p className="hint">No AI — manage posts manually only</p>
              )}
              <p className="hint">
                {p.max_workspaces === 1 ? "1 avatar" : `Up to ${p.max_workspaces} avatars`}
                {p.extra_workspace_price_inr ? ` (+₹${p.extra_workspace_price_inr}/mo each beyond the first)` : ""}
              </p>
              {isCurrent ? (
                <span className="tag accent" style={{ marginTop: 10, display: "inline-block" }}>Current plan</span>
              ) : key === "free" ? null : (
                <button className="btn primary small" style={{ marginTop: 10 }} onClick={() => upgrade(key)} disabled={busy === key}>
                  {busy === key ? <span className="spin" /> : `Upgrade to ${p.name}`}
                </button>
              )}
            </div>
          );
        })}
      </div>
    </main>
  );
}
