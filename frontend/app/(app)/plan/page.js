"use client";
import { useEffect, useState } from "react";
import { api } from "../../../lib/api";
import { useWorkspace } from "../../../lib/workspace";

function todayISO(offsetDays = 0) {
  const d = new Date(); d.setDate(d.getDate() + offsetDays);
  return d.toISOString().slice(0, 10);
}

export default function PlanPage() {
  const { current } = useWorkspace();
  const [plans, setPlans] = useState([]);
  const [activePlan, setActivePlan] = useState(null);
  const [form, setForm] = useState({ subject: "", brief: "", num_posts: 4, num_articles: 0, start_date: todayISO(), end_date: todayISO(21) });
  const [selected, setSelected] = useState({});
  const [busy, setBusy] = useState({});
  const [error, setError] = useState("");

  async function loadPlans() {
    if (!current) return;
    const data = await api("/content/plans/", { workspace: current.id });
    setPlans(data.results || data);
  }
  useEffect(() => { loadPlans(); }, [current?.id]);

  async function createPlan(e) {
    e.preventDefault();
    setBusy((b) => ({ ...b, create: true })); setError("");
    try {
      const plan = await api("/content/plans/", { method: "POST", body: form, workspace: current.id });
      setActivePlan(plan);
      await loadPlans();
    } catch (err) { setError(err.message); }
    setBusy((b) => ({ ...b, create: false }));
  }

  async function generateCalendar() {
    setBusy((b) => ({ ...b, calendar: true })); setError("");
    try {
      const updated = await api(`/content/plans/${activePlan.id}/generate-calendar/`, { method: "POST" });
      setActivePlan(updated);
      setSelected(Object.fromEntries(updated.items.map((it) => [it.id, true])));
    } catch (err) { setError(err.message); }
    setBusy((b) => ({ ...b, calendar: false }));
  }

  function updateItemTitle(id, title) {
    setActivePlan((p) => ({ ...p, items: p.items.map((it) => (it.id === id ? { ...it, title } : it)) }));
  }

  async function approveAndGenerate() {
    setBusy((b) => ({ ...b, approve: true })); setError("");
    try {
      // Persist any title edits first.
      for (const it of activePlan.items) {
        if (selected[it.id]) await api(`/content/planned-items/${it.id}/`, { method: "PATCH", body: { title: it.title } });
      }
      const approved = activePlan.items.filter((it) => selected[it.id]).map((it) => it.id);
      const rejected = activePlan.items.filter((it) => !selected[it.id]).map((it) => it.id);
      const out = await api(`/content/plans/${activePlan.id}/approve-items/`, { method: "POST", body: { approved, rejected } });
      setActivePlan((p) => ({ ...p, status: "approved" }));
      alert(`${out.created_post_ids.length} draft(s) generated. Open "Approve Posts" to review them.`);
    } catch (err) { setError(err.message); }
    setBusy((b) => ({ ...b, approve: false }));
  }

  if (!current) return <main className="page"><p className="hint">Loading...</p></main>;

  return (
    <main className="page">
      <div className="hero"><h1>Strategy &amp; calendar — {current.name}</h1><p>Tell us the brief, and we'll propose a posting calendar.</p></div>

      {!activePlan && (
        <form className="card" onSubmit={createPlan}>
          <label htmlFor="subject">Subject</label>
          <input id="subject" required value={form.subject} onChange={(e) => setForm({ ...form, subject: e.target.value })} placeholder="Q4 content push" />
          <label htmlFor="brief">Brief</label>
          <textarea id="brief" rows={3} value={form.brief} onChange={(e) => setForm({ ...form, brief: e.target.value })} placeholder="What should this batch focus on?" />
          <div className="grid-2">
            <div><label htmlFor="posts">Number of posts</label><input id="posts" type="number" min="0" value={form.num_posts} onChange={(e) => setForm({ ...form, num_posts: Number(e.target.value) })} /></div>
            <div><label htmlFor="articles">Number of articles</label><input id="articles" type="number" min="0" value={form.num_articles} onChange={(e) => setForm({ ...form, num_articles: Number(e.target.value) })} /></div>
          </div>
          <div className="grid-2">
            <div><label htmlFor="start">Start date</label><input id="start" type="date" value={form.start_date} onChange={(e) => setForm({ ...form, start_date: e.target.value })} /></div>
            <div><label htmlFor="end">End date</label><input id="end" type="date" value={form.end_date} onChange={(e) => setForm({ ...form, end_date: e.target.value })} /></div>
          </div>
          {error && <p className="error">{error}</p>}
          <button className="btn primary" style={{ marginTop: 16 }} disabled={busy.create} type="submit">
            {busy.create ? <span className="spin" /> : "Create plan"}
          </button>
        </form>
      )}

      {activePlan && activePlan.items.length === 0 && (
        <div className="card">
          <p className="hint" style={{ marginTop: 0 }}>Plan "{activePlan.subject}" created. Next, generate a proposed calendar of titles and dates.</p>
          {error && <p className="error">{error}</p>}
          <button className="btn primary" onClick={generateCalendar} disabled={busy.calendar}>
            {busy.calendar ? <span className="spin" /> : "Generate calendar"}
          </button>
        </div>
      )}

      {activePlan && activePlan.items.length > 0 && (
        <>
          <h2 className="section-title">Proposed calendar — review and approve</h2>
          {activePlan.items.map((it) => (
            <div className="card" key={it.id}>
              <div className="card-row">
                <label style={{ display: "flex", alignItems: "center", gap: 10, margin: 0 }}>
                  <input type="checkbox" checked={!!selected[it.id]} onChange={(e) => setSelected({ ...selected, [it.id]: e.target.checked })} />
                  <span className="tag">{it.item_type}</span>
                </label>
                <span className="tag accent">{it.suggested_date}</span>
              </div>
              <input style={{ marginTop: 10, fontWeight: 600 }} value={it.title} onChange={(e) => updateItemTitle(it.id, e.target.value)} />
              <p className="hint">{it.angle}</p>
              <p className="hint">{it.date_rationale}</p>
            </div>
          ))}
          {error && <p className="error">{error}</p>}
          <button className="btn primary" onClick={approveAndGenerate} disabled={busy.approve}>
            {busy.approve ? <span className="spin" /> : "Approve selected & write drafts"}
          </button>
        </>
      )}

      <h2 className="section-title">Past plans</h2>
      {plans.length === 0 && <p className="hint">No plans yet.</p>}
      {plans.map((p) => (
        <div className="card card-row" key={p.id}>
          <div><h3>{p.subject}</h3><p className="hint">{p.start_date} to {p.end_date} &middot; {p.status}</p></div>
          <button className="btn small" onClick={() => setActivePlan(p)}>Open</button>
        </div>
      ))}
    </main>
  );
}
