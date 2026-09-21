# Environment setup

The backend reads every setting from environment variables, all defined in one
place: `lineup_backend/config.py` (`AppConfig.from_env`). `.env.example` lists
each variable with its default and a one-line comment; it is the source of truth
for this checklist. Locally, `app.py` loads `.env` with python-dotenv. On Render,
set the values in the service's environment (see `render.yaml`).

Every variable is optional for local development. With nothing set, the API
starts with in-memory storage, developer sign-in and mock fallbacks for every
integration. Production needs `FIREBASE_CREDENTIALS` (storage and auth; the
service refuses to boot without it) and the Stripe variables (payments); see
"Production" below.

This is the consumer launch: `LINEUP_BARBER_SIDE` is off, so the API serves
sign-in, credits, analysis, previews and barbershop search only. Barber
accounts, bookings, portfolios, packages and the community feed are not
registered (404) until the flag is on, and the shipped frontend has no UI for
them either.

## Local development

```
cp .env.example .env     # then edit; .env is git-ignored
```

Use `FLASK_ENV=development` locally: it enables the debug server, seeds demo
content and the dev account `client@lineup.dev` into the in-memory store, and
turns on `POST /auth/dev-login` (any email creates a client account with 3
credits). Set `LINEUP_DEV_SECRET` to any string so dev tokens survive
restarts. Restart the API after backend changes.

## Checklist

### Integrations (each one degrades gracefully when absent)

| Variable | Enables | Without it |
|---|---|---|
| `GEMINI_API_KEY` | Photo analysis, image moderation, haircut matching (`/analyze`, `/social` moderation) | Fixed mock analysis; responses carry `"mock": true` and a `reason` |
| `GOOGLE_PLACES_API_KEY` | Real barbershop search, reviews and photos (`/barbers`, `/places/photo`) | Sample barbershops with `"mock": true` |
| `REPLICATE_API_TOKEN` | Virtual try-on image generation (`/virtual-tryon`) | A labelled preview of the uploaded photo (`"mode": "preview"`) |
| `FIREBASE_CREDENTIALS` | Firestore storage and Firebase ID-token verification (service-account JSON as a single line) | Development/testing: in-memory store (data lost on restart) and auth mode `dev`. Production: the API refuses to start unless `LINEUP_ALLOW_MEMORY_STORE=true`, and then auth is `disabled` (protected routes return 503) |
| `FIREBASE_WEB_CONFIG` | Browser sign-in with Google / email (public web-app config JSON, served by `GET /config`) | The sign-in page shows only the developer sign-in (dev mode) or "sign-in unavailable" |
| `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET` | Uploading community post images to Cloudinary (all three required) | Images are stored inline as base64 |
| `STRIPE_SECRET_KEY` | Stripe Checkout and the billing portal (`/billing/checkout`, `/billing/portal`) | 503 `stripe_not_configured`; only the 3 signup credits (plus dev grants locally) |
| `STRIPE_WEBHOOK_SECRET` | Signature verification for `POST /billing/webhook` | The webhook returns 503; purchases are never credited |
| `STRIPE_PRICE_STARTER`, `STRIPE_PRICE_PLUS`, `STRIPE_PRICE_STUDIO` | Stripe price ids for the three credit packs (one-time) | That pack is reported `purchasable: false`; checkout returns 503 `price_not_configured` |
| `STRIPE_PRICE_BARBER_PRO` | Barber Pro (monthly); read only with `LINEUP_BARBER_SIDE=true` | Pro is `purchasable: false` |

Tuning for the integrations: `GEMINI_MODEL` (default `gemini-2.0-flash`),
`LINEUP_GEMINI_DAILY_LIMIT` (50), `LINEUP_PLACES_DAILY_LIMIT` (1700, counted in Google API calls: one search costs up to 17),
`LINEUP_PLACES_CACHE_TTL` (3600 s), `LINEUP_PLACES_CACHE_MAX` (50),
`LINEUP_SEED_MOCK_DATA` (`true`/`false`; default seeds only in development
without Firestore).

### Auth and metering

| Variable | Default | Notes |
|---|---|---|
| `LINEUP_DEV_SECRET` | random per process | HS256 secret for dev-login JWTs. Unset means tokens die on restart. Ignored in `firebase` mode. |
| `LINEUP_DEV_TOKEN_TTL` | `604800` | Dev token lifetime in seconds (7 days) |
| `LINEUP_ADMIN_TOKEN` | - | Gates `/metrics`, `/cache-stats` and `/clear-cache` (send as `X-Admin-Token`). Set it in production; unset, those routes answer 404 there and stay open only in dev auth mode. |
| `LINEUP_METER_MOCK` | auto | Charge credits for mock/preview responses. Default: true outside production (so the out-of-credits flow can be demoed), false in production |
| `MAX_ANALYSIS_PER_DAY_PER_USER` | `20` | Per-user daily cap on `/analyze`; 429 `daily_cap_reached` (0 = unlimited) |
| `MAX_TRYON_PER_DAY_PER_USER` | `10` | Per-user daily cap on `/virtual-tryon` |
| `MAX_BARBER_SEARCH_PER_DAY_PER_USER` | `40` | Per-user daily cap on charged `/barbers` searches |

Credit costs, pack sizes and prices are not environment variables; they live in
`lineup_backend/pricing.py` and must match the Stripe prices.

### Runtime

