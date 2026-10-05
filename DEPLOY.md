# Deploying Postroom on Contabo

This assumes a fresh Ubuntu 22.04/24.04 Contabo VPS and that postroom.in's DNS
is yours to edit.

## 0. Put Cloudflare in front of the site (free plan)
This is the piece that actually protects against spam/bot traffic and basic DDoS —
not AWS CloudFront, which is just a CDN. Cloudflare's free plan gives you:
- Automatic DDoS mitigation and a basic WAF
- "Bot Fight Mode" (free) — challenges traffic that looks automated
- Turnstile — a free CAPTCHA alternative, already wired into registration below

Steps:
1. Sign up at cloudflare.com (free plan), add `postroom.in`, and follow its
   instructions to change your domain's nameservers to Cloudflare's.
2. In the Cloudflare dashboard, add DNS records for `postroom.in`, `www`, and
   `api` all pointing at your VPS's IP, with the orange "Proxied" cloud turned
   **on** (this is what routes traffic through Cloudflare instead of straight
   to your server).
3. Under Security -> Bots, turn on Bot Fight Mode.
4. Under Security -> Turnstile, add a site for `postroom.in`, choose the
   "Managed" widget type, and copy its Site Key and Secret Key — you'll need
   both below. (Exact free-tier feature names and limits change over time;
   check your dashboard for what's currently included.)

## 1. Point DNS at the VPS
If you did step 0, your DNS is already pointed at the VPS through Cloudflare —
skip to step 2. If you're not using Cloudflare, create three A records instead,
pointing straight at your VPS's IP: `postroom.in`, `www.postroom.in`, `api.postroom.in`.

Wait for propagation (`dig postroom.in` should return the right IP) before step 5.

## 2. Install Docker on the VPS
```bash
ssh root@your-vps-ip
curl -fsSL https://get.docker.com | sh
apt install -y docker-compose-plugin
```

## 3. Copy the project to the VPS
From your machine:
```bash
scp -r postroom root@your-vps-ip:/opt/postroom
ssh root@your-vps-ip
cd /opt/postroom
```

## 4. Configure environment
```bash
cp .env.example .env                       # compose-level vars (Postgres creds, API base URL)
cp backend/.env.example backend/.env        # Django/Celery/AI vars
nano .env backend/.env
```
Fill in for real:
- `DJANGO_SECRET_KEY` — any long random string (`openssl rand -hex 32`)
- `POSTGRES_PASSWORD` — same value in both files
- `ANTHROPIC_API_KEY`, `OPENAI_API_KEY` — your keys
- `EMAIL_HOST` / `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` — from Resend, SendGrid, or any SMTP provider; sends posting-room reminders and password-reset emails
- `COOKIE_DOMAIN=.postroom.in` — so the login cookie is sent from the frontend to `api.postroom.in`
- `STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY` — from your Stripe Dashboard
- `STRIPE_PRICE_BASE`, `STRIPE_PRICE_PRO`, `STRIPE_PRICE_PRO_EXTRA_AVATAR` — create three Stripe Prices first (₹99/mo, ₹199/mo, and ₹100/mo licensed-per-unit for the extra-avatar add-on — see `.env.example` for details), then copy their price ids here
- `TURNSTILE_SECRET_KEY` in `backend/.env`, and `NEXT_PUBLIC_TURNSTILE_SITE_KEY` in the frontend's env — both from step 0
- `NEXT_PUBLIC_API_BASE=https://api.postroom.in/api` in the root `.env`

**Before relying on this for real recurring INR billing**: India has specific
RBI rules around recurring/auto-debit card payments that have changed Stripe's
support for this over time, and I can't verify the current status from here.
Confirm directly with Stripe (or your payment provider) that recurring INR
subscriptions are supported for your business before launching — this may
affect checkout flow details, not just the price currency.

After first deploy, register the webhook in the Stripe Dashboard (Developers → Webhooks → Add endpoint): URL `https://api.postroom.in/api/billing/webhook/`, events `checkout.session.completed`, `customer.subscription.updated`, `customer.subscription.deleted`, `invoice.payment_failed`. Copy the signing secret it gives you into `STRIPE_WEBHOOK_SECRET` in `backend/.env` and restart the backend container.

## 5. First launch — get a TLS certificate
Nginx's config expects a certificate that doesn't exist yet, so bring it up in two passes.

**Pass 1 — HTTP only, to prove domain ownership:**
```bash
# Temporarily comment out the "listen 443" server blocks in nginx/conf.d/postroom.conf,
# leaving only the port-80 block, then:
docker compose up -d nginx
docker compose run --rm certbot certonly --webroot -w /var/www/certbot \
  -d postroom.in -d www.postroom.in -d api.postroom.in \
  --email you@postroom.in --agree-tos --no-eff-email
```

**Pass 2 — restore the full config and bring everything up:**
```bash
# Uncomment the 443 server blocks again
docker compose up -d --build
docker compose logs -f backend   # watch migrations run cleanly
```

Certbot's container auto-renews the certificate every 12 hours when due; no further action needed.

## 6. Create an admin user (optional, for Django admin at /admin/)
```bash
docker compose exec backend python manage.py createsuperuser
```

## 7. Verify
- https://postroom.in — the app
- https://api.postroom.in/admin/ — Django admin
- `docker compose logs -f celery_beat` — should show the daily reminder task registered

## Updating later
```bash
cd /opt/postroom
git pull   # or re-scp your changes
docker compose up -d --build
```

## Day-to-day operations
- **Backups**: `docker compose exec db pg_dump -U postroom postroom > backup.sql` — put this on a cron job and copy it off the VPS.
- **Logs**: `docker compose logs -f backend celery_worker celery_beat`
- **Scaling later**: all state is in Postgres/Redis volumes; moving to a bigger VPS or a managed Postgres later is a matter of restoring the dump.
