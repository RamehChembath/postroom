"use client";
import { useEffect, useState } from "react";
import { api } from "../../../lib/api";
import { useWorkspace } from "../../../lib/workspace";

const PERSONAS = [
  { value: "individual", title: "Myself", desc: "First-person, personal opinions and experience." },
  { value: "company", title: "Company spokesperson", desc: "The official \"we\" voice of a company page." },
];

export default function StrategyPage() {
  const { current, reload } = useWorkspace();
  const [profile, setProfile] = useState(null);
  const [persona, setPersona] = useState(null);
  const [topics, setTopics] = useState([]);
  const [busy, setBusy] = useState({});
  const [error, setError] = useState("");

  async function load() {
    if (!current) return;
    setProfile(await api("/brand/profile/", { workspace: current.id }));
    setPersona(current.persona_type);
  }
  useEffect(() => { load(); }, [current?.id]);

  async function save() {
    setBusy((b) => ({ ...b, save: true }));
    try {
      await api("/brand/profile/", { method: "PATCH", workspace: current.id, body: {
        industry: profile.industry, target_audience: profile.target_audience,
        core_topics: profile.core_topics, voice_notes: profile.voice_notes, company_name: profile.company_name,
      } });
      if (persona !== current.persona_type) {
        await api(`/brand/workspaces/${current.id}/`, { method: "PATCH", body: { persona_type: persona } });
        await reload();
      }
    } catch (e) { setError(e.message); }
    setBusy((b) => ({ ...b, save: false }));
  }

  async function analyzeTone() {
    setBusy((b) => ({ ...b, tone: true })); setError("");
    try { setProfile(await api("/brand/profile/analyze-tone/", { method: "POST", workspace: current.id })); }
    catch (e) { setError(e.message); }
    setBusy((b) => ({ ...b, tone: false }));
  }

  async function suggestTopics() {
    setBusy((b) => ({ ...b, topics: true })); setError("");
    try { const out = await api("/brand/profile/suggest-topics/", { method: "POST", workspace: current.id }); setTopics(out.topics || []); }
    catch (e) { setError(e.message); }
    setBusy((b) => ({ ...b, topics: false }));
  }

  if (!profile || !current) return <main className="page"><p className="hint">Loading...</p></main>;

  return (
    <main className="page">
      <div className="hero"><h1>Voice and strategy — {current.name}</h1><p>What Postroom has learned for this avatar, and who it writes for.</p></div>

      <h2 className="section-title">Who are you writing as?</h2>
      <div className="card">
        <div className="persona-choice">
          {PERSONAS.map((p) => (
            <button type="button" key={p.value} className={`persona-card ${persona === p.value ? "on" : ""}`} onClick={() => setPersona(p.value)}>
              <h3>{p.title}</h3><p>{p.desc}</p>
            </button>
          ))}
        </div>
        {persona === "company" && (
          <>
            <label htmlFor="company">Company name</label>
            <input id="company" value={profile.company_name || ""} onChange={(e) => setProfile({ ...profile, company_name: e.target.value })} placeholder="Northwind" />
          </>
        )}
      </div>

      <h2 className="section-title">Your voice</h2>
      <div className="card">
        {profile.tone_summary ? (
          <>
            <p>{profile.tone_summary}</p>
            <div className="row">{(profile.tone_traits || []).map((t) => <span className="tag accent" key={t}>{t}</span>)}</div>
            {profile.tone_language && <p className="hint">{profile.tone_language}</p>}
            <p className="hint">Learned from {profile.tone_posts_analyzed} posted {profile.tone_posts_analyzed === 1 ? "post" : "posts"}
              {profile.tone_analyzed_at ? `, last updated ${new Date(profile.tone_analyzed_at).toLocaleDateString()}` : ""}.</p>
          </>
        ) : <p className="hint" style={{ marginTop: 0 }}>Mark a few posts as posted, then analyze them to learn this avatar's real tone.</p>}
        <button className="btn" onClick={analyzeTone} disabled={busy.tone}>
          {busy.tone ? <span className="spin" /> : profile.tone_summary ? "Re-analyze from posted posts" : "Analyze my posted posts"}
        </button>
        <label htmlFor="notes">Anything else about this voice</label>
        <textarea id="notes" rows={3} value={profile.voice_notes || ""} onChange={(e) => setProfile({ ...profile, voice_notes: e.target.value })} />
      </div>

      <h2 className="section-title">Audience and industry</h2>
      <div className="card">
        <label htmlFor="industry">Industry</label>
        <input id="industry" value={profile.industry || ""} onChange={(e) => setProfile({ ...profile, industry: e.target.value })} />
        <label htmlFor="audience">Target audience</label>
        <textarea id="audience" rows={2} value={profile.target_audience || ""} onChange={(e) => setProfile({ ...profile, target_audience: e.target.value })} />
        <label htmlFor="topics">Core topics</label>
        <input id="topics" value={profile.core_topics || ""} onChange={(e) => setProfile({ ...profile, core_topics: e.target.value })} />
        {error && <p className="error">{error}</p>}
        <button className="btn primary" style={{ marginTop: 14 }} onClick={save} disabled={busy.save}>
          {busy.save ? <span className="spin" /> : "Save"}
        </button>
      </div>

      <h2 className="section-title">Topic ideas</h2>
      <p className="hint">Based on this avatar's audience, industry, and what's performed well so far.</p>
      <button className="btn primary" onClick={suggestTopics} disabled={busy.topics}>
        {busy.topics ? <span className="spin" /> : "Suggest topics"}
      </button>
      {topics.map((t, i) => (
        <div className="card" key={i} style={{ borderLeft: "3px solid var(--accent)" }}>
          <h3>{t.title}</h3>
          <p>{t.angle}</p>
          <p className="hint">{t.why}</p>
        </div>
      ))}
    </main>
  );
}
