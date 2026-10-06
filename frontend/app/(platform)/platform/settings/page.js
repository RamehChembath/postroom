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
const CATEGORY_LABEL = { ai: "AI features", non_ai: "Non-AI features" };

function FeatureRow({ pf, onChange }) {
  const f = pf.feature;
  return (
    <div className="pf-feature-row">
      <div className="pf-feature-info">
        <label style={{ display: "flex", alignItems: "center", gap: 8, margin: 0 }}>
          <input type="checkbox" style={{ width: "auto" }} checked={pf.enabled} onChange={(e) => onChange({ ...pf, enabled: e.target.checked })} />
          <strong>{f.name}</strong>
        </label>
        {f.description && <div className="hint" style={{ margin: "2px 0 0 26px" }}>{f.description}</div>}
      </div>
      <div className="pf-feature-value">
        {f.value_kind === "quantity" && (
          <input type="number" min="0" style={{ width: 90 }} disabled={!pf.enabled}
                 value={pf.quantity ?? ""} placeholder="0"
                 onChange={(e) => onChange({ ...pf, quantity: e.target.value === "" ? null : Number(e.target.value) })} />
        )}
        {f.value_kind === "quantity" && <span className="hint">{f.unit}</span>}
        {f.value_kind === "tier" && (
          <select disabled={!pf.enabled} value={pf.tier || ""} onChange={(e) => onChange({ ...pf, tier: e.target.value })}>
            <option value="">—</option>
            {f.tier_options.map((t) => <option key={t} value={t}>{t.replace(/_/g, " ")}</option>)}
          </select>
        )}
      </div>
    </div>
  );
}

function PlanCard({ plan, onSaved, onDeleted, canDelete }) {
  const [form, setForm] = useState(plan);
  const [features, setFeatures] = useState(plan.features);
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);
  const [deleteError, setDeleteError] = useState(null);
  const [confirmingDelete, setConfirmingDelete] = useState(false);

  function set(field, value) { setForm((f) => ({ ...f, [field]: value })); setSaved(false); }

  async function save() {
    setBusy(true); setSaved(false);
    const updated = await api(`/platform/plan-configs/${plan.id}/`, {
      method: "PATCH",
      body: {
        name: form.name,
        price_monthly_inr: Number(form.price_monthly_inr),
        included_workspaces: Number(form.included_workspaces),
        max_workspaces: Number(form.max_workspaces),
        extra_workspace_price_inr: form.extra_workspace_price_inr === "" || form.extra_workspace_price_inr == null ? null : Number(form.extra_workspace_price_inr),
        ai_budget_usd_per_workspace: Number(form.ai_budget_usd_per_workspace),
        stripe_price_id: form.stripe_price_id,
        stripe_extra_avatar_price_id: form.stripe_extra_avatar_price_id,
        is_default_free: form.is_default_free,
      },
    });
    const featuresResult = await api(`/platform/plan-configs/${plan.id}/features/`, {
      method: "PATCH",
      body: features.map((pf) => ({ feature_id: pf.feature.id, enabled: pf.enabled, quantity: pf.quantity, tier: pf.tier })),
    });
    setForm(featuresResult);
    setFeatures(featuresResult.features);
    onSaved(featuresResult);
    setSaved(true);
    setBusy(false);
  }

  async function doDelete() {
    setDeleteError(null);
    try {
      await api(`/platform/plan-configs/${plan.id}/`, { method: "DELETE" });
      onDeleted(plan.id);
    } catch (e) {
      setDeleteError(e.message || "Couldn't delete this plan.");
    }
  }

  const grouped = { ai: features.filter((pf) => pf.feature.category === "ai"), non_ai: features.filter((pf) => pf.feature.category === "non_ai") };

  return (
    <div className="pf-card">
      <div className="row" style={{ alignItems: "center", justifyContent: "space-between" }}>
        <h2 style={{ margin: 0 }}>{form.name} <span className="hint" style={{ fontWeight: 400 }}>({plan.key}) · {plan.subscriber_count} subscriber{plan.subscriber_count === 1 ? "" : "s"}</span></h2>
        <div className="row" style={{ gap: 8 }}>
          {saved && <span className="pf-tag-ok">Saved</span>}
          {canDelete && !confirmingDelete && <button className="btn" onClick={() => setConfirmingDelete(true)}>Delete plan</button>}
          {confirmingDelete && (
            <>
              <button className="btn" style={{ borderColor: "#C0392B", color: "#C0392B" }} onClick={doDelete}>Confirm delete</button>
              <button className="btn" onClick={() => setConfirmingDelete(false)}>Cancel</button>
            </>
          )}
        </div>
      </div>
      {deleteError && <p className="error">{deleteError}</p>}

      <div className="row" style={{ gap: 14 }}>
        <div style={{ flex: 1, minWidth: 160 }}><label>Display name</label><input value={form.name} onChange={(e) => set("name", e.target.value)} /></div>
        <div style={{ flex: 1, minWidth: 160 }}><label>Price (₹/month)</label><input type="number" min="0" value={form.price_monthly_inr} onChange={(e) => set("price_monthly_inr", e.target.value)} /></div>
      </div>
      <div className="row" style={{ gap: 14 }}>
        <div style={{ flex: 1, minWidth: 160 }}><label>Included avatars</label><input type="number" min="1" value={form.included_workspaces} onChange={(e) => set("included_workspaces", e.target.value)} /></div>
        <div style={{ flex: 1, minWidth: 160 }}><label>Max avatars</label><input type="number" min="1" value={form.max_workspaces} onChange={(e) => set("max_workspaces", e.target.value)} /></div>
        <div style={{ flex: 1, minWidth: 160 }}><label>Extra avatar price (₹, blank = not allowed)</label><input type="number" min="0" value={form.extra_workspace_price_inr ?? ""} onChange={(e) => set("extra_workspace_price_inr", e.target.value)} /></div>
      </div>
      <div className="row" style={{ gap: 14 }}>
        <div style={{ flex: 1, minWidth: 160 }}><label>AI $ safety cap (per avatar/month)</label><input type="number" min="0" step="0.01" value={form.ai_budget_usd_per_workspace} onChange={(e) => set("ai_budget_usd_per_workspace", e.target.value)} /></div>
        <div style={{ flex: 1, minWidth: 160 }}>
          <label style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 14 }}>
            <input type="checkbox" style={{ width: "auto" }} checked={form.is_default_free} onChange={(e) => set("is_default_free", e.target.checked)} />
            Default fallback plan (canceled subscriptions land here)
          </label>
        </div>
      </div>
      <div className="row" style={{ gap: 14 }}>
        <div style={{ flex: 1, minWidth: 160 }}><label>Stripe price ID</label><input value={form.stripe_price_id} onChange={(e) => set("stripe_price_id", e.target.value)} placeholder="price_... (blank = free, no checkout)" /></div>
        <div style={{ flex: 1, minWidth: 160 }}><label>Stripe price ID (extra avatar add-on)</label><input value={form.stripe_extra_avatar_price_id} onChange={(e) => set("stripe_extra_avatar_price_id", e.target.value)} placeholder="price_..." /></div>
      </div>

      {["ai", "non_ai"].map((cat) => (
        <div key={cat} style={{ marginTop: 18 }}>
          <h3 className="pf-feature-group">{CATEGORY_LABEL[cat]}</h3>
          {grouped[cat].map((pf) => (
            <FeatureRow key={pf.id} pf={pf} onChange={(updated) => setFeatures((fs) => fs.map((x) => (x.id === updated.id ? updated : x)))} />
          ))}
        </div>
      ))}

      <button className="btn primary" style={{ marginTop: 16 }} onClick={save} disabled={busy}>
        {busy ? <span className="spin" /> : `Save ${form.name} plan`}
      </button>
    </div>
  );
}

