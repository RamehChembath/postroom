"use client";
import { useEffect, useRef, useState } from "react";
import { api } from "../../../../lib/api";

const RANGES = [
  { key: "7d", label: "Last 7d" }, { key: "30d", label: "Last 30d" },
  { key: "90d", label: "Last 90d" }, { key: "365d", label: "Last 365d" },
];

function DailyChart({ daily }) {
  const canvasRef = useRef(null);
  const chartRef = useRef(null);

  useEffect(() => {
    if (!canvasRef.current || !daily?.length) return;
    let cancelled = false;
    import("chart.js").then(({ Chart, BarController, BarElement, LinearScale, CategoryScale, Tooltip }) => {
      if (cancelled) return;
      Chart.register(BarController, BarElement, LinearScale, CategoryScale, Tooltip);
      if (chartRef.current) chartRef.current.destroy();
      chartRef.current = new Chart(canvasRef.current, {
        type: "bar",
        data: {
          labels: daily.map((d) => d.date.slice(5)),
          datasets: [{ data: daily.map((d) => d.cost_usd), backgroundColor: "#4F5CF0", borderRadius: 3, maxBarThickness: 36 }],
        },
        options: {
          responsive: true, maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: { x: { grid: { display: false } }, y: { beginAtZero: true, grid: { color: "#F0F1F3" } } },
        },
      });
    });
    return () => { cancelled = true; chartRef.current?.destroy(); };
  }, [daily]);

  if (!daily?.length) return <p className="hint">No posted AI activity in this period yet.</p>;
  return (
    <>
      <div style={{ height: 220 }}><canvas ref={canvasRef} /></div>
      <div className="row" style={{ justifyContent: "space-between", marginTop: 8 }}>
        <span className="hint">{daily[0]?.date}</span>
        <span className="hint">{daily[daily.length - 1]?.date}</span>
      </div>
    </>
  );
}

export default function CostsPage() {
  const [range, setRange] = useState("30d");
  const [data, setData] = useState(null);

  useEffect(() => { api(`/platform/overview/?range=${range}`).then(setData).catch(() => {}); }, [range]);

  if (!data) return <main className="pf-content-inner"><p className="hint">Loading...</p></main>;

  const marginNeg = data.estimated_margin_inr < 0;

  return (
    <main>
      <h1 className="pf-h1">Cost dashboard</h1>
      <p className="pf-sub">Platform-wide cost, billing, and margin. <strong>Tenants do not see this page</strong> — they only see their own usage and quota.</p>

      <div className="pf-pills">
        {RANGES.map((r) => (
          <button key={r.key} className={`pf-pill ${range === r.key ? "on" : ""}`} onClick={() => setRange(r.key)}>{r.label}</button>
        ))}
      </div>

      <div className="pf-stats">
        <div className="pf-stat"><div className="num">${data.total_cost_usd.toFixed(2)}</div><div className="lbl">Total LLM cost ({range})</div></div>
        <div className="pf-stat"><div className="num">{data.total_calls}</div><div className="lbl">API calls</div></div>
        <div className="pf-stat"><div className="num">₹{data.subscription_fees_inr.toLocaleString()}</div><div className="lbl">Subscription fees billed</div></div>
        <div className="pf-stat"><div className={`num ${marginNeg ? "neg" : ""}`}>₹{data.estimated_margin_inr.toLocaleString()}</div><div className="lbl">Estimated margin</div></div>
      </div>

      <div className="pf-card">
        <h2>Daily LLM cost ({RANGES.find((r) => r.key === range)?.label.toLowerCase()})</h2>
        <DailyChart daily={data.daily} />
      </div>

      <div className="pf-grid-2">
        <div className="pf-card">
          <h2>Cost by purpose</h2>
          <table className="pf-table">
            <thead><tr><th>Purpose</th><th>Calls</th><th>Cost</th></tr></thead>
            <tbody>
              {data.by_purpose.map((p) => (
                <tr key={p.purpose}><td>{p.purpose.replace(/_/g, " ")}</td><td>{p.calls}</td><td>${p.cost_usd.toFixed(4)}</td></tr>
              ))}
              {!data.by_purpose.length && <tr><td colSpan={3} className="hint">No data yet.</td></tr>}
            </tbody>
          </table>
        </div>
        <div className="pf-card">
          <h2>Cost by model</h2>
          <table className="pf-table">
            <thead><tr><th>Model</th><th>Calls</th><th>Cost</th></tr></thead>
            <tbody>
              {data.by_model.map((m) => (
                <tr key={m.model}><td>{m.model}</td><td>{m.calls}</td><td>${m.cost_usd.toFixed(4)}</td></tr>
              ))}
              {!data.by_model.length && <tr><td colSpan={3} className="hint">No data yet.</td></tr>}
            </tbody>
          </table>
        </div>
      </div>

      <div className="pf-card">
        <h2>Per-tenant breakdown</h2>
        <table className="pf-table">
          <thead><tr><th>Tenant</th><th>Status</th><th>Plan</th><th>Avatars</th><th>Cost</th><th>Fees billed</th><th>Margin</th></tr></thead>
          <tbody>
            {data.tenants.map((t) => (
              <tr key={t.user_id}>
                <td><strong>{t.name}</strong><div className="hint" style={{ margin: 0 }}>{t.email}</div></td>
                <td><span className={`pf-status ${t.status}`}>{t.status}</span></td>
                <td>{t.plan}</td>
                <td>{t.workspace_count}</td>
                <td>${t.cost_usd.toFixed(4)}</td>
                <td>₹{t.fees_inr}</td>
                <td className={t.margin_inr < 0 ? "pf-margin-neg" : "pf-margin-pos"}>₹{t.margin_inr}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="pf-card">
        <h2>Top 10 most expensive calls ({RANGES.find((r) => r.key === range)?.label.toLowerCase()})</h2>
        <table className="pf-table">
          <thead><tr><th>Avatar</th><th>Purpose</th><th>Model</th><th>Cost</th><th>When</th></tr></thead>
          <tbody>
            {data.top_expensive_calls.map((c, i) => (
              <tr key={i}>
                <td>{c.workspace}</td><td>{c.purpose.replace(/_/g, " ")}</td><td>{c.model}</td>
                <td>${c.cost_usd.toFixed(4)}</td><td className="hint">{new Date(c.created_at).toLocaleString()}</td>
              </tr>
            ))}
            {!data.top_expensive_calls.length && <tr><td colSpan={5} className="hint">No data yet.</td></tr>}
          </tbody>
        </table>
      </div>

      <p className="hint">{data.fx_note}</p>
    </main>
  );
}
