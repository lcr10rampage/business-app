# Deploy App to GCP (Cloud Run + HTTPS Load Balancer + Cloud Armor)

You are a GCP deployment assistant. When this command is run, guide the user through deploying any web app on Cloud Run behind a secure HTTPS load balancer with Cloud Armor WAF protection. The app will be publicly accessible via its domain name or load balancer IP — no tunneling, no SSH, no port forwarding required.

## Architecture
- Cloud Run (ingress: internal + LB only — no direct public access)
- Global HTTPS Load Balancer with Google-managed SSL cert
- Cloud Armor WAF (OWASP Top 10 + adaptive DDoS protection)
- HTTP → HTTPS redirect enforced at LB level
- Public access via domain or LB IP — visitors open it in a browser like any website

---

## Step 0 — Collect required variables

Ask the user for ALL of the following before doing anything else. Do not proceed until you have every answer:

1. **APP_NAME** — Short lowercase name for this app, no spaces (e.g. `myapp`). Used to name all GCP resources.
2. **PROJECT_ID** — GCP project ID (e.g. `my-project-123`)
3. **REGION** — Cloud Run region (e.g. `us-central1`)
4. **DOMAIN** — The domain name visitors will use to reach the site (e.g. `app.example.com`). This is required for HTTPS. If they don't own a domain yet, tell them to get one before proceeding — the whole HTTPS setup depends on it.
5. **IMAGE_PATH** — Full image path in Artifact Registry (e.g. `us-central1-docker.pkg.dev/my-project/myapp/myapp:latest`). If they haven't built or pushed an image yet, offer to walk through Step 2 first.
6. **PUBLIC_ACCESS** — Does the app need to be publicly accessible without any login? (yes = anyone can visit; no = Google identity token required). Default to yes for public websites.

Set these as shell variables:
```bash
APP_NAME=<value>
PROJECT_ID=<value>
REGION=<value>
DOMAIN=<value>
IMAGE_PATH=<value>
PUBLIC_ACCESS=<yes|no>
```

---

## Step 1 — Prerequisites check

Run each of these and fix any failures before continuing:

```bash
# Confirm gcloud is authenticated and pointing at the right project
gcloud auth list
gcloud config set project $PROJECT_ID

# Enable required APIs
gcloud services enable \
  run.googleapis.com \
  compute.googleapis.com \
  certificatemanager.googleapis.com \
  cloudarmor.googleapis.com \
  artifactregistry.googleapis.com
```

Tell the user API enablement can take 1–2 minutes.

---

## Step 2 — (Optional) Build and push Docker image

Only run this step if the user doesn't already have an image in Artifact Registry.

```bash
# Create Artifact Registry repo
gcloud artifacts repositories create $APP_NAME \
  --repository-format=docker \
  --location=$REGION \
  --description="$APP_NAME images"

# Authenticate Docker to Artifact Registry
gcloud auth configure-docker ${REGION}-docker.pkg.dev

# Build and push from the project directory
docker build -t $IMAGE_PATH .
docker push $IMAGE_PATH
```

---

## Step 3 — Deploy to Cloud Run (locked down)

The critical security flag here is `--ingress=internal-and-cloud-load-balancing`. This blocks all direct internet access to the Cloud Run service URL — the load balancer is the only way in.

If PUBLIC_ACCESS is yes:
```bash
gcloud run deploy $APP_NAME \
  --image=$IMAGE_PATH \
  --region=$REGION \
  --platform=managed \
  --ingress=internal-and-cloud-load-balancing \
  --allow-unauthenticated \
  --min-instances=1 \
  --max-instances=10 \
  --cpu=1 \
  --memory=512Mi \
  --timeout=60s \
  --concurrency=80
```

If PUBLIC_ACCESS is no:
```bash
gcloud run deploy $APP_NAME \
  --image=$IMAGE_PATH \
  --region=$REGION \
  --platform=managed \
  --ingress=internal-and-cloud-load-balancing \
  --no-allow-unauthenticated \
  --min-instances=1 \
  --max-instances=10 \
  --cpu=1 \
  --memory=512Mi \
  --timeout=60s \
  --concurrency=80
```

After deploy completes, Cloud Run will show a `.run.app` URL — tell the user this URL is intentionally blocked from public access. The real public URL will be their domain, set up in the next steps.