function NewPlanForm({ onCreated, onCancel }) {
  const [name, setName] = useState("");
  const [price, setPrice] = useState("0");
  const [busy, setBusy] = useState(false);

  async function create() {
    if (!name.trim()) return;
    setBusy(true);
    const created = await api("/platform/plan-configs/", {
      method: "POST",
      body: { name, price_monthly_inr: Number(price) || 0, included_workspaces: 1, max_workspaces: 1, ai_budget_usd_per_workspace: 0 },
    });
    onCreated(created);
    setBusy(false);
  }

  return (
    <div className="pf-card" style={{ borderStyle: "dashed" }}>
      <h2 style={{ marginTop: 0 }}>New plan</h2>
      <div className="row" style={{ gap: 14 }}>
        <div style={{ flex: 1, minWidth: 160 }}><label>Name</label><input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Agency" /></div>
        <div style={{ flex: 1, minWidth: 160 }}><label>Price (₹/month)</label><input type="number" min="0" value={price} onChange={(e) => setPrice(e.target.value)} /></div>
      </div>
      <p className="hint">Starts with every feature off at quantity 0 — configure it after creating, same as any other plan.</p>
      <div className="row">
        <button className="btn primary" onClick={create} disabled={busy || !name.trim()}>{busy ? <span className="spin" /> : "Create plan"}</button>
        <button className="btn" onClick={onCancel}>Cancel</button>
      </div>
    </div>
  );
}

function PlanBuilderTab() {
  const [plans, setPlans] = useState(null);
  const [showNew, setShowNew] = useState(false);

  async function load() {
    const data = await api("/platform/plan-configs/");
    setPlans((data.results || data).sort((a, b) => a.order - b.order));
  }
  useEffect(() => { load(); }, []);

  if (!plans) return <p className="hint">Loading...</p>;

  return (
    <>
      <div className="row" style={{ justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <p className="hint" style={{ margin: 0 }}>Changes here take effect immediately for every user on that plan — no deploy, no restart. Create as many plans as you want.</p>
        {!showNew && <button className="btn primary" onClick={() => setShowNew(true)}>+ New plan</button>}
      </div>

      {showNew && (
        <NewPlanForm
          onCancel={() => setShowNew(false)}
          onCreated={(created) => { setPlans((ps) => [...ps, created]); setShowNew(false); }}
        />
      )}

      {plans.map((p) => (
        <PlanCard
          key={p.id}
          plan={p}
          canDelete={plans.length > 1}
          onSaved={(updated) => setPlans((ps) => ps.map((x) => (x.id === updated.id ? updated : x)))}
          onDeleted={(id) => setPlans((ps) => ps.filter((x) => x.id !== id))}
        />
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
