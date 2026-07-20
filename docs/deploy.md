# Deployment Runbook — Hetzner (Falkenstein)

Standing up Melo-News from nothing to a running, TLS-served pilot instance.

**Target stack:** one Hetzner Cloud VM running `docker-compose.prod.yml` —
Postgres + Flask API (gunicorn) + nginx (static React + reverse proxy) — with
media in Hetzner Object Storage (ADR-0017).

> **Region: Falkenstein (`fsn1`).** The object storage bucket already lives at
> `https://fsn1.your-objectstorage.com`. Put the VM in the same location so
> app↔bucket traffic stays in-network.

> ⚠️ **Who this is for.** ADR-0011 (real at-rest encryption, Keystore-backed
> secrets, signature-only auth) is a **hard gate that is still stubbed**. This
> deployment is fit for the **scripted drill with a dummy cohort** — it is NOT
> yet safe to put in front of real at-risk reporters. See ADR-0011 before any
> real-reporter use.

---

## 0. Prerequisites

- A Hetzner Cloud account, and the existing Object Storage bucket + credentials.
- A domain you control (needed for TLS in step 6).
- Your SSH public key added to the Hetzner project.

---

## 1. Provision the server

Create a Cloud Server:

| Setting | Value |
|---|---|
| Location | **Falkenstein (fsn1)** — same as the bucket |
| Image | Ubuntu 24.04 LTS |
| Type | CPX21 (3 vCPU / 4 GB) — CPX11 (2 vCPU / 2 GB) works but is tight while building the frontend |
| SSH key | your public key (disable password auth) |

Then harden the box before anything else:

```bash
ssh root@<server-ip>

# Firewall: only SSH + HTTP + HTTPS. Postgres and the API are bound to
# loopback in compose, but this is the belt to that braces.
ufw allow OpenSSH && ufw allow 80 && ufw allow 443 && ufw --force enable

apt update && apt upgrade -y
```

Install Docker:

```bash
curl -fsSL https://get.docker.com | sh
docker --version && docker compose version
```

---

## 2. Get the code

The repo is private, so the server needs read access. Use a **deploy key**
(read-only, repo-scoped — safer than putting your personal key on a server):

```bash
ssh-keygen -t ed25519 -C "melo-deploy" -f ~/.ssh/id_ed25519 -N ""
cat ~/.ssh/id_ed25519.pub
```

Add that public key at **GitHub → repo → Settings → Deploy keys → Add**, leaving
"Allow write access" **unchecked**. Then:

```bash
git clone git@github.com:Emesgee/Melo-News.git /opt/melo
cd /opt/melo
```

---

## 3. Configure `.env`

**Do not copy your development `.env` up.** It still carries unused `AZURE_*`
and `KAFKA_*` credentials from the pre-pivot architecture; putting live, unused
secrets on an internet-facing box is pure downside.

```bash
cp .env.production.example .env
python3 -c "import secrets; print(secrets.token_urlsafe(48))"   # SECRET_KEY
python3 -c "import secrets; print(secrets.token_urlsafe(48))"   # JWT_SECRET_KEY
nano .env
```

Fill in: `SECRET_KEY`, `JWT_SECRET_KEY`, `DB_PASSWORD` (do **not** leave `admin`),
`S3_BUCKET`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`.

`config.py` **raises on startup in production** if `SECRET_KEY` or
`JWT_SECRET_KEY` is missing or left at its default — the app cannot boot
half-configured, which is deliberate.

```bash
chmod 600 .env
```

---

## 4. Build the frontend

nginx serves `app/frontend/build` as a **bind mount from the host**, so this
directory must exist *before* the stack starts. It is not built inside any
image.

```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt install -y nodejs
cd /opt/melo/app/frontend
npm ci
npm run build          # emits app/frontend/build
cd /opt/melo
```

> Low-RAM alternative: on a 2 GB box `npm run build` can OOM. Build locally
> instead and copy the output up:
> `rsync -av app/frontend/build/ root@<server-ip>:/opt/melo/app/frontend/build/`

---

## 5. First boot (HTTP only)

TLS comes after, because certificate issuance needs a reachable HTTP server.

```bash
mkdir -p ssl certbot/www uploads exports
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml ps
```

Verify before moving on:

```bash
# nginx config parses (this is the check that could not be run locally)
docker compose -f docker-compose.prod.yml exec melo-nginx nginx -t

