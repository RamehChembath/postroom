"use client";
import { useEffect, useState } from "react";
import { api } from "../../../../lib/api";

const TABS = [
  { key: "ai", label: "AI Provider", built: true },
  { key: "plans", label: "Plan Builder", built: true },
  { key: "email", label: "Email (SMTP)", built: false },
  { key: "payments", label: "Payments", built: false },
  { key: "branding", label: "Branding", built: false },
];

function AIProviderTab() {
  const [settings, setSettings] = useState(null);
  const [anthropicKey, setAnthropicKey] = useState("");
  const [openaiKey, setOpenaiKey] = useState("");
  const [model, setModel] = useState("");
  const [busy, setBusy] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [saved, setSaved] = useState(false);

  async function load() {
    const data = await api("/platform/ai-settings/");
    setSettings(data);
    setModel(data.default_claude_model || "");
  }
  useEffect(() => { load(); }, []);

  async function save() {
    setBusy(true); setSaved(false);
    const body = { default_claude_model: model };
    if (anthropicKey) body.anthropic_api_key = anthropicKey;
    if (openaiKey) body.openai_api_key = openaiKey;
    const data = await api("/platform/ai-settings/", { method: "PATCH", body });
    setSettings(data);
    setAnthropicKey(""); setOpenaiKey("");
    setSaved(true);
    setBusy(false);
  }

  async function test(provider) {
    setTestResult(null);
    const r = await api("/platform/ai-settings/test/", { method: "POST", body: { provider } });
    setTestResult({ provider, ...r });
  }

  if (!settings) return <p className="hint">Loading...</p>;

  return (
    <div className="pf-card">
      <div className="row" style={{ alignItems: "center" }}>
        <h2 style={{ margin: 0 }}>Anthropic API</h2>
        {settings.anthropic_configured && <span className="pf-tag-ok">Configured</span>}
      </div>
      <p className="hint">Used for all post drafting, tone analysis, replies and suggestions.</p>
      <label htmlFor="ak">API key</label>
      <input id="ak" type="password" placeholder={settings.anthropic_masked || "sk-ant-..."} value={anthropicKey} onChange={(e) => setAnthropicKey(e.target.value)} />
      <p className="hint">Get one from console.anthropic.com → Settings → API Keys. Field shows the saved value masked — type a new one to replace it.</p>

      <label htmlFor="model">Default model</label>
      <input id="model" placeholder={settings.effective_claude_model} value={model} onChange={(e) => setModel(e.target.value)} />
      <p className="hint">Leave blank to use the server default ({settings.effective_claude_model}).</p>

      <hr style={{ border: 0, borderTop: "1px solid #EEF0F2", margin: "18px 0" }} />

      <h2 style={{ margin: "0 0 4px" }}>OpenAI API {settings.openai_configured && <span className="pf-tag-ok">Configured</span>}</h2>
      <p className="hint">Used for image generation.</p>
      <label htmlFor="ok">API key</label>
      <input id="ok" type="password" placeholder={settings.openai_masked || "sk-..."} value={openaiKey} onChange={(e) => setOpenaiKey(e.target.value)} />

      <div className="row" style={{ marginTop: 18 }}>
        <button className="btn primary" onClick={save} disabled={busy}>{busy ? <span className="spin" /> : "Save AI settings"}</button>
        <button className="btn" onClick={() => test("anthropic")}>Test Anthropic</button>
        <button className="btn" onClick={() => test("openai")}>Test OpenAI</button>
      </div>
      {saved && <p className="success-text">Saved.</p>}
      {testResult && (
        <p className={testResult.success ? "success-text" : "error"}>
          {testResult.provider}: {testResult.success ? "✓ " : "✗ "}{testResult.detail}
        </p>
      )}
    </div>
  );
}

