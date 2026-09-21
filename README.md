# LineUp

LineUp reads one photo and tells you which haircuts fit your face. Sign in,
upload a front-facing photo, get your face shape and hair texture with five
or six recommended cuts, preview any of them on your own photo, and find
barbershops near you with real ratings, hours, phone and website so you can
book with the shop directly.

Paid third-party calls (Gemini analysis, Replicate try-on, Google Places
search) go through the backend and are metered in credits: every account
starts with 3, and more are bought as one-time packs through Stripe. Sign-in
is Firebase Authentication (Google or email/password); without Firebase keys
the backend issues local developer tokens so everything works offline.

This branch is the **consumer launch**. The two-sided product (barber
accounts with bookings, a portfolio, services, hours, a client list, packages,
a Barber Pro plan and a shared community feed) is still in the API behind
`LINEUP_BARBER_SIDE=true`, but it is switched off, its routes answer 404, and
the frontend on this branch has no UI for it. The last complete two-sided
frontend is on branch `finish-lineup-fullstack-polish-ui`.

## Architecture

**Backend** (`lineup_backend/`, Flask 2.3, Python 3.12, version 3.2.0): an app
factory (`factory.py: create_app`) loads `AppConfig.from_env()`, configures
logging, CORS, JSON error handlers and Flask-Limiter, builds a `Services`
container (store, Gemini, Places, try-on, image storage, auth, ledger, Stripe,
quotas, cache) and registers the blueprints for the configured mode from
`routes/__init__.py`: `CONSUMER_BLUEPRINTS` (system, auth, billing, analyze,
barbers) always, `BARBER_SIDE_BLUEPRINTS` (barber_shop, social, appointments,
portfolio) only with `LINEUP_BARBER_SIDE`. Every integration in `services/`
has a mock fallback when its key is missing. Persistence goes through the
`Store`/`Collection` interface in `storage/`: Firestore with
`FIREBASE_CREDENTIALS`, in-memory otherwise. **Production refuses to start on
the in-memory store** (`PersistentStoreRequired`): a restart would erase
credits people paid for. `LINEUP_ALLOW_MEMORY_STORE=true` overrides that for
throwaway demos. `app.py` is the WSGI entry: `load_dotenv()` then
`app = create_app()`.

*Auth* (`services/auth.py`, `middleware/auth.py`): requests carry
`Authorization: Bearer <token>`. The mode is derived, never toggled: with
`FIREBASE_CREDENTIALS` set, tokens are Firebase ID tokens verified by the Admin
SDK (`firebase`); otherwise in development or testing `POST /auth/dev-login`
issues HS256 JWTs signed with `LINEUP_DEV_SECRET` (`dev`); in production
without Firebase the mode is `disabled` and protected routes answer 503. In
consumer-only mode every account gets `role: client` on its first request
(accounts from before the cut are promoted the same way), so there is no
onboarding step; `POST /auth/onboarding {role: "barber"}` answers 403
`barber_signups_closed`. Decorators `require_auth`, `require_role("barber")`,
`optional_auth`; helpers `assert_owner(uid)` (403) and `require_pro(feature)`
(402 `pro_required`). Rate limits are keyed by uid when signed in, else by IP.

*Billing* (`pricing.py`, `services/billing.py`, `services/stripe_*.py`,
`routes/billing.py`): `pricing.py` is the single source of truth for credit
costs (`analysis` 1, `tryon` 3, `barber_search` 1), the 3 signup credits, the
packs (Starter 10/$4.99, Plus 30/$9.99, Studio 100/$24.99), Barber Pro
($19/month, only offered with the barber side on) and estimated provider cost
per action. The `Ledger` charges, refunds and grants credits and records every
movement in `usage_events`. `@metered(action, free_when=...)` wraps
`/analyze`, `/virtual-tryon` and `/barbers`: it checks the per-user daily cap,
charges before the view runs and refunds on error, cache hit, provider error,
exhausted server quota, or mock data while `LINEUP_METER_MOCK` is off;
responses carry a `billing` block with the new balance. Stripe Checkout
(payment mode for packs), the portal and `/billing/webhook` sit behind a
four-method gateway so tests inject a fake client; webhook events are
idempotent by id (`stripe_events`).

