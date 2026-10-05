"use client";
import { useEffect, useState } from "react";
import { api } from "../../../lib/api";
import { useWorkspace } from "../../../lib/workspace";

function todayISO(offsetDays = 0) { const d = new Date(); d.setDate(d.getDate() + offsetDays); return d.toISOString().slice(0, 10); }

export default function GoalsPage() {
  const { current } = useWorkspace();
  const [goals, setGoals] = useState([]);
  const [form, setForm] = useState({ title: "", metric: "likes", target_value: 500, period: "month", start_date: todayISO(), end_date: todayISO(30) });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function load() {
    if (!current) return;
    const data = await api("/brand/goals/", { workspace: current.id });
    setGoals(data.results || data);
  }
  useEffect(() => { load(); }, [current?.id]);

  async function createGoal(e) {
    e.preventDefault();
    setBusy(true); setError("");
    try {
      await api("/brand/goals/", { method: "POST", body: form, workspace: current.id });
      setForm({ ...form, title: "" });
      load();
    } catch (err) { setError(err.message); }
    setBusy(false);
  }

  async function removeGoal(id) {
    await api(`/brand/goals/${id}/`, { method: "DELETE" });
    load();
  }

  return (
    <main className="page">
      <div className="hero"><h1>Goals — {current?.name}</h1><p>Set a target. Strategy and dashboard both work toward it.</p></div>

      <form className="card" onSubmit={createGoal}>
        <label htmlFor="title">Goal</label>
        <input id="title" required placeholder="Grow engagement this quarter" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
        <div className="grid-2">
          <div>
            <label htmlFor="metric">Metric</label>
            <select id="metric" value={form.metric} onChange={(e) => setForm({ ...form, metric: e.target.value })}>
              <option value="likes">Likes</option>
              <option value="comments">Comments</option>
              <option value="posts">Posts published</option>
            </select>
          </div>
          <div>
            <label htmlFor="target">Target value</label>
            <input id="target" type="number" min="1" value={form.target_value} onChange={(e) => setForm({ ...form, target_value: Number(e.target.value) })} />
          </div>
        </div>
        <div className="grid-2">
          <div><label htmlFor="start">Start date</label><input id="start" type="date" value={form.start_date} onChange={(e) => setForm({ ...form, start_date: e.target.value })} /></div>
          <div><label htmlFor="end">End date</label><input id="end" type="date" value={form.end_date} onChange={(e) => setForm({ ...form, end_date: e.target.value })} /></div>
        </div>
        {error && <p className="error">{error}</p>}
        <button className="btn primary" style={{ marginTop: 14 }} disabled={busy} type="submit">{busy ? <span className="spin" /> : "Set goal"}</button>
      </form>

      <h2 className="section-title">Active goals</h2>
      {goals.length === 0 && <p className="hint">No goals yet.</p>}
      {goals.map((g) => (
        <div className="card" key={g.id}>
          <div className="card-row">
            <h3>{g.title}</h3>
            <button className="btn small danger" onClick={() => removeGoal(g.id)}>Remove</button>
          </div>
          <p className="hint">{g.progress.current} of {g.progress.target} {g.metric} &middot; {g.start_date} to {g.end_date}</p>
          <div style={{ height: 8, background: "var(--line)", borderRadius: 4, overflow: "hidden", marginTop: 6 }}>
            <div style={{ height: "100%", width: `${g.progress.pct}%`, background: "var(--accent)" }} />
          </div>
        </div>
      ))}
    </main>
  );
}
