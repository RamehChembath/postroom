"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "../../../lib/api";

export default function PlatformDashboard() {
  const [data, setData] = useState(null);
  useEffect(() => { api("/platform/overview/?range=30d").then(setData).catch(() => {}); }, []);
  if (!data) return <main><p className="hint">Loading...</p></main>;

  const marginNeg = data.estimated_margin_inr < 0;
  const topTenants = [...data.tenants].sort((a, b) => b.cost_usd - a.cost_usd).slice(0, 5);

  return (
    <main>
      <h1 className="pf-h1">Dashboard</h1>
      <p className="pf-sub">Platform health at a glance — last 30 days.</p>

      <div className="pf-stats">
        <div className="pf-stat"><div className="num">{data.tenants.length}</div><div className="lbl">Active tenants</div></div>
        <div className="pf-stat"><div className="num">${data.total_cost_usd.toFixed(2)}</div><div className="lbl">Total LLM cost</div></div>
        <div className="pf-stat"><div className="num">₹{data.subscription_fees_inr.toLocaleString()}</div><div className="lbl">Fees billed</div></div>
        <div className="pf-stat"><div className={`num ${marginNeg ? "neg" : ""}`}>₹{data.estimated_margin_inr.toLocaleString()}</div><div className="lbl">Estimated margin</div></div>
      </div>

      <div className="pf-card">
        <div className="row" style={{ justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
          <h2 style={{ margin: 0 }}>Top tenants by AI spend</h2>
          <Link href="/platform/costs" className="pf-link">Full cost dashboard →</Link>
        </div>
        <table className="pf-table">
          <thead><tr><th>Tenant</th><th>Plan</th><th>Cost</th><th>Margin</th></tr></thead>
          <tbody>
            {topTenants.map((t) => (
              <tr key={t.user_id}>
                <td>{t.name}</td><td>{t.plan}</td><td>${t.cost_usd.toFixed(4)}</td>
                <td className={t.margin_inr < 0 ? "pf-margin-neg" : "pf-margin-pos"}>₹{t.margin_inr}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </main>
  );
}