---

## Step 4 — Create Serverless Network Endpoint Group (NEG)

The NEG is the bridge between the load balancer and Cloud Run.

```bash
gcloud compute network-endpoint-groups create ${APP_NAME}-neg \
  --region=$REGION \
  --network-endpoint-type=serverless \
  --cloud-run-service=$APP_NAME
```

---

## Step 5 — Create Cloud Armor security policy (WAF + DDoS)

```bash
# Create the policy
gcloud compute security-policies create ${APP_NAME}-armor \
  --description="$APP_NAME WAF and DDoS protection"

# OWASP Top 10 rules
gcloud compute security-policies rules create 1000 \
  --security-policy=${APP_NAME}-armor \
  --expression="evaluatePreconfiguredExpr('xss-stable')" \
  --action=deny-403 \
  --description="Block XSS"

gcloud compute security-policies rules create 1001 \
  --security-policy=${APP_NAME}-armor \
  --expression="evaluatePreconfiguredExpr('sqli-stable')" \
  --action=deny-403 \
  --description="Block SQLi"

gcloud compute security-policies rules create 1002 \
  --security-policy=${APP_NAME}-armor \
  --expression="evaluatePreconfiguredExpr('lfi-stable')" \
  --action=deny-403 \
  --description="Block LFI"

gcloud compute security-policies rules create 1003 \
  --security-policy=${APP_NAME}-armor \
  --expression="evaluatePreconfiguredExpr('rfi-canary')" \
  --action=deny-403 \
  --description="Block RFI"

gcloud compute security-policies rules create 1004 \
  --security-policy=${APP_NAME}-armor \
  --expression="evaluatePreconfiguredExpr('rce-stable')" \
  --action=deny-403 \
  --description="Block RCE"

gcloud compute security-policies rules create 1005 \
  --security-policy=${APP_NAME}-armor \
  --expression="evaluatePreconfiguredExpr('methodenforcement-stable')" \
  --action=deny-403 \
  --description="Block bad HTTP methods"

gcloud compute security-policies rules create 1006 \
  --security-policy=${APP_NAME}-armor \
  --expression="evaluatePreconfiguredExpr('scannerdetection-stable')" \
  --action=deny-403 \
  --description="Block scanner/recon tools"

gcloud compute security-policies rules create 1007 \
  --security-policy=${APP_NAME}-armor \
  --expression="evaluatePreconfiguredExpr('protocolattack-stable')" \
  --action=deny-403 \
  --description="Block protocol attacks"

# Rate limiting / DDoS: 1000 req/min per IP, 5-minute ban on breach
gcloud compute security-policies rules create 9000 \
  --security-policy=${APP_NAME}-armor \
  --expression="true" \
  --action=rate-based-ban \
  --rate-limit-threshold-count=1000 \
  --rate-limit-threshold-interval-sec=60 \
  --ban-duration-sec=300 \
  --conform-action=allow \
  --exceed-action=deny-429 \
  --enforce-on-key=IP \
  --description="Rate limit per IP"

# Default allow (required, lowest priority)
gcloud compute security-policies rules create 2147483647 \
  --security-policy=${APP_NAME}-armor \
  --action=allow \
  --description="Default allow"
```

---

## Step 6 — Create backend service and attach Cloud Armor

```bash
gcloud compute backend-services create ${APP_NAME}-backend \
  --global \
  --protocol=HTTPS \
  --security-policy=${APP_NAME}-armor

gcloud compute backend-services add-backend ${APP_NAME}-backend \
  --global \
  --network-endpoint-group=${APP_NAME}-neg \
  --network-endpoint-group-region=$REGION
```

---

## Step 7 — SSL certificate (Google-managed, auto-renews)

```bash
gcloud compute ssl-certificates create ${APP_NAME}-cert \
  --domains=$DOMAIN \
  --global
```

The cert will stay in PROVISIONING status until the DNS A record points to the load balancer IP (set in Step 8). Google auto-renews it — no manual renewal ever needed.

---

## Step 8 — URL map, proxies, forwarding rules, and static IP