**Frontend** (`index.html`, `config.js`, `src/js/`, `styles.css`): a static
single page with native ES modules and no bundler. `main.js` boots the modules;
`router.js` shows one `.view` per hash route and gates the app and account
behind a session; `session.js` persists the bearer token and user in
localStorage; `api.js` is the only `fetch` wrapper (sends the token, emits
`lineup:unauthorized`, `lineup:payment-required` and `lineup:credits` DOM
events); `auth.js` loads the Firebase modular SDK (10.14.1) only when `/config`
returns a Firebase web config, otherwise shows the developer sign-in;
`billing.js` owns pricing cards, the header credits pill, Checkout/portal
redirects, the usage ledger and the out-of-credits modal; `state.js` holds
preferences and the last analysis; `nav.js` renders the Home and Explore tabs
plus an Account link; `ui/` holds the toast, modal, skeleton and dropzone
primitives and `features/` the analysis, try-on, barber search and landing
modules. Styling is Tailwind v3 built from `src/input.css` to the committed
`styles.css`. `config.js` picks the API base URL (`http://localhost:5000` on
localhost, otherwise the production backend).

Hash routes: `#/` (landing), `#/pricing`, `#/signin`, `#/account`,
`#/legal/terms`, `#/legal/privacy`, and the app at `#/client/{home,explore}`.

## Quick start

