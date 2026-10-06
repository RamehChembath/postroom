"use client";
import { useEffect, useState } from "react";
import { api } from "../../../../lib/api";

export default function TenantsPage() {
  const [data, setData] = useState(null);
  useEffect(() => { api("/platform/overview/?range=365d").then(setData).catch(() => {}); }, []);
  if (!data) return <main><p className="hint">Loading...</p></main>;

  return (
    <main>
      <h1 className="pf-h1">Tenants</h1>
      <p className="pf-sub">Every account on the platform — plan, status, and avatars managed.</p>

      <div className="pf-card">
        <table className="pf-table">
          <thead><tr><th>Tenant</th><th>Status</th><th>Plan</th><th>Avatars</th><th>AI cost (365d)</th></tr></thead>
          <tbody>
            {data.tenants.map((t) => (
              <tr key={t.user_id}>
                <td><strong>{t.name}</strong><div className="hint" style={{ margin: 0 }}>{t.email}</div></td>
                <td><span className={`pf-status ${t.status}`}>{t.status}</span></td>
                <td>{t.plan}</td>
                <td>{t.workspace_count}</td>
                <td>${t.cost_usd.toFixed(4)}</td>
              </tr>
            ))}
            {!data.tenants.length && <tr><td colSpan={5} className="hint">No tenants yet.</td></tr>}
          </tbody>
        </table>
      </div>
    </main>
  );
}