function PlanCard({ plan, onSaved }) {
  const [form, setForm] = useState(plan);
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);

  function set(field, value) { setForm((f) => ({ ...f, [field]: value })); setSaved(false); }

  async function save() {
    setBusy(true);
    const updated = await api(`/platform/plan-configs/${plan.id}/`, {
      method: "PATCH",
      body: {
        name: form.name,
        price_monthly_inr: Number(form.price_monthly_inr),
        included_workspaces: Number(form.included_workspaces),
        max_workspaces: Number(form.max_workspaces),
        extra_workspace_price_inr: form.extra_workspace_price_inr === "" ? null : Number(form.extra_workspace_price_inr),
        ai_enabled: form.ai_enabled,
        ai_budget_usd_per_workspace: Number(form.ai_budget_usd_per_workspace),
        stripe_price_id: form.stripe_price_id,
        stripe_extra_avatar_price_id: form.stripe_extra_avatar_price_id,
      },
    });
    setForm(updated);
    onSaved(updated);
    setSaved(true);
    setBusy(false);
  }

  return (
    <div className="pf-card">
      <div className="row" style={{ alignItems: "center", justifyContent: "space-between" }}>
        <h2 style={{ margin: 0 }}>{form.name} <span className="hint" style={{ fontWeight: 400 }}>({plan.key})</span></h2>
        {saved && <span className="pf-tag-ok">Saved</span>}
      </div>

      <div className="row" style={{ gap: 14 }}>
        <div style={{ flex: 1, minWidth: 160 }}>
          <label>Display name</label>
          <input value={form.name} onChange={(e) => set("name", e.target.value)} />
        </div>
        <div style={{ flex: 1, minWidth: 160 }}>
          <label>Price (₹/month)</label>
          <input type="number" min="0" value={form.price_monthly_inr} onChange={(e) => set("price_monthly_inr", e.target.value)} />
        </div>
      </div>

      <div className="row" style={{ gap: 14 }}>
        <div style={{ flex: 1, minWidth: 160 }}>
          <label>Included avatars</label>
          <input type="number" min="1" value={form.included_workspaces} onChange={(e) => set("included_workspaces", e.target.value)} />
        </div>
        <div style={{ flex: 1, minWidth: 160 }}>
          <label>Max avatars</label>
          <input type="number" min="1" value={form.max_workspaces} onChange={(e) => set("max_workspaces", e.target.value)} />
        </div>
        <div style={{ flex: 1, minWidth: 160 }}>
          <label>Extra avatar price (₹, blank = not allowed)</label>
          <input type="number" min="0" value={form.extra_workspace_price_inr ?? ""} onChange={(e) => set("extra_workspace_price_inr", e.target.value)} />
        </div>
      </div>

      <div className="row" style={{ gap: 14, alignItems: "flex-end" }}>
        <div style={{ flex: 1, minWidth: 160 }}>
          <label style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 14 }}>
            <input type="checkbox" style={{ width: "auto" }} checked={form.ai_enabled} onChange={(e) => set("ai_enabled", e.target.checked)} />
            AI features enabled
          </label>
        </div>
        <div style={{ flex: 1, minWidth: 160 }}>
          <label>AI budget ($/avatar/month)</label>
          <input type="number" min="0" step="0.01" value={form.ai_budget_usd_per_workspace} onChange={(e) => set("ai_budget_usd_per_workspace", e.target.value)} disabled={!form.ai_enabled} />
        </div>
      </div>

      <div className="row" style={{ gap: 14 }}>
        <div style={{ flex: 1, minWidth: 160 }}>
          <label>Stripe price ID (base plan)</label>
          <input value={form.stripe_price_id} onChange={(e) => set("stripe_price_id", e.target.value)} placeholder="price_..." />
        </div>
        <div style={{ flex: 1, minWidth: 160 }}>
          <label>Stripe price ID (extra avatar add-on)</label>
          <input value={form.stripe_extra_avatar_price_id} onChange={(e) => set("stripe_extra_avatar_price_id", e.target.value)} placeholder="price_..." />
        </div>
      </div>

      <button className="btn primary" style={{ marginTop: 16 }} onClick={save} disabled={busy}>
        {busy ? <span className="spin" /> : `Save ${form.name} plan`}
      </button>
    </div>
  );
}

function PlanBuilderTab() {
  const [plans, setPlans] = useState(null);

  async function load() {
    const data = await api("/platform/plan-configs/");
    setPlans((data.results || data).sort((a, b) => a.order - b.order));
  }
  useEffect(() => { load(); }, []);

  if (!plans) return <p className="hint">Loading...</p>;

  return (
    <>
      <p className="hint" style={{ marginTop: 0, marginBottom: 16 }}>
        Changes here take effect immediately for every user on that plan — no deploy, no restart.
      </p>
      {plans.map((p) => (
        <PlanCard key={p.id} plan={p} onSaved={(updated) => setPlans((ps) => ps.map((x) => (x.id === updated.id ? updated : x)))} />
      ))}
    </>
  );
}

export default function PlatformSettingsPage() {
  const [tab, setTab] = useState("ai");
  const active = TABS.find((t) => t.key === tab);

  return (
    <main>
      <h1 className="pf-h1">Platform Settings</h1>
      <p className="pf-sub">Configure integrations from one place. Changes save to the database immediately. Visible to super-admin only.</p>

      <div className="pf-tabs">
        {TABS.map((t) => (
          <button key={t.key} className={`pf-tab ${tab === t.key ? "on" : ""}`} onClick={() => setTab(t.key)}>{t.label}</button>
        ))}
      </div>

      {tab === "ai" && <AIProviderTab />}
      {tab === "plans" && <PlanBuilderTab />}
      {!active.built && (
        <div className="pf-card"><p className="pf-soon">{active.label} isn't wired up yet — this tab is a placeholder for when it is.</p></div>
      )}
    </main>
  );
}
