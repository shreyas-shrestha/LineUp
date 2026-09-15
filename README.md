# LineUp

LineUp is a two-sided haircut app. Clients sign in, upload a photo, get an
analysis of face shape and hair texture with recommended cuts, preview a cut on
their own photo, find barbershops near them and request a booking. Barbers get
a dashboard with bookings, a portfolio, services, working hours, a client list
and subscription packages. Both sides share a community feed.

Paid third-party calls (Gemini analysis, Replicate try-on, Google Places
search) go through the backend and are metered in credits: every account starts
with 3, and more are bought as one-time packs through Stripe. Barbers can
subscribe to Barber Pro, which unlocks the client list, notes, packages,
analytics and an unlimited portfolio (free: 6 photos). Sign-in is Firebase
Authentication (Google or email/password); without Firebase keys the backend
issues local developer tokens so everything works offline.

## Architecture

**Backend** (`lineup_backend/`, Flask 2.3, Python 3.12, version 3.1.0): an app
factory (`factory.py: create_app`) loads `AppConfig.from_env()`, configures
logging, CORS, JSON error handlers and Flask-Limiter, builds a `Services`
container (store, Gemini, Places, try-on, image storage, auth, ledger, Stripe,
quotas, cache) and registers one blueprint per domain from `routes/`. Every
integration in `services/` has a mock fallback when its key is missing.
Persistence goes through the `Store`/`Collection` interface in `storage/`
(in-memory by default, Firestore with `FIREBASE_CREDENTIALS`). `app.py` is the
WSGI entry: `load_dotenv()` then `app = create_app()`.

*Auth* (`services/auth.py`, `middleware/auth.py`): requests carry
`Authorization: Bearer <token>`. The mode is derived, never toggled: with
`FIREBASE_CREDENTIALS` set, tokens are Firebase ID tokens verified by the Admin
SDK (`firebase`); otherwise in development or testing `POST /auth/dev-login`
issues HS256 JWTs signed with `LINEUP_DEV_SECRET` (`dev`); in production
without Firebase the mode is `disabled` and protected routes answer 503.
Decorators `require_auth`, `require_role("barber")`, `optional_auth`; helpers
`assert_owner(uid)` (403) and `require_pro(feature)` (402 `pro_required`). The
barber id is the user's uid and barber writes derive the owner from the token.
Users carry `role` (chosen once at `/auth/onboarding`), `credits` and `plan`.
Rate limits are keyed by uid when signed in, else by IP.

*Billing* (`pricing.py`, `services/billing.py`, `services/stripe_*.py`,
`routes/billing.py`): `pricing.py` is the single source of truth for credit
costs (`analysis` 1, `tryon` 3, `barber_search` 1), the 3 signup credits, the
packs (Starter 10/$4.99, Plus 30/$9.99, Studio 100/$24.99), Barber Pro
($19/month) and estimated provider cost per action. The `Ledger` charges,
refunds and grants credits and records every movement in `usage_events`.
`@metered(action, free_when=...)` wraps `/analyze`, `/virtual-tryon` and
`/barbers`: it checks the per-user daily cap, charges before the view runs and
refunds on error, cache hit, provider error, exhausted server quota, or mock
data while `LINEUP_METER_MOCK` is off; responses carry a `billing` block with
the new balance. Stripe Checkout (payment for packs, subscription for Pro), the
portal and `/billing/webhook` sit behind a four-method gateway so tests inject
a fake client; webhook events are idempotent by id (`stripe_events`).

**Frontend** (`index.html`, `config.js`, `src/js/`, `styles.css`): a static
single page with native ES modules and no bundler. `main.js` boots the modules;
`router.js` shows one `.view` per hash route and gates the app, onboarding and
account behind a session; `session.js` persists the bearer token and user in
localStorage; `api.js` is the only `fetch` wrapper (sends the token, emits
`lineup:unauthorized`, `lineup:payment-required` and `lineup:credits` DOM
events); `auth.js` loads the Firebase modular SDK (10.14.1) only when `/config`
returns a Firebase web config, otherwise shows the developer sign-in;
`billing.js` owns pricing cards, the header credits pill and plan badge, Pro
locks, Checkout/portal redirects, the usage ledger and the out-of-credits
modal; `state.js` holds preferences and the last analysis (client and barber
ids are both the uid); `ui/` and `features/` are unchanged from phase 1.
Styling is Tailwind v3 built from `src/input.css` to the committed
`styles.css`. `config.js` picks the API base URL (`http://localhost:5000` on
localhost, otherwise the production backend).

