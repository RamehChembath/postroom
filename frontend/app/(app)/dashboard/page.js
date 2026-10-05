"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "../../../lib/api";
import { useWorkspace } from "../../../lib/workspace";
import TrendChart from "../../../components/TrendChart";

function dayLabel(iso) { return new Date(iso).toLocaleDateString(undefined, { day: "numeric", month: "short" }); }
function monthLabel(iso) { return new Date(iso).toLocaleDateString(undefined, { month: "short", year: "2-digit" }); }

export default function DashboardPage() {
  const { current } = useWorkspace();
  const [data, setData] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function load() {
    if (!current) return;
    setData(await api("/content/dashboard/", { workspace: current.id }));
  }
  useEffect(() => { load(); }, [current?.id]);

  async function runAnalysis() {
    setBusy(true); setError("");
    try { setAnalysis(await api("/content/dashboard/analyze/", { method: "POST", workspace: current.id })); }
    catch (e) { setError(e.message); }
    setBusy(false);
  }

  if (!data || !current) return <main className="page"><p className="hint">Loading...</p></main>;

  const dailySeries = data.daily.map((d) => ({ label: dayLabel(d.day), posts: d.posts, likes: d.likes, comments: d.comments }));
  const monthlySeries = data.monthly.map((m) => ({ label: monthLabel(m.month), posts: m.posts, likes: m.likes, comments: m.comments }));

  return (
    <main className="page">
      <div className="hero"><h1>Performance — {current.name}</h1><p>{data.total_posts} posted &middot; {data.total_likes} total likes &middot; {data.total_comments} total comments</p></div>

      <div className="stat-grid">
        <div className="stat-card"><div className="num">{data.total_likes}</div><div className="lbl">Total likes</div></div>
        <div className="stat-card"><div className="num">{data.total_comments}</div><div className="lbl">Total comments</div></div>
        <div className="stat-card"><div className="num">{data.avg_likes}</div><div className="lbl">Avg likes / post</div></div>
        <div className="stat-card"><div className="num">{data.total_posts}</div><div className="lbl">Posts published</div></div>
      </div>

      {data.active_goal && (
        <div className="card" style={{ borderLeft: "3px solid var(--signal)" }}>
          <div className="card-row"><h3>{data.active_goal.title}</h3><span className="tag accent">{data.active_goal.progress.pct}%</span></div>
          <p className="hint">{data.active_goal.progress.current} of {data.active_goal.progress.target} {data.active_goal.metric}</p>
        </div>
      )}

      <h2 className="section-title">Day by day (last 30 days)</h2>
      <div className="card"><TrendChart series={dailySeries} /></div>

      <h2 className="section-title">Month by month</h2>
      <div className="card"><TrendChart series={monthlySeries} /></div>

      <div className="grid-2">
        <div>
          <h2 className="section-title">Top posts</h2>
          {data.top_posts.map((p) => (
            <Link href={`/posts/${p.id}`} key={p.id} className="card" style={{ display: "block", textDecoration: "none", color: "inherit" }}>
              <div className="card-row"><span>{p.title || p.text.slice(0, 40)}</span><strong style={{ color: "var(--like)" }}>{p.likes}</strong></div>
            </Link>
          ))}
        </div>
        <div>
          <h2 className="section-title">Lowest performing</h2>
          {data.lowest_posts.length ? data.lowest_posts.map((p) => (
            <Link href={`/posts/${p.id}`} key={p.id} className="card" style={{ display: "block", textDecoration: "none", color: "inherit" }}>
              <div className="card-row"><span>{p.title || p.text.slice(0, 40)}</span><strong>{p.likes}</strong></div>
            </Link>
          )) : <p className="hint">Not enough data yet.</p>}
        </div>
      </div>

      <h2 className="section-title">Growth analysis</h2>
      <button className="btn primary" onClick={runAnalysis} disabled={busy}>{busy ? <span className="spin" /> : "Analyze my performance"}</button>
      {error && <p className="error">{error}</p>}
      {analysis && (
        <div className="card">
          <h3>{analysis.headline}</h3>
          <p><strong>What's working:</strong> {analysis.whats_working}</p>
          <p><strong>What isn't:</strong> {analysis.whats_not}</p>
          <ul>{(analysis.actions || []).map((a, i) => <li key={i}>{a}</li>)}</ul>
        </div>
      )}
    </main>
  );
}