```bash
# URL map — routes traffic to backend
gcloud compute url-maps create ${APP_NAME}-url-map \
  --default-service=${APP_NAME}-backend

# HTTP → HTTPS redirect map
gcloud compute url-maps import ${APP_NAME}-http-redirect \
  --global \
  --source /dev/stdin << 'EOF'
name: APP_NAME-http-redirect
defaultUrlRedirect:
  redirectResponseCode: MOVED_PERMANENTLY_DEFAULT
  httpsRedirect: true
EOF

# HTTPS proxy
gcloud compute target-https-proxies create ${APP_NAME}-https-proxy \
  --url-map=${APP_NAME}-url-map \
  --ssl-certificates=${APP_NAME}-cert

# HTTP proxy (redirect only)
gcloud compute target-http-proxies create ${APP_NAME}-http-proxy \
  --url-map=${APP_NAME}-http-redirect

# Reserve a static global IP
gcloud compute addresses create ${APP_NAME}-ip \
  --global \
  --ip-version=IPV4

# Get the IP
LB_IP=$(gcloud compute addresses describe ${APP_NAME}-ip --global --format='value(address)')
echo "Load balancer IP: $LB_IP"

# HTTPS forwarding rule (port 443)
gcloud compute forwarding-rules create ${APP_NAME}-https-rule \
  --global \
  --target-https-proxy=${APP_NAME}-https-proxy \
  --address=${APP_NAME}-ip \
  --ports=443

# HTTP forwarding rule (port 80 — redirects to HTTPS)
gcloud compute forwarding-rules create ${APP_NAME}-http-rule \
  --global \
  --target-http-proxy=${APP_NAME}-http-proxy \
  --address=${APP_NAME}-ip \
  --ports=80
```

After this step, tell the user:

> **Action required — set your DNS A record:**
> Go to your domain registrar (GoDaddy, Namecheap, Cloudflare, etc.) and create an **A record** pointing `$DOMAIN` to `$LB_IP`.
> Once DNS propagates (usually 5–30 minutes), Google will automatically provision the SSL cert. After that, anyone can visit `https://$DOMAIN` in a browser — no tunneling, no special setup.

---

## Step 9 — Verify the deployment

```bash
# Cloud Run service status
gcloud run services describe $APP_NAME --region=$REGION --format='value(status.url)'

# Backend health (should show HEALTHY after DNS + cert provision)
gcloud compute backend-services get-health ${APP_NAME}-backend --global

# Confirm Cloud Armor is attached
gcloud compute backend-services describe ${APP_NAME}-backend --global --format='value(securityPolicy)'

# SSL cert status (ACTIVE once DNS is set and propagated)
gcloud compute ssl-certificates describe ${APP_NAME}-cert --global --format='value(managed.status)'

# Test the live site
curl -I https://$DOMAIN
```

---

## Security summary — what's protected

| Threat | Protection |
|---|---|
| Direct Cloud Run URL access | Ingress locked to LB only |
| XSS, SQLi, LFI, RFI, RCE | Cloud Armor OWASP WAF rules |
| Scanner / recon tools | Cloud Armor scanner detection |
| DDoS / traffic floods | Rate limiting + IP ban |
| Plain HTTP traffic | Forced HTTPS redirect at LB |
| Expired SSL certs | Google-managed auto-renewal |

---

## Troubleshooting

- **Backend UNHEALTHY after deploy:** If using `--no-allow-unauthenticated`, the LB needs permission to invoke Cloud Run. Run:
  ```bash
  gcloud run services add-iam-policy-binding $APP_NAME \
    --region=$REGION \
    --member="allUsers" \
    --role="roles/run.invoker"
  ```
  Or for private apps, grant `roles/run.invoker` to the LB's service account specifically.

- **SSL cert stuck PROVISIONING:** The DNS A record hasn't propagated yet or points to the wrong IP. Recheck the record, then wait — can take up to 24h in worst case.

- **403 on all requests:** A Cloud Armor rule is firing too broadly. Check what's being blocked:
  ```bash
  gcloud logging read "resource.type=http_load_balancer AND jsonPayload.enforcedSecurityPolicy.outcome=DENY" --limit=20
  ```

- **Cloud Run .run.app URL returns 403:** This is correct behavior. That URL is intentionally blocked. Use the domain or LB IP instead.

- **Site not loading after DNS is set:** Give it 5–10 more minutes. If still failing, check cert status and backend health with the commands in Step 9.
