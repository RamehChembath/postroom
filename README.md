# Postroom

A LinkedIn strategy, writing, posting, and growth platform.

## Architecture
- **backend/** — Django + Django REST Framework + Postgres + Celery. All data, AI
  orchestration (Claude for writing/reasoning, OpenAI for images), and scheduled
  reminders live here.
- **frontend/** — Next.js (App Router). Talks to the backend over REST with JWT auth.
- **nginx/** — reverse proxy + TLS termination for both.
- **docker-compose.yml** — runs the whole stack together.

## How the six pieces of the product map to the code

| Feature | Backend | Frontend |
|---|---|---|
| 1. Personalize | `brand` app: `BrandProfile`, website summarizer, onboarding preview, tone analysis | `/onboarding`, `/strategy` |
| 2. Strategy & calendar | `content` app: `ContentPlan`, `PlannedItem`, `generate_calendar()` | `/plan` |
| 3. Draft + image generation | `content.services.generate_draft_for_item()`, `generate_post_image()` | `/plan` (approve) → `/posts` |
| 4. Posting room + reminders | `Post.status`, `notifications` app (Celery beat, daily email) | `/posting-room` |
| 5. Engagement loop | `engagement` app: `Comment`, `suggest_reply()`, `suggest_next_step()` | `/posts/[id]` |
| 6. Dashboard | `content.views.DashboardView`, `analyze_performance()` | `/dashboard` |
| 7. Goals | `brand` app: `Goal` + progress calc | `/goals` |
| Billing & plan limits | `billing` app: `Subscription`, `UsageCounter`, Stripe checkout/portal/webhook | `/billing` |
| Auth security | httpOnly-cookie JWT (`accounts/cookies.py`), token blacklist on logout | login/register, no UI |
| Password reset | `accounts` app: email + token flow | `/forgot-password`, `/reset-password/[uid]/[token]` |
| Email verification | `accounts` app: separate token generator from password reset, non-blocking | `/verify-email/[uid]/[token]`, banner in the sidebar |
| Spam protection | Cloudflare (DNS/WAF/Bot Fight Mode) in front of the site + Turnstile on signup | registration form |
| Admin / monitoring | Django admin, customized: user list shows plan/verified/avatar count, editable subscription, usage reset action | `/admin/` (staff accounts only — separate from app logins) |

## Local development (without Docker)
**Backend:**
```bash
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # set USE_SQLITE=true for a quick local DB
python manage.py migrate
python manage.py runserver
```
**Frontend:**
```bash
cd frontend
npm install
echo "NEXT_PUBLIC_API_BASE=http://localhost:8000/api" > .env.local
npm run dev
```
**Celery (for reminders), separately:**
```bash
celery -A postroom worker --loglevel=info
celery -A postroom beat --loglevel=info
```

## Production (Contabo)
See `DEPLOY.md`.

## What's in place for selling this
- **Plan tiers** (`billing/plans.py`):
  | Plan | Price | Avatars | AI |
  |---|---|---|---|
  | Free | ₹0 | 1 | off entirely — manage/log posts only, no drafting |
  | Base | ₹99/mo | 1 (hard cap, no add-ons) | $3/month budget |
  | Pro | ₹199/mo | up to 20, +₹100/mo each beyond the first | $3/month budget **per avatar** |
- **Real dollar-cost metering, not a flat action count**: every Claude/OpenAI call returns actual token usage, which is converted to USD using a per-model pricing table and added to that *specific avatar's* monthly spend (`billing/models.WorkspaceUsage`). Two avatars on the same Pro account have fully independent $3 budgets — tested directly: draining avatar A's budget doesn't touch avatar B's. The token-price constants in `aiengine/providers.py` are illustrative and need checking against Anthropic's/OpenAI's current pricing.
- **Stripe billing**, including the extra-avatar add-on: checkout, a billing portal link, a webhook handler, and `billing/stripe_billing.py`, which keeps a Pro subscription's "extra avatar" line item quantity in sync with how many avatars actually exist — adding/removing an avatar updates Stripe automatically. Tested end-to-end with constructed webhook events and a stubbed Stripe client; confirmed real Stripe network failures are caught and logged without blocking avatar creation.
- **httpOnly-cookie auth**: tokens never touch `localStorage` or JS — confirmed via test that no token appears in any response body, that cookie-only requests authenticate, and that a request with no cookie is rejected. Logout blacklists the refresh token server-side, not just clears cookies.
- **Password reset**: email + one-time token flow, tested end-to-end (including no-email-enumeration and one-time token use).
- **Rate limiting**: auth endpoints throttled to 20/hour (brute-force protection); every endpoint additionally capped at 300/min per user as a general ceiling.
- **Terms of Service & Privacy Policy pages** (`/terms`, `/privacy`) — these are templates, not legal advice; replace the bracketed placeholders and have a lawyer review before launch.

## Updating AI keys without SSH
Django admin → **AI provider settings** lets you set (or rotate) the Anthropic
and OpenAI API keys from a web page — no server access, no redeploy, takes
effect immediately. Leave a field blank there to fall back to whatever's in
`backend/.env`; fill it in to override. This is the one setting I specifically
pulled out of `.env` and into the database for exactly this reason — it's the
value most likely to need changing without a code change.

## The platform admin dashboard
A real, custom-built ops dashboard at `/platform` in the main app (Next.js, not Django templates) — staff-only, gated by `is_staff` on login. This is separate from Django's `/admin/` (below), which is still there for raw data management.
- **Dashboard** (`/platform`) — condensed 30-day overview
- **Tenants** (`/platform/tenants`) — every account, plan, status, avatar count
- **Costs & Billing** (`/platform/costs`) — the real one: a daily spend chart, cost by purpose, cost by model, per-tenant margin (fees billed − AI cost, converted via `USD_TO_INR` in `platform_admin/views.py` — update that to your real rate), and the 10 most expensive individual AI calls. Every number here comes from `billing.AIUsageEvent`, a row logged on every single Claude/OpenAI call with its purpose, model, and exact cost — not an estimate.
- **Settings** (`/platform/settings`) — AI Provider (same as Django admin's version, just nicer) and **Plan Builder**: create/delete as many plans as you want (not fixed to Free/Base/Pro), and configure each one's full feature matrix — 13 features (7 AI, 4 non-AI, split across quantity quotas like "10 drafts/month", quality tiers like smart day scheduling, and plain on/off) individually enabled and sized per plan. Takes effect for every user on that plan immediately — no deploy, no restart. Tested directly: created a brand-new plan from scratch, gave it a 1-draft quota, confirmed a real user got blocked on their 2nd draft, then raised the quota live and confirmed the same user immediately succeeded.
  - Deleting a plan is guarded: refuses if it still has active subscribers, or if it's the designated free-fallback plan.
  - The feature catalog itself (the 13 definitions) lives in `billing.Feature`, editable via Django admin at `/admin/billing/feature/` if you need to add a brand-new capability — the Plan Builder UI configures each plan's *values* against that catalog, not the catalog itself.
- Email/Payments/Branding tabs are placeholders, honestly labeled "not wired up yet" rather than faked.

## The admin panel
Django admin at `/admin/` — a separate URL, gated by `is_staff`/`is_superuser` on
the *same* user table the app uses (not a separate account system). Nobody gets
staff access by registering normally; you grant it yourself:
```bash
docker compose exec backend python manage.py createsuperuser
```
From there: the User list shows email-verified status, plan, and avatar count at
a glance; opening a user shows their Subscription and AccountProfile inline,
with plan/status directly editable (useful for comping someone or fixing a
stuck Stripe state by hand); a "Reset this month's AI usage" bulk action is
available from the Subscription list for support cases.

## Still worth doing before a public launch
- **LinkedIn posting is still copy-paste**, not automatic. LinkedIn's API allows posting via OAuth ("Share on LinkedIn"), but reading others' feeds, reach/impressions, or comments isn't available to personal apps — the manual logging in the Posting Room and `/posts/[id]` is a deliberate design choice, not a gap to fix.
- **Image generation** calls OpenAI synchronously inside the request/response cycle for drafts — for real traffic, move this to a Celery task so draft approval doesn't block on image generation latency.
- **Set real Stripe keys and products** before going live: create the Pro/Team products and prices in your Stripe Dashboard, put their price ids in `backend/.env` (`STRIPE_PRICE_PRO`, `STRIPE_PRICE_TEAM`), and register the webhook endpoint (`https://api.postroom.in/api/billing/webhook/`) in the Stripe Dashboard to get a real `STRIPE_WEBHOOK_SECRET`.
