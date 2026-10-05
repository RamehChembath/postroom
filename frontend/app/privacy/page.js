export const metadata = { title: "Privacy Policy — Postroom" };

export default function PrivacyPage() {
  return (
    <main className="page" style={{ maxWidth: 720 }}>
      <div className="card" style={{ borderColor: "var(--signal)", background: "var(--accent-soft)" }}>
        <p style={{ margin: 0, fontSize: "0.85rem" }}>
          <strong>Template — not legal advice.</strong> Replace the bracketed items and have a
          lawyer review this before launch, especially if you'll have users in the EU/UK (GDPR)
          or California (CCPA) — this draft doesn't cover those obligations in full.
        </p>
      </div>

      <h1>Privacy Policy</h1>
      <p className="hint">Last updated: [date]</p>

      <h2 className="section-title">What we collect</h2>
      <p>Account info (email, name), the content you create or paste in (drafts, past posts for
        tone analysis, comments you log), usage data (which features you use, how often), and
        payment info (handled by Stripe — we never see your full card number).</p>

      <h2 className="section-title">How we use it</h2>
      <p>To provide the service: generating drafts and suggestions (sent to Anthropic and OpenAI
        as needed), sending posting reminders, processing payments, and improving the product.
        We don't sell your data.</p>

      <h2 className="section-title">Third parties we share data with</h2>
      <ul>
        <li><strong>Anthropic (Claude)</strong> — post content and context you provide, to generate drafts and suggestions.</li>
        <li><strong>OpenAI</strong> — prompts derived from your posts, to generate images.</li>
        <li><strong>Stripe</strong> — billing information, to process payments.</li>
        <li><strong>[Your email provider]</strong> — your email address, to send reminders and account emails.</li>
      </ul>
      <p>We don't control how these providers handle data beyond what's in their own privacy
        policies and our agreements with them — review those directly for details.</p>

      <h2 className="section-title">Data retention</h2>
      <p>We keep your account data as long as your account is active. You can request deletion of
        your account and associated data by contacting [support email]; some data may be retained
        where required for legal or billing records.</p>

      <h2 className="section-title">Security</h2>
      <p>We use industry-standard measures (encrypted connections, hashed passwords, httpOnly
        session cookies) but no system is perfectly secure — we can't guarantee absolute security.</p>

      <h2 className="section-title">Your rights</h2>
      <p>Depending on where you live, you may have rights to access, correct, or delete your
        data, or to object to certain processing. Contact [support email] to exercise these.</p>

      <h2 className="section-title">Changes</h2>
      <p>We'll post updates here with a new "last updated" date.</p>

      <h2 className="section-title">Contact</h2>
      <p>[support email]</p>
    </main>
  );
}