# API is alive — schema is created automatically on import (db.create_all)
# and file types are seeded by create_app -> populate_initial_data
curl -s localhost:5000/api/health

# Through nginx: the React app, not an API 404
curl -sI http://<server-ip>/ | head -1        # expect 200
curl -s  http://<server-ip>/api/events | head -c 200
```

If the API container is unhealthy: `docker compose -f docker-compose.prod.yml logs melo-api`.

---

## 6. Domain + TLS

Point an **A record** for your domain at the server IP and wait for it to
resolve. Then issue a certificate via the webroot that nginx already exposes at
`/.well-known/acme-challenge/`:

```bash
docker run --rm \
  -v /opt/melo/ssl:/etc/letsencrypt \
  -v /opt/melo/certbot/www:/var/www/certbot \
  certbot/certbot certonly --webroot -w /var/www/certbot \
  -d your.domain --agree-tos -m you@example.com --no-eff-email
```

Then enable HTTPS:

1. In `nginx.conf`, uncomment the `server { listen 443 ssl; ... }` block.
2. Set `server_name` and the two `ssl_certificate*` paths to `your.domain`.
3. Add a redirect in the port-80 server so plain HTTP forwards to HTTPS:
   ```nginx
   location / { return 301 https://$host$request_uri; }
   ```
   (Keep the ACME `location` above it so renewals keep working.)
4. Apply:
   ```bash
   docker compose -f docker-compose.prod.yml exec melo-nginx nginx -t
   docker compose -f docker-compose.prod.yml restart melo-nginx
   ```

> nginx **refuses to start** if `ssl_certificate` points at a missing file —
> which is exactly why the block ships commented out. Always `nginx -t` before
> restarting.

**Renewal** (certs last 90 days) — add to `crontab -e`:

```
0 3 * * 1 docker run --rm -v /opt/melo/ssl:/etc/letsencrypt -v /opt/melo/certbot/www:/var/www/certbot certbot/certbot renew --quiet && docker compose -f /opt/melo/docker-compose.prod.yml restart melo-nginx
```

---

## 7. Redeploying

```bash
cd /opt/melo
git pull
cd app/frontend && npm ci && npm run build && cd /opt/melo   # only if frontend changed
docker compose -f docker-compose.prod.yml up -d --build
```

## 8. Backups

The Postgres volume holds the Events, corroboration graph, and snapshots — the
archive-grade record (UC9). Back it up from day one:

```bash
mkdir -p /backups   # already mounted into the DB container
docker compose -f docker-compose.prod.yml exec -T melo-database \
  pg_dump -U admin melonews_prod | gzip > /backups/melo-$(date +%F).sql.gz
```

Media lives in Object Storage, which is separate from this VM — losing the
server does not lose media, but losing the bucket does.

---

## Known gaps (deliberate, not oversights)

- **ADR-0011 security hardening is stubbed.** Hard gate before real reporters.
- **Dev/prod parity drift (partly closed).** The image was bumped 3.9 -> 3.12
  after the API crash-looped on PEP 604 syntax; dev is still 3.14. Postgres
  remains split: dev 13, prod 15. Closing that needs a deliberate dump/restore,
  not a silent image bump.
- **No CI/CD.** Deploys are manual `git pull` + rebuild. The old GitHub-Actions
  DigitalOcean pipeline is archived in `docs/old-architecture/` and does not
  match this stack.
- **Hosting jurisdiction is unresolved.** Hetzner is German/EU. Before any
  real-reporter launch or takedown-resistant archive, jurisdiction and
  redundancy need a decision (UC7, ADR-0020 Phase 3).
- **Single box, no redundancy.** Correct for a pilot; revisit at scale.