| Variable | Default | Notes |
|---|---|---|
| `LINEUP_BARBER_SIDE` | `false` | `true` registers the barber-side API (shop management, bookings, portfolios/packages, community feed) and lets `/auth/onboarding` create barber accounts. The shipped frontend does not use it. |
| `LINEUP_ALLOW_MEMORY_STORE` | `false` | `true` lets production start without Firestore (throwaway demos only; every purchase is lost on restart). |
| `FLASK_ENV` | `production` | `development` (debug + seed + dev login), `testing` (pytest), or `production`. `ENV` is read as a fallback. |
| `PORT` | `5000` | Port for `python app.py`; Render sets it |
| `LOG_LEVEL` | `INFO` | `DEBUG` also logs every request |
| `LOG_FORMAT` | `text` | `json` for one JSON object per line |
| `LINEUP_TRUST_PROXY` | `false` | Set `true` behind a reverse proxy (Render) so client IPs and HTTPS come from `X-Forwarded-*`. Anonymous rate limits are per-IP and need this in production. |
| `LINEUP_PUBLIC_URL` | request host | Public base URL of the API, used to build `/places/photo` links |
| `LINEUP_FRONTEND_URL` | `https://lineupai.onrender.com` | Site origin: Stripe Checkout returns to `<origin>/#/account?checkout=success|cancel`, the portal to `<origin>/#/account`; also reported by `/health` |
| `LINEUP_ALLOWED_ORIGINS` | production hosts plus any `localhost` / `127.0.0.1` port | Comma-separated CORS origins, exact strings or regexes |
| `MAX_CONTENT_LENGTH` | `12582912` | Request body limit in bytes; larger bodies get a JSON 413 |

### Rate limiting

| Variable | Default | Notes |
|---|---|---|
| `RATELIMIT_ENABLED` | `true` | `false` disables all limits |
| `RATELIMIT_STORAGE_URI` | `memory://` | Use `redis://host:6379` when running more than one instance or worker |
| `LINEUP_RATE_GLOBAL` | `1000 per hour` | Default for every route |
| `LINEUP_RATE_HEALTH` | `200 per minute` | `/`, `/health`, `/config`, `/billing/pricing` |
| `LINEUP_RATE_READ` | `200 per hour` | List and get endpoints |
| `LINEUP_RATE_WRITE` | `60 per hour` | Create and update endpoints |
| `LINEUP_RATE_ENGAGEMENT` | `100 per hour` | Likes, comments, shares, follows |
| `LINEUP_RATE_SOCIAL_WRITE` | `20 per hour` | Creating feed posts |
| `LINEUP_RATE_AI` | `10 per hour` | `/analyze` |
| `LINEUP_RATE_TRYON` | `20 per hour` | `/virtual-tryon` |
| `LINEUP_RATE_PLACES` | `50 per hour` | `/barbers` search |
| `LINEUP_RATE_OPS` | `10 per hour` | `/metrics`, `/cache-stats`, `/clear-cache` |
| `LINEUP_RATE_AUTH` | `30 per hour` | `/auth/dev-login`, `/auth/onboarding` |
| `LINEUP_RATE_BILLING` | `60 per hour` | `/billing/checkout`, `/billing/portal`, dev grants |
| `LINEUP_RATE_WEBHOOK` | `600 per hour` | `/billing/webhook` |

Values use Flask-Limiter syntax (`N per second|minute|hour|day`). Limits are
keyed by user id when a valid token is sent, otherwise by client IP.

## Production

Firebase (console steps): enable the Google and Email/Password providers under
Authentication; generate a service-account key (Project settings, Service
accounts) into `FIREBASE_CREDENTIALS`; copy the web app config (Project
settings, General) into `FIREBASE_WEB_CONFIG`; add the frontend hostname to
Authentication's authorized domains.

Stripe (dashboard steps): create the three one-time prices (Starter 10
credits $4.99, Plus 30 $9.99, Studio 100 $24.99) and put the ids in
`STRIPE_PRICE_STARTER`, `_PLUS`, `_STUDIO`; copy the secret key into
`STRIPE_SECRET_KEY`; add a webhook endpoint `https://<backend-host>/billing/webhook`
for `checkout.session.completed` (the subscription events are only relevant
with the barber side on) and put its signing secret in `STRIPE_WEBHOOK_SECRET`;
enable the customer portal. Use test mode keys and prices until the flow is
verified. Locally, `stripe listen --forward-to localhost:5000/billing/webhook`
prints a `whsec_...` to use as `STRIPE_WEBHOOK_SECRET`.

`render.yaml` sets `FLASK_ENV=production`, `LOG_FORMAT=json`,
`LINEUP_TRUST_PROXY=true`, `LINEUP_PUBLIC_URL`, `LINEUP_ALLOWED_ORIGINS` and
`LINEUP_FRONTEND_URL`, and declares the keys above with `sync: false` so they
are entered in the dashboard. After deploying, confirm with:

```
curl https://<backend-host>/health
```

`auth_mode` must be `firebase`, `storage` must be `firestore` (the service
does not start otherwise), and `integrations.stripe` true. `GET /config`
shows `auth.firebase` (the public web config), `billing.stripe` and
`consumerOnly: true`.

## Frontend

The static site has no environment variables at runtime. The API base URL is
chosen in `config.js`: `http://localhost:5000` when served from `localhost` or
`127.0.0.1`, otherwise the production backend URL hard-coded there
(`API_URL`). Override per page load with `?api=https://host`, or inject
`window.__LINEUP_CONFIG__ = { API_URL: '...' }` before `config.js` runs. The
Firebase web config comes from the backend's `/config`, not from the site.
