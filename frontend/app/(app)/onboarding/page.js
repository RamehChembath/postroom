"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "../../../lib/api";
import { useWorkspace } from "../../../lib/workspace";

const STEPS = ["Company", "Industry & audience", "Past posts", "Preview"];

export default function OnboardingPage() {
  const router = useRouter();
  const { current } = useWorkspace();
  const [step, setStep] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [form, setForm] = useState({ company_website: "", industry: "", target_audience: "", core_topics: "" });
  const [pastPosts, setPastPosts] = useState([{ text: "", likes: "" }]);
  const [preview, setPreview] = useState(null);

  function updateField(k, v) { setForm((f) => ({ ...f, [k]: v })); }
  function updatePost(i, k, v) { setPastPosts((p) => p.map((x, idx) => (idx === i ? { ...x, [k]: v } : x))); }
  function addPost() { setPastPosts((p) => [...p, { text: "", likes: "" }]); }

  async function next() {
    setError(""); setBusy(true);
    try {
      if (step === 0) {
        await api("/brand/profile/", { method: "PATCH", body: { company_website: form.company_website }, workspace: current.id });
        if (form.company_website) await api("/brand/profile/analyze-website/", { method: "POST", workspace: current.id });
      } else if (step === 1) {
        await api("/brand/profile/", { method: "PATCH", body: { industry: form.industry, target_audience: form.target_audience, core_topics: form.core_topics }, workspace: current.id });
      } else if (step === 2) {
        for (const p of pastPosts) {
          if (p.text.trim()) await api("/brand/past-posts/", { method: "POST", body: { text: p.text, likes: Number(p.likes) || 0 }, workspace: current.id });
        }
        const out = await api("/brand/profile/preview/", { method: "POST", workspace: current.id });
        setPreview(out);
      } else {
        await api("/brand/profile/", { method: "PATCH", body: { onboarding_completed: true }, workspace: current.id });
        router.push("/strategy");
        return;
      }
      setStep((s) => s + 1);
    } catch (err) {
      setError(err.message);
    }
    setBusy(false);
  }

  if (!current) return <main className="page"><p className="hint">Loading...</p></main>;

  return (
    <main className="page">
      <div className="hero"><h1>Let's personalize {current.name}</h1><p>Step {step + 1} of {STEPS.length}: {STEPS[step]}</p></div>

      {step === 0 && (
        <div className="card">
          <label htmlFor="website">Your company website (optional)</label>
          <input id="website" placeholder="https://example.com" value={form.company_website} onChange={(e) => updateField("company_website", e.target.value)} />
          <p className="hint">We'll read it and use it as writing context — what you do, who you serve, how you talk about yourselves.</p>
        </div>
      )}

      {step === 1 && (
        <div className="card">
          <label htmlFor="industry">Industry</label>
          <input id="industry" placeholder="B2B SaaS, sales and customer success" value={form.industry} onChange={(e) => updateField("industry", e.target.value)} />
          <label htmlFor="audience">Target audience</label>
          <textarea id="audience" rows={3} placeholder="VPs of Sales and CS leaders at mid-market SaaS companies" value={form.target_audience} onChange={(e) => updateField("target_audience", e.target.value)} />
          <label htmlFor="topics">Core topics</label>
          <input id="topics" placeholder="onboarding, forecasting, renewals, hiring" value={form.core_topics} onChange={(e) => updateField("core_topics", e.target.value)} />
        </div>
      )}

      {step === 2 && (
        <div className="card">
          <p className="hint" style={{ marginTop: 0 }}>Paste a few of your own past LinkedIn posts. This is what teaches Postroom your real tone.</p>
          {pastPosts.map((p, i) => (
            <div key={i} style={{ marginBottom: 14, paddingBottom: 14, borderBottom: "1px solid var(--line)" }}>
              <label>Post {i + 1}</label>
              <textarea rows={4} value={p.text} onChange={(e) => updatePost(i, "text", e.target.value)} />
              <label>Likes it got (optional)</label>
              <input type="number" min="0" value={p.likes} onChange={(e) => updatePost(i, "likes", e.target.value)} style={{ maxWidth: 140 }} />
            </div>
          ))}
          <button type="button" className="btn small" onClick={addPost}>Add another post</button>
        </div>
      )}

      {step === 3 && (
        <div className="card">
          {preview ? (
            <>
              <p className="hint" style={{ marginTop: 0 }}>Here's what writing in your voice could look like:</p>
              <div className="card" style={{ background: "var(--paper)" }}>
                <p style={{ whiteSpace: "pre-line" }}>{preview.sample_post}</p>
              </div>
              <p className="hint">{preview.notes}</p>
              <p className="hint"><strong>{preview.disclaimer}</strong></p>
            </>
          ) : <p className="hint">Generating a preview...</p>}
        </div>
      )}

      {error && <p className="error">{error}</p>}
      <div className="row" style={{ marginTop: 16 }}>
        {step > 0 && <button className="btn" onClick={() => setStep((s) => s - 1)} disabled={busy}>Back</button>}
        <button className="btn primary" onClick={next} disabled={busy}>
          {busy ? <span className="spin" /> : step === STEPS.length - 1 ? "Go to Strategy" : "Continue"}
        </button>
      </div>
    </main>
  );
}