Requirements: Python 3.12 (3.14 also installs), Node 22, [uv](https://docs.astral.sh/uv/).

```
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements-dev.txt
npm ci && npm run build
cp .env.example .env        # optional: add API keys
scripts/dev.sh
```

`scripts/dev.sh` starts the API on http://localhost:5000 with
`FLASK_ENV=development` (debug server, demo data seeded) and the frontend on
http://localhost:8000. Ctrl-C stops both. `FRONTEND_PORT` and `PORT` override
the ports. To run only the API: `FLASK_ENV=development .venv/bin/python app.py`.
Restart the API after changing backend code; the debug reloader is not relied on.

Without Firebase keys the sign-in page shows a "Developer sign-in" card that
calls `POST /auth/dev-login {email, name?}`. Any email creates a client account
with 3 credits; `client@lineup.dev` maps to the seeded uid `client_1`. Dev
tokens last 7 days; set `LINEUP_DEV_SECRET` in `.env` so they survive restarts.
Without Stripe, the account page offers a dev grant (`POST /billing/dev-grant`,
404 outside dev mode). Mock analysis and preview try-on still cost credits
locally (`LINEUP_METER_MOCK` defaults to true outside production) so the
out-of-credits path can be exercised.

Frontend development: `npm run watch` rebuilds `styles.css` on change. After
adding a component class to `src/input.css`, run
`node src/tools/gen-safelist.js && npm run build`.

## Production setup

A production deploy needs Firebase (Firestore storage and Auth: the API does
not start without `FIREBASE_CREDENTIALS`) and Stripe (otherwise Checkout
returns 503 `stripe_not_configured` and credits can only come from the 3
signup credits).

**Firebase**

1. In Authentication, Sign-in method, enable Google and Email/Password.
2. Project settings, Service accounts: generate a private key and paste the
   JSON as one line into `FIREBASE_CREDENTIALS`. This enables Firestore storage
   and token verification (`storage: firestore`, `auth_mode: firebase` in `/health`).
3. Project settings, General, Your apps: register a web app and put its config
   object into `FIREBASE_WEB_CONFIG` as JSON (`apiKey`, `authDomain`,
   `projectId`, `appId`; `storageBucket`, `messagingSenderId`, `measurementId`
   are also forwarded). `/config` serves these public keys to the browser.
4. Authentication, Settings, Authorized domains: add the frontend hostname.
5. Firestore collections (`users`, `usage_events`, `stripe_events`) are created
   on first write; the console prompts for a composite index the first time
   `usage_events` is queried by uid, action, kind and day.

**Stripe**

1. Create three one-time products (Starter 10 credits $4.99, Plus 30 $9.99,
   Studio 100 $24.99) and put the `price_...` ids in `STRIPE_PRICE_STARTER`,
   `_PLUS`, `_STUDIO`. Displayed amounts come from `pricing.py`; keep them in
   sync. (`STRIPE_PRICE_BARBER_PRO` is only read with the barber side on.)
2. `STRIPE_SECRET_KEY`: the secret key (`sk_test_...` while in test mode).
3. Developers, Webhooks: add `https://<backend-host>/billing/webhook` for
   `checkout.session.completed` and put the signing secret in
   `STRIPE_WEBHOOK_SECRET` (the route is 503 without it). The subscription
   events (`invoice.paid`, `customer.subscription.*`) are handled too but only
   matter with the barber side on.
4. Settings, Billing: enable the customer portal for `POST /billing/portal`.
5. `LINEUP_FRONTEND_URL` is the site origin: Checkout returns to
   `<origin>/#/account?checkout=success|cancel`, the portal to `<origin>/#/account`.
   Credits are granted by the webhook, so the account page refetches
   `/billing/me` after returning.
6. Locally: `stripe listen --forward-to localhost:5000/billing/webhook` and use
   the printed `whsec_...`.

## Environment variables

All variables are read only in `lineup_backend/config.py`. `.env.example`
documents each with its default; `ENVIRONMENT_SETUP.md` is the deployment
checklist. Locally, `.env` is loaded by `app.py`.

| Variable | Default | Effect / what degrades without it |
|---|---|---|
| `LINEUP_BARBER_SIDE` | `false` | `true` registers the barber-side API (shop management, bookings, portfolios/packages, community feed) and lets onboarding create barber accounts. No frontend on this branch. |
| `LINEUP_ALLOW_MEMORY_STORE` | `false` | `true` lets production start without Firestore. Demos only: every purchase is lost on restart. |
| `GEMINI_API_KEY` | unset | Photo analysis, haircut matching. Without it `/analyze` returns mock data (`"mock": true`). |
| `GOOGLE_PLACES_API_KEY` | unset | Real barbershop search, reviews, photos. Without it `/barbers` returns sample shops. |
| `REPLICATE_API_TOKEN` | unset | Try-on generation. Without it `/virtual-tryon` returns a labelled preview (`"mode": "preview"`). |
| `FIREBASE_CREDENTIALS` | unset | Service-account JSON (one line): Firestore storage and Firebase token verification. Required in production. Without it locally: memory store and dev auth. |
| `FIREBASE_WEB_CONFIG` | unset | Public web-app config JSON served by `/config` so the browser can sign in with Firebase. |
| `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET` | unset | Image uploads for the community feed (barber side only). |
| `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` | unset | Checkout/portal, and webhook verification. Without them 503 `stripe_not_configured`. |
| `STRIPE_PRICE_STARTER`, `STRIPE_PRICE_PLUS`, `STRIPE_PRICE_STUDIO` | unset | Stripe price ids; a pack without one is not purchasable (503 `price_not_configured`). |
| `STRIPE_PRICE_BARBER_PRO` | unset | Barber Pro price id; read only with `LINEUP_BARBER_SIDE=true`. |
| `LINEUP_DEV_SECRET`, `LINEUP_DEV_TOKEN_TTL` | random per process, `604800` | Dev-login JWT secret and lifetime (seconds). |
| `LINEUP_ADMIN_TOKEN` | - | Shared secret for `/metrics`, `/cache-stats`, `/clear-cache` (`X-Admin-Token` header). Without it those routes only exist in dev auth mode. |
| `LINEUP_METER_MOCK` | auto | Charge credits for mock/preview responses. Default true outside production, false in production. |
| `MAX_ANALYSIS_PER_DAY_PER_USER`, `MAX_TRYON_PER_DAY_PER_USER`, `MAX_BARBER_SEARCH_PER_DAY_PER_USER` | `20`, `10`, `40` | Per-user daily caps (0 = unlimited); 429 `daily_cap_reached`. |
| `FLASK_ENV` | `production` | `development`: debug server, seeded data, dev login. `testing`: pytest. `ENV` is a fallback. |
| `PORT` | `5000` | Dev server port (Render sets it). |
| `LOG_LEVEL`, `LOG_FORMAT` | `INFO`, `text` | `DEBUG` logs each request; `json` emits one object per line. |
| `LINEUP_TRUST_PROXY` | `false` | `true` behind a proxy (Render) so client IPs and HTTPS come from `X-Forwarded-*`. |
| `LINEUP_PUBLIC_URL` | request host | Public API base URL used in `/places/photo` links. |
| `LINEUP_FRONTEND_URL` | `https://lineupai.onrender.com` | Site origin for Stripe return URLs; reported by `/health`. |
| `LINEUP_ALLOWED_ORIGINS` | production hosts + any `localhost`/`127.0.0.1` port | Comma-separated CORS origins, exact or regex. |
| `MAX_CONTENT_LENGTH` | `12582912` | Body limit in bytes; larger requests get a JSON 413. |
| `RATELIMIT_ENABLED`, `RATELIMIT_STORAGE_URI` | `true`, `memory://` | Use `redis://...` with more than one worker or instance. |
| `LINEUP_RATE_{GLOBAL,HEALTH,READ,WRITE,ENGAGEMENT,SOCIAL_WRITE,AI,TRYON,PLACES,OPS,AUTH,BILLING,WEBHOOK}` | see `.env.example` | Per-group limits in Flask-Limiter syntax. |
| `GEMINI_MODEL`, `LINEUP_GEMINI_DAILY_LIMIT` | `gemini-2.0-flash`, `50` | Model and server-wide daily call cap before falling back to mock. |
| `LINEUP_PLACES_DAILY_LIMIT`, `LINEUP_PLACES_CACHE_TTL`, `LINEUP_PLACES_CACHE_MAX` | `1700`, `3600`, `50` | Server-wide daily cap on Google Places API calls (one search costs up to 17: geocode + nearby + one details call per shop) and the per-location cache. |
| `LINEUP_SEED_MOCK_DATA` | auto | Force demo seeding on or off (default: only in development without Firestore). |

## API

All responses are JSON; errors are `{"error", "message", ...}` with 400, 401
(`code`: `unauthorized`, `invalid_token`, `token_expired`), 402
(`insufficient_credits` with `needed`/`credits`), 403 (`forbidden`,
`barber_signups_closed`), 404, 405, 409, 413, 429 (`Retry-After`;
`daily_cap_reached` for per-user caps), 500, 502 (`stripe_error`) or 503
(`auth_not_configured`, `stripe_not_configured`, `price_not_configured`).

Auth: `public` (no token; a valid token personalises), `user` (any signed-in
account), `dev-only` (404 unless `/config` reports `auth.devLogin`). Credits
are charged only for signed-in users.

### Shipped (consumer) routes

| Method | Path | Auth | Credits | Notes |
|---|---|---|---|---|
| GET | `/` | public | - | Service name, version, endpoint list |
| GET | `/health` | public | - | `status`, `version`, `storage`, `integrations`, `auth_mode`, usage counters |
| GET | `/config` | public | - | Capability flags, `consumerOnly`, `auth` (`mode`, `devLogin`, `firebase`), `billing` (`stripe`, `chargeForMock`, `dailyCaps`) |
| GET | `/metrics`, `/cache-stats` | ops | - | Request timing; Places cache stats. Send `X-Admin-Token: <LINEUP_ADMIN_TOKEN>`; without a configured token they exist only in dev auth mode (404 otherwise) |
| GET, POST | `/clear-cache` | ops | - | Empty the Places and matcher caches (same gate) |
| GET | `/auth/me` | user | - | `user`, `entitlements`, `auth.mode` |
| POST | `/auth/dev-login` | dev-only | - | `{email, name?}` -> `token`, `expiresAt`, `user`; 404 in production or Firebase mode |
| POST | `/auth/onboarding` | user | - | Accounts are already clients: `{role: "client"}` is 409 `already_onboarded`, `{role: "barber"}` is 403 `barber_signups_closed` |
| GET | `/billing/pricing` | public | - | Packs, credit costs, `stripe_configured`; `barber_pro` is `null` |
| GET | `/billing/me` | user | - | `credits`, `plan`, `entitlements`, usage summary, Stripe state, dev flags |
| GET | `/billing/usage` | user | - | `?limit=50` ledger events, newest first |
| POST | `/billing/checkout` | user | - | `{packId}` -> `{url, sessionId, mode: "payment"}`; `{plan: "barber_pro"}` is 400 `plan_not_available` |
| POST | `/billing/portal` | user | - | `{url}`; 400 `no_billing_account` |
| POST | `/billing/webhook` | Stripe signature | - | Grants credits; idempotent by event id |
| POST | `/billing/dev-grant` | dev-only | - | `{credits?}` (default 10, max 1000) |
| POST | `/analyze` | user | 1 | `{image}` -> `analysis`, `recommendations[]`, `mock`, `billing`; daily cap 20 |
| POST | `/virtual-tryon` | user | 3 | `{userPhoto, styleDescription}` -> `resultImage`, `mode`, `billing`; daily cap 10 |
| GET | `/ai-insights` | public | - | Trending styles and hashtags |
| GET | `/barbers` | public | 1 | `?location=&styles=`; charged only when a signed-in user triggers a real Places call (cache hits are free); anonymous callers get cached or sample data |
| GET | `/places/photo` | public | - | `?ref=&maxwidth=` 302 to the Google photo |
| GET | `/barbers/<id>/reviews` | public | - | Google reviews for a Places id, otherwise reviews stored on LineUp |

### Barber side (`LINEUP_BARBER_SIDE=true` only; 404 otherwise)

`POST /barbers/<id>/reviews`; `/barbers/<id>/{profile,availability,available-slots,services,clients,...}`
(`routes/barber_shop.py`); `/appointments...`; `/social...`, `/users/<id>/follow`;
`/portfolio...`, `/subscription-packages...`, `/client-subscriptions`; and
`POST /billing/dev-activate-pro`. Their contracts are unchanged from the
two-sided app and stay covered by the test suite.

## Testing

```
.venv/bin/python -m pytest -q      # 184 passed, no network
```

Tests build the app with `create_app(**overrides)` (see `tests/conftest.py`):
no keys, limits off, demo data seeded, dev auth with a fixed secret, fakes for
every external service (`tests/helpers.py` has a `FakeStripeClient`). The
fixtures build the full two-sided app (`barber_side=True`) so the switched-off
routes stay covered; `tests/test_consumer_mode.py` builds the shipped
consumer-only configuration and the production persistence guard. Fixtures
`as_client`, `as_barber`, `as_pro_barber` and `other_client` return a test
client that sends the bearer header. There is no JavaScript test suite; the
frontend is verified in headless Chromium at 375, 768 and 1440 px (Playwright
is not a dependency: `npm i --no-save playwright` when needed).

## Deployment (Render)

`render.yaml` is a Blueprint with two services:

- `lineup-backend` (Python 3.12.0): `pip install -r requirements.txt`, then
  `gunicorn app:app --workers 1 --threads 4 --timeout 120`, health check
  `/health`. The 120 s timeout covers Replicate try-on calls. Sets
  `FLASK_ENV=production`, `LINEUP_BARBER_SIDE=false`, `LOG_FORMAT=json`,
  `LINEUP_TRUST_PROXY=true`, `LINEUP_PUBLIC_URL`, `LINEUP_ALLOWED_ORIGINS`,
  `LINEUP_FRONTEND_URL`; API keys, Firebase and Stripe values are
  `sync: false` and entered in the dashboard. `FIREBASE_CREDENTIALS` must be
  set or the service fails its health check on purpose. Move to `--workers 2`
  only with `RATELIMIT_STORAGE_URI=redis://...`.
- `lineup-frontend` (static, Node 22.20.0): `npm ci && npm run build`, publish
  path `.`, SPA rewrite `/* -> /index.html`, `no-cache` for `index.html`,
  five-minute cache for `styles.css`, `config.js` and `src/*`, one day for
  `images/*`. `.renderignore` lists the files kept out of the published site.

After the first deploy, point `LINEUP_PUBLIC_URL`, `LINEUP_ALLOWED_ORIGINS` and
`LINEUP_FRONTEND_URL` at the assigned hostnames, make sure `config.js`
`API_URL` is the backend URL, add the frontend host to Firebase's authorized
domains and the backend host to the Stripe webhook. `/health` should report
`storage: firestore`, `auth_mode: firebase` and `integrations.stripe: true`.
`Procfile` carries the same gunicorn command for other hosts.

## Project structure

```
app.py                      WSGI entry: load_dotenv(); app = create_app()
lineup_backend/
  __init__.py, factory.py   create_app, __version__ (3.2.0)
  config.py                 AppConfig.from_env(); the only place env vars are read
  pricing.py                credit costs, packs, Barber Pro, provider cost estimates
  context.py, extensions.py Services container; Flask-Limiter and rate("group")
  http.py, logging_config.py, metrics.py
  middleware/               cors, error_handler, auth (require_auth, require_role, optional_auth, assert_owner, require_pro)
  routes/                   __init__ (CONSUMER_BLUEPRINTS / BARBER_SIDE_BLUEPRINTS), system, auth, billing, analyze,
                            barbers (discovery); barber_shop, social, appointments, portfolio (barber side)
  services/                 auth, users, billing (Ledger, metered), stripe_gateway, stripe_events, gemini, places,
                            tryon, image_storage, barber_matcher, availability, haircuts, quota, cache
  storage/                  base.py (Store/Collection), memory.py, firestore.py, seed.py, PersistentStoreRequired
tests/                      pytest suite (conftest.py with auth fixtures, helpers.py, test_*.py, test_consumer_mode.py)
scripts/dev.sh              API + static frontend for local development
get_metrics.py, Procfile, requirements.txt, requirements-dev.txt
index.html                  the single page: landing, pricing, sign-in, app, account, legal views
config.js                   window.LINEUP_CONFIG (API URL, ?api= ?debug=)
src/input.css               Tailwind entry: tokens and @layer components
src/safelist.js             generated component-class safelist (src/tools/gen-safelist.js)
src/js/                     main, router, session, auth, billing, api, state, nav, dom, env, format, icons
src/js/ui/                  toast, modal, skeleton, dropzone
src/js/features/            analysis, tryon, barbers, landing
styles.css, tailwind.config.js, package.json, package-lock.json
images/logo.png             logo; images/screens/ holds the landing-page product screenshot
render.yaml, .renderignore  Render Blueprint and the files kept out of the published site
.env.example, ENVIRONMENT_SETUP.md, CLAUDE.md
```

## Known limitations

- Firestore, Firebase ID-token verification, Stripe, Gemini, Places, Replicate
  and Cloudinary are covered by tests with injected fakes, not live calls.
- One gunicorn worker. Scaling out needs a Redis rate-limit store, otherwise
  each worker keeps separate limits.
- Daily caps filter the user's charge events by day; on Firestore a heavy
  user's query grows with their history.
- No admin role in the app. The operational endpoints (`/metrics`, `/cache-stats`,
  `/clear-cache`) are gated by `LINEUP_ADMIN_TOKEN` (header `X-Admin-Token`) and
  answer 404 in production without it.
- Booking inside LineUp is off with the barber side: search results link to
  the shop's own phone, map, website and booking page instead.