Hash routes: `#/` (landing), `#/pricing`, `#/signin`, `#/onboarding`,
`#/account`, `#/legal/terms`, `#/legal/privacy`, and the app at
`#/client/{home,explore,bookings,community,profile}` and
`#/barber/{dashboard,bookings,work,community,shop}`.

## Quick start

Requirements: Python 3.12 (3.11 also works), Node 22, [uv](https://docs.astral.sh/uv/).

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
calls `POST /auth/dev-login {email, name?}`. Two accounts are seeded:

| Email | uid | Role | Notes |
|---|---|---|---|
| `client@lineup.dev` | `client_1` | client | 3 credits, one confirmed booking |
| `barber@lineup.dev` | `barber_1` | barber | shop "Mike's Cuts", default hours and services, free plan |

Any other email creates a fresh account that goes through onboarding. Dev
tokens last 7 days; set `LINEUP_DEV_SECRET` in `.env` so they survive restarts.
Without Stripe, the account page offers a dev grant (`POST /billing/dev-grant`)
and barbers can activate Pro (`POST /billing/dev-activate-pro`); both are 404
outside dev mode. Mock analysis and preview try-on still cost credits locally
(`LINEUP_METER_MOCK` defaults to true outside production) so the
out-of-credits path can be exercised.

Frontend development: `npm run watch` rebuilds `styles.css` on change. After
adding a component class to `src/input.css`, run
`node src/tools/gen-safelist.js && npm run build`.

## Production setup

A production deploy needs Firebase Auth (otherwise every protected route is
503) and Stripe (otherwise Checkout returns 503 `stripe_not_configured` and
credits can only come from the 3 signup credits).

**Firebase Authentication**

1. In Authentication, Sign-in method, enable Google and Email/Password.
2. Project settings, Service accounts: generate a private key and paste the
   JSON as one line into `FIREBASE_CREDENTIALS`. This enables Firestore storage
   and token verification (`auth_mode: firebase` in `/health`).
3. Project settings, General, Your apps: register a web app and put its config
   object into `FIREBASE_WEB_CONFIG` as JSON (`apiKey`, `authDomain`,
   `projectId`, `appId`; `storageBucket`, `messagingSenderId`, `measurementId`
   are also forwarded). `/config` serves these public keys to the browser.
4. Authentication, Settings, Authorized domains: add the frontend hostname.
5. Firestore collections (`users`, `usage_events`, `stripe_events`,
   `barber_profiles`) are created on first write; the console prompts for a
   composite index the first time `usage_events` is queried by uid, action and kind.

**Stripe**

1. Create three one-time products (Starter 10 credits $4.99, Plus 30 $9.99,
   Studio 100 $24.99) and one monthly product (Barber Pro $19). Put the four
   `price_...` ids in `STRIPE_PRICE_STARTER`, `_PLUS`, `_STUDIO`,
   `_BARBER_PRO`. Displayed amounts come from `pricing.py`; keep them in sync.
2. `STRIPE_SECRET_KEY`: the secret key (`sk_test_...` while in test mode).
3. Developers, Webhooks: add `https://<backend-host>/billing/webhook` for
   `checkout.session.completed`, `invoice.paid`, `customer.subscription.updated`
   and `customer.subscription.deleted`; put the signing secret in
   `STRIPE_WEBHOOK_SECRET` (the route is 503 without it).
4. Settings, Billing: enable the customer portal for `POST /billing/portal`.
5. `LINEUP_FRONTEND_URL` is the site origin: Checkout returns to
   `<origin>/#/account?checkout=success|cancel`, the portal to `<origin>/#/account`.
   Credits are granted by the webhook, so the account page refetches
   `/billing/me` after returning.
6. Locally: `stripe listen --forward-to localhost:5000/billing/webhook` and use
   the printed `whsec_...`.

## Environment variables

All variables are optional and read only in `lineup_backend/config.py`.
`.env.example` documents each with its default; `ENVIRONMENT_SETUP.md` is the
deployment checklist. Locally, `.env` is loaded by `app.py`.

| Variable | Default | Effect / what degrades without it |
|---|---|---|
| `GEMINI_API_KEY` | unset | Photo analysis, moderation, haircut matching. Without it `/analyze` returns mock data (`"mock": true`). |
| `GOOGLE_PLACES_API_KEY` | unset | Real barbershop search, reviews, photos. Without it `/barbers` returns sample shops. |
| `REPLICATE_API_TOKEN` | unset | Try-on generation. Without it `/virtual-tryon` returns a labelled preview (`"mode": "preview"`). |
| `FIREBASE_CREDENTIALS` | unset | Service-account JSON (one line): Firestore storage and Firebase token verification. Without it: memory store, dev auth (or disabled in production). |
| `FIREBASE_WEB_CONFIG` | unset | Public web-app config JSON served by `/config` so the browser can sign in with Firebase. |
| `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET` | unset | Post images uploaded to Cloudinary (all three). Without them images are stored as base64. |
| `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` | unset | Checkout/portal, and webhook verification. Without them 503 `stripe_not_configured`. |
| `STRIPE_PRICE_STARTER`, `STRIPE_PRICE_PLUS`, `STRIPE_PRICE_STUDIO`, `STRIPE_PRICE_BARBER_PRO` | unset | Stripe price ids; a pack without one is not purchasable (503 `price_not_configured`). |
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
(`insufficient_credits` with `needed`/`credits`, or `pro_required` with
`feature`), 403 (`forbidden`, `onboarding_required`), 404, 405, 409, 413, 429
(`Retry-After`; `daily_cap_reached` for per-user caps), 500, 502 (`stripe_error`)
or 503 (`auth_not_configured`, `stripe_not_configured`, `price_not_configured`).

Auth: `public` (no token; a valid token personalises), `user` (any signed-in
account), `barber` (barber role; the barber id in the path must be the caller),
`pro` (barber on the Pro plan), `dev-only` (404 unless `/config` reports
`auth.devLogin`). Credits are charged only for signed-in users.

| Method | Path | Auth | Credits | Notes |
|---|---|---|---|---|
| GET | `/` | public | - | Service name, version, endpoint list |
| GET | `/health` | public | - | `status`, `version`, `storage`, `integrations`, `auth_mode`, usage counters |
| GET | `/config` | public | - | Capability flags, `auth` (`mode`, `devLogin`, `firebase`), `billing` (`stripe`, `chargeForMock`, `dailyCaps`) |
| GET | `/metrics`, `/cache-stats` | ops | - | Request timing; Places cache stats. Send `X-Admin-Token: <LINEUP_ADMIN_TOKEN>`; without a configured token they exist only in dev auth mode (404 otherwise) |
| GET, POST | `/clear-cache` | ops | - | Empty the Places and matcher caches (same gate) |
| GET | `/auth/me` | user | - | `user`, `entitlements`, `barber` profile, `auth.mode` |
| POST | `/auth/dev-login` | dev-only | - | `{email, name?}` -> `token`, `expiresAt`, `user`; 404 in production or Firebase mode |
| POST | `/auth/onboarding` | user | - | `{role, shopName?, phone?, address?, bio?}` sets the role once; 409 `already_onboarded` |
| GET | `/billing/pricing` | public | - | Packs, Barber Pro, credit costs, `stripe_configured` |
| GET | `/billing/me` | user | - | `credits`, `plan`, `entitlements`, usage summary, Stripe state, dev flags |
| GET | `/billing/usage` | user | - | `?limit=50` ledger events, newest first |
| POST | `/billing/checkout` | user | - | `{packId}` or `{plan: "barber_pro"}` (barbers only) -> `{url, sessionId, mode}` |
| POST | `/billing/portal` | user | - | `{url}`; 400 `no_billing_account` |
| POST | `/billing/webhook` | Stripe signature | - | Grants credits, sets or clears Pro; idempotent by event id |
| POST | `/billing/dev-grant`, `/billing/dev-activate-pro` | dev-only (user / barber) | - | `{credits?}` (default 10, max 1000); `{active?}` toggles the Pro plan |
| POST | `/analyze` | user | 1 | `{image}` -> `analysis`, `recommendations[]`, `mock`, `billing`; daily cap 20 |
| POST | `/virtual-tryon` | user | 3 | `{userPhoto, styleDescription}` -> `resultImage`, `mode`, `billing`; daily cap 10 |
| GET | `/ai-insights` | public | - | Trending styles and hashtags |
| GET | `/barbers` | public | 1 | `?location=&styles=`; charged only when a signed-in user triggers a real Places call (cache hits are free); anonymous callers get cached or sample data |
| GET | `/places/photo` | public | - | `?ref=&maxwidth=` 302 to the Google photo |
| GET, PUT | `/barbers/<id>/profile` | public / barber | - | Shop name, phone, address, bio; 404 for unregistered ids |
| GET, POST | `/barbers/<id>/reviews` | public / user | - | POST needs `rating` 1-5; author from the token |
| GET, PUT | `/barbers/<id>/availability` | public / barber | - | Working hours, breaks, blocked dates |
| GET | `/barbers/<id>/available-slots` | public | - | `?date=YYYY-MM-DD` -> `slots[]` |
| GET, POST, PUT, DELETE | `/barbers/<id>/services` | public / barber | - | Unregistered ids get 3 unsaved defaults; `?service_id=` for PUT/DELETE |
| GET | `/barbers/<id>/clients` | pro | - | Clients aggregated from appointments |
| GET | `/barbers/<id>/clients/<cid>/history` | pro | - | That client's appointments |
| GET, POST, PUT | `/barbers/<id>/clients/<cid>/notes` | pro | - | Private notes per client |
| GET, POST | `/appointments` | user | - | `?type=client\|barber` (barber role for `barber`); own bookings only. POST needs `barberId`, `date`, `time`; client id from the token |
| PUT, POST | `/appointments/<id>/status`; `/accept`, `/reject` | barber (owner) | - | `status` in `pending`, `confirmed`, `rejected`, `rescheduled`, `cancelled`, `completed`; `reject` takes `reason` |
| POST | `/appointments/<id>/reschedule`, `/cancel` | user (booking's client or barber) | - | `reschedule` takes `date`, `time` |
| POST, PUT | `/appointments/<id>/notes` | barber (owner) | - | Add or update a note |
| GET, POST | `/social` | public / user | - | Feed with per-viewer `liked` and `mine`; POST `{image, caption, hashtags[]}`, moderated when Gemini is configured |
| GET, POST | `/social/<id>/comments` | public / user | - | POST `{text}` |
| POST | `/social/<id>/like`, `/share` | user | - | Toggle the caller's like; count a share |
| POST, GET | `/users/<id>/follow`, `/unfollow`; `/users/me/following` | user | - | -> `following`, `followingCount`; `{following: [...]}` |
| GET, POST, DELETE | `/portfolio`, `/portfolio/<barber_id>[/<work_id>]` | public / barber (owner) | - | POST needs `image`; the 7th photo needs Pro (402 `pro_required`) |
| GET, POST, DELETE | `/subscription-packages[/<id>]` | public / pro / barber (owner) | - | `?barber_id=`; POST needs `title` |
| GET, POST | `/client-subscriptions` | user | - | Own subscriptions; POST needs an existing `packageId` |

## Testing

```
.venv/bin/python -m pytest -q      # 159 passed, no network
```

Tests build the app with `create_app(**overrides)` (see `tests/conftest.py`):
no keys, limits off, demo data seeded, dev auth with a fixed secret, fakes for
every external service (`tests/helpers.py` has a `FakeStripeClient`). Fixtures
`as_client`, `as_barber`, `as_pro_barber` and `other_client` return a test
client that sends the bearer header. There is no JavaScript test suite; the
frontend is verified in headless Chromium at 375, 768 and 1440 px (Playwright
is not a dependency: `npm i --no-save playwright` when needed).

## Deployment (Render)

`render.yaml` is a Blueprint with two services:

- `lineup-backend` (Python 3.12.0): `pip install -r requirements.txt`, then
  `gunicorn app:app --workers 1 --threads 4 --timeout 120`, health check
  `/health`. One worker because the default store is per-process memory; the
  120 s timeout covers Replicate try-on calls. Sets `FLASK_ENV=production`,
  `LOG_FORMAT=json`, `LINEUP_TRUST_PROXY=true`, `LINEUP_PUBLIC_URL`,
  `LINEUP_ALLOWED_ORIGINS`, `LINEUP_FRONTEND_URL`; API keys, Firebase and
  Stripe values are `sync: false` and entered in the dashboard. Move to
  `--workers 2` only with `FIREBASE_CREDENTIALS` and
  `RATELIMIT_STORAGE_URI=redis://...`.
- `lineup-frontend` (static, Node 22.20.0): `npm ci && npm run build`, publish
  path `.`, SPA rewrite `/* -> /index.html`, `no-cache` for `index.html`,
  five-minute cache for `styles.css`, `config.js` and `src/*`, one day for
  `images/*`. `.renderignore` lists the files kept out of the published site.

After the first deploy, point `LINEUP_PUBLIC_URL`, `LINEUP_ALLOWED_ORIGINS` and
`LINEUP_FRONTEND_URL` at the assigned hostnames, make sure `config.js`
`API_URL` is the backend URL, add the frontend host to Firebase's authorized
domains and the backend host to the Stripe webhook. `/health` should report
`auth_mode: firebase` and `integrations.stripe: true`. `Procfile` carries the
same gunicorn command for other hosts.

## Project structure

```
app.py                      WSGI entry: load_dotenv(); app = create_app()
lineup_backend/
  __init__.py, factory.py   create_app, __version__ (3.1.0)
  config.py                 AppConfig.from_env(); the only place env vars are read
  pricing.py                credit costs, packs, Barber Pro, provider cost estimates
  context.py, extensions.py Services container; Flask-Limiter and rate("group")
  http.py, logging_config.py, metrics.py
  middleware/               cors, error_handler, auth (require_auth, require_role, optional_auth, assert_owner, require_pro)
  routes/                   system, auth, billing, analyze, barbers, social, appointments, portfolio
  services/                 auth, users, billing (Ledger, metered), stripe_gateway, stripe_events, gemini, places,
                            tryon, image_storage, barber_matcher, availability, haircuts, quota, cache
  storage/                  base.py (Store/Collection), memory.py, firestore.py, seed.py (demo data + dev accounts)
tests/                      pytest suite (conftest.py with auth fixtures, helpers.py, test_*.py)
scripts/dev.sh              API + static frontend for local development
get_metrics.py, Procfile, requirements.txt, requirements-dev.txt
index.html                  the single page: landing, pricing, sign-in, onboarding, app, account, legal views
config.js                   window.LINEUP_CONFIG (API URL, feature flags, ?api= ?debug= ?mock=)
src/input.css               Tailwind entry: tokens and @layer components
src/safelist.js             generated component-class safelist (src/tools/gen-safelist.js)
src/js/                     main, router, session, auth, billing, api, state, nav, dom, env, format, icons
src/js/ui/                  toast, modal, confirm, skeleton, dropzone
src/js/features/            analysis, tryon, barbers, booking, appointments, barber-dashboard, portfolio, community, shop, profile
styles.css, tailwind.config.js, package.json, package-lock.json
images/logo.png             logo; images/screens/ holds the landing-page product screenshots
render.yaml, .renderignore  Render Blueprint and the files kept out of the published site
.env.example, ENVIRONMENT_SETUP.md, CLAUDE.md
.static, static-build.sh    leftovers from the previous static deploy; unused
```

## Known limitations

- Storage is in memory by default: every restart or deploy clears users,
  credits, bookings, posts and portfolios. Firestore is the persistent option.
- Firestore, Firebase ID-token verification, Stripe, Gemini, Places, Replicate
  and Cloudinary are covered by tests with injected fakes, not live calls.
- One gunicorn worker. Scaling out needs Firestore plus a Redis rate-limit
  store, otherwise each worker sees different data and separate limits.
- Daily caps scan the user's charge events for the day; on Firestore a heavy
  user's query grows linearly.
- No admin role in the app. The operational endpoints (`/metrics`, `/cache-stats`,
  `/clear-cache`) are gated by `LINEUP_ADMIN_TOKEN` (header `X-Admin-Token`) and
  answer 404 in production without it. `GET /social` returns every post (no pagination).
- The Barber Pro `analytics` entitlement is exposed and the dashboard panel
  locks on it, but there is no analytics endpoint yet.
