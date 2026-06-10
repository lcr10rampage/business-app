# How to Deploy a Website Using /deploy-app

This guide walks you through everything you need to successfully deploy a web app or website to Google Cloud using the `/deploy-app` skill in Claude Code. When it's done, anyone can visit your site at `https://yourdomain.com` — no tunneling, no special setup.

---

## What you need before starting

Have these ready before running the skill:

| Requirement | Details |
|---|---|
| **GCP account** | A Google Cloud account with billing enabled |
| **GCP project** | A project to deploy into. Create one at console.cloud.google.com if you don't have one. |
| **gcloud CLI** | Install from: https://cloud.google.com/sdk/docs/install — then run `gcloud auth login` |
| **Docker** | Install from: https://docs.docker.com/get-docker — only needed if you haven't built your image yet |
| **Domain name** | A domain you own (e.g. from GoDaddy, Namecheap, Cloudflare). Required for HTTPS. |
| **App code** | Your app must have a `Dockerfile` in the root of the project folder |

---

## Information to have on hand

When you run `/deploy-app`, it will ask for these 6 things up front. Have them ready:

1. **APP_NAME** — a short lowercase name with no spaces (e.g. `mywebsite`). This names all your cloud resources.
2. **PROJECT_ID** — your GCP project ID. Find it in the GCP console, top-left dropdown (e.g. `my-project-123`).
3. **REGION** — where to run the app. `us-central1` is a safe default unless you need a specific location.
4. **DOMAIN** — the domain visitors will use (e.g. `app.mywebsite.com` or `www.mywebsite.com`).
5. **IMAGE_PATH** — where your Docker image will live in GCP. Format: `REGION-docker.pkg.dev/PROJECT_ID/APP_NAME/APP_NAME:latest`. Example: `us-central1-docker.pkg.dev/my-project-123/mywebsite/mywebsite:latest`
6. **PUBLIC_ACCESS** — answer `yes` if anyone should be able to visit the site. Answer `no` if it requires a Google login.

---

## How to run it

1. Open Claude Code in the folder that contains your project (the one with `Dockerfile`)
2. Type `/deploy-app` and press Enter
3. Claude will ask for the 6 variables above — answer each one
4. Claude will walk you through each step, running commands and explaining what's happening
5. Follow along and approve each command as prompted

**Total time:** 15–30 minutes for a first deploy, plus up to 60 minutes for DNS to propagate and SSL to activate.

---

## What happens step by step

| Step | What it does |
|---|---|
| 1 | Authenticates gcloud and enables required GCP APIs |
| 2 | (If needed) Builds your Docker image and pushes it to Google's Artifact Registry |
| 3 | Deploys the app to Cloud Run — locked so it's only reachable through the load balancer |
| 4 | Creates a Serverless NEG — the bridge between the load balancer and Cloud Run |
| 5 | Sets up Cloud Armor — blocks XSS, SQLi, RCE, scanners, and DDoS attacks |
| 6 | Creates the backend service with Cloud Armor attached |
| 7 | Creates a Google-managed SSL certificate for your domain (auto-renews forever) |
| 8 | Wires up the load balancer, HTTPS proxy, HTTP→HTTPS redirect, and reserves a static IP |
| 9 | Verifies everything is running correctly |

---

## After the skill finishes — final DNS step

At the end of Step 8, Claude will give you a **load balancer IP address** (e.g. `34.120.x.x`).

You need to add one DNS record at your domain registrar:

- **Type:** A
- **Name:** your subdomain (e.g. `app` for `app.mywebsite.com`, or `@` for the root domain)
- **Value:** the IP address Claude gave you
- **TTL:** 300 (or Auto)

Once that record propagates (usually 5–30 minutes), Google will issue your SSL certificate automatically. After that, your site is live at `https://yourdomain.com`.

---

## Security — what's protected out of the box

| Threat | How it's blocked |
|---|---|
| Bypassing the load balancer | Cloud Run only accepts traffic from the LB — direct URL access returns 403 |
| XSS, SQL injection, code execution | Cloud Armor WAF blocks all OWASP Top 10 attack patterns |
| Scanner and recon tools | Cloud Armor detects and blocks automated scanners |
| DDoS and traffic floods | Rate limiting: 1,000 req/min per IP, 5-minute ban if exceeded |
| HTTP (unencrypted) traffic | Automatically redirected to HTTPS |
| SSL certificate expiring | Google-managed cert renews itself — nothing to do |

---

## Troubleshooting quick reference

**Site not loading after DNS is set**
Wait another 10 minutes and check cert status:
```bash
gcloud compute ssl-certificates describe <APP_NAME>-cert --global --format='value(managed.status)'
```
Should say `ACTIVE`. If it says `PROVISIONING`, DNS hasn't propagated yet.

**Getting 403 on every request**
A Cloud Armor rule may be too aggressive. Check the denial logs:
```bash
gcloud logging read "resource.type=http_load_balancer AND jsonPayload.enforcedSecurityPolicy.outcome=DENY" --limit=20
```

**Backend shows UNHEALTHY**
The load balancer needs permission to call Cloud Run. Claude will walk you through this in the troubleshooting section of the skill.

**The `.run.app` URL returns 403**
That's intentional — direct access is blocked. Your site is only reachable at the domain you configured.

---

## Updating the app later

To deploy a new version, just rebuild and push your Docker image to the same image path, then redeploy Cloud Run:
```bash
docker build -t $IMAGE_PATH .
docker push $IMAGE_PATH
gcloud run deploy $APP_NAME --image=$IMAGE_PATH --region=$REGION --platform=managed
```
The load balancer, Cloud Armor, and SSL cert stay in place — no changes needed there.
