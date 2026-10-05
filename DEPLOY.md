# Deploying Postroom on Contabo, via GitHub

This assumes a fresh Ubuntu 22.04/24.04 Contabo VPS and that postroom.in's DNS
is yours to edit. The flow: get it running once by hand (so you can sort out
TLS and confirm everything works), then wire up GitHub Actions so every push
to `main` after that deploys itself automatically.

## 0. Put Cloudflare in front of the site (free plan)
This is the piece that actually protects against spam/bot traffic and basic DDoS —
not AWS CloudFront, which is just a CDN. Cloudflare's free plan gives you:
- Automatic DDoS mitigation and a basic WAF
- "Bot Fight Mode" (free) — challenges traffic that looks automated
- Turnstile — a free CAPTCHA alternative, already wired into registration

Steps:
1. Sign up at cloudflare.com (free plan), add `postroom.in`, and follow its
   instructions to change your domain's nameservers to Cloudflare's.
2. In the Cloudflare dashboard, add DNS records for `postroom.in`, `www`, and
   `api` all pointing at your VPS's IP, with the orange "Proxied" cloud turned
   **on**.
3. Under Security -> Bots, turn on Bot Fight Mode.
4. Under Security -> Turnstile, add a site for `postroom.in`, "Managed" widget
   type, and copy its Site Key and Secret Key — needed below. (Exact free-tier
   feature names/limits change over time; check your dashboard.)

## 1. Point DNS at the VPS
Already done if you completed step 0. Otherwise, create three A records
pointing straight at your VPS's IP: `postroom.in`, `www.postroom.in`, `api.postroom.in`.
Wait for propagation (`dig postroom.in`) before continuing.

## 2. Create the GitHub repo and push the code
From your own machine, inside the unzipped `postroom/` folder (it's already a
git repo with a sensible `.gitignore` — no secrets or build artifacts in it):
```bash
# Create an empty repo on github.com first (no README/license — you already have files), then:
git remote add origin https://github.com/<you>/postroom.git
git branch -M main
git push -u origin main
```

## 3. Install Docker on the VPS and clone the repo
```bash
ssh root@your-vps-ip
curl -fsSL https://get.docker.com | sh
apt install -y docker-compose-plugin git
git clone https://github.com/<you>/postroom.git /opt/postroom
cd /opt/postroom
```

## 4. Configure environment
```bash
cp .env.example .env                       # compose-level vars
cp backend/.env.example backend/.env        # Django/Celery/AI/Stripe vars
nano .env backend/.env
```
Fill in for real:
- `DJANGO_SECRET_KEY` — any long random string (`openssl rand -hex 32`)
- `POSTGRES_PASSWORD` — same value in both files
- `ANTHROPIC_API_KEY`, `OPENAI_API_KEY` — your keys
- `EMAIL_HOST` / `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` — sends reminders and account emails
- `COOKIE_DOMAIN=.postroom.in`
- `STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY`, `STRIPE_PRICE_BASE`, `STRIPE_PRICE_PRO`, `STRIPE_PRICE_PRO_EXTRA_AVATAR` — see `backend/.env.example` for what each Stripe Price should be
- `TURNSTILE_SECRET_KEY` in `backend/.env`; `NEXT_PUBLIC_TURNSTILE_SITE_KEY` in the root `.env` — both from step 0
- `NEXT_PUBLIC_API_BASE=https://api.postroom.in/api` in the root `.env`
- `GHCR_OWNER=<your-github-username-lowercase>` in the root `.env` — used later once CI is wired up (step 8); harmless to set now

**Before relying on this for real recurring INR billing**: India has specific
RBI rules around recurring/auto-debit card payments that have changed Stripe's
support for this over time, and I can't verify the current status from here.
Confirm directly with Stripe that recurring INR subscriptions are supported
for your business before launching.

After first deploy (step 6), register the webhook in the Stripe Dashboard
(Developers → Webhooks → Add endpoint): URL `https://api.postroom.in/api/billing/webhook/`,
events `checkout.session.completed`, `customer.subscription.updated`,
`customer.subscription.deleted`, `invoice.payment_failed`. Copy the signing
secret into `STRIPE_WEBHOOK_SECRET` in `backend/.env` and restart the backend.

## 5. First launch (manual, local build) — get a TLS certificate
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

**Pass 2 — restore the full config and bring everything up (builds locally this first time):**
```bash
# Uncomment the 443 server blocks again
docker compose up -d --build
docker compose logs -f backend   # watch migrations run cleanly
```

## 6. Create an admin user and verify
```bash
docker compose exec backend python manage.py createsuperuser
```
- https://postroom.in — the app
- https://api.postroom.in/admin/ — Django admin
- `docker compose logs -f celery_beat` — should show the daily reminder task registered

Everything above gets you a working site deployed by hand. The rest of this
guide wires up GitHub Actions so every future `git push` deploys itself.

## 7. Let GitHub Container Registry images be pulled on the VPS
GHCR packages default to private. Either make them public after the first
push (GitHub → your profile → Packages → postroom-backend/postroom-frontend →
Package settings → Change visibility), or authenticate the VPS once:
```bash
# A classic PAT with the read:packages scope, created at github.com/settings/tokens
docker login ghcr.io -u <your-github-username>
```
This is a one-time step — Docker remembers it in `~/.docker/config.json` on the VPS.

## 8. Set up a deploy key and GitHub secrets
```bash
# On the VPS:
ssh-keygen -t ed25519 -f ~/.ssh/postroom_deploy -N ""
cat ~/.ssh/postroom_deploy.pub >> ~/.ssh/authorized_keys
cat ~/.ssh/postroom_deploy        # copy this private key
```
In your GitHub repo → Settings → Secrets and variables → Actions:

| Type | Name | Value |
|---|---|---|
| Secret | `VPS_HOST` | your VPS IP or hostname |
| Secret | `VPS_USER` | `root` (or whatever user you used above) |
| Secret | `VPS_SSH_KEY` | the private key you just copied |
| Variable | `NEXT_PUBLIC_API_BASE` | `https://api.postroom.in/api` |
| Variable | `NEXT_PUBLIC_TURNSTILE_SITE_KEY` | from step 0 |

(`GITHUB_TOKEN` used in the workflow is automatic — nothing to add for that one.)

## 9. Trigger the pipeline
Push anything to `main`, or go to the Actions tab → "Build and deploy" → Run
workflow. It will: run Django's checks, build both images, push them to
`ghcr.io/<you>/postroom-backend` and `-frontend`, then SSH into the VPS and run
```bash
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```
From here on, **every push to `main` deploys automatically** — no more manual
`docker compose up --build` on the VPS.

## Updating later
Just `git push`. To redeploy without a code change (e.g. after editing env
vars), re-run the workflow manually from the Actions tab.

## Day-to-day operations
- **Backups**: `docker compose exec db pg_dump -U postroom postroom > backup.sql` — put this on a cron job and copy it off the VPS.
- **Logs**: `docker compose logs -f backend celery_worker celery_beat`
- **Rolling back**: set `GHCR_TAG=<previous-commit-sha>` in `.env` on the VPS, then `docker compose -f docker-compose.prod.yml up -d` — pulls and runs that exact previous image instead of rebuilding anything.
- **Scaling later**: all state is in Postgres/Redis volumes; moving to a bigger VPS or a managed Postgres later is a matter of restoring the dump.
